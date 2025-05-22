import time
import hmac
import base64
import hashlib
import urllib.parse
import requests
import pandas as pd
import plotly.express as px

# 🔐 Substitua pelas suas credenciais reais
api_key = 'ndz4OOcqqo/k0qM82AmiJFWwmSg5tunQ+ywT/oqCgWM='  # chave pública correta
api_secret = '3FALcKBovy5/GiUL+mVbCvxEjbZ855ZnjeMebLSWuthBoNkjNm+/sY0D9lyPLkIgNo1x5bLPRVPs/U/2bTJT0Q=='  # secret (base64, termina com ==)
passphrase = 'renatoapi'

# Transforma a chave secreta em bytes
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
        print("✅ Dados obtidos com sucesso!")
        return pd.DataFrame(response.json())
    else:
        print(f"❌ Erro: {response.status_code}")
        print(response.text)
        return pd.DataFrame()

# Obter os dados e armazenar no DataFrame
df = get_closed_positions()

# Bloco 2 - Tratamento final e formatação das ordens fechadas

# Converter timestamps e formatar datas
df['Entrada'] = pd.to_datetime(df['market_filled_ts'], unit='ms').dt.strftime('%d/%m/%Y')
df['Saida'] = pd.to_datetime(df['closed_ts'], unit='ms').dt.strftime('%d/%m/%Y')

# Somar taxas
df['Taxa'] = df['opening_fee'] + df['closing_fee'] + df['sum_carry_fees']

# Calcular lucro líquido
df['Lucro'] = df['pl'] - df['Taxa']

# Calcular ROI
df['ROI'] = (df['Lucro'] / df['margin']) * 100

# Filtrar apenas ordens com lucro diferente de zero
df = df[df['Lucro'] != 0]

# Selecionar e renomear colunas
df_formatado = df[[
    'Entrada', 'margin', 'price', 'Saida', 'Taxa', 'Lucro', 'ROI'
]].rename(columns={
    'margin': 'Margem',
    'price': 'Preço de entrada'
})

# Formatar valores
df_formatado['Margem'] = df_formatado['Margem'].astype(int).map('฿{:,}'.format)
df_formatado['Preço de entrada'] = df_formatado['Preço de entrada'].map('${:,.2f}'.format)
df_formatado['Taxa'] = df_formatado['Taxa'].astype(int).map('฿{:,}'.format)
df_formatado['Lucro'] = df_formatado['Lucro'].astype(int).map('฿{:,}'.format)
df_formatado['ROI'] = df_formatado['ROI'].map('{:.2f}%'.format)

# Garantir que a data de Saída está no formato datetime
df_dashboard = df.copy()
df_dashboard['Saida'] = pd.to_datetime(df_dashboard['Saida'], format='%d/%m/%Y')

# Criar coluna com mês/ano real para ordenação
df_dashboard['Mes_dt'] = df_dashboard['Saida'].dt.to_period('M').dt.to_timestamp()

# Criar rótulo traduzido para exibir no gráfico
meses_traducao = {
    1: 'Janeiro', 2: 'Fevereiro', 3: 'Março', 4: 'Abril', 5: 'Maio',
    6: 'Junho', 7: 'Julho', 8: 'Agosto', 9: 'Setembro',
    10: 'Outubro', 11: 'Novembro', 12: 'Dezembro'
}
df_dashboard['Mes'] = df_dashboard['Mes_dt'].dt.month.map(meses_traducao) + ' ' + df_dashboard['Mes_dt'].dt.year.astype(str)

# Converter 'Lucro' para inteiro (remover ฿ e vírgulas)
df_dashboard['Lucro_int'] = (
    df_dashboard['Lucro']
    .astype(str)
    .str.replace('฿', '', regex=False)
    .str.replace(',', '', regex=False)
    .astype(int)
)

# Agrupar lucro por mês (usando a data real para ordenação)
lucro_mensal = (
    df_dashboard.groupby(['Mes_dt', 'Mes'])['Lucro_int']
    .sum()
    .reset_index()
    .sort_values('Mes_dt')
)

# Criar gráfico
fig1 = px.bar(
    lucro_mensal,
    x='Mes',
    y='Lucro_int',
    text='Lucro_int',
    title='Lucro mensal com base na data de Saída',
    labels={'Lucro_int': 'Lucro (฿)', 'Mes': 'Mês'},
    color_discrete_sequence=['cornflowerblue']
)

# Melhorar layout
fig1.update_traces(texttemplate='฿%{text:,}', textposition='outside')
fig1.update_layout(
    uniformtext_minsize=8,
    uniformtext_mode='hide',
    yaxis_title='Lucro (฿)',
    xaxis_title='Mês',
    bargap=0.3
)

fig1.show()
