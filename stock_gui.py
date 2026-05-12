import tkinter as tk
from tkinter import ttk, messagebox
import yfinance as yf
import threading
from datetime import datetime

class StockApp:
    def __init__(self, root):
        self.root = root
        self.root.title("股票價格分析工具")
        self.root.geometry("600x850")
        self.root.resizable(False, False)

        style = ttk.Style()
        style.configure("Title.TLabel", font=("Arial", 16, "bold"))
        style.configure("Header.TLabel", font=("Arial", 12, "bold"))
        style.configure("Result.TLabel", font=("Arial", 11))
        style.configure("Num.TButton", font=("Arial", 14, "bold"))

        main_frame = ttk.Frame(root, padding="15")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # ===== 0. 版本顯示 =====
        ttk.Label(main_frame, text="目前版本: V02", font=("Arial", 9, "bold"), foreground="gray").pack(pady=(0, 5))

        # ===== 1. 股票數據查詢 =====
        ttk.Label(main_frame, text="股票數據查詢", style="Title.TLabel").pack(pady=(0, 10))

        input_frame = ttk.Frame(main_frame)
        input_frame.pack(fill=tk.X, pady=5)

        ttk.Label(input_frame, text="市場:").pack(side=tk.LEFT, padx=5)

        self.market_var = tk.StringVar(value="TW")
        tw_btn = ttk.Radiobutton(input_frame, text="台灣", value="TW", variable=self.market_var)
        tw_btn.pack(side=tk.LEFT, padx=5)
        us_btn = ttk.Radiobutton(input_frame, text="美國", value="US", variable=self.market_var)
        us_btn.pack(side=tk.LEFT, padx=5)

        ttk.Label(input_frame, text="代號:").pack(side=tk.LEFT, padx=15)
        self.symbol_entry = ttk.Entry(input_frame, width=12, font=("Arial", 12))
        self.symbol_entry.insert(0, "2330")
        self.symbol_entry.pack(side=tk.LEFT, padx=5)

        self.search_btn = ttk.Button(input_frame, text="查詢", command=self.search_stock, width=10)
        self.search_btn.pack(side=tk.LEFT, padx=5)

        # 結果顯示區域
        self.result_frame = ttk.LabelFrame(main_frame, text="查詢結果", padding="10")
        self.result_frame.pack(fill=tk.X, pady=10)

        self.current_price_label = ttk.Label(self.result_frame, text="目前成交價: --", style="Result.TLabel")
        self.current_price_label.pack(anchor=tk.W, pady=2)

        self.high_price_label = ttk.Label(self.result_frame, text="歷史最高點: --", style="Result.TLabel")
        self.high_price_label.pack(anchor=tk.W, pady=2)

        # 新增：歷史最高點回撤百分比
        self.drawdown_label = ttk.Label(self.result_frame, text="距歷史最高點回撤: --", style="Result.TLabel")
        self.drawdown_label.pack(anchor=tk.W, pady=2)

        self.base_price_label = ttk.Label(self.result_frame, text="基準價 (P_base): --", style="Result.TLabel")
        self.base_price_label.pack(anchor=tk.W, pady=2)

        self.base_type_label = ttk.Label(self.result_frame, text="基準價類型: --", style="Result.TLabel")
        self.base_type_label.pack(anchor=tk.W, pady=2)

        # 新增：ETF淨值顯示
        self.net_value_label = ttk.Label(self.result_frame, text="ETF每股淨值: --", style="Result.TLabel")
        self.net_value_label.pack(anchor=tk.W, pady=2)

        # ===== 2. 自定義回撤計算 =====
        drawdown_calc_frame = ttk.LabelFrame(main_frame, text="自定義回撤計算", padding="10")
        drawdown_calc_frame.pack(fill=tk.X, pady=10)

        drawdown_input_frame = ttk.Frame(drawdown_calc_frame)
        drawdown_input_frame.pack(fill=tk.X, pady=5)

        ttk.Label(drawdown_input_frame, text="輸入回撤百分比 (1-99%):").pack(side=tk.LEFT, padx=5)
        self.drawdown_pct_entry = ttk.Entry(drawdown_input_frame, width=8, font=("Arial", 11))
        self.drawdown_pct_entry.insert(0, "20")
        self.drawdown_pct_entry.pack(side=tk.LEFT, padx=5)
        self.drawdown_pct_entry.bind("<KeyRelease>", self.on_drawdown_change)

        self.drawdown_price_label = ttk.Label(drawdown_calc_frame, text="對應價格: --", style="Result.TLabel")
        self.drawdown_price_label.pack(anchor=tk.W, pady=5)

        # ===== 3. 回撤加碼區間 =====
        ttk.Label(main_frame, text="回撤加碼區間計算", style="Header.TLabel").pack(pady=(10, 5))

        self.ladder_frame = ttk.Frame(main_frame)
        self.ladder_frame.pack(fill=tk.X, pady=5)

        self.ladder_labels = []
        percentages = [90, 80, 70, 60, 50, 40, 30, 20, 10]
        for i, pct in enumerate(percentages):
            lbl = ttk.Label(self.ladder_frame, text=f"{pct}%: --", width=15)
            lbl.grid(row=i//3, column=i%3, padx=5, pady=3, sticky=tk.W)
            self.ladder_labels.append((pct, lbl))

        # 狀態列
        self.status_label = ttk.Label(main_frame, text="就緒", foreground="gray")
        self.status_label.pack(pady=5)

        self.p_base = None
        self.historical_high = None
        self.current_price = None
        self.is_etf = False
        self.stock_symbol = None

    def check_is_etf(self, info):
        """自動檢查是否為ETF"""
        if not info:
            return False, None, None
        # 檢查多個可能的ETF標記欄位
        quote_type = info.get('quoteType', '').upper()
        type_disp = info.get('typeDisp', '').upper()
        legal_type = info.get('legalType', '').upper()
        nav_price = info.get('navPrice')
        nav_update_time = info.get('regularMarketTime')  # 使用市場時間作為參考

        is_etf = quote_type == 'ETF' or 'ETF' in type_disp or 'ETF' in legal_type
        return is_etf, nav_price, nav_update_time

    def on_drawdown_change(self, event=None):
        if self.historical_high is None:
            return
        try:
            pct = float(self.drawdown_pct_entry.get())
            if pct < 1:
                pct = 1
            elif pct > 99:
                pct = 99
            # 計算對應價格 = 歷史最高價 * (1 - 回撤%)
            price = self.historical_high * (1 - pct / 100)
            self.drawdown_price_label.config(text=f"對應價格: ${price:,.2f}")
        except ValueError:
            pass

    def search_stock(self):
        symbol = self.symbol_entry.get().strip()
        if not symbol:
            messagebox.showwarning("警告", "請輸入股票代號")
            return

        market = self.market_var.get()
        if market == "TW":
            symbols_to_try = [f"{symbol}.TW", f"{symbol}.TWO"]
        else:
            symbols_to_try = [symbol.upper()]

        self.search_btn.config(state=tk.DISABLED)
        self.status_label.config(text="正在查詢...")

        thread = threading.Thread(target=self._fetch_data, args=(symbols_to_try, market))
        thread.daemon = True
        thread.start()

    def _fetch_data(self, symbols_to_try, market):
        current_price = None
        historical_high = None
        success_symbol = None
        stock_info = None

        for symbol in symbols_to_try:
            try:
                stock = yf.Ticker(symbol)

                stock_info = stock.info
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
                    success_symbol = symbol
                    break

            except Exception:
                continue

        if current_price is None:
            self.root.after(0, lambda s=symbols_to_try[0]: self._show_error(
                f"無法獲取「{s}」的股票資料。\n\n"
                "請檢查代號是否正確，或嘗試切換市場（台灣/美國）。"
            ))
            return

        # 自動檢查是否為ETF
        is_etf, net_value, nav_time = self.check_is_etf(stock_info)

        if historical_high > current_price:
            p_base = historical_high
            base_type = "歷史最高點"
        else:
            p_base = current_price
            base_type = "目前成交價"

        self.root.after(0, self._update_ui, current_price, historical_high, p_base, base_type, success_symbol, is_etf, net_value, nav_time)

    def _update_ui(self, current, high, p_base, base_type, symbol=None, is_etf=False, net_value=None, nav_time=None):
        self.current_price_label.config(text=f"目前成交價: ${current:,.2f}")
        self.high_price_label.config(text=f"歷史最高點: ${high:,.2f}")

        # 計算回撤百分比
        if high > 0:
            drawdown_pct = ((high - current) / high) * 100
            self.drawdown_label.config(text=f"距歷史最高點回撤: {drawdown_pct:.2f}%")
        else:
            self.drawdown_label.config(text="距歷史最高點回撤: --")

        self.base_price_label.config(text=f"基準價 (P_base): ${p_base:,.2f}")
        self.base_type_label.config(text=f"基準價類型: {base_type}")

        # ETF淨值顯示 - 如果有 navPrice 就顯示，含更新時間
        if net_value:
            if nav_time:
                try:
                    update_time = datetime.fromtimestamp(nav_time)
                    time_str = update_time.strftime("%Y-%m-%d %H:%M")
                    self.net_value_label.config(text=f"ETF每股淨值: ${net_value:,.2f} (更新: {time_str})")
                except:
                    self.net_value_label.config(text=f"ETF每股淨值: ${net_value:,.2f}")
            else:
                self.net_value_label.config(text=f"ETF每股淨值: ${net_value:,.2f}")
        else:
            self.net_value_label.config(text="ETF每股淨值: --")

        # 更新實例變數
        self.p_base = p_base
        self.historical_high = high
        self.current_price = current
        self.is_etf = is_etf
        self.stock_symbol = symbol

        # 更新回撤加碼區間
        for pct, lbl in self.ladder_labels:
            price = p_base * (pct / 100)
            lbl.config(text=f"{pct}%: ${price:,.2f}")

        # 更新自定義回撤計算
        self.on_drawdown_change()

        self.search_btn.config(state=tk.NORMAL)
        if symbol:
            status_text = f"查詢成功: {symbol}"
            if is_etf:
                status_text += " (ETF)"
            self.status_label.config(text=status_text)
        else:
            self.status_label.config(text="查詢完成")

    def _show_error(self, msg):
        messagebox.showerror("錯誤", msg)
        self.search_btn.config(state=tk.NORMAL)
        self.status_label.config(text="查詢失敗")

if __name__ == "__main__":
    root = tk.Tk()
    app = StockApp(root)
    root.mainloop()