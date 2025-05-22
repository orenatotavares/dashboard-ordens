import streamlit as st
import pandas as pd
from datetime import date

st.set_page_config(page_title="Controle Financeiro", layout="wide")
st.title("💼 Controle Financeiro")

# Inicializa sessão
if "transacoes" not in st.session_state:
    st.session_state.transacoes = pd.DataFrame(columns=["Data", "Tipo", "Valor"])

# Formulário para nova transação
with st.form("form_transacao"):
    col1, col2, col3 = st.columns(3)
    data = col1.date_input("Data", date.today())
    tipo = col2.selectbox("Tipo", ["Depósito", "Saque"])
    valor = col3.number_input("Valor (฿)", min_value=0.0, step=0.0001, format="%.4f")
    submit = st.form_submit_button("Adicionar")

if submit and valor > 0:
    nova_transacao = {"Data": data, "Tipo": tipo, "Valor": valor}
    st.session_state.transacoes = pd.concat(
        [st.session_state.transacoes, pd.DataFrame([nova_transacao])],
        ignore_index=True
    )
    st.success("Transação adicionada!")

# Cálculo de saldo
df_transacoes = st.session_state.transacoes.copy()
saldo = df_transacoes.apply(
    lambda row: row["Valor"] if row["Tipo"] == "Depósito" else -row["Valor"], axis=1
).sum()

st.metric("💰 Saldo na plataforma", f"฿{saldo:,.4f}")

# Lucro do dashboard
lucro_total = st.session_state.get("lucro_total", 0)
saldo_geral = saldo + lucro_total
st.metric("📈 Saldo total com lucros", f"฿{saldo_geral:,.4f}")

# Mostrar histórico
st.subheader("📜 Histórico de transações")
st.dataframe(df_transacoes, use_container_width=True)
