import streamlit as st
import pandas as pd
import plotly.express as px
import time
import hmac
import base64
import hashlib
import urllib.parse
import requests
from dotenv import load_dotenv
import os

# Página configurada para modo wide
st.set_page_config(page_title="Dashboard de Ordens", layout="wide")
st.title("📊 Dashboard")

# Carregar variáveis do .env
load_dotenv()

# Proteção com senha
senha_correta = os.getenv("SENHA_DASHBOARD")
senha_digitada = st.text_input("Digite a senha para acessar o dashboard:", type="password")
if senha_digitada != senha_correta:
    st.warning("Acesso restrito. Digite a senha correta.")
    st.stop()

# Chaves da API
api_key = os.getenv("API_KEY")
api_secret = os.getenv("API_SECRET")
passphrase = os.getenv("PASSPHRASE")

if isinstance(api_secret, str):
    api_secret = api_secret.encode()

def generate_signature(timestamp, method, path, query_string, secret):
    message = f"{timestamp}{method}{path}{query_string}"
    signature = hmac.new(secret, message.encode(), hashlib.sha256).digest()
    return base64.b64encode(signature).decode()

def get_closed_positions():
    base_url = 'https://api.lnmarkets.com'
    path = '/v2/futures'
    method = 'GET'
    params = {'type': 'closed', 'limit': 1000}
    query_string = urllib.parse.urlencode(params)
    timestamp = str(int(time.time() * 1000))
    signature = generate_signature(timestamp, method, path, query_string, api_secret)

    headers = {
        'LNM-ACCESS-KEY': api_key,
        'LNM-ACCESS-SIGNATURE': signature,
        'LNM-ACCESS-PASSPHRASE': passphrase,
        'LNM-ACCESS-TIMESTAMP': timestamp,
    }

    url = f"{base_url}{path}?{query_string}"
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        return pd.DataFrame(response.json())
    else:
        st.error(f"Erro na API: {response.status_code}")
        return pd.DataFrame()

# Botão para atualizar dados
if st.button("🔄 Atualizar dados"):
    st.session_state.df = get_closed_positions()

# Carrega do estado ou da API caso ainda não tenha
if "df" not in st.session_state:
    st.session_state.df = get_closed_positions()

df = st.session_state.df

# Processamento e visualização
if not df.empty:
    if 'market_filled_ts' in df.columns and 'closed_ts' in df.columns:
        df = df[df['market_filled_ts'].notna() & df['closed_ts'].notna()]
        df['Entrada'] = pd.to_datetime(df['market_filled_ts'], unit='ms', errors='coerce').dt.strftime('%d/%m/%Y')
        df['Saida'] = pd.to_datetime(df['closed_ts'], unit='ms', errors='coerce').dt.strftime('%d/%m/%Y')
    else:
        st.error("Colunas de data não encontradas no DataFrame.")
        st.stop()
    
    df['Taxa'] = df['opening_fee'] + df['closing_fee'] + df['sum_carry_fees']
    df['Lucro'] = df['pl'] - df['Taxa']
    df['ROI'] = (df['Lucro'] / df['margin']) * 100
    df = df[df['Lucro'] != 0]
    df = df.reset_index(drop=True)
    df.index = df.index + 1
    df.index.name = "Nº"


    total_investido = df['margin'].sum()
    lucro_total = df['Lucro'].sum()
    roi_total = (lucro_total / total_investido) * 100 if total_investido != 0 else 0
    num_ordens = len(df)

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("💰 Total Investido", f"฿{int(total_investido):,}".replace(",", "."))
    col2.metric("📈 Lucro Total", f"฿{int(lucro_total):,}".replace(",", "."))
    col3.metric("📊 ROI Total", f"{roi_total:.2f}%")
    col4.metric("📋 Total de Ordens", num_ordens)

    df_formatado = df[[
        'Entrada', 'margin', 'price', 'Saida', 'Taxa', 'Lucro', 'ROI'
    ]].rename(columns={
        'margin': 'Margem',
        'price': 'Preço de entrada'
    })

    df_formatado['Margem'] = df_formatado['Margem'].astype(int).map('฿{:,}'.format)
    df_formatado['Preço de entrada'] = df_formatado['Preço de entrada'].map('${:,.2f}'.format)
    df_formatado['Taxa'] = df_formatado['Taxa'].astype(int).map('฿{:,}'.format)
    df_formatado['Lucro'] = df_formatado['Lucro'].astype(int).map('฿{:,}'.format)
    df_formatado['ROI'] = df_formatado['ROI'].map('{:.2f}%'.format)

    df_dashboard = df.copy()
    df_dashboard['Saida'] = pd.to_datetime(df_dashboard['Saida'], format='%d/%m/%Y')
    df_dashboard['Mes_dt'] = df_dashboard['Saida'].dt.to_period('M').dt.to_timestamp()
    meses_traducao = {
        1: 'Janeiro', 2: 'Fevereiro', 3: 'Março', 4: 'Abril', 5: 'Maio',
        6: 'Junho', 7: 'Julho', 8: 'Agosto', 9: 'Setembro',
        10: 'Outubro', 11: 'Novembro', 12: 'Dezembro'
    }
    df_dashboard['Mes'] = df_dashboard['Mes_dt'].dt.month.map(meses_traducao) + ' ' + df_dashboard['Mes_dt'].dt.year.astype(str)
    df_dashboard['Lucro_int'] = df_dashboard['Lucro'].astype(int)

    lucro_mensal = (
        df_dashboard.groupby(['Mes_dt', 'Mes'])['Lucro_int']
        .sum()
        .reset_index()
        .sort_values('Mes_dt')
    )

    fig1 = px.bar(
        lucro_mensal,
        x='Mes',
        y='Lucro_int',
        text='Lucro_int',
        title='Lucro mensal',
        labels={'Lucro_int': 'Lucro (฿)', 'Mes': 'Mês'},
        color_discrete_sequence=['cornflowerblue']
    )
    fig1.update_traces(texttemplate='฿%{text:,}', textposition='outside')
    fig1.update_layout(yaxis_title='Lucro (฿)', xaxis_title='Mês', bargap=0.3)
    st.plotly_chart(fig1, use_container_width=True)

    st.subheader("📋 Ordens Fechadas")
    
    # Estilo centralizado com índice a partir de 1
    styled_df = df_formatado.style \
        .set_table_styles([
            {"selector": "th", "props": [("text-align", "center")]},
            {"selector": "td", "props": [("text-align", "center")]}
        ]) \
        .set_properties(**{"text-align": "center"})
    
    # Mostrar tabela com índice a partir de 1
    df_formatado_com_indice = df_formatado.copy()
    df_formatado_com_indice.index = range(1, len(df_formatado) + 1)
    df_formatado_com_indice.index.name = "Nº"
    
    st.write(styled_df, use_container_width=True)




else:
    st.warning("Nenhuma ordem encontrada ou erro na API.")
