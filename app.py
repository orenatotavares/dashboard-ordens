import streamlit as st
import pandas as pd
import plotly.express as px
import time
import hmac
import base64
import hashlib
import urllib.parse
import requests

# ======================= CONFIGURAÇÕES =======================
st.set_page_config(page_title="Dashboard LNMarkets", layout="wide")
st.title("📊 Dashboard de Ordens Fechadas LNMarkets")

# 🔐 Credenciais
api_key = 'ndz4OOcqqo/k0qM82AmiJFWwmSg5tunQ+ywT/oqCgWM='
api_secret = '3FALcKBovy5/GiUL+mVbCvxEjbZ855ZnjeMebLSWuthBoNkjNm+/sY0D9lyPLkIgNo1x5bLPRVPs/U/2bTJT0Q=='
passphrase = 'renatoapi'

# ======================= FUNÇÕES =======================
def generate_signature(timestamp, method, path, query_string, secret):
    message = f"{timestamp}{method}{path}{query_string}"
    signature = hmac.new(secret, message.encode(), hashlib.sha256).digest()
    return base64.b64encode(signature).decode()

@st.cache_data(show_spinner=False)
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
        st.error(f"Erro {response.status_code}: {response.text}")
        return pd.DataFrame()

# ======================= INTERFACE =======================
atualizar = st.button("🔄 Atualizar Dados")

if atualizar:
    df = get_closed_positions.__wrapped__()
else:
    df = get_closed_positions()

if df.empty:
    st.warning("Nenhuma ordem fechada encontrada.")
    st.stop()

# ======================= TRATAMENTO DE DADOS =======================
df['Entrada'] = pd.to_datetime(df['market_filled_ts'], unit='ms').dt.strftime('%d/%m/%Y')
df['Saida'] = pd.to_datetime(df['closed_ts'], unit='ms').dt.strftime('%d/%m/%Y')
df['Taxa'] = df['opening_fee'] + df['closing_fee'] + df['sum_carry_fees']
df['Lucro'] = df['pl'] - df['Taxa']
df['ROI'] = (df['Lucro'] / df['margin']) * 100
df = df[df['Lucro'] != 0]

# Cópia formatada
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

# Cópia para gráfico
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
    .sum().reset_index().sort_values('Mes_dt')
)

# ======================= VISUALIZAÇÃO =======================
st.plotly_chart(px.bar(
    lucro_mensal,
    x='Mes',
    y='Lucro_int',
    text='Lucro_int',
    title='Lucro Mensal',
    labels={'Lucro_int': 'Lucro (฿)', 'Mes': 'Mês'},
    color_discrete_sequence=['cornflowerblue']
).update_traces(
    texttemplate='฿%{text:,}', textposition='outside'
).update_layout(
    yaxis_title='Lucro (฿)', xaxis_title='Mês', bargap=0.3
), use_container_width=True)

# ======================= RESUMO =======================
total_lucro = df['Lucro'].sum()
total_taxa = df['Taxa'].sum()
total_investido = df['margin'].sum()
total_ordens = df.shape[0]
roi_total = (total_lucro / total_investido) * 100 if total_investido != 0 else 0

st.markdown("""
### 📈 Resumo das Ordens Fechadas
""")
col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Total de Ordens", f"{total_ordens}")
col2.metric("Investido", f"฿{total_investido:,.0f}")
col3.metric("Lucro Líquido", f"฿{total_lucro:,.0f}")
col4.metric("Taxas Pagas", f"฿{total_taxa:,.0f}")
col5.metric("ROI Total", f"{roi_total:.2f}%")

# ======================= TABELA =======================
st.markdown("""
### 📋 Detalhamento das Ordens
""")
st.dataframe(df_formatado, use_container_width=True)
