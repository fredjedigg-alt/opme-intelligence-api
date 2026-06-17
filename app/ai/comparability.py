"""Comparabilidade econômica entre dois itens OPME (Serviço de IA nº 3).

Distingue "mesma classe taxonômica" de "equivalência para benchmark de preço".
Dois itens só são COMPARABLE quando estão na mesma taxonomia E seus atributos
técnicos críticos (material, dimensões) são compatíveis.
"""

import sqlite3

from .classifier import classify
from .similarity import similarity


def _critical_diffs(a: dict, b: dict) -> list[str]:
    diffs = []
    if a.get("material") and b.get("material") and a["material"] != b["material"]:
        diffs.append(f"material difere ({a['material']} vs {b['material']})")
    da, db = a.get("dimensions", {}), b.get("dimensions", {})
    for key in ("diameter_mm", "length_mm", "size_mm"):
        if key in da and key in db and abs(da[key] - db[key]) > 0.01:
            diffs.append(f"{key} difere ({da[key]} vs {db[key]})")
    return diffs


def compare(item_a: str, item_b: str, conn: sqlite3.Connection) -> dict:
    ca = classify(item_a, conn, use_llm=False)
    cb = classify(item_b, conn, use_llm=False)

    same_tax = (
        ca.get("taxonomy_id") is not None
        and ca.get("taxonomy_id") == cb.get("taxonomy_id")
    )
    attr_sim = similarity(ca["canonical_name"], cb["canonical_name"])
    diffs = _critical_diffs(ca, cb)

    if same_tax and not diffs and attr_sim >= 0.6:
        decision, rationale = "COMPARABLE", "Mesma taxonomia e atributos técnicos compatíveis."
    elif same_tax and (diffs or attr_sim >= 0.4):
        decision, rationale = "REVIEW", "Mesma taxonomia, mas com diferenças técnicas a validar."
    else:
        decision, rationale = "NOT_COMPARABLE", "Taxonomias distintas ou atributos incompatíveis."

    confidence = round(min(ca["confidence"], cb["confidence"]) * (0.5 + 0.5 * attr_sim), 4)

    return {
        "item_a_canonical": ca["canonical_name"],
        "item_b_canonical": cb["canonical_name"],
        "same_taxonomy": same_tax,
        "taxonomy_a": ca.get("taxonomy_path"),
        "taxonomy_b": cb.get("taxonomy_path"),
        "attribute_similarity": attr_sim,
        "decision": decision,
        "critical_differences": diffs,
        "rationale": rationale,
        "confidence": confidence,
    }
