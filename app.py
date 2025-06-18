import streamlit as st
import openai
import os
import requests
import pandas as pd
import plotly.graph_objects as go
import pandas_ta as ta
from datetime import datetime
from dotenv import load_dotenv
from openai import OpenAI

# Load API Keys
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
TWELVE_API_KEY = os.getenv("TWELVE_DATA_API_KEY")
NEWS_API_KEY = os.getenv("NEWS_API_KEY")

st.set_page_config(page_title="Forex AI Chat", layout="wide")
st.title("💬 Forex AI Chat")
st.markdown("Tanyakan apa pun tentang trading forex")

# Chat memory
if "messages" not in st.session_state:
    st.session_state.messages = []

# =========================
# 🔁 Ambil Data Forex
# =========================
def get_time_series(pair="EUR/USD"):
    base, quote = pair.split("/")
    url = f"https://api.twelvedata.com/time_series?symbol={base}/{quote}&interval=1h&outputsize=100&apikey={TWELVE_API_KEY}"
    r = requests.get(url).json()
    if "values" in r:
        df = pd.DataFrame(r["values"])
        df["datetime"] = pd.to_datetime(df["datetime"])
        df = df.sort_values("datetime")
        df[["open", "high", "low", "close"]] = df[["open", "high", "low", "close"]].astype(float)
        return df
    return None

# =========================
# 📈 Indikator
# =========================
def add_indicators(df):
    df["MA20"] = ta.sma(df["close"], length=20)
    df["RSI14"] = ta.rsi(df["close"], length=14)
    macd = ta.macd(df["close"])
    df["MACD"] = macd["MACD_12_26_9"]
    df["Signal"] = macd["MACDs_12_26_9"]
    return df

# =========================
# 📊 Plot Grafik
# =========================
def plot_chart(df):
    st.subheader("📉 Grafik Candlestick")
    fig = go.Figure(data=[go.Candlestick(
        x=df["datetime"],
        open=df["open"],
        high=df["high"],
        low=df["low"],
        close=df["close"]
    )])
    fig.update_layout(xaxis_rangeslider_visible=False, height=500)
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("📈 Moving Average (MA20)")
    st.line_chart(df.set_index("datetime")[["close", "MA20"]])

    st.subheader("📊 RSI (14)")
    st.line_chart(df.set_index("datetime")[["RSI14"]])

    st.subheader("📊 MACD & Signal")
    st.line_chart(df.set_index("datetime")[["MACD", "Signal"]])

# =========================
# 🗞 Sentimen dari NewsAPI
# =========================
def get_news_sentiment(pair="EUR/USD"):
    keywords = pair.replace("/", "")
    url = f"https://newsapi.org/v2/everything?q={keywords}+forex&language=en&sortBy=publishedAt&pageSize=5&apiKey={NEWS_API_KEY}"
    r = requests.get(url).json()
    if "articles" not in r:
        return "Tidak ditemukan berita terkait saat ini."

    news_summaries = "\n\n".join([f"- {a['title']}: {a['description']}" for a in r["articles"] if a["description"]])
    prompt = (
        f"Berdasarkan berita berikut tentang pasangan mata uang {pair}:\n\n"
        f"{news_summaries}\n\n"
        "Buatlah ringkasan sentimen pasar terhadap pasangan mata uang tersebut. "
        "Gunakan gaya analisis profesional dan bahasa Indonesia."
    )
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content

# =========================
# UI
# =========================
pair = st.sidebar.selectbox("Pilih Pasangan Mata Uang", ["EUR/USD", "USD/JPY", "GBP/USD", "AUD/USD", "USD/CAD"])
data = get_time_series(pair)
if data is not None:
    data = add_indicators(data)
    price_now = data["close"].iloc[-1]
    price_prev = data["close"].iloc[-2]
    change = price_now - price_prev
    percent = (change / price_prev) * 100
    trend = "📈 naik" if change > 0 else "📉 turun"
    st.sidebar.metric(label=f"Harga Saat Ini {pair}", value=f"{price_now:.4f}", delta=f"{percent:.2f}%")

    plot_chart(data)

    st.subheader("🧠 Analisa Sentimen Pasar")
    sentiment = get_news_sentiment(pair)
    st.markdown(sentiment)
else:
    st.warning("Gagal mengambil data harga.")

# =========================
# AI Chat (Spesifik & Analitis)
# =========================
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

user_input = st.chat_input("Tulis pertanyaanmu...")
if user_input:
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    with st.chat_message("assistant"):
        with st.spinner("Menganalisis..."):
            system_prompt = (
                "Kamu adalah analis forex profesional. Jawabanmu harus tajam, spesifik, dan analitis. "
                "Gunakan data teknikal seperti MA, RSI, MACD, serta sentimen pasar."
            )
            data_context = f"Harga saat ini {pair} = {price_now:.4f} ({trend}), RSI = {data['RSI14'].iloc[-1]:.2f}, MACD = {data['MACD'].iloc[-1]:.4f}, Signal = {data['Signal'].iloc[-1]:.4f}."
            full_prompt = f"{data_context}\n\n{user_input}"

            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": full_prompt}
                ]
            )
            reply = response.choices[0].message.content
            st.markdown(reply)
            st.session_state.messages.append({"role": "assistant", "content": reply})
