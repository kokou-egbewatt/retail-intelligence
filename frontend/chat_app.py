import os

import streamlit as st

# Default API URL (override with env STREAMLIT_CHAT_API_URL)
API_URL = os.environ.get("STREAMLIT_CHAT_API_URL", "http://localhost:8000")


def call_chat_api(query: str, country: str | None) -> str:
    import requests

    try:
        r = requests.post(
            f"{API_URL}/api/chat",
            json={"query": query, "country": country or None},
            timeout=30,
        )
        r.raise_for_status()
        return r.json().get("response", "")
    except requests.RequestException as e:
        return f"Error calling API: {e}"


def main():
    st.set_page_config(
        page_title="Global Retail Assistant", page_icon="🛒", layout="centered"
    )
    st.title("🛒 Global Retail Intelligence Engine")
    st.caption(
        "Ask about products, pricing by region, and warranty. Choose your country for accurate results."
    )

    country = st.selectbox(
        "Your country (for regional pricing)",
        [
            "",
            "Ghana",
            "Nigeria",
            "South Africa",
            "Kenya",
            "Germany",
            "United Kingdom",
            "France",
            "Netherlands",
            "United States",
            "Canada",
        ],
        index=0,
    )

    if "messages" not in st.session_state:
        st.session_state.messages = []

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if prompt := st.chat_input("Ask about products, price, or warranty..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                response = call_chat_api(prompt, country.strip() or None)
            st.markdown(response)
        st.session_state.messages.append({"role": "assistant", "content": response})

    st.sidebar.markdown("### How to run")
    st.sidebar.markdown("1. Start API: `uvicorn app.main:app --reload`")
    st.sidebar.markdown("2. Run this UI: `streamlit run frontend/chat_app.py`")
    st.sidebar.markdown(
        "3. Add `OPENROUTER_API_KEY` to `.env` for full LLM answers (get a key at [openrouter.ai](https://openrouter.ai))."
    )


if __name__ == "__main__":
    main()
