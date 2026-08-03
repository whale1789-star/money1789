import json
import sys
import pandas as pd
import yfinance as yf


def generate_channel_data(ticker_symbol="3008.TW"):
    print(f"正在抓取 {ticker_symbol} 歷史數據...")

    try:
        # 方法一：使用 Ticker 抓取
        ticker = yf.Ticker(ticker_symbol)
        df = ticker.history(period="60d")

        # 方法二：若方法一為空，切換為 yf.download 備案
        if df.empty or len(df) < 5:
            print("⚠️ 備用抓取模式...")
            df = yf.download(ticker_symbol, period="60d", progress=False)
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)

        if df.empty or len(df) < 5:
            raise ValueError(
                f"無法獲取 {ticker_symbol} 的數據，請確認 Yahoo Finance 服務正常。"
            )

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

        print("✅ stock_data.json 已成功生成！")

    except Exception as e:
        print(f"❌ 執行失敗！錯誤原因: {e}")
        sys.exit(1)


if __name__ == "__main__":
    generate_channel_data("3008.TW")
