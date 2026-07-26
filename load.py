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
    
    # Dimensão: Cidade (O contexto estático - Agora com a Média Global)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS dim_city (
        city_name TEXT PRIMARY KEY,
        historical_avg_temp_celsius REAL,
        latest_global_historical_avg_temp REAL
    )
    ''')

    # Facto: Registo Meteorológico (O evento dinâmico)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS fact_weather_log (
        log_id INTEGER PRIMARY KEY AUTOINCREMENT,
        city_name TEXT NOT NULL,
        timestamp DATETIME NOT NULL,
        current_temp_celsius REAL,
        humidity_percent REAL,
        wind_speed_ms REAL,
        temp_difference_from_history REAL,
        FOREIGN KEY (city_name) REFERENCES dim_city (city_name)
    )
    ''')
    
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_weather_date ON fact_weather_log(timestamp);')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_weather_city ON fact_weather_log(city_name);')

    # Dimensão: Série Anual Global (Terceira Fonte completa, não apenas o último ano)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS dim_global_yearly (
        year INTEGER PRIMARY KEY,
        global_avg_temp_celsius REAL
    )
    ''')

    logging.info("Esquema dimensional (Star Schema), chaves e índices criados com sucesso.")


# 3. Load

def load_data(conn):
    """Lê da camada Curated/Staging e insere na BD."""
    try:
        curated_df = pd.read_csv("data/curated/weather_analytical_model.csv")
        
        # 1. Carregar a Dimensão (dim_city)
        # Selecionamos as colunas de contexto, incluindo a nova coluna global
        dim_cols = ['city', 'historical_avg_temp_celsius']
        if 'latest_global_historical_avg_temp' in curated_df.columns:
            dim_cols.append('latest_global_historical_avg_temp')
            
        dim_city_df = curated_df[dim_cols].drop_duplicates()
        dim_city_df.rename(columns={'city': 'city_name'}, inplace=True)
        
        dim_city_df.to_sql('dim_city_temp', conn, if_exists='replace', index=False)
        
        # Usamos IGNORE para garantir que a carga incremental não duplica o registo da cidade
        # E usamos COALESCE/estruturas condicionais se existirem atualizações a fazer
        conn.execute('''
            INSERT OR IGNORE INTO dim_city (city_name, historical_avg_temp_celsius, latest_global_historical_avg_temp)
            SELECT 
                city_name, 
                historical_avg_temp_celsius, 
                COALESCE(latest_global_historical_avg_temp, NULL)
            FROM dim_city_temp
        ''')
        
        # 2. Carregar os Factos (fact_weather_log)
        fact_cols = [
            'city', 'timestamp', 'current_temp_celsius', 'humidity_percent',
            'wind_speed_ms', 'temp_difference_from_history'
        ]
        # Garantir que as colunas existem para evitar erros caso a API falhe campos
        existing_fact_cols = [col for col in fact_cols if col in curated_df.columns]
        
        fact_df = curated_df[existing_fact_cols].copy()
        fact_df.rename(columns={'city': 'city_name'}, inplace=True)
        
        # Append para adicionar logs dinâmicos
        fact_df.to_sql('fact_weather_log', conn, if_exists='append', index=False)
        
        logging.info("Carga concluída: Inseridos registos em fact_weather_log.")

        # 3. Carregar a série anual global completa (dim_global_yearly)
        # Esta tabela permite ao dashboard mostrar a evolução do aquecimento global
        # ao longo de todo o histórico disponível, e não apenas o último ano.
        global_yearly_path = "data/staging/global_historical_clean.csv"
        if os.path.exists(global_yearly_path):
            global_yearly_df = pd.read_csv(global_yearly_path)
            global_yearly_df.to_sql('dim_global_yearly_temp', conn, if_exists='replace', index=False)
            conn.execute('''
                INSERT OR REPLACE INTO dim_global_yearly (year, global_avg_temp_celsius)
                SELECT year, global_avg_temp_celsius FROM dim_global_yearly_temp
            ''')
            logging.info(f"Carga concluída: dim_global_yearly atualizada com {len(global_yearly_df)} anos.")
        else:
            logging.warning(
                f"Ficheiro {global_yearly_path} não encontrado. "
                "dim_global_yearly não foi atualizada nesta execução."
            )
        
    except FileNotFoundError:
        logging.error("Ficheiro da camada Curated não encontrado. Execute o transform.py primeiro.")
        raise
    except Exception as e:
         logging.error(f"Erro durante o processo de Load: {e}")
         raise


# 4. Validação 

def validate_load(conn):
    """Executa queries de validação de contagens e integridade."""
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM dim_city")
    dim_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM fact_weather_log")
    fact_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM dim_global_yearly")
    global_yearly_count = cursor.fetchone()[0]
    
    logging.info(f"VALIDAÇÃO: A tabela 'dim_city' contém {dim_count} registos.")
    logging.info(f"VALIDAÇÃO: A tabela 'fact_weather_log' contém {fact_count} registos.")
    logging.info(f"VALIDAÇÃO: A tabela 'dim_global_yearly' contém {global_yearly_count} registos.")
    
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
    
    # Criar a pasta data/ se não existir para prevenir erros na criação do SQLite
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        create_schema(cursor)
        load_data(conn)
        validate_load(conn)
        
    logging.info("Pipeline de Load finalizado com sucesso.")