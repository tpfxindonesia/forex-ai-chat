import streamlit as st
import openai
import os
from dotenv import load_dotenv
import requests

load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

def get_forex_price(pair="EUR/USD"):
    base, quote = pair.split("/")
    url = f"https://api.twelvedata.com/price?symbol={base}/{quote}&apikey={os.getenv('TWELVE_DATA_API_KEY')}"
    response = requests.get(url)
    data = response.json()
    if "price" in data:
        return float(data["price"])
    return None

st.set_page_config(page_title="Forex AI Chat", layout="wide")
st.title("💬 Forex AI Chat")
st.markdown("Tanyakan apa pun tentang trading forex")

if "messages" not in st.session_state:
    st.session_state.messages = []

selected_pair = st.sidebar.selectbox("Pilih Pasangan Mata Uang", ["EUR/USD", "USD/JPY", "GBP/USD", "AUD/USD", "USD/CAD"])
price = get_forex_price(selected_pair)
if price:
    st.sidebar.metric(label=f"Harga Saat Ini {selected_pair}", value=f"{price:.4f}")
else:
    st.sidebar.warning("Gagal mengambil data harga.")

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

user_input = st.chat_input("Tulis pertanyaanmu di sini...")
if user_input:
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)
    with st.chat_message("assistant"):
        with st.spinner("Sedang memproses..."):
            forex_info = f"Harga saat ini untuk {selected_pair} adalah {price:.4f}." if price else ""
            prompt = f"{forex_info}\n\nPertanyaan pengguna: {user_input}\n\nBerikan jawaban analitis dan edukatif seputar forex."
            from openai import OpenAI
                client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

                # Di dalam st.chat_message("assistant"):
                response = client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": "Kamu adalah asisten ahli forex yang memberikan wawasan dan analisis profesional."},
                        {"role": "user", "content": prompt},
                    ]
                )
reply = response.choices[0].message.content

            reply = response.choices[0].message["content"]
            st.markdown(reply)
            st.session_state.messages.append({"role": "assistant", "content": reply})
