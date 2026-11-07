# Números canônicos

Cada número impresso no README, no relatório e nos títulos das figuras tem uma linha aqui. Arquivo **gerado** por `scripts/numeros.py`: para mudar um número, mude o script ou o dado, rode `python scripts/numeros.py` e confira os lugares da coluna "Onde aparece". Valores monetários em reais de 2025 (IPCA, média do ano).

| Número | Valor | O que é | Sai de | Onde aparece |
|---|---|---|---|---|
| `\NumMunicipios` | 645 | municípios de SP na base | `scripts/numeros.py` | (ainda não usado) |
| `\NumIndicadores` | 8 | Indicadores definidos por escrito | `scripts/numeros.py` | (ainda não usado) |
| `\NumIndicadoresComparaveis` | 7 | Indicadores comparados com a faixa (todos menos a receita total) | `scripts/numeros.py` | `graficos/02-municipio-na-faixa.png` |
| `\NumAnoInicial` | 2015 | primeiro ano da série | `scripts/numeros.py` | `graficos/01-painel-municipio.png`, `graficos/03-previsao.png` |
| `\NumAnoFinal` | 2025 | último ano da série | `scripts/numeros.py` | `graficos/01-painel-municipio.png` |
| `\NumLinhasFato` | 50.413 | linhas da tabela fato (município × ano × Indicador com dado) | `scripts/numeros.py` | (ainda não usado) |
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
| `\NumCelulasConferencia` | 174 | células de powerbi/conferencia.md (valor esperado de uma medida) | `scripts/conferir_powerbi.py` | (ainda não usado) |
| `\NumMunicipiosConferencia` | 3 | municípios sorteados para a conferência | `scripts/gerar_conferencia.py` | (ainda não usado) |
| `\NumCelulasBatem` | 174 | células em que a medida DAX devolveu o valor esperado | `scripts/conferir_powerbi.py` | (ainda não usado) |
| `\NumCelulasCompletas` | 151.239 | células da conferência completa (3 medidas × município × ano × Indicador) | `scripts/conferir_powerbi.py` | (ainda não usado) |
| `\NumDivergenciasCompletas` | 0 | divergências entre DAX e SQLite na conferência completa | `scripts/conferir_powerbi.py` | (ainda não usado) |
| `\NumExemplo` | Ibirá | município de exemplo, sorteado com semente fixa | `scripts/comum.py` | `graficos/01-painel-municipio.png`, `graficos/02-municipio-na-faixa.png`, `graficos/03-previsao.png` |
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
| `\NumErroEscolhidoUm` | 6,6 | erro médio absoluto, em %, do método tendencia3 a 1 ano(s) | `scripts/modelo.py` | (ainda não usado) |
| `\NumErroEscolhidoDois` | 9,4 | erro médio absoluto, em %, do método tendencia3 a 2 ano(s) | `scripts/modelo.py` | (ainda não usado) |
| `\NumErroEscolhidoTres` | 12,5 | erro médio absoluto, em %, do método tendencia3 a 3 ano(s) | `scripts/modelo.py` | `graficos/04-teste-do-modelo.png` |
| `\NumViesEscolhidoTres` | +5,2 | viés médio, em %, do método tendencia3 a 3 anos | `scripts/modelo.py` | (ainda não usado) |
| `\NumErroIngenuoUm` | 7,0 | erro médio absoluto, em %, do método ingenuo a 1 ano(s) | `scripts/modelo.py` | (ainda não usado) |
| `\NumErroIngenuoDois` | 12,7 | erro médio absoluto, em %, do método ingenuo a 2 ano(s) | `scripts/modelo.py` | (ainda não usado) |
| `\NumErroIngenuoTres` | 18,4 | erro médio absoluto, em %, do método ingenuo a 3 ano(s) | `scripts/modelo.py` | `graficos/04-teste-do-modelo.png` |
| `\NumViesIngenuoTres` | +18,2 | viés médio, em %, do método ingenuo a 3 anos | `scripts/modelo.py` | (ainda não usado) |
| `\NumErroRetaUm` | 6,8 | erro médio absoluto, em %, do método tendencia5 a 1 ano(s) | `scripts/modelo.py` | (ainda não usado) |
| `\NumErroRetaDois` | 10,0 | erro médio absoluto, em %, do método tendencia5 a 2 ano(s) | `scripts/modelo.py` | (ainda não usado) |
| `\NumErroRetaTres` | 13,3 | erro médio absoluto, em %, do método tendencia5 a 3 ano(s) | `scripts/modelo.py` | (ainda não usado) |
| `\NumViesRetaTres` | +9,1 | viés médio, em %, do método tendencia5 a 3 anos | `scripts/modelo.py` | (ainda não usado) |
| `\NumOrigensTeste` | 4 | anos de origem do Teste contra o passado | `scripts/modelo.py` | (ainda não usado) |
| `\NumOrigemInicial` | 2019 | primeira origem do Teste contra o passado | `scripts/modelo.py` | `graficos/04-teste-do-modelo.png` |
| `\NumOrigemFinal` | 2022 | última origem do Teste contra o passado | `scripts/modelo.py` | `graficos/04-teste-do-modelo.png` |
| `\NumCobOitentaSem` | 71 | cobertura do intervalo de 80% sem ajuste, em % | `scripts/modelo.py` | (ainda não usado) |
| `\NumCobOitentaCom` | 81 | cobertura do intervalo de 80% depois do ajuste, em % | `scripts/modelo.py` | `graficos/04-teste-do-modelo.png` |
| `\NumCobOitentaPior` | 62 | cobertura do intervalo de 80% na pior origem deixada de fora, depois do ajuste, em % | `scripts/modelo.py` | `graficos/04-teste-do-modelo.png` |
| `\NumCobOitentaPiorOrigem` | 2022 | a pior origem deixada de fora para o intervalo de 80% | `scripts/modelo.py` | `graficos/04-teste-do-modelo.png` |
| `\NumEscalaOitenta` | 1,25 | fator de alargamento do intervalo de 80% | `scripts/modelo.py` | (ainda não usado) |
| `\NumCobNoventaCincoSem` | 92 | cobertura do intervalo de 95% sem ajuste, em % | `scripts/modelo.py` | (ainda não usado) |
| `\NumCobNoventaCincoCom` | 95 | cobertura do intervalo de 95% depois do ajuste, em % | `scripts/modelo.py` | (ainda não usado) |
| `\NumCobNoventaCincoPior` | 91 | cobertura do intervalo de 95% na pior origem deixada de fora, depois do ajuste, em % | `scripts/modelo.py` | (ainda não usado) |
| `\NumCobNoventaCincoPiorOrigem` | 2022 | a pior origem deixada de fora para o intervalo de 95% | `scripts/modelo.py` | (ainda não usado) |
| `\NumEscalaNoventaCinco` | 1,15 | fator de alargamento do intervalo de 95% | `scripts/modelo.py` | (ainda não usado) |
| `\NumCelulasExcel` | PENDENTE | células da aba Painel conferidas contra o SQLite | `scripts/conferir_excel.py` | (ainda não usado) |
| `\NumCelulasExcelBatem` | PENDENTE | células da aba Painel iguais ao SQLite | `scripts/conferir_excel.py` | (ainda não usado) |
| `\NumMunicipiosExcel` | PENDENTE | municípios testados na planilha | `scripts/conferir_excel.py` | (ainda não usado) |
