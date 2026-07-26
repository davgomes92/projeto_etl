# Registo de Uso de Inteligência Artificial
**Projeto:** Pipeline de Monitorização Ambiental

## Metodologia Adotada: Spec-Driven Development
De acordo com os requisitos do projeto, a utilização de ferramentas de IA foi conduzida através de uma abordagem Requirement-First. A IA não foi utilizada para gerar código ad-hoc, mas sim para materializar especificações técnicas e arquiteturais previamente definidas.

---

**Fase:** Semana 1 - Extração (Extract)

### Tarefa 1: Implementação do script extract.py
* **Intenção e Requisitos (A Especificação):** Foi solicitado à IA o desenvolvimento de um script Python modular para interagir com a OpenWeatherMap API. A especificação técnica exigida incluiu:
  1. Carregamento seguro de credenciais via python-dotenv.
  2. Implementação de resiliência de rede (Exponential Backoff) utilizando a biblioteca tenacity para gerir limites de taxa (HTTP 429) e erros de servidor (HTTP 5xx).
  3. Armazenamento na camada Raw em formato JSON estrito, garantindo imutabilidade e rastreabilidade (adição de timestamps).
* **Validação Humana e Correções:** O output gerado foi revisto para confirmar que o response.raise_for_status() estava posicionado corretamente antes do bloco de captura da tenacity, garantindo que os erros HTTP acionavam efetivamente o ciclo de repetição. O código foi validado através de execução local com sucesso.
* **Impacto no Projeto:** Acelerou o setup inicial do pipeline e garantiu a implementação de padrões de resiliência de nível de produção desde a primeira etapa.

### Tarefa 2: Refinamento da Documentação e Arquitetura
* **Intenção e Requisitos:** Solicitou-se à IA o apoio na estruturação do Relatório Técnico e do README, pedindo especificamente a geração de um diagrama Mermaid e a articulação formal das decisões arquiteturais tomadas (ex: porquê o JSON).
* **Validação Humana e Correções:** O raciocínio sugerido pela IA em torno de "Imutabilidade" e "Schema-on-Read" como justificação para o formato JSON foi analisado, validado contra a literatura de Engenharia de Dados, e aceite como justificação técnica oficial para o projeto.

---

**Fase:** Semana 2 - Transformação e Qualidade

### Tarefa 1: Implementação da Arquitetura Medallion e Limpeza de Dados
* **Intenção e Requisitos (Design Humano):** A arquitetura em camadas (Medallion: Staging/Curated) e as regras de negócio para a criação de métricas derivadas (diferença térmica) foram previamente definidas e desenhadas por mim. A IA foi utilizada de forma pontual, atuando como copilot, para otimizar a sintaxe na biblioteca pandas. Com base na minha especificação, solicitei abordagens eficientes para a limpeza de nulls (dropna) e para a normalização de strings, de forma a garantir o cruzamento de chaves sem falhas.
* **Validação Humana e Integração:** Os blocos de sintaxe sugeridos pela IA não foram aplicados cegamente. Analisei e adaptei os métodos propostos (como o pd.merge e o pd.json_normalize), garantindo a sua compatibilidade com a estrutura de pastas e o formato dos nossos dados brutos. O código foi testado localmente passo a passo, e a validação do matching foi confirmada manualmente no Relatório de Qualidade de Dados.

---

**Fase:** Semana 3 - Carregamento (Load) e Modelação

### Tarefa 1: Desenho do Esquema Relacional e Script de Carregamento
* **Intenção e Requisitos (Design Humano):** Para começar, defini que o armazenamento final seria feito em SQLite, utilizando um modelo dimensional Star Schema (Tabelas Fact e Dimension) para facilitar a leitura futura pelo Dashboard. Foram exigidas constraints de integridade referencial (Foreign Keys) e índices de performance.
* **Validação Humana:** O código SQL gerado com o apoio da IA para a criação do esquema DDL foi revisto para garantir que a estratégia incremental (Load) não criava registos duplicados na dimensão de cidades (utilização de `INSERT OR IGNORE`). As queries do Relatório de Validação Pós-Carga foram testadas para assegurar a ausência de registos órfãos.

---

**Fase:** Semana 4 - Visualização (Dashboard)

### Tarefa 1: Implementação do dashboard.py com Streamlit
* **Intenção e Requisitos (Design Humano):** A ferramenta Streamlit foi escolhida pela sua integração nativa com Python e facilidade de execução local, sem depender de licenças externas (Power BI/Tableau). Defini como requisito que o dashboard respondesse diretamente às perguntas analíticas do projeto: comparação da temperatura atual com a média histórica da cidade, contexto face ao aquecimento global, e correlação entre indicadores meteorológicos (humidade vs. vento).
* **Uso da IA:** A IA foi utilizada para gerar o esqueleto do `dashboard.py`, mapeando as queries SQL do modelo Star Schema diretamente para os componentes visuais do Streamlit (KPIs com `st.metric`, gráficos `plotly.express`), incluindo o uso de `st.cache_data` para evitar leituras repetidas à base de dados.
* **Validação Humana e Correções:** Revi o tratamento de valores nulos (cidades sem histórico associado) e confirmei que os filtros por cidade (`st.sidebar.selectbox`) refletiam corretamente as cidades presentes na base de dados.

### Tarefa 2: Revisão Crítica e Correção da Pipeline a Montante
* **Intenção e Requisitos (Design Humano):** Ao planear melhorias ao dashboard, identifiquei — com o apoio da IA numa análise crítica ao pipeline completo — três limitações estruturais que impediam o dashboard de responder às perguntas analíticas na íntegra:
  1. `extract.py` só recolhia dados de uma única cidade, impossibilitando qualquer comparação entre cidades.
  2. `transform.py` calculava a série anual global completa mas o `integrate_data()` descartava-a, mantendo apenas o último ano.
  3. `load.py` calculava `temp_difference_from_history` mas não a persistia na base de dados, obrigando o dashboard a recalculá-la.
* **Uso da IA:** Solicitei a correção destes três pontos de forma consistente entre `extract.py`, `transform.py` e `load.py`: extração multi-cidade com isolamento de falhas por cidade, leitura de todos os ficheiros JSON de uma mesma execução (necessário após a extração multi-cidade), nova tabela `dim_global_yearly` para a série histórica completa, e persistência da métrica derivada na `fact_weather_log`.
* **Validação Humana e Correções:** Testei a compilação dos scripts (`python -m py_compile`) e revi manualmente que a leitura de múltiplos JSONs por execução (`load_latest_api_data`) não misturava ficheiros de execuções diferentes, através de uma janela temporal de agrupamento. Atualizei também o `dashboard.py` para consumir a nova tabela `dim_global_yearly` e a coluna persistida `temp_difference_from_history`, e o `README.md` para refletir o novo modelo de dados.
* **Impacto no Projeto:** Sem esta revisão, o dashboard funcionaria tecnicamente mas não cumpriria de facto as perguntas de negócio definidas no início do projeto — a comparação entre cidades e a evolução histórica do aquecimento global. Este processo reforça a importância de validar cada camada do pipeline contra os requisitos de negócio, e não apenas a correção sintática do código.