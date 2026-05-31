# Relatório de Qualidade de Dados (Data Quality) - Semana 2

Durante a fase de transformação (`transform.py`), foram aplicadas as seguintes validações e correções:

1. **Valores Nulos no Dataset Histórico (Kaggle):**
   * *Problema:* Identificadas linhas na coluna `AverageTemperature` sem leitura válida (NaN).
   * *Decisão Técnica:* Remoção destas linhas (`dropna`), uma vez que a imputação de médias climáticas históricas poderia enviesar a métrica derivada na camada analítica.

2. **Inconsistência de Chaves (Matching):**
   * *Problema:* O cruzamento (Join) entre a API e o Kaggle depende da coluna "City". O formato do texto diferia entre as fontes (espaços extra, capitalização).
   * *Decisão Técnica:* Aplicação de padronização nas duas fontes (`str.strip().str.upper()`) antes do `pd.merge()`, garantindo uma integridade referencial correta.

3. **Validação de Tipos de Dados:**
   * *Problema:* A data na API chega em formato *Unix Timestamp* (inteiro) e no Kaggle em formato de *string*.
   * *Decisão Técnica:* Conversão explícita de ambas as colunas para o tipo estandardizado `datetime64` do Pandas, permitindo consistência cronológica.
