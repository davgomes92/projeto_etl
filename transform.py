import os
import glob
import json
import logging
import pandas as pd
from datetime import datetime


# 1. Configuração Inicial e Logging

def setup_logging():
    os.makedirs("logs", exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler("logs/transform.log"),
            logging.StreamHandler()
        ]
    )


# 2. Extração da Camada Raw (Leitura)

def load_latest_api_data() -> pd.DataFrame:
    """Lê o ficheiro JSON mais recente da API na pasta raw."""
    list_of_files = glob.glob('data/raw/*.json')
    if not list_of_files:
        raise FileNotFoundError("Nenhum ficheiro JSON encontrado na camada raw.")
    
    latest_file = max(list_of_files, key=os.path.getctime)
    logging.info(f"A ler dados da API do ficheiro: {latest_file}")
    
    with open(latest_file, 'r') as f:
        data = json.load(f)
    
    # Aplanar (flatten) o JSON para um formato tabular
    df = pd.json_normalize(data)
    return df

def load_historical_data() -> pd.DataFrame:
    """Lê a amostra do dataset histórico do Kaggle."""
    filepath = 'data/raw/sample_temperatures.csv'
    logging.info(f"A ler dados históricos do ficheiro: {filepath}")
    return pd.read_csv(filepath)


# 3. Transformação: Camada Staging / Silver (Limpeza)

def clean_api_data(df: pd.DataFrame) -> pd.DataFrame:
    """Padroniza e limpa os dados em tempo real da API."""
    # Selecionar e renomear apenas as colunas relevantes
    cols_to_keep = {
        'name': 'city',
        'dt': 'timestamp',
        'main.temp': 'current_temp_celsius',
        'main.humidity': 'humidity_percent',
        'wind.speed': 'wind_speed_ms'
    }
    df_clean = df[list(cols_to_keep.keys())].rename(columns=cols_to_keep)
    
    # Converter Unix timestamp para data legível
    df_clean['timestamp'] = pd.to_datetime(df_clean['timestamp'], unit='s')
    
    # Normalizar o nome da cidade (remover espaços extra e colocar em maiúsculas)
    df_clean['city'] = df_clean['city'].str.strip().str.upper()
    
    # Validação de Qualidade de Dados (Data Quality)
    if df_clean['current_temp_celsius'].isnull().any():
        logging.warning("Regra de Qualidade: Valores nulos encontrados na temperatura da API!")
        df_clean = df_clean.dropna(subset=['current_temp_celsius'])
        
    return df_clean

def clean_historical_data(df: pd.DataFrame) -> pd.DataFrame:
    """Limpa e formata os dados históricos do Kaggle."""
    # Tratar valores nulos (ex: remover linhas sem temperatura média)
    linhas_iniciais = len(df)
    df_clean = df.dropna(subset=['AverageTemperature']).copy()
    linhas_removidas = linhas_iniciais - len(df_clean)
    
    if linhas_removidas > 0:
        logging.info(f"Data Quality: Removidas {linhas_removidas} linhas com temperaturas nulas do histórico.")

    # Renomear e padronizar
    df_clean = df_clean.rename(columns={
        'dt': 'date',
        'AverageTemperature': 'historical_avg_temp_celsius',
        'City': 'city'
    })
    
    df_clean['date'] = pd.to_datetime(df_clean['date'])
    df_clean['city'] = df_clean['city'].str.strip().str.upper()
    
    return df_clean

# 4. Transformação: Camada Curated / Gold (Integração)

def integrate_data(api_df: pd.DataFrame, hist_df: pd.DataFrame) -> pd.DataFrame:
    """Cruza as fontes de dados para criar métricas derivadas."""
    # Agregação: Calcular a média histórica global por cidade
    hist_agg = hist_df.groupby('city')['historical_avg_temp_celsius'].mean().reset_index()
    
    # Integração (Join) entre a API em tempo real e a média histórica
    merged_df = pd.merge(api_df, hist_agg, on='city', how='left')
    
    # Criação de Métrica Derivada: Diferença de temperatura
    merged_df['temp_difference_from_history'] = merged_df['current_temp_celsius'] - merged_df['historical_avg_temp_celsius']
    
    logging.info("Integração concluída com sucesso. Tabela analítica gerada.")
    return merged_df


if __name__ == "__main__":
    setup_logging()
    logging.info("Início da Fase de Transformação (Semana 2)")
    
    try:
        # 1. Criação das pastas de destino
        os.makedirs("data/staging", exist_ok=True)
        os.makedirs("data/curated", exist_ok=True)
        
        # 2. Extract (Leitura do Raw)
        raw_api = load_latest_api_data()
        raw_hist = load_historical_data()
        
        # 3. Transform (Staging / Silver)
        staging_api = clean_api_data(raw_api)
        staging_hist = clean_historical_data(raw_hist)
        
        # Guardar dados limpos (Staging)
        staging_api.to_csv("data/staging/api_weather_clean.csv", index=False)
        staging_hist.to_csv("data/staging/historical_weather_clean.csv", index=False)
        logging.info("Dados limpos gravados na camada Staging.")
        
        # 4. Integrate (Curated / Gold)
        curated_df = integrate_data(staging_api, staging_hist)
        
        # Guardar dados analíticos finais (Curated)
        curated_df.to_csv("data/curated/weather_analytical_model.csv", index=False)
        logging.info("Modelo analítico gravado na camada Curated.")
        
        print("\nSucesso! Pipeline de transformação executado.")
        print(curated_df.head())
        
    except Exception as e:
        logging.error(f"Erro no pipeline de transformação: {e}")