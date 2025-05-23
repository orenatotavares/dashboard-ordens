df_hoje['closed_ts_dt'] = pd.to_datetime(df_hoje['closed_ts'], unit='ms', errors='coerce').dt.tz_localize('UTC').dt.tz_convert('America/Sao_Paulo')
df_hoje = df_hoje[df_hoje['closed_ts_dt'].dt.date == data_hoje]
