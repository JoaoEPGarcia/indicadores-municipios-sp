# A planilha é gerada por script em Python e completada no Excel para a web, sem Power Query

A especificação previa a planilha de referência montada por automação COM: um script comandaria o Excel do computador, gravaria o Power Query (parâmetro de pasta, função de leitura, cinco consultas e a mescla do nome do Indicador) e conferiria as fórmulas recalculando no próprio Excel. O dono só tem o Excel para a web (Microsoft 365 da universidade). Nele não há como escrever Power Query ("Obter Dados" não existe, só "Consultas e Conexões"), não há Office Scripts e não há COM. Decidimos gerar o `.xlsx` em Python (XlsxWriter): os CSV entram como cinco tabelas nomeadas, a tabela Fato já com o nome do Indicador, e as fórmulas, as listas de escolha e os gráficos vão gravados pelo script. A tabela dinâmica e a segmentação da aba Explorar são inseridas à mão no Excel para a web, que também calcula as fórmulas. O conferidor lê os valores calculados de cópias baixadas, uma por município, e compara com o SQLite. O Power Query fica demonstrado onde ele é natural: nas consultas do modelo do Power BI, em TMDL.

## Considered Options

- **Automação COM do Excel do computador** (a especificação original): exige o Excel instalado, que esta máquina não tem.
- **Power Query escrito à mão no XML do arquivo** (a parte `customXml` do Data Mashup): formato não documentado para escrita. O Excel para a web não edita nem atualiza a consulta, então ninguém conseguiria conferir se ela funciona.
- **Tabela dinâmica gerada pelo script**: o XlsxWriter não grava tabela dinâmica, e uma imitada à mão no XML arriscaria um arquivo que o Excel recusa. São cinco cliques no Excel para a web, descritos no passo a passo.

## Consequences

A planilha não se atualiza sozinha com dado novo: roda-se o script de novo e refaz-se a tabela dinâmica. As histórias 10 e 11 da especificação (Power Query na planilha) passam a ser atendidas pelo modelo do Power BI. O README diz que a planilha é "gerada por script em Python e completada no Excel para a web", com passo a passo para refazê-la à mão. O conferidor deixa de precisar do Excel e passa a rodar sobre arquivos versionados em `excel/calculadas/`.
