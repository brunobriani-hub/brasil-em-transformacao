# Modelo e medidas do Power BI

## Relacionamentos

Configure todos os relacionamentos como **um para muitos**, com direção de
filtro única da dimensão para a tabela fato.

| Dimensão | Coluna | Tabela fato | Coluna |
|---|---|---|---|
| `Dim_Estado` | `estado_id` | `Fato_Cobertura` | `estado_id` |
| `Dim_Estado` | `estado_id` | `Fato_Transicao` | `estado_id` |
| `Dim_Estado` | `estado_id` | `Fato_Focos` | `estado_id` |
| `Dim_Bioma` | `bioma_id` | `Fato_Cobertura` | `bioma_id` |
| `Dim_Bioma` | `bioma_id` | `Fato_Transicao` | `bioma_id` |
| `Dim_Classe` | `classe_id` | `Fato_Cobertura` | `classe_id` |
| `Dim_Ano` | `ano` | Todas as fatos | `ano` |
| `Dim_Mes` | `mes` | `Fato_Focos` | `mes` |

Evite relacionar as três tabelas fato diretamente entre si.

## Medidas DAX iniciais

```DAX
Área de Cobertura (ha) =
SUM ( Fato_Cobertura[area_ha] )
```

```DAX
Vegetação Natural (ha) =
CALCULATE (
    [Área de Cobertura (ha)],
    Dim_Classe[natureza] = "Natural"
)
```

```DAX
Participação Natural (%) =
DIVIDE (
    [Vegetação Natural (ha)],
    CALCULATE (
        [Área de Cobertura (ha)],
        REMOVEFILTERS ( Dim_Classe )
    )
)
```

```DAX
Conversão Natural → Antrópica (ha) =
CALCULATE (
    SUM ( Fato_Transicao[area_ha] ),
    Fato_Transicao[tipo_transicao] = "Natural → Antrópica"
)
```

```DAX
Recuperação Antrópica → Natural (ha) =
CALCULATE (
    SUM ( Fato_Transicao[area_ha] ),
    Fato_Transicao[tipo_transicao] = "Antrópica → Natural"
)
```

```DAX
Saldo de Recuperação (ha) =
[Recuperação Antrópica → Natural (ha)]
    - [Conversão Natural → Antrópica (ha)]
```

```DAX
Focos de Fogo =
SUM ( Fato_Focos[focos] )
```

```DAX
Focos no Ano Anterior =
VAR AnoAtual = SELECTEDVALUE ( Dim_Ano[ano] )
RETURN
    CALCULATE (
        [Focos de Fogo],
        FILTER ( ALL ( Dim_Ano ), Dim_Ano[ano] = AnoAtual - 1 )
    )
```

```DAX
Variação Anual de Focos (%) =
DIVIDE (
    [Focos de Fogo] - [Focos no Ano Anterior],
    [Focos no Ano Anterior]
)
```

## Páginas recomendadas

1. **Visão Geral** – KPIs, evolução e mapa por estado.
2. **Cobertura e Uso da Terra** – classes, participação e transformação desde 1985.
3. **Conversão e Recuperação** – fluxos Natural → Antrópica e Antrópica → Natural.
4. **Fogo** – sazonalidade mensal, ranking de estados e evolução desde 1998.
5. **Metodologia** – fontes, definições, limitações e fluxo de tratamento.
