"""Classificador taxonômico híbrido OPME (Serviço de IA nº 1).

Pipeline (espelha o blueprint da Atlas Health):
  1) regras determinísticas  -> extrai atributos/dimensões/evidências;
  2) recuperação de candidatos -> similaridade contra a taxonomia mestre;
  3) decisão                  -> MATCH / REVIEW / NO_MATCH por limiar de confiança;
  4) (opcional) LLM           -> refina nome canônico e atributos, com fallback.

A confiança final combina a força da melhor correspondência com a margem em relação
ao segundo candidato (separabilidade), penalizando casos ambíguos.
"""

import logging
import sqlite3

from .extractor import extract_attributes
from .llm import enrich_classification
from .similarity import similarity

logger = logging.getLogger("opme.ai.classifier")

_MATCH_THRESHOLD = 0.45
_REVIEW_THRESHOLD = 0.25
_TOP_K = 3


def _load_taxonomy(conn: sqlite3.Connection) -> list[dict]:
    rows = conn.execute(
        "SELECT taxonomy_id, specialty, family, subfamily, canonical_label, "
        "keywords, default_uom FROM opme_taxonomy"
    ).fetchall()
    return [dict(r) for r in rows]


def _path(node: dict) -> str:
    parts = [node["specialty"], node["family"]]
    if node.get("subfamily"):
        parts.append(node["subfamily"])
    return " > ".join(p.upper() for p in parts if p)


def _score_node(description: str, node: dict) -> float:
    """Score de aderência: melhor entre o rótulo canônico e cada keyword."""
    target_label = f"{node['family']} {node.get('subfamily') or ''} {node['canonical_label']}"
    best = similarity(description, target_label)
    for kw in node["keywords"].split(","):
        kw = kw.strip()
        if kw:
            best = max(best, similarity(description, kw))
    return round(best, 4)


def _build_canonical(description: str, attrs: dict, dims: dict, node: dict | None) -> str:
    """Monta um nome canônico curto a partir de família + atributos extraídos."""
    if node:
        base = node["canonical_label"]
    else:
        base = description.strip()[:60]
    extra = []
    if dims.get("diameter_mm") and dims.get("length_mm"):
        extra.append(f"{dims['diameter_mm']}x{dims['length_mm']}mm")
    elif dims.get("size_mm"):
        extra.append(f"{dims['size_mm']}mm")
    if dims.get("holes"):
        extra.append(f"{dims['holes']} furos")
    # Só anexa o material se ele ainda não estiver presente no rótulo base.
    if attrs.get("material") and attrs["material"].lower() not in base.lower():
        extra.append(attrs["material"])
    return (base + (" " + " ".join(extra) if extra else "")).strip()


def classify(description: str, conn: sqlite3.Connection, use_llm: bool = True) -> dict:
    """Classifica uma descrição OPME e devolve o dicionário pronto p/ ClassifyResponse."""
    extracted = extract_attributes(description)
    attrs, dims = extracted["attributes"], extracted["dimensions"]
    evidence = list(extracted["evidence"])

    taxonomy = _load_taxonomy(conn)
    scored = sorted(
        ({"node": n, "score": _score_node(description, n)} for n in taxonomy),
        key=lambda x: x["score"],
        reverse=True,
    )
    top = scored[:_TOP_K]
    best = top[0] if top else None
    best_score = best["score"] if best else 0.0
    second_score = top[1]["score"] if len(top) > 1 else 0.0

    # Decisão por limiar + separabilidade.
    if best_score >= _MATCH_THRESHOLD:
        decision = "MATCH"
    elif best_score >= _REVIEW_THRESHOLD:
        decision = "REVIEW"
    else:
        decision = "NO_MATCH"

    margin = best_score - second_score
    # Confiança: força do melhor candidato, ajustada pela margem de separação.
    confidence = round(min(1.0, best_score * (0.7 + 0.3 * min(margin / 0.2, 1.0))), 4)
    if decision == "NO_MATCH":
        confidence = round(best_score, 4)

    node = best["node"] if (best and decision != "NO_MATCH") else None
    ambiguity_note = None
    if decision == "REVIEW":
        ambiguity_note = (
            "Baixa separabilidade entre candidatos — recomenda-se revisão humana."
        )

    canonical = _build_canonical(description, attrs, dims, node)
    engine = "regras+similaridade"

    result = {
        "raw_description": description,
        "canonical_name": canonical,
        "specialty": node["specialty"] if node else None,
        "family": node["family"] if node else None,
        "subfamily": node.get("subfamily") if node else None,
        "taxonomy_id": node["taxonomy_id"] if node else None,
        "taxonomy_path": _path(node) if node else None,
        "material": attrs.get("material"),
        "sterile": attrs.get("sterile"),
        "dimensions": dims,
        "reference_code": attrs.get("reference_code"),
        "manufacturer": attrs.get("manufacturer"),
        "uom_standard": node.get("default_uom") if node else None,
        "decision": decision,
        "confidence": confidence,
        "candidates": [
            {"taxonomy_id": c["node"]["taxonomy_id"], "path": _path(c["node"]), "score": c["score"]}
            for c in top
        ],
        "evidence": evidence,
        "ambiguity_note": ambiguity_note,
        "engine": engine,
    }

    # Etapa opcional de LLM (refina sem nunca quebrar).
    if use_llm:
        refined = enrich_classification(description, {
            "canonical_name": canonical,
            "material": attrs.get("material"),
            "specialty": result["specialty"],
        })
        if refined:
            if refined.get("canonical_name"):
                result["canonical_name"] = refined["canonical_name"]
            if refined.get("material") and not result["material"]:
                result["material"] = refined["material"]
            if refined.get("ambiguity_note"):
                result["ambiguity_note"] = refined["ambiguity_note"]
            result["engine"] = "regras+similaridade+llm"

    return result
