
import streamlit as st
import pandas as pd
import yfinance as yf
from reportlab.lib.pagesizes import LETTER
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
import io
import requests

# --- APP CONFIG ---
st.set_page_config(page_title="Margin of Safety OS", layout="wide")

# --- ACCESS CONTROL ---
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.title("🛡️ Margin of Safety OS")
    pwd = st.text_input("Enter Tester Access Code", type="password")
    if pwd == "GMU_TEST_2026":
        st.session_state.authenticated = True
        st.rerun()
    else:
        st.stop()

# --- DATA ENGINE ---
def get_clean_data(ticker_symbol):
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    })
    try:
        t = yf.Ticker(ticker_symbol, session=session)
        info = t.info
        # Use fast_info for price as a backup
        price = t.fast_info.get('last_price') or info.get('currentPrice') or info.get('regularMarketPrice')
        return info, t.news, price
    except:
        return None, None, None

def create_pdf(ticker, iv, mos, price):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=LETTER)
    styles = getSampleStyleSheet()
    elements = []
    
    header_style = ParagraphStyle('Header', parent=styles['Heading1'], alignment=1, textColor=colors.HexColor("#2E5077"))
    elements.append(Paragraph(f"Investment Memorandum: {ticker}", header_style))
    elements.append(Spacer(1, 12))
    
    body = f"""
    <b>Intrinsic Value:</b> ${iv:.2f}<br/>
    <b>Current Price:</b> ${price:.2f}<br/>
    <b>Margin of Safety:</b> {mos:.1f}%<br/><br/>
    <i>This report was generated via the Margin of Safety OS v1.4.</i>
    """
    elements.append(Paragraph(body, styles['Normal']))
    
    doc.build(elements)
    buffer.seek(0)
    return buffer

# --- UI ---
st.title("🛡️ Margin of Safety OS (v1.4)")
st.write("Focused Valuation & Strategic Weighting Engine")

ticker = st.sidebar.text_input("Enter Ticker", value="TSM").upper()

if st.sidebar.button("Analyze Ticker"):
    with st.spinner(f"Pulling data for {ticker}..."):
        info, news, price = get_clean_data(ticker)
        if info and price:
            st.session_state.info = info
            st.session_state.news = news
            st.session_state.price = price
            st.success(f"Data for {ticker} loaded.")
        else:
            st.error("Data fetch failed. Yahoo Finance may be throttling the connection. Wait 30s and try again.")

if "info" in st.session_state:
    inf = st.session_state.info
    price = st.session_state.price
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Current Price", f"${price:.2f}")
    col2.metric("P/E Ratio", inf.get('trailingPE', 'N/A'))
    col3.metric("Market Cap", f"${inf.get('marketCap', 0)/1e9:.1f}B")

    st.divider()

    # 1. Qualitative Section
    st.header("1. Strategic Qualitative Weighting")
    if st.session_state.news:
        for i, item in enumerate(st.session_state.news[:5]):
            title = item.get('title') or item.get('headline') or "Market News"
            with st.expander(f"NEWS: {title}"):
                st.write(f"Source: {item.get('publisher', 'Unknown')}")
                st.select_slider(f"Strategic Importance (1-5)", options=[1,2,3,4,5], value=3, key=f"v_{i}")
    else:
        st.warning("No recent news found.")
    
    st.divider()

    # 2. Probability Modeling
    st.header("2. Scenario Probability Modeling")
    cL, cR = st.columns(2)
    with cL:
        bear_p = st.slider("Bear Case %", 0, 100, 25)
        base_p = st.slider("Base Case %", 0, 100, 50)
        opt_p = 100 - (bear_p + base_p)
        st.info(f"Optimistic Case Probability: {opt_p}%")

    # Math
    iv = (price * 0.7 * bear_p/100) + (price * 1.15 * base_p/100) + (price * 1.5 * opt_p/100)
    mos = ((iv - price) / iv) * 100

    with cR:
        st.metric("Expected Intrinsic Value", f"${iv:.2f}", delta=f"{mos:.1f}% MoS")
        
        pdf = create_pdf(ticker, iv, mos, price)
        st.download_button("📥 Download Analysis Memo", data=pdf, file_name=f"{ticker}_Analysis.pdf")
