# Roteiro do painel no Power BI Desktop

Este roteiro diz o que montar, página por página, sobre o modelo que já vem pronto em `painel-municipios-sp.pbip`, e quais capturas exportar no fim. O modelo semântico (consultas Power Query, relações, medidas DAX e formatos) está em TMDL, em `painel-municipios-sp.SemanticModel/definition/`, e é a fonte única das medidas: este roteiro só diz qual medida vai em qual visual. A tabela `powerbi/conferencia.md` traz o que cada medida tem de devolver, e `scripts/conferir_powerbi.py` confere.

Os termos seguem o `GLOSSARY.md` da raiz: Faixa de porte, Municípios parecidos, Mediana da faixa, Posição na faixa, Intervalo de previsão.

## 0. Antes de abrir

1. **Instale o Power BI Desktop** (gratuito, pela Microsoft Store ou pelo instalador do site da Microsoft).
2. **Instale a Lato no Windows.** Os arquivos estão em `%LOCALAPPDATA%\Programs\MiKTeX\fonts\truetype\typoland\lato\`. Selecione `Lato-Regular.ttf`, `Lato-Bold.ttf`, `Lato-Italic.ttf` e `Lato-BoldItalic.ttf`, clique com o botão direito e escolha **Instalar para todos os usuários**. Feche e reabra o Power BI Desktop depois disso. Sem a Lato, o tema cai para a Segoe UI.
3. **Abra `powerbi/painel-municipios-sp.pbip`** com dois cliques.
4. Se o repositório não estiver em `C:\Users\Pichau\Desktop\indicadores-municipios-sp`, vá em **Página Inicial → Transformar dados → Editar parâmetros** e troque `PastaDados` pelo caminho da pasta `dados\tratados\` da sua cópia, **terminado em barra invertida**.
5. **Página Inicial → Atualizar.** As consultas leem os CSV. A primeira atualização leva alguns segundos.
6. **Confira o modelo antes de montar qualquer visual.** Com o Desktop aberto, rode no terminal, na raiz do repositório:

   ```
   .venv\Scripts\python scripts\conferir_powerbi.py --completo
   ```

   O script deve terminar com todas as células batendo e gravar `powerbi/resultado_conferencia.csv` e `powerbi/resultado_conferencia_completa.csv`. Se alguma célula não bater, o defeito está na medida, e o valor certo está no SQLite. Corrija no Desktop, salve (o TMDL se atualiza) e rode de novo.

**Se o Desktop não abrir o relatório** (mensagem sobre `report.json` ou tema), o modelo continua bom. Feche o Desktop, apague a pasta `painel-municipios-sp.Report`, abra o Desktop, crie um relatório em branco e escolha **Arquivo → Salvar como → Arquivos do projeto do Power BI (.pbip)**, com o nome `painel-municipios-sp`, numa pasta temporária. Copie de lá só a pasta `.Report` para `powerbi/` e abra o `.pbip` de novo. Depois aplique o tema em **Exibir → Temas → Procurar temas → `powerbi/tema.json`**.

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

Todas as relações são 1:N, de direção única. As chaves e os valores brutos ficam ocultos: os visuais usam as dimensões e as medidas. O modelo desencoraja medidas implícitas, então arrastar uma coluna numérica para um visual não a soma: use sempre uma medida.

## Formato comum a todas as páginas

- Tamanho da página: 16:9 (1280 × 720). Fundo branco (o tema já aplica).
- Título da página: caixa de texto, Lato Bold 20, cor de texto do tema.
- **Cor.** O Município selecionado sai na **cor 1 do tema** (vermelho de destaque), só em marca: linha, ponto, contorno. A mediana sai na **cor 2** (cinza neutro). Os quartis saem num cinza mais claro (cor 2, 60% mais clara no seletor). Número grande de cartão sai na cor de texto, e não em vermelho: o tema já faz isso.
- Nenhum visual usa cor de "bom" ou "ruim": nenhum Indicador tem um lado melhor que valha para todo município.
- Texto alternativo em todo visual (**Formato → Geral → Texto alternativo**), dizendo a pergunta que o visual responde.

## Página 1, "Município"

Pergunta: **onde este município está, e onde estão os parecidos?**

| Posição (x, y, l × a) | Visual | Campos | Formato |
|---|---|---|---|
| 24, 16, 640 × 40 | Caixa de texto | "Indicadores do município" | título |
| 24, 64, 320 × 56 | Segmentação, lista suspensa | `dim_municipio[municipio]` | **Seleção única** ligada; pesquisa ligada. Deixe Ibirá escolhido |
| 360, 64, 260 × 56 | Cartão | `[Faixa de porte]` | rótulo "Faixa de porte" |
| 640, 64, 200 × 56 | Cartão | `[Municípios na faixa]` | rótulo "Municípios na faixa" |
| 860, 64, 200 × 56 | Cartão | `[População (Censo 2022)]` | rótulo "População (Censo 2022)" |
| 24, 136, 1232 × 112 | 4 cartões de 296 × 112 (ou um visual **Cartão (novo)** com 4 valores) | `[Último valor]`, cada um filtrado (painel de filtros do visual) a um Indicador: Receita corrente por habitante, Despesa com saúde por habitante, Despesa com educação por habitante, Dependência de transferências. Valor de referência: `[Último valor da faixa]` | rótulo "mediana da faixa" no valor de referência |
| 800, 264, 456 × 160 | Segmentação, botões | `dim_indicador[nome]` | **Seleção única**. No filtro do visual, tire "Receita corrente total (R$ milhões)": ela é da página 3 |
| 24, 264, 760 × 440 | Gráfico de linhas | Eixo X: `dim_ano[ano]`. Eixo Y: `[Valor]`, `[Mediana da faixa]`, `[1º quartil da faixa]`, `[3º quartil da faixa]` | `[Valor]`: cor 1, 2,5 pt, com marcador. Mediana: cor 2, 2 pt. Quartis: cinza claro, 1 pt. Título do visual: **fx → `[Título da evolução]`**. Legenda desligada; ligue **Rótulos de série** (rótulo direto na ponta da linha) |
| 800, 440, 456 × 264 | Tabela | `dim_ano[ano]`, `[Valor formatado]`, `[Mediana da faixa]`, `[Diferença para a mediana]`, `[Posição na faixa]` | linhas em zebra (o tema já faz); sem formatação condicional de cor |
| 24, 708, 1232 × 12 | Caixa de texto | "A sombra cinza vai do 1º ao 3º quartil dos municípios parecidos. Estar acima ou abaixo da mediana não é, por si, bom nem ruim." | 9 pt |

O eixo X mostra anos até o último previsto. No gráfico de linhas, filtre `dim_ano[ano]` para "é menor ou igual a" o último ano observado, ou deixe o eixo cortar sozinho onde as medidas ficam em branco (**Formato → Eixo X → Mostrar itens sem dados** desligado).

## Página 2, "Comparação na faixa"

Pergunta: **o município está no meio ou na ponta do grupo?**

Esta página usa a tabela solta `sel_municipio`, e não `dim_municipio`, na segmentação de município. O motivo: a dispersão tem de mostrar **todos** os Municípios parecidos. Se a segmentação filtrasse `dim_municipio`, sobraria um ponto só. Se a interação fosse desligada (**Editar interações**), a medida que separa a faixa também deixaria de enxergar o município escolhido. A tabela solta resolve os dois lados: ela não filtra nada, e as medidas "do escolhido" a leem.

| Visual | Campos | Formato |
|---|---|---|
| Segmentação, lista suspensa, seleção única | `sel_municipio[municipio]` | Ibirá escolhido |
| Segmentação, botões, seleção única | `dim_indicador[nome]` | **Sincronize com a página 1** (Exibir → Sincronizar segmentações) |
| Segmentação, lista suspensa, seleção única | `dim_ano[ano]` | escolha o último ano em que o Indicador tem dado |
| Gráfico de dispersão | Valores (detalhes): `dim_municipio[municipio]`. Eixo X: `[Valor]`. Eixo Y: `[População (Censo 2022)]`, em **escala logarítmica** | Filtro do visual: `[Na faixa do escolhido]` **é 1**. Cor dos pontos: **fx → Regras → `[É o escolhido]`**: se = 1, cor 1 do tema; senão, cinza claro. Ponto maior para o escolhido: em **Marcadores → Tamanho**, use a mesma regra |
| Cartão | `[Posição do escolhido]` | rótulo "Posição na faixa (0% = menor valor, 100% = maior)" |
| Cartão | `[Valor do escolhido]` | |
| Cartão | `[Mediana da faixa do escolhido]` | |
| Cartão | `[Diferença do escolhido]` | |

Sem ranking por nome: a página mostra posição e grupo, e não uma lista do "pior" ao "melhor".

## Página 3, "Previsão da receita"

Pergunta: **quanto de receita o município pode esperar nos próximos três anos, e com que margem?**

| Visual | Campos | Formato |
|---|---|---|
| Segmentação de município | `dim_municipio[municipio]` | sincronizada com a página 1 |
| Gráfico de linhas | Eixo X: `dim_ano[ano]`. Eixo Y: `[Receita observada]`, `[Receita prevista (linha)]`, `[Limite inferior 80%]`, `[Limite superior 80%]`, `[Limite inferior 95%]`, `[Limite superior 95%]` | Observada: cor 1, sólida, 2,5 pt, com marcador. Prevista: cor 1, **tracejada**, 2 pt. Intervalo de 80%: cor 1, 1 pt. Intervalo de 95%: cor 2, 1 pt, pontilhada. Eixo Y em R$ milhões, sem forçar o zero, e diga isso no subtítulo do visual |
| Cartão | `[Receita prevista no último ano]` | rótulo "R$ milhões, a preços de 2025" |
| Caixa de texto com valor dinâmico | `[Texto da previsão]` (Inserir → Caixa de texto → **+ Valor**) | 14 pt |
| Caixa de texto fixa | o aviso abaixo | 10 pt, sobre fundo zebra |

Aviso (copie como está): "Previsão simples, sem informação de fora da série: repete a tendência recente da receita do município. Não leva em conta mudança de lei, de alíquota, de convênio nem de gestão. O intervalo mostra o quanto o método errou ao prever o passado de municípios do mesmo porte, alargado até a cobertura do teste chegar ao nível prometido. A página "Como ler" mostra quanto ele cobriu em cada ano deixado de fora. Projeto de portfólio feito com dado público."

## Página 4, "Como ler, fontes e limites"

| Visual | Campos |
|---|---|
| Tabela | `dim_indicador[nome]`, `[unidade]`, `[formula]`, `[fonte]`, `[periodicidade]`, `[meta]` |
| Gráfico de linhas | Eixo X: `backtest_metodos[horizonte]`. Eixo Y: `[Erro médio absoluto]`. Legenda: `backtest_metodos[metodo_nome]`. A tendência dos 3 últimos anos na cor 1, os outros dois métodos na cor 2 |
| Gráfico de colunas | Eixo X: `backtest_cobertura[origem_fora]`. Eixo Y: `[Cobertura com ajuste]`. Filtro do visual: `backtest_cobertura[nivel]` = 80. Linha de referência constante em 80% (**Análise → Linha constante**). A origem com menor cobertura na cor 1, as outras na cor 2 (**fx → Regras**) |
| Caixa de texto | Fontes e licenças (resumo da seção "Fontes" do README) e os cuidados: degrau do Censo 2022 nas séries por habitante; Ideb bienal; município sem rede municipal fica sem Ideb |

## Ordem de tabulação e acessibilidade

**Exibir → Painel de seleção → Ordem de tabulação**: segmentação de município, segmentação de Indicador, visual principal, cartões, tabela. O azul e o vermelho cheios aparecem só em marca e em número grande, nunca em texto pequeno.

## Capturas

Salve o relatório. Deixe as segmentações exatamente como abaixo antes de cada captura. O município de exemplo é Ibirá, sorteado com semente fixa (`scripts/comum.py`).

| Arquivo | Página | Estado |
|---|---|---|
| `powerbi/capturas/01-municipio.png` | Município | Ibirá; Indicador "Despesa com saúde por habitante" |
| `powerbi/capturas/02-comparacao.png` | Comparação na faixa | Ibirá; "Despesa com saúde por habitante"; ano 2025 |
| `powerbi/capturas/03-previsao.png` | Previsão da receita | Ibirá |
| `powerbi/capturas/04-como-ler.png` | Como ler, fontes e limites | sem filtro |
| `powerbi/capturas/05-modelo.png` | **Exibição de modelo** (ícone à esquerda) | todas as tabelas à vista, sem sobreposição; `Medidas` num canto |

Como exportar:

1. **Páginas 1 a 4:** **Arquivo → Exportar → Exportar para PDF**, salvando `powerbi/capturas/paginas.pdf`. Depois rode `.venv\Scripts\python scripts\capturas.py`, que corta o PDF em um PNG por página, com os nomes da tabela.
2. **Visão de modelo:** o Desktop não exporta essa visão. Use **Win + Shift + S**, recorte a área do diagrama e salve como `powerbi/capturas/05-modelo.png`.

Depois das capturas, avise: o README e o relatório só passam a mostrar o painel montado a partir daí.
