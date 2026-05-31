import os
import sqlite3
import logging
import pandas as pd


# 1. Configuração Inicial e Logging

def setup_logging():
    os.makedirs("logs", exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler("logs/load.log"),
            logging.StreamHandler()
        ]
    )


# 2. Criação do Esquema da Base de Dados (DDL)

def create_schema(cursor):
    """Cria o modelo dimensional (Star Schema) com constraints."""
    
    # Dimensão: Cidade (O contexto)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS dim_city (
        city_name TEXT PRIMARY KEY,
        historical_avg_temp_celsius REAL NOT NULL
    )
    ''')

    # Facto: Registo Meteorológico (O evento)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS fact_weather_log (
        log_id INTEGER PRIMARY KEY AUTOINCREMENT,
        city_name TEXT NOT NULL,
        timestamp DATETIME NOT NULL,
        current_temp_celsius REAL,
        humidity_percent REAL,
        wind_speed_ms REAL,
        FOREIGN KEY (city_name) REFERENCES dim_city (city_name)
    )
    ''')
    
    # Criar um índice para otimizar pesquisas por data e cidade
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_weather_date ON fact_weather_log(timestamp);')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_weather_city ON fact_weather_log(city_name);')
    logging.info("Esquema dimensional (Star Schema), chaves e índices criados com sucesso.")


# 3. Load

def load_data(conn):
    """Lê da camada Curated/Staging e insere na BD."""
    try:
        # Lê os dados previamente transformados (Semana 2)
        curated_df = pd.read_csv("data/curated/weather_analytical_model.csv")
        
        # 1. Carregar a Dimensão (dim_city)
        # Usamos drop_duplicates para garantir chaves únicas
        dim_city_df = curated_df[['city', 'historical_avg_temp_celsius']].drop_duplicates()
        dim_city_df.rename(columns={'city': 'city_name'}, inplace=True)
        
        # Inserção com IGNORE para não duplicar cidades já existentes
        dim_city_df.to_sql('dim_city_temp', conn, if_exists='replace', index=False)
        conn.execute('''
            INSERT OR IGNORE INTO dim_city (city_name, historical_avg_temp_celsius)
            SELECT city_name, historical_avg_temp_celsius FROM dim_city_temp
        ''')
        
        # 2. Carregar os Factos (fact_weather_log)
        fact_df = curated_df[['city', 'timestamp', 'current_temp_celsius', 'humidity_percent', 'wind_speed_ms']]
        fact_df.rename(columns={'city': 'city_name'}, inplace=True)
        
        # Append para adicionar o log incrementalmente
        fact_df.to_sql('fact_weather_log', conn, if_exists='append', index=False)
        
        logging.info(f"Carga concluída: Inseridos registos em fact_weather_log.")
        
    except FileNotFoundError:
        logging.error("Ficheiro da camada Curated não encontrado. Execute o transform.py primeiro.")
        raise


# 4. Validação 

def validate_load(conn):
    """Executa queries de validação de contagens e integridade."""
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM dim_city")
    dim_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM fact_weather_log")
    fact_count = cursor.fetchone()[0]
    
    logging.info(f"VALIDAÇÃO: A tabela 'dim_city' contém {dim_count} registos.")
    logging.info(f"VALIDAÇÃO: A tabela 'fact_weather_log' contém {fact_count} registos.")
    
    # Validação de Integridade Referencial
    cursor.execute('''
        SELECT COUNT(*) FROM fact_weather_log f
        LEFT JOIN dim_city d ON f.city_name = d.city_name
        WHERE d.city_name IS NULL
    ''')
    orphans = cursor.fetchone()[0]
    if orphans > 0:
        logging.warning(f"FALHA DE INTEGRIDADE: {orphans} registos órfãos encontrados!")
    else:
        logging.info("VALIDAÇÃO: Integridade referencial garantida a 100%. Nenhuns órfãos.")



if __name__ == "__main__":
    setup_logging()
    logging.info("Início da Fase de Carregamento (Semana 3)")
    
    db_path = "data/database.sqlite"
    
    # Ligar à Base de Dados SQLite
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        create_schema(cursor)
        load_data(conn)
        validate_load(conn)
        
    logging.info("Pipeline de Load finalizado com sucesso.")