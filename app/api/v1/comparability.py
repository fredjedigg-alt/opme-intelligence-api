"""Serviço de IA nº 3 — comparabilidade econômica entre dois itens OPME."""

import logging
import sqlite3

from fastapi import APIRouter, Depends

from ...ai.comparability import compare
from ...schemas import ComparabilityRequest, ComparabilityResponse
from ..deps import get_current_user, get_db, rate_limit

logger = logging.getLogger("opme.api.comparability")
router = APIRouter(prefix="/comparability", tags=["IA · Comparabilidade"])


@router.post(
    "",
    response_model=ComparabilityResponse,
    summary="Decide se dois itens são comparáveis para benchmark",
    dependencies=[Depends(rate_limit)],
)
def compare_items(
    payload: ComparabilityRequest,
    db: sqlite3.Connection = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Avalia se dois itens podem ser comparados em preço — distinguindo
    'mesma classe taxonômica' de 'equivalência econômica' (material/dimensões).
    """
    result = compare(payload.item_a, payload.item_b, db)
    logger.info("comparability_done user=%s decision=%s", user["username"], result["decision"])
    return ComparabilityResponse(**result)
