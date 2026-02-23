"""
ProjectionService — computes UMAP projections, DBSCAN clustering,
and dimension coloring for the phase space visualization.

Extracted from routes/propositions.py (Piece 5, Build 4).
Pure read-only computation: propositions + embeddings → 3D positions,
model_evidence + user_model → dimension assignments per node.
"""

import sqlite3
from collections import Counter, defaultdict
from datetime import datetime

import numpy as np
from sklearn.cluster import DBSCAN
from umap import UMAP


SCALE = 5.0  # Normalize UMAP output to roughly [-5, 5]
KNN_K = 5    # Neighbors per node for ambient edge mesh

STOPWORDS = {
    "the", "and", "for", "that", "this", "with", "from", "have", "has",
    "been", "was", "were", "are", "but", "not", "they", "their", "than",
    "its", "also", "about", "into", "more", "when", "what", "which",
    "will", "would", "could", "should", "does", "did", "had", "being",
    "over", "after", "before", "between", "through", "during", "without",
    "because", "each", "other", "some", "very", "just", "only", "then",
    "still", "even", "most", "much", "both", "same", "such", "like",
    "used", "using", "based", "need", "want", "make", "take", "user", "keep",
}


def _extract_keywords(text: str, max_kw: int = 15) -> list[str]:
    words = set(text.lower().split())
    keywords = [
        w.strip(".,;:!?()\"'")
        for w in words
        if len(w) > 3 and w not in STOPWORDS
    ]
    return keywords[:max_kw]


def _scale_positions(coords: np.ndarray) -> np.ndarray:
    centered = coords - coords.mean(axis=0)
    factor = SCALE / max(np.abs(centered).max(), 0.001)
    return centered * factor


def _compute_knn_edges(
    X: np.ndarray, ids: list[str], k: int = KNN_K
) -> list[dict]:
    """Compute k-nearest-neighbor edges from cosine similarity in embedding space.

    Operates on the raw embedding matrix (768d), NOT the UMAP projection.
    UMAP preserves local neighborhoods but distorts distances — the original
    space gives ground-truth semantic proximity.

    Returns deduplicated undirected edges: [{source, target, weight}].
    Weight = cosine similarity (0-1). Higher = more semantically related.

    Deduplication: edge (A,B) and (B,A) collapse to one entry with the
    higher weight. Uses frozenset of index pairs as the dedup key.
    """
    n = X.shape[0]
    if n < 2:
        return []

    # L2-normalize rows → dot product = cosine similarity
    norms = np.linalg.norm(X, axis=1, keepdims=True)
    norms = np.where(norms == 0, 1.0, norms)  # guard zero-vectors
    X_norm = X / norms

    # Full similarity matrix: (n, n) — feasible for n ≤ ~5000
    sim = X_norm @ X_norm.T

    # Zero out diagonal (no self-edges)
    np.fill_diagonal(sim, 0.0)

    # Effective k: can't have more neighbors than n-1
    k_eff = min(k, n - 1)

    # For each node, find top-k neighbor indices by descending similarity
    # argpartition is O(n) vs O(n log n) for full argsort — matters at scale
    top_k_indices = np.argpartition(-sim, k_eff, axis=1)[:, :k_eff]

    # Collect edges with deduplication
    seen: set[frozenset[int]] = set()
    edges: list[dict] = []

    for i in range(n):
        for j_idx in range(k_eff):
            j = int(top_k_indices[i, j_idx])
            pair = frozenset((i, j))
            if pair in seen:
                continue
            seen.add(pair)
            weight = float(sim[i, j])
            if weight <= 0:
                continue  # skip anti-correlated or zero-similarity
            edges.append({
                "source": ids[i],
                "target": ids[j],
                "weight": round(weight, 4),
            })

    return edges


def _load_dimension_map(conn: sqlite3.Connection) -> dict[str, dict]:
    """Build prop_id → {dimension, relevance} using highest-relevance assignment.

    Each proposition can map to 1-3 dimensions. We pick the one with the
    highest relevance score as the "primary" dimension for coloring.
    Multi-assignment rendering (blends, secondary indicators) deferred.
    """
    rows = conn.execute(
        """SELECT me.proposition_id, me.relevance, um.dimension
           FROM model_evidence me
           JOIN user_model um ON me.model_id = um.id
           ORDER BY me.proposition_id, me.relevance DESC"""
    ).fetchall()

    # Group by proposition, keep highest relevance
    best: dict[str, dict] = {}
    for row in rows:
        pid = row["proposition_id"]
        if pid not in best or row["relevance"] > best[pid]["relevance"]:
            best[pid] = {
                "dimension": row["dimension"],
                "relevance": round(float(row["relevance"]), 3),
            }
    return best


def compute_projection(db_path: str) -> dict:
    """Compute UMAP projections, clustering, and dimension coloring.

    Opens a fresh connection (thread-safe for FastAPI's threadpool).
    Returns {nodes, clusters, meta} ready for JSON serialization.
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    # --- Load propositions + embeddings ---
    props = conn.execute(
        "SELECT id, text, node_type, confidence, source_file, "
        "event_timeframe, created_at, superseded_in_conversation, status "
        "FROM propositions ORDER BY created_at"
    ).fetchall()

    emb_rows = conn.execute(
        "SELECT proposition_id, embedding FROM embeddings"
    ).fetchall()
    emb_map = {
        row["proposition_id"]: np.frombuffer(row["embedding"], dtype=np.float32).copy()
        for row in emb_rows
    }

    # --- Load dimension assignments ---
    dim_map = _load_dimension_map(conn)
    conn.close()

    # --- Build aligned arrays ---
    data = []
    vectors = []
    timestamps = []

    for p in props:
        pid = p["id"]
        if pid not in emb_map:
            continue

        created = p["created_at"] or ""
        try:
            ts = datetime.fromisoformat(created).timestamp()
        except (ValueError, TypeError):
            ts = 0.0

        dim_info = dim_map.get(pid, {})

        data.append({
            "id": pid,
            "text": p["text"],
            "nodeType": p["node_type"],
            "confidence": float(p["confidence"]) if p["confidence"] else 0.5,
            "sourceFile": p["source_file"],
            "eventTimeframe": p["event_timeframe"],
            "createdAt": created,
            "supersededInConversation": bool(p["superseded_in_conversation"]),
            "status": p["status"] or "active",
            "dimension": dim_info.get("dimension"),
            "dimensionRelevance": dim_info.get("relevance", 0.0),
        })
        vectors.append(emb_map[pid])
        timestamps.append(ts)

    if not data:
        return {"nodes": [], "clusters": [], "edges": [], "meta": {"count": 0}}

    X = np.array(vectors)
    ts_arr = np.array(timestamps)
    n = len(data)
    node_ids = [d["id"] for d in data]

    # --- k-NN edges (computed in original 768d embedding space) ---
    edges = _compute_knn_edges(X, node_ids)

    # --- 3D UMAP (semantic space) ---
    n_neighbors_3d = min(15, n - 1)
    reducer_3d = UMAP(
        n_components=3, n_neighbors=n_neighbors_3d,
        min_dist=0.3, random_state=42,
    )
    X_3d = reducer_3d.fit_transform(X)
    X_3d_scaled = _scale_positions(X_3d)

    # --- 2D UMAP + time axis (developmental arc) ---
    n_neighbors_2d = min(15, n - 1)
    reducer_2d = UMAP(
        n_components=2, n_neighbors=n_neighbors_2d,
        min_dist=0.3, random_state=42,
    )
    X_2d = reducer_2d.fit_transform(X)
    X_2d_scaled = _scale_positions(X_2d)

    # Normalize timestamps to [-SCALE, SCALE] for Z axis
    ts_min, ts_max = ts_arr.min(), ts_arr.max()
    if ts_max > ts_min:
        ts_norm = (ts_arr - ts_min) / (ts_max - ts_min)
        ts_z = ts_norm * (2 * SCALE) - SCALE
    else:
        ts_norm = np.zeros(n)
        ts_z = np.zeros(n)

    age_arr = ts_norm

    # --- DBSCAN clustering (on 3D semantic positions) ---
    db = DBSCAN(eps=0.7, min_samples=3).fit(X_3d_scaled)
    labels = db.labels_
    n_clusters = len(set(labels)) - (1 if -1 in labels else 0)

    # --- Build nodes ---
    nodes = []
    for i, d in enumerate(data):
        keywords = _extract_keywords(d["text"])
        nodes.append({
            **d,
            "label": d["text"][:80],
            "fullText": d["text"],
            "position": [
                round(float(X_3d_scaled[i, 0]), 3),
                round(float(X_3d_scaled[i, 1]), 3),
                round(float(X_3d_scaled[i, 2]), 3),
            ],
            "positionTime": [
                round(float(X_2d_scaled[i, 0]), 3),
                round(float(ts_z[i]), 3),
                round(float(X_2d_scaled[i, 1]), 3),
            ],
            "age": round(float(age_arr[i]), 4),
            "keywords": keywords,
            "cluster": int(labels[i]),
        })

    # --- Build cluster metadata ---
    clusters = []
    for c in range(n_clusters):
        mask = labels == c
        center = X_3d_scaled[mask].mean(axis=0)
        radius = float(np.max(np.linalg.norm(X_3d_scaled[mask] - center, axis=1)))
        member_kw: Counter = Counter()
        for idx in np.where(mask)[0]:
            member_kw.update(nodes[idx]["keywords"][:8])
        top_words = [w for w, _ in member_kw.most_common(3)]

        clusters.append({
            "id": c,
            "center": [round(float(center[0]), 3), round(float(center[1]), 3), round(float(center[2]), 3)],
            "radius": round(radius, 3),
            "count": int(mask.sum()),
            "label": " / ".join(top_words),
        })

    return {
        "nodes": nodes,
        "clusters": clusters,
        "edges": edges,
        "meta": {
            "count": n,
            "n_clusters": n_clusters,
            "n_edges": len(edges),
            "knn_k": KNN_K,
            "method": "UMAP",
            "params_3d": {"n_neighbors": n_neighbors_3d, "min_dist": 0.3, "n_components": 3},
            "params_2d": {"n_neighbors": n_neighbors_2d, "min_dist": 0.3, "n_components": 2},
        },
    }
