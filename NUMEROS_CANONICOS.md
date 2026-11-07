# Números canônicos

Cada número impresso no README, no relatório e nos títulos das figuras tem uma linha aqui. Arquivo **gerado** por `scripts/numeros.py`: para mudar um número, mude o script ou o dado, rode `python scripts/numeros.py` e confira os lugares da coluna "Onde aparece". Valores monetários em reais de 2025 (IPCA, média do ano).

| Número | Valor | O que é | Sai de | Onde aparece |
|---|---|---|---|---|
| `\NumMunicipios` | 645 | municípios de SP na base | `scripts/numeros.py` | `relatorio/gerados/tabelas_modelo.tex`, `excel/painel-municipios-sp.xlsx` |
| `\NumIndicadores` | 8 | Indicadores definidos por escrito | `scripts/numeros.py` | `relatorio/gerados/tabelas_modelo.tex`, `excel/painel-municipios-sp.xlsx` |
| `\NumIndicadoresComparaveis` | 7 | Indicadores comparados com a faixa (todos menos a receita total) | `scripts/numeros.py` | `graficos/02-municipio-na-faixa.png` |
| `\NumAnoInicial` | 2015 | primeiro ano da série | `scripts/numeros.py` | `graficos/01-painel-municipio.png`, `graficos/03-previsao.png`, `excel/painel-municipios-sp.xlsx` |
| `\NumAnoFinal` | 2025 | último ano da série | `scripts/numeros.py` | `graficos/01-painel-municipio.png`, `excel/painel-municipios-sp.xlsx` |
| `\NumLinhasFato` | 50.413 | linhas da tabela fato (município × ano × Indicador com dado) | `scripts/numeros.py` | `relatorio/gerados/tabelas_modelo.tex` |
| `\NumFaixas` | 7 | Faixas de porte do Censo 2022 | `scripts/numeros.py` | (ainda não usado) |
| `\NumMunicipioAnos` | 7.095 | declarações possíveis à DCA (municípios × anos) | `scripts/numeros.py` | (ainda não usado) |
| `\NumExclusoes` | 27 | valores declarados excluídos pela regra de qualidade | `scripts/numeros.py` | (ainda não usado) |
| `\NumMunicipiosComExclusao` | 15 | municípios com pelo menos um valor excluído | `scripts/numeros.py` | (ainda não usado) |
| `\NumAnoPrevInicial` | 2026 | primeiro ano previsto | `scripts/numeros.py` | (ainda não usado) |
| `\NumAnoPrevFinal` | 2028 | último ano previsto | `scripts/numeros.py` | `graficos/03-previsao.png` |
| `\NumMunicipiosComPrevisao` | 642 | municípios com Previsão da receita | `scripts/numeros.py` | (ainda não usado) |
| `\NumTabelasFato` | 3 | tabelas fato do modelo (lado "muitos" das relações: fato_indicador, previsao, ref_faixa) | `scripts/numeros.py` | (ainda não usado) |
| `\NumDimensoes` | 3 | dimensões do modelo (lado "um": dim_ano, dim_indicador, dim_municipio) | `scripts/numeros.py` | (ainda não usado) |
| `\NumRelacoes` | 7 | relações do modelo, todas 1:N e de direção única | `scripts/numeros.py` | (ainda não usado) |
| `\NumMedidas` | 39 | medidas DAX no modelo | `scripts/numeros.py` | (ainda não usado) |
| `\NumCelulasConferencia` | 174 | células de powerbi/conferencia.md (valor esperado de uma medida) | `scripts/conferir_powerbi.py` | `relatorio/gerados/conferencias.tex` |
| `\NumMunicipiosConferencia` | 3 | municípios sorteados para a conferência | `scripts/gerar_conferencia.py` | `relatorio/gerados/conferencias.tex` |
| `\NumCelulasBatem` | 174 | células em que a medida DAX devolveu o valor esperado | `scripts/conferir_powerbi.py` | `relatorio/gerados/conferencias.tex` |
| `\NumCelulasCompletas` | 151.239 | células da conferência completa (3 medidas × município × ano × Indicador) | `scripts/conferir_powerbi.py` | `relatorio/gerados/conferencias.tex` |
| `\NumDivergenciasCompletas` | 0 | divergências entre DAX e SQLite na conferência completa | `scripts/conferir_powerbi.py` | `relatorio/gerados/conferencias.tex` |
| `\NumExemplo` | Ibirá | município de exemplo, sorteado com semente fixa | `scripts/comum.py` | `graficos/01-painel-municipio.png`, `graficos/02-municipio-na-faixa.png`, `graficos/03-previsao.png`, `excel/painel-municipios-sp.xlsx` |
| `\NumExemploCandidatos` | 521 | municípios com série completa entre os quais o exemplo foi sorteado | `scripts/comum.py` | (ainda não usado) |
| `\NumExemploFaixa` | de 10 a 20 mil | Faixa de porte do exemplo | `scripts/numeros.py` | `graficos/01-painel-municipio.png`, `graficos/02-municipio-na-faixa.png` |
| `\NumExemploNaFaixa` | 120 | municípios na Faixa de porte do exemplo | `scripts/numeros.py` | `graficos/01-painel-municipio.png`, `graficos/02-municipio-na-faixa.png` |
| `\NumExemploPopulacao` | 11.690 | população do exemplo no Censo 2022 | `scripts/numeros.py` | (ainda não usado) |
| `\NumFigUmVerbo` | gasta | verbo do título da Figura 1 (segue o Indicador de maior diferença) | `scripts/numeros.py` | `graficos/01-painel-municipio.png` |
| `\NumFigUmObjeto` | com saúde por habitante | complemento do título da Figura 1 | `scripts/numeros.py` | `graficos/01-painel-municipio.png` |
| `\NumFigUmDif` | 18,7 | diferença do exemplo para a mediana da faixa, em %, no Indicador mais distante dos quatro da Figura 1 | `scripts/numeros.py` | `graficos/01-painel-municipio.png` |
| `\NumFigUmSentido` | mais | acima (mais) ou abaixo (menos) da mediana | `scripts/numeros.py` | `graficos/01-painel-municipio.png` |
| `\NumFigUmAno` | 2025 | ano do valor da Figura 1 | `scripts/numeros.py` | (ainda não usado) |
| `\NumDifReceita` | −4,9 | diferença do exemplo para a mediana da faixa em receita_pc, 2025, em % | `scripts/numeros.py` | (ainda não usado) |
| `\NumDifSaude` | +18,7 | diferença do exemplo para a mediana da faixa em saude_pc, 2025, em % | `scripts/numeros.py` | (ainda não usado) |
| `\NumDifEducacao` | −7,1 | diferença do exemplo para a mediana da faixa em educacao_pc, 2025, em % | `scripts/numeros.py` | (ainda não usado) |
| `\NumDifDependencia` | −1,0 | diferença do exemplo para a mediana da faixa em dependencia_transf, 2025, em % | `scripts/numeros.py` | (ainda não usado) |
| `\NumFigDoisAcima` | 3 | Indicadores em que o exemplo fica acima da mediana da faixa, no último ano de cada um | `scripts/numeros.py` | `graficos/02-municipio-na-faixa.png` |
| `\NumFigDoisExtremo` | Ideb dos anos iniciais, rede municipal | Indicador em que o exemplo está mais perto de uma ponta da faixa | `scripts/numeros.py` | (ainda não usado) |
| `\NumFigDoisExtremoPos` | 92 | Posição na faixa do exemplo nesse Indicador, em % | `scripts/numeros.py` | (ainda não usado) |
| `\NumExemploReceitaUltima` | 76,7 | receita corrente total do exemplo em 2025, R$ milhões de 2025 | `scripts/numeros.py` | (ainda não usado) |
| `\NumExemploPrevista` | 88,6 | Previsão da receita do exemplo para 2028, R$ milhões de 2025 | `scripts/numeros.py` | `graficos/03-previsao.png` |
| `\NumExemploInfOitenta` | 74,9 | limite inferior do Intervalo de previsão de 80% | `scripts/numeros.py` | (ainda não usado) |
| `\NumExemploSupOitenta` | 114,6 | limite superior do Intervalo de previsão de 80% | `scripts/numeros.py` | (ainda não usado) |
| `\NumExemploInfNoventaCinco` | 67,6 | limite inferior do Intervalo de previsão de 95% | `scripts/numeros.py` | `graficos/03-previsao.png` |
| `\NumExemploSupNoventaCinco` | 128,2 | limite superior do Intervalo de previsão de 95% | `scripts/numeros.py` | `graficos/03-previsao.png` |
| `\NumErroEscolhidoUm` | 6,6 | erro médio absoluto, em %, do método tendencia3 a 1 ano(s) | `scripts/modelo.py` | `relatorio/gerados/teste_metodos.tex` |
| `\NumErroEscolhidoDois` | 9,4 | erro médio absoluto, em %, do método tendencia3 a 2 ano(s) | `scripts/modelo.py` | `relatorio/gerados/teste_metodos.tex` |
| `\NumErroEscolhidoTres` | 12,5 | erro médio absoluto, em %, do método tendencia3 a 3 ano(s) | `scripts/modelo.py` | `relatorio/gerados/teste_metodos.tex`, `graficos/04-teste-do-modelo.png` |
| `\NumViesEscolhidoTres` | +5,2 | viés médio, em %, do método tendencia3 a 3 anos | `scripts/modelo.py` | `relatorio/gerados/teste_metodos.tex` |
| `\NumErroIngenuoUm` | 7,0 | erro médio absoluto, em %, do método ingenuo a 1 ano(s) | `scripts/modelo.py` | `relatorio/gerados/teste_metodos.tex` |
| `\NumErroIngenuoDois` | 12,7 | erro médio absoluto, em %, do método ingenuo a 2 ano(s) | `scripts/modelo.py` | `relatorio/gerados/teste_metodos.tex` |
| `\NumErroIngenuoTres` | 18,4 | erro médio absoluto, em %, do método ingenuo a 3 ano(s) | `scripts/modelo.py` | `relatorio/gerados/teste_metodos.tex`, `graficos/04-teste-do-modelo.png` |
| `\NumViesIngenuoTres` | +18,2 | viés médio, em %, do método ingenuo a 3 anos | `scripts/modelo.py` | `relatorio/gerados/teste_metodos.tex` |
| `\NumErroRetaUm` | 6,8 | erro médio absoluto, em %, do método tendencia5 a 1 ano(s) | `scripts/modelo.py` | `relatorio/gerados/teste_metodos.tex` |
| `\NumErroRetaDois` | 10,0 | erro médio absoluto, em %, do método tendencia5 a 2 ano(s) | `scripts/modelo.py` | `relatorio/gerados/teste_metodos.tex` |
| `\NumErroRetaTres` | 13,3 | erro médio absoluto, em %, do método tendencia5 a 3 ano(s) | `scripts/modelo.py` | `relatorio/gerados/teste_metodos.tex` |
| `\NumViesRetaTres` | +9,1 | viés médio, em %, do método tendencia5 a 3 anos | `scripts/modelo.py` | `relatorio/gerados/teste_metodos.tex` |
| `\NumOrigensTeste` | 4 | anos de origem do Teste contra o passado | `scripts/modelo.py` | (ainda não usado) |
| `\NumOrigemInicial` | 2019 | primeira origem do Teste contra o passado | `scripts/modelo.py` | `graficos/04-teste-do-modelo.png` |
| `\NumOrigemFinal` | 2022 | última origem do Teste contra o passado | `scripts/modelo.py` | `graficos/04-teste-do-modelo.png` |
| `\NumCobOitentaSem` | 71 | cobertura do intervalo de 80% sem ajuste, em % | `scripts/modelo.py` | `relatorio/gerados/cobertura.tex` |
| `\NumCobOitentaCom` | 81 | cobertura do intervalo de 80% depois do ajuste, em % | `scripts/modelo.py` | `relatorio/gerados/cobertura.tex`, `graficos/04-teste-do-modelo.png` |
| `\NumCobOitentaPior` | 62 | cobertura do intervalo de 80% na pior origem deixada de fora, depois do ajuste, em % | `scripts/modelo.py` | `relatorio/gerados/cobertura.tex`, `graficos/04-teste-do-modelo.png`, `excel/painel-municipios-sp.xlsx` |
| `\NumCobOitentaPiorOrigem` | 2022 | a pior origem deixada de fora para o intervalo de 80% | `scripts/modelo.py` | `relatorio/gerados/cobertura.tex`, `graficos/04-teste-do-modelo.png`, `excel/painel-municipios-sp.xlsx` |
| `\NumEscalaOitenta` | 1,25 | fator de alargamento do intervalo de 80% | `scripts/modelo.py` | `relatorio/gerados/cobertura.tex` |
| `\NumCobNoventaCincoSem` | 92 | cobertura do intervalo de 95% sem ajuste, em % | `scripts/modelo.py` | `relatorio/gerados/cobertura.tex` |
| `\NumCobNoventaCincoCom` | 95 | cobertura do intervalo de 95% depois do ajuste, em % | `scripts/modelo.py` | `relatorio/gerados/cobertura.tex` |
| `\NumCobNoventaCincoPior` | 91 | cobertura do intervalo de 95% na pior origem deixada de fora, depois do ajuste, em % | `scripts/modelo.py` | `relatorio/gerados/cobertura.tex` |
| `\NumCobNoventaCincoPiorOrigem` | 2022 | a pior origem deixada de fora para o intervalo de 95% | `scripts/modelo.py` | `relatorio/gerados/cobertura.tex` |
| `\NumEscalaNoventaCinco` | 1,15 | fator de alargamento do intervalo de 95% | `scripts/modelo.py` | `relatorio/gerados/cobertura.tex` |
| `\NumCelulasExcel` | 256 | células da aba Painel conferidas contra o SQLite | `scripts/conferir_excel.py` | `relatorio/gerados/conferencias.tex` |
| `\NumCelulasExcelBatem` | 256 | células da aba Painel iguais ao SQLite | `scripts/conferir_excel.py` | `relatorio/gerados/conferencias.tex` |
| `\NumMunicipiosExcel` | 4 | municípios testados na planilha | `scripts/conferir_excel.py` | `relatorio/gerados/conferencias.tex` |
| `\NumMesCapa` | Novembro | mês da capa do relatório (o mês em que o registro foi gerado) | `scripts/numeros.py` | (ainda não usado) |
| `\NumAnoCapa` | 2026 | ano da capa do relatório (o ano em que o registro foi gerado) | `scripts/numeros.py` | (ainda não usado) |
| `\NumAnoBaseReais` | 2025 | ano-base dos reais (IPCA médio do ano) | `sql/20_indicadores.sql` | (ainda não usado) |
| `\NumRegraFator` | 4 | quantas vezes acima ou abaixo da média dos outros anos o valor sai | `sql/20_indicadores.sql` | (ainda não usado) |
| `\NumLinhasRefFaixa` | 553 | linhas de ref_faixa (Faixa de porte × ano × Indicador) | `scripts/numeros.py` | `relatorio/gerados/tabelas_modelo.tex` |
| `\NumLinhasPrevisao` | 1.926 | linhas de previsao (município × ano previsto) | `scripts/numeros.py` | `relatorio/gerados/tabelas_modelo.tex` |
| `\NumLinhasDimAno` | 14 | linhas de dim_ano (do primeiro ano dos dados ao último previsto) | `scripts/numeros.py` | `relatorio/gerados/tabelas_modelo.tex` |
| `\NumPastasMedidas` | 7 | pastas de exibição das medidas DAX | `scripts/numeros.py` | (ainda não usado) |
| `\NumMedidasPastaBase` | 7 | medidas DAX na pasta "Base" | `scripts/numeros.py` | `relatorio/gerados/pastas_medidas.tex` |
| `\NumMedidasPastaFaixa` | 6 | medidas DAX na pasta "Faixa" | `scripts/numeros.py` | `relatorio/gerados/pastas_medidas.tex` |
| `\NumMedidasPastaUltimoValor` | 5 | medidas DAX na pasta "Último valor" | `scripts/numeros.py` | `relatorio/gerados/pastas_medidas.tex` |
| `\NumMedidasPastaPrevisao` | 11 | medidas DAX na pasta "Previsão" | `scripts/numeros.py` | `relatorio/gerados/pastas_medidas.tex` |
| `\NumMedidasPastaComparacaoNaFaixa` | 6 | medidas DAX na pasta "Comparação na faixa" | `scripts/numeros.py` | `relatorio/gerados/pastas_medidas.tex` |
| `\NumMedidasPastaTitulos` | 1 | medidas DAX na pasta "Títulos" | `scripts/numeros.py` | `relatorio/gerados/pastas_medidas.tex` |
| `\NumMedidasPastaTesteContraOPassado` | 3 | medidas DAX na pasta "Teste contra o passado" | `scripts/numeros.py` | `relatorio/gerados/pastas_medidas.tex` |
| `\NumPaginasPainel` | 4 | páginas do painel no Power BI | `scripts/gerar_relatorio_pbi.py` | (ainda não usado) |
| `\NumMedidasCompletas` | 3 | medidas conferidas em cada linha da fato na conferência completa | `scripts/conferir_powerbi.py` | `relatorio/gerados/conferencias.tex` |
| `\NumValoresValidados` | 50.413 | valores dos Indicadores refeitos em pandas e comparados com o SQL | `scripts/validar.py` | `relatorio/gerados/conferencias.tex` |
| `\NumValoresValidadosIguais` | 50.413 | desses, os iguais ao SQL (diferença máxima zero) | `scripts/validar.py` | `relatorio/gerados/conferencias.tex` |
| `\NumMetodos` | 3 | métodos de previsão testados contra o passado | `scripts/modelo.py` | (ainda não usado) |
| `\NumHorizontes` | 3 | anos à frente da Previsão da receita e do Teste contra o passado | `scripts/modelo.py` | (ainda não usado) |
| `\NumJanelaEscolhido` | 3 | anos da tendência do método escolhido | `scripts/modelo.py` | `relatorio/gerados/teste_metodos.tex` |
| `\NumJanelaReta` | 5 | anos da reta do método concorrente | `scripts/modelo.py` | `relatorio/gerados/teste_metodos.tex` |
| `\NumNivelOitenta` | 80 | nível de um Intervalo de previsão, em % | `scripts/modelo.py` | `relatorio/gerados/cobertura.tex` |
| `\NumNivelNoventaCinco` | 95 | nível de um Intervalo de previsão, em % | `scripts/modelo.py` | `relatorio/gerados/cobertura.tex` |
