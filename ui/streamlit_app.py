import pandas as pd
import requests
import streamlit as st

st.set_page_config(page_title="SpendSense", layout="wide")
st.title("SpendSense")
st.caption("Local-first statement ingest, categorize, and grounded spend Q&A")

base = st.sidebar.text_input("API base URL", "http://127.0.0.1:8000")

try:
    health = requests.get(f"{base}/health", timeout=2).json()
    st.sidebar.write("API:", health.get("status"))
    st.sidebar.write("Ollama:", health.get("ollama"))
except Exception as exc:
    st.sidebar.error(f"API unreachable: {exc}")

uploaded = st.file_uploader("Upload CSV or PDF statement", type=["csv", "pdf"])
if uploaded and st.button("Ingest"):
    files = {"file": (uploaded.name, uploaded.getvalue(), uploaded.type or "application/octet-stream")}
    r = requests.post(f"{base}/upload", files=files, timeout=60)
    if r.status_code == 200:
        st.success(r.json())
    else:
        st.error(r.text)

col1, col2 = st.columns(2)
with col1:
    use_llm = st.checkbox("Use Ollama for leftover rows", value=False)
    if st.button("Categorize (rules + optional Ollama)"):
        r = requests.post(
            f"{base}/categorize",
            json={"use_llm": use_llm},
            timeout=600 if use_llm else 120,
        )
        st.write(r.json() if r.status_code == 200 else r.text)

with col2:
    st.write("Tip: money totals always come from SQL, not the LLM.")

tx = requests.get(f"{base}/transactions", timeout=30)
if tx.status_code == 200:
    df = pd.DataFrame(tx.json())
    st.subheader("Transactions")
    st.dataframe(df, use_container_width=True)

    if not df.empty:
        txn_id = st.number_input("Transaction id to edit", min_value=1, step=1)
        new_cat = st.text_input("New category")
        if st.button("Update category") and new_cat:
            r = requests.patch(f"{base}/transactions/{int(txn_id)}", json={"category": new_cat})
            st.write(r.json() if r.ok else r.text)

st.subheader("Ask")
q = st.text_input("Question", "How much on food in August 2024?")
if st.button("Ask"):
    with st.spinner("Asking…"):
        r = requests.post(f"{base}/ask", json={"question": q}, timeout=120)
    if r.ok:
        body = r.json()
        st.write(body["answer"])
        st.dataframe(pd.DataFrame(body.get("citations") or []), use_container_width=True)
        with st.expander("Tool trace"):
            st.json(body.get("tool_trace"))
    else:
        st.error(r.text)
