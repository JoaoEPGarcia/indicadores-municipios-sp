# A regra do número digitado tem uma lista curta de exceções, e ela mora só no verificador

O guia do kit diz que nenhum número se digita no `.tex` nem no `.md`: todo número impresso sai de `scripts/numeros.py`. Tomada ao pé da letra, a regra acusaria números que não são resultado do estudo e que nenhum script calcula: o ano no nome de uma fonte ("Censo 2022"), o número de um ato normativo ("Portaria STN nº 642/2019"), a versão de uma licença ("CC BY 4.0") ou de uma ferramenta ("Python 3.12"), o nome de um arquivo, um comando em bloco de código e a numeração dos títulos e dos passos que o modelo de README do kit pede. Decidimos manter a regra e abrir exceções só para esses casos, cada uma estreita (o número da Portaria passa, outro número na mesma frase não) e comentada. A lista é a constante `EXCECOES` de `scripts/verificar_textos.py`, e não existe outra: quem precisa de uma exceção nova a acrescenta lá, com o comentário do porquê.

## Considered Options

- **Regra sem exceção**: obrigaria a criar macros para "2022" do Censo ou "3.12" do Python, números que não mudam com os dados. O registro de números ficaria cheio de constantes, e a coluna "Onde aparece" perderia o sentido.
- **Exceções espalhadas** (no verificador, no gerador do README, em cada texto): ninguém saberia ao certo o que a regra deixa passar.
- **Marcar a exceção no próprio texto** (um comentário ao lado do número): polui o modelo do README e o LaTeX, e cada autor decidiria a sua.

## Consequences

O verificador dos textos falha com qualquer número fora de marcador, macro ou exceção, apontando arquivo e linha. A data da capa do relatório não é exceção: mês e ano vêm do registro (ticket 07). O ticket 06 pode acrescentar à lista o que a seção de Fontes do README pedir, como código de tabela do IBGE, e decide isso lá.
