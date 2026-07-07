"""Serviço nº 4 — Radar de Licitações OPME (varredura do PNCP)."""

import logging
import sqlite3
from typing import Optional

from fastapi import APIRouter, Depends, Query

from ...ai.benchmark import benchmark
from ...errors import NotFoundError
from ...logging_config import log_with_fields
from ...schemas import (
    TenderItemsResponse,
    TenderListResponse,
    TenderScanRequest,
    TenderScanResponse,
)
from ...services.tender_scan import run_scan
from ..deps import get_current_user, get_db, rate_limit

logger = logging.getLogger("opme.api.tenders")
router = APIRouter(prefix="/tenders", tags=["IA · Radar de Licitações"])

_TENDER_LIST_SQL = """
SELECT t.*,
       COUNT(i.item_id)                            AS items_total,
       COALESCE(SUM(i.is_opme), 0)                 AS items_opme,
       COALESCE(SUM(CASE WHEN i.is_opme = 1
                    THEN i.total_estimated END), 0) AS opme_estimated_value
FROM tender t
LEFT JOIN tender_item i ON i.tender_id = t.tender_id
{where}
GROUP BY t.tender_id
ORDER BY t.data_fim_propostas ASC
LIMIT ? OFFSET ?
"""


@router.post(
    "/scan",
    response_model=TenderScanResponse,
    summary="Varre o PNCP em busca de licitações OPME com propostas abertas",
    dependencies=[Depends(rate_limit)],
)
def scan_tenders(
    payload: TenderScanRequest,
    db: sqlite3.Connection = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Busca editais **recebendo propostas** nas 3 esferas (fonte: PNCP),
    persiste com dedupe por `numero_controle_pncp` e classifica cada item
    do edital com o Serviço 1 para identificar as demandas de OPME.
    """
    result = run_scan(
        db,
        terms=payload.terms,
        uf=payload.uf,
        esfera=payload.esfera,
        max_pages=payload.max_pages,
        use_llm=payload.use_llm,
    )
    log_with_fields(
        logger,
        logging.INFO,
        "tender_scan_done",
        user=user["username"],
        tenders=result["tenders_found"],
        items_opme=result["items_opme"],
    )
    return TenderScanResponse(**result)


@router.get(
    "",
    response_model=TenderListResponse,
    summary="Lista as licitações OPME já varridas",
    dependencies=[Depends(rate_limit)],
)
def list_tenders(
    uf: Optional[str] = Query(default=None, min_length=2, max_length=2),
    esfera: Optional[str] = Query(default=None),
    q: Optional[str] = Query(
        default=None, description="Busca textual em título/descrição/órgão."
    ),
    only_open: bool = Query(
        default=False, description="Apenas prazos de proposta futuros."
    ),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: sqlite3.Connection = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Consulta o repositório local de licitações alimentado pelo `/tenders/scan`."""
    clauses, params = [], []
    if uf:
        clauses.append("t.uf = ?")
        params.append(uf.upper())
    if esfera:
        clauses.append("LOWER(t.esfera) = LOWER(?)")
        params.append(esfera)
    if q:
        clauses.append(
            "(t.title LIKE ? OR t.description LIKE ? OR t.orgao_nome LIKE ?)"
        )
        params.extend([f"%{q}%"] * 3)
    if only_open:
        clauses.append("t.data_fim_propostas >= datetime('now')")
    where = ("WHERE " + " AND ".join(clauses)) if clauses else ""

    total = db.execute(
        f"SELECT COUNT(*) AS n FROM tender t {where}", params
    ).fetchone()["n"]
    rows = db.execute(
        _TENDER_LIST_SQL.format(where=where),
        [*params, page_size, (page - 1) * page_size],
    ).fetchall()

    return TenderListResponse(
        total=total,
        page=page,
        page_size=page_size,
        tenders=[dict(r) for r in rows],
    )


@router.get(
    "/{tender_id}/items",
    response_model=TenderItemsResponse,
    summary="Itens de uma licitação com classificação OPME (e benchmark opcional)",
    dependencies=[Depends(rate_limit)],
)
def tender_items(
    tender_id: int,
    include_benchmark: bool = Query(
        default=False,
        alias="benchmark",
        description="Cruza itens OPME com a base de preços (mediana de mercado).",
    ),
    db: sqlite3.Connection = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Retorna as demandas do edital. Com `benchmark=true`, compara o valor
    unitário estimado de cada item OPME com a mediana de mercado do Serviço 2 —
    o "radar de oportunidade" (edital acima/abaixo do mercado).
    """
    tender = db.execute(
        "SELECT tender_id, pncp_control_number FROM tender WHERE tender_id = ?",
        (tender_id,),
    ).fetchone()
    if not tender:
        raise NotFoundError(
            f"Licitação {tender_id} não encontrada no repositório local."
        )

    rows = [
        dict(r)
        for r in db.execute(
            "SELECT * FROM tender_item WHERE tender_id = ? ORDER BY numero_item",
            (tender_id,),
        ).fetchall()
    ]

    items = []
    for row in rows:
        row["is_opme"] = bool(row["is_opme"])
        if include_benchmark and row["is_opme"] and row.get("unit_price_estimated"):
            bm = benchmark(row["description"][:1000], db)
            stats = bm.get("stats")
            if stats:
                median = stats["median"]
                delta = (
                    round((row["unit_price_estimated"] - median) / median * 100, 2)
                    if median
                    else None
                )
                verdict = (
                    "edital acima da mediana de mercado"
                    if delta and delta > 0
                    else "edital em linha ou abaixo da mediana de mercado"
                )
                row["benchmark"] = {
                    "market_median": median,
                    "sample_count": stats["count"],
                    "delta_pct": delta,
                    "verdict": verdict,
                }
        items.append(row)

    return TenderItemsResponse(
        tender_id=tender["tender_id"],
        pncp_control_number=tender["pncp_control_number"],
        items=items,
    )
