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
    (
        "Ortopedia",
        "Placas",
        "Placa bloqueada distal rádio volar",
        "Placa bloqueada distal rádio volar",
        "placa bloqueada distal radio volar,placa volar,placa radio distal,placa bloqueada radio,placa 2.4",
        "unidade",
    ),
    (
        "Ortopedia",
        "Parafusos",
        "Parafuso bloqueado",
        "Parafuso bloqueado",
        "parafuso bloqueado,parafuso canulado,parafuso cortical,parafuso 2.4,parafuso 3.5,parafuso travado",
        "unidade",
    ),
    (
        "Ortopedia",
        "Próteses",
        "Prótese total de quadril",
        "Prótese total de quadril",
        "protese de quadril,protese total quadril,artroplastia quadril,haste femoral,componente acetabular",
        "kit",
    ),
    (
        "Cardiologia",
        "Stents",
        "Stent farmacológico coronário",
        "Stent farmacológico coronário",
        "stent farmacologico,stent coronario,stent farmacologico coronario,stent eluidor,stent droga",
        "unidade",
    ),
    (
        "Cardiologia",
        "Stents",
        "Stent coronário convencional",
        "Stent coronário convencional",
        "stent convencional,stent metalico,stent nao farmacologico,stent bare metal",
        "unidade",
    ),
    (
        "Cardiologia",
        "Válvulas",
        "Prótese valvar aórtica transcateter",
        "Prótese valvar aórtica (TAVI)",
        "protese valvar aortica,valvula aortica,tavi,valvula cardiaca,valvula transcateter",
        "unidade",
    ),
    (
        "Vascular",
        "Cateteres",
        "Cateter de angioplastia (balão)",
        "Cateter de angioplastia",
        "cateter de angioplastia,cateter balao,cateter pta,balao angioplastia,cateter dilatacao",
        "unidade",
    ),
    (
        "Cirurgia Geral",
        "Telas",
        "Tela de polipropileno",
        "Tela de polipropileno",
        "tela cirurgica,tela de polipropileno,tela hernia,tela inguinal,tela hernioplastia",
        "unidade",
    ),
    (
        "Neurocirurgia",
        "Derivações",
        "Válvula de derivação ventricular",
        "Válvula de derivação ventrículo-peritoneal",
        "valvula de derivacao,dvp,derivacao ventriculo peritoneal,shunt,valvula hidrocefalia",
        "unidade",
    ),
    (
        "Bucomaxilo",
        "Placas",
        "Placa reta de titânio",
        "Placa reta de titânio (miniplaca)",
        "placa reta,placa bucomaxilo,miniplaca,placa l titanio,placa fixacao",
        "unidade",
    ),
    # ---- Expansão (nós 11+): cobertura das demandas reais observadas no PNCP ----
    (
        "Ortopedia",
        "Próteses",
        "Prótese total de joelho",
        "Prótese total de joelho",
        "protese de joelho,protese total joelho,artroplastia joelho,artroplastia total joelho,"
        "componente femoral joelho,plato tibial,joelho revisao",
        "kit",
    ),
    (
        "Ortopedia",
        "Próteses",
        "Prótese parcial de quadril",
        "Prótese parcial de quadril (hemiartroplastia)",
        "protese parcial quadril,hemiartroplastia,protese bipolar,protese unipolar quadril",
        "kit",
    ),
    (
        "Ortopedia",
        "Hastes",
        "Haste intramedular",
        "Haste intramedular bloqueada",
        "haste intramedular,haste femoral bloqueada,haste tibial,haste umeral,haste bloqueada",
        "unidade",
    ),
    (
        "Ortopedia",
        "Fixadores",
        "Fixador externo",
        "Fixador externo",
        "fixador externo,fixador ilizarov,fixador monoplanar,fixador circular",
        "kit",
    ),
    (
        "Ortopedia",
        "Âncoras",
        "Âncora de sutura",
        "Âncora de sutura",
        "ancora de sutura,ancora titanio,ancora absorvivel,ancora metalica,reparo manguito rotador",
        "unidade",
    ),
    (
        "Ortopedia",
        "Cimentos",
        "Cimento ósseo",
        "Cimento ósseo (PMMA)",
        "cimento osseo,cimento ortopedico,pmma,cimento com antibiotico,espacador de cimento",
        "unidade",
    ),
    (
        "Coluna",
        "Parafusos",
        "Parafuso pedicular",
        "Parafuso pedicular",
        "parafuso pedicular,parafuso poliaxial,parafuso monoaxial,fixacao pedicular,parafuso coluna",
        "unidade",
    ),
    (
        "Coluna",
        "Cages",
        "Cage intersomático",
        "Cage intersomático",
        "cage intersomatico,cage cervical,cage lombar,dispositivo intersomatico,cage peek,plif,tlif",
        "unidade",
    ),
    (
        "Coluna",
        "Placas",
        "Placa cervical anterior",
        "Placa cervical anterior",
        "placa cervical,placa cervical anterior,placa coluna cervical",
        "unidade",
    ),
    (
        "Cardiologia",
        "Marcapassos",
        "Marcapasso definitivo",
        "Marcapasso definitivo",
        "marcapasso,marca-passo,marcapasso dupla camara,marcapasso camara unica,gerador de pulso,"
        "marcapasso definitivo",
        "unidade",
    ),
    (
        "Cardiologia",
        "Marcapassos",
        "Cardiodesfibrilador implantável",
        "Cardiodesfibrilador implantável (CDI)",
        "cardiodesfibrilador,cdi,desfibrilador implantavel,cardioversor desfibrilador,ressincronizador",
        "unidade",
    ),
    (
        "Cardiologia",
        "Eletrodos",
        "Eletrodo de marcapasso",
        "Eletrodo endocárdico de marcapasso",
        "eletrodo marcapasso,eletrodo endocardico,cabo eletrodo,eletrodo atrial,eletrodo ventricular",
        "unidade",
    ),
    (
        "Cardiologia",
        "Oclusores",
        "Oclusor septal",
        "Oclusor septal (prótese oclusora)",
        "oclusor,oclusor septal,protese oclusora,oclusor cia,oclusor civ,amplatzer",
        "unidade",
    ),
    (
        "Vascular",
        "Endopróteses",
        "Endoprótese aórtica",
        "Endoprótese aórtica (stent graft)",
        "endoprotese,endoprotese aortica,stent graft,endoprotese abdominal,endoprotese toracica,evar,tevar",
        "unidade",
    ),
    (
        "Vascular",
        "Stents",
        "Stent periférico",
        "Stent periférico autoexpansível",
        "stent periferico,stent carotideo,stent iliaco,stent femoral,stent autoexpansivel,stent renal",
        "unidade",
    ),
    (
        "Vascular",
        "Filtros",
        "Filtro de veia cava",
        "Filtro de veia cava",
        "filtro veia cava,filtro de vena cava,filtro cava",
        "unidade",
    ),
    (
        "Vascular",
        "Introdutores",
        "Introdutor valvulado",
        "Introdutor valvulado",
        "introdutor,introdutor valvulado,bainha introdutora,kit introdutor",
        "unidade",
    ),
    (
        "Vascular",
        "Guias",
        "Fio guia hidrofílico",
        "Fio guia hidrofílico",
        "fio guia,guia hidrofilico,corda guia,fio guia metalico",
        "unidade",
    ),
    (
        "Neurocirurgia",
        "Clipes",
        "Clipe de aneurisma",
        "Clipe de aneurisma",
        "clipe aneurisma,clip de aneurisma,clipe yasargil,clipe neurocirurgico",
        "unidade",
    ),
    (
        "Neurocirurgia",
        "Estimuladores",
        "Estimulador medular",
        "Estimulador medular implantável",
        "estimulador medular,neuroestimulador,eletrodo de estimulacao medular,gerador neuroestimulacao",
        "kit",
    ),
    (
        "Oftalmologia",
        "Lentes",
        "Lente intraocular",
        "Lente intraocular (LIO)",
        "lente intraocular,lio,lente dobravel,lente acrilica,facectomia,catarata lente,lente camara posterior",
        "unidade",
    ),
    (
        "Urologia",
        "Cateteres",
        "Cateter duplo J",
        "Cateter duplo J",
        "cateter duplo j,duplo jota,cateter ureteral,stent ureteral",
        "unidade",
    ),
    (
        "Urologia",
        "Slings",
        "Sling suburetral",
        "Sling suburetral",
        "sling,faixa suburetral,sling masculino,sling feminino,esfincter urinario artificial",
        "unidade",
    ),
    (
        "Cirurgia Geral",
        "Grampeadores",
        "Grampeador cirúrgico e cargas",
        "Grampeador cirúrgico (linear/circular) e cargas",
        "grampeador linear,grampeador cortador,grampeador circular,carga grampeador,carga linear,"
        "grampeador endoscopico",
        "unidade",
    ),
    (
        "Cirurgia Geral",
        "Clipes",
        "Clipe para videocirurgia",
        "Clipe de titânio/polímero para videocirurgia",
        "clipe titanio,clipador,grampo de titanio,clipe polimerico,clipe hem-o-lok,clipe metalico cirurgico",
        "unidade",
    ),
    (
        "Cirurgia Geral",
        "Trocartes",
        "Trocarte para videocirurgia",
        "Trocarte para videocirurgia",
        "trocarte,trocater,canula de videocirurgia,trocarte descartavel,trocarte 5mm,trocarte 10mm,"
        "trocarte 12mm",
        "unidade",
    ),
    (
        "Reconstrução",
        "Mama",
        "Prótese mamária de silicone",
        "Prótese mamária de silicone",
        "protese mamaria,implante mamario,protese de silicone,gel de silicone,protese mama reconstrucao",
        "unidade",
    ),
    (
        "Reconstrução",
        "Mama",
        "Expansor tecidual",
        "Expansor tecidual mamário",
        "expansor tecidual,expansor mamario,expansor de pele,expansor para reconstrucao mamaria",
        "unidade",
    ),
    (
        "Otorrino",
        "Implantes",
        "Implante coclear",
        "Implante coclear",
        "implante coclear,processador de fala,implante auditivo,protese auditiva ancorada",
        "kit",
    ),
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
    # ---- Expansão (nós 11+) — preços-base plausíveis em BRL ----
    11: (12000, 0.18, 18),  # prótese total de joelho
    12: (6500, 0.20, 16),  # prótese parcial de quadril
    13: (3800, 0.22, 18),  # haste intramedular
    14: (4500, 0.30, 14),  # fixador externo
    15: (900, 0.25, 20),  # âncora de sutura
    16: (850, 0.25, 18),  # cimento ósseo
    17: (1100, 0.22, 24),  # parafuso pedicular
    18: (4200, 0.25, 18),  # cage intersomático
    19: (3500, 0.20, 14),  # placa cervical anterior
    20: (12000, 0.25, 18),  # marcapasso definitivo
    21: (45000, 0.20, 12),  # CDI
    22: (2800, 0.25, 16),  # eletrodo de marcapasso
    23: (18000, 0.22, 10),  # oclusor septal
    24: (55000, 0.18, 12),  # endoprótese aórtica
    25: (6500, 0.25, 18),  # stent periférico
    26: (7500, 0.20, 10),  # filtro de veia cava
    27: (350, 0.30, 24),  # introdutor valvulado
    28: (480, 0.30, 22),  # fio guia hidrofílico
    29: (3200, 0.20, 12),  # clipe de aneurisma
    30: (95000, 0.15, 8),  # estimulador medular
    31: (1500, 0.35, 26),  # lente intraocular
    32: (380, 0.30, 22),  # cateter duplo J
    33: (4800, 0.25, 10),  # sling suburetral
    34: (2900, 0.30, 20),  # grampeador e cargas
    35: (650, 0.30, 18),  # clipe videocirurgia
    36: (780, 0.30, 18),  # trocarte
    37: (3200, 0.25, 16),  # prótese mamária
    38: (4200, 0.22, 12),  # expansor tecidual
    39: (78000, 0.12, 8),  # implante coclear
}

SUPPLIERS = [
    "MedSupply BR",
    "OrthoFix Dist",
    "CardioMed",
    "Hospitalar Center",
    "BioImplantes",
    "Vascular Trade",
]
REGIONS = ["Centro-Oeste", "Sudeste", "Sul", "Nordeste", "Norte"]
MANUFACTURERS = [
    "OrthoMed",
    "Stryker",
    "Synthes",
    "Boston Sci",
    "Medtronic",
    "Abbott",
    "Nacional",
]

# Outliers propositais: (taxonomy_id, fornecedor, região, multiplicador sobre a base)
OUTLIERS = [
    (4, "Hospitalar Center", "Norte", 2.4),  # stent farmacológico muito caro
    (8, "BioImplantes", "Nordeste", 2.8),  # tela muito cara
    (2, "Vascular Trade", "Norte", 0.35),  # parafuso anormalmente barato
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
            rows.append(
                (
                    tax_id,
                    label,
                    rng.choice(SUPPLIERS),
                    rng.choice(MANUFACTURERS),
                    rng.choice(REGIONS),
                    uom,
                    round(price, 2),
                    (today - timedelta(days=rng.randint(0, 180))).isoformat(),
                )
            )

    for tax_id, supplier, region, mult in OUTLIERS:
        base = PRICE_PROFILE[tax_id][0]
        label = TAXONOMY[tax_id - 1][3]
        uom = TAXONOMY[tax_id - 1][5]
        rows.append(
            (
                tax_id,
                label,
                supplier,
                rng.choice(MANUFACTURERS),
                region,
                uom,
                round(base * mult, 2),
                (today - timedelta(days=rng.randint(0, 60))).isoformat(),
            )
        )

    conn.executemany(
        "INSERT INTO price_observation "
        "(taxonomy_id, canonical_name, supplier, manufacturer, region, "
        "uom_standard, normalized_price, observation_date) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        rows,
    )
    conn.commit()
