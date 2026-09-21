from __future__ import annotations

import re
import time
from collections.abc import Callable
from dataclasses import asdict
from datetime import UTC, datetime
from typing import Any, Literal, NotRequired, TypedDict, TypeVar, cast
from urllib.parse import quote
from uuid import UUID, uuid4

from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.graph import END, START, StateGraph
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.errors import AppError
from app.core.security import decrypt_secret
from app.models import (
    DataSource,
    ModelConfig,
    QaAnswerVersion,
    QaExecution,
    QaExecutionStep,
    QaMessage,
)
from app.repositories.qa import compare_and_set_execution_status
from app.services.context_service import (
    resolve_context_messages,
    resolve_conversation_context_messages,
)
from app.services.execution_effects import (
    begin_execution_effect,
    complete_execution_effect,
    fail_execution_effect,
    select_effect,
)
from app.services.execution_events import append_step_event, append_terminal_event
from app.text2sql.adapters import FakeModelAdapter, ModelAdapter, OpenAICompatibleAdapter
from app.text2sql.answer import AnswerValidator
from app.text2sql.executor import (
    RECOVERABLE_ERROR_CATEGORIES,
    QueryExecutionError,
    QueryExecutor,
)
from app.text2sql.rag import (
    BgeEmbeddingProvider,
    DeterministicEmbeddingProvider,
    HybridSchemaRetriever,
)
from app.text2sql.types import (
    AnswerBundle,
    Intent,
    IntentClassification,
    ModelAnswerOutput,
    ModelSqlOutput,
    PromptContextItem,
    QueryResult,
    RetrievedKnowledgeItem,
    SchemaContext,
    ValidatedSql,
)
from app.text2sql.validator import SqlValidator

GRAPH_NODES = (
    "load_context",
    "build_memory",
    "classify_intent",
    "retrieve_knowledge",
    "generate_sql",
    "validate_sql",
    "execute_sql",
    "correct_sql",
    "summarize_result",
    "verify_answer",
    "persist_result",
    "persist_clarification",
    "persist_non_data_response",
)
TModelOutput = TypeVar("TModelOutput", IntentClassification, ModelSqlOutput, ModelAnswerOutput)
ModelEffectOutput = IntentClassification | ModelSqlOutput | ModelAnswerOutput


class AgentState(TypedDict):
    execution_id: str
    session_id: str
    request_id: str
    question: str
    normalized_question: str
    intent: str | None
    missing_slots: list[str]
    intent_confidence: float | None
    intent_reason_code: str | None
    intent_route: Literal["data_query", "clarification", "non_data", "unsafe"]
    generate_chart: bool
    original_context: list[PromptContextItem]
    conversation_context: list[PromptContextItem]
    memory: dict[str, Any]
    allowed_objects: list[str]
    rag_documents: list[str]
    rag_context: list[RetrievedKnowledgeItem]
    retrieval_scores: dict[str, float]
    rag_degraded: bool
    schema_objects: list[str]
    schema_descriptions: dict[str, str]
    model_output: dict[str, Any]
    generated_sql: str | None
    executed_sql: str | None
    validation_status: str
    validation_summary: str | None
    correction_count: int
    recoverable_error: str | None
    route: Literal["correct", "summarize"]
    result: dict[str, Any] | None
    answer_output: dict[str, Any] | None
    answer_bundle: dict[str, Any] | None
    current_node: str
    node_trace: list[str]
    cancelled: bool
    error_code: NotRequired[str | None]
    error_message: NotRequired[str | None]


class LangGraphQueryRunner:
    def __init__(
        self,
        db: Session,
        settings: Settings,
        execution: QaExecution,
        generate_chart: bool,
        query_engine: Any,
        owner_id: str,
    ) -> None:
        self.db = db
        self.settings = settings
        self.execution = execution
        self.generate_chart = generate_chart
        self.query_engine = query_engine
        self.owner_id = owner_id
        self.started_at = time.perf_counter()
        self.node_started_at: dict[str, datetime] = {}
        self.adapter = self._adapter()
        self.validator = SqlValidator(settings.sql_max_rows)
        self.executor = QueryExecutor(
            query_engine,
            settings.sql_timeout_seconds,
            settings.sql_lock_timeout_seconds,
            settings.sql_max_rows,
            settings.sql_max_response_bytes,
        )

    def run(self, resume_with_input: bool = False) -> AgentState:
        checkpoint_url = self._checkpoint_url()
        config = RunnableConfig(
            configurable={"thread_id": str(self.execution.id)},
            recursion_limit=self.settings.graph_recursion_limit,
        )
        with PostgresSaver.from_conn_string(checkpoint_url) as checkpointer:
            graph = self._build_graph(checkpointer)
            existing = checkpointer.get_tuple(config)
            self.execution.checkpoint_status = "resuming" if existing else "initialized"
            self.db.commit()
            state = graph.invoke(
                self._initial_state() if resume_with_input or not existing else None,
                config=config,
                durability="sync",
            )
        if self.execution.status != "awaiting_input":
            self.execution.checkpoint_status = "completed"
        self.db.commit()
        return cast(AgentState, state)

    def _build_graph(self, checkpointer: PostgresSaver):  # type: ignore[no-untyped-def]
        graph = StateGraph(AgentState)
        graph.add_node("load_context", self.load_context)
        graph.add_node("build_memory", self.build_memory)
        graph.add_node("classify_intent", self.classify_intent)
        graph.add_node("retrieve_knowledge", self.retrieve_knowledge)
        graph.add_node("generate_sql", self.generate_sql)
        graph.add_node("validate_sql", self.validate_sql)
        graph.add_node("execute_sql", self.execute_sql)
        graph.add_node("correct_sql", self.correct_sql)
        graph.add_node("summarize_result", self.summarize_result)
        graph.add_node("verify_answer", self.verify_answer)
        graph.add_node("persist_result", self.persist_result)
        graph.add_node("persist_clarification", self.persist_clarification)
        graph.add_node("persist_non_data_response", self.persist_non_data_response)
        graph.add_edge(START, "load_context")
        graph.add_edge("load_context", "build_memory")
        graph.add_edge("build_memory", "classify_intent")
        graph.add_conditional_edges(
            "classify_intent",
            lambda state: state["intent_route"],
            {
                "data_query": "retrieve_knowledge",
                "clarification": "persist_clarification",
                "non_data": "persist_non_data_response",
                "unsafe": "persist_non_data_response",
            },
        )
        graph.add_edge("retrieve_knowledge", "generate_sql")
        graph.add_edge("generate_sql", "validate_sql")
        graph.add_edge("validate_sql", "execute_sql")
        graph.add_conditional_edges(
            "execute_sql",
            lambda state: state["route"],
            {"correct": "correct_sql", "summarize": "summarize_result"},
        )
        graph.add_edge("correct_sql", "validate_sql")
        graph.add_edge("summarize_result", "verify_answer")
        graph.add_edge("verify_answer", "persist_result")
        graph.add_edge("persist_result", END)
        graph.add_edge("persist_clarification", END)
        graph.add_edge("persist_non_data_response", END)
        return graph.compile(checkpointer=checkpointer, name=self.settings.graph_version)

    def load_context(self, state: AgentState) -> dict[str, Any]:
        self._enter_node(state, "load_context")
        current = self.db.get(QaMessage, self.execution.user_message_id)
        context, context_ids, provenance = resolve_context_messages(self.db, self.execution)
        conversation_context, conversation_provenance = resolve_conversation_context_messages(
            self.db, self.execution
        )
        current_provenance: list[dict[str, Any]] = [
            {
                "source": "current_user",
                "role": "user",
                "messageId": str(self.execution.user_message_id),
                "sessionId": str(self.execution.session_id),
                "executionId": str(self.execution.id),
                "includedInPrompt": True,
            }
        ]
        if current and current.source_message_id:
            current_provenance.append(
                {
                    "source": "resubmit_source",
                    "messageId": str(current.source_message_id),
                    "includedInPrompt": False,
                }
            )
        if self.execution.regenerated_from_execution_id:
            current_provenance.append(
                {
                    "source": "regenerated_execution",
                    "executionId": str(self.execution.regenerated_from_execution_id),
                    "includedInPrompt": False,
                }
            )
        clarification_provenance = [
            item
            for item in self.execution.context_provenance
            if item.get("source") == "clarification"
            and item.get("executionId") == str(self.execution.id)
        ]
        self.execution.context_message_ids = [str(item) for item in context_ids]
        resolved_provenance: list[dict[str, Any]] = []
        for item in [
            *current_provenance,
            *provenance,
            *conversation_provenance,
            *clarification_provenance,
        ]:
            if item not in resolved_provenance:
                resolved_provenance.append(item)
        self.execution.context_provenance = resolved_provenance
        self.db.commit()
        return self._node_update(
            state,
            "load_context",
            original_context=context,
            conversation_context=conversation_context,
        )

    def build_memory(self, state: AgentState) -> dict[str, Any]:
        self._enter_node(state, "build_memory")
        source = "\n".join(
            [
                *[
                    str(item["content"])
                    for item in state["original_context"]
                    if item["channel"] == "history"
                ],
                state["question"],
            ]
        )
        years = sorted({int(item) for item in re.findall(r"20\d{2}", source)})
        months = sorted({int(item) for item in re.findall(r"(1[0-2]|[1-9])月", source)})
        metrics = [
            name
            for name in ("商业目标", "商解目标", "完成率", "收入", "回款", "应收", "风险")
            if name in source
        ]
        memory = {"years": years[-2:], "months": months, "metrics": metrics[-4:]}
        return self._node_update(state, "build_memory", memory=memory)

    def classify_intent(self, state: AgentState) -> dict[str, Any]:
        self._enter_node(state, "classify_intent")
        output = self._call_model(
            "intent_classification",
            self._effect_key("model:intent_classification"),
            lambda: self.adapter.classify_intent(
                state["question"], self._classification_context(state)
            ),
        )
        route: Literal["data_query", "clarification", "non_data", "unsafe"]
        if output.intent == "data_query":
            route = "data_query"
        elif output.intent == "clarification" or output.missing_slots:
            route = "clarification"
        elif output.intent == "unsafe":
            route = "unsafe"
        else:
            route = "non_data"
        self.execution.intent = output.intent
        self.execution.normalized_question = output.normalized_question
        self.execution.missing_slots = list(output.missing_slots)
        self.execution.intent_confidence = output.confidence
        self.execution.intent_reason_code = output.reason_code
        self.execution.model_name = output.model_name
        self._step(
            self._effect_key("step:intent_classification"),
            "intent_classification",
            f"意图分类完成：{output.intent}",
        )
        return self._node_update(
            state,
            "classify_intent",
            normalized_question=output.normalized_question,
            intent=output.intent,
            missing_slots=list(output.missing_slots),
            intent_confidence=output.confidence,
            intent_reason_code=output.reason_code,
            intent_route=route,
        )

    def retrieve_knowledge(self, state: AgentState) -> dict[str, Any]:
        self._enter_node(state, "retrieve_knowledge")
        sources = list(
            self.db.scalars(
                select(DataSource).where(
                    DataSource.id.in_([UUID(value) for value in self.execution.data_source_ids])
                )
            )
        )
        allowed = sorted({item for source in sources for item in source.allowed_objects})
        provider = (
            DeterministicEmbeddingProvider()
            if self.settings.app_env == "test"
            else BgeEmbeddingProvider(self.settings.rag_embedding_model)
        )
        schema = HybridSchemaRetriever(self.db, self.settings, provider).retrieve(
            state["question"], allowed, [source.id for source in sources]
        )
        self.execution.selected_objects = list(schema.objects)
        self.execution.rag_document_ids = list(schema.rag_document_ids)
        self.execution.rag_degraded = schema.degraded
        self._append_context_provenance(
            *[
                {
                    "source": "rag",
                    "documentId": item["documentId"],
                    "stableKey": item["stableKey"],
                    "knowledgeType": item["knowledgeType"],
                    "score": schema.retrieval_scores.get(item["stableKey"]),
                    "includedInPrompt": True,
                }
                for item in schema.retrieved_knowledge
            ]
        )
        self._step(
            self._effect_key("step:schema_selection"),
            "schema_selection",
            f"混合召回 {len(schema.rag_document_ids)} 条知识，选择 {len(schema.objects)} 个对象",
        )
        return self._node_update(
            state,
            "retrieve_knowledge",
            allowed_objects=allowed,
            rag_documents=list(schema.rag_document_ids),
            rag_context=list(schema.retrieved_knowledge),
            retrieval_scores=schema.retrieval_scores,
            rag_degraded=schema.degraded,
            schema_objects=list(schema.objects),
            schema_descriptions=schema.descriptions,
        )

    def generate_sql(self, state: AgentState) -> dict[str, Any]:
        self._enter_node(state, "generate_sql")
        schema = self._schema(state)
        output = self._call_model(
            "sql_generation",
            self._effect_key("model:sql_generation"),
            lambda: self.adapter.generate_sql(
                state["question"], schema, self._model_context(state)
            ),
        )
        self.execution.generated_sql = output.sql
        self.execution.selected_objects = list(output.selected_objects)
        self.execution.model_name = output.model_name
        self._step(
            self._effect_key("step:sql_generation"),
            "sql_generation",
            "模型已生成结构化候选 SQL",
        )
        if output.sql is None:
            message = (
                "问题存在歧义，请明确指标或时间范围"
                if output.intent == "clarification"
                else "当前数据源无法回答该问题"
            )
            raise AppError("SQL_GENERATION_FAILED", message, 422)
        return self._node_update(
            state,
            "generate_sql",
            model_output=asdict(output),
            generated_sql=output.sql,
        )

    def validate_sql(self, state: AgentState) -> dict[str, Any]:
        self._enter_node(state, "validate_sql")
        candidate = state["generated_sql"]
        if candidate is None:
            raise AppError("SQL_GENERATION_FAILED", "模型未生成 SQL", 422)
        selected = set(state["model_output"].get("selected_objects", ()))
        recalled = set(state["schema_objects"])
        permitted = set(state["allowed_objects"]) & recalled & selected
        if not permitted:
            raise AppError("SQL_VALIDATION_FAILED", "候选 SQL 未使用本次召回的数据对象", 422)
        validated = self.validator.validate(candidate, permitted)
        summary = (
            f"一次纠错后通过 SQL 安全策略 {validated.rule_version}"
            if state["correction_count"]
            else f"通过 SQL 安全策略 {validated.rule_version}"
        )
        self.execution.executed_sql = validated.sql
        self.execution.validation_summary = summary
        self._step(
            self._effect_key("step:sql_validation", state["correction_count"]),
            "sql_validation",
            summary,
        )
        return self._node_update(
            state,
            "validate_sql",
            executed_sql=validated.sql,
            validation_status="passed",
            validation_summary=summary,
        )

    def execute_sql(self, state: AgentState) -> dict[str, Any]:
        self._enter_node(state, "execute_sql")
        validated = ValidatedSql(
            state["generated_sql"] or "",
            state["executed_sql"] or "",
            tuple(state["schema_objects"]),
        )
        try:
            result = self._execute_query_effect(state, validated)
        except QueryExecutionError as exc:
            if (
                exc.recoverable
                and exc.category in RECOVERABLE_ERROR_CATEGORIES
                and state["correction_count"] == 0
            ):
                self._append_context_provenance(
                    {
                        "source": "database_error_category",
                        "category": exc.category,
                        "rawErrorIncluded": False,
                        "includedInPrompt": True,
                    }
                )
                self.db.commit()
                return self._node_update(
                    state,
                    "execute_sql",
                    route="correct",
                    recoverable_error=exc.category,
                )
            raise
        return self._node_update(
            state,
            "execute_sql",
            route="summarize",
            recoverable_error=None,
            result=self._result_dict(result),
        )

    def correct_sql(self, state: AgentState) -> dict[str, Any]:
        self._enter_node(state, "correct_sql")
        if state["correction_count"] >= 1:
            raise AppError("QUERY_FAILED", "查询执行失败", 422)
        output = self._call_model(
            "sql_correction",
            self._effect_key("model:sql_correction", 1),
            lambda: self.adapter.generate_sql(
                state["question"],
                self._schema(state),
                [
                    PromptContextItem(
                        channel="generated_sql",
                        source="validator_approved_candidate",
                        role="data",
                        trust="untrusted",
                        content=state["executed_sql"],
                        provenance={"executionId": str(self.execution.id)},
                    ),
                    PromptContextItem(
                        channel="database_error",
                        source="sqlstate_category",
                        role="data",
                        trust="untrusted",
                        content=state["recoverable_error"],
                        provenance={"rawErrorIncluded": False},
                    ),
                ],
            ),
        )
        if output.sql is None:
            raise AppError("QUERY_FAILED", "查询执行失败", 422)
        self.execution.generated_sql = output.sql
        return self._node_update(
            state,
            "correct_sql",
            generated_sql=output.sql,
            correction_count=1,
            model_output=asdict(output),
        )

    def summarize_result(self, state: AgentState) -> dict[str, Any]:
        self._enter_node(state, "summarize_result")
        result = self._query_result(state)
        output: ModelAnswerOutput | None = None
        for attempt in range(2):
            output = self._call_model(
                "answer_generation",
                self._effect_key("model:answer_generation", attempt),
                lambda: self.adapter.generate_answer(
                    state["question"], result, state["generate_chart"]
                ),
            )
            try:
                AnswerValidator().validate(
                    output, state["question"], result, state["generate_chart"]
                )
            except AppError as exc:
                self._mark_last_model_call_invalid()
                if exc.code == "MODEL_INVALID_RESPONSE" and attempt == 0:
                    continue
                raise
            break
        if output is None:
            raise AppError("MODEL_INVALID_RESPONSE", "模型未生成答案", 502)
        return self._node_update(state, "summarize_result", answer_output=asdict(output))

    def verify_answer(self, state: AgentState) -> dict[str, Any]:
        self._enter_node(state, "verify_answer")
        payload = state["answer_output"]
        if payload is None:
            raise AppError("MODEL_INVALID_RESPONSE", "模型未生成答案", 502)
        output = ModelAnswerOutput(
            payload["answer"],
            payload["chart"],
            payload["follow_up_questions"],
            payload["model_name"],
            payload["prompt_tokens"],
            payload["completion_tokens"],
        )
        try:
            bundle = AnswerValidator().validate(
                output, state["question"], self._query_result(state), state["generate_chart"]
            )
        except AppError:
            self._mark_last_model_call_invalid()
            raise
        return self._node_update(state, "verify_answer", answer_bundle=asdict(bundle))

    def persist_result(self, state: AgentState) -> dict[str, Any]:
        self._enter_node(state, "persist_result")
        effect = begin_execution_effect(
            self.db,
            execution_id=self.execution.id,
            effect_key=self._effect_key("persist:result"),
            node_name="persist_result",
            attempt=0,
            owner_id=self.owner_id,
        )
        if effect.status == "completed":
            return self._node_update(state, "persist_result")
        payload = state["answer_bundle"]
        if payload is None:
            raise AppError("MODEL_INVALID_RESPONSE", "答案核验结果不存在", 502)
        bundle = AnswerBundle(payload["answer"], payload["chart"], payload["follow_up_questions"])
        current_version = (
            self.db.scalar(
                select(QaAnswerVersion).where(
                    QaAnswerVersion.execution_id == self.execution.id,
                    QaAnswerVersion.assistant_message_id == self.execution.assistant_message_id,
                )
            )
            if self.execution.assistant_message_id
            else None
        )
        if self.execution.assistant_message_id is None or current_version is None:
            assistant = QaMessage(
                session_id=self.execution.session_id,
                role="assistant",
                content=bundle.answer,
                execution_id=self.execution.id,
            )
            self.db.add(assistant)
            self.db.flush()
            self.db.add(
                QaAnswerVersion(
                    assistant_message_id=assistant.id,
                    execution_id=self.execution.id,
                    version_no=1,
                    is_current=True,
                )
            )
            self.execution.assistant_message_id = assistant.id
        self.execution.answer = bundle.answer
        self.execution.chart_json = bundle.chart
        self.execution.follow_up_questions = bundle.follow_up_questions
        self._step(
            self._effect_key("step:answer_generation"),
            "answer_generation",
            "回答、图表建议和推荐追问已生成",
            commit=False,
        )
        self.execution.clarification_json = None
        self.execution.missing_slots = []
        complete_execution_effect(
            effect,
            {
                "assistantMessageId": str(self.execution.assistant_message_id),
                "status": "completed",
            },
        )
        self._commit_status("completed", completed_at=datetime.now(UTC))
        return self._node_update(state, "persist_result")

    def persist_clarification(self, state: AgentState) -> dict[str, Any]:
        self._enter_node(state, "persist_clarification")
        next_round = self.execution.clarification_round + 1
        if next_round > self.settings.clarification_max_rounds:
            raise AppError("CLARIFICATION_LIMIT_REACHED", "当前执行已达到澄清轮次上限", 409)
        missing = state["missing_slots"] or ["analysis_scope"]
        prompt = self._clarification_prompt(missing)
        effect = begin_execution_effect(
            self.db,
            execution_id=self.execution.id,
            effect_key=self._effect_key("persist:clarification", next_round),
            node_name="persist_clarification",
            attempt=next_round,
            owner_id=self.owner_id,
        )
        if effect.status == "completed":
            return self._node_update(state, "persist_clarification")
        assistant = QaMessage(
            session_id=self.execution.session_id,
            role="assistant",
            content=prompt,
            execution_id=self.execution.id,
        )
        self.db.add(assistant)
        self.db.flush()
        self.execution.assistant_message_id = assistant.id
        self.execution.answer = prompt
        self.execution.clarification_round = next_round
        self.execution.clarification_json = {
            "prompt": prompt,
            "missingSlots": missing,
            "round": next_round,
            "maxRounds": self.settings.clarification_max_rounds,
        }
        self.execution.checkpoint_status = "awaiting_input"
        self.execution.completed_at = None
        self._step(
            self._effect_key("step:clarification", next_round),
            "clarification_required",
            f"需要补充信息，第 {next_round} 轮",
            commit=False,
        )
        complete_execution_effect(
            effect,
            {"assistantMessageId": str(assistant.id), "round": next_round},
        )
        self._commit_status(
            "awaiting_input",
            checkpoint_status="awaiting_input",
            completed_at=None,
        )
        return self._node_update(state, "persist_clarification")

    def persist_non_data_response(self, state: AgentState) -> dict[str, Any]:
        self._enter_node(state, "persist_non_data_response")
        intent = state["intent"] or "out_of_scope"
        if intent in ("chat", "business_definition", "product_help"):
            output = self._call_model(
                "answer_generation",
                self._effect_key(f"model:conversation_answer:{intent}"),
                lambda: self.adapter.generate_non_data_answer(
                    state["normalized_question"],
                    cast(Intent, intent),
                    state["conversation_context"],
                ),
            )
            answer = output.answer
        else:
            answer = self._non_data_answer(intent)
        effect = begin_execution_effect(
            self.db,
            execution_id=self.execution.id,
            effect_key=self._effect_key(f"persist:non_data:{intent}"),
            node_name="persist_non_data_response",
            attempt=0,
            owner_id=self.owner_id,
        )
        if effect.status == "completed":
            return self._node_update(state, "persist_non_data_response")
        assistant = QaMessage(
            session_id=self.execution.session_id,
            role="assistant",
            content=answer,
            execution_id=self.execution.id,
        )
        self.db.add(assistant)
        self.db.flush()
        self.execution.assistant_message_id = assistant.id
        self.execution.answer = answer
        self.execution.chart_json = {"type": "none", "yFields": []}
        self.execution.follow_up_questions = []
        completed_at = datetime.now(UTC)
        self.execution.completed_at = completed_at
        if intent == "unsafe":
            self.execution.error_code = "UNSAFE_REQUEST"
            self.execution.error_message = answer
            target_status = "rejected"
        else:
            self.db.add(
                QaAnswerVersion(
                    assistant_message_id=assistant.id,
                    execution_id=self.execution.id,
                    version_no=1,
                    is_current=True,
                )
            )
            target_status = "completed"
        self._step(
            self._effect_key(f"step:answer_non_data:{intent}"),
            "answer_generation",
            f"已按 {intent} 意图生成非查询响应",
            commit=False,
        )
        terminal_values: dict[str, Any] = {"completed_at": completed_at}
        if target_status == "rejected":
            terminal_values.update(error_code="UNSAFE_REQUEST", error_message=answer)
        complete_execution_effect(
            effect,
            {"assistantMessageId": str(assistant.id), "status": target_status},
        )
        self._commit_status(target_status, **terminal_values)
        return self._node_update(state, "persist_non_data_response")

    def _initial_state(self) -> AgentState:
        question = self._effective_question()
        return AgentState(
            execution_id=str(self.execution.id),
            session_id=str(self.execution.session_id),
            request_id=self.execution.request_id,
            question=question,
            normalized_question=self.execution.normalized_question or question,
            intent=None,
            missing_slots=[],
            intent_confidence=None,
            intent_reason_code=None,
            intent_route="data_query",
            generate_chart=self.generate_chart,
            original_context=[],
            conversation_context=[],
            memory={},
            allowed_objects=[],
            rag_documents=[],
            rag_context=[],
            retrieval_scores={},
            rag_degraded=False,
            schema_objects=[],
            schema_descriptions={},
            model_output={},
            generated_sql=None,
            executed_sql=None,
            validation_status="not_started",
            validation_summary=None,
            correction_count=0,
            recoverable_error=None,
            route="summarize",
            result=None,
            answer_output=None,
            answer_bundle=None,
            current_node="",
            node_trace=[],
            cancelled=False,
        )

    def _enter_node(self, state: AgentState, node: str) -> None:
        self.db.refresh(self.execution)
        if self.execution.status == "cancelled":
            raise AppError("EXECUTION_CANCELLED", "执行已取消", 409)
        if self.execution.status != "running" or self.execution.lease_owner != self.owner_id:
            raise AppError("EXECUTION_LEASE_LOST", "执行租约已失效", 409)
        if time.perf_counter() - self.started_at > self.settings.execution_deadline_seconds:
            raise AppError("EXECUTION_DEADLINE_EXCEEDED", "问数执行超过时间限制", 504)
        self.node_started_at[node] = datetime.now(UTC)
        self.execution.graph_node_trace = [*state["node_trace"], node]
        self.execution.checkpoint_status = f"running:{node}"
        self.db.commit()

    @staticmethod
    def _node_update(state: AgentState, node: str, **updates: Any) -> dict[str, Any]:
        return {"current_node": node, "node_trace": [*state["node_trace"], node], **updates}

    def _schema(self, state: AgentState) -> SchemaContext:
        return SchemaContext(
            tuple(state["schema_objects"]),
            state["schema_descriptions"],
            rag_document_ids=tuple(state["rag_documents"]),
            retrieval_scores=state["retrieval_scores"],
            degraded=state["rag_degraded"],
            retrieved_knowledge=tuple(state["rag_context"]),
        )

    @staticmethod
    def _model_context(state: AgentState) -> list[PromptContextItem]:
        memory = PromptContextItem(
            channel="structured_memory",
            source="derived_memory",
            role="data",
            trust="untrusted",
            content=state["memory"],
            provenance={"derivedFrom": "current_user_and_selected_history"},
        )
        return [*state["original_context"], memory]

    @staticmethod
    def _classification_context(state: AgentState) -> list[PromptContextItem]:
        memory = PromptContextItem(
            channel="structured_memory",
            source="derived_memory",
            role="data",
            trust="untrusted",
            content=state["memory"],
            provenance={"derivedFrom": "current_user_and_sql_eligible_history"},
        )
        return [*state["conversation_context"], memory]

    def _append_context_provenance(self, *items: dict[str, Any]) -> None:
        existing = list(self.execution.context_provenance)
        for item in items:
            if item not in existing:
                existing.append(item)
        self.execution.context_provenance = existing

    @staticmethod
    def _result_dict(result: QueryResult) -> dict[str, Any]:
        return {
            "columns": result.columns,
            "rows": result.rows,
            "rowCount": result.row_count,
            "truncated": result.truncated,
            "responseBytes": result.response_bytes,
        }

    @staticmethod
    def _query_result(state: AgentState) -> QueryResult:
        payload = state["result"]
        if payload is None:
            raise AppError("QUERY_FAILED", "查询结果不存在", 500)
        return QueryResult(
            payload["columns"],
            payload["rows"],
            payload["rowCount"],
            payload["truncated"],
            payload.get("responseBytes", 0),
        )

    def _execute_query_effect(self, state: AgentState, validated: ValidatedSql) -> QueryResult:
        attempt = state["correction_count"]
        effect = begin_execution_effect(
            self.db,
            execution_id=self.execution.id,
            effect_key=self._effect_key("sql:execute", attempt),
            node_name="execute_sql",
            attempt=attempt,
            owner_id=self.owner_id,
        )
        payload = effect.payload_json or {}
        if effect.status == "completed":
            return self._query_result_from_payload(payload["result"])
        if effect.status == "failed":
            raise QueryExecutionError(
                str(payload.get("code", "QUERY_FAILED")),
                str(payload.get("message", "查询执行失败")),
                int(payload.get("statusCode", 422)),
                recoverable=bool(payload.get("recoverable", False)),
                category=str(payload.get("category", "unknown_error")),
            )
        try:
            result = self.executor.execute(validated)
        except QueryExecutionError as exc:
            self._ensure_active_lease()
            fail_execution_effect(
                effect,
                error_code=exc.code,
                payload={
                    "code": exc.code,
                    "message": exc.message,
                    "statusCode": exc.status_code,
                    "recoverable": exc.recoverable,
                    "category": exc.category,
                },
            )
            self.db.commit()
            raise
        self._ensure_active_lease()
        result_payload = self._result_dict(result)
        self.execution.result_json = result_payload
        self.execution.row_count = result.row_count
        self._step(
            self._effect_key("step:query_execution", attempt),
            "query_execution",
            f"查询完成，返回 {result.row_count} 行",
            commit=False,
        )
        complete_execution_effect(effect, {"result": result_payload})
        self.db.commit()
        return result

    @staticmethod
    def _query_result_from_payload(payload: object) -> QueryResult:
        if not isinstance(payload, dict):
            raise AppError("INTERNAL_ERROR", "查询效果记录无效", 500)
        return QueryResult(
            list(payload.get("columns", [])),
            list(payload.get("rows", [])),
            int(payload.get("rowCount", 0)),
            bool(payload.get("truncated", False)),
            int(payload.get("responseBytes", 0)),
        )

    def _adapter(self) -> ModelAdapter:
        if self.settings.default_model_config == "fake":
            if self.settings.app_env not in ("local", "test"):
                raise AppError("FAKE_MODEL_FORBIDDEN", "当前环境禁止使用 Fake 模型", 503)
            return FakeModelAdapter()
        model = self.db.scalar(
            select(ModelConfig).where(ModelConfig.active.is_(True), ModelConfig.enabled.is_(True))
        )
        if model:
            self.execution.model_config_id = model.id
            key = decrypt_secret(model.encrypted_api_key or "", self.settings.model_secret_key)
            return OpenAICompatibleAdapter(
                model.base_url,
                key,
                model.model_name,
                model.timeout_seconds,
                cast(Literal["responses", "chat_completions"], model.protocol),
                self.settings.model_http_max_attempts_per_call,
            )
        runtime_key = self.settings.real_model_api_key
        if (
            self.settings.real_model_base_url
            and runtime_key is not None
            and runtime_key.get_secret_value()
            and self.settings.real_model_name
        ):
            return OpenAICompatibleAdapter(
                self.settings.real_model_base_url,
                runtime_key.get_secret_value(),
                self.settings.real_model_name,
                self.settings.real_model_timeout_seconds,
                self.settings.real_model_protocol,
                self.settings.model_http_max_attempts_per_call,
            )
        raise AppError("MODEL_NOT_CONFIGURED", "未配置可用真实模型", 409)

    def _call_model(
        self,
        purpose: str,
        effect_key: str,
        call: Callable[[], TModelOutput],
    ) -> TModelOutput:
        existing_effect = self.db.scalar(
            select_effect(execution_id=self.execution.id, effect_key=effect_key)
        )
        if existing_effect is not None:
            payload = existing_effect.payload_json or {}
            if existing_effect.status == "completed":
                return cast(
                    TModelOutput,
                    self._restore_model_output(purpose, payload.get("output")),
                )
            if existing_effect.status == "failed":
                raise AppError(
                    str(payload.get("code", existing_effect.error_code or "MODEL_UNAVAILABLE")),
                    str(payload.get("message", "模型调用失败")),
                    int(payload.get("statusCode", 502)),
                )
        else:
            if len(self.execution.model_call_audit) >= self.settings.model_call_budget:
                raise AppError("MODEL_BUDGET_EXCEEDED", "本次执行的模型调用预算已用尽", 429)
            if isinstance(self.adapter, OpenAICompatibleAdapter):
                used_attempts = sum(
                    int(item.get("retryCount", 0)) + 1 for item in self.execution.model_call_audit
                )
                remaining_attempts = self.settings.model_http_attempt_budget - used_attempts
                if remaining_attempts <= 0:
                    raise AppError(
                        "MODEL_BUDGET_EXCEEDED",
                        "本次执行的模型 HTTP 尝试预算已用尽",
                        429,
                    )
                self.adapter.max_attempts = min(
                    self.settings.model_http_max_attempts_per_call,
                    remaining_attempts,
                )
        effect = begin_execution_effect(
            self.db,
            execution_id=self.execution.id,
            effect_key=effect_key,
            node_name=purpose,
            attempt=self._effect_attempt(effect_key),
            owner_id=self.owner_id,
        )
        payload = effect.payload_json or {}
        if effect.status == "completed":
            return cast(TModelOutput, self._restore_model_output(purpose, payload.get("output")))
        if effect.status == "failed":
            raise AppError(
                str(payload.get("code", effect.error_code or "MODEL_UNAVAILABLE")),
                str(payload.get("message", "模型调用失败")),
                int(payload.get("statusCode", 502)),
            )
        started = time.perf_counter()
        try:
            output = call()
        except AppError as exc:
            self._ensure_active_lease()
            self._record_model_call(effect_key, purpose, started, 0, 0, "failed", exc.code)
            fail_execution_effect(
                effect,
                error_code=exc.code,
                payload={
                    "code": exc.code,
                    "message": exc.message,
                    "statusCode": exc.status_code,
                },
            )
            self.db.commit()
            raise
        self._ensure_active_lease()
        self._record_model_call(
            effect_key,
            purpose,
            started,
            output.prompt_tokens,
            output.completion_tokens,
            "success",
            None,
        )
        complete_execution_effect(effect, {"output": asdict(output)})
        self.db.commit()
        return output

    def _record_model_call(
        self,
        effect_key: str,
        purpose: str,
        started: float,
        prompt_tokens: int,
        completion_tokens: int,
        status: str,
        error_code: str | None,
    ) -> None:
        entry = {
            "effectKey": effect_key,
            "provider": self.adapter.provider_name,
            "model": self.adapter.model_name,
            "purpose": purpose,
            "durationMs": int((time.perf_counter() - started) * 1000),
            "promptTokens": prompt_tokens,
            "completionTokens": completion_tokens,
            "totalTokens": prompt_tokens + completion_tokens,
            "retryCount": self.adapter.last_retry_count,
            "status": status,
            "errorCode": error_code,
        }
        if any(item.get("effectKey") == effect_key for item in self.execution.model_call_audit):
            return
        self.execution.model_call_audit = [*self.execution.model_call_audit, entry]
        usage = self.execution.token_usage or {}
        self.execution.token_usage = {
            "promptTokens": int(usage.get("promptTokens", 0)) + prompt_tokens,
            "completionTokens": int(usage.get("completionTokens", 0)) + completion_tokens,
            "totalTokens": int(usage.get("totalTokens", 0)) + prompt_tokens + completion_tokens,
        }

    def _mark_last_model_call_invalid(self) -> None:
        calls = list(self.execution.model_call_audit)
        if calls:
            calls[-1] = {
                **calls[-1],
                "status": "invalid_output",
                "errorCode": "MODEL_INVALID_RESPONSE",
            }
            self.execution.model_call_audit = calls
            self.db.commit()

    def _step(
        self,
        effect_key: str,
        step_type: str,
        summary: str,
        *,
        commit: bool = True,
    ) -> None:
        now = datetime.now(UTC)
        node_by_step = {
            "intent_classification": "classify_intent",
            "schema_selection": "retrieve_knowledge",
            "sql_generation": "generate_sql",
            "sql_validation": "validate_sql",
            "query_execution": "execute_sql",
            "answer_generation": "summarize_result",
            "clarification_required": "persist_clarification",
        }
        node = node_by_step.get(step_type)
        started_at = self.node_started_at.get(node, now) if node else now
        inserted_step_id = self.db.scalar(
            insert(QaExecutionStep)
            .values(
                id=uuid4(),
                execution_id=self.execution.id,
                effect_key=effect_key,
                step_type=step_type,
                status="completed",
                summary=summary,
                started_at=started_at,
                completed_at=now,
            )
            .on_conflict_do_nothing(
                index_elements=[QaExecutionStep.execution_id, QaExecutionStep.effect_key]
            )
            .returning(QaExecutionStep.id)
        )
        if inserted_step_id is not None:
            append_step_event(
                self.db,
                self.execution,
                effect_key=effect_key,
                step_type=step_type,
                summary=summary,
                created_at=now,
                owner_id=self.owner_id,
            )
        if commit:
            self.db.commit()

    def _commit_status(self, target_status: str, **values: object) -> None:
        values.setdefault("lease_owner", None)
        values.setdefault("lease_expires_at", None)
        values.setdefault("heartbeat_at", None)
        with self.db.no_autoflush:
            transitioned = compare_and_set_execution_status(
                self.db,
                self.execution.id,
                ("running",),
                target_status,
                expected_lease_owner=self.owner_id,
                **values,
            )
        if not transitioned:
            self.db.rollback()
            current_status = self.db.scalar(
                select(QaExecution.status).where(QaExecution.id == self.execution.id)
            )
            if current_status == "cancelled":
                raise AppError("EXECUTION_CANCELLED", "执行已取消", 409)
            raise AppError("EXECUTION_LEASE_LOST", "执行租约已失效", 409)
        self.execution.status = target_status
        for key, value in values.items():
            setattr(self.execution, key, value)
        if target_status in ("completed", "failed", "cancelled", "rejected"):
            completed_at = self.execution.completed_at or datetime.now(UTC)
            append_terminal_event(
                self.db,
                self.execution,
                status=target_status,
                created_at=completed_at,
            )
        self.db.commit()

    def _ensure_active_lease(self) -> None:
        self.db.refresh(self.execution)
        if self.execution.status == "cancelled":
            raise AppError("EXECUTION_CANCELLED", "执行已取消", 409)
        if self.execution.status != "running" or self.execution.lease_owner != self.owner_id:
            raise AppError("EXECUTION_LEASE_LOST", "执行租约已失效", 409)

    def _effect_key(self, name: str, attempt: int = 0) -> str:
        return f"{name}:round:{self.execution.clarification_round}:attempt:{attempt}"

    @staticmethod
    def _effect_attempt(effect_key: str) -> int:
        return int(effect_key.rsplit(":", 1)[-1])

    @staticmethod
    def _restore_model_output(purpose: str, payload: object) -> ModelEffectOutput:
        if not isinstance(payload, dict):
            raise AppError("INTERNAL_ERROR", "模型效果记录无效", 500)
        if purpose == "intent_classification":
            return IntentClassification(
                cast(Any, payload["intent"]),
                str(payload["normalized_question"]),
                tuple(payload["missing_slots"]),
                float(payload["confidence"]),
                str(payload["reason_code"]),
                str(payload["model_name"]),
                int(payload.get("prompt_tokens", 0)),
                int(payload.get("completion_tokens", 0)),
            )
        if purpose in ("sql_generation", "sql_correction"):
            return ModelSqlOutput(
                str(payload["intent"]),
                tuple(payload["assumptions"]),
                str(payload["sql"]) if payload.get("sql") is not None else None,
                tuple(payload["selected_objects"]),
                str(payload["model_name"]),
                int(payload.get("prompt_tokens", 0)),
                int(payload.get("completion_tokens", 0)),
            )
        return ModelAnswerOutput(
            str(payload["answer"]),
            dict(payload["chart"]),
            list(payload["follow_up_questions"]),
            str(payload["model_name"]),
            int(payload.get("prompt_tokens", 0)),
            int(payload.get("completion_tokens", 0)),
        )

    def _checkpoint_url(self) -> str:
        url = self.settings.checkpoint_database_url
        separator = "&" if "?" in url else "?"
        return f"{url}{separator}options={quote('-c search_path=app', safe='')}"

    def _effective_question(self) -> str:
        supplements = [
            str(item.get("content", "")).strip()
            for item in self.execution.clarification_history
            if str(item.get("content", "")).strip()
        ]
        if not supplements:
            return self.execution.question
        return "\n".join([self.execution.question, *[f"用户补充：{item}" for item in supplements]])

    @staticmethod
    def _clarification_prompt(missing_slots: list[str]) -> str:
        labels = {
            "metric": "指标口径（如收入额、合同额或完成率）",
            "dimension": "分析维度（如经营单元、行业或产品线）",
            "entity": "具体对象",
            "time_range": "时间范围",
            "comparison_basis": "比较基准",
            "analysis_scope": "要分析的指标、对象或时间范围",
        }
        items = "、".join(labels.get(item, item) for item in missing_slots)
        return f"为了准确回答，请补充{items}。"

    @staticmethod
    def _non_data_answer(intent: str) -> str:
        if intent == "unsafe":
            return "该请求涉及写操作、敏感配置或越权访问，系统只允许安全的经营数据只读查询。"
        return "这个问题不属于当前经营数据与产品帮助范围。你可以改问经营目标、收入、合同、回款、应收或项目风险。"
