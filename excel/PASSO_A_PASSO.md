# Passo a passo: refazer a planilha à mão

Este guia refaz, no Excel para a web e sem script, a planilha `painel-municipios-sp.xlsx`: tabelas nomeadas com os dados, PROCX para o painel, tabela dinâmica para explorar. A versão de referência é gerada por `scripts/montar_excel.py` (Python) e completada no Excel para a web, onde se insere a tabela dinâmica e onde as fórmulas são calculadas (ver `docs/adr/0004-planilha-sem-power-query.md`). O `scripts/conferir_excel.py` confere o resultado. Use o mesmo conferidor na sua versão (passo 9).

**Precisa de:** Excel para a web (Microsoft 365) ou Excel 365/2021 no computador (PROCX, LET e SEQUÊNCIA não existem antes disso) e a pasta `dados\tratados\` do repositório.

**Sem Power Query.** O Excel para a web desta conta não tem "Obter Dados" (só "Consultas e Conexões") nem Office Scripts. Os dados entram copiados para tabelas, e a ligação com os CSV fica no script. O Power Query aparece no modelo do Power BI.

**Convenções do Excel em português:** argumentos separados por **ponto e vírgula**, vírgula decimal. As fórmulas abaixo já estão assim. Mantenha as células nas posições indicadas: o conferidor lê `Painel!C4`, `Painel!C5`, `Painel!D13:H19` e `Previsão!B8:H21`.

Comece de uma **pasta de trabalho em branco**, e não de uma cópia da planilha de referência: a de referência leva uma marca (o nome definido `OrigemDaPlanilha`) que faz o conferidor gravar o resultado do README.

---

## 1. Os dados em cinco tabelas

Os cinco CSV têm o mesmo formato: UTF-8, vírgula como separador, ponto decimal, cabeçalho na primeira linha.

| Arquivo | Nome da aba | Nome da tabela |
|---|---|---|
| `dim_indicador.csv` | Indicadores | `tIndicadores` |
| `dim_municipio.csv` | Municípios | `tMunicipios` |
| `indicadores_longo.csv` | Dados | `tFato` |
| `referencia_faixa.csv` | Referência | `tReferencia` |
| `previsao_receita_total.csv` | Previsões | `tPrevisao` |

Para cada linha da tabela:

1. Crie a aba com o nome indicado (botão **+** embaixo, dois cliques no nome para renomear).
2. **Abra o CSV e copie para uma tabela.** O Excel para a web não importa CSV para dentro de uma pasta de trabalho aberta. O caminho que funciona sem Power Query é abrir o CSV e copiar tudo (Ctrl+A, Ctrl+C) para a célula A1 da aba nova (Ctrl+V).
3. **Confira o ponto decimal.** Este é o passo que mais quebra num Excel em português: o CSV usa **ponto** decimal, e o Excel em pt-BR pode ler `5176.4883` como texto, ou como cinco milhões. Antes de colar, troque a localidade da pasta de trabalho para inglês: **Arquivo → Opções → Configurações de Formato Regional → Inglês (Estados Unidos)**. Depois de colar todas as tabelas, volte para **Português (Brasil)**: os números ficam números, e passam a aparecer com vírgula. Se o seu Excel não tiver essa opção, abra o CSV num Excel já configurado em inglês, ou copie as abas de dados da planilha de referência: elas são os CSV sem mudança.
4. Clique numa célula dos dados → **Inserir → Tabela** → marque **Minha tabela tem cabeçalhos**. Em **Design da Tabela → Nome da Tabela**, dê o nome indicado.

**Confira:** na tabela `tFato`, a primeira linha de Adamantina, `dependencia_transf`, 2015, deve mostrar `57,27` (e não `5.726.642.839…` nem um texto alinhado à esquerda).

Por que tabela nomeada: a fórmula lê `tFato[valor]`, e não `Dados!F2:F50414`. Se a tabela crescer com dado novo, as fórmulas acompanham sem mudar nada.

## 2. O nome do Indicador ao lado do código

A tabela `tFato` só tem o código (`receita_pc`). Para a tabela dinâmica mostrar o nome, traga-o da tabela `tIndicadores`, como um PROCV feito uma vez só.

Na primeira coluna vazia à direita da `tFato`, escreva o cabeçalho `indicador` e, na primeira linha de dados:

```
=PROCX([@indicador_id]; tIndicadores[indicador_id]; tIndicadores[nome])
```

A tabela copia a fórmula para todas as linhas sozinha (coluna calculada). Na versão de referência, o script já grava o nome como valor, que dá o mesmo resultado.

## 3. As listas de escolha

**Fórmulas → Definir Nome** (ou **Gerenciador de Nomes → Novo**):

- Nome `ListaMunicipios`, refere-se a `=tMunicipios[municipio]`
- Nome `ListaIndicadores`, refere-se a `=tIndicadores[nome]`

Por que um nome: a Validação de Dados aceita um nome definido como fonte da lista, e o nome acompanha a tabela se ela crescer.

## 4. A aba Painel

Crie uma aba `Painel`. Em **Exibir**, desmarque **Linhas de Grade**.

### 4.1 Escolha do município e cartões

| Célula | Conteúdo |
|---|---|
| B4 | `Município (escolha na lista)` |
| C4 | **Dados → Validação de Dados → Permitir: Lista → Fonte: `=ListaMunicipios`**. Escolha Ibirá. Pinte o fundo de azul-claro: é a célula onde o leitor mexe |
| B5 / C5 | `Código IBGE` / `=PROCX($C$4; tMunicipios[municipio]; tMunicipios[cod_ibge]; "escolha um município")` |
| B6 / C6 | `Faixa de porte (municípios parecidos)` / `=PROCX($C$4; tMunicipios[municipio]; tMunicipios[faixa_porte]; "")` |
| B7 / C7 | `Municípios na faixa` / `=CONT.SES(tMunicipios[faixa_porte]; $C$6)` |
| B8 / C8 | `População (Censo 2022)` / `=PROCX($C$4; tMunicipios[municipio]; tMunicipios[populacao_censo_2022]; "")` |
| B9 / C9 | `Região geográfica imediata (IBGE)` / `=PROCX($C$4; tMunicipios[municipio]; tMunicipios[regiao_imediata]; "")` |

PROCX tem a forma `PROCX(o_que_procurar; onde_procurar; o_que_devolver; se_não_achar)`. Diferente do PROCV, a coluna devolvida não precisa estar à direita, e o "não achei" vem no próprio PROCX, sem SEERRO.

### 4.2 Tabela dos sete Indicadores

Cabeçalhos na linha 12, de B a H: `Indicador`, `Unidade`, `Último ano com dado`, `Valor do município`, `Mediana da faixa`, `Diferença para a mediana`, `Posição na faixa (0% a 100%)`.

Na coluna A, de A13 a A19, digite os códigos, um por linha, nesta ordem: `receita_pc`, `dependencia_transf`, `saude_pc`, `educacao_pc`, `pib_pc`, `ideb`, `pre_natal_7mais`. Fonte pequena e cinza: as fórmulas da linha leem esse código.

Na linha 13, digite as fórmulas abaixo. Depois selecione B13:H13 e arraste até a linha 19.

| Célula | Fórmula | Formato |
|---|---|---|
| B13 | `=PROCX($A13; tIndicadores[indicador_id]; tIndicadores[nome])` | |
| C13 | `=PROCX($A13; tIndicadores[indicador_id]; tIndicadores[unidade])` | |
| D13 | `=LET(a; MÁXIMOSES(tFato[ano]; tFato[cod_ibge]; $C$5; tFato[indicador_id]; $A13); SE(a=0; "n.d."; a))` | `0` |
| E13 | `=PROCX(1; (tFato[cod_ibge]=$C$5)*(tFato[ano]=$D13)*(tFato[indicador_id]=$A13); tFato[valor]; "n.d.")` | `#.##0,0` |
| F13 | `=PROCX(1; (tReferencia[faixa_porte]=$C$6)*(tReferencia[ano]=$D13)*(tReferencia[indicador_id]=$A13); tReferencia[mediana]; "n.d.")` | `#.##0,0` |
| G13 | `=SE(E(ÉNÚM(E13); ÉNÚM(F13)); E13/F13-1; "n.d.")` | `+0,0%;-0,0%;0,0%` |
| H13 | ver abaixo | `0%` |

Os formatos ficam em **Página Inicial → Formato de Número → Mais Formatos de Número → Personalizado**.

**O truque do PROCX com várias condições (E13 e F13).** `(tFato[cod_ibge]=$C$5)` devolve uma lista de VERDADEIRO e FALSO, uma por linha da tabela. Multiplicar três listas dá 1 só na linha em que as três condições valem, e 0 nas outras. O PROCX procura o 1. É o jeito de fazer PROCV com chave composta sem criar coluna auxiliar.

**LET (D13 e H13)** dá nome a um resultado intermediário, para não repetir a conta e para a fórmula se ler. Os nomes não podem parecer endereço de célula: `inf80` seria a coluna INF, linha 80. Por isso a frase da Previsão usa `inf_80`.

**Posição na faixa (H13):**

```
=LET(v; E13; ano; $D13; ind; $A13; faixa; $C$6;
     n; PROCX(1; (tReferencia[faixa_porte]=faixa)*(tReferencia[ano]=ano)*(tReferencia[indicador_id]=ind); tReferencia[n]; 0);
     menores; SOMARPRODUTO((tFato[faixa_porte]=faixa)*(tFato[ano]=ano)*(tFato[indicador_id]=ind)*(tFato[valor]<v));
     SE(E(ÉNÚM(v); n>1); menores/(n-1); "n.d."))
```

Quantos municípios da faixa têm valor menor, dividido por (n − 1): 0% é o menor da faixa, 100% o maior, igual ao `PERCENT_RANK` do SQL e à medida `[Posição na faixa]` do Power BI. Use SOMARPRODUTO, e não `CONT.SES(...; "<"&E13)`: o CONT.SES transforma o número em texto para comparar e pode errar no último dígito, contando o próprio município como "menor".

Pinte de cinza-claro (F4F4F4) as linhas 13, 15, 17 e 19. Em B21, escreva a regra de leitura: "A mediana é a dos municípios do mesmo porte (Censo 2022) no mesmo ano. Estar acima ou abaixo da mediana não é, por si, bom nem ruim."

### 4.3 Gráfico de um Indicador

| Célula | Conteúdo |
|---|---|
| B24 | `Indicador do gráfico (escolha na lista)` |
| C24 | Validação de Dados, lista, Fonte `=ListaIndicadores`. Escolha "Receita corrente por habitante" |
| D24 | `=PROCX($C$24; tIndicadores[nome]; tIndicadores[indicador_id]; "")` (fonte cinza) |
| B25 | `=$C$24&": "&$C$4&" e a mediana dos "&$C$7&" municípios da faixa"` (o título do gráfico) |

Dados do gráfico, a partir da linha 46:

| Célula | Conteúdo |
|---|---|
| C46 | `=SEQUÊNCIA(1; 11; 2015)`. A fórmula "derrama" os anos de 2015 a 2025 até M46 |
| B47 / C47 | `Município` / `=PROCX(1; (tFato[cod_ibge]=$C$5)*(tFato[ano]=C$46)*(tFato[indicador_id]=$D$24); tFato[valor]; NÃO.DISP())` |
| B48 / C48 | `Mediana da faixa` / `=PROCX(1; (tReferencia[faixa_porte]=$C$6)*(tReferencia[ano]=C$46)*(tReferencia[indicador_id]=$D$24); tReferencia[mediana]; NÃO.DISP())` |
| B49 / C49 | `1º quartil da faixa` / a mesma de C48, com `tReferencia[p25]` |
| B50 / C50 | `3º quartil da faixa` / a mesma de C48, com `tReferencia[p75]` |

Arraste C47:C50 até a coluna M. `NÃO.DISP()` (o `#N/D`) é de propósito: o gráfico de linhas pula o ano sem dado, em vez de desenhar um zero que não existe (o Ideb é bienal).

O gráfico:

1. Selecione B46:M50 → **Inserir → Linha**. Arraste-o para B27.
2. **Cores** (clique na linha → **Formatar** → painel à direita → Linha):
   - Município: vermelho `E41A1C`, 2,5 pt, marcador círculo vermelho com borda branca;
   - Mediana: cinza `ACA9AE`, 2 pt, sem marcador;
   - quartis: cinza-claro `E6E6E7`, 1 pt, sem marcador.
3. Nome da série do município ligado à célula `=Painel!$C$4` (**Selecionar Dados → série → Nome**), para a legenda trocar com o município.
4. Título ligado a B25 (clique no título, `=` na barra de fórmulas, clique em B25). Se o Excel para a web não deixar ligar o título ou o nome da série a uma célula, escreva-os à mão: o que se perde é só a troca automática do texto. Na versão de referência, o script grava as duas ligações.
5. Grade horizontal tracejada e cinza-clara; sem borda no gráfico; legenda embaixo.

## 5. A aba Explorar (tabela dinâmica)

Na versão de referência, este é o passo feito à mão no Excel para a web, sobre a planilha que o script gera.

1. Crie a aba `Explorar` (na de referência ela já existe, com as instruções nas linhas 1 a 6). Clique em **D8** → **Inserir → Tabela Dinâmica** → tabela `tFato` → **Planilha existente**, `Explorar!$D$8`. **OK.**
2. No painel **Campos da Tabela Dinâmica**, arraste: `ano` para **Linhas**, `indicador` para **Colunas**, `valor` para **Valores**.
3. Em Valores, clique em "Soma de valor" → **Configurações do Campo de Valor → Média**, nome `Valor (média)`; formato de número com 1 casa e separador de milhar.
4. **Design → Totais Gerais → Desabilitado para Linhas e Colunas** (média de Indicadores com unidades diferentes não quer dizer nada).
5. Com a tabela dinâmica selecionada, **Inserir → Segmentação de Dados → `municipio`**. Arraste a segmentação para a coluna B, a partir da linha 8, à esquerda da tabela dinâmica. Escolha Ibirá.

Com um município escolhido, cada célula é o valor da fonte (há uma linha por município, ano e Indicador). Sem município escolhido, a célula vira a média de todos, que não é o que se quer: deixe sempre um município marcado.

## 6. A aba Previsão

| Célula | Conteúdo |
|---|---|
| B2 | `="Município: "&Painel!$C$4&" (troque na aba Painel). R$ milhões a preços de "&$D$4&"."` |
| B4 / D4 | `Último ano observado` / `=MÍNIMO(tPrevisao[ano])-1` |
| B5 / D5 | `Último ano previsto` / `=MÁXIMO(tPrevisao[ano])` |
| B7:H7 | `Ano`, `Receita observada`, `Receita prevista`, `Limite inferior 80%`, `Limite superior 80%`, `Limite inferior 95%`, `Limite superior 95%` |
| B8 | `=SEQUÊNCIA(14; 1; MÍNIMO(tFato[ano]))` (derrama de 2015 a 2028) |
| C8 | `=PROCX(1; (tFato[cod_ibge]=Painel!$C$5)*(tFato[ano]=$B8)*(tFato[indicador_id]="receita_total"); tFato[valor]; NÃO.DISP())` |
| D8 | `=SE($B8=$D$4; $C8; PROCX(1; (tPrevisao[cod_ibge]=Painel!$C$5)*(tPrevisao[ano]=$B8); tPrevisao[previsto]; NÃO.DISP()))` |
| E8 a H8 | a mesma de D8, trocando `previsto` por `inferior_80`, `superior_80`, `inferior_95`, `superior_95` |

Arraste C8:H8 até a linha 21. O `SE($B8=$D$4; $C8; ...)` repete o último valor observado no ano de partida, para a linha prevista sair do ponto real, e não do nada.

A frase, em B23 (mesclada até H23, com quebra de texto):

```
=LET(a; $D$5; m; Painel!$C$4; linha; CORRESP(a; $B$8:$B$21; 0);
     p; ÍNDICE($D$8:$D$21; linha); inf_80; ÍNDICE($E$8:$E$21; linha); sup_80; ÍNDICE($F$8:$F$21; linha);
     inf_95; ÍNDICE($G$8:$G$21; linha); sup_95; ÍNDICE($H$8:$H$21; linha);
     SEERRO("Em "&a&", a receita corrente de "&m&" fica perto de R$ "&DEF.NÚM.DEC(p; 1)&" milhões (a preços de "&$D$4&"). No intervalo de 80% do teste contra o passado, entre R$ "&DEF.NÚM.DEC(inf_80; 1)&" e R$ "&DEF.NÚM.DEC(sup_80; 1)&" milhões; no de 95%, entre R$ "&DEF.NÚM.DEC(inf_95; 1)&" e R$ "&DEF.NÚM.DEC(sup_95; 1)&" milhões.";
            "Este município não tem os anos recentes de receita válidos: sem previsão."))
```

Use `DEF.NÚM.DEC`, e não `TEXTO(p; "#.##0,0")`: o código de formato do TEXTO é escrito no idioma de quem digita e quebra quando a planilha abre num Excel em inglês. O DEF.NÚM.DEC segue o idioma de quem abre.

Em B24, o aviso, sobre fundo cinza-claro: "Previsão simples, sem informação de fora da série: repete a tendência recente da receita do município. Não leva em conta mudança de lei, de alíquota, de convênio nem de gestão. O intervalo mostra o quanto o método errou ao prever o passado de municípios do mesmo porte. Projeto de portfólio feito com dado público."

O gráfico: selecione B7:H21 → **Inserir → Linha**, e ponha-o a partir de J7. Observada em vermelho 2,5 pt com marcador; prevista em vermelho tracejado 2 pt; limites de 80% em vermelho 1 pt; limites de 95% em cinza 1 pt pontilhado. Título ligado a `=Previsão!$B$2` (ou escrito à mão, como no passo 4.3).

## 7. Leia-me e Fontes e licenças

Uma aba `Leia-me` no começo, com o que é a planilha, como usar, de onde vêm os números e os cuidados de leitura; uma aba `Fontes e licenças` com base, órgão, o que foi usado e a condição de uso encontrada. A ordem das abas da versão de referência: Leia-me, Painel, Explorar, Previsão, Indicadores, Fontes e licenças, e por último as de dados (Municípios, Dados, Referência, Previsões).

## 8. Baixar a cópia calculada

O conferidor não calcula fórmulas: ele lê o valor que o Excel guardou no arquivo. E o arquivo guarda só o município que estava escolhido em `Painel!C4`. Por isso, uma cópia por município:

1. Em `Painel!C4`, escolha o município. Espere as fórmulas calcularem (a tabela e a Previsão mudam).
2. **Arquivo → Salvar como → Baixar uma Cópia.** Renomeie o arquivo com o nome do município, por exemplo `minha-versao-ibira.xlsx`.
3. Repita para Franco da Rocha, Morro Agudo e Santa Lúcia (os três de `powerbi/conferencia.md`).

Na versão de referência, as quatro cópias ficam em `excel/calculadas/`, e é lá que o conferidor procura quando roda sem argumentos.

## 9. Conferir

Na raiz do repositório:

```
.venv\Scripts\python scripts\conferir_excel.py --arquivo minha-versao-ibira.xlsx minha-versao-franco.xlsx minha-versao-morro.xlsx minha-versao-santa-lucia.xlsx
```

Para cada arquivo, o script lê o município de `Painel!C4` e compara cada célula da tabela do Painel e da aba Previsão com o SQLite. No fim, ele diz quantas células batem e quais municípios da conferência faltaram. Se alguma divergir, a mensagem diz o município, a aba, o Indicador ou o ano, e o valor esperado. Um arquivo que nunca passou pelo Excel (sem valores guardados) é recusado com aviso. Conferir a sua versão não muda os números do README: só a planilha de referência grava o resultado.

## Para onde ir depois

- **Atualizar com dados novos:** rode os scripts do projeto (README, "Como reproduzir"), depois `python scripts/montar_excel.py`, suba o arquivo novo para o Excel para a web e refaça o passo 5 (tabela dinâmica e segmentação). Na sua versão à mão, cole os CSV novos por cima das tabelas (passo 1): as fórmulas e a tabela dinâmica acompanham (na tabela dinâmica, botão direito → **Atualizar**).
