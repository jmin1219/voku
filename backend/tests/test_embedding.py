"""
Tests for embedding interface and implementations.

Component 1.3 in COMPONENT_SPEC.md.
"""

import numpy as np
from services.embedding.bge import BGEBaseEmbedding


def test_embed_single_text_shape():
    embedder = BGEBaseEmbedding()
    vec = embedder.embed("I think rowing is limited by my ankle")
    assert vec.shape == (768,)
    assert vec.dtype == np.float32


def test_embed_batch_shape():
    embedder = BGEBaseEmbedding()
    texts = ["First proposition", "Second proposition", "Third proposition"]
    matrix = embedder.embed_batch(texts)
    assert matrix.shape == (3, 768)


def test_similar_texts_high_cosine():
    embedder = BGEBaseEmbedding()
    v1 = embedder.embed("My ankle limits my rowing performance")
    v2 = embedder.embed("Ankle mobility constrains how far I can extend on the erg")
    score = float(np.dot(v1, v2))
    assert score > 0.7


def test_unrelated_texts_low_cosine():
    embedder = BGEBaseEmbedding()
    v1 = embedder.embed("My ankle limits my rowing performance")
    v2 = embedder.embed("The knowledge graph market will reach 28 billion by 2028")
    score = float(np.dot(v1, v2))
    assert score < 0.5


def test_model_properties():
    embedder = BGEBaseEmbedding()
    assert embedder.dimensions == 768
    assert embedder.model_name == "bge-base-en-v1.5"
