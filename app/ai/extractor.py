"""Extração determinística de atributos técnicos de OPME (motor de regras).

Esta é a primeira etapa do pipeline híbrido (regras -> similaridade -> LLM).
Regras determinísticas são baratas, auditáveis e não alucinam; por isso resolvem
unidades, dimensões, material, esterilidade, código de referência e fabricante
antes de qualquer modelo. Cada atributo extraído vem com seu trecho de evidência.
"""

import re

# Materiais comuns em OPME e suas variações de grafia.
_MATERIALS = {
    "titanio": "titânio",
    "aco inox": "aço inoxidável",
    "aco inoxidavel": "aço inoxidável",
    "aco": "aço",
    "polietileno": "polietileno",
    "polipropileno": "polipropileno",
    "peek": "PEEK",
    "cobalto cromo": "cobalto-cromo",
    "cromo cobalto": "cobalto-cromo",
    "nitinol": "nitinol",
    "silicone": "silicone",
    "ceramica": "cerâmica",
}

_STERILE_TRUE = re.compile(r"\best[eé]ril\b", re.IGNORECASE)
_STERILE_FALSE = re.compile(r"\bn[aã]o\s+est[eé]ril\b", re.IGNORECASE)

# Código de referência: ref/cod/código seguido de um código alfanumérico.
_REF = re.compile(r"\b(?:ref|cod|c[oó]digo|referencia|refer[eê]ncia)\.?\s*[:\-]?\s*([A-Z0-9][A-Z0-9\-\/]{2,})", re.IGNORECASE)

# Fabricante: "fabricante X" ou "fab. X" (captura 1-3 palavras seguintes).
_MANUF = re.compile(r"\bfabricante\.?\s*[:\-]?\s*([A-Za-zÀ-ÿ0-9][A-Za-zÀ-ÿ0-9\s&\.\-]{1,30})", re.IGNORECASE)


def _norm(s: str) -> str:
    import unicodedata

    s = unicodedata.normalize("NFKD", s.lower())
    return "".join(c for c in s if not unicodedata.combining(c))


def extract_attributes(description: str) -> dict:
    """Retorna {'attributes': {...}, 'dimensions': {...}, 'evidence': [...]}."""
    desc = description.strip()
    desc_n = _norm(desc)
    attributes: dict = {}
    dimensions: dict = {}
    evidence: list[dict] = []

    # --- Material (match por palavra inteira; evita falso-positivo como
    # "aco" dentro de "farmaCOlogico") ---
    for key, canonical in _MATERIALS.items():
        if re.search(rf"\b{re.escape(key)}\b", desc_n):
            attributes["material"] = canonical
            evidence.append({"field": "material", "text": key})
            break

    # --- Esterilidade (negação tem prioridade) ---
    if _STERILE_FALSE.search(desc):
        attributes["sterile"] = False
        evidence.append({"field": "sterile", "text": "não estéril"})
    elif _STERILE_TRUE.search(desc):
        attributes["sterile"] = True
        evidence.append({"field": "sterile", "text": "estéril"})

    # --- Dimensões em mm (ex.: "2.4 mm", "3.0 x 18 mm") ---
    dim_pairs = re.findall(r"(\d+(?:[.,]\d+)?)\s*[xX]\s*(\d+(?:[.,]\d+)?)\s*mm", desc)
    if dim_pairs:
        d, l = dim_pairs[0]
        dimensions["diameter_mm"] = float(d.replace(",", "."))
        dimensions["length_mm"] = float(l.replace(",", "."))
        evidence.append({"field": "dimensions", "text": f"{d} x {l} mm"})
    else:
        single = re.findall(r"(\d+(?:[.,]\d+)?)\s*mm", desc)
        if single:
            dimensions["size_mm"] = float(single[0].replace(",", "."))
            evidence.append({"field": "dimensions", "text": f"{single[0]} mm"})

    # --- Número de furos (placas) ---
    furos = re.search(r"(\d+)\s*furos?", desc_n)
    if furos:
        dimensions["holes"] = int(furos.group(1))
        evidence.append({"field": "holes", "text": furos.group(0)})

    # --- Código de referência ---
    ref = _REF.search(desc)
    if ref:
        attributes["reference_code"] = ref.group(1).strip().upper()
        evidence.append({"field": "reference_code", "text": ref.group(0).strip()})

    # --- Fabricante ---
    manuf = _MANUF.search(desc)
    if manuf:
        # Limpa cauda comum (ex.: "OrthoMed." -> "OrthoMed").
        value = manuf.group(1).strip().rstrip(".").split(",")[0].strip()
        attributes["manufacturer"] = value
        evidence.append({"field": "manufacturer", "text": f"fabricante {value}"})

    return {"attributes": attributes, "dimensions": dimensions, "evidence": evidence}
