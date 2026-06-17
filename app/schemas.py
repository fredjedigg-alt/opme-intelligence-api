"""Schemas Pydantic — contratos de entrada e saída da API.

Requisito da disciplina: "Validação de dados". O Pydantic v2 valida tipos, limites
e formatos automaticamente; entradas inválidas resultam em HTTP 422 padronizado.
Cada modelo traz `examples`, que alimentam a documentação interativa (Swagger).
"""

from typing import Literal, Optional

from pydantic import BaseModel, Field


# --------------------------------------------------------------------------- #
# Autenticação
# --------------------------------------------------------------------------- #
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in_minutes: int


# --------------------------------------------------------------------------- #
# Serviço 1 — Classificação / extração de item OPME
# --------------------------------------------------------------------------- #
class ClassifyRequest(BaseModel):
    description: str = Field(
        ...,
        min_length=3,
        max_length=1000,
        description="Descrição livre do item OPME (como aparece em cotação/nota).",
        examples=[
            "Placa bloqueada distal rádio volar 2.4 mm titânio 6 furos, "
            "estéril, ref XZ-244, fabricante OrthoMed"
        ],
    )
    document_type: Optional[
        Literal["cotacao", "contrato", "catalogo", "nota_fiscal", "edital", "desconhecido"]
    ] = Field(default="desconhecido", description="Tipo documental de origem (opcional).")


class EvidenceSpan(BaseModel):
    field: str
    text: str


class TaxonomyCandidate(BaseModel):
    taxonomy_id: int
    path: str
    score: float = Field(..., ge=0, le=1)


class ClassifyResponse(BaseModel):
    raw_description: str
    canonical_name: str
    specialty: Optional[str] = None
    family: Optional[str] = None
    subfamily: Optional[str] = None
    taxonomy_id: Optional[int] = None
    taxonomy_path: Optional[str] = None
    material: Optional[str] = None
    sterile: Optional[bool] = None
    dimensions: dict = Field(default_factory=dict)
    reference_code: Optional[str] = None
    manufacturer: Optional[str] = None
    uom_standard: Optional[str] = None
    decision: Literal["MATCH", "REVIEW", "NO_MATCH"]
    confidence: float = Field(..., ge=0, le=1)
    candidates: list[TaxonomyCandidate] = Field(default_factory=list)
    evidence: list[EvidenceSpan] = Field(default_factory=list)
    ambiguity_note: Optional[str] = None
    engine: str = Field(..., description="Motor usado: regras+similaridade [+llm].")


# --------------------------------------------------------------------------- #
# Serviço 2 — Benchmark de preço / dispersão
# --------------------------------------------------------------------------- #
class BenchmarkRequest(BaseModel):
    description: str = Field(
        ..., min_length=3, max_length=1000,
        examples=["stent farmacológico coronário 3.0 x 18 mm"],
    )
    region: Optional[str] = Field(
        default=None, description="Filtra observações por região (ex.: 'Centro-Oeste')."
    )
    reference_price: Optional[float] = Field(
        default=None, gt=0,
        description="Preço pago/cotado para calcular economia vs. mediana de mercado.",
    )


class PriceStats(BaseModel):
    count: int
    median: float
    mean: float
    p25: float
    p75: float
    min: float
    max: float
    std: float
    coefficient_of_variation: float


class GroupStat(BaseModel):
    key: str
    count: int
    median_price: float


class Outlier(BaseModel):
    supplier: str
    region: str
    normalized_price: float
    reason: str


class SavingOpportunity(BaseModel):
    reference_price: float
    market_median: float
    potential_saving_abs: float
    potential_saving_pct: float
    verdict: str


class BenchmarkResponse(BaseModel):
    raw_description: str
    matched_taxonomy_path: Optional[str] = None
    classification_confidence: float
    comparable_basis: str
    stats: Optional[PriceStats] = None
    dispersion_level: Optional[Literal["baixa", "media", "alta"]] = None
    by_supplier: list[GroupStat] = Field(default_factory=list)
    by_region: list[GroupStat] = Field(default_factory=list)
    outliers: list[Outlier] = Field(default_factory=list)
    saving_opportunity: Optional[SavingOpportunity] = None
    note: Optional[str] = None


# --------------------------------------------------------------------------- #
# Serviço 3 — Comparabilidade entre dois itens
# --------------------------------------------------------------------------- #
class ComparabilityRequest(BaseModel):
    item_a: str = Field(..., min_length=3, max_length=1000)
    item_b: str = Field(..., min_length=3, max_length=1000)


class ComparabilityResponse(BaseModel):
    item_a_canonical: str
    item_b_canonical: str
    same_taxonomy: bool
    taxonomy_a: Optional[str] = None
    taxonomy_b: Optional[str] = None
    attribute_similarity: float = Field(..., ge=0, le=1)
    decision: Literal["COMPARABLE", "REVIEW", "NOT_COMPARABLE"]
    critical_differences: list[str] = Field(default_factory=list)
    rationale: str
    confidence: float = Field(..., ge=0, le=1)


# --------------------------------------------------------------------------- #
# Metadados
# --------------------------------------------------------------------------- #
class HealthResponse(BaseModel):
    status: str
    version: str
    environment: str
    llm_enabled: bool
    taxonomy_nodes: int
    price_observations: int


class TaxonomyNode(BaseModel):
    taxonomy_id: int
    specialty: str
    family: str
    subfamily: Optional[str] = None
    canonical_label: str
    path: str
