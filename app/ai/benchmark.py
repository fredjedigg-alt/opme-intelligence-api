"""Benchmark de preço, dispersão e detecção de outliers (Serviço de IA nº 2).

Diferente do Serviço 1 (NLP/classificação), aqui a "inteligência" é analítica:
  - classifica a descrição para achar o grupo comparável na taxonomia;
  - recupera as observações de preço normalizadas desse grupo (filtrando região);
  - calcula estatísticas (mediana, p25/p75, desvio, coeficiente de variação);
  - sinaliza outliers pelo método do IQR (intervalo interquartil);
  - quantifica a oportunidade de economia vs. a mediana de mercado.
"""

import sqlite3
import statistics
from collections import defaultdict

from .classifier import classify


def _quantile(sorted_vals: list[float], q: float) -> float:
    """Quantil por interpolação linear (robusto p/ amostras pequenas)."""
    if not sorted_vals:
        return 0.0
    if len(sorted_vals) == 1:
        return sorted_vals[0]
    pos = q * (len(sorted_vals) - 1)
    lo = int(pos)
    frac = pos - lo
    if lo + 1 < len(sorted_vals):
        return sorted_vals[lo] + frac * (sorted_vals[lo + 1] - sorted_vals[lo])
    return sorted_vals[lo]


def _dispersion_level(cv: float) -> str:
    if cv < 0.15:
        return "baixa"
    if cv < 0.35:
        return "media"
    return "alta"


def benchmark(
    description: str,
    conn: sqlite3.Connection,
    region: str | None = None,
    reference_price: float | None = None,
) -> dict:
    """Executa o benchmark e devolve dict pronto p/ BenchmarkResponse."""
    cls = classify(description, conn, use_llm=False)
    taxonomy_id = cls.get("taxonomy_id")
    path = cls.get("taxonomy_path")

    base = {
        "raw_description": description,
        "matched_taxonomy_path": path,
        "classification_confidence": cls["confidence"],
        "comparable_basis": "taxonomia (família/subfamília) + região" if region else "taxonomia (família/subfamília)",
    }

    if not taxonomy_id:
        base["note"] = (
            "Não foi possível associar o item a um grupo comparável da taxonomia. "
            "Refine a descrição ou cadastre o item na taxonomia mestre."
        )
        return base

    query = "SELECT supplier, manufacturer, region, normalized_price FROM price_observation WHERE taxonomy_id = ?"
    params: list = [taxonomy_id]
    if region:
        query += " AND region = ?"
        params.append(region)
    rows = [dict(r) for r in conn.execute(query, params).fetchall()]

    if len(rows) < 3:
        base["note"] = (
            f"Amostra insuficiente para benchmark confiável "
            f"({len(rows)} observação(ões)). Mínimo recomendado: 3."
        )
        return base

    prices = sorted(r["normalized_price"] for r in rows)
    median = statistics.median(prices)
    mean = statistics.fmean(prices)
    std = statistics.pstdev(prices)
    p25, p75 = _quantile(prices, 0.25), _quantile(prices, 0.75)
    cv = round(std / mean, 4) if mean else 0.0

    base["stats"] = {
        "count": len(prices),
        "median": round(median, 2),
        "mean": round(mean, 2),
        "p25": round(p25, 2),
        "p75": round(p75, 2),
        "min": round(prices[0], 2),
        "max": round(prices[-1], 2),
        "std": round(std, 2),
        "coefficient_of_variation": cv,
    }
    base["dispersion_level"] = _dispersion_level(cv)

    # Outliers pelo método IQR (1.5 * intervalo interquartil).
    iqr = p75 - p25
    lo_fence, hi_fence = p25 - 1.5 * iqr, p75 + 1.5 * iqr
    outliers = []
    for r in rows:
        price = r["normalized_price"]
        if price > hi_fence:
            outliers.append({**r, "reason": "acima do limite superior (IQR)"})
        elif price < lo_fence:
            outliers.append({**r, "reason": "abaixo do limite inferior (IQR)"})
    base["outliers"] = [
        {
            "supplier": o["supplier"],
            "region": o["region"],
            "normalized_price": round(o["normalized_price"], 2),
            "reason": o["reason"],
        }
        for o in sorted(outliers, key=lambda x: x["normalized_price"], reverse=True)
    ]

    # Agrupamentos por fornecedor e por região (mediana de cada grupo).
    def _group(field: str) -> list[dict]:
        buckets: dict[str, list[float]] = defaultdict(list)
        for r in rows:
            buckets[r[field]].append(r["normalized_price"])
        return sorted(
            (
                {"key": k, "count": len(v), "median_price": round(statistics.median(v), 2)}
                for k, v in buckets.items()
            ),
            key=lambda x: x["median_price"],
        )

    base["by_supplier"] = _group("supplier")
    base["by_region"] = _group("region")

    # Oportunidade de economia vs. mediana.
    if reference_price:
        saving_abs = reference_price - median
        saving_pct = round((saving_abs / reference_price) * 100, 2) if reference_price else 0.0
        if saving_abs > 0:
            verdict = (
                f"Preço de referência {saving_pct:.1f}% acima da mediana de mercado — "
                f"há oportunidade de economia."
            )
        else:
            verdict = "Preço de referência está em linha ou abaixo da mediana de mercado."
        base["saving_opportunity"] = {
            "reference_price": round(reference_price, 2),
            "market_median": round(median, 2),
            "potential_saving_abs": round(max(saving_abs, 0.0), 2),
            "potential_saving_pct": max(saving_pct, 0.0),
            "verdict": verdict,
        }

    return base
