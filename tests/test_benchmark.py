"""Testes do Serviço de IA nº 2 (benchmark) e nº 3 (comparabilidade)."""


def test_benchmark_returns_stats(client, auth_headers):
    resp = client.post(
        "/api/v1/benchmark",
        json={"description": "stent farmacológico coronário 3.0 x 18 mm"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["matched_taxonomy_path"] is not None
    stats = body["stats"]
    assert stats["count"] >= 3
    assert stats["min"] <= stats["median"] <= stats["max"]
    assert stats["p25"] <= stats["p75"]
    assert body["dispersion_level"] in ("baixa", "media", "alta")
    # Há um outlier proposital de stent farmacológico no seed.
    assert len(body["outliers"]) >= 1


def test_benchmark_saving_opportunity(client, auth_headers):
    resp = client.post(
        "/api/v1/benchmark",
        json={"description": "tela de polipropileno", "reference_price": 900},
        headers=auth_headers,
    )
    body = resp.json()
    saving = body["saving_opportunity"]
    assert saving is not None
    # 900 deve estar acima da mediana (~320), gerando economia potencial.
    assert saving["potential_saving_abs"] > 0
    assert saving["market_median"] < 900


def test_benchmark_region_filter(client, auth_headers):
    resp = client.post(
        "/api/v1/benchmark",
        json={"description": "parafuso bloqueado", "region": "Sudeste"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert "região" in resp.json()["comparable_basis"]


def test_benchmark_unmatched_item(client, auth_headers):
    resp = client.post(
        "/api/v1/benchmark",
        json={"description": "xpto zzz qwerty nada"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    # Sem grupo comparável -> sem stats, com nota explicativa.
    assert resp.json()["stats"] is None
    assert resp.json()["note"] is not None


def test_comparability_same_item(client, auth_headers):
    resp = client.post(
        "/api/v1/comparability",
        json={
            "item_a": "stent farmacológico coronário 3.0 x 18 mm",
            "item_b": "stent farmacológico coronário 3.0 x 18 mm",
        },
        headers=auth_headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["same_taxonomy"] is True
    assert body["decision"] == "COMPARABLE"


def test_comparability_different_items(client, auth_headers):
    resp = client.post(
        "/api/v1/comparability",
        json={
            "item_a": "stent farmacológico coronário 3.0 x 18 mm",
            "item_b": "tela de polipropileno para hérnia inguinal",
        },
        headers=auth_headers,
    )
    body = resp.json()
    assert body["same_taxonomy"] is False
    assert body["decision"] == "NOT_COMPARABLE"


def test_comparability_different_dimensions_review(client, auth_headers):
    resp = client.post(
        "/api/v1/comparability",
        json={
            "item_a": "stent farmacológico coronário 3.0 x 18 mm",
            "item_b": "stent farmacológico coronário 2.5 x 12 mm",
        },
        headers=auth_headers,
    )
    body = resp.json()
    assert body["same_taxonomy"] is True
    # Dimensões diferentes -> diferenças críticas registradas.
    assert len(body["critical_differences"]) >= 1
