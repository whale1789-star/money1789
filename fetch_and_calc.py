import json
import pandas as pd
import yfinance as yf


def generate_channel_data(ticker_symbol="3008.TW"):
    # 抓取近 60 個交易日數據以確保均線計算完整
    df = yf.download(ticker_symbol, period="60d", interval="1d")

    # 處理 yfinance 多重索引問題
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    # 計算 5D 平均高點與 5D 平均低點 (使用 shift(1) 避開當日，計算前 5 日；若要包含當日則去掉 .shift(1))
    df['5D_Avg_High'] = df['High'].rolling(window=5).mean()
    df['5D_Avg_Low'] = df['Low'].rolling(window=5).mean()

    # 僅保留最近 30 個交易日呈現於圖表
    df_recent = df.tail(30).copy()

    dates = df_recent.index.strftime('%m/%d').tolist()
    closes = [round(float(x), 2) for x in df_recent['Close']]
    high_channel = [round(float(x), 2) for x in df_recent['5D_Avg_High']]
    low_channel = [round(float(x), 2) for x in df_recent['5D_Avg_Low']]

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

    print(f"✅ {ticker_symbol} 數據計算完成並已存入 stock_data.json")


if __name__ == "__main__":
    generate_channel_data("3008.TW")  # 預設為大立光，可更改為任意代碼如 2317.TW