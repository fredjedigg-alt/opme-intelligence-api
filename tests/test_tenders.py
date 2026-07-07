"""Testes do Serviço 4 — Radar de Licitações (PNCP).

Sem rede: os clientes HTTP do PNCP são substituídos por stubs com payloads REAIS
capturados do portal em 2026-07-07 (busca + itens), garantindo que o parse
reflete o contrato verdadeiro da API pública.
"""

import pytest

from app.services import pncp

# Recorte real da resposta de /api/search/ (q=OPME, status=recebendo_proposta).
SEARCH_PAYLOAD = {
    "total": 2,
    "items": [
        {
            "title": "Edital nº 43/2026",
            "description": (
                "Aquisição futura de Órteses, Próteses e Materiais Especiais (OPME) "
                "para uso na Fundação Hospital Centenário (FHC)."
            ),
            "item_url": "/compras/92931245000150/2026/112",
            "numero_controle_pncp": "92931245000150-1-000112/2026",
            "ano": "2026",
            "numero_sequencial": "112",
            "orgao_cnpj": "92931245000150",
            "orgao_nome": "FUNDACAO HOSPITAL CENTENARIO",
            "unidade_nome": "Fundação Hospital Centenário de São Leopoldo",
            "esfera_nome": "Municipal",
            "uf": "RS",
            "municipio_nome": "São Leopoldo",
            "modalidade_licitacao_nome": "Pregão - Eletrônico",
            "situacao_nome": "Divulgada no PNCP",
            "data_publicacao_pncp": "2026-06-25T11:41:17.381722",
            "data_fim_vigencia": "2030-07-08T09:00",
        },
        {
            "title": "Edital nº 90/2026",
            "description": "Registro de preços de stents e materiais hemodinâmica.",
            "item_url": "/compras/00000000000191/2026/90",
            "numero_controle_pncp": "00000000000191-1-000090/2026",
            "ano": "2026",
            "numero_sequencial": "90",
            "orgao_cnpj": "00000000000191",
            "orgao_nome": "HOSPITAL FEDERAL DE GOIAS",
            "unidade_nome": "Unidade de Compras",
            "esfera_nome": "Federal",
            "uf": "GO",
            "municipio_nome": "Goiânia",
            "modalidade_licitacao_nome": "Pregão - Eletrônico",
            "situacao_nome": "Divulgada no PNCP",
            "data_publicacao_pncp": "2026-07-01T08:00:00",
            "data_fim_vigencia": "2030-07-20T09:00",
        },
    ],
}

# Recorte real de /api/pncp/v1/orgaos/{cnpj}/compras/{ano}/{seq}/itens.
ITEMS_BY_TENDER = {
    "92931245000150": [
        {
            "numeroItem": 1,
            "descricao": "Prótese total de quadril não cimentada, haste femoral e componente acetabular",
            "quantidade": 96.0,
            "unidadeMedida": "Unidade",
            "valorUnitarioEstimado": 3457.36,
            "valorTotal": 331906.56,
        },
        {
            "numeroItem": 2,
            "descricao": "Serviço de manutenção predial, pintura e reparos de alvenaria",
            "quantidade": 1.0,
            "unidadeMedida": "Serviço",
            "valorUnitarioEstimado": 5000.0,
            "valorTotal": 5000.0,
        },
    ],
    "00000000000191": [
        {
            "numeroItem": 1,
            "descricao": "Stent farmacológico coronário 3.0 x 18 mm eluidor de droga",
            "quantidade": 50.0,
            "unidadeMedida": "Unidade",
            "valorUnitarioEstimado": 9000.0,
            "valorTotal": 450000.0,
        },
    ],
}


@pytest.fixture()
def pncp_stub(monkeypatch):
    """Substitui os dois clientes HTTP por stubs determinísticos."""
    calls = {"search": 0, "items": 0}

    def fake_search(term, pagina=1, tam_pagina=50):
        calls["search"] += 1
        return SEARCH_PAYLOAD

    def fake_items(cnpj, ano, sequencial, pagina=1, tamanho_pagina=100):
        calls["items"] += 1
        return ITEMS_BY_TENDER.get(cnpj, [])

    monkeypatch.setattr(pncp, "search_open_tenders", fake_search)
    monkeypatch.setattr(pncp, "fetch_tender_items", fake_items)
    return calls


def _scan(client, auth_headers, **body):
    return client.post(
        "/api/v1/tenders/scan",
        json={"terms": ["OPME"], **body},
        headers=auth_headers,
    )


def test_scan_requires_auth(client):
    resp = client.post("/api/v1/tenders/scan", json={})
    assert resp.status_code == 401


def test_scan_persists_and_classifies(client, auth_headers, pncp_stub):
    resp = _scan(client, auth_headers)
    assert resp.status_code == 200, resp.text
    data = resp.json()

    assert data["tenders_found"] == 2
    assert data["tenders_new"] == 2
    assert data["items_scanned"] == 3
    # Prótese de quadril + stent são OPME; manutenção predial é ruído.
    assert data["items_opme"] == 2
    assert data["opme_estimated_value"] == pytest.approx(331906.56 + 450000.0)
    assert data["by_esfera"] == {"Municipal": 1, "Federal": 1}
    assert set(data["by_uf"]) == {"RS", "GO"}


def test_rescan_updates_without_duplicating(client, auth_headers, pncp_stub):
    first = _scan(client, auth_headers).json()
    again = _scan(client, auth_headers).json()

    assert again["tenders_new"] == 0
    assert again["tenders_updated"] == first["tenders_found"] == 2
    # Itens não são rebuscados nem duplicados na re-varredura.
    assert again["items_scanned"] == 0

    listing = client.get("/api/v1/tenders", headers=auth_headers).json()
    assert listing["total"] == 2


def test_scan_filters_by_esfera_and_uf(client, auth_headers, pncp_stub):
    resp = _scan(client, auth_headers, esfera="Federal", uf="GO")
    data = resp.json()
    assert data["by_esfera"].get("Federal") == data["tenders_found"]
    assert list(data["by_uf"].keys()) == ["GO"]


def test_list_tenders_with_filters(client, auth_headers, pncp_stub):
    _scan(client, auth_headers)

    resp = client.get("/api/v1/tenders?uf=RS", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    tender = data["tenders"][0]
    assert tender["esfera"] == "Municipal"
    assert tender["items_total"] == 2
    assert tender["items_opme"] == 1
    assert tender["source_url"].startswith("https://pncp.gov.br/app/editais/")

    # only_open: datas de fim em 2030 mantêm os dois editais.
    resp = client.get("/api/v1/tenders?only_open=true", headers=auth_headers)
    assert resp.json()["total"] == 2

    resp = client.get("/api/v1/tenders?q=stents", headers=auth_headers)
    assert resp.json()["total"] == 1


def test_tender_items_with_benchmark(client, auth_headers, pncp_stub):
    _scan(client, auth_headers)
    listing = client.get("/api/v1/tenders?uf=GO", headers=auth_headers).json()
    tender_id = listing["tenders"][0]["tender_id"]

    resp = client.get(
        f"/api/v1/tenders/{tender_id}/items?benchmark=true", headers=auth_headers
    )
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert len(items) == 1

    stent = items[0]
    assert stent["is_opme"] is True
    assert stent["classify_decision"] in ("MATCH", "REVIEW")
    assert stent["taxonomy_path"] is not None
    # Base de seed tem 26 observações de stent farmacológico -> benchmark presente.
    assert stent["benchmark"] is not None
    assert stent["benchmark"]["sample_count"] >= 3
    assert stent["benchmark"]["market_median"] > 0
    assert stent["benchmark"]["verdict"]


def test_tender_items_not_found(client, auth_headers):
    resp = client.get("/api/v1/tenders/99999/items", headers=auth_headers)
    assert resp.status_code == 404
