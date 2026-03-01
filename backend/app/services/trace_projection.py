"""
Trace projection — UMAP positions, DBSCAN clustering, k-NN edges for phase space.

v2 replacement for projection.py. Same algorithms, trace-based data source.
Reads from SQLiteTraceStorage (via get_all_embeddings + trace queries).

Differences from v1:
- No proposition types, no dimension assignments, no user model
- Source type (user/assistant) replaces nodeType
- conversation_id included for grouping
- Annotations included as node metadata
- k-NN edges computed here; ConnectionService edges merged by the route

Design: SPEC.md § UI/UX Architecture — Phase Space
"""

from collections import Counter
from datetime import datetime

import numpy as np
from sklearn.cluster import DBSCAN
from umap import UMAP

from app.services.storage.sqlite_trace import SQLiteTraceStorage


SCALE = 5.0
KNN_K = 5

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
    """k-NN edges from cosine similarity in embedding space (768d).

    Returns deduplicated undirected edges: [{source, target, weight}].
    """
    n = X.shape[0]
    if n < 2:
        return []

    norms = np.linalg.norm(X, axis=1, keepdims=True)
    norms = np.where(norms == 0, 1.0, norms)
    X_norm = X / norms
    sim = X_norm @ X_norm.T
    np.fill_diagonal(sim, 0.0)

    k_eff = min(k, n - 1)
    top_k_indices = np.argpartition(-sim, k_eff, axis=1)[:, :k_eff]

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
                continue
            edges.append({
                "source": ids[i],
                "target": ids[j],
                "weight": round(weight, 4),
            })

    return edges


def compute_trace_projection(storage: SQLiteTraceStorage) -> dict:
    """Compute UMAP projections, clustering, and k-NN edges for traces.

    Args:
        storage: Initialized SQLiteTraceStorage with traces + embeddings.

    Returns:
        {nodes, clusters, edges, meta} ready for JSON serialization.
    """
    # --- Load embeddings from cache ---
    trace_ids, embedding_matrix = storage.get_all_embeddings()

    if len(trace_ids) == 0:
        return {"nodes": [], "clusters": [], "orientations": [], "edges": [], "meta": {"count": 0}}

    # --- Load trace metadata ---
    traces_by_id = {}
    for tid in trace_ids:
        trace = storage.get_trace(tid)
        if trace is not None:
            traces_by_id[tid] = trace

    # --- Load annotations for all traces ---
    annotations_by_trace: dict[str, list[dict]] = {}
    for tid in trace_ids:
        anns = storage.get_annotations_for_trace(tid)
        if anns:
            annotations_by_trace[tid] = [
                {"type": a.type, "key": a.key, "value": a.value}
                for a in anns
            ]

    # --- Build aligned arrays (only traces that have both metadata + embedding) ---
    data = []
    vectors = []
    timestamps = []

    for i, tid in enumerate(trace_ids):
        if tid not in traces_by_id:
            continue

        trace = traces_by_id[tid]
        try:
            ts = datetime.fromisoformat(trace.timestamp).timestamp()
        except (ValueError, TypeError):
            ts = 0.0

        data.append({
            "id": tid,
            "text": trace.content,
            "source": trace.source,
            "conversationId": trace.conversation_id,
            "parentTraceId": trace.parent_trace_id,
            "createdAt": trace.timestamp,
            "annotations": annotations_by_trace.get(tid, []),
        })
        vectors.append(embedding_matrix[i])
        timestamps.append(ts)

    if not data:
        return {"nodes": [], "clusters": [], "orientations": [], "edges": [], "meta": {"count": 0}}

    X = np.array(vectors)
    ts_arr = np.array(timestamps)
    n = len(data)
    node_ids = [d["id"] for d in data]

    # --- k-NN edges (768d embedding space) ---
    edges = _compute_knn_edges(X, node_ids)

    # --- UMAP (requires n_neighbors > 1, so n >= 3) ---
    if n < 5:
        # Too few traces for UMAP's spectral initialization — assign origin positions
        # UMAP internally needs k eigenvectors where k > n for small n, causing scipy to crash
        X_3d_scaled = np.zeros((n, 3), dtype=np.float32)
        X_2d_scaled = np.zeros((n, 2), dtype=np.float32)
    else:
        n_neighbors_3d = min(15, n - 1)
        reducer_3d = UMAP(
            n_components=3, n_neighbors=n_neighbors_3d,
            min_dist=0.3, random_state=42,
        )
        X_3d = reducer_3d.fit_transform(X)
        X_3d_scaled = _scale_positions(X_3d)

        n_neighbors_2d = min(15, n - 1)
        reducer_2d = UMAP(
            n_components=2, n_neighbors=n_neighbors_2d,
            min_dist=0.3, random_state=42,
        )
        X_2d = reducer_2d.fit_transform(X)
        X_2d_scaled = _scale_positions(X_2d)

    # Normalize timestamps for Z axis
    ts_min, ts_max = ts_arr.min(), ts_arr.max()
    if ts_max > ts_min:
        ts_norm = (ts_arr - ts_min) / (ts_max - ts_min)
        ts_z = ts_norm * (2 * SCALE) - SCALE
    else:
        ts_norm = np.zeros(n)
        ts_z = np.zeros(n)

    # --- Hierarchical clustering (on normalized embeddings, not UMAP) ---
    # Normalize embeddings for cosine-based DBSCAN
    emb_norms = np.linalg.norm(X, axis=1, keepdims=True) + 1e-10
    X_normed = X / emb_norms

    # Fine clusters: eps=0.3 in cosine distance (1 - similarity)
    # DBSCAN with metric='cosine' on normalized vectors
    db_fine = DBSCAN(eps=0.3, min_samples=3, metric="cosine").fit(X_normed)
    labels = db_fine.labels_
    n_clusters = len(set(labels)) - (1 if -1 in labels else 0)

    # Orientation clusters: DBSCAN eps=0.6 on fine cluster centroids
    orientation_labels = np.full(n, -1, dtype=int)  # per-trace orientation
    cluster_orientation_map = {}  # fine_cluster_id -> orientation_id
    orientations_data = []

    if n_clusters >= 2:
        # Compute centroids per fine cluster
        centroid_ids = []
        centroids = []
        for c in range(n_clusters):
            mask = labels == c
            if mask.sum() == 0:
                continue
            centroid_ids.append(c)
            centroids.append(X_normed[mask].mean(axis=0))

        if len(centroids) >= 2:
            C = np.array(centroids)
            C_norms = np.linalg.norm(C, axis=1, keepdims=True) + 1e-10
            C_normed = C / C_norms

            db_orient = DBSCAN(
                eps=0.6, min_samples=1, metric="cosine"
            ).fit(C_normed)
            orient_labels = db_orient.labels_

            for i, cid in enumerate(centroid_ids):
                oid = int(orient_labels[i])
                cluster_orientation_map[cid] = oid

            # Map orientation to individual traces
            for i in range(n):
                fc = int(labels[i])
                if fc in cluster_orientation_map:
                    orientation_labels[i] = cluster_orientation_map[fc]
    elif n_clusters == 1:
        # Single cluster = single orientation
        cluster_orientation_map[0] = 0
        for i in range(n):
            if labels[i] == 0:
                orientation_labels[i] = 0

    # --- Build nodes ---
    nodes = []
    for i, d in enumerate(data):
        keywords = _extract_keywords(d["text"])
        nodes.append({
            "id": d["id"],
            "label": d["text"][:80],
            "fullText": d["text"],
            "source": d["source"],
            "conversationId": d["conversationId"],
            "parentTraceId": d["parentTraceId"],
            "createdAt": d["createdAt"],
            "annotations": d["annotations"],
            "age": round(float(ts_norm[i]), 4),
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
            "keywords": keywords,
            "cluster": int(labels[i]),
            "orientation": int(orientation_labels[i]),
        })

    # --- Build cluster metadata ---
    clusters = []
    for c in range(n_clusters):
        mask = labels == c
        center = X_3d_scaled[mask].mean(axis=0)
        radius = float(np.max(np.linalg.norm(X_3d_scaled[mask] - center, axis=1)))
        member_kw: Counter = Counter()
        member_ids = []
        for idx in np.where(mask)[0]:
            member_kw.update(nodes[idx]["keywords"][:8])
            member_ids.append(nodes[idx]["id"])
        top_words = [w for w, _ in member_kw.most_common(3)]

        clusters.append({
            "id": c,
            "center": [round(float(center[0]), 3), round(float(center[1]), 3), round(float(center[2]), 3)],
            "radius": round(radius, 3),
            "count": int(mask.sum()),
            "label": " / ".join(top_words),
            "trace_ids": member_ids,
            "orientation_id": cluster_orientation_map.get(c, -1),
        })

    # --- Build orientation metadata ---
    orient_ids_set = set(cluster_orientation_map.values()) - {-1}
    orientations = []
    for oid in sorted(orient_ids_set):
        member_cluster_ids = [
            cid for cid, o in cluster_orientation_map.items() if o == oid
        ]
        # Aggregate center from member clusters
        member_trace_mask = orientation_labels == oid
        if member_trace_mask.sum() > 0:
            o_center = X_3d_scaled[member_trace_mask].mean(axis=0)
        else:
            o_center = np.zeros(3)

        # Aggregate keywords from member clusters
        o_kw: Counter = Counter()
        for cid in member_cluster_ids:
            for cl in clusters:
                if cl["id"] == cid:
                    o_kw.update(cl["label"].split(" / "))
        o_label = " / ".join([w for w, _ in o_kw.most_common(3)])

        orientations.append({
            "id": oid,
            "label": o_label,
            "cluster_ids": member_cluster_ids,
            "center": [round(float(o_center[0]), 3), round(float(o_center[1]), 3), round(float(o_center[2]), 3)],
            "trace_count": int(member_trace_mask.sum()),
        })

    return {
        "nodes": nodes,
        "clusters": clusters,
        "orientations": orientations,
        "edges": edges,
        "meta": {
            "count": n,
            "n_clusters": n_clusters,
            "n_orientations": len(orientations),
            "n_edges": len(edges),
            "knn_k": KNN_K,
        },
    }
