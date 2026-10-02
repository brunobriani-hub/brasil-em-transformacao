# Brasil em Transformação

[📊 Acessar dashboard no Power BI](https://app.powerbi.com/view?r=eyJrIjoiOTc0N2UzNDQtNWUyZC00OWUzLTk5ZTAtMTkzYzdlN2I2NjJhIiwidCI6IjJjZjdkNGQ1LWJkMWItNDk1Ni1hY2Y4LTI5OTUzOTliMjE2OCJ9)


Projeto de portfólio em análise de dados ambientais para explorar mudanças na
cobertura e no uso da terra, transições entre cobertura natural e antrópica e
focos ativos de fogo no Brasil.

## Tecnologias demonstradas

- Python e pandas para coleta, transformação e validação;
- modelagem dimensional em esquema estrela;
- Power BI, Power Query e DAX;
- análise temporal e territorial;
- comunicação visual e documentação técnica.

## Fontes oficiais

- MapBiomas Brasil – Coleção 11, cobertura e uso da terra por bioma e estado,
  1985–2025: https://brasil.mapbiomas.org/downloads/estatisticas/
- INPE – Programa Queimadas, histórico mensal de focos pelo satélite de
  referência, 1998–2025:
  https://data.inpe.br/queimadas/estatisticas/?tipo=estados

O ano de 2026 não foi incluído nas tabelas tratadas porque ainda está incompleto.

## Como executar no Visual Studio Code

1. Abra esta pasta no VS Code.
2. Crie e ative um ambiente virtual.
3. Instale as dependências: `pip install -r requirements.txt`.
4. Execute: `python src/coletar_tratar_dados.py`.
5. Importe os CSVs de `dados/tratados` no Power BI.

O script baixa as bases brutas apenas quando elas ainda não existem, valida os
totais mensais do INPE e cria as tabelas tratadas novamente de forma
reprodutível.

## Tabelas finais

| Tabela | Granularidade |
|---|---|
| `fato_cobertura.csv` | Estado × bioma × classe × ano |
| `fato_transicao.csv` | Estado × bioma × tipo de transição × ano |
| `fato_focos.csv` | Estado × ano × mês |
| `dim_estado.csv` | Uma linha por unidade da federação |
| `dim_bioma.csv` | Uma linha por bioma |
| `dim_classe.csv` | Uma linha por classe do MapBiomas |
| `dim_ano.csv` | Uma linha por ano |
| `dim_mes.csv` | Uma linha por mês |

## Observação metodológica

O indicador `Natural → Antrópica` é uma transição de classes do MapBiomas. Ele
não deve ser apresentado como equivalente direto à taxa oficial de
desmatamento do PRODES. No dashboard, use o nome **conversão de cobertura
natural para uso antrópico**.

## Dashboard concluído

Dashboard desenvolvido em Power BI para explorar a cobertura da terra, as transições entre áreas naturais e antrópicas e os focos de queimadas no Brasil, com filtros por período e território.

[📊 Acessar dashboard no Power BI](https://app.powerbi.com/view?r=eyJrIjoiOTc0N2UzNDQtNWUyZC00OWUzLTk5ZTAtMTkzYzdlN2I2NjJhIiwidCI6IjJjZjdkNGQ1LWJkMWItNDk1Ni1hY2Y4LTI5OTUzOTliMjE2OCJ9)

O arquivo `brasilemtransformacao.pbix` está disponível neste repositório para abertura no Power BI Desktop.
