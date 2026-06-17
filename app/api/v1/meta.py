"""Endpoints de metadados: health-check e consulta da taxonomia."""

import sqlite3

from fastapi import APIRouter, Depends

from ... import __version__
from ...config import get_settings
from ...schemas import HealthResponse, TaxonomyNode
from ..deps import get_db

router = APIRouter(tags=["Metadados"])


@router.get("/health", response_model=HealthResponse, summary="Status da aplicação")
def health(db: sqlite3.Connection = Depends(get_db)):
    """Endpoint público de saúde — não exige autenticação."""
    settings = get_settings()
    tax = db.execute("SELECT COUNT(*) AS n FROM opme_taxonomy").fetchone()["n"]
    obs = db.execute("SELECT COUNT(*) AS n FROM price_observation").fetchone()["n"]
    return HealthResponse(
        status="ok",
        version=__version__,
        environment=settings.app_env,
        llm_enabled=settings.llm_enabled,
        taxonomy_nodes=tax,
        price_observations=obs,
    )


@router.get("/taxonomy", response_model=list[TaxonomyNode], summary="Lista a taxonomia OPME")
def list_taxonomy(db: sqlite3.Connection = Depends(get_db)):
    """Retorna todos os nós da taxonomia mestre OPME carregada."""
    rows = db.execute(
        "SELECT taxonomy_id, specialty, family, subfamily, canonical_label "
        "FROM opme_taxonomy ORDER BY specialty, family"
    ).fetchall()
    nodes = []
    for r in rows:
        parts = [r["specialty"], r["family"]] + ([r["subfamily"]] if r["subfamily"] else [])
        nodes.append(
            TaxonomyNode(
                taxonomy_id=r["taxonomy_id"],
                specialty=r["specialty"],
                family=r["family"],
                subfamily=r["subfamily"],
                canonical_label=r["canonical_label"],
                path=" > ".join(p.upper() for p in parts),
            )
        )
    return nodes
