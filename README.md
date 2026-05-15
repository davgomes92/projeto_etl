# Projeto Prático de ETL: Monitorização Ambiental

Este repositório contém a implementação de um pipeline modular de Engenharia de Dados (Extract, Transform, Load - ETL) focado no domínio do Clima e Meio Ambiente. 

**Módulo Atual:** Semana 1 - Extração (Extract) e Raw Storage.

## Inventário das Fontes de Dados

Para cumprir os requisitos de diversidade e volume, o projeto utiliza duas fontes primárias na fase de extração:

1. **OpenWeatherMap API (Tempo Real):** Extração dinâmica de dados meteorológicos atuais (temperatura, vento, pressão, humidade). Os dados são consumidos com uma política de *retries* (Exponential Backoff) para evitar limites de taxa.
2. **Kaggle Earth Surface Temperature Data (Histórico / Grande Volume):** Dataset massivo (ficheiro `GlobalLandTemperaturesByCity.csv`, >500MB) contendo o registo histórico climático. 
   * *Nota Técnica:* Devido ao limite de 100MB do GitHub, este ficheiro de alto volume foi adicionado ao `.gitignore` e não consta no repositório remoto. Uma amostra representativa (`sample_temperatures.csv`) poderá ser fornecida para efeitos de validação do pipeline de transformação nas semanas seguintes.

## Pré-Requisitos e Configuração (Setup)

O projeto foi desenhado para ser totalmente reproduzível num computador pessoal. 

1. **Clonar o repositório e aceder à pasta:**
   ```bash
   git clone <url-do-teu-repositorio>
   cd projeto_etl
