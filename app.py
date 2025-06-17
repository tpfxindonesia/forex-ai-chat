#import streamlit as st
#import warnings
#warnings.filterwarnings("ignore")
#import requests, openai, pandas as pd, pandas_ta as ta, plotly.graph_objects as go
#from datetime import datetime
import warnings
warnings.filterwarnings("ignore", category=UserWarning)

import pandas_ta as ta
# Nonaktifkan squeeze_pro jika masih diimport otomatis
try:
    import pandas_ta.momentum as mom; del mom.squeeze_pro
except Exception:
    pass


# Setup
st.set_page_config(page_title="Forex AI Chat", page_icon=":money_with_wings:", layout="centered")
st.sidebar.image("assets/logo.png", width=120)
st.sidebar.markdown("# Forex AI Chat\n_Tanyai seputar forex trading_")

openai.api_key = st.secrets["OPENAI_API_KEY"]
TWELVE_KEY = st.secrets["TWELVEDATA_API_KEY"]

# utils
@st.cache_data(ttl=300)
def fetch_data(symbol):
    url = "https://api.twelvedata.com/time_series"
    params = {"symbol": symbol, "interval": "1h", "outputsize": 100, "apikey": TWELVE_KEY}
    r = requests.get(url, params=params).json()
    if "values" not in r: return None
    df = pd.DataFrame(r["values"]).astype({"open":float,"high":float,"low":float,"close":float})
    df["datetime"] = pd.to_datetime(df["datetime"])
    df = df.sort_values("datetime")
    df["RSI"] = ta.rsi(df["close"],14)
    df["EMA20"] = ta.ema(df["close"],20)
    df["SMA50"] = ta.sma(df["close"],50)
    return df

# UI
symbol = st.sidebar.text_input("Pasangan Forex", "EUR/USD")
question = st.text_area("Tanyakan forex...", height=100)
chat_history = st.session_state.setdefault("history", [])

if st.button("Kirim"):
    df = fetch_data(symbol.replace("/",""))
    if df is None:
        st.error("Data tidak tersedia.")
    else:
        last = df.iloc[-1]
        prompt = f"""
Anda seorang analis forex ahli.
Data terakhir {symbol} pada {last.datetime} UTC:
Open: {last.open}, High: {last.high}, Low: {last.low}, Close: {last.close}
RSI(14): {last.RSI:.2f}, EMA20: {last.EMA20:.5f}, SMA50: {last.SMA50:.5f}
Berdasarkan ini, jawablah: {question}
"""
        res = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role":"system","content":"Kamu adalah analis forex teknikal."},
                {"role":"user","content":prompt}
            ], temperature=0.3)
        answer = res.choices[0].message.content
        chat_history.append({"q": question, "a": answer, "df": df})

# tampil chat history & grafik
for msg in chat_history:
    st.markdown(f"**Kamu:** {msg['q']}")
    st.markdown(f"**AI:** {msg['a']}")
    df = msg["df"]
    fig = go.Figure(data=[go.Candlestick(x=df.datetime,
                                         open=df.open, high=df.high,
                                         low=df.low, close=df.close)])
    fig.add_scatter(x=df.datetime, y=df.EMA20, name="EMA20", line=dict(color="cyan"))
    fig.add_scatter(x=df.datetime, y=df.SMA50, name="SMA50", line=dict(color="magenta"))
    st.plotly_chart(fig, use_container_width=True)
