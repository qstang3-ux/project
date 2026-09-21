import time
from datetime import UTC, datetime
from typing import Literal, cast
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.errors import AppError, ConflictError, NotFoundError
from app.core.security import decrypt_secret, encrypt_secret, mask_secret
from app.models import ApplicationConfig, ModelConfig
from app.schemas.admin import (
    ApplicationConfigOut,
    ApplicationConfigUpdate,
    ModelConfigCreate,
    ModelConfigOut,
    ModelConfigUpdate,
    ModelConnectionTestRequest,
    ModelConnectionTestResult,
)
from app.text2sql.adapters import OpenAICompatibleAdapter


def model_out(model: ModelConfig, settings: Settings) -> ModelConfigOut:
    key = (
        decrypt_secret(model.encrypted_api_key, settings.model_secret_key)
        if model.encrypted_api_key
        else None
    )
    return ModelConfigOut(
        id=model.id,
        name=model.name,
        provider="openai_compatible",
        protocol=model.protocol,
        base_url=model.base_url,
        model_name=model.model_name,
        api_key_mask=mask_secret(key),
        timeout_seconds=model.timeout_seconds,
        enabled=model.enabled,
        is_active=model.active,
        last_test_status=model.last_test_status,
        last_tested_at=model.last_tested_at,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


class ModelConfigService:
    def __init__(self, db: Session, settings: Settings) -> None:
        self.db = db
        self.settings = settings

    def list(self) -> list[ModelConfigOut]:
        return [
            model_out(item, self.settings)
            for item in self.db.scalars(select(ModelConfig).order_by(ModelConfig.created_at))
        ]

    def get(self, model_id: UUID) -> ModelConfigOut:
        model = self.db.get(ModelConfig, model_id)
        if not model:
            raise NotFoundError("模型配置不存在")
        return model_out(model, self.settings)

    def create(self, body: ModelConfigCreate) -> ModelConfigOut:
        now = datetime.now(UTC)
        model = ModelConfig(
            name=body.name,
            provider=body.provider,
            protocol=body.protocol,
            base_url=str(body.base_url).rstrip("/"),
            model_name=body.model_name,
            encrypted_api_key=encrypt_secret(body.api_key, self.settings.model_secret_key),
            timeout_seconds=body.timeout_seconds,
            enabled=body.enabled,
            active=False,
            updated_at=now,
        )
        self.db.add(model)
        self.db.commit()
        self.db.refresh(model)
        return model_out(model, self.settings)

    def update(self, model_id: UUID, body: ModelConfigUpdate) -> ModelConfigOut:
        model = self.db.get(ModelConfig, model_id)
        if not model:
            raise NotFoundError("模型配置不存在")
        values = body.model_dump(exclude_none=True)
        if "base_url" in values:
            values["base_url"] = str(values["base_url"]).rstrip("/")
        if "api_key" in values:
            values["encrypted_api_key"] = encrypt_secret(
                values.pop("api_key"), self.settings.model_secret_key
            )
        candidate_model = str(values.get("model_name", model.model_name)).lower()
        if candidate_model == "gpt-5.6-sol":
            values["protocol"] = "responses"
        for key, value in values.items():
            setattr(model, key, value)
        model.updated_at = datetime.now(UTC)
        self.db.commit()
        return model_out(model, self.settings)

    def delete(self, model_id: UUID) -> None:
        model = self.db.get(ModelConfig, model_id)
        if not model:
            return
        if model.active:
            raise ConflictError("当前启用模型不可删除")
        self.db.delete(model)
        self.db.commit()

    def activate(self, model_id: UUID) -> ModelConfigOut:
        model = self.db.get(ModelConfig, model_id)
        if not model:
            raise NotFoundError("模型配置不存在")
        if not model.enabled:
            raise ConflictError("禁用的模型不可启用")
        self.db.execute(update(ModelConfig).values(active=False))
        model.active = True
        model.updated_at = datetime.now(UTC)
        self.db.commit()
        return model_out(model, self.settings)

    def test(self, body: ModelConnectionTestRequest) -> ModelConnectionTestResult:
        if body.model_config_id:
            model = self.db.get(ModelConfig, body.model_config_id)
            if not model:
                raise NotFoundError("模型配置不存在")
            base_url = model.base_url
            model_name = model.model_name
            protocol = model.protocol
            api_key = decrypt_secret(model.encrypted_api_key or "", self.settings.model_secret_key)
        else:
            base_url = str(body.base_url).rstrip("/")
            model_name = body.model_name or ""
            protocol = body.protocol
            api_key = body.api_key or ""
        started = time.perf_counter()
        status = "success"
        success = True
        message = "连接成功"
        try:
            OpenAICompatibleAdapter(
                base_url,
                api_key,
                model_name,
                body.timeout_seconds,
                cast(Literal["responses", "chat_completions"], protocol),
            ).probe()
        except AppError as exc:
            success = False
            status = {
                "MODEL_AUTH_FAILED": "auth_failed",
                "MODEL_NOT_FOUND": "model_not_found",
                "MODEL_TIMEOUT": "timeout",
                "MODEL_INVALID_RESPONSE": "invalid_response",
            }.get(exc.code, "unavailable")
            message = exc.message
        return ModelConnectionTestResult(
            success=success,
            status=status,
            message=message,
            duration_ms=int((time.perf_counter() - started) * 1000),
        )


def config_out(config: ApplicationConfig) -> ApplicationConfigOut:
    return ApplicationConfigOut.model_validate(config)


def update_application_config(db: Session, body: ApplicationConfigUpdate) -> ApplicationConfigOut:
    config = db.get(ApplicationConfig, True)
    if not config:
        raise NotFoundError("应用配置不存在")
    if config.version != body.version:
        raise ConflictError("应用配置已被其他请求更新")
    values = body.model_dump(exclude={"version"})
    for key, value in values.items():
        setattr(config, key, value)
    config.version += 1
    config.updated_at = datetime.now(UTC)
    db.commit()
    return config_out(config)
