from uuid import uuid4

from app.text2sql.rag import (
    DeterministicEmbeddingProvider,
    HybridSchemaRetriever,
    RagHit,
    _tokens,
)


def test_deterministic_embedding_is_normalized_and_stable() -> None:
    provider = DeterministicEmbeddingProvider()
    first, second = provider.encode(["商业目标", "商业目标"])
    assert first == second
    assert len(first) == 512
    assert abs(sum(item * item for item in first) - 1.0) < 1e-9


def test_chinese_keyword_tokenization_includes_business_terms() -> None:
    tokens = _tokens("北京代表处2026年收入同比")
    assert "收入" in tokens
    assert "同比" in tokens
    assert "2026" in tokens


def test_hybrid_fusion_rewards_hits_present_in_both_rankings() -> None:
    shared = RagHit(
        document_id=uuid4(),
        stable_key="shared",
        title="shared",
        content="",
        knowledge_type="metric",
        object_names=("mart.v_target_achievement",),
        score=1.0,
    )
    vector_only = RagHit(
        document_id=uuid4(),
        stable_key="vector",
        title="vector",
        content="",
        knowledge_type="schema",
        object_names=("mart.v_sales_performance",),
        score=1.0,
    )
    fused = HybridSchemaRetriever._fuse([shared, vector_only], [shared])
    assert fused[0].stable_key == "shared"
