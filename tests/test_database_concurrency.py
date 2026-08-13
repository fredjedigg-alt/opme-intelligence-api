"""Regressão: o banco precisa estar em WAL.

A varredura do PNCP (`/tenders/scan`) segura uma transação de escrita por
dezenas de segundos. No journal padrão do SQLite, quando o cache do escritor
transborda, o lock escala para exclusivo e toda leitura concorrente falha — a
API passa a devolver 500 "database is locked", inclusive no login. Em WAL os
leitores não esperam o escritor.

Guardamos o pragma em vez de simular a concorrência: reproduzir o lock exige
forçar o transbordo do cache, o que rende um teste lento e dependente do
tamanho de página. Esta asserção falha assim que alguém remover o WAL de
`app.database.connect`, que é o jeito real de a regressão voltar.
"""

from app.database import connect


def test_wal_habilitado(client):
    with connect() as conn:
        modo = conn.execute("PRAGMA journal_mode;").fetchone()[0]
    assert (
        modo.lower() == "wal"
    ), f"journal_mode={modo}; sem WAL a varredura do PNCP derruba as leituras"


def test_busy_timeout_configurado(client):
    """Dois escritores continuam serializados; o timeout evita erro imediato."""
    with connect() as conn:
        timeout_ms = conn.execute("PRAGMA busy_timeout;").fetchone()[0]
    assert timeout_ms >= 30_000
