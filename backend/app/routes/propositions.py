"""
Propositions API — serves all propositions with 3D positions for the phase space.

GET /api/propositions
  - Runs UMAP 3D (semantic) + UMAP 2D + time axis (developmental)
  - Returns nodes with both position sets, clusters, temporal metadata
  - Cached in memory; recomputed after extraction

Design: two layouts per node
  - position:     [x, y, z] from 3D UMAP (semantic space)
  - positionTime: [x, y, z] from 2D UMAP + normalized time as Z axis (developmental arc)
"""

import json
from collections import Counter
from datetime import datetime, timezone

import numpy as np
from fastapi import APIRouter
from sklearn.cluster import DBSCAN

from app.dependencies import propositions_storage

router = APIRouter(prefix="/api", tags=["propositions"])

# In-memory cache — recomputed on first call and after extraction
_cache: dict | None = None

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

SCALE = 5.0  # Normalize UMAP output to roughly [-5, 5]


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


def _compute_projection() -> dict:
    """Compute UMAP projections and clustering for all propositions."""
    import sqlite3
    from umap import UMAP

    # Open a fresh connection (thread-safe) — don't use the shared one
    # because FastAPI runs sync endpoints in a threadpool
    db_path = propositions_storage.db_path
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

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

    # Build aligned arrays
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
        })
        vectors.append(emb_map[pid])
        timestamps.append(ts)

    if not data:
        return {"nodes": [], "clusters": [], "meta": {"count": 0}}

    X = np.array(vectors)
    ts_arr = np.array(timestamps)
    n = len(data)

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
        ts_norm = (ts_arr - ts_min) / (ts_max - ts_min)  # 0..1
        ts_z = ts_norm * (2 * SCALE) - SCALE  # -5..5
    else:
        ts_z = np.zeros(n)

    # Normalized age: 0 = oldest, 1 = newest
    age_arr = ts_norm if ts_max > ts_min else np.zeros(n)

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
        "meta": {
            "count": n,
            "n_clusters": n_clusters,
            "method": "UMAP",
            "params_3d": {"n_neighbors": n_neighbors_3d, "min_dist": 0.3, "n_components": 3},
            "params_2d": {"n_neighbors": n_neighbors_2d, "min_dist": 0.3, "n_components": 2},
        },
    }


def invalidate_cache():
    """Called after extraction to force recomputation on next request."""
    global _cache
    _cache = None


@router.get("/propositions")
def get_propositions():
    """Return all propositions with 3D positions and temporal metadata."""
    global _cache
    if _cache is None:
        _cache = _compute_projection()
    return _cache
