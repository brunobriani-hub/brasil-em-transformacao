"""Prepara as bases do projeto Brasil em Transformação para o Power BI.

Fontes:
- MapBiomas Brasil, Coleção 11: cobertura e transições de uso da terra.
- INPE Programa Queimadas: histórico mensal de focos pelo satélite de referência.

O script baixa os arquivos brutos, valida totais e produz tabelas CSV em modelo
estrela. O recorte final termina em 2025 para utilizar somente anos completos e
compatíveis entre as fontes.
"""

from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path
from urllib.request import Request, urlopen

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
RAW_MAPBIOMAS = ROOT / "dados" / "brutos" / "mapbiomas"
RAW_INPE = ROOT / "dados" / "brutos" / "inpe"
PROCESSED = ROOT / "dados" / "tratados"

MAPBIOMAS_URL = (
    "https://brasil.mapbiomas.org/wp-content/uploads/sites/3/2026/08/"
    "MAPBIOMAS_BRAZIL-COL.11-BIOME_STATE.xlsx"
)
MAPBIOMAS_FILE = RAW_MAPBIOMAS / "MAPBIOMAS_BRAZIL-COL.11-BIOME_STATE.xlsx"
INPE_BASE_URL = (
    "https://data.inpe.br/queimadas/portal/csv/download/"
    "historico-mensal/estados/{slug}.csv"
)

ESTADOS = [
    (12, "AC", "Acre", "Norte", "acre"),
    (27, "AL", "Alagoas", "Nordeste", "alagoas"),
    (16, "AP", "Amapá", "Norte", "amapa"),
    (13, "AM", "Amazonas", "Norte", "amazonas"),
    (29, "BA", "Bahia", "Nordeste", "bahia"),
    (23, "CE", "Ceará", "Nordeste", "ceara"),
    (53, "DF", "Distrito Federal", "Centro-Oeste", "distrito_federal"),
    (32, "ES", "Espírito Santo", "Sudeste", "espirito_santo"),
    (52, "GO", "Goiás", "Centro-Oeste", "goias"),
    (21, "MA", "Maranhão", "Nordeste", "maranhao"),
    (51, "MT", "Mato Grosso", "Centro-Oeste", "mato_grosso"),
    (50, "MS", "Mato Grosso do Sul", "Centro-Oeste", "mato_grosso_do_sul"),
    (31, "MG", "Minas Gerais", "Sudeste", "minas_gerais"),
    (15, "PA", "Pará", "Norte", "para"),
    (25, "PB", "Paraíba", "Nordeste", "paraiba"),
    (41, "PR", "Paraná", "Sul", "parana"),
    (26, "PE", "Pernambuco", "Nordeste", "pernambuco"),
    (22, "PI", "Piauí", "Nordeste", "piaui"),
    (33, "RJ", "Rio de Janeiro", "Sudeste", "rio_de_janeiro"),
    (24, "RN", "Rio Grande do Norte", "Nordeste", "rio_grande_do_norte"),
    (43, "RS", "Rio Grande do Sul", "Sul", "rio_grande_do_sul"),
    (11, "RO", "Rondônia", "Norte", "rondonia"),
    (14, "RR", "Roraima", "Norte", "roraima"),
    (42, "SC", "Santa Catarina", "Sul", "santa_catarina"),
    (35, "SP", "São Paulo", "Sudeste", "sao_paulo"),
    (28, "SE", "Sergipe", "Nordeste", "sergipe"),
    (17, "TO", "Tocantins", "Norte", "tocantins"),
]

BIOMAS = [
    (1, "Amazônia"),
    (2, "Caatinga"),
    (3, "Cerrado"),
    (4, "Mata Atlântica"),
    (5, "Pampa"),
    (6, "Pantanal"),
]

MESES = [
    (1, "Janeiro"),
    (2, "Fevereiro"),
    (3, "Março"),
    (4, "Abril"),
    (5, "Maio"),
    (6, "Junho"),
    (7, "Julho"),
    (8, "Agosto"),
    (9, "Setembro"),
    (10, "Outubro"),
    (11, "Novembro"),
    (12, "Dezembro"),
]


def baixar(url: str, destino: Path) -> None:
    """Baixa um arquivo público somente quando ele ainda não existe."""
    if destino.exists() and destino.stat().st_size > 0:
        return
    destino.parent.mkdir(parents=True, exist_ok=True)
    requisicao = Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urlopen(requisicao, timeout=180) as resposta:
        destino.write_bytes(resposta.read())


def sem_acentos(texto: str) -> str:
    normalizado = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in normalizado if not unicodedata.combining(c))


def salvar_csv(df: pd.DataFrame, nome: str) -> None:
    PROCESSED.mkdir(parents=True, exist_ok=True)
    df.to_csv(PROCESSED / nome, index=False, encoding="utf-8-sig")


def dimensoes_basicas() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    dim_estado = pd.DataFrame(
        ESTADOS, columns=["estado_id", "uf", "estado", "regiao", "slug"]
    ).drop(columns="slug")
    dim_bioma = pd.DataFrame(BIOMAS, columns=["bioma_id", "bioma"])
    dim_mes = pd.DataFrame(MESES, columns=["mes", "mes_nome"])
    dim_mes["trimestre"] = "T" + (((dim_mes["mes"] - 1) // 3) + 1).astype(str)
    dim_mes["semestre"] = "S" + (((dim_mes["mes"] - 1) // 6) + 1).astype(str)
    dim_ano = pd.DataFrame({"ano": range(1985, 2026)})
    dim_ano["decada"] = (dim_ano["ano"] // 10 * 10).astype(str) + "s"
    dim_ano["tem_cobertura"] = True
    dim_ano["tem_focos"] = dim_ano["ano"].between(1998, 2025)
    return dim_estado, dim_bioma, dim_mes, dim_ano


def tratar_mapbiomas(
    dim_estado: pd.DataFrame, dim_bioma: pd.DataFrame
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    cobertura = pd.read_excel(
        MAPBIOMAS_FILE, sheet_name="COVERAGE_11", engine="openpyxl"
    )
    cobertura.columns = [str(c).strip() for c in cobertura.columns]
    cobertura["class"] = pd.to_numeric(cobertura["class"], errors="raise").astype(int)

    legenda = pd.read_excel(
        MAPBIOMAS_FILE,
        sheet_name="LEGEND_CODE",
        header=2,
        usecols="A:D",
        engine="openpyxl",
    )
    legenda.columns = ["classe_pt", "classe_en", "classe_id", "cor_hex"]
    legenda["classe_id"] = pd.to_numeric(legenda["classe_id"], errors="coerce")
    legenda = legenda.dropna(subset=["classe_id"]).copy()
    legenda["classe_id"] = legenda["classe_id"].astype(int)
    legenda["classe_pt"] = legenda["classe_pt"].astype(str).str.strip()
    legenda["classe_en"] = legenda["classe_en"].astype(str).str.strip()
    legenda = legenda.drop_duplicates("classe_id")

    classe_cols = [
        "class",
        "class_level_0",
        "class_level_1",
        "class_level_2",
        "class_level_3",
        "class_level_4",
    ]
    dim_classe = cobertura[classe_cols].drop_duplicates("class").copy()
    dim_classe = dim_classe.rename(
        columns={
            "class": "classe_id",
            "class_level_0": "natureza_en",
            "class_level_1": "nivel_1_en",
            "class_level_2": "nivel_2_en",
            "class_level_3": "nivel_3_en",
            "class_level_4": "nivel_4_en",
        }
    )
    dim_classe = dim_classe.merge(legenda, on="classe_id", how="left")
    dim_classe["natureza"] = dim_classe["natureza_en"].map(
        {"Natural": "Natural", "Antropic": "Antrópica", "Undefined": "Não observado"}
    )
    dim_classe.loc[dim_classe["classe_id"] == 0, "classe_pt"] = "Não observado"
    dim_classe.loc[dim_classe["classe_id"] == 0, "classe_en"] = "Not observed"
    dim_classe.loc[dim_classe["classe_id"] == 0, "cor_hex"] = "#FFFFFF"
    # A classe 13 está presente na tabela de estatísticas da Coleção 11, mas não
    # consta no CSV oficial de códigos da legenda publicado com a coleção.
    # Mantemos o nome descritivo informado na própria tabela de cobertura e
    # deixamos a cor vazia, evitando atribuir uma cor oficial inexistente.
    dim_classe.loc[dim_classe["classe_id"] == 13, "classe_pt"] = (
        "Mosaico Herbáceo-Arbustivo"
    )
    dim_classe.loc[dim_classe["classe_id"] == 13, "classe_en"] = (
        "Herbaceous-Shrub Mosaic"
    )
    dim_classe = dim_classe[
        [
            "classe_id",
            "classe_pt",
            "classe_en",
            "natureza",
            "nivel_1_en",
            "nivel_2_en",
            "nivel_3_en",
            "nivel_4_en",
            "cor_hex",
        ]
    ].sort_values("classe_id")

    estado_id = dim_estado.set_index("estado")["estado_id"].to_dict()
    bioma_id = dim_bioma.set_index("bioma")["bioma_id"].to_dict()
    anos = [c for c in cobertura.columns if re.fullmatch(r"y\d{4}", c)]
    fato_cobertura = cobertura.melt(
        id_vars=["biome", "state", "class"],
        value_vars=anos,
        var_name="ano",
        value_name="area_ha",
    )
    fato_cobertura["ano"] = fato_cobertura["ano"].str[1:].astype(int)
    fato_cobertura["estado_id"] = fato_cobertura["state"].map(estado_id)
    fato_cobertura["bioma_id"] = fato_cobertura["biome"].map(bioma_id)
    fato_cobertura = fato_cobertura.rename(columns={"class": "classe_id"})
    fato_cobertura["area_ha"] = pd.to_numeric(
        fato_cobertura["area_ha"], errors="coerce"
    ).fillna(0).round(2)
    fato_cobertura = fato_cobertura[
        ["estado_id", "bioma_id", "classe_id", "ano", "area_ha"]
    ].sort_values(["ano", "estado_id", "bioma_id", "classe_id"])

    assert fato_cobertura[["estado_id", "bioma_id"]].notna().all().all()
    assert fato_cobertura["area_ha"].ge(0).all()
    assert not fato_cobertura.duplicated(
        ["estado_id", "bioma_id", "classe_id", "ano"]
    ).any()

    transicao = pd.read_excel(
        MAPBIOMAS_FILE, sheet_name="TRANSITION_11", engine="openpyxl"
    )
    transicao.columns = [str(c).strip() for c in transicao.columns]
    periodos_anuais = []
    for coluna in transicao.columns:
        match = re.fullmatch(r"p(\d{4})_(\d{4})", coluna)
        if match and int(match.group(2)) == int(match.group(1)) + 1:
            periodos_anuais.append(coluna)

    fato_transicao = transicao.melt(
        id_vars=["biome", "state", "class_from", "class_to"],
        value_vars=periodos_anuais,
        var_name="periodo",
        value_name="area_ha",
    )
    fato_transicao["classe_origem_id"] = pd.to_numeric(
        fato_transicao["class_from"], errors="raise"
    ).astype(int)
    fato_transicao["classe_destino_id"] = pd.to_numeric(
        fato_transicao["class_to"], errors="raise"
    ).astype(int)
    natureza = dim_classe.set_index("classe_id")["natureza"].to_dict()
    fato_transicao["natureza_origem"] = fato_transicao["classe_origem_id"].map(natureza)
    fato_transicao["natureza_destino"] = fato_transicao["classe_destino_id"].map(natureza)
    pares = {
        ("Natural", "Antrópica"): "Natural → Antrópica",
        ("Antrópica", "Natural"): "Antrópica → Natural",
    }
    fato_transicao["tipo_transicao"] = [
        pares.get((origem, destino))
        for origem, destino in zip(
            fato_transicao["natureza_origem"],
            fato_transicao["natureza_destino"],
        )
    ]
    fato_transicao = fato_transicao.dropna(subset=["tipo_transicao"]).copy()
    fato_transicao["ano"] = fato_transicao["periodo"].str[-4:].astype(int)
    fato_transicao["estado_id"] = fato_transicao["state"].map(estado_id)
    fato_transicao["bioma_id"] = fato_transicao["biome"].map(bioma_id)
    fato_transicao["area_ha"] = pd.to_numeric(
        fato_transicao["area_ha"], errors="coerce"
    ).fillna(0)
    fato_transicao = (
        fato_transicao.groupby(
            ["estado_id", "bioma_id", "ano", "tipo_transicao"], as_index=False
        )["area_ha"]
        .sum()
        .sort_values(["ano", "estado_id", "bioma_id", "tipo_transicao"])
    )
    fato_transicao["area_ha"] = fato_transicao["area_ha"].round(2)
    assert fato_transicao["area_ha"].ge(0).all()
    assert not fato_transicao.duplicated(
        ["estado_id", "bioma_id", "ano", "tipo_transicao"]
    ).any()
    return fato_cobertura, fato_transicao, dim_classe


def tratar_focos(dim_estado: pd.DataFrame) -> pd.DataFrame:
    nomes_meses = [nome for _, nome in MESES]
    frames = []
    for estado_id, _, estado, _, slug in ESTADOS:
        arquivo = RAW_INPE / f"{slug}.csv"
        baixar(INPE_BASE_URL.format(slug=slug), arquivo)
        dados = pd.read_csv(arquivo, encoding="utf-8-sig")
        dados.columns = [str(c).strip() for c in dados.columns]
        dados["Ano"] = pd.to_numeric(dados["Ano"], errors="coerce")
        dados = dados[dados["Ano"].between(1998, 2025)].copy()
        dados["Ano"] = dados["Ano"].astype(int)
        for mes in nomes_meses + ["Total"]:
            dados[mes] = pd.to_numeric(dados[mes], errors="coerce").fillna(0).astype(int)
        soma_meses = dados[nomes_meses].sum(axis=1)
        if not soma_meses.equals(dados["Total"]):
            divergencias = int((soma_meses != dados["Total"]).sum())
            raise ValueError(f"{estado}: {divergencias} totais anuais divergentes no INPE")
        longo = dados.melt(
            id_vars="Ano",
            value_vars=nomes_meses,
            var_name="mes_nome",
            value_name="focos",
        )
        longo["estado_id"] = estado_id
        frames.append(longo)

    fato_focos = pd.concat(frames, ignore_index=True)
    mes_numero = {nome: numero for numero, nome in MESES}
    fato_focos["mes"] = fato_focos["mes_nome"].map(mes_numero).astype(int)
    fato_focos = fato_focos.rename(columns={"Ano": "ano"})
    fato_focos["data"] = pd.to_datetime(
        dict(year=fato_focos["ano"], month=fato_focos["mes"], day=1)
    ).dt.strftime("%Y-%m-%d")
    fato_focos = fato_focos[
        ["estado_id", "ano", "mes", "data", "focos"]
    ].sort_values(["ano", "mes", "estado_id"])
    assert fato_focos["focos"].ge(0).all()
    assert not fato_focos.duplicated(["estado_id", "ano", "mes"]).any()
    assert set(fato_focos["estado_id"]) == set(dim_estado["estado_id"])
    return fato_focos


def main() -> None:
    for pasta in (RAW_MAPBIOMAS, RAW_INPE, PROCESSED):
        pasta.mkdir(parents=True, exist_ok=True)

    baixar(MAPBIOMAS_URL, MAPBIOMAS_FILE)
    dim_estado, dim_bioma, dim_mes, dim_ano = dimensoes_basicas()
    fato_cobertura, fato_transicao, dim_classe = tratar_mapbiomas(
        dim_estado, dim_bioma
    )
    fato_focos = tratar_focos(dim_estado)

    tabelas = {
        "dim_estado.csv": dim_estado,
        "dim_bioma.csv": dim_bioma,
        "dim_mes.csv": dim_mes,
        "dim_ano.csv": dim_ano,
        "dim_classe.csv": dim_classe,
        "fato_cobertura.csv": fato_cobertura,
        "fato_transicao.csv": fato_transicao,
        "fato_focos.csv": fato_focos,
    }
    for nome, tabela in tabelas.items():
        salvar_csv(tabela, nome)

    resumo = {
        "periodo_cobertura": [
            int(fato_cobertura["ano"].min()),
            int(fato_cobertura["ano"].max()),
        ],
        "periodo_focos": [int(fato_focos["ano"].min()), int(fato_focos["ano"].max())],
        "linhas": {nome: int(len(tabela)) for nome, tabela in tabelas.items()},
        "total_focos_1998_2025": int(fato_focos["focos"].sum()),
        "area_natural_para_antropica_ha": round(
            float(
                fato_transicao.loc[
                    fato_transicao["tipo_transicao"] == "Natural → Antrópica",
                    "area_ha",
                ].sum()
            ),
            2,
        ),
        "area_antropica_para_natural_ha": round(
            float(
                fato_transicao.loc[
                    fato_transicao["tipo_transicao"] == "Antrópica → Natural",
                    "area_ha",
                ].sum()
            ),
            2,
        ),
        "fontes": {
            "mapbiomas": MAPBIOMAS_URL,
            "inpe": "https://data.inpe.br/queimadas/estatisticas/?tipo=estados",
        },
    }
    (PROCESSED / "resumo_qualidade.json").write_text(
        json.dumps(resumo, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(resumo, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
