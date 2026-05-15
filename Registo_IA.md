# Registo de Uso de Inteligência Artificial
**Projeto:** Pipeline de Monitorização Ambiental
**Fase:** Semana 1 - Extração (Extract)

## Metodologia Adotada: Spec-Driven Development
De acordo com os requisitos do projeto, a utilização de ferramentas de IA foi conduzida através de uma abordagem *Requirement-First*. A IA não foi utilizada para gerar código ad-hoc, mas sim para materializar especificações técnicas e arquiteturais previamente definidas pela equipa.

### Tarefa 1: Implementação do script `extract.py`
* **Intenção e Requisitos (A Especificação):** Foi solicitado à IA o desenvolvimento de um script Python modular para interagir com a OpenWeatherMap API. A especificação técnica exigida incluiu:
  1. Carregamento seguro de credenciais via `python-dotenv`.
  2. Implementação de resiliência de rede (Exponential Backoff) utilizando a biblioteca `tenacity` para gerir limites de taxa (HTTP 429) e erros de servidor (HTTP 5xx).
  3. Armazenamento na camada *Raw* em formato JSON estrito, garantindo imutabilidade e rastreabilidade (adição de *timestamps*).
* **Validação Humana e Correções:** O output gerado foi revisto para confirmar que o `response.raise_for_status()` estava posicionado corretamente antes do bloco de captura da `tenacity`, garantindo que os erros HTTP acionavam efetivamente o ciclo de repetição. O código foi validado através de execução local com sucesso.
* **Impacto no Projeto:** Acelerou o *setup* inicial do pipeline e garantiu a implementação de padrões de resiliência de nível de produção desde a primeira etapa.

### Tarefa 2: Refinamento da Documentação e Arquitetura
* **Intenção e Requisitos:** Solicitou-se à IA o apoio na estruturação do Relatório Técnico e do README, pedindo especificamente a geração de um diagrama Mermaid e a articulação formal das decisões arquiteturais tomadas (ex: porquê o JSON).
* **Validação Humana e Correções:** O raciocínio sugerido pela IA em torno de "Imutabilidade" e "Schema-on-Read" como justificação para o formato JSON foi analisado, validado contra a literatura de Engenharia de Dados, e aceite como justificação técnica oficial para o projeto.