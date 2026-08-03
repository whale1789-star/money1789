import json
import sys
import pandas as pd
import yfinance as yf


def generate_channel_data(ticker_symbol="3008.TW"):
    print(f"正在抓取 {ticker_symbol} 歷史數據...")

    # 使用 Ticker.history 抓取，格式比 yf.download 更穩定
    ticker = yf.Ticker(ticker_symbol)
    df = ticker.history(period="60d")

    # 檢查是否抓到空的資料
    if df.empty or len(df) < 5:
        print(
            f"❌ 錯誤: 無法抓取到 {ticker_symbol} 數據！(可能受 Yahoo Finance"
            " 頻率限制)"
        )
        sys.exit(1)

    print(f"✅ 成功抓取 {len(df)} 筆交易日數據。")

    # 計算 5D 平均高點與 5D 平均低點
    df["5D_Avg_High"] = df["High"].rolling(window=5).mean()
    df["5D_Avg_Low"] = df["Low"].rolling(window=5).mean()

    # 擷取最近 30 個交易日
    df_recent = df.tail(30).copy()

    dates = df_recent.index.strftime("%m/%d").tolist()
    closes = [round(float(x), 2) for x in df_recent["Close"]]
    high_channel = [round(float(x), 2) for x in df_recent["5D_Avg_High"]]
    low_channel = [round(float(x), 2) for x in df_recent["5D_Avg_Low"]]

    output_data = {
        "stock": ticker_symbol,
        "updated_at": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S"),
        "dates": dates,
        "close": closes,
        "avg_high": high_channel,
        "avg_low": low_channel,
    }

    with open("stock_data.json", "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)

    print("✅ stock_data.json 檔案已成功生成與更新！")


if __name__ == "__main__":
    generate_channel_data("3008.TW")
