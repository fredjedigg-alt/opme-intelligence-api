"""Enriquecimento opcional por LLM (Claude / Anthropic).

Princípio do blueprint: o LLM NÃO decide sozinho — ele refina a saída do motor
determinístico. Esta camada é totalmente opcional e à prova de falhas:

  - se não houver ANTHROPIC_API_KEY  -> retorna None (API segue offline);
  - se a lib `anthropic` não estiver instalada -> retorna None;
  - se a chamada falhar/expirar -> loga e retorna None (fallback para regras).

Ou seja: a presença do LLM melhora a classificação, mas a ausência nunca quebra.
"""

import json
import logging

from ..config import get_settings

logger = logging.getLogger("opme.ai.llm")

_SYSTEM = (
    "Você é um classificador técnico de OPME. Não invente valores ausentes. "
    "Responda APENAS com um objeto JSON com as chaves: canonical_name (str), "
    "material (str|null), specialty (str|null), confidence (0..1), "
    "ambiguity_note (str|null). Preserve a terminologia técnica."
)


def enrich_classification(description: str, base_result: dict) -> dict | None:
    """Tenta refinar a classificação via LLM. Retorna dict parcial ou None."""
    settings = get_settings()
    if not settings.llm_enabled:
        return None

    try:
        import anthropic  # import tardio: só falha aqui se realmente formos usar
    except ImportError:
        logger.warning("anthropic_not_installed; seguindo apenas com regras+similaridade")
        return None

    try:
        client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        user = (
            f"Descrição do item: {description}\n"
            f"Extração determinística prévia: {json.dumps(base_result, ensure_ascii=False)}\n"
            "Refine o nome canônico e os atributos. Responda só com o JSON."
        )
        msg = client.messages.create(
            model=settings.anthropic_model,
            max_tokens=400,
            system=_SYSTEM,
            messages=[{"role": "user", "content": user}],
        )
        text = "".join(
            block.text for block in msg.content if getattr(block, "type", "") == "text"
        )
        # Extrai o primeiro bloco JSON da resposta.
        start, end = text.find("{"), text.rfind("}")
        if start == -1 or end == -1:
            return None
        data = json.loads(text[start : end + 1])
        logger.info("llm_enrichment_ok model=%s", settings.anthropic_model)
        return data
    except Exception as exc:  # noqa: BLE001 — fallback proposital e logado
        logger.warning("llm_enrichment_failed err=%s; usando fallback de regras", exc)
        return None
