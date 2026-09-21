import argparse
import json
import time
from pathlib import Path
from typing import Any

from sqlalchemy import func, select

from app.core.config import get_settings
from app.core.database import new_session
from app.models import DataSource, RagDocument
from app.text2sql.rag import BgeEmbeddingProvider, HybridSchemaRetriever


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate pgvector hybrid retrieval")
    parser.add_argument("--cases", default="tests/evaluation/rag-retrieval-cases.json")
    parser.add_argument("--output", default=".runtime/rag-evaluation.json")
    args = parser.parse_args()
    cases = json.loads(Path(args.cases).read_text(encoding="utf-8"))
    settings = get_settings()
    provider = BgeEmbeddingProvider(settings.rag_embedding_model)
    with new_session() as db:
        source = db.scalar(select(DataSource).where(DataSource.is_default.is_(True)))
        if source is None:
            raise RuntimeError("default data source is missing")
        retriever = HybridSchemaRetriever(db, settings, provider)
        stable_keys = {
            str(item.id): item.stable_key for item in db.scalars(select(RagDocument)).all()
        }
        rows: list[dict[str, Any]] = []
        reciprocal_rank = 0.0
        started = time.perf_counter()
        for case in cases:
            case_started = time.perf_counter()
            context = retriever.retrieve(case["question"], source.allowed_objects, [source.id])
            retrieved = [stable_keys[item] for item in context.rag_document_ids]
            expected = set(case["expectedStableKeys"])
            rank = next(
                (index for index, key in enumerate(retrieved, start=1) if key in expected), None
            )
            reciprocal_rank += 0.0 if rank is None else 1.0 / rank
            rows.append(
                {
                    "id": case["id"],
                    "question": case["question"],
                    "expectedStableKeys": sorted(expected),
                    "retrievedStableKeys": retrieved,
                    "hit": rank is not None,
                    "rank": rank,
                    "latencyMs": int((time.perf_counter() - case_started) * 1000),
                }
            )
        document_count = db.scalar(
            select(func.count()).select_from(RagDocument).where(RagDocument.enabled.is_(True))
        )
    hits = sum(1 for item in rows if item["hit"])
    report = {
        "caseCount": len(rows),
        "hits": hits,
        "recallAt5": hits / len(rows),
        "mrr": reciprocal_rank / len(rows),
        "documentCount": document_count,
        "embeddingModel": provider.model_name,
        "embeddingDimension": provider.dimension,
        "durationMs": int((time.perf_counter() - started) * 1000),
        "cases": rows,
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(
        json.dumps(
            {key: value for key, value in report.items() if key != "cases"},
            ensure_ascii=False,
            indent=2,
        )
    )
    if hits != len(rows):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
