import streamlit as st
import requests
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# 設置 HTTP Headers
http_headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Accept': 'application/json, text/plain, */*',
}

st.set_page_config(page_title="股票價格分析工具", page_icon="📈", layout="wide")

st.title("📈 股票價格分析工具")
st.caption("版本: V04 (Streamlit Web版)")

# ===== 初始化 session state =====
if 'current_price' not in st.session_state:
    st.session_state.current_price = None
if 'historical_high' not in st.session_state:
    st.session_state.historical_high = None
if 'success_symbol' not in st.session_state:
    st.session_state.success_symbol = None
if 'is_etf' not in st.session_state:
    st.session_state.is_etf = False
if 'net_value' not in st.session_state:
    st.session_state.net_value = None

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

# ===== 按鈕觸發查詢 =====
if search_btn:
    symbol_input = stock_symbol.strip()
    current_price = None
    historical_high = None
    success_symbol = None

    try:
        # ===== 台股 =====
        if market == "TW":
            if symbol_input.endswith((".TW", ".TWO")):
                symbols_to_try = [symbol_input]
            else:
                symbols_to_try = [f"{symbol_input}.TW", f"{symbol_input}.TWO"]

            for test_sym in symbols_to_try:
                url = f"https://query1.finance.yahoo.com/v8/finance/chart/{test_sym}"
                payload = {'interval': '1d', 'range': '1y'}
                resp = requests.get(url, headers=http_headers, params=payload, timeout=10, verify=False)

                if resp.status_code == 200:
                    data = resp.json()
                    if 'chart' in data and data['chart'].get('result'):
                        result = data['chart']['result'][0]
                        closes = result.get('indicators', {}).get('quote', [{}])[0].get('close', [])
                        highs = result.get('indicators', {}).get('quote', [{}])[0].get('high', [])

                        valid_closes = [c for c in closes if c is not None]
                        valid_highs = [h for h in highs if h is not None]

                        if valid_closes:
                            current_price = float(valid_closes[-1])
                        if valid_highs:
                            historical_high = float(max(valid_highs))
                        if current_price:
                            success_symbol = test_sym
                            break


        # ===== 美股 =====
        elif market == "US":
            us_symbol = symbol_input.upper()
            url = f"https://query1.finance.yahoo.com/v8/finance/chart/{us_symbol}"
            payload = {'interval': '1d', 'range': 'max'}
            resp = requests.get(url, headers=http_headers, params=payload, timeout=10, verify=False)

            if resp.status_code == 200:
                data = resp.json()
                if 'chart' in data and data['chart'].get('result'):
                    result = data['chart']['result'][0]
                    closes = result.get('indicators', {}).get('quote', [{}])[0].get('close', [])
                    highs = result.get('indicators', {}).get('quote', [{}])[0].get('high', [])

                    valid_closes = [c for c in closes if c is not None]
                    valid_highs = [h for h in highs if h is not None]

                    if valid_closes:
                        current_price = float(valid_closes[-1])
                    if valid_highs:
                        historical_high = float(max(valid_highs))
                    if current_price:
                        success_symbol = us_symbol

    except Exception as e:
        st.error(f"請求錯誤: {e}")
        st.stop()

    # 儲存結果到 session state
    if current_price:
        if historical_high is None:
            historical_high = current_price

        # 偵測是否為 ETF
        is_etf = False
        net_value = None
        if market == "TW":
            # 台股 ETF 代碼開頭通常是 00 或 0
            if symbol_input.startswith('0'):
                is_etf = True
                # 嘗試從 Yahoo 獲取 ETF 淨值
                nav_url = f"https://www.twse.com.tw/rwd/zh/fund/T86?date=&stockNo={symbol_input}&response=json"
                nav_resp = requests.get(nav_url, headers=http_headers, timeout=10, verify=False)
                if nav_resp.status_code == 200:
                    try:
                        nav_data = nav_resp.json()
                        if nav_data.get('data') and nav_data['data'][0]:
                            nav = nav_data['data'][0]
                            nav_str = nav[3] if nav[3] != '--' else None
                            if nav_str:
                                net_value = float(nav_str.replace(',', ''))
                    except:
                        pass

        st.session_state.current_price = current_price
        st.session_state.historical_high = historical_high
        st.session_state.success_symbol = success_symbol
        st.session_state.is_etf = is_etf
        st.session_state.net_value = net_value
        st.rerun()
    else:
        st.error(f"無法獲取「{stock_symbol}」的股票資料")
        st.info("提示：請確認股票代號正確，如 2330、AAPL、MSFT 等")

# ===== 顯示查詢結果 =====
if st.session_state.current_price is not None:
    current_price = st.session_state.current_price
    historical_high = st.session_state.historical_high
    success_symbol = st.session_state.success_symbol
    is_etf = st.session_state.is_etf
    net_value = st.session_state.net_value

    # 判斷基準價
    if historical_high > current_price:
        p_base = historical_high
        base_type = "歷史最高點"
    else:
        p_base = current_price
        base_type = "目前成交價"

    # 計算回撤百分比
    drawdown_pct = ((historical_high - current_price) / historical_high) * 100

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

    if is_etf:
        if net_value:
            st.metric("ETF 每股淨值", f"${net_value:,.2f}")
        else:
            st.info("ETF 資訊：無淨值數據")

    # ===== 2. 自定義回撤計算 =====
    st.divider()
    st.header("2. 自定義回撤計算")

    drawdown_pct_input = st.slider("選擇回撤百分比", min_value=1, max_value=99, value=20, key="slider_dd")
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
        x_value = st.number_input("輸入金額 X", min_value=0, max_value=9999999, value=100000, step=1000, format="%d", key="input_x")

    with col_result:
        n = st.selectbox("選擇除數 N", list(range(1, 10)), index=0, key="select_n")
        result_val = x_value / n
        st.metric(f"Y = X ÷ {n}", f"${result_val:,.2f}")

    st.caption(f"公式：Y = {x_value:,} ÷ {n} = ${result_val:,.2f}")

else:
    st.info("👆 請輸入股票代號並點擊查詢")

st.divider()
st.caption("📊 數據來源：Yahoo Finance API")
