import os
import json
import logging
from datetime import datetime
import requests
from dotenv import load_dotenv
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type, retry_if_result


# 1. Logging

def setup_logging():
    """Configura o sistema de logging para escrever no ficheiro e na consola."""
    log_dir = "logs"
    os.makedirs(log_dir, exist_ok=True)
    
    log_filename = os.path.join(log_dir, "extraction.log")
    
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(log_filename),
            logging.StreamHandler() # Também mostra no terminal
        ]
    )
    logging.info("Logging configurado com sucesso.")


# 2. Retries e Extração

def is_rate_limit_or_server_error(exception):
    """Verifica se o erro é um Rate Limit (429) ou Erro de Servidor (5xx)."""
    if isinstance(exception, requests.exceptions.HTTPError):
        status_code = exception.response.status_code
        return status_code == 429 or status_code >= 500
    return False

# Usamos a Tenacity para gerir as tentativas: 
# Tenta até 5 vezes, esperando 2^x segundos entre tentativas (ex: 2, 4, 8, 16s)
@retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=2, min=2, max=30),
    retry=(retry_if_exception_type(requests.exceptions.RequestException) & 
           retry_if_exception_type(Exception)),
    reraise=True
)
def get_weather_data(city: str) -> dict:
    """Faz a chamada à API do OpenWeatherMap com retries em caso de falha."""
    api_key = os.getenv("OPENWEATHER_API_KEY")
    if not api_key:
        logging.error("API Key não encontrada. Verifica o ficheiro .env.")
        raise ValueError("OPENWEATHER_API_KEY em falta.")

    url = "https://api.openweathermap.org/data/2.5/weather"
    params = {
        "q": city,
        "appid": api_key,
        "units": "metric" # Retorna a temperatura em Celsius
    }

    logging.info(f"A iniciar extração de dados para a cidade: {city}")
    response = requests.get(url, params=params, timeout=10)
    
    # Levanta uma exceção para códigos HTTP de erro (ex: 404, 429, 500)
    response.raise_for_status() 
    
    logging.info(f"Dados extraídos com sucesso para {city}.")
    return response.json()

# 3. Armazenamento de Dados

def save_raw_data(data: dict, city: str):
    """Guarda o payload JSON bruto num ficheiro com timestamp."""
    output_dir = os.path.join("data", "raw")
    os.makedirs(output_dir, exist_ok=True)

    # Criação do timestamp e formatação do nome do ficheiro
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_city_name = city.lower().replace(" ", "_")
    filename = f"weather_{safe_city_name}_{timestamp}.json"
    filepath = os.path.join(output_dir, filename)

    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        logging.info(f"Dados guardados com sucesso em: {filepath}")
    except Exception as e:
        logging.error(f"Erro ao guardar os dados no ficheiro {filepath}: {e}")
        raise


# Main

if __name__ == "__main__":
    # Carrega as variáveis de ambiente do ficheiro .env
    load_dotenv()
    
    # Inicializa o logger
    setup_logging()
    
    # Define a cidade alvo (isto poderia vir de uma lista ou argumento de linha de comandos)
    TARGET_CITY = "Covilha"
    
    try:
        logging.info("Início do processo de extração (Extract).")
        
        # 1. Extrair
        raw_weather_data = get_weather_data(TARGET_CITY)
        
        # 2. Guardar (sem alterações destrutivas)
        save_raw_data(raw_weather_data, TARGET_CITY)
        
        logging.info("Processo de extração concluído com sucesso.")
        
    except Exception as e:
        logging.critical(f"O pipeline de extração falhou: {e}")