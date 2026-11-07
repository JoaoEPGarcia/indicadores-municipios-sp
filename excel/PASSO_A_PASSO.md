# Passo a passo: refazer a planilha à mão

Este guia refaz, no Excel e sem script, a planilha `painel-municipios-sp.xlsx`: Power Query para trazer os dados, PROCX para o painel, tabela dinâmica para explorar. O `scripts/montar_excel.py` faz exatamente estes passos pelo Excel, e o `scripts/conferir_excel.py` confere o resultado. Use o mesmo conferidor na sua versão (passo 9).

**Precisa de:** Excel 365 ou 2021 (PROCX, LET e SEQUÊNCIA não existem antes disso) e a pasta `dados\tratados\` do repositório.

**Convenções do Excel em português:** argumentos separados por **ponto e vírgula**, vírgula decimal. As fórmulas abaixo já estão assim. Mantenha as células nas posições indicadas: o conferidor lê `Painel!C4`, `Painel!D13:H19` e `Previsão!B8:H21`.

---

## 1. O parâmetro com a pasta dos dados

1. Abra uma pasta de trabalho em branco. **Dados → Obter Dados → Iniciar Editor do Power Query**.
2. No editor: **Página Inicial → Gerenciar Parâmetros → Novo Parâmetro**.
   - Nome: `PastaDados`
   - Tipo: **Texto**
   - Valor Atual: o caminho da sua pasta `dados\tratados\`, **terminado em barra invertida**. Exemplo: `C:\Users\Pichau\Desktop\indicadores-municipios-sp\dados\tratados\`
3. **OK.**

Por que um parâmetro: se a pasta mudar, você troca num lugar só, e todas as consultas acompanham.

## 2. Uma função que lê qualquer CSV do projeto

Os cinco CSV têm o mesmo formato (UTF-8, vírgula como separador, cabeçalho na primeira linha). Em vez de repetir a importação cinco vezes, crie uma função.

1. **Página Inicial → Nova Fonte → Outras Fontes → Consulta Nula.**
2. **Página Inicial → Editor Avançado**, apague o que houver e digite:

   ```m
   (arquivo as text) as table =>
   let
       Fonte = Csv.Document(File.Contents(PastaDados & arquivo), [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
       Cabecalho = Table.PromoteHeaders(Fonte, [PromoteAllScalars = true])
   in
       Cabecalho
   ```

   `Encoding = 65001` é o UTF-8: sem ele, "Ibirá" vira "IbirÃ¡".
3. **Concluído.** No painel **Consultas** à esquerda, renomeie a consulta para `LerCsv` (dois cliques no nome).

## 3. As cinco consultas

Para cada linha da tabela abaixo:

1. **Nova Fonte → Outras Fontes → Consulta Nula.**
2. Na barra de fórmulas, digite `= LerCsv("nome-do-arquivo.csv")` e tecle Enter.
3. Renomeie a consulta.
4. **Tipos com a localidade certa.** Este é o passo que mais quebra num Windows em português: o CSV usa **ponto** decimal, e o Excel em pt-BR lê `5176.4883` como cinco milhões. Selecione as colunas numéricas, clique com o botão direito → **Alterar Tipo → Usando Localidade…** → Tipo de Dados: **Número Decimal** (ou **Número Inteiro**) e Localidade: **Inglês (Estados Unidos)**. As colunas de texto ficam como **Texto** (botão direito → Alterar Tipo → Texto).

| Consulta | Arquivo | Inteiro (localidade EUA) | Decimal (localidade EUA) |
|---|---|---|---|
| `Municipios` | `dim_municipio.csv` | `cod_ibge`, `populacao_censo_2022` | — |
| `Indicadores` | `dim_indicador.csv` | `casas`, `ordem` | — |
| `Fato` | `indicadores_longo.csv` | `cod_ibge`, `ano` | `valor` |
| `Referencia` | `referencia_faixa.csv` | `ano`, `n` | `minimo`, `maximo`, `media`, `p25`, `mediana`, `p75` |
| `Previsao` | `previsao_receita_total.csv` | `cod_ibge`, `ano` | `previsto`, `inferior_80`, `superior_80`, `inferior_95`, `superior_95` |

**Confira:** na consulta `Fato`, a primeira linha de Adamantina, `dependencia_transf`, 2015, deve mostrar `57,27` (e não `5.726.642.839…`).

## 4. Mesclar o nome do Indicador na consulta Fato

A tabela Fato só tem o código (`receita_pc`). Para a tabela dinâmica mostrar o nome, traga-o da consulta Indicadores, como um PROCV feito uma vez só, na carga.

1. Selecione a consulta `Fato`. **Página Inicial → Mesclar Consultas** (não "como nova").
2. Tabela de cima: `Fato`, clique na coluna `indicador_id`. Tabela de baixo: `Indicadores`, clique em `indicador_id`. Tipo de Junção: **Externa esquerda**. **OK.**
3. Na nova coluna `Indicadores`, clique no ícone de expandir (duas setas), marque **só `nome`**, desmarque "Usar o nome da coluna original como prefixo". **OK.**
4. Renomeie a coluna `nome` para `indicador`.

## 5. Carregar as tabelas

1. **Página Inicial → Fechar e Carregar → Fechar e Carregar Para…** → **Tabela**, **Nova planilha**. O Excel cria uma aba por consulta (o parâmetro e a função não são carregados).
2. Em cada aba, clique numa célula da tabela → **Design da Tabela → Nome da Tabela** e renomeie, e renomeie a aba:

| Consulta | Nome da tabela | Nome da aba |
|---|---|---|
| Municipios | `tMunicipios` | Municípios |
| Indicadores | `tIndicadores` | Indicadores |
| Fato | `tFato` | Dados |
| Referencia | `tReferencia` | Referência |
| Previsao | `tPrevisao` | Previsões |

3. **Fórmulas → Gerenciador de Nomes → Novo:**
   - Nome `ListaMunicipios`, refere-se a `=tMunicipios[municipio]`
   - Nome `ListaIndicadores`, refere-se a `=tIndicadores[nome]`

## 6. A aba Painel

Crie uma aba `Painel`. Em **Exibir**, desmarque **Linhas de Grade**.

### 6.1 Escolha do município e cartões

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

### 6.2 Tabela dos sete Indicadores

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

**O truque do PROCX com várias condições (E13 e F13).** `(tFato[cod_ibge]=$C$5)` devolve uma lista de VERDADEIRO e FALSO, uma por linha da tabela. Multiplicar três listas dá 1 só na linha em que as três condições valem, e 0 nas outras. O PROCX procura o 1. É o jeito de fazer PROCV com chave composta sem criar coluna auxiliar.

**LET (D13 e H13)** dá nome a um resultado intermediário, para não repetir a conta e para a fórmula se ler.

**Posição na faixa (H13):**

```
=LET(v; E13; ano; $D13; ind; $A13; faixa; $C$6;
     n; PROCX(1; (tReferencia[faixa_porte]=faixa)*(tReferencia[ano]=ano)*(tReferencia[indicador_id]=ind); tReferencia[n]; 0);
     menores; SOMARPRODUTO((tFato[faixa_porte]=faixa)*(tFato[ano]=ano)*(tFato[indicador_id]=ind)*(tFato[valor]<v));
     SE(E(ÉNÚM(v); n>1); menores/(n-1); "n.d."))
```

Quantos municípios da faixa têm valor menor, dividido por (n − 1): 0% é o menor da faixa, 100% o maior, igual ao `PERCENT_RANK` do SQL e à medida `[Posição na faixa]` do Power BI. Use SOMARPRODUTO, e não `CONT.SES(...; "<"&E13)`: o CONT.SES transforma o número em texto para comparar e pode errar no último dígito, contando o próprio município como "menor".

Pinte de cinza-claro (F4F4F4) as linhas 13, 15, 17 e 19. Em B21, escreva a regra de leitura: "A mediana é a dos municípios do mesmo porte (Censo 2022) no mesmo ano. Estar acima ou abaixo da mediana não é, por si, bom nem ruim."

### 6.3 Gráfico de um Indicador

| Célula | Conteúdo |
|---|---|
| B24 | `Indicador do gráfico (escolha na lista)` |
| C24 | Validação de Dados, lista, Fonte `=ListaIndicadores`. Escolha "Receita corrente por habitante" |
| D24 | `=PROCX($C$24; tIndicadores[nome]; tIndicadores[indicador_id]; "")` (fonte cinza) |
| B25 | `=$C$24&": "&$C$4&" e a mediana dos "&$C$7&" municípios da faixa"` (vai virar o título do gráfico) |

Dados do gráfico, a partir da linha 46:

| Célula | Conteúdo |
|---|---|
| C46 | `=SEQUÊNCIA(1; 11; 2015)`. A fórmula "derrama" os anos de 2015 a 2025 até M46 |
| B47 / C47 | `Município` / `=PROCX(1; (tFato[cod_ibge]=$C$5)*(tFato[ano]=C$46)*(tFato[indicador_id]=$D$24); tFato[valor]; NÃO.DISP())` |
| B48 / C48 | `Mediana da faixa` / `=PROCX(1; (tReferencia[faixa_porte]=$C$6)*(tReferencia[ano]=C$46)*(tReferencia[indicador_id]=$D$24); tReferencia[mediana]; NÃO.DISP())` |
| B49 / C49 | `1º quartil da faixa` / a mesma de C48, com `tReferencia[p25]` |
| B50 / C50 | `3º quartil da faixa` / a mesma de C48, com `tReferencia[p75]` |

Arraste C47:C50 até a coluna M. `NÃO.DISP()` (o `#N/D`) é de propósito: o gráfico de linhas pula o ponto, em vez de desenhar um zero que não existe (o Ideb é bienal).

O gráfico:

1. Selecione B46:M50 → **Inserir → Gráfico de Linhas**. Arraste-o para B27.
2. **Cores** (botão direito na linha → Formatar Série de Dados → Linha):
   - Município: vermelho `E41A1C`, 2,5 pt, marcador círculo vermelho com borda branca;
   - Mediana: cinza `ACA9AE`, 2 pt, sem marcador;
   - quartis: cinza-claro `E6E6E7`, 1 pt, sem marcador.
3. Nome da série do município ligado à célula: **Selecionar Dados → Município → Editar → Nome da série: `=Painel!$C$4`**.
4. **Título ligado à célula:** clique no título, digite `=` na barra de fórmulas, clique em B25 e Enter.
5. Grade horizontal tracejada e cinza-clara; sem borda no gráfico; legenda embaixo.

## 7. A aba Explorar (tabela dinâmica)

1. Crie a aba `Explorar`. Clique em B8 → **Inserir → Tabela Dinâmica → Da Tabela/Intervalo** → Tabela/Intervalo: `tFato` → Planilha Existente. **OK.**
2. Arraste: `ano` para **Linhas**, `indicador` para **Colunas**, `valor` para **Valores**, `municipio` para **Filtros**.
3. Em Valores, clique em "Soma de valor" → **Configurações do Campo de Valor → Média**, Nome personalizado `Valor (média)` → **Formato do Número → Número, 1 casa, separador de milhar**.
4. **Design → Totais Gerais → Desabilitado para Linhas e Colunas** (média de Indicadores com unidades diferentes não quer dizer nada).
5. **Análise da Tabela Dinâmica → Inserir Segmentação de Dados → `municipio`.** Escolha Ibirá.

Com um município escolhido, cada célula é o valor da fonte (há uma linha por município, ano e Indicador). Sem município escolhido, a célula vira a média de todos, que não é o que se quer: deixe sempre um município marcado.

## 8. A aba Previsão

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
     p; ÍNDICE($D$8:$D$21; linha); lo8; ÍNDICE($E$8:$E$21; linha); hi8; ÍNDICE($F$8:$F$21; linha);
     lo9; ÍNDICE($G$8:$G$21; linha); hi9; ÍNDICE($H$8:$H$21; linha);
     SEERRO("Em "&a&", a receita corrente de "&m&" fica perto de R$ "&DEF.NÚM.DEC(p; 1)&" milhões (a preços de "&$D$4&"). No intervalo de 80% do teste contra o passado, entre R$ "&DEF.NÚM.DEC(lo8; 1)&" e R$ "&DEF.NÚM.DEC(hi8; 1)&" milhões; no de 95%, entre R$ "&DEF.NÚM.DEC(lo9; 1)&" e R$ "&DEF.NÚM.DEC(hi9; 1)&" milhões.";
            "Este município não tem os anos recentes de receita válidos: sem previsão."))
```

Use `DEF.NÚM.DEC`, e não `TEXTO(p; "#.##0,0")`: o código de formato do TEXTO é escrito no idioma de quem digita e quebra quando a planilha abre num Excel em inglês. O DEF.NÚM.DEC segue o idioma de quem abre.

Em B24, o aviso, sobre fundo cinza-claro: "Previsão simples, sem informação de fora da série: repete a tendência recente da receita do município. Não leva em conta mudança de lei, de alíquota, de convênio nem de gestão. O intervalo mostra o quanto o método errou ao prever o passado de municípios do mesmo porte. Projeto de portfólio feito com dado público."

O gráfico: selecione B7:H21 → **Inserir → Gráfico de Linhas**. Observada em vermelho 2,5 pt com marcador; prevista em vermelho tracejado 2 pt; limites de 80% em vermelho 1 pt; limites de 95% em cinza 1 pt pontilhado. Título ligado a `=Previsão!$B$2`.

## 9. Conferir

Salve o arquivo, por exemplo `excel\minha-versao.xlsx`, feche o Excel e rode, na raiz do repositório:

```
.venv\Scripts\python scripts\conferir_excel.py --arquivo excel\minha-versao.xlsx
```

O script escolhe quatro municípios em `Painel!C4`, um de cada vez, manda o Excel recalcular e compara cada célula da tabela do Painel e da aba Previsão com o SQLite. No fim, ele diz quantas células batem. Se alguma divergir, a mensagem diz o município, a aba, o Indicador ou o ano, e o valor esperado.

## Para onde ir depois

- **Atualizar com dados novos:** rode os scripts do projeto (README, "Como reproduzir"), abra a planilha e clique em **Dados → Atualizar Tudo**. As consultas releem os CSV, e as fórmulas e a tabela dinâmica acompanham.
- **Outra pasta:** **Dados → Consultas e Conexões → botão direito em PastaDados → Editar** e troque o valor.
