# Roteiro do painel no Power BI Desktop

Este roteiro é a especificação legível das quatro páginas do painel: o que cada página mostra, em que posição, com que medida e em que formato, e quais capturas exportar no fim. Os visuais são **definidos em código (PBIR) sobre modelo em TMDL**: `scripts/gerar_relatorio_pbi.py` escreve as páginas em `painel-municipios-sp.Report/definition/`, um JSON por página e por visual, a partir deste roteiro ([ADR 0003](../docs/adr/0003-visuais-do-painel-em-codigo.md)). O modelo semântico (consultas Power Query, relações, medidas DAX e formatos) está em TMDL, em `painel-municipios-sp.SemanticModel/definition/`, e é a fonte única das medidas: o roteiro e o gerador só dizem qual medida vai em qual visual. A tabela `powerbi/conferencia.md` traz o que cada medida tem de devolver, e `scripts/conferir_powerbi.py` confere.

Os termos seguem o `GLOSSARY.md` da raiz: Faixa de porte, Municípios parecidos, Mediana da faixa, Posição na faixa, Intervalo de previsão.

## 0. Antes de abrir

1. **Instale o Power BI Desktop** (gratuito, pela Microsoft Store ou pelo instalador do site da Microsoft).
2. **Instale a Lato no Windows.** Os arquivos estão em `%LOCALAPPDATA%\Programs\MiKTeX\fonts\truetype\typoland\lato\`. Selecione `Lato-Regular.ttf`, `Lato-Bold.ttf`, `Lato-Italic.ttf` e `Lato-BoldItalic.ttf`, clique com o botão direito e escolha **Instalar para todos os usuários**. Feche e reabra o Power BI Desktop depois disso. Sem a Lato, o tema cai para a Segoe UI.
3. **Abra `powerbi/painel-municipios-sp.pbip`** com dois cliques.
4. Se o repositório não estiver em `C:\Users\Pichau\Desktop\indicadores-municipios-sp`, vá em **Página Inicial → Transformar dados → Editar parâmetros** e troque `PastaDados` pelo caminho da pasta `dados\tratados\` da sua cópia, **terminado em barra invertida**.
5. **Página Inicial → Atualizar.** As consultas leem os CSV. A primeira atualização leva alguns segundos.
6. **Confira o modelo.** Com o Desktop aberto, rode no terminal, na raiz do repositório:

   ```
   .venv\Scripts\python scripts\conferir_powerbi.py --completo
   ```

   O script deve terminar com todas as células batendo e gravar `powerbi/resultado_conferencia.csv` e `powerbi/resultado_conferencia_completa.csv`. Se alguma célula não bater, o defeito está na medida, e o valor certo está no SQLite. **A correção vai no TMDL**, que é a fonte das medidas: com o Desktop fechado, corrija a medida em `painel-municipios-sp.SemanticModel/definition/tables/Medidas.tmdl`, reabra o `.pbip`, atualize e rode o script de novo. (Se preferir testar a correção no Desktop, pode: ao salvar, o Desktop regrava o modelo em TMDL, e a medida corrigida fica no arquivo; confira o diff do TMDL antes de versionar. O que o Desktop grava na pasta `.Report` não vale: as páginas se regeneram pelo gerador, abaixo.)

## Como regenerar as páginas

Com o Desktop **fechado** (ele regrava a pasta `.Report` ao salvar), rode na raiz do repositório:

```
.venv\Scripts\python scripts\gerar_relatorio_pbi.py
```

O gerador apaga `painel-municipios-sp.Report/definition/` e o `report.json` do formato antigo, se houver, e grava de novo as quatro páginas, o `definition.pbir` (que aponta para o modelo por caminho relativo) e o tema do kit em `StaticResources/RegisteredResources/`. Nada dos dados é digitado no gerador: o município de exemplo vem de `scripts/comum.py`, o último ano observado e o ano-base dos reais vêm dos CSV, o nome do método escolhido vem do TMDL e as cores vêm do kit e do tema (`scripts/gerar_tema.py`). Depois, abra o `.pbip` e atualize.

**Mudança feita nas páginas pelo Desktop se perde na próxima geração**, porque o gerador reescreve a pasta `.Report`. Mudança no modelo (medida, formato, relação) não se perde: ela vai no TMDL, que o gerador não toca. Para mudar uma página, mude o gerador e este roteiro, e rode de novo. Os testes (`python -m unittest discover -s tests`) conferem, sem o Desktop, que todo campo usado existe no TMDL, que todo visual tem texto alternativo, a ordem das páginas e de tabulação, a sincronia das segmentações, o município de exemplo escolhido, que nenhum visual ordena municípios por nome e que as cores são só a de destaque e o neutro. O que os testes não veem é se o Desktop aceita cada propriedade de formato: isso só se vê ao abrir.

## Se o Desktop recusar o relatório

O modelo (`painel-municipios-sp.SemanticModel/`) e as páginas (`painel-municipios-sp.Report/`) são pastas separadas: um relatório que o Desktop recusa não estraga o modelo, e o modelo continua conferível. A mensagem do Desktop diz o arquivo e a propriedade que ele não aceitou; anote-a antes de fechar.

1. **Feche o Desktop sem salvar** e regenere as páginas (seção acima). Muitas recusas vêm de uma pasta `.Report` misturada: sobra do formato antigo (`report.json`) ou página regravada pelo Desktop pela metade. O gerador apaga `definition/` e escreve tudo de novo. Abra o `.pbip` outra vez.
2. **Se ainda recusar, abra só o modelo, com um relatório em branco.** Feche o Desktop e apague a pasta `painel-municipios-sp.Report` (ela está no git e volta com `git checkout -- powerbi/painel-municipios-sp.Report`). Abra o Desktop, crie um relatório em branco e escolha **Arquivo → Salvar como → Arquivos do projeto do Power BI (.pbip)**, com o nome `painel-municipios-sp`, numa pasta temporária. Copie de lá só a pasta `painel-municipios-sp.Report` para `powerbi/`: o `definition.pbir` dela aponta para `../painel-municipios-sp.SemanticModel`, que é o modelo do projeto. Abra `powerbi/painel-municipios-sp.pbip` e atualize: o modelo abre inteiro, sem páginas, e `scripts/conferir_powerbi.py` funciona igual, porque só consulta o modelo.
3. **Corrija no gerador, e não no Desktop.** Com o modelo aberto, a propriedade recusada (anotada no início) se corrige em `scripts/gerar_relatorio_pbi.py`; feche o Desktop, rode o gerador (que substitui a pasta em branco pelas quatro páginas) e abra de novo. Se nada disso servir, as páginas podem ser montadas à mão sobre o modelo, seguindo as tabelas abaixo, que dizem o visual, os campos e o formato de cada uma.

Em nenhum desses passos o modelo é apagado: as medidas, as consultas e as relações estão no TMDL, e é ele que importa para os números do README.

## O que o modelo já traz

| Tabela | Papel | Liga-se a |
|---|---|---|
| `dim_municipio` | um município por linha, com a Faixa de porte | `fato_indicador`, `previsao` |
| `dim_indicador` | um Indicador por linha, com a definição escrita | `fato_indicador`, `ref_faixa` |
| `dim_ano` | do primeiro ano dos dados ao último previsto (tabela calculada) | `fato_indicador`, `ref_faixa`, `previsao` |
| `fato_indicador` | valor por município, ano e Indicador | as três dimensões |
| `ref_faixa` | mediana e quartis por Faixa de porte, ano e Indicador | `dim_ano`, `dim_indicador`; a faixa chega por `TREATAS` ([ADR 0001](../docs/adr/0001-ref-faixa-como-segunda-fato.md)) |
| `previsao` | Previsão da receita e Intervalos de previsão | `dim_municipio`, `dim_ano` |
| `sel_municipio` | cópia solta da lista de municípios, só para a página 2 | nenhuma, de propósito |
| `backtest_metodos`, `backtest_cobertura` | Teste contra o passado | nenhuma |
| `Medidas` | todas as medidas, em pastas de exibição | |

Todas as relações são 1:N, de direção única. As chaves e os valores brutos ficam ocultos: os visuais usam as dimensões e as medidas. O modelo desencoraja medidas implícitas, então todo número de visual é uma medida.

## Formato comum a todas as páginas

- Tamanho da página: 16:9 (1280 × 720), ajustada à janela. Fundo branco (o tema aplica).
- Título da página: caixa de texto, Lato Bold 20, cor de texto do tema. É o primeiro item da ordem de tabulação. As caixas de texto usam a mesma pilha de fontes do tema (`Lato, 'Segoe UI', sans-serif`): só "Lato" o Desktop não resolve e cai numa fonte serifada.
- **Cor.** O Município selecionado sai na **cor 1 do tema** (vermelho de destaque), só em marca: linha, ponto, coluna. A mediana e o contexto saem na **cor 2** (cinza neutro). Os quartis saem na cor 2, 60% mais clara. Número grande de cartão sai na cor de texto, e não em vermelho. Nenhuma outra cor do tema aparece. No JSON do PBIR, a cor 1 é `ThemeDataColor` de id 2 e a cor 2, de id 3: os ids 0 e 1 são o fundo e a cor de texto do tema.
- As segmentações em lista suspensa têm 72 px de altura, para o valor escolhido não cortar embaixo. Subtítulos de visual também quebram em linhas.
- Cartões mostram o número inteiro, no formato da medida (unidade de exibição "nenhuma": 11.690, e não "12 Mil"), com quebra de linha. Títulos de visual quebram em linhas, em vez de cortar.
- Nenhum visual usa cor de "bom" ou "ruim": nenhum Indicador tem um lado melhor que valha para todo município. Nenhuma tabela tem formatação condicional de cor.
- Texto alternativo em todo visual (**Formato → Geral → Texto alternativo**), dizendo a pergunta que o visual responde.
- O cabeçalho dos visuais (os ícones de foco e de filtro sobre o visual) fica oculto.
- Segmentações de seleção única, com o estado padrão já escolhido: o município de exemplo e, no Indicador, "Despesa com saúde por habitante".

## Página 1, "Município"

Pergunta: **onde este município está, e onde estão os parecidos?**

| Tab | Posição (x, y, l × a) | Visual | Campos | Formato |
|---|---|---|---|---|
| 0 | 24, 16, 900 × 40 | Caixa de texto | "Indicadores do município" | título |
| 1 | 24, 64, 320 × 72 | Segmentação, lista suspensa | `dim_municipio[municipio]` | seleção única; pesquisa ligada; o município de exemplo escolhido. Sincronizada com a página 3 |
| 2 | 800, 272, 456 × 156 | Segmentação, lista | `dim_indicador[nome]` | seleção única; filtro do visual tira a Receita corrente total (`indicador_id` ≠ `receita_total`), que é da página 3. Sincronizada com a página 2 |
| 3 | 24, 272, 760 × 412 | Gráfico de linhas | Eixo X: `dim_ano[ano]` (categórico). Eixo Y: `[Valor]`, `[Mediana da faixa]`, `[1º quartil da faixa]`, `[3º quartil da faixa]` | `[Valor]`: cor 1, 2,5 pt, com marcador. Mediana: cor 2, 2 pt. Quartis: cor 2 clara, 1 pt. Título do visual: **fx → `[Título da evolução]`**, com quebra de linha. Legenda no topo (o rótulo na ponta da linha do município batia no do 3º quartil). Filtro do visual: ano até o último observado |
| 4 | 360, 64, 300 × 80 | Cartão | `[Faixa de porte]` | rótulo "Faixa de porte"; número em 20 pt |
| 5 | 676, 64, 200 × 80 | Cartão | `[Municípios na faixa]` | rótulo "Municípios na faixa"; 20 pt |
| 6 | 892, 64, 220 × 80 | Cartão | `[População (Censo 2022)]` | rótulo "População (Censo 2022)"; 20 pt, número inteiro com ponto de milhar |
| 7 a 10 | 24 + 312·i, 152, 296 × 116 | 4 cartões de várias linhas | `[Último valor]` (rótulo "município"), `[Último valor da faixa]` ("mediana da faixa") e `[Ano do último valor]` ("ano"), cada cartão preso por filtro do visual a um Indicador: Receita corrente por habitante, Despesa com saúde por habitante, Despesa com educação por habitante, Dependência de transferências | título do visual: o nome do Indicador; números em 14 pt. A segmentação de Indicador **não** filtra estes cartões (interação desligada na página) |
| 11 | 800, 440, 456 × 244 | Tabela | `dim_ano[ano]`, `[Valor]`, `[Mediana da faixa]`, `[Diferença para a mediana]`, `[Posição na faixa]` | ordenada por ano; valor e mediana com a mesma casa decimal (o formato das duas medidas); sem linha de total; linhas em zebra (o tema faz); sem formatação condicional de cor. Filtro do visual: ano até o último observado |
| 12 | 24, 688, 1232 × 28 | Caixa de texto | "As linhas cinza-claras são o 1º e o 3º quartil dos Municípios parecidos. Estar acima ou abaixo da mediana não é, por si, bom nem ruim." | 9 pt |

O filtro "ano até o último observado" usa o maior ano de `indicadores_longo.csv`, lido pelo gerador: sem ele, o eixo e a tabela iriam até o último ano previsto.

## Página 2, "Comparação na faixa"

Pergunta: **o município está no meio ou na ponta do grupo?**

Esta página usa a tabela solta `sel_municipio`, e não `dim_municipio`, na segmentação de município. O motivo: a dispersão tem de mostrar **todos** os Municípios parecidos. Se a segmentação filtrasse `dim_municipio`, sobraria um ponto só. Se a interação fosse desligada, a medida que separa a faixa também deixaria de enxergar o município escolhido. A tabela solta resolve os dois lados: ela não filtra nada, e as medidas "do escolhido" a leem.

| Tab | Posição (x, y, l × a) | Visual | Campos | Formato |
|---|---|---|---|---|
| 0 | 24, 16, 900 × 40 | Caixa de texto | "Comparação na faixa" | título |
| 1 | 24, 64, 320 × 72 | Segmentação, lista suspensa | `sel_municipio[municipio]` | seleção única; o município de exemplo escolhido |
| 2 | 24, 148, 320 × 248 | Segmentação, lista | `dim_indicador[nome]` | seleção única; **sincronizada com a página 1**; sem a Receita corrente total |
| 3 | 24, 408, 320 × 72 | Segmentação, lista suspensa | `dim_ano[ano]` | seleção única; o último ano em que a Despesa com saúde por habitante tem dado (lido dos CSV) |
| 4 | 360, 64, 600 × 636 | Gráfico de dispersão | Detalhes: `dim_municipio[municipio]`. Eixo X: `[Valor]`. Eixo Y: `[População (Censo 2022)]`, em **escala logarítmica** | Filtro do visual: `[Na faixa do escolhido]` **é 1**. Cor dos pontos: **fx → Regras → `[É o escolhido]`**: 1 na cor 1, 0 no cinza neutro. Legenda e rótulos dos pontos desligados |
| 5 | 980, 64, 276 × 140 | Cartão | `[Posição do escolhido]` | rótulo "Posição na faixa (0 a 100%)"; a nota diz que 0% é o menor valor da faixa e 100%, o maior |
| 6 | 980, 216, 276 × 140 | Cartão | `[Valor do escolhido]` | rótulo "Valor do município" |
| 7 | 980, 368, 276 × 140 | Cartão | `[Mediana da faixa do escolhido]` | rótulo "Mediana da faixa" |
| 8 | 980, 520, 276 × 140 | Cartão | `[Diferença do escolhido]` | rótulo "Diferença para a mediana" |
| 9 | 24, 492, 320 × 208 | Caixa de texto | o que é cada ponto, como ler a Posição na faixa, e que a página mostra posição e grupo, e não lista | 9 pt |

Sem ranking por nome: a página mostra posição e grupo, e não uma lista do "pior" ao "melhor". Todos os pontos têm o mesmo tamanho; o escolhido se distingue só pela cor.

## Página 3, "Previsão da receita"

Pergunta: **quanto de receita o município pode esperar nos próximos três anos, e com que margem?**

| Tab | Posição (x, y, l × a) | Visual | Campos | Formato |
|---|---|---|---|---|
| 0 | 24, 16, 900 × 40 | Caixa de texto | "Previsão da receita" | título |
| 1 | 24, 64, 320 × 72 | Segmentação, lista suspensa | `dim_municipio[municipio]` | seleção única; **sincronizada com a página 1** |
| 2 | 24, 148, 840 × 468 | Gráfico de linhas | Eixo X: `dim_ano[ano]` (categórico). Eixo Y: `[Receita observada]`, `[Receita prevista (linha)]`, `[Limite inferior 80%]`, `[Limite superior 80%]`, `[Limite inferior 95%]`, `[Limite superior 95%]` | Observada: cor 1, sólida, 2,5 pt, com marcador. Prevista: cor 1, **tracejada**, 2 pt (as duas no vermelho, como na Figura 3). Intervalo de 80%: cor 1 50% mais clara, 1 pt. Intervalo de 95%: cor 2, 1 pt, pontilhada. Eixo Y sem forçar o zero; o subtítulo diz "R$ milhões, a preços de" o ano-base e que o eixo não começa no zero. Legenda desligada, rótulos de série ligados |
| 3 | 880, 136, 376 × 120 | Cartão | `[Receita prevista no último ano]` | rótulo "R$ milhões em" o último ano previsto ", a preços de" o ano-base |
| 4 | 880, 272, 376 × 344 | Cartão | `[Texto da previsão]` | 14 pt, quebra de linha, sem rótulo: a frase com o valor e os dois intervalos |
| 5 | 24, 632, 1232 × 80 | Caixa de texto | o aviso abaixo | 10 pt, sobre fundo zebra |

O ano-base é o ano anterior ao primeiro ano previsto em `previsao_receita_total.csv`, o mesmo que a medida `[Ano de partida da previsão]` calcula.

Aviso: "Previsão simples, sem informação de fora da série: repete a tendência recente da receita do município. Não leva em conta mudança de lei, de alíquota, de convênio nem de gestão. O intervalo mostra o quanto o método errou ao prever o passado de municípios do mesmo porte, alargado até a cobertura do teste chegar ao nível prometido. A página "Como ler" mostra quanto ele cobriu em cada ano deixado de fora. Projeto de portfólio feito com dado público."

## Página 4, "Como ler, fontes e limites"

| Tab | Posição (x, y, l × a) | Visual | Campos | Formato |
|---|---|---|---|---|
| 0 | 24, 16, 900 × 40 | Caixa de texto | "Como ler, fontes e limites" | título |
| 1 | 24, 64, 1232 × 360 | Tabela | `dim_indicador[nome]`, `[unidade]`, `[formula]`, `[fonte]`, `[periodicidade]`, `[meta]` | largura fixa por coluna (190, 160, 330, 290, 100 e 130), somando menos que a tabela: sem rolagem lateral; quebra de linha no cabeçalho e nos valores |
| 2 | 24, 440, 400 × 272 | Gráfico de linhas | Eixo X: `backtest_metodos[horizonte]` (categórico). Eixo Y: `[Erro médio absoluto]`. Legenda: `backtest_metodos[metodo_nome]` | o método escolhido (a tendência dos 3 últimos anos) na cor 1, os outros dois na cor 2; título com o nome do método escolhido, lido do TMDL. Sem legenda (os nomes dos métodos não cabiam): o subtítulo diz que o vermelho é o método usado e nomeia os dois em cinza |
| 3 | 440, 440, 400 × 272 | Gráfico de colunas | Eixo X: `backtest_cobertura[origem_fora]` (categórico). Eixo Y: `[Cobertura com ajuste]`, começando no zero | Filtro do visual: `backtest_cobertura[nivel]` = 80 (o menor nível dos CSV). Linha constante tracejada em 80%. A origem com menor cobertura na cor 1, as outras na cor 2 (a mesma conta de `scripts/numeros.py`) |
| 4 | 856, 440, 400 × 272 | Caixa de texto | fontes e licenças (resumo da seção "Fontes" do README) e os cuidados: degrau do Censo 2022 nas séries por habitante; Ideb bienal; município sem rede municipal fica sem Ideb; Municípios parecidos é só porte | 10 pt |

## Ordem de tabulação e acessibilidade

A coluna "Tab" de cada tabela acima é a ordem de tabulação gravada (**Exibir → Painel de seleção → Ordem de tabulação** mostra a mesma): título, segmentação de município, segmentação de Indicador, outras segmentações, visual principal, cartões, tabela, notas. O azul e o vermelho cheios aparecem só em marca e em número grande, nunca em texto pequeno.

## Capturas

Abra o relatório e atualize. As segmentações já abrem no estado de cada captura; confira antes de exportar. O município de exemplo é Ibirá, sorteado com semente fixa (`scripts/comum.py`).

| Arquivo | Página | Estado |
|---|---|---|
| `powerbi/capturas/01-municipio.png` | Município | Ibirá; Indicador "Despesa com saúde por habitante" |
| `powerbi/capturas/02-comparacao.png` | Comparação na faixa | Ibirá; "Despesa com saúde por habitante"; ano 2025 |
| `powerbi/capturas/03-previsao.png` | Previsão da receita | Ibirá |
| `powerbi/capturas/04-como-ler.png` | Como ler, fontes e limites | sem filtro |
| `powerbi/capturas/05-modelo.png` | **Exibição de modelo** (ícone à esquerda) | todas as tabelas à vista, sem sobreposição; `Medidas` num canto |

Como exportar:

1. **Páginas 1 a 4:** **Arquivo → Exportar → Exportar para PDF**. O Desktop não pergunta onde salvar: abre o PDF no navegador, a partir de `%LOCALAPPDATA%\Temp\Power BI Desktop\print-job-…\`; salve-o (ou copie de lá) como `powerbi/capturas/paginas.pdf`. Depois rode `.venv\Scripts\python scripts\capturas.py`, que corta o PDF em um PNG por página, com os nomes da tabela.
2. **Visão de modelo:** a posição de cada tabela vem de `painel-municipios-sp.SemanticModel/diagramLayout.json`, escrito à parte para que todas apareçam sem sobreposição. Não salve o PBIP no Desktop só para mexer nessa visão: o Desktop regrava todos os arquivos do modelo e do relatório no formato dele. O Desktop não exporta essa visão. Use **Win + Shift + S**, recorte a área do diagrama e salve como `powerbi/capturas/05-modelo.png`.

Depois das capturas, avise: o README e o relatório só passam a mostrar o painel a partir daí, e dizem que os visuais são definidos em código (PBIR) sobre modelo em TMDL.
