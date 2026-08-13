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

-- Licitações públicas encontradas pelo Radar (fonte: PNCP, Lei 14.133/2021).
CREATE TABLE IF NOT EXISTS tender (
    tender_id           INTEGER PRIMARY KEY AUTOINCREMENT,
    pncp_control_number TEXT UNIQUE NOT NULL,  -- numero_controle_pncp (chave de dedupe)
    title               TEXT,
    description         TEXT,
    orgao_cnpj          TEXT NOT NULL,
    orgao_nome          TEXT,
    unidade_nome        TEXT,
    esfera              TEXT,                  -- Federal / Estadual / Municipal
    uf                  TEXT,
    municipio           TEXT,
    modalidade          TEXT,
    ano                 INTEGER NOT NULL,
    sequencial          INTEGER NOT NULL,
    data_publicacao     TEXT,
    data_fim_propostas  TEXT,
    situacao            TEXT,
    source_url          TEXT,
    matched_term        TEXT,                  -- termo de busca que encontrou o edital
    scanned_at          TEXT NOT NULL
);

-- Itens (demandas) de cada licitação, com classificação OPME do Serviço 1.
CREATE TABLE IF NOT EXISTS tender_item (
    item_id              INTEGER PRIMARY KEY AUTOINCREMENT,
    tender_id            INTEGER NOT NULL REFERENCES tender(tender_id),
    numero_item          INTEGER,
    description          TEXT NOT NULL,
    quantity             REAL,
    unit                 TEXT,
    unit_price_estimated REAL,
    total_estimated      REAL,
    is_opme              INTEGER NOT NULL DEFAULT 0,  -- 1 quando MATCH/REVIEW na taxonomia
    taxonomy_id          INTEGER,
    taxonomy_path        TEXT,
    canonical_name       TEXT,
    classify_decision    TEXT,
    classify_confidence  REAL
);

CREATE INDEX IF NOT EXISTS idx_tender_uf       ON tender(uf);
CREATE INDEX IF NOT EXISTS idx_tender_esfera   ON tender(esfera);
CREATE INDEX IF NOT EXISTS idx_titem_tender    ON tender_item(tender_id);
CREATE INDEX IF NOT EXISTS idx_titem_is_opme   ON tender_item(is_opme);
"""


def get_db_path() -> str:
    from .config import get_settings

    return get_settings().database_path


def connect() -> sqlite3.Connection:
    """Abre uma conexão com row factory de dicionário e FKs habilitadas.

    Usa WAL porque a varredura do PNCP (`/tenders/scan`) mantém uma transação de
    escrita aberta por dezenas de segundos; no journal padrão isso bloqueia toda
    leitura concorrente e a API inteira passa a devolver 500 "database is
    locked". Em WAL os leitores não esperam o escritor. O `busy_timeout` cobre o
    caso de dois escritores simultâneos, que continuam serializados.
    """
    conn = sqlite3.connect(get_db_path(), timeout=30.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA busy_timeout = 30000;")
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
