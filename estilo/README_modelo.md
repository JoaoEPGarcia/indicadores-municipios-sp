<!--
MODELO DE README DO PORTFÓLIO. Copie para a raiz do projeto como README.md
e troque tudo o que está entre <>. Apague estes comentários.

A estrutura é a do README do projeto de gestão hospitalar:
  1. título com a pergunta, e um parágrafo que a diz em uma frase;
  2. a tabela Dados / Painel / Métodos / Entrega / Ferramentas;
  3. principais resultados, cada um com número e com fonte;
  4. como a análise foi feita, em passos numerados;
  5. como reproduzir, com os comandos na ordem;
  6. limitações: o que os dados não autorizam afirmar.
Estrutura do repositório e "In English" são opcionais.

Regras:
  · todo número deste arquivo sai de script e está em NUMEROS_CANONICOS.md;
  · resultado se escreve como afirmação com número ("atendem 32,9% mais"),
    e não como descrição do que foi feito ("comparamos a produção");
  · vírgula decimal e ponto de milhar no texto em português;
  · quem chega aqui pela primeira vez lê só até "Principais resultados":
    o resto é para quem vai conferir ou refazer.
-->

# <Tema do projeto>: <a pergunta que ele responde, em uma linha>?

<Uma pesquisa / análise sobre uma pergunta direta:> **<a pergunta, em uma frase, em negrito?>** <Uma frase sobre o que se compara, em que lugar e em que período.>

| | |
|---|---|
| **Dados** | <volume e origem: "28,3 milhões de registros do <sistema> (2015 a 2025, 2,2 GB)"> |
| **Painel** | <unidade de análise × período = **<n> observações**, e de quantas saíram, "com critérios documentados"> |
| **Métodos** | <os métodos pelo nome, do principal ao de robustez> |
| **Entrega** | <o que foi entregue e para quem: "relatório de <n> páginas escrito para <público> (<mês> de <ano>)"> |
| **Ferramentas** | <Python (pandas, statsmodels, matplotlib), R (<pacotes>) e LaTeX> |

## Principais resultados

Os números abaixo são os do <sumário do relatório> (`<caminho/do/arquivo>`). A fonte de cada número impresso está em `NUMEROS_CANONICOS.md`.

- **<Rótulo curto do achado 1>.** <Afirmação com o número em negrito: "Comparando <grupos equivalentes>, <grupo> **<faz X> <n>% mais**">.
- **<Rótulo curto do achado 2>.** <Afirmação com número e com a comparação que dá escala ao número.>
- **<Rótulo do achado nulo, se houver>: sem diferença.** <O valor de cada lado e a faixa que os dados admitem. Achado nulo também é resultado, e se escreve com a mesma clareza.>
- **<Rótulo curto do achado 4>.** <Afirmação, número e o que move o número.>

## Como a análise foi feita

1. **<Seleção dos dados>.** <De onde sai a amostra e quais exclusões, nesta ordem:>
   1. <critério 1>;
   2. <critério 2>;
   3. <critério 3>.

   <Onde os critérios estão documentados: `<arquivo>`.>
2. **<Etapa 2, pelo nome do método>.** <Uma ou duas frases: o que foi estimado e com que cuidado (réplicas, erro-padrão, especificação).>
3. **<Etapa 3>.** <Idem.>
4. **<Robustez>.** <O que foi refeito de outro jeito para ver se o achado se mantém.>

## Estrutura do repositório (opcional)

| Caminho | O que é |
|---|---|
| `<script_de_leitura.py>` | <leitura dos dados brutos e montagem do painel> |
| `<script_de_analise.py>` | <análise principal: figuras em `figuras/` e tabelas em `tabelas/`> |
| `estilo/` | <kit de estilo do portfólio (`estilo_portfolio.py`, `theme_portfolio.R`)> |
| `relatorio/` | <relatório em LaTeX> |
| `NUMEROS_CANONICOS.md` | de onde sai cada número impresso |

## Como reproduzir

1. Instale as dependências: `pip install <pacotes>` <e, em R, `install.packages(c("<pacotes>"))`>.
2. <Como obter os dados brutos, de onde, e por que não estão versionados (tamanho, licença).>
3. Rode o pipeline nesta ordem:
   ```
   python <script_1>.py
   python <script_2>.py
   ```
4. <Para compilar o relatório: `pdflatex relatorio.tex`, duas passadas.>

<Se houver dado intermediário versionado: "O painel agregado (`<arquivo>`) e todas as saídas derivadas estão versionados. Por isso, a análise pode ser refeita a partir do painel, sem baixar os arquivos brutos.">

## Limitações

- **<O que o desenho não permite>.** <Ex.: "A comparação é observacional: uma diferença entre grupos não prova que o grupo a causou.">
- **<O que os dados não medem>.** <Variável ausente, cobertura incompleta, registro administrativo e não clínico.>
- **<Onde o resultado não se generaliza>.** <Período, região, tipo de unidade fora da amostra.>

## Autoria

- **<Seu nome>**: <papel>. <O que fez.> [LinkedIn](<url>) · [GitHub](<url>)

## In English (opcional)

<Two-sentence summary of the question and the comparison.>

- **Data:** <...>
- **Methods:** <...>
- **Main findings:** <the same numbers as above, with decimal points>
- **Deliverable:** <...>
