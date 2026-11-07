# Os visuais do painel são definidos em código (PBIR), e não montados à mão no Power BI Desktop

A especificação deixava o modelo semântico em TMDL, escrito pelo agente, e as quatro páginas do relatório para o dono montar à mão no Power BI Desktop, seguindo o roteiro. O dono decidiu que as páginas também saem de código: `scripts/gerar_relatorio_pbi.py` escreve a pasta `.Report` do PBIP no formato de relatório aprimorado (PBIR), um JSON por página e por visual, com os campos, as medidas, o formato, o texto alternativo, a ordem de tabulação e a sincronia das segmentações que o roteiro manda. O motivo: nesta máquina não há automação da interface gráfica do Desktop, e montar cada visual à mão, clique a clique, não se repete nem se revisa; um gerador se roda de novo depois de qualquer mudança no modelo, e o diff mostra o que mudou em cada visual.

## Considered Options

- **Montar à mão no Desktop** (a especificação): mostra a habilidade de usar o Desktop, mas o resultado não se reproduz, e cada ajuste do roteiro vira outra rodada de cliques.
- **Escrever o `report.json` do formato antigo**: um arquivo só, com cada visual como texto JSON dentro de texto JSON. O formato está sendo substituído pelo PBIR e não tem esquema público por visual.
- **Gerar em PBIR** (escolhida): formato documentado, com esquema JSON publicado pela Microsoft para cada arquivo, que o Desktop abre e grava.

## Consequences

O README e o relatório dizem "visuais definidos em código (PBIR) sobre modelo em TMDL", e não "montado à mão no Power BI Desktop". O roteiro (`powerbi/roteiro.md`) continua a ser a especificação legível de cada página e diz como regenerar. Uma mudança feita no Desktop se perde na próxima geração: quem muda uma página muda o gerador e roda de novo. O Desktop continua necessário para abrir o PBIP, atualizar os dados, conferir as medidas e exportar as capturas. Os testes (`tests/test_gerar_relatorio_pbi.py`) conferem a estrutura sem o Desktop: todo campo usado existe no TMDL, todo visual tem texto alternativo, nenhum visual ordena municípios por nome e as cores são só a de destaque e o neutro. Se o Desktop recusa uma propriedade de formato, ela não aparece em nenhum teste: só se vê ao abrir.
