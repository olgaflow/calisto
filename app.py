import streamlit as st
import ollama

st.set_page_config(page_title="Mon IA Locale", page_icon="ð¤", layout="wide")

MODEL = "llama3.2"

st.title("ð¤ Mon IA Locale (Ollama)")
st.caption(f"Modele : {MODEL} - tout tourne en local sur votre PC")

if "messages" not in st.session_state:
    st.session_state.messages = []

with st.sidebar:
    st.header("Reglages")
    system_prompt = st.text_area(
        "Instruction systeme (personnalite de l'IA)",
        value="Tu es un assistant utile, amical et tu reponds en francais.",
        height=120,
    )
    temperature = st.slider("Creativite (temperature)", 0.0, 1.5, 0.7, 0.1)
    if st.button("Effacer la conversation"):
        st.session_state.messages = []
        st.rerun()

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if prompt := st.chat_input("Ãcrivez votre message ici..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    messages = [{"role": "system", "content": system_prompt}] + st.session_state.messages

    with st.chat_message("assistant"):
        placeholder = st.empty()
        full = ""
        try:
            stream = ollama.chat(
                model=MODEL,
                messages=messages,
                stream=True,
                options={"temperature": temperature},
            )
            for chunk in stream:
                token = chunk["message"]["content"]
                full += token
                placeholder.markdown(full + "â")
            placeholder.markdown(full)
        except Exception as e:
            full = f"Erreur : {e}"
            placeholder.markdown(full)
    st.session_state.messages.append({"role": "assistant", "content": full})
