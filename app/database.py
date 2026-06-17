"""Camada de dados em SQLite (stdlib `sqlite3`).

Escolha deliberada: SQLite não exige servidor nem dependência externa, então a API
roda em qualquer máquina (critério de avaliação: "executa em outro computador").
O esquema é um recorte enxuto do modelo lógico OPME (taxonomia + observações de preço),
suficiente para alimentar os serviços de IA e o benchmark.
"""

import logging
import sqlite3
from pathlib import Path

logger = logging.getLogger("opme.database")

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    username      TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    role          TEXT NOT NULL DEFAULT 'analyst'
);

-- Taxonomia mestre OPME (hierarquia especialidade > família > subfamília).
CREATE TABLE IF NOT EXISTS opme_taxonomy (
    taxonomy_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    specialty      TEXT NOT NULL,
    family         TEXT NOT NULL,
    subfamily      TEXT,
    canonical_label TEXT NOT NULL,
    keywords       TEXT NOT NULL,   -- termos/sinônimos separados por vírgula
    default_uom    TEXT DEFAULT 'unidade'
);

-- Observações de preço normalizadas (base do benchmark).
CREATE TABLE IF NOT EXISTS price_observation (
    obs_id          INTEGER PRIMARY KEY AUTOINCREMENT,
    taxonomy_id     INTEGER NOT NULL REFERENCES opme_taxonomy(taxonomy_id),
    canonical_name  TEXT NOT NULL,
    supplier        TEXT NOT NULL,
    manufacturer    TEXT,
    region          TEXT NOT NULL,
    uom_standard    TEXT NOT NULL DEFAULT 'unidade',
    normalized_price REAL NOT NULL,
    observation_date TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_price_taxonomy ON price_observation(taxonomy_id);
CREATE INDEX IF NOT EXISTS idx_price_region   ON price_observation(region);
"""


def get_db_path() -> str:
    from .config import get_settings

    return get_settings().database_path


def connect() -> sqlite3.Connection:
    """Abre uma conexão com row factory de dicionário e FKs habilitadas."""
    conn = sqlite3.connect(get_db_path())
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def init_db() -> None:
    """Cria o esquema (idempotente) e popula com seed caso esteja vazio."""
    conn = connect()
    try:
        conn.executescript(SCHEMA)
        conn.commit()
        count = conn.execute("SELECT COUNT(*) AS n FROM opme_taxonomy").fetchone()["n"]
        if count == 0:
            from data.seed_opme import seed_database

            seed_database(conn)
            logger.info("Banco populado com dados de seed (taxonomia + preços).")
        else:
            logger.info("Banco já populado (%s nós de taxonomia).", count)
    finally:
        conn.close()


def reset_db() -> None:
    """Remove o arquivo do banco (usado em testes)."""
    p = Path(get_db_path())
    if p.exists():
        p.unlink()
