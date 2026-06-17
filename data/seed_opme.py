"""Seed determinístico do banco OPME.

Cria o usuário de demonstração, a taxonomia mestre (10 nós / 5 especialidades) e
observações de preço sintéticas porém realistas, com dispersão controlada e alguns
outliers propositais — para que o benchmark e a detecção de anomalias tenham o que
analisar. Tudo com `random.seed` fixo, garantindo reprodutibilidade entre máquinas.
"""

import random
import sqlite3
from datetime import date, timedelta

from app.config import get_settings
from app.security import hash_password

# (specialty, family, subfamily, canonical_label, keywords, default_uom)
TAXONOMY = [
    ("Ortopedia", "Placas", "Placa bloqueada distal rádio volar",
     "Placa bloqueada distal rádio volar",
     "placa bloqueada distal radio volar,placa volar,placa radio distal,placa bloqueada radio,placa 2.4", "unidade"),
    ("Ortopedia", "Parafusos", "Parafuso bloqueado",
     "Parafuso bloqueado",
     "parafuso bloqueado,parafuso canulado,parafuso cortical,parafuso 2.4,parafuso 3.5,parafuso travado", "unidade"),
    ("Ortopedia", "Próteses", "Prótese total de quadril",
     "Prótese total de quadril",
     "protese de quadril,protese total quadril,artroplastia quadril,haste femoral,componente acetabular", "kit"),
    ("Cardiologia", "Stents", "Stent farmacológico coronário",
     "Stent farmacológico coronário",
     "stent farmacologico,stent coronario,stent farmacologico coronario,stent eluidor,stent droga", "unidade"),
    ("Cardiologia", "Stents", "Stent coronário convencional",
     "Stent coronário convencional",
     "stent convencional,stent metalico,stent nao farmacologico,stent bare metal", "unidade"),
    ("Cardiologia", "Válvulas", "Prótese valvar aórtica transcateter",
     "Prótese valvar aórtica (TAVI)",
     "protese valvar aortica,valvula aortica,tavi,valvula cardiaca,valvula transcateter", "unidade"),
    ("Vascular", "Cateteres", "Cateter de angioplastia (balão)",
     "Cateter de angioplastia",
     "cateter de angioplastia,cateter balao,cateter pta,balao angioplastia,cateter dilatacao", "unidade"),
    ("Cirurgia Geral", "Telas", "Tela de polipropileno",
     "Tela de polipropileno",
     "tela cirurgica,tela de polipropileno,tela hernia,tela inguinal,tela hernioplastia", "unidade"),
    ("Neurocirurgia", "Derivações", "Válvula de derivação ventricular",
     "Válvula de derivação ventrículo-peritoneal",
     "valvula de derivacao,dvp,derivacao ventriculo peritoneal,shunt,valvula hidrocefalia", "unidade"),
    ("Bucomaxilo", "Placas", "Placa reta de titânio",
     "Placa reta de titânio (miniplaca)",
     "placa reta,placa bucomaxilo,miniplaca,placa l titanio,placa fixacao", "unidade"),
]

# taxonomy_id (1-based) -> (preço-base, coef. variação aproximado, nº observações)
PRICE_PROFILE = {
    1: (1200, 0.18, 22),
    2: (180, 0.22, 24),
    3: (9500, 0.15, 18),
    4: (4200, 0.30, 26),
    5: (1800, 0.20, 20),
    6: (62000, 0.12, 16),
    7: (950, 0.28, 22),
    8: (320, 0.35, 20),
    9: (2600, 0.18, 18),
    10: (540, 0.25, 20),
}

SUPPLIERS = ["MedSupply BR", "OrthoFix Dist", "CardioMed", "Hospitalar Center", "BioImplantes", "Vascular Trade"]
REGIONS = ["Centro-Oeste", "Sudeste", "Sul", "Nordeste", "Norte"]
MANUFACTURERS = ["OrthoMed", "Stryker", "Synthes", "Boston Sci", "Medtronic", "Abbott", "Nacional"]

# Outliers propositais: (taxonomy_id, fornecedor, região, multiplicador sobre a base)
OUTLIERS = [
    (4, "Hospitalar Center", "Norte", 2.4),   # stent farmacológico muito caro
    (8, "BioImplantes", "Nordeste", 2.8),      # tela muito cara
    (2, "Vascular Trade", "Norte", 0.35),      # parafuso anormalmente barato
]


def seed_database(conn: sqlite3.Connection) -> None:
    rng = random.Random(42)
    settings = get_settings()

    # --- Usuário demo ---
    conn.execute(
        "INSERT OR IGNORE INTO users (username, password_hash, role) VALUES (?, ?, ?)",
        (settings.demo_username, hash_password(settings.demo_password), "analyst"),
    )

    # --- Taxonomia ---
    conn.executemany(
        "INSERT INTO opme_taxonomy "
        "(specialty, family, subfamily, canonical_label, keywords, default_uom) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        TAXONOMY,
    )

    # --- Observações de preço ---
    today = date(2026, 6, 1)
    rows = []
    for tax_id, (base, cv, n) in PRICE_PROFILE.items():
        label = TAXONOMY[tax_id - 1][3]
        uom = TAXONOMY[tax_id - 1][5]
        for _ in range(n):
            price = max(1.0, rng.gauss(base, base * cv))
            rows.append((
                tax_id, label,
                rng.choice(SUPPLIERS), rng.choice(MANUFACTURERS),
                rng.choice(REGIONS), uom, round(price, 2),
                (today - timedelta(days=rng.randint(0, 180))).isoformat(),
            ))

    for tax_id, supplier, region, mult in OUTLIERS:
        base = PRICE_PROFILE[tax_id][0]
        label = TAXONOMY[tax_id - 1][3]
        uom = TAXONOMY[tax_id - 1][5]
        rows.append((
            tax_id, label, supplier, rng.choice(MANUFACTURERS),
            region, uom, round(base * mult, 2),
            (today - timedelta(days=rng.randint(0, 60))).isoformat(),
        ))

    conn.executemany(
        "INSERT INTO price_observation "
        "(taxonomy_id, canonical_name, supplier, manufacturer, region, "
        "uom_standard, normalized_price, observation_date) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        rows,
    )
    conn.commit()
