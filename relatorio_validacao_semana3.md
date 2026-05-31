# Relatório de Modelação e Validação Pós-Carga (Semana 3)

## 1. Estratégia de Modelação
Foi adotada uma modelação dimensional em **Star Schema** para otimizar as consultas analíticas do futuro Dashboard:
* **`dim_city` (Dimensão):** Armazena o contexto estático/histórico, atuando como fonte de verdade para a temperatura média histórica (`historical_avg_temp_celsius`).
* **`fact_weather_log` (Factos):** Armazena os eventos dinâmicos recolhidos pela API em tempo real (`current_temp_celsius`, humidade, vento), ligados à dimensão através da chave estrangeira `city_name`.

## 2. Validação Pós-Carga
O script `load.py` inclui um módulo de validação automática (`validate_load`) que executa queries à base de dados para garantir a qualidade. Resultados da execução:
* **Contagem de Registos:** As tabelas foram populadas com sucesso através de uma estratégia de carga incremental (`APPEND` para factos, `INSERT OR IGNORE` para dimensões).
* **Integridade Referencial:** Confirmou-se a ausência de registos órfãos (0 resultados na query de validação de FKs). Todas as leituras na tabela de factos correspondem a uma cidade válida na tabela de dimensões.
