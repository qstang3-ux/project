from __future__ import annotations

import hashlib
import math
import re
import time
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from functools import lru_cache
from typing import Protocol, cast
from uuid import UUID

from sqlalchemy import Select, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.errors import AppError
from app.models import RagDocument
from app.text2sql.knowledge import KnowledgeDocument
from app.text2sql.schema import SCHEMA_DESCRIPTIONS
from app.text2sql.types import RetrievedKnowledgeItem, SchemaContext


class EmbeddingProvider(Protocol):
    model_name: str
    dimension: int

    def encode(self, texts: Sequence[str]) -> list[list[float]]: ...


class BgeEmbeddingProvider:
    dimension = 512

    def __init__(self, model_name: str = "BAAI/bge-small-zh-v1.5") -> None:
        self.model_name = model_name

    def encode(self, texts: Sequence[str]) -> list[list[float]]:
        model = _load_sentence_transformer(self.model_name)
        prefixed = [f"为这个句子生成表示以用于检索相关文章：{text}" for text in texts]
        result = model.encode(prefixed, normalize_embeddings=True, show_progress_bar=False)
        vectors = cast(list[list[float]], result.tolist())
        if any(len(item) != self.dimension for item in vectors):
            raise AppError("EMBEDDING_INVALID", "Embedding 维度无效", 503)
        return vectors


class DeterministicEmbeddingProvider:
    model_name = "deterministic-test-embedding"
    dimension = 512

    def encode(self, texts: Sequence[str]) -> list[list[float]]:
        vectors: list[list[float]] = []
        for text in texts:
            values = []
            for index in range(self.dimension):
                digest = hashlib.sha256(f"{index}:{text}".encode()).digest()
                values.append((int.from_bytes(digest[:2], "big") / 32767.5) - 1.0)
            norm = math.sqrt(sum(item * item for item in values)) or 1.0
            vectors.append([item / norm for item in values])
        return vectors


@lru_cache(maxsize=2)
def _load_sentence_transformer(model_name: str):  # type: ignore[no-untyped-def]
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(model_name, device="cpu")


@dataclass(frozen=True)
class RagBuildReport:
    total: int
    inserted: int
    updated: int
    skipped: int
    disabled: int
    duration_ms: int
    embedding_model: str
    embedding_dimension: int


@dataclass(frozen=True)
class RagHit:
    document_id: UUID
    stable_key: str
    title: str
    content: str
    knowledge_type: str
    object_names: tuple[str, ...]
    score: float


def content_hash(document: KnowledgeDocument) -> str:
    payload = "\n".join(
        (document.stable_key, document.knowledge_type, document.title, document.content)
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class RagIndexer:
    def __init__(self, db: Session, provider: EmbeddingProvider) -> None:
        self.db = db
        self.provider = provider

    def build(
        self, documents: Sequence[KnowledgeDocument], data_source_id: UUID | None
    ) -> RagBuildReport:
        started = time.perf_counter()
        existing = {item.stable_key: item for item in self.db.scalars(select(RagDocument)).all()}
        changed = [
            item
            for item in documents
            if item.stable_key not in existing
            or existing[item.stable_key].content_hash != content_hash(item)
            or existing[item.stable_key].embedding_model != self.provider.model_name
            or existing[item.stable_key].embedding_dimension != self.provider.dimension
        ]
        vectors = self.provider.encode([item.content for item in changed]) if changed else []
        inserted = updated = 0
        now = datetime.now(UTC)
        for source, vector in zip(changed, vectors, strict=True):
            target = existing.get(source.stable_key)
            if target is None:
                target = RagDocument(stable_key=source.stable_key)
                self.db.add(target)
                inserted += 1
            else:
                updated += 1
            target.knowledge_type = source.knowledge_type
            target.source_path = source.source_path
            target.title = source.title
            target.content = source.content
            target.data_source_id = data_source_id
            target.object_names = list(source.object_names)
            target.metadata_json = source.metadata
            target.content_hash = content_hash(source)
            target.embedding_model = self.provider.model_name
            target.embedding_dimension = self.provider.dimension
            target.embedding = vector
            target.version = target.version + 1 if target.id and target in existing.values() else 1
            target.enabled = True
            target.updated_at = now
        keys = {item.stable_key for item in documents}
        disabled = 0
        for key, target in existing.items():
            if key not in keys and target.enabled:
                target.enabled = False
                target.updated_at = now
                disabled += 1
        self.db.commit()
        return RagBuildReport(
            len(documents),
            inserted,
            updated,
            len(documents) - len(changed),
            disabled,
            int((time.perf_counter() - started) * 1000),
            self.provider.model_name,
            self.provider.dimension,
        )


class HybridSchemaRetriever:
    def __init__(self, db: Session, settings: Settings, provider: EmbeddingProvider) -> None:
        self.db = db
        self.settings = settings
        self.provider = provider

    def retrieve(
        self, question: str, allowed_objects: list[str], data_source_ids: list[UUID]
    ) -> SchemaContext:
        documents = self._candidate_documents(data_source_ids)
        if not documents:
            if self.settings.app_env not in ("local", "test"):
                raise AppError("RAG_UNAVAILABLE", "知识库尚未构建", 503)
            return self._keyword_schema_fallback(question, allowed_objects)
        degraded = False
        try:
            query_vector = self.provider.encode([question])[0]
            vector_hits = self._vector_hits(query_vector, data_source_ids)
        except (AppError, SQLAlchemyError, OSError, RuntimeError):
            if self.settings.app_env not in ("local", "test"):
                raise AppError("RAG_UNAVAILABLE", "向量知识检索不可用", 503) from None
            vector_hits = []
            degraded = True
        keyword_hits = self._keyword_hits(question, documents)
        if not vector_hits and not keyword_hits:
            if self.settings.app_env not in ("local", "test"):
                raise AppError("RAG_UNAVAILABLE", "知识库尚未构建", 503)
            return self._keyword_schema_fallback(question, allowed_objects)
        fused = self._fuse(vector_hits, keyword_hits)
        allowed = set(allowed_objects)
        selected_hits = [
            hit
            for hit in fused
            if not hit.object_names or any(name in allowed for name in hit.object_names)
        ][: self.settings.rag_final_top_k]
        objects: list[str] = []
        for hit in selected_hits:
            for name in hit.object_names:
                if name in allowed and name not in objects:
                    objects.append(name)
        objects = objects[: self.settings.rag_max_objects]
        if not objects:
            objects = list(allowed_objects[: self.settings.rag_max_objects])
        descriptions = {name: SCHEMA_DESCRIPTIONS[name] for name in objects}
        knowledge = tuple(
            RetrievedKnowledgeItem(
                documentId=str(hit.document_id),
                stableKey=hit.stable_key,
                title=hit.title,
                content=hit.content,
                knowledgeType=hit.knowledge_type,
                objectNames=list(hit.object_names),
                trust="untrusted",
            )
            for hit in selected_hits
        )
        return SchemaContext(
            tuple(objects),
            descriptions,
            rag_document_ids=tuple(str(hit.document_id) for hit in selected_hits),
            retrieval_scores={hit.stable_key: round(hit.score, 8) for hit in selected_hits},
            degraded=degraded,
            retrieved_knowledge=knowledge,
        )

    def _base_query(self) -> Select[tuple[RagDocument]]:
        return select(RagDocument).where(RagDocument.enabled.is_(True))

    def _candidate_documents(self, data_source_ids: list[UUID]) -> list[RagDocument]:
        query = self._base_query().where(
            (RagDocument.data_source_id.is_(None))
            | (RagDocument.data_source_id.in_(data_source_ids))
        )
        return list(self.db.scalars(query))

    def _vector_hits(self, query_vector: list[float], data_source_ids: list[UUID]) -> list[RagHit]:
        distance = RagDocument.embedding.cosine_distance(query_vector).label("distance")
        statement = (
            select(RagDocument, distance)
            .where(
                RagDocument.enabled.is_(True),
                (RagDocument.data_source_id.is_(None))
                | (RagDocument.data_source_id.in_(data_source_ids)),
            )
            .order_by(distance)
            .limit(self.settings.rag_vector_top_k)
        )
        return [
            self._hit(document, max(0.0, 1.0 - float(value)))
            for document, value in self.db.execute(statement)
        ]

    def _keyword_hits(self, question: str, documents: list[RagDocument]) -> list[RagHit]:
        tokens = _tokens(question)
        scored: list[tuple[RagDocument, float]] = []
        for document in documents:
            haystack = f"{document.title} {document.content}".lower()
            keywords = document.metadata_json.get("keywords", [])
            score = sum(2.0 for item in keywords if str(item).lower() in question.lower())
            score += sum(1.0 for token in tokens if token in haystack)
            if score:
                scored.append((document, score))
        scored.sort(key=lambda item: (-item[1], item[0].stable_key))
        return [
            self._hit(document, score)
            for document, score in scored[: self.settings.rag_keyword_top_k]
        ]

    @staticmethod
    def _fuse(vector_hits: list[RagHit], keyword_hits: list[RagHit]) -> list[RagHit]:
        by_key = {hit.stable_key: hit for hit in [*vector_hits, *keyword_hits]}
        scores = {key: 0.0 for key in by_key}
        for rank, hit in enumerate(vector_hits, start=1):
            scores[hit.stable_key] += 0.65 / (60 + rank)
        for rank, hit in enumerate(keyword_hits, start=1):
            scores[hit.stable_key] += 0.35 / (60 + rank)
        return [
            RagHit(
                by_key[key].document_id,
                key,
                by_key[key].title,
                by_key[key].content,
                by_key[key].knowledge_type,
                by_key[key].object_names,
                score,
            )
            for key, score in sorted(scores.items(), key=lambda item: (-item[1], item[0]))
        ]

    @staticmethod
    def _hit(document: RagDocument, score: float) -> RagHit:
        return RagHit(
            document.id,
            document.stable_key,
            document.title,
            document.content,
            document.knowledge_type,
            tuple(document.object_names),
            score,
        )

    @staticmethod
    def _keyword_schema_fallback(question: str, allowed_objects: list[str]) -> SchemaContext:
        from app.text2sql.schema import SchemaRetriever

        fallback = SchemaRetriever().retrieve(question, allowed_objects)
        return SchemaContext(
            fallback.objects,
            fallback.descriptions,
            fallback.data_as_of,
            degraded=True,
        )


def _tokens(value: str) -> set[str]:
    ascii_tokens = re.findall(r"[a-z0-9_]+", value.lower())
    chinese_chunks = re.findall(r"[\u4e00-\u9fff]{2,}", value)
    ngrams = {
        chunk[index : index + size]
        for chunk in chinese_chunks
        for size in (2, 3, 4)
        for index in range(max(0, len(chunk) - size + 1))
    }
    return {item for item in [*ascii_tokens, *ngrams] if item}
