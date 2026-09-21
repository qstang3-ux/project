import argparse
import json

from sqlalchemy import select

from app.core.config import get_settings
from app.core.database import new_session
from app.models import DataSource
from app.text2sql.knowledge import KNOWLEDGE_DOCUMENTS
from app.text2sql.rag import BgeEmbeddingProvider, RagIndexer


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the pgvector knowledge index")
    parser.add_argument("--data-source-id")
    args = parser.parse_args()
    settings = get_settings()
    with new_session() as db:
        source_id = args.data_source_id
        if source_id is None:
            source_id = db.scalar(select(DataSource.id).where(DataSource.is_default.is_(True)))
        provider = BgeEmbeddingProvider(settings.rag_embedding_model)
        report = RagIndexer(db, provider).build(KNOWLEDGE_DOCUMENTS, source_id)
    print(json.dumps(report.__dict__, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
