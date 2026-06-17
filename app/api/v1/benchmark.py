"""Serviço de IA nº 2 — benchmark de preço e dispersão de OPME."""

import logging
import sqlite3

from fastapi import APIRouter, Depends

from ...ai.benchmark import benchmark
from ...logging_config import log_with_fields
from ...schemas import BenchmarkRequest, BenchmarkResponse
from ..deps import get_current_user, get_db, rate_limit

logger = logging.getLogger("opme.api.benchmark")
router = APIRouter(prefix="/benchmark", tags=["IA · Benchmark"])


@router.post(
    "",
    response_model=BenchmarkResponse,
    summary="Benchmark de preço, dispersão e oportunidade de economia",
    dependencies=[Depends(rate_limit)],
)
def benchmark_item(
    payload: BenchmarkRequest,
    db: sqlite3.Connection = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Classifica o item, recupera observações comparáveis e calcula estatísticas
    (mediana, p25/p75, coeficiente de variação), outliers (IQR) e — se houver
    `reference_price` — a economia potencial frente à mediana de mercado.
    """
    result = benchmark(
        payload.description, db, region=payload.region,
        reference_price=payload.reference_price,
    )
    log_with_fields(
        logger, logging.INFO, "benchmark_done",
        user=user["username"], taxonomy=result.get("matched_taxonomy_path"),
        n=result.get("stats", {}).get("count") if result.get("stats") else 0,
    )
    return BenchmarkResponse(**result)
