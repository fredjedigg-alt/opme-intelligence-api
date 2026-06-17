"""Testes do Serviço de IA nº 1 — classificação/extração."""


def test_classify_orthopedic_plate(client, auth_headers):
    desc = ("Placa bloqueada distal rádio volar 2.4 mm titânio 6 furos, "
            "estéril, ref XZ-244, fabricante OrthoMed")
    resp = client.post("/api/v1/classify", json={"description": desc}, headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["decision"] in ("MATCH", "REVIEW")
    assert body["specialty"] == "Ortopedia"
    # Extração determinística de atributos:
    assert body["material"] == "titânio"
    assert body["sterile"] is True
    assert body["reference_code"] == "XZ-244"
    assert body["manufacturer"].lower().startswith("orthomed")
    assert body["dimensions"].get("size_mm") == 2.4
    assert body["dimensions"].get("holes") == 6
    assert 0 <= body["confidence"] <= 1
    assert len(body["candidates"]) > 0


def test_classify_drug_eluting_stent(client, auth_headers):
    resp = client.post(
        "/api/v1/classify",
        json={"description": "stent farmacológico coronário 3.0 x 18 mm"},
        headers=auth_headers,
    )
    body = resp.json()
    assert body["specialty"] == "Cardiologia"
    assert body["dimensions"].get("diameter_mm") == 3.0
    assert body["dimensions"].get("length_mm") == 18.0
    assert body["engine"].startswith("regras+similaridade")
    # Regressão: "farmacológico" NÃO deve disparar falso-positivo de material "aço".
    assert body["material"] is None


def test_classify_gibberish_is_no_match_or_review(client, auth_headers):
    resp = client.post(
        "/api/v1/classify",
        json={"description": "xpto zzz qwerty 123 nada disso"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["decision"] in ("NO_MATCH", "REVIEW")


def test_classify_validation_too_short(client, auth_headers):
    resp = client.post("/api/v1/classify", json={"description": "ab"}, headers=auth_headers)
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "validation_error"


def test_classify_missing_field(client, auth_headers):
    resp = client.post("/api/v1/classify", json={}, headers=auth_headers)
    assert resp.status_code == 422
