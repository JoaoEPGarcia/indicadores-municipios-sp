# A referência da faixa é uma segunda tabela fato, e a faixa chega por TREATAS

A especificação original deixava `ref_faixa` (mediana e quartis por Faixa de porte, ano e Indicador) solta no modelo e filtrava as três colunas dentro de cada medida, porque o Power BI não relaciona por chave composta. Decidimos relacionar `ref_faixa` a `dim_ano` e a `dim_indicador` por coluna simples (muitos para um, direção única). Assim, ela vira uma segunda tabela fato, em outro grão, que compartilha dimensões com `fato_indicador`. A Faixa de porte do Município selecionado chega por `TREATAS(VALUES(dim_municipio[faixa_porte]), ref_faixa[faixa_porte])`. Os motivos: o ano e o Indicador do contexto passam a filtrar sozinhos, as medidas ficam mais curtas e o modelo mostra uma estrela com duas fatos e dimensões conformes.

## Considered Options

- **Tabela solta com `CALCULATE` nas três colunas** (a especificação original): funciona, mas repete três `SELECTEDVALUE` em cada medida e não mostra o modelo.
- **Uma `dim_faixa` ligada a `dim_municipio` e a `ref_faixa`**: vira floco de neve, e o filtro de `dim_municipio` não sobe para `dim_faixa` sem relação bidirecional, que é o que se quer evitar.

## Consequences

Os números de `powerbi/conferencia.md` não mudam. As medidas de `ref_faixa` deixam de ler `dim_ano` e `dim_indicador` por `SELECTEDVALUE`. Elas mantêm uma guarda (`HASONEVALUE` no ano, no Indicador e na faixa) para devolver vazio, e não um `MAX` sem sentido, quando o contexto tem mais de um valor.
