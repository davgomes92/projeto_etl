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
    """Lê todos os ficheiros JSON da última execução do extract.py (uma cidade por ficheiro).

    Os ficheiros são nomeados como weather_<cidade>_<timestamp>.json. Como o extract.py
    corre para uma lista de cidades em sequência, agrupamos os ficheiros cujo timestamp
    pertence à mesma "corrida" (batch), assumindo o timestamp mais recente como referência
    e aceitando uma pequena margem de segundos para cobrir a duração total do loop.
    """
    list_of_files = glob.glob('data/raw/*.json')
    if not list_of_files:
        raise FileNotFoundError("Nenhum ficheiro JSON encontrado na camada raw.")
    
    # Ordenar por data de criação, do mais recente para o mais antigo
    list_of_files.sort(key=os.path.getctime, reverse=True)
    
    latest_ctime = os.path.getctime(list_of_files[0])
    BATCH_WINDOW_SECONDS = 120  # margem para cobrir todas as chamadas de uma execução
    
    batch_files = [
        f for f in list_of_files
        if latest_ctime - os.path.getctime(f) <= BATCH_WINDOW_SECONDS
    ]
    
    logging.info(f"A ler {len(batch_files)} ficheiro(s) JSON da última execução da API: {batch_files}")
    
    registos = []
    for filepath in batch_files:
        with open(filepath, 'r') as f:
            data = json.load(f)
        registos.append(data)
    
    # Aplanar (flatten) o JSON para um formato tabular, uma linha por cidade
    df = pd.json_normalize(registos)
    return df

def load_historical_data() -> pd.DataFrame:
    """Lê a amostra do dataset histórico de cidades do Kaggle (Fonte 2)."""
    filepath = 'data/raw/sample_temperatures.csv'
    logging.info(f"A ler dados históricos de cidades do ficheiro: {filepath}")
    return pd.read_csv(filepath)

def load_global_historical_data() -> pd.DataFrame:
    """Lê o dataset complementar de temperaturas globais (Fonte 3)."""
    filepath = 'data/raw/GlobalTemperatures.csv'
    logging.info(f"A ler dados globais históricos do ficheiro: {filepath}")
    return pd.read_csv(filepath)


# 3. Transformação: Camada Staging / Silver (Limpeza)

def clean_api_data(df: pd.DataFrame) -> pd.DataFrame:
    """Padroniza e limpa os dados em tempo real da API."""
    cols_to_keep = {
        'name': 'city',
        'dt': 'timestamp',
        'main.temp': 'current_temp_celsius',
        'main.humidity': 'humidity_percent',
        'wind.speed': 'wind_speed_ms'
    }
    # Verifica se as colunas existem antes de renomear para evitar KeyError
    existing_cols = {k: v for k, v in cols_to_keep.items() if k in df.columns}
    df_clean = df[list(existing_cols.keys())].rename(columns=existing_cols).copy()
    
    df_clean['timestamp'] = pd.to_datetime(df_clean['timestamp'], unit='s')
    
    if 'city' in df_clean.columns:
        df_clean['city'] = df_clean['city'].astype(str).str.strip().str.upper()
    
    if 'current_temp_celsius' in df_clean.columns and df_clean['current_temp_celsius'].isnull().any():
        logging.warning("Regra de Qualidade: Valores nulos encontrados na temperatura da API!")
        df_clean = df_clean.dropna(subset=['current_temp_celsius'])
        
    return df_clean

def clean_historical_data(df: pd.DataFrame) -> pd.DataFrame:
    """Limpa e formata os dados históricos de cidades."""
    linhas_iniciais = len(df)
    df_clean = df.dropna(subset=['AverageTemperature']).copy()
    linhas_removidas = linhas_iniciais - len(df_clean)
    
    if linhas_removidas > 0:
        logging.info(f"Data Quality: Removidas {linhas_removidas} linhas com temperaturas nulas do histórico da cidade.")

    df_clean = df_clean.rename(columns={
        'dt': 'date',
        'AverageTemperature': 'historical_avg_temp_celsius',
        'City': 'city'
    })
    
    df_clean['date'] = pd.to_datetime(df_clean['date'])
    df_clean['city'] = df_clean['city'].astype(str).str.strip().str.upper()
    
    return df_clean

def clean_global_historical_data(df: pd.DataFrame) -> pd.DataFrame:
    """Limpa e formata os dados globais e agrega-os por ano."""
    cols_to_keep = {
        'dt': 'date',
        'LandAverageTemperature': 'global_avg_temp_celsius'
    }
    df_clean = df[list(cols_to_keep.keys())].rename(columns=cols_to_keep).copy()
    
    linhas_iniciais = len(df_clean)
    df_clean = df_clean.dropna(subset=['global_avg_temp_celsius'])
    linhas_removidas = linhas_iniciais - len(df_clean)
    
    if linhas_removidas > 0:
        logging.info(f"Data Quality: Removidas {linhas_removidas} linhas nulas do histórico global.")

    df_clean['date'] = pd.to_datetime(df_clean['date'])
    df_clean['year'] = df_clean['date'].dt.year
    
    # Agregar: calcular a média anual global
    df_yearly = df_clean.groupby('year')['global_avg_temp_celsius'].mean().reset_index()
    
    return df_yearly


# 4. Transformação: Camada Curated / Gold (Integração)

def integrate_data(api_df: pd.DataFrame, hist_city_df: pd.DataFrame, hist_global_df: pd.DataFrame) -> pd.DataFrame:
    """Cruza as 3 fontes de dados para criar a tabela analítica final."""
    
    # 1. Agregação Histórica por Cidade
    hist_agg = hist_city_df.groupby('city')['historical_avg_temp_celsius'].mean().reset_index()
    
    # 2. Join (API + Histórico Cidade)
    merged_df = pd.merge(api_df, hist_agg, on='city', how='left')
    
    # 3. Métricas Derivadas
    if 'current_temp_celsius' in merged_df.columns and 'historical_avg_temp_celsius' in merged_df.columns:
        merged_df['temp_difference_from_history'] = merged_df['current_temp_celsius'] - merged_df['historical_avg_temp_celsius']
    
    # 4. Injeção do Contexto Global (Terceira Fonte)
    # Para a tabela curated (uma linha por leitura atual) usamos o registo global
    # mais recente como baseline pontual de comparação.
    # NOTA: a série anual completa (hist_global_df) NÃO é descartada aqui — é gravada
    # integralmente em data/staging/global_historical_clean.csv e carregada como tabela
    # própria (dim_global_yearly) pelo load.py, para permitir ao dashboard mostrar a
    # evolução histórica completa do aquecimento global, não apenas o último ano.
    if not hist_global_df.empty:
        latest_global_temp = hist_global_df.iloc[-1]['global_avg_temp_celsius']
        merged_df['latest_global_historical_avg_temp'] = latest_global_temp
    else:
        merged_df['latest_global_historical_avg_temp'] = None
    
    logging.info("Integração concluída com sucesso. Tabela analítica com as 3 fontes gerada.")
    return merged_df


if __name__ == "__main__":
    setup_logging()
    logging.info("Início da Fase de Transformação (Semana 2)")
    
    try:
        # 1. Criação das pastas de destino
        os.makedirs("data/staging", exist_ok=True)
        os.makedirs("data/curated", exist_ok=True)
        
        # 2. Extract (Leitura do Raw) - AGORA COM AS 3 FONTES
        raw_api = load_latest_api_data()
        raw_hist = load_historical_data()
        raw_global = load_global_historical_data()
        
        # 3. Transform (Staging / Silver)
        staging_api = clean_api_data(raw_api)
        staging_hist = clean_historical_data(raw_hist)
        staging_global = clean_global_historical_data(raw_global)
        
        # Guardar dados limpos (Staging)
        staging_api.to_csv("data/staging/api_weather_clean.csv", index=False)
        staging_hist.to_csv("data/staging/historical_weather_clean.csv", index=False)
        staging_global.to_csv("data/staging/global_historical_clean.csv", index=False)
        logging.info("Dados limpos gravados na camada Staging.")
        
        # 4. Integrate (Curated / Gold) - PASSAGEM DOS 3 DATAFRAMES
        curated_df = integrate_data(staging_api, staging_hist, staging_global)
        
        # Guardar dados analíticos finais (Curated)
        curated_df.to_csv("data/curated/weather_analytical_model.csv", index=False)
        logging.info("Modelo analítico gravado na camada Curated.")
        
        print("\nSucesso! Pipeline de transformação executado.")
        
    except Exception as e:
        logging.error(f"Erro no pipeline de transformação: {e}")