"""Serviço de IA nº 1 — classificação/extração de itens OPME."""

import logging
import sqlite3

from fastapi import APIRouter, Depends

from ...ai.classifier import classify
from ...logging_config import log_with_fields
from ...schemas import ClassifyRequest, ClassifyResponse
from ..deps import get_current_user, get_db, rate_limit

logger = logging.getLogger("opme.api.classify")
router = APIRouter(prefix="/classify", tags=["IA · Classificação"])


@router.post(
    "",
    response_model=ClassifyResponse,
    summary="Classifica e extrai atributos de uma descrição OPME",
    dependencies=[Depends(rate_limit)],
)
def classify_item(
    payload: ClassifyRequest,
    db: sqlite3.Connection = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Transforma uma descrição livre em item estruturado + classe taxonômica.

    Pipeline híbrido: **regras determinísticas → similaridade contra taxonomia →
    (opcional) refino por LLM**. Retorna nome canônico, atributos, candidatos,
    decisão (MATCH/REVIEW/NO_MATCH), confiança e evidências.
    """
    result = classify(payload.description, db)
    log_with_fields(
        logger, logging.INFO, "classify_done",
        user=user["username"], decision=result["decision"],
        confidence=result["confidence"], engine=result["engine"],
    )
    return ClassifyResponse(**result)
