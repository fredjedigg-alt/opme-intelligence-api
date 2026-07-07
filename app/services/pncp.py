"""Cliente HTTP do PNCP — Portal Nacional de Contratações Públicas (Lei 14.133/2021).

O PNCP é a fonte única para licitações de TODAS as esferas (federal, estadual e
municipal), sem autenticação. Dois endpoints públicos são usados:

  1. Busca de editais recebendo propostas:
     GET {pncp_search_url}?q=<termo>&tipos_documento=edital&status=recebendo_proposta
  2. Itens de uma compra:
     GET {pncp_api_url}/orgaos/{cnpj}/compras/{ano}/{sequencial}/itens

Peculiaridades do WAF do PNCP (validadas empiricamente): exige User-Agent de
navegador e HTTP/1.1 — sem isso a conexão é resetada. Toda falha vira
`UpstreamError`, para o cliente da API receber 502 em vez de um 500 genérico.
"""

import logging
import time

import httpx

from ..config import get_settings
from ..errors import UpstreamError

logger = logging.getLogger("opme.services.pncp")

# O WAF do PNCP reseta conexões sem User-Agent de navegador.
_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"
    ),
    "Accept": "application/json",
}
_MAX_ATTEMPTS = 2
_RETRY_WAIT_SECONDS = 1.5


def _get_json(url: str, params: dict) -> dict | list:
    """GET com retry único; qualquer falha final vira UpstreamError (HTTP 502)."""
    settings = get_settings()
    last_error: Exception | None = None
    for attempt in range(1, _MAX_ATTEMPTS + 1):
        try:
            # httpx usa HTTP/1.1 por padrão (h2 só com flag no Client) — ok p/ o WAF.
            resp = httpx.get(
                url,
                params=params,
                headers=_HEADERS,
                timeout=settings.pncp_timeout_seconds,
            )
            resp.raise_for_status()
            return resp.json()
        except (
            httpx.HTTPError,
            ValueError,
        ) as exc:  # rede, HTTP >= 400 ou JSON inválido
            last_error = exc
            logger.warning(
                "pncp_request_failed url=%s attempt=%s error=%s", url, attempt, exc
            )
            if attempt < _MAX_ATTEMPTS:
                time.sleep(_RETRY_WAIT_SECONDS)
    raise UpstreamError(
        "PNCP indisponível ou lento no momento. Tente novamente em instantes.",
        {"url": url, "cause": str(last_error)},
    )


def search_open_tenders(
    term: str,
    pagina: int = 1,
    tam_pagina: int = 50,
) -> dict:
    """Busca editais com propostas em aberto no PNCP para um termo.

    Retorna o JSON bruto da busca: {"total": int, "items": [...]}.
    Cada item traz numero_controle_pncp, órgão, esfera_nome, uf, município,
    modalidade, data_fim_vigencia (prazo de propostas) e item_url.
    """
    settings = get_settings()
    return _get_json(
        settings.pncp_search_url,
        {
            "q": term,
            "tipos_documento": "edital",
            "status": "recebendo_proposta",
            "pagina": pagina,
            "tam_pagina": tam_pagina,
        },
    )


def fetch_tender_items(
    cnpj: str,
    ano: int,
    sequencial: int,
    pagina: int = 1,
    tamanho_pagina: int = 100,
) -> list[dict]:
    """Busca os itens (demandas) de uma compra específica no PNCP."""
    settings = get_settings()
    data = _get_json(
        f"{settings.pncp_api_url}/orgaos/{cnpj}/compras/{ano}/{sequencial}/itens",
        {"pagina": pagina, "tamanhoPagina": tamanho_pagina},
    )
    return data if isinstance(data, list) else []
