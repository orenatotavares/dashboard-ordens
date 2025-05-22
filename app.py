import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import time
import base64
import hashlib
import hmac
import urllib.parse
import requests

st.set_page_config(page_title="Dashboard de Ordens", layout="wide")
st.title("📊 Dashboard de Ordens Fechadas")

if st.button("🔄 Atualizar dados"):
    st.experimental_rerun()

@st.cache_data
def carregar_dados():
    api_key = 'ndz4OOcqqo/k0qM82AmiJFWwmSg5tunQ+ywT/oqCgWM='  # chave pública correta
    api_secret = '3FALcKBovy5/GiUL+mVbCvxEjbZ855ZnjeMebLSWuthBoNkjNm+/sY0D9lyPLkIgNo1x5bLPRVPs/U/2bTJT0Q=='  # secret (base64, termina com ==)
    passphrase = 'renatoapi'

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
            st.error(f"Erro ao buscar dados: {response.status_code}")
            return pd.DataFrame()

    return get_closed_positions()

df = carregar_dados()

if df.empty:
    st.warning("Nenhum dado retornado.")
    st.stop()

df['Entrada'] = pd.to_datetime(df['Entrada'], dayfirst=True).dt.strftime('%d/%m/%Y')
df['Saida'] = pd.to_datetime(df['Saida'], dayfirst=True)
df['Margem_int'] = df['Margem'].str.replace('฿', '').str.replace('.', '').astype(int)
df['Lucro_int'] = df['Lucro'].str.replace('฿', '').str.replace('.', '').astype(int)
df['ROI_float'] = df['ROI'].str.replace('%', '').str.replace(',', '.').astype(float)

total_investido = df['Margem_int'].sum()
lucro_total = df['Lucro_int'].sum()
taxa_total = df['Taxa'].str.replace('฿', '').str.replace('.', '').astype(int).sum()
lucro_liquido = lucro_total
rentabilidade = lucro_liquido / total_investido * 100 if total_investido else 0
ganhos = len(df[df['Lucro_int'] > 0])
perdas = len(df[df['Lucro_int'] < 0])
total_ordens = len(df)

col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("₿ Total Investido", f"{total_investido:,.0f}".replace(",", "."))
col2.metric("₿ Lucro Total", f"{lucro_total:,.0f}".replace(",", "."))
col3.metric("₿ Total de Taxas", f"{taxa_total:,.0f}".replace(",", "."))
col4.metric("₿ Lucro Líquido", f"{lucro_liquido:,.0f}".replace(",", "."))
col5.metric("Rentabilidade", f"{rentabilidade:.2f}%")

col6, col7, col8 = st.columns(3)
col6.metric("Total de Ordens", total_ordens)
col7.metric("Ganhos", ganhos)
col8.metric("Perdas", perdas)

df['Mes'] = df['Saida'].dt.to_period('M').dt.strftime('%B de %Y')
lucro_mensal = df.groupby('Mes')['Lucro_int'].sum().reset_index()
lucro_mensal['LucroFormatado'] = lucro_mensal['Lucro_int'].apply(lambda x: f"฿{x:,}".replace(",", "."))

fig = px.bar(
    lucro_mensal,
    x='Mes',
    y='Lucro_int',
    text='LucroFormatado',
    title='Lucro por Mês',
    labels={'Lucro_int': 'Lucro (฿)', 'Mes': 'Mês'},
    color_discrete_sequence=['#29B6F6']
)
fig.update_traces(textposition='outside')
fig.update_layout(yaxis_title='Lucro (฿)', xaxis_title='Mês')

st.plotly_chart(fig, use_container_width=True)
