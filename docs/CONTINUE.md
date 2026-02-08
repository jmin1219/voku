# Voku Session Continuation

> Copy-paste this to start next session.

## Prompt

Continue Voku Phase 1 implementation in **mentor mode** (explain concepts, review code line-by-line, verify understanding before moving on). Read `docs/STATE.md` for current state and `brain/concepts/voku — development plan.md` Phase 1 section for full spec.

**Completed Feb 7 AM (Phase 1 Steps 1-3):**
- ✅ Database lifecycle (lifespan events, idempotent schema)
- ✅ Dependency injection system (4 service factories)
- ✅ Chat route wired to ChatService
- ✅ End-to-end pipeline: POST /api/chat/ → extraction → LeafNode creation
- ✅ Query script confirms node storage

**Completed Feb 7 PM (Phase 1 Steps 4-6):**
- ✅ EmbeddingService: bge-base-en-v1.5, 768-dim vectors, model caching
- ✅ GraphOps.store_embedding(): writes to NodeEmbedding table
- ✅ GraphOps.find_similar_nodes(): cosine similarity search (linear scan O(n))
- ✅ All tests passing: embedding storage verified, similarity validated
- ✅ Error handling review: EAFP approach, propagate DB errors to service layer

**Next: Phase 1 Steps 7-10**
7. Wire into ChatService: implement `_embed_propositions()` and `_deduplicate()` methods
8. Update dependency injection: pass EmbeddingService to ChatService in main.py
9. End-to-end dedup test: POST same message twice, verify second is skipped
10. Basic edge creation: SIMILAR_TO connections between related nodes (0.85-0.95 similarity)

**Implementation guidance for Step 7:**
- Add `EmbeddingService` to ChatService.__init__
- Make EmbeddingService a SINGLETON in app.state (avoid ~2s model reload per request)
- Restructure process_message flow: embed → dedup → create (NOT create → dedup)
  - Embed each proposition BEFORE creating nodes
  - Call find_similar_nodes(threshold=0.95) for each
  - If match found → skip creation, increment duplicates_found counter
  - If no match → create LeafNode, then store embedding
- Consider dropping `embedding` from find_similar_nodes return dict (only need node_id + similarity)
- Return ProcessedMessage with actual duplicates_found count

**Pre-flight before Step 7 (from Opus review):**
- Unskip and implement 5 embedding tests in test_graph.py:
  1. test_store_and_retrieve_embedding (round-trip)
  2. test_find_similar_above_threshold
  3. test_find_similar_below_threshold
  4. test_find_similar_empty_db
  5. test_store_embedding_zero_vector
- Use synthetic 768-dim vectors for speed (no model loading in tests)

**Success criteria:**
- POST /api/chat/ with "I'm anxious about co-ops"
- POST /api/chat/ with "Nervous about finding internships" 
- Second request returns existing node ID (duplicate detected)
- Cosine similarity > 0.95 triggers deduplication

**Files to work with:**
- `backend/app/services/chat.py` - ChatService (has TODO placeholders)
- `backend/app/main.py` - Dependency injection (add embedding_service factory)
- `backend/app/services/embeddings.py` - EmbeddingService (complete, tested)
- `backend/app/services/graph/operations.py` - store_embedding, find_similar_nodes (complete)

**Remember:**
- HNSW optimization deferred to Phase 2 (linear scan fast enough for demo)
- Multi-aspect embeddings deferred (single "content" embedding sufficient)
- Temporal NLP deferred to Phase 1.5 (today → 2026-02-07)
