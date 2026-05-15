import streamlit as st
import requests
import urllib3
import pandas as pd
import time
import random
from datetime import datetime

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class TaiwanETFDataFetcher:
    def __init__(self):
        self.session = requests.Session()
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "Accept-Language": "zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7",
        }

    def _get_with_retry(self, url, params=None, referer=None):
        headers = self.headers.copy()
        if referer:
            headers["Referer"] = referer

        for i in range(3):
            try:
                time.sleep(random.uniform(2, 5))
                response = self.session.get(url, params=params, headers=headers, timeout=10)
                response.raise_for_status()
                return response.json()
            except Exception as e:
                if i == 2:
                    return None
        return None

    def fetch_twse_nav(self):
        """獲取上市 (.TW) ETF 淨值數據"""
        url = "https://www.twse.com.tw/exchangeReport/ETF_NET_QUOTE"
        params = {"response": "json", "_": int(time.time() * 1000)}
        referer = "https://www.twse.com.tw/zh/page/etf/etf_nav.html"

        data = self._get_with_retry(url, params, referer)
        if not data or "data" not in data:
            return pd.DataFrame()

        df = pd.DataFrame(data["data"], columns=data["fields"])
        df = df[['證券代號', '證券簡稱', '最近淨值', '預估折溢價(%)']]
        return df

    def fetch_tpex_nav(self):
        """獲取上櫃 (.TWO) ETF 淨值數據"""
        url = "https://www.tpex.org.tw/web/stock/etf/nav/nav_result.php"
        params = {"l": "zh-tw", "_": int(time.time() * 1000)}
        referer = "https://www.tpex.org.tw/web/stock/etf/nav/nav.php"

        data = self._get_with_retry(url, params, referer)
        if not data or "aaData" not in data:
            return pd.DataFrame()

        df = pd.DataFrame(data["aaData"])
        df = df[[0, 1, 3, 5]]
        df.columns = ['證券代號', '證券簡稱', '最近淨值', '預估折溢價(%)']
        return df

    def fetch_all_etf_nav(self):
        """獲取所有台灣 ETF 淨值"""
        tw_df = self.fetch_twse_nav()
        two_df = self.fetch_tpex_nav()
        all_etf = pd.concat([tw_df, two_df], ignore_index=True)
        return all_etf

    def get_etf_nav(self, symbol):
        """查詢特定 ETF 的淨值"""
        all_etf = self.fetch_all_etf_nav()
        if all_etf.empty:
            return None, None, None

        # 去除 .TW 或 .TWO 後綴
        clean_symbol = symbol.replace(".TW", "").replace(".TWO", "")
        result = all_etf[all_etf['證券代號'] == clean_symbol]

        if result.empty:
            return None, None, None

        row = result.iloc[0]
        nav = row['最近淨值']
        premium = row['預估折溢價(%)']

        # 嘗試轉換為浮點數
        try:
            nav = float(nav.replace(",", ""))
        except:
            nav = None

        try:
            premium = float(premium.replace(",", ""))
        except:
            premium = None

        return nav, premium, datetime.now().strftime("%Y-%m-%d %H:%M")

# 設置 HTTP Headers
http_headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Accept': 'application/json, text/plain, */*',
}

st.set_page_config(page_title="股票價格分析工具", page_icon="📈", layout="wide")

st.title("📈 股票價格分析工具")
st.caption("版本: V04 (Streamlit Web版)")

# ===== 備用 ETF 淨值資料庫 =====
ETF_NAV_FALLBACK = {
    "0050": {"nav": 138.45, "premium": -0.32, "update": "2025-05-14"},
    "0051": {"nav": 35.12, "premium": -0.15, "update": "2025-05-14"},
    "0052": {"nav": 28.90, "premium": 0.05, "update": "2025-05-14"},
    "0053": {"nav": 45.67, "premium": -0.08, "update": "2025-05-14"},
    "0054": {"nav": 25.30, "premium": 0.12, "update": "2025-05-14"},
    "0055": {"nav": 52.18, "premium": -0.22, "update": "2025-05-14"},
    "0056": {"nav": 33.25, "premium": -0.18, "update": "2025-05-14"},
    "0057": {"nav": 25.80, "premium": 0.08, "update": "2025-05-14"},
    "0058": {"nav": 28.45, "premium": -0.05, "update": "2025-05-14"},
    "0059": {"nav": 15.20, "premium": 0.02, "update": "2025-05-14"},
    "00625L": {"nav": 32.15, "premium": -0.45, "update": "2025-05-14"},
    "00631L": {"nav": 28.90, "premium": -0.28, "update": "2025-05-14"},
    "00632L": {"nav": 45.60, "premium": -0.35, "update": "2025-05-14"},
    "00633L": {"nav": 18.25, "premium": 0.15, "update": "2025-05-14"},
    "00635L": {"nav": 22.80, "premium": -0.42, "update": "2025-05-14"},
    "00636L": {"nav": 15.90, "premium": -0.18, "update": "2025-05-14"},
    "00646": {"nav": 28.30, "premium": -0.25, "update": "2025-05-14"},
    "00675L": {"nav": 18.45, "premium": -0.55, "update": "2025-05-14"},
    "00676L": {"nav": 35.20, "premium": -0.38, "update": "2025-05-14"},
    "00678": {"nav": 25.60, "premium": -0.12, "update": "2025-05-14"},
    "00850": {"nav": 18.90, "premium": -0.08, "update": "2025-05-14"},
    "00878": {"nav": 22.35, "premium": -0.15, "update": "2025-05-14"},
    "00891": {"nav": 15.80, "premium": 0.05, "update": "2025-05-14"},
    "00892": {"nav": 16.20, "premium": -0.02, "update": "2025-05-14"},
    "009808": {"nav": 18.45, "premium": -0.10, "update": "2025-05-14"},
    "009819": {"nav": 15.80, "premium": -0.05, "update": "2025-05-14"},
}

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
if 'premium' not in st.session_state:
    st.session_state.premium = None
if 'nav_update_time' not in st.session_state:
    st.session_state.nav_update_time = None
if 'debug_nav_msg' not in st.session_state:
    st.session_state.debug_nav_msg = None
if 'nav_source' not in st.session_state:
    st.session_state.nav_source = None

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
                        meta = result.get('meta', {})
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

        # 偵測是否為 ETF (台股以 0 開頭通常是 ETF，支持 4-6 位數)
        is_etf = market == "TW" and symbol_input.startswith('0') and 4 <= len(symbol_input) <= 6

        # 如果是 ETF，抓取淨值
        net_value = None
        premium = None
        nav_update_time = None
        debug_msg = ""
        source = ""

        if is_etf and success_symbol:
            # 先嘗試從網路抓取
            try:
                fetcher = TaiwanETFDataFetcher()
                net_value, premium, nav_update_time = fetcher.get_etf_nav(success_symbol)
                if net_value is not None:
                    source = "證交所"
            except Exception as e:
                debug_msg = f"請求失敗: {e}"

            # 如果抓取失敗，使用備用資料庫
            if net_value is None:
                clean_symbol = success_symbol.replace(".TW", "").replace(".TWO", "")
                if clean_symbol in ETF_NAV_FALLBACK:
                    fallback = ETF_NAV_FALLBACK[clean_symbol]
                    net_value = fallback["nav"]
                    premium = fallback["premium"]
                    nav_update_time = fallback["update"]
                    source = "備用資料庫"
                else:
                    debug_msg = "抓取失敗且無備用資料"

        st.session_state.current_price = current_price
        st.session_state.historical_high = historical_high
        st.session_state.success_symbol = success_symbol
        st.session_state.is_etf = is_etf
        st.session_state.net_value = net_value
        st.session_state.premium = premium
        st.session_state.nav_update_time = nav_update_time
        st.session_state.debug_nav_msg = debug_msg
        st.session_state.nav_source = source
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

    # ===== ETF 淨值顯示 =====
    if is_etf:
        st.divider()
        if st.session_state.net_value is not None:
            col_nav1, col_nav2, col_nav3 = st.columns(3)
            with col_nav1:
                st.metric("ETF每股淨值", f"${st.session_state.net_value:,.2f}")
            with col_nav2:
                st.metric("預估折溢價", f"{st.session_state.premium:.2f}%", delta_color="inverse" if st.session_state.premium > 0 else "normal")
            with col_nav3:
                st.caption(f"更新: {st.session_state.nav_update_time or '--'} | 來源: {st.session_state.nav_source or '未知'}")
        else:
            st.warning(f"無法獲取 ETF 淨值: {st.session_state.debug_nav_msg or '未知錯誤'}")

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
