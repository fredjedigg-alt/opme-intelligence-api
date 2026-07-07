"""Configuração central da aplicação (12-factor): tudo vem de variáveis de ambiente.

Usamos `pydantic-settings`, que lê o arquivo `.env` automaticamente e valida tipos.
Qualquer valor possui default seguro, de modo que a API sobe sem nenhum `.env`.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # --- Aplicação ---
    app_name: str = "OPME Intelligence API"
    app_env: str = "development"
    api_v1_prefix: str = "/api/v1"

    # --- Logs ---
    log_level: str = "INFO"
    log_json: bool = True

    # --- Banco de dados ---
    database_path: str = "opme.db"

    # --- Segurança / JWT ---
    jwt_secret_key: str = (
        "troque-este-segredo-em-producao-por-uma-string-aleatoria-longa-32b+"
    )
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60

    # --- Usuário de demonstração (criado no seed) ---
    demo_username: str = "atlas"
    demo_password: str = "atlas123"

    # --- Rate limiting ---
    rate_limit_per_minute: int = 60

    # --- LLM opcional ---
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-opus-4-8"

    # --- Radar de Licitações (PNCP) ---
    pncp_search_url: str = "https://pncp.gov.br/api/search/"
    pncp_api_url: str = "https://pncp.gov.br/api/pncp/v1"
    pncp_timeout_seconds: float = 30.0
    # Termos usados na varredura quando o cliente não informa os seus.
    pncp_default_terms: str = (
        "OPME, órteses e próteses, prótese, órtese, "
        "stent, marcapasso, material especial cirúrgico"
    )

    @property
    def pncp_terms_list(self) -> list[str]:
        return [t.strip() for t in self.pncp_default_terms.split(",") if t.strip()]

    @property
    def llm_enabled(self) -> bool:
        """LLM só é considerado ativo quando há chave configurada."""
        return bool(self.anthropic_api_key.strip())


@lru_cache
def get_settings() -> Settings:
    """Cacheia as settings (lidas uma única vez por processo)."""
    return Settings()
