import streamlit as st
import yfinance as yf
import twstock
from datetime import datetime
import requests
from bs4 import BeautifulSoup
import time
import random
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# 設置 HTTP Headers 來減少被封鎖
http_headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

st.set_page_config(page_title="股票價格分析工具", page_icon="📈", layout="wide")

st.title("📈 股票價格分析工具")
st.caption("版本: V02 (Streamlit Web版)")

# ===== 1. 股票數據查詢 =====
st.header("1. 股票數據查詢")

col_market, col_symbol, col_btn = st.columns([1, 3, 1])

with col_market:
    market = st.radio("市場", ["TW", "US"], horizontal=True, index=0)

with col_symbol:
    stock_symbol = st.text_input("股票代號", value="2330", label_visibility="collapsed")

with col_btn:
    st.write("")
    search_btn = st.button("🔍 查詢", type="primary", use_container_width=True)

# 使用 session state 追蹤是否已查詢
if 'searched' not in st.session_state:
    st.session_state.searched = False

if search_btn:
    st.session_state.searched = True

if st.session_state.searched and stock_symbol:
    try:
        if market == "TW":
            # 台股代碼處理
            symbol_input = stock_symbol.strip()
            # 如果已經有 .TW 就不要重複加
            if not symbol_input.endswith((".TW", ".TWO")):
                symbols_to_try = [f"{symbol_input}.TW", f"{symbol_input}.TWO"]
            else:
                symbols_to_try = [symbol_input]
        else:
            symbols_to_try = [stock_symbol.strip().upper()]

        current_price = None
        historical_high = None
        success_symbol = None
        stock_info = None

        error_msg = ""

        # 優先使用台灣證券交易所 API 獲取台股數據
        if market == "TW":
            try:
                # 使用 TAIEX API 獲取即時報價
                url = f"https://www.twse.com.tw/rwd/zh/fund/T86?date=&stockNo={symbol_input}&response=json"
                resp = requests.get(url, headers=http_headers, timeout=10, verify=False)
                if resp.status_code == 200:
                    data = resp.json()
                    if data.get('data'):
                        # 取得最新價格
                        latest = data['data'][0]
                        current_price = float(latest[-5].replace(',', ''))  # 收盤價
                        # 嘗試取得歷史資料來計算歷史最高
                        hist_url = f"https://www.twse.com.tw/rwd/zh/fund/T86?date=20240101&stockNo={symbol_input}&response=json"
                        hist_resp = requests.get(hist_url, headers=http_headers, timeout=10, verify=False)
                        if hist_resp.status_code == 200:
                            hist_data = hist_resp.json()
                            if hist_data.get('data'):
                                highs = [float(d[-3].replace(',', '')) for d in hist_data['data'] if d[-3] != '--']
                                if highs:
                                    historical_high = max(highs)
                        success_symbol = f"{symbol_input}.TW"
            except Exception as e:
                error_msg = str(e)
                # 如果台灣證交所 API 失敗，改用 twstock
                try:
                    stock = twstock.Stock(symbol_input)
                    stock.fetch_from_today()
                    if stock.price:
                        current_price = float(stock.price[-1])
                        success_symbol = f"{symbol_input}.TW"
                except:
                    pass

        # 如果台股失敗，嘗試用 yfinance (可能會被 rate limit)
        if not success_symbol and market == "US":
            for sym in symbols_to_try:
                try:
                    # 延遲避免被限流
                    time.sleep(2)

                    stock = yf.Ticker(sym)
                    # 設定代理或使用更保守的請求
                    stock_info = stock.info

                    if not stock_info:
                        # 如果 info 為空，嘗試從歷史資料獲取
                        hist = stock.history(period="5d")
                        if not hist.empty:
                            current_price = float(hist['Close'].iloc[-1])
                    else:
                        current_price = stock_info.get('currentPrice') or stock_info.get('regularMarketPrice')

                    if current_price is None:
                        hist = stock.history(period="5d")
                        if not hist.empty:
                            current_price = float(hist['Close'].iloc[-1])

                    if current_price is not None:
                        hist_data = stock.history(period="max")
                        if not hist_data.empty:
                            historical_high = float(hist_data['High'].max())
                        else:
                            historical_high = current_price
                        success_symbol = sym
                        break
                except Exception as e:
                    error_msg = str(e)
                    continue

        if current_price is None:
            st.session_state.searched = False  # 重置搜尋狀態
            st.error(f"無法獲取「{stock_symbol}」的股票資料")
            if error_msg:
                st.error(f"錯誤原因: {error_msg}")
            if "rate limited" in error_msg.lower() or "too many requests" in error_msg.lower():
                st.warning("⏳ Yahoo Finance 伺服器忙碌中，請稍等 30 秒後再試")
            else:
                st.info("提示：請確認股票代號正確，如 2330、AAPL、MSFT 等")
        else:
            # 判斷基準價
            if historical_high > current_price:
                p_base = historical_high
                base_type = "歷史最高點"
            else:
                p_base = current_price
                base_type = "目前成交價"

            # 計算回撤百分比
            if historical_high > 0:
                drawdown_pct = ((historical_high - current_price) / historical_high) * 100
            else:
                drawdown_pct = 0

            # 檢查是否為ETF
            is_etf = False
            net_value = None
            quote_type = stock_info.get('quoteType', '').upper() if stock_info else ''
            type_disp = stock_info.get('typeDisp', '').upper() if stock_info else ''
            if stock_info:
                is_etf = quote_type == 'ETF' or 'ETF' in type_disp
                net_value = stock_info.get('navPrice')

            # 如果是台股ETF但沒有navPrice，嘗試從wantgoo獲取
            if market == "TW" and not net_value:
                try:
                    url = f"https://www.wantgoo.com/stock/{stock_symbol}"
                    resp = requests.get(url, headers=http_headers, timeout=5, verify=False)
                    if resp.status_code == 200:
                        soup = BeautifulSoup(resp.text, 'html.parser')
                        nav_elem = soup.find(string='每股淨值')
                        if nav_elem:
                            parent = nav_elem.find_parent('div')
                            if parent:
                                nav_text = parent.get_text(strip=True)
                                import re
                                match = re.search(r'[\d.]+', nav_text)
                                if match:
                                    net_value = float(match.group())
                except:
                    pass

            # ===== 顯示查詢結果 =====
            st.session_state.searched = False  # 重置搜尋狀態
            st.success(f"✅ 查詢成功: {success_symbol}" + (" (ETF)" if is_etf else ""))

            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("目前成交價", f"${current_price:,.2f}")
            with col2:
                st.metric("歷史最高點", f"${historical_high:,.2f}")
            with col3:
                st.metric("距歷史最高點回撤", f"{drawdown_pct:.2f}%", delta_color="inverse")
            with col4:
                st.metric("基準價 (P_base)", f"${p_base:,.2f}", delta=base_type)

            if net_value:
                st.metric("ETF每股淨值", f"${net_value:,.2f}")
            elif is_etf:
                st.info("ETF 資訊：無淨值數據")

            # ===== 2. 自定義回撤計算 =====
            st.divider()
            st.header("2. 自定義回撤計算")

            col_pct, col_result = st.columns([2, 2])

            with col_pct:
                drawdown_pct_input = st.slider("選擇回撤百分比", min_value=1, max_value=99, value=20)

            with col_result:
                drawdown_price = p_base * (1 - drawdown_pct_input / 100)
                st.metric("對應價格", f"${drawdown_price:,.2f}", delta=f"回撤 {drawdown_pct_input}%")

            # ===== 3. 回撤加碼區間 =====
            st.divider()
            st.header("3. 回撤加碼區間 (90% - 10%)")

            percentages = [90, 80, 70, 60, 50, 40, 30, 20, 10]

            cols = st.columns(9)
            for i, pct in enumerate(percentages):
                price = p_base * (pct / 100)
                with cols[i]:
                    st.metric(f"{pct}%", f"${price:,.0f}")

            # ===== 4. 金額分配計算機 =====
            st.divider()
            st.header("4. 金額分配計算機")

            col_x, col_result = st.columns([2, 1])

            with col_x:
                x_value = st.number_input(
                    "輸入金額 X",
                    min_value=0,
                    max_value=9999999,
                    value=100000,
                    step=1000,
                    format="%d"
                )

            with col_result:
                n = st.selectbox("選擇除數 N", list(range(1, 10)), index=0)
                result = x_value / n
                st.metric(f"Y = X ÷ {n}", f"${result:,.2f}")

            st.caption(f"公式：Y = {x_value:,} ÷ {n} = ${result:,.2f}")

    except Exception as e:
        st.error(f"查詢失敗: {str(e)}")
        st.info("提示：請確認股票代號正確，如 2330、AAPL、MSFT 等")

else:
    st.info("👆 請輸入股票代號並點擊查詢")

st.divider()
st.caption("📊 數據來源：Yahoo Finance | 使用 yfinance 獲取即時報價")