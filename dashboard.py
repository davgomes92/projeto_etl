import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px

# 1. Configuração da Página
st.set_page_config(page_title="Dashboard Climático", page_icon="🌍", layout="wide")

DB_PATH = "data/database.sqlite"


# 2. Carregamento de Dados (com cache para performance)

@st.cache_data
def load_weather_data():
    """Lê a tabela de factos cruzada com a dimensão de cidades."""
    try:
        conn = sqlite3.connect(DB_PATH)
        query = """
        SELECT 
            f.log_id,
            f.timestamp,
            f.city_name,
            f.current_temp_celsius,
            f.humidity_percent,
            f.wind_speed_ms,
            f.temp_difference_from_history,
            d.historical_avg_temp_celsius,
            d.latest_global_historical_avg_temp
        FROM fact_weather_log f
        JOIN dim_city d ON f.city_name = d.city_name
        """
        df = pd.read_sql_query(query, conn)
        conn.close()
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        return df
    except Exception as e:
        st.error(f"Erro ao ligar à Base de Dados: {e}")
        return pd.DataFrame()


@st.cache_data
def load_global_yearly_data():
    """Lê a série histórica anual completa da temperatura global (dim_global_yearly)."""
    try:
        conn = sqlite3.connect(DB_PATH)
        df = pd.read_sql_query(
            "SELECT year, global_avg_temp_celsius FROM dim_global_yearly ORDER BY year",
            conn,
        )
        conn.close()
        return df
    except Exception:
        # Tabela pode ainda não existir se o load.py não tiver sido corrido com a versão atual
        return pd.DataFrame(columns=["year", "global_avg_temp_celsius"])


df = load_weather_data()
df_global_yearly = load_global_yearly_data()


# 3. Construção do Layout do Dashboard

if df.empty:
    st.warning("⚠️ Não foram encontrados dados. Por favor, corre os scripts extract.py, transform.py e load.py primeiro.")
else:
    # Cabeçalho Principal
    st.title("🌍 Monitorização Climática e Meio Ambiente")
    st.markdown(
        "Este painel compara a temperatura atual em tempo real com as médias históricas "
        "(Local e Global) para identificar desvios térmicos, e explora a evolução do "
        "aquecimento global ao longo do tempo."
    )

    col_info, col_refresh = st.columns([4, 1])
    with col_info:
        ultima_atualizacao = df['timestamp'].max()
        st.caption(f"🕒 Última leitura registada: {ultima_atualizacao.strftime('%Y-%m-%d %H:%M')}")
    with col_refresh:
        if st.button("🔄 Atualizar dados"):
            st.cache_data.clear()
            st.rerun()

    st.divider()

    # Filtro de Cidade (Menu Lateral)
    st.sidebar.header("Filtros Analíticos")
    cidades_disponiveis = sorted(df['city_name'].unique())
    cidade_selecionada = st.sidebar.selectbox("Selecione a Cidade:", cidades_disponiveis)
    st.sidebar.caption(f"📊 {len(cidades_disponiveis)} cidade(s) disponível(is) na base de dados.")

    # Filtrar o DataFrame para a cidade selecionada e ordenar temporalmente
    df_cidade = df[df['city_name'] == cidade_selecionada].sort_values(by='timestamp')

    # Isolar a extração mais recente para as métricas principais
    ultimo_registo = df_cidade.iloc[-1]

    # Extrair valores com segurança (podem ser nulos/NaN)
    temp_atual = ultimo_registo['current_temp_celsius']
    temp_hist_cidade = ultimo_registo['historical_avg_temp_celsius']
    temp_hist_global = ultimo_registo['latest_global_historical_avg_temp']

    # Preferir o valor já calculado e persistido na base de dados (temp_difference_from_history);
    # cair para cálculo manual apenas se, por alguma razão, vier nulo.
    delta_persistido = ultimo_registo['temp_difference_from_history']
    if pd.notna(delta_persistido):
        delta_temp = delta_persistido
    elif pd.notna(temp_hist_cidade):
        delta_temp = temp_atual - temp_hist_cidade
    else:
        delta_temp = None

    # --- SECÇÃO 1: KPIs (Métricas em Destaque) ---
    st.subheader(f"📍 Indicadores Atuais para {cidade_selecionada}")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        if delta_temp is None:
            st.metric(
                label="Temperatura Atual (°C)",
                value=f"{temp_atual:.1f} °C",
                delta="Sem histórico",
                delta_color="off"
            )
        else:
            st.metric(
                label="Temperatura Atual (°C)",
                value=f"{temp_atual:.1f} °C",
                delta=f"{delta_temp:+.1f} °C vs Histórico",
                delta_color="inverse"
            )

    with col2:
        val_hist = "N/D" if pd.isna(temp_hist_cidade) else f"{temp_hist_cidade:.1f} °C"
        st.metric(label="Média Histórica (Secular)", value=val_hist)

    with col3:
        val_glob = "N/D" if pd.isna(temp_hist_global) else f"{temp_hist_global:.1f} °C"
        st.metric(label="Média Global Terrestre", value=val_glob)

    with col4:
        st.metric(
            label="Humidade e Vento",
            value=f"{ultimo_registo['humidity_percent']}%",
            delta=f"{ultimo_registo['wind_speed_ms']} m/s",
            delta_color="off"
        )

    st.divider()

    # --- SECÇÃO 2: Contexto Térmico e Evolução Temporal ---
    col_grafico1, col_grafico2 = st.columns(2)

    with col_grafico1:
        st.subheader("🌡️ Contexto Térmico (Atual vs Histórico)")

        nomes_metricas = ['Atual (Cidade)']
        valores_metricas = [temp_atual]
        cores = ['#EF553B']

        if pd.notna(temp_hist_cidade):
            nomes_metricas.append('Histórica (Cidade)')
            valores_metricas.append(temp_hist_cidade)
            cores.append('#636EFA')

        if pd.notna(temp_hist_global):
            nomes_metricas.append('Histórica (Global)')
            valores_metricas.append(temp_hist_global)
            cores.append('#00CC96')

        dados_comp = pd.DataFrame({
            'Métrica': nomes_metricas,
            'Temperatura (°C)': valores_metricas
        })

        fig_bar = px.bar(
            dados_comp,
            x='Métrica',
            y='Temperatura (°C)',
            color='Métrica',
            text='Temperatura (°C)',
            color_discrete_sequence=cores
        )
        fig_bar.update_traces(texttemplate='%{text:.1f}°C', textposition='outside')
        fig_bar.update_layout(showlegend=False, yaxis_title="Graus Celsius")

        st.plotly_chart(fig_bar, use_container_width=True)

    with col_grafico2:
        st.subheader("📈 Evolução Temporal (Extrações API)")

        if len(df_cidade) > 1:
            fig_line = px.line(
                df_cidade,
                x='timestamp',
                y='current_temp_celsius',
                markers=True,
                title="Histórico das Leituras Atuais"
            )

            if pd.notna(temp_hist_cidade):
                fig_line.add_hline(
                    y=temp_hist_cidade,
                    line_dash="dot",
                    annotation_text="Linha de Base Histórica",
                    annotation_position="bottom right"
                )
            fig_line.update_layout(xaxis_title="Data e Hora", yaxis_title="Temperatura (°C)")
            st.plotly_chart(fig_line, use_container_width=True)
        else:
            st.info(
                "💡 Apenas uma extração disponível. Executa o pipeline "
                "(extract/transform/load) mais vezes para veres a evolução temporal aqui."
            )

    st.divider()

    # --- SECÇÃO 3: Aquecimento Global (Série Histórica Completa) ---
    st.subheader("🌐 Evolução do Aquecimento Global (Terra)")

    if not df_global_yearly.empty:
        fig_global = px.line(
            df_global_yearly,
            x='year',
            y='global_avg_temp_celsius',
            title="Temperatura Média Global Terrestre por Ano"
        )
        fig_global.update_traces(line_color='#00CC96')

        if pd.notna(temp_hist_cidade):
            fig_global.add_hline(
                y=temp_hist_cidade,
                line_dash="dot",
                line_color="#636EFA",
                annotation_text=f"Média Histórica de {cidade_selecionada}",
                annotation_position="top left"
            )

        fig_global.update_layout(xaxis_title="Ano", yaxis_title="Temperatura Média (°C)")
        st.plotly_chart(fig_global, use_container_width=True)
        st.caption(
            "Fonte: Kaggle Global Temperatures (fonte complementar). A linha tracejada mostra "
            "a média histórica secular da cidade selecionada, para contexto comparativo."
        )
    else:
        st.info(
            "💡 A tabela 'dim_global_yearly' está vazia ou não existe. "
            "Corre o load.py atualizado para popular a série histórica global completa."
        )

    st.divider()

    # --- SECÇÃO 4: Comparação Entre Cidades ---
    st.subheader("🏙️ Desvio Térmico por Cidade (Atual vs Histórico)")

    df_ultima_leitura_por_cidade = (
        df.sort_values('timestamp')
        .groupby('city_name')
        .tail(1)
        .copy()
    )

    if len(df_ultima_leitura_por_cidade) > 1:
        df_ultima_leitura_por_cidade['desvio'] = df_ultima_leitura_por_cidade['temp_difference_from_history']
        df_ultima_leitura_por_cidade = df_ultima_leitura_por_cidade.dropna(subset=['desvio'])
        df_ultima_leitura_por_cidade = df_ultima_leitura_por_cidade.sort_values('desvio', ascending=False)

        fig_cidades = px.bar(
            df_ultima_leitura_por_cidade,
            x='city_name',
            y='desvio',
            color='desvio',
            color_continuous_scale='RdBu_r',
            text='desvio',
            labels={'city_name': 'Cidade', 'desvio': 'Desvio (°C)'}
        )
        fig_cidades.update_traces(texttemplate='%{text:+.1f}°C', textposition='outside')
        fig_cidades.update_layout(coloraxis_showscale=False)
        st.plotly_chart(fig_cidades, use_container_width=True)
        st.caption(
            "Diferença entre a temperatura atual e a média histórica secular de cada cidade, "
            "na sua leitura mais recente. Valores positivos indicam temperatura acima da média histórica."
        )
    else:
        st.info(
            "💡 Apenas uma cidade disponível na base de dados. Adiciona mais cidades à lista "
            "TARGET_CITIES em extract.py para veres a comparação entre cidades aqui."
        )

    st.divider()

    # --- SECÇÃO 5: Correlação Humidade vs Vento ---
    st.subheader("💧 Correlação: Humidade vs Velocidade do Vento")

    if len(df) > 1:
        fig_scatter = px.scatter(
            df,
            x='wind_speed_ms',
            y='humidity_percent',
            color='city_name',
            size='current_temp_celsius',
            hover_data=['timestamp', 'current_temp_celsius'],
            labels={
                'wind_speed_ms': 'Velocidade do Vento (m/s)',
                'humidity_percent': 'Humidade (%)',
                'city_name': 'Cidade'
            }
        )
        st.plotly_chart(fig_scatter, use_container_width=True)
        st.caption(
            "Cada ponto representa uma leitura da API. O tamanho do ponto reflete a temperatura "
            "atual registada no momento."
        )
    else:
        st.info("💡 São necessárias pelo menos duas leituras para visualizar uma correlação.")
