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