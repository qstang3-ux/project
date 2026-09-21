from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Path, Query, Response
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.database import get_session
from app.models import ApplicationConfig
from app.schemas.admin import (
    ApplicationConfigOut,
    ApplicationConfigUpdate,
    FavoriteCreate,
    FavoriteOut,
    FeedbackCreate,
    FeedbackDetail,
    FeedbackListResponse,
    FeedbackUpdate,
    FrequentQuestionOut,
    ModelConfigCreate,
    ModelConfigOut,
    ModelConfigUpdate,
    ModelConnectionTestRequest,
    ModelConnectionTestResult,
    QaLogDetail,
    QaLogListResponse,
)
from app.services.admin_service import ModelConfigService, config_out, update_application_config
from app.services.support_service import SupportService

router = APIRouter(prefix="/api/v1")


@router.get("/model-configs", response_model=list[ModelConfigOut])
def list_models(
    db: Session = Depends(get_session), settings: Settings = Depends(get_settings)
) -> list[ModelConfigOut]:
    return ModelConfigService(db, settings).list()


@router.post("/model-configs", response_model=ModelConfigOut, status_code=201)
def create_model(
    body: ModelConfigCreate,
    db: Session = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> ModelConfigOut:
    return ModelConfigService(db, settings).create(body)


@router.post("/model-configs/test", response_model=ModelConnectionTestResult)
def test_model(
    body: ModelConnectionTestRequest,
    db: Session = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> ModelConnectionTestResult:
    return ModelConfigService(db, settings).test(body)


@router.get("/model-configs/{id}", response_model=ModelConfigOut)
def get_model(
    model_id: UUID = Path(alias="id"),
    db: Session = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> ModelConfigOut:
    return ModelConfigService(db, settings).get(model_id)


@router.patch("/model-configs/{id}", response_model=ModelConfigOut)
def update_model(
    body: ModelConfigUpdate,
    model_id: UUID = Path(alias="id"),
    db: Session = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> ModelConfigOut:
    return ModelConfigService(db, settings).update(model_id, body)


@router.delete("/model-configs/{id}", status_code=204)
def delete_model(
    model_id: UUID = Path(alias="id"),
    db: Session = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> Response:
    ModelConfigService(db, settings).delete(model_id)
    return Response(status_code=204)


@router.post("/model-configs/{id}/activate", response_model=ModelConfigOut)
def activate_model(
    model_id: UUID = Path(alias="id"),
    db: Session = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> ModelConfigOut:
    return ModelConfigService(db, settings).activate(model_id)


@router.get("/application-config", response_model=ApplicationConfigOut)
def get_application_config(db: Session = Depends(get_session)) -> ApplicationConfigOut:
    config = db.get(ApplicationConfig, True)
    if config is None:
        raise RuntimeError("application config is not seeded")
    return config_out(config)


@router.put("/application-config", response_model=ApplicationConfigOut)
def put_application_config(
    body: ApplicationConfigUpdate, db: Session = Depends(get_session)
) -> ApplicationConfigOut:
    return update_application_config(db, body)


@router.get("/questions/favorites", response_model=list[FavoriteOut])
def list_favorites(
    db: Session = Depends(get_session), settings: Settings = Depends(get_settings)
) -> list[FavoriteOut]:
    return SupportService(db, settings).favorites()


@router.post(
    "/questions/favorites",
    response_model=FavoriteOut,
    status_code=201,
    responses={200: {"model": FavoriteOut, "description": "Existing"}},
)
def add_favorite(
    body: FavoriteCreate,
    response: Response,
    db: Session = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> FavoriteOut:
    result, created = SupportService(db, settings).add_favorite(
        body.question, body.source_message_id
    )
    response.status_code = 201 if created else 200
    return result


@router.delete("/questions/favorites/{favoriteId}", status_code=204)
def remove_favorite(
    favorite_id: UUID = Path(alias="favoriteId"),
    db: Session = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> Response:
    SupportService(db, settings).remove_favorite(favorite_id)
    return Response(status_code=204)


@router.get("/questions/frequent", response_model=list[FrequentQuestionOut])
def frequent_questions(
    limit: int = Query(10, ge=1, le=20),
    db: Session = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> list[FrequentQuestionOut]:
    return SupportService(db, settings).frequent(limit)


@router.post("/feedback", response_model=FeedbackDetail, status_code=201)
def create_feedback(
    body: FeedbackCreate,
    db: Session = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> FeedbackDetail:
    return SupportService(db, settings).create_feedback(body)


@router.get("/feedback", response_model=FeedbackListResponse)
def list_feedback(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, alias="pageSize", ge=1, le=100),
    keyword: str | None = None,
    status: str | None = None,
    reason: str | None = None,
    user_id: str | None = Query(None, alias="userId", max_length=64),
    from_at: datetime | None = Query(None, alias="from"),
    to_at: datetime | None = Query(None, alias="to"),
    db: Session = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> FeedbackListResponse:
    return SupportService(db, settings).list_feedback(
        page, page_size, keyword, status, reason, user_id, from_at, to_at
    )


@router.get("/feedback/{id}", response_model=FeedbackDetail)
def get_feedback(
    feedback_id: UUID = Path(alias="id"),
    db: Session = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> FeedbackDetail:
    return SupportService(db, settings).feedback_detail(feedback_id)


@router.patch("/feedback/{id}", response_model=FeedbackDetail)
def update_feedback(
    body: FeedbackUpdate,
    feedback_id: UUID = Path(alias="id"),
    db: Session = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> FeedbackDetail:
    return SupportService(db, settings).update_feedback(feedback_id, body)


@router.get("/qa/logs", response_model=QaLogListResponse)
def list_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, alias="pageSize", ge=1, le=100),
    keyword: str | None = None,
    status: str | None = None,
    model_config_id: UUID | None = Query(None, alias="modelConfigId"),
    user_id: str | None = Query(None, alias="userId", max_length=64),
    from_at: datetime | None = Query(None, alias="from"),
    to_at: datetime | None = Query(None, alias="to"),
    db: Session = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> QaLogListResponse:
    return SupportService(db, settings).logs(
        page, page_size, keyword, status, model_config_id, user_id, from_at, to_at
    )


@router.get("/qa/logs/{executionId}", response_model=QaLogDetail)
def get_log(
    execution_id: UUID = Path(alias="executionId"),
    db: Session = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> QaLogDetail:
    return SupportService(db, settings).log_detail(execution_id)
