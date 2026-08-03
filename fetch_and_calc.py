import json
import sys
import pandas as pd
import yfinance as yf

# 設定每檔股票的建議入手價與脫手價目標
STOCK_STRATEGY = {
    "3008.TW": {"name": "大立光", "entry_price": 3875, "target_price": 4600},
    "2317.TW": {"name": "鴻海", "entry_price": 190, "target_price": 240},
    "2330.TW": {"name": "台積電", "entry_price": 930, "target_price": 1180},
    "0050.TW": {"name": "元大台灣50", "entry_price": 180, "target_price": 220},
    "0056.TW": {"name": "元大高股息", "entry_price": 36, "target_price": 42},
    "00919.TW": {"name": "群益台灣精選高息", "entry_price": 23, "target_price": 27},
    "00878.TW": {"name": "國泰永續高股息", "entry_price": 21, "target_price": 25},
}


def process_stock(ticker_symbol):
    strategy = STOCK_STRATEGY.get(
        ticker_symbol, {"entry_price": 0, "target_price": 0}
    )

    df = pd.DataFrame()

    # 嘗試方法 1: yf.Ticker
    try:
        ticker = yf.Ticker(ticker_symbol)
        df = ticker.history(period="60d", auto_adjust=False)
    except Exception as e:
        print(f"⚠️ {ticker_symbol} Ticker fetch failed: {e}")

    # 嘗試方法 2: yf.download (備援)
    if df.empty or "Close" not in df.columns or len(df) < 5:
        try:
            df = yf.download(
                ticker_symbol, period="60d", auto_adjust=False, progress=False
            )
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
        except Exception as e:
            print(f"⚠️ {ticker_symbol} Download failed: {e}")

    # 如果仍然抓不到數據，跳過此股票，避免整隻程式 Crash
    if df.empty or "Close" not in df.columns or len(df) < 5:
        print(f"❌ {ticker_symbol} 無法取得足夠 K 線資料，跳過處理。")
        return None

    # 計算 5D 平均高點與平均低點
    df["5D_Avg_High"] = df["High"].rolling(window=5).mean()
    df["5D_Avg_Low"] = df["Low"].rolling(window=5).mean()

    # 清理 NA 值並取最近 30 筆
    df_clean = df.dropna(subset=["5D_Avg_High", "5D_Avg_Low"]).tail(30)

    return {
        "dates": df_clean.index.strftime("%m/%d").tolist(),
        "close": [round(float(x), 2) for x in df_clean["Close"]],
        "avg_high": [round(float(x), 2) for x in df_clean["5D_Avg_High"]],
        "avg_low": [round(float(x), 2) for x in df_clean["5D_Avg_Low"]],
        "entry_price": strategy["entry_price"],
        "target_price": strategy["target_price"],
    }


def main():
    print("🚀 開始更新多股通道與戰略價格資料...")
    results = {}

    for symbol in STOCK_STRATEGY.keys():
        print(f"正在處理: {symbol}...")
        data = process_stock(symbol)
        if data:
            results[symbol] = data
            print(f"✅ {symbol} 成功處理")

    if not results:
        print("❌ 錯誤: 所有股票資料皆無法順利讀取！")
        sys.exit(1)

    output_payload = {
        "updated_at": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S"),
        "stocks": results,
    }

    with open("stock_data.json", "w", encoding="utf-8") as f:
        json.dump(output_payload, f, ensure_ascii=False, indent=2)

    print("🎉 stock_data.json 更新完畢！")


if __name__ == "__main__":
    main()
