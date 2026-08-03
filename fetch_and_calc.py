import json
import sys
import pandas as pd
import yfinance as yf

# 設定每檔股票的建議入手價與脫手價目標
STOCK_STRATEGY = {
    "3008.TW": {"name": "大立光", "entry_price": 3875, "target_price": 4600},
    "2317.TW": {"name": "鴻海", "entry_price": 190, "target_price": 240},
    "2330.TW": {"name": "台積電", "entry_price": 930, "target_price": 1180},
}


def process_stock(ticker_symbol):
    strategy = STOCK_STRATEGY.get(
        ticker_symbol, {"entry_price": 0, "target_price": 0}
    )

    ticker = yf.Ticker(ticker_symbol)
    df = ticker.history(period="60d")

    if df.empty or len(df) < 5:
        df = yf.download(ticker_symbol, period="60d", progress=False)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

    if df.empty or len(df) < 5:
        return None

    # 計算 5D 平均高點與平均低點
    df["5D_Avg_High"] = df["High"].rolling(window=5).mean()
    df["5D_Avg_Low"] = df["Low"].rolling(window=5).mean()

    df_recent = df.tail(30).copy()

    return {
        "dates": df_recent.index.strftime("%m/%d").tolist(),
        "close": [round(float(x), 2) for x in df_recent["Close"]],
        "avg_high": [round(float(x), 2) for x in df_recent["5D_Avg_High"]],
        "avg_low": [round(float(x), 2) for x in df_recent["5D_Avg_Low"]],
        "entry_price": strategy["entry_price"],
        "target_price": strategy["target_price"],
    }


def main():
    print("🚀 開始更新多股通道與戰略價格資料...")
    results = {}

    for symbol in STOCK_STRATEGY.keys():
        try:
            data = process_stock(symbol)
            if data:
                results[symbol] = data
                print(f"✅ {symbol} 資料更新成功")
        except Exception as e:
            print(f"⚠️ {symbol} 更新失敗: {e}")

    output_payload = {
        "updated_at": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S"),
        "stocks": results,
    }

    with open("stock_data.json", "w", encoding="utf-8") as f:
        json.dump(output_payload, f, ensure_ascii=False, indent=2)

    print("🎉 stock_data.json 全數更新完成！")


if __name__ == "__main__":
    main()
