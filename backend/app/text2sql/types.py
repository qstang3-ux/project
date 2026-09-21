from dataclasses import dataclass, field
from typing import Any, Literal, TypedDict

Intent = Literal[
    "data_query",
    "clarification",
    "business_definition",
    "product_help",
    "chat",
    "out_of_scope",
    "unsafe",
]


class PromptContextItem(TypedDict):
    channel: Literal[
        "history",
        "structured_memory",
        "generated_sql",
        "database_error",
    ]
    source: str
    role: str
    trust: Literal["untrusted"]
    content: Any
    provenance: dict[str, Any]


class RetrievedKnowledgeItem(TypedDict):
    documentId: str
    stableKey: str
    title: str
    content: str
    knowledgeType: str
    objectNames: list[str]
    trust: Literal["untrusted"]


@dataclass(frozen=True)
class IntentClassification:
    intent: Intent
    normalized_question: str
    missing_slots: tuple[str, ...]
    confidence: float
    reason_code: str
    model_name: str
    prompt_tokens: int = 0
    completion_tokens: int = 0


@dataclass(frozen=True)
class SchemaContext:
    objects: tuple[str, ...]
    descriptions: dict[str, str]
    data_as_of: str = "2026-05-31"
    rag_document_ids: tuple[str, ...] = ()
    retrieval_scores: dict[str, float] = field(default_factory=dict)
    degraded: bool = False
    retrieved_knowledge: tuple[RetrievedKnowledgeItem, ...] = ()


@dataclass(frozen=True)
class ModelSqlOutput:
    intent: str
    assumptions: tuple[str, ...]
    sql: str | None
    selected_objects: tuple[str, ...]
    model_name: str
    prompt_tokens: int = 0
    completion_tokens: int = 0


@dataclass(frozen=True)
class ModelAnswerOutput:
    answer: str
    chart: dict[str, Any]
    follow_up_questions: list[str]
    model_name: str
    prompt_tokens: int = 0
    completion_tokens: int = 0


@dataclass(frozen=True)
class ValidatedSql:
    original_sql: str
    sql: str
    objects: tuple[str, ...]
    rule_version: str = "1.0"


@dataclass(frozen=True)
class QueryResult:
    columns: list[dict[str, Any]]
    rows: list[dict[str, Any]]
    row_count: int
    truncated: bool
    response_bytes: int


@dataclass(frozen=True)
class AnswerBundle:
    answer: str
    chart: dict[str, Any]
    follow_up_questions: list[str] = field(default_factory=list)
