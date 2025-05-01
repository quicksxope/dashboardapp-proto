import streamlit as st

def render():
    st.title("Finance Dashboard")
    st.metric("Revenue", "$1.2M")
    st.metric("Expenses", "$800K")
    st.bar_chart({"Q1": [400000], "Q2": [800000]})
