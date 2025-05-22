import time
import hmac
import base64
import hashlib
import urllib.parse
import requests
import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(page_title="Dashboard de Ordens", layout="wide")
st.title("📊 Dashboard de Ordens Fechadas")

# 🔄 Botão para atualizar
if st.button("🔄 Atualizar dados"):
    st.experimental_rerun()

# 🔐 Credenciais
api_key = 'ndz4OOcqqo/k0qM82AmiJFWwmSg5tunQ+ywT/oqCgWM='
api_secret = '3FALcKBovy5/GiUL+mVbCvxEjbZ855ZnjeMebLSWuthBoNkjNm+/sY0D9lyPLkIgNo1x5bLPRVPs/U/2bTJT0Q=='
passphrase = 'renatoapi'

if isinstance(api_secret, str):
    api_secret = api_secret.encode()

def generate_signature(timestamp, method, path, query_string, secret):
    message = f"{timestamp}{method}{path}{query_string}"
    signature = hmac.new(secret, message.encode(), hashlib.sha256).digest()
    return base64.b64encode(signature).decode()

@st.cache_data
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
        st.error(f"Erro: {response.status_code}")
        st.error(response.text)
        return pd.DataFrame()

df = get_closed_positions()

# Processamento
df['Entrada'] = pd.to_datetime(df['market_filled_ts'], unit='ms').dt.strftime('%d/%m/%Y')
df['Saida'] = pd.to_datetime(df['closed_ts'], unit='ms')
df['Taxa'] = df['opening_fee'] + df['closing_fee'] + df['sum_carry_fees']
df['Lucro'] = df['pl'] - df['Taxa']
df['ROI'] = (df['Lucro'] / df['margin']) * 100
df = df[df['Lucro'] != 0]

# KPIs
total_investido = df['margin'].sum()
lucro_total = df['pl'].sum()
taxa_total = df['Taxa'].sum()
lucro_liquido = lucro_total - taxa_total
rentabilidade = lucro_liquido / total_investido * 100
ganhos = len(df[df['Lucro'] > 0])
perdas = len(df[df['Lucro'] < 0])
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

# Gráfico
df['Mes_dt'] = df['Saida'].dt.to_period('M').dt.to_timestamp()
meses_traducao = {
    1: 'Janeiro', 2: 'Fevereiro', 3: 'Março', 4: 'Abril', 5: 'Maio',
    6: 'Junho', 7: 'Julho', 8: 'Agosto', 9: 'Setembro',
    10: 'Outubro', 11: 'Novembro', 12: 'Dezembro'
}
df['Mes'] = df['Mes_dt'].dt.month.map(meses_traducao) + ' ' + df['Mes_dt'].dt.year.astype(str)
df['Lucro_int'] = df['Lucro'].astype(int)

lucro_mensal = df.groupby(['Mes_dt', 'Mes'])['Lucro_int'].sum().reset_index().sort_values('Mes_dt')

fig = px.bar(
    lucro_mensal,
    x='Mes',
    y='Lucro_int',
    text='Lucro_int',
    title='Lucro mensal com base na data de Saída',
    labels={'Lucro_int': 'Lucro (฿)', 'Mes': 'Mês'},
    color_discrete_sequence=['#29B6F6']
)
fig.update_traces(texttemplate='฿%{text:,}', textposition='outside')
fig.update_layout(
    yaxis_title='Lucro (฿)',
    xaxis_title='Mês',
    bargap=0.3
)
st.plotly_chart(fig, use_container_width=True)
