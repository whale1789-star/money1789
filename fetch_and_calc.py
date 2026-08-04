import json
import sys
import pandas as pd
import yfinance as yf

# 追蹤標的清單 (價格改為由程式每日自動動態計算)
STOCKS = {
    "3008.TW": "大立光",
    "2317.TW": "鴻海",
    "2330.TW": "台積電",
    "0050.TW": "元大台灣50",
    "0056.TW": "元大高股息",
    "00919.TW": "群益台灣精選高息",
    "00878.TW": "國泰永續高股息",
}


def process_stock(ticker_symbol):
    df = pd.DataFrame()

    # 嘗試抓取 60 日 K 線數據
    try:
        ticker = yf.Ticker(ticker_symbol)
        df = ticker.history(period="60d", auto_adjust=False)
    except Exception as e:
        print(f"⚠️ {ticker_symbol} Ticker fetch failed: {e}")

    if df.empty or "Close" not in df.columns or len(df) < 20:
        try:
            df = yf.download(
                ticker_symbol, period="60d", auto_adjust=False, progress=False
            )
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
        except Exception as e:
            print(f"⚠️ {ticker_symbol} Download failed: {e}")

    if df.empty or "Close" not in df.columns or len(df) < 20:
        print(f"❌ {ticker_symbol} 資料不足 20 日，無法計算動態戰略價。")
        return None

    # 1. 計算 5 日平均高點與低點 (5D 通道)
    df["5D_Avg_High"] = df["High"].rolling(window=5).mean()
    df["5D_Avg_Low"] = df["Low"].rolling(window=5).mean()

    # 2. 動態計算戰略價格 (使用 20日均線 MA20 ± 1.5倍標準差)
    df["MA20"] = df["Close"].rolling(window=20).mean()
    df["STD20"] = df["Close"].rolling(window=20).std()

    # 最新一日的動態入手價與脫手價
    latest_ma = df["MA20"].iloc[-1]
    latest_std = df["STD20"].iloc[-1]

    # 高價股保留個位數小數，ETF保留兩位小數
    digits = 2 if "00" in ticker_symbol else 0
    dynamic_entry = round(latest_ma - 1.5 * latest_std, digits)
    dynamic_target = round(latest_ma + 1.5 * latest_std, digits)

    # 擷取最近 30 筆資料供前端繪圖
    df_clean = df.dropna(subset=["5D_Avg_High", "5D_Avg_Low"]).tail(30)

    return {
        "name": STOCKS.get(ticker_symbol, ticker_symbol),
        "dates": df_clean.index.strftime("%m/%d").tolist(),
        "close": [round(float(x), digits) for x in df_clean["Close"]],
        "avg_high": [round(float(x), digits) for x in df_clean["5D_Avg_High"]],
        "avg_low": [round(float(x), digits) for x in df_clean["5D_Avg_Low"]],
        "entry_price": dynamic_entry,
        "target_price": dynamic_target,
    }


def main():
    print("🚀 開始動態計算各標的之 5D 通道與戰略價格...")
    results = {}

    for symbol in STOCKS.keys():
        print(f"正在分析與計算: {symbol}...")
        data = process_stock(symbol)
        if data:
            results[symbol] = data
            print(
                f"✅ {data['name']} ({symbol}) -> 動態入手價: {data['entry_price']}, 動態脫手價: {data['target_price']}"
            )

    if not results:
        print("❌ 錯誤: 所有股票資料皆無法順利讀取！")
        sys.exit(1)

    output_payload = {
        "updated_at": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S"),
        "stocks": results,
    }

    with open("stock_data.json", "w", encoding="utf-8") as f:
        json.dump(output_payload, f, ensure_ascii=False, indent=2)

    print("🎉 stock_data.json 全數動態計算並更新完畢！")


if __name__ == "__main__":
    main()
