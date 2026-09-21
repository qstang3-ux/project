from typing import cast
from uuid import uuid4

from sqlalchemy.orm import Session

from app.models import RagDocument
from app.text2sql.knowledge import KNOWLEDGE_DOCUMENTS, KnowledgeDocument
from app.text2sql.rag import (
    DeterministicEmbeddingProvider,
    HybridSchemaRetriever,
    RagHit,
    RagIndexer,
    _tokens,
    content_hash,
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


def test_pipeline_schema_knowledge_defines_project_count_identifier() -> None:
    document = next(
        item for item in KNOWLEDGE_DOCUMENTS if item.stable_key == "schema.pipeline_risk"
    )

    assert document.object_names == ("mart.v_pipeline_risk",)
    assert "project_id" in document.content
    assert "contract_id" in document.content

    metric = next(item for item in KNOWLEDGE_DOCUMENTS if item.stable_key == "metric.project_count")
    assert metric.object_names == ("mart.v_pipeline_risk",)


def test_index_reenables_unchanged_disabled_document() -> None:
    source = KnowledgeDocument(
        "metric.test",
        "metric",
        "docs/test.md",
        "测试指标",
        "测试指标使用 value 字段。",
        ("mart.v_sales_performance",),
    )
    provider = DeterministicEmbeddingProvider()
    existing = RagDocument(
        id=uuid4(),
        stable_key=source.stable_key,
        knowledge_type=source.knowledge_type,
        source_path=source.source_path,
        title=source.title,
        content=source.content,
        data_source_id=None,
        object_names=list(source.object_names),
        metadata_json={},
        content_hash=content_hash(source),
        embedding_model=provider.model_name,
        embedding_dimension=provider.dimension,
        embedding=provider.encode([source.content])[0],
        version=1,
        enabled=False,
    )

    class ScalarResult:
        def all(self) -> list[RagDocument]:
            return [existing]

    class RecordingSession:
        committed = False

        def scalars(self, statement: object) -> ScalarResult:
            del statement
            return ScalarResult()

        def add(self, document: RagDocument) -> None:
            raise AssertionError(f"unexpected insert: {document.stable_key}")

        def commit(self) -> None:
            self.committed = True

    db = RecordingSession()
    report = RagIndexer(cast(Session, db), provider).build([source], None)

    assert existing.enabled is True
    assert existing.version == 2
    assert report.updated == 1
    assert report.skipped == 0
    assert db.committed is True
