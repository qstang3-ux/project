from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import Field, HttpUrl, StringConstraints, model_validator

from app.schemas.common import ApiModel, PageMeta, TokenUsage
from app.schemas.qa import ExecutionStatus, ExecutionStepOut, IntentType


class ModelConfigCreate(ApiModel):
    name: str = Field(min_length=1, max_length=50)
    provider: Literal["openai_compatible"]
    protocol: Literal["responses", "chat_completions"]
    base_url: HttpUrl
    model_name: str = Field(min_length=1, max_length=100)
    api_key: str = Field(min_length=1)
    timeout_seconds: int = Field(default=30, ge=1, le=120)
    enabled: bool = True

    @model_validator(mode="after")
    def normalize_protocol(self) -> "ModelConfigCreate":
        if self.model_name.lower() == "gpt-5.6-sol":
            self.protocol = "responses"
        return self


class ModelConfigUpdate(ApiModel):
    name: str | None = Field(default=None, min_length=1, max_length=50)
    base_url: HttpUrl | None = None
    protocol: Literal["responses", "chat_completions"] | None = None
    model_name: str | None = Field(default=None, min_length=1, max_length=100)
    api_key: str | None = Field(default=None, min_length=1)
    timeout_seconds: int | None = Field(default=None, ge=1, le=120)
    enabled: bool | None = None


class ModelConfigOut(ApiModel):
    id: UUID
    name: str
    provider: Literal["openai_compatible"]
    protocol: Literal["responses", "chat_completions"]
    base_url: str
    model_name: str
    api_key_mask: str
    timeout_seconds: int
    enabled: bool
    is_active: bool
    last_test_status: Literal["success", "failed", "timeout"] | None = None
    last_tested_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class ModelConnectionTestRequest(ApiModel):
    model_config_id: UUID | None = None
    provider: Literal["openai_compatible"] | None = None
    protocol: Literal["responses", "chat_completions"] = "chat_completions"
    base_url: HttpUrl | None = None
    model_name: str | None = Field(default=None, min_length=1, max_length=100)
    api_key: str | None = None
    timeout_seconds: int = Field(default=10, ge=1, le=30)

    @model_validator(mode="after")
    def validate_source(self) -> "ModelConnectionTestRequest":
        complete_inline = self.base_url and self.model_name and self.api_key
        if bool(self.model_config_id) == bool(complete_inline):
            raise ValueError("modelConfigId 与完整未保存配置必须二选一")
        if self.model_name and self.model_name.lower() == "gpt-5.6-sol":
            self.protocol = "responses"
        return self


class ModelConnectionTestResult(ApiModel):
    success: bool
    status: Literal[
        "success",
        "auth_failed",
        "model_not_found",
        "timeout",
        "unavailable",
        "invalid_config",
        "invalid_response",
    ]
    message: str
    duration_ms: int


RecommendedQuestion = Annotated[str, StringConstraints(min_length=1, max_length=100)]


class ApplicationConfigOut(ApiModel):
    greeting_enabled: bool
    greeting_text: str
    recommended_questions: list[RecommendedQuestion]
    follow_up_enabled: bool
    frequent_questions_enabled: bool
    frequent_question_threshold: int
    model_qa_enabled: bool
    tts_enabled: bool
    stt_enabled: bool
    version: int
    updated_at: datetime


class ApplicationConfigUpdate(ApiModel):
    greeting_enabled: bool
    greeting_text: str = Field(max_length=1000)
    recommended_questions: list[RecommendedQuestion] = Field(max_length=10)
    follow_up_enabled: bool
    frequent_questions_enabled: bool
    frequent_question_threshold: int = Field(ge=1, le=1000)
    model_qa_enabled: bool
    tts_enabled: bool
    stt_enabled: bool
    version: int = Field(ge=1)


class FavoriteCreate(ApiModel):
    question: str = Field(min_length=1, max_length=2000)
    source_message_id: UUID | None = None


class FavoriteOut(ApiModel):
    id: UUID
    question: str
    source_message_id: UUID | None = None
    created_at: datetime


class FrequentQuestionOut(ApiModel):
    question: str
    count: int
    last_asked_at: datetime


FeedbackReason = Literal["sql_error", "result_error", "metric_error", "answer_error", "other"]
FeedbackStatus = Literal["pending", "processing", "resolved", "ignored"]


class FeedbackCreate(ApiModel):
    session_id: UUID
    assistant_message_id: UUID
    execution_id: UUID
    reason: FeedbackReason
    description: str | None = Field(default=None, max_length=500)


class FeedbackUpdate(ApiModel):
    status: FeedbackStatus
    resolution_note: str | None = Field(default=None, max_length=2000)
    version: int = Field(ge=1)


class FeedbackSummary(ApiModel):
    id: UUID
    user_id: str
    question: str
    reason: FeedbackReason
    description: str | None
    status: FeedbackStatus
    version: int
    created_at: datetime
    updated_at: datetime


class FeedbackDetail(FeedbackSummary):
    session_id: UUID
    assistant_message_id: UUID
    execution_id: UUID
    data_source_names: list[str]
    sql: str | None
    result_summary: str | None
    model_name: str | None
    answer: str
    resolution_note: str | None


class FeedbackListResponse(ApiModel):
    items: list[FeedbackSummary]
    page: PageMeta


class QaLogSummary(ApiModel):
    execution_id: UUID
    user_id: str
    request_id: str
    question: str
    status: ExecutionStatus
    model_name: str | None
    row_count: int | None
    duration_ms: int | None
    error_code: str | None
    created_at: datetime


class ModelCallAuditOut(ApiModel):
    provider: str
    model: str
    purpose: Literal[
        "intent_classification", "sql_generation", "sql_correction", "answer_generation"
    ]
    duration_ms: int
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    retry_count: int
    status: Literal["success", "failed", "invalid_output"]
    error_code: str | None


class QaLogDetail(QaLogSummary):
    session_id: UUID
    user_message_id: UUID
    assistant_message_id: UUID | None
    intent: IntentType | None
    normalized_question: str | None
    missing_slots: list[str]
    clarification_round: int
    data_source_names: list[str]
    selected_objects: list[str]
    generated_sql: str | None
    executed_sql: str | None
    validation_summary: str | None
    token_usage: TokenUsage
    model_calls: list[ModelCallAuditOut]
    graph_version: str | None
    graph_node_trace: list[str]
    checkpoint_status: str | None
    rag_document_ids: list[UUID]
    rag_degraded: bool
    steps: list[ExecutionStepOut]
    error_message: str | None


class QaLogListResponse(ApiModel):
    items: list[QaLogSummary]
    page: PageMeta
