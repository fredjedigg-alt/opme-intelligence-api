"""Motor do Radar de Licitações (Serviço nº 4).

Orquestra a varredura: busca editais abertos no PNCP por termos OPME, deduplica,
persiste com upsert (re-varreduras atualizam situação/prazo sem duplicar) e roda
o classificador taxonômico (Serviço 1) sobre cada item para separar o que é
demanda de OPME do que é ruído do edital.
"""

import logging
import sqlite3
from collections import Counter
from datetime import datetime, timezone

from ..ai.classifier import classify
from ..config import get_settings
from ..errors import UpstreamError
from . import pncp

logger = logging.getLogger("opme.services.tender_scan")

_SEARCH_PAGE_SIZE = 50
# Decisões do classificador que marcam o item como demanda OPME.
_OPME_DECISIONS = ("MATCH", "REVIEW")


def _portal_url(cnpj: str, ano: int, sequencial: int) -> str:
    return f"https://pncp.gov.br/app/editais/{cnpj}/{ano}/{sequencial}"


def _collect_search_results(
    terms: list[str], uf: str | None, esfera: str | None, max_pages: int
) -> dict[str, dict]:
    """Busca todos os termos e devolve editais únicos por numero_controle_pncp."""
    found: dict[str, dict] = {}
    for term in terms:
        for page in range(1, max_pages + 1):
            data = pncp.search_open_tenders(
                term, pagina=page, tam_pagina=_SEARCH_PAGE_SIZE
            )
            items = data.get("items", [])
            for raw in items:
                control = raw.get("numero_controle_pncp")
                if not control or control in found:
                    continue
                if uf and (raw.get("uf") or "").upper() != uf.upper():
                    continue
                if esfera and (raw.get("esfera_nome") or "").lower() != esfera.lower():
                    continue
                raw["_matched_term"] = term
                found[control] = raw
            if len(items) < _SEARCH_PAGE_SIZE:
                break  # última página deste termo
    return found


def _upsert_tender(
    conn: sqlite3.Connection, raw: dict, scanned_at: str
) -> tuple[int, bool]:
    """Insere ou atualiza um edital; retorna (tender_id, is_new)."""
    control = raw["numero_controle_pncp"]
    existing = conn.execute(
        "SELECT tender_id FROM tender WHERE pncp_control_number = ?", (control,)
    ).fetchone()

    ano = int(raw.get("ano") or 0)
    sequencial = int(raw.get("numero_sequencial") or 0)
    cnpj = raw.get("orgao_cnpj") or ""

    if existing:
        conn.execute(
            "UPDATE tender SET situacao = ?, data_fim_propostas = ?, scanned_at = ? "
            "WHERE tender_id = ?",
            (
                raw.get("situacao_nome"),
                raw.get("data_fim_vigencia"),
                scanned_at,
                existing["tender_id"],
            ),
        )
        return existing["tender_id"], False

    cur = conn.execute(
        """
        INSERT INTO tender (
            pncp_control_number, title, description, orgao_cnpj, orgao_nome,
            unidade_nome, esfera, uf, municipio, modalidade, ano, sequencial,
            data_publicacao, data_fim_propostas, situacao, source_url,
            matched_term, scanned_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            control,
            raw.get("title"),
            raw.get("description"),
            cnpj,
            raw.get("orgao_nome"),
            raw.get("unidade_nome"),
            raw.get("esfera_nome"),
            raw.get("uf"),
            raw.get("municipio_nome"),
            raw.get("modalidade_licitacao_nome"),
            ano,
            sequencial,
            raw.get("data_publicacao_pncp"),
            raw.get("data_fim_vigencia"),
            raw.get("situacao_nome"),
            _portal_url(cnpj, ano, sequencial),
            raw.get("_matched_term"),
            scanned_at,
        ),
    )
    return cur.lastrowid, True


def _store_items(
    conn: sqlite3.Connection, tender_id: int, raw_items: list[dict], use_llm: bool
) -> tuple[int, int, float]:
    """Classifica e grava os itens; retorna (total, qtde OPME, valor OPME estimado)."""
    total, opme_count, opme_value = 0, 0, 0.0
    for item in raw_items:
        description = (item.get("descricao") or "").strip()
        if not description:
            continue
        cls = classify(description[:1000], conn, use_llm=use_llm)
        is_opme = cls["decision"] in _OPME_DECISIONS
        conn.execute(
            """
            INSERT INTO tender_item (
                tender_id, numero_item, description, quantity, unit,
                unit_price_estimated, total_estimated, is_opme, taxonomy_id,
                taxonomy_path, canonical_name, classify_decision, classify_confidence
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                tender_id,
                item.get("numeroItem"),
                description,
                item.get("quantidade"),
                item.get("unidadeMedida"),
                item.get("valorUnitarioEstimado"),
                item.get("valorTotal"),
                1 if is_opme else 0,
                cls.get("taxonomy_id"),
                cls.get("taxonomy_path"),
                cls.get("canonical_name"),
                cls["decision"],
                cls["confidence"],
            ),
        )
        total += 1
        if is_opme:
            opme_count += 1
            opme_value += float(item.get("valorTotal") or 0.0)
    return total, opme_count, opme_value


def run_scan(
    conn: sqlite3.Connection,
    terms: list[str] | None = None,
    uf: str | None = None,
    esfera: str | None = None,
    max_pages: int = 1,
    use_llm: bool = False,
) -> dict:
    """Executa a varredura completa e devolve dict pronto p/ TenderScanResponse."""
    settings = get_settings()
    terms = [t for t in (terms or settings.pncp_terms_list) if t.strip()]
    scanned_at = datetime.now(timezone.utc).isoformat(timespec="seconds")

    found = _collect_search_results(terms, uf, esfera, max_pages)

    tenders_new = tenders_updated = 0
    items_total = items_opme = 0
    opme_value = 0.0
    fetch_errors = 0
    by_esfera: Counter[str] = Counter()
    by_uf: Counter[str] = Counter()

    for raw in found.values():
        tender_id, is_new = _upsert_tender(conn, raw, scanned_at)
        tenders_new += is_new
        tenders_updated += not is_new
        by_esfera[raw.get("esfera_nome") or "?"] += 1
        by_uf[raw.get("uf") or "?"] += 1

        # Itens são imutáveis no PNCP após publicação: só busca quando ainda não temos.
        has_items = conn.execute(
            "SELECT 1 FROM tender_item WHERE tender_id = ? LIMIT 1", (tender_id,)
        ).fetchone()
        if has_items:
            continue
        try:
            raw_items = pncp.fetch_tender_items(
                raw.get("orgao_cnpj") or "",
                int(raw.get("ano") or 0),
                int(raw.get("numero_sequencial") or 0),
            )
        except UpstreamError:
            # Falha pontual em um edital não aborta a varredura inteira.
            fetch_errors += 1
            logger.warning(
                "tender_items_fetch_failed control=%s", raw.get("numero_controle_pncp")
            )
            continue
        total, opme, value = _store_items(conn, tender_id, raw_items, use_llm)
        items_total += total
        items_opme += opme
        opme_value += value

    conn.commit()
    logger.info(
        "scan_done terms=%s tenders=%s new=%s items=%s opme=%s errors=%s",
        len(terms),
        len(found),
        tenders_new,
        items_total,
        items_opme,
        fetch_errors,
    )

    return {
        "scanned_at": scanned_at,
        "terms_used": terms,
        "tenders_found": len(found),
        "tenders_new": tenders_new,
        "tenders_updated": tenders_updated,
        "items_scanned": items_total,
        "items_opme": items_opme,
        "opme_estimated_value": round(opme_value, 2),
        "item_fetch_errors": fetch_errors,
        "by_esfera": dict(by_esfera),
        "by_uf": dict(by_uf),
    }
