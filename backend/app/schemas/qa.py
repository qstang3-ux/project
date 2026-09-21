from datetime import date, datetime
from typing import Annotated, Any, Literal
from uuid import UUID

from pydantic import Field, StringConstraints

from app.schemas.common import ApiModel, ErrorDetail, PageMeta, TokenUsage

ExecutionStatus = Literal[
    "queued", "running", "awaiting_input", "completed", "failed", "cancelled", "rejected"
]
IntentType = Literal[
    "data_query",
    "clarification",
    "business_definition",
    "product_help",
    "chat",
    "out_of_scope",
    "unsafe",
]
SqlValidationStatus = Literal["not_started", "passed", "rejected"]


class DataSourceOut(ApiModel):
    id: UUID
    name: str
    description: str | None
    group: Literal["ledger", "report"]
    enabled: bool
    is_default: bool
    unavailable_reason: str | None
    data_as_of: date
    allowed_objects: list[str]


class DataSourceListResponse(ApiModel):
    items: list[DataSourceOut]
    max_selection: int = 8


class SessionCreate(ApiModel):
    title: Annotated[str, StringConstraints(min_length=1, max_length=60)] | None = None


class SessionUpdate(ApiModel):
    title: Annotated[str, StringConstraints(min_length=1, max_length=60)] | None = None
    pinned: bool | None = None


class SessionOut(ApiModel):
    id: UUID
    title: str
    pinned: bool
    parent_session_id: UUID | None = None
    message_count: int
    last_message_preview: str | None = None
    created_at: datetime
    updated_at: datetime


class SessionListResponse(ApiModel):
    items: list[SessionOut]
    page: PageMeta


class MessageOut(ApiModel):
    id: UUID
    session_id: UUID
    role: Literal["user", "assistant"]
    content: str
    source_message_id: UUID | None = None
    execution_id: UUID | None = None
    execution_status: ExecutionStatus | None = None
    favorite_id: UUID | None = None
    current_version_no: int | None = None
    created_at: datetime


class MessageListResponse(ApiModel):
    items: list[MessageOut]
    next_cursor: str | None = None
    has_more: bool


class QueryCreate(ApiModel):
    question: str = Field(min_length=1, max_length=2000)
    data_source_ids: list[UUID] = Field(min_length=1, max_length=8)
    generate_chart: bool = True
    context_message_ids: list[UUID] = Field(default_factory=list, max_length=20)


class MessageResubmitRequest(QueryCreate):
    branch_title: Annotated[str, StringConstraints(min_length=1, max_length=60)] | None = None


class RegenerateRequest(ApiModel):
    model_config_id: UUID | None = None
    generate_chart: bool = True


class QueryAccepted(ApiModel):
    session_id: UUID
    user_message_id: UUID
    execution_id: UUID
    status: ExecutionStatus
    event_url: str


class ClarificationSubmit(ApiModel):
    content: str = Field(min_length=1, max_length=2000)


class ClarificationRequest(ApiModel):
    prompt: str
    missing_slots: list[str]
    round: int = Field(ge=1, le=2)
    max_rounds: int = Field(ge=1, le=2)


class ExecutionStepOut(ApiModel):
    type: str
    status: str
    summary: str
    started_at: datetime | None = None
    completed_at: datetime | None = None
    duration_ms: int | None = None


class ResultColumn(ApiModel):
    key: str
    label: str
    data_type: Literal["string", "integer", "decimal", "percent", "date", "datetime", "boolean"]
    unit: str | None = None


class ResultSet(ApiModel):
    columns: list[ResultColumn]
    rows: list[dict[str, Any]]
    row_count: int
    truncated: bool


class ChartSpec(ApiModel):
    type: Literal["bar", "line", "pie", "metric", "none"]
    title: str | None = None
    x_field: str | None = None
    y_fields: list[str] = Field(default_factory=list)
    name_field: str | None = None
    value_field: str | None = None
    unit: str | None = None


class ExecutionDetail(ApiModel):
    id: UUID
    request_id: str
    session_id: UUID
    user_message_id: UUID
    assistant_message_id: UUID | None = None
    question: str
    intent: IntentType | None = None
    normalized_question: str | None = None
    missing_slots: list[str] = Field(default_factory=list)
    clarification_round: int = Field(ge=0, le=2)
    clarification: ClarificationRequest | None = None
    data_source_ids: list[UUID]
    status: ExecutionStatus
    sql_validation_status: SqlValidationStatus
    steps: list[ExecutionStepOut]
    selected_objects: list[str] = Field(default_factory=list)
    sql: str | None = None
    result: ResultSet | None
    answer: str | None = None
    chart: ChartSpec | None
    follow_up_questions: list[str] = Field(default_factory=list, max_length=3)
    model_name: str | None = None
    token_usage: TokenUsage = Field(default_factory=TokenUsage)
    current_version_no: int | None = None
    duration_ms: int | None = None
    error: ErrorDetail | None
    created_at: datetime
    completed_at: datetime | None = None


class ExecutionStatusResponse(ApiModel):
    execution_id: UUID
    status: ExecutionStatus
    updated_at: datetime


class AnswerVersion(ApiModel):
    version_no: int
    execution_id: UUID
    answer: str
    sql: str | None = None
    chart: ChartSpec | None = None
    model_name: str | None = None
    duration_ms: int | None = None
    is_current: bool
    created_at: datetime
