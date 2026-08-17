import os
import json
import numpy as np
import pandas as pd
import yfinance as yf
from datetime import datetime

# 追蹤標的清單（涵蓋原 7 檔 + 新增 6 檔，包含上市 .TW 與上櫃 .TWO）
STOCK_STRATEGY = {
    "2330.TW": {"name": "台積電"},
    "3008.TW": {"name": "大立光"},
    "2317.TW": {"name": "鴻海"},
    "0050.TW": {"name": "元大台灣50"},
    "0056.TW": {"name": "元大高股息"},
    "00919.TW": {"name": "群益台灣精選高息"},
    "00878.TW": {"name": "國泰永續高股息"},
    # ➕ 新增 6 檔標的
    "2408.TW": {"name": "南亞科"},
    "2337.TW": {"name": "旺宏"},
    "6770.TW": {"name": "力積電"},
    "8358.TWO": {"name": "金居"},
    "6213.TW": {"name": "聯茂"},
    "6290.TWO": {"name": "良維"},
}

def fetch_and_calculate():
    output_data = {
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "stocks": {}
    }

    for ticker, meta in STOCK_STRATEGY.items():
        name = meta["name"]
        print(f"正在抓取 {name} ({ticker}) 的數據...")
        
        try:
            stock = yf.Ticker(ticker)
            # 抓取最近 60 天歷史資料以計算 20 日均線與標準差
            df = stock.history(period="60d")
            
            if df.empty or len(df) < 20:
                print(f"⚠️ {ticker} 歷史資料不足 20 日，跳過計算。")
                continue

            # 計算 20 日月線 (MA20) 與 20 日標準差 (Std20)
            df['MA20'] = df['Close'].rolling(window=20).mean()
            df['STD20'] = df['Close'].rolling(window=20).std()
            
            # 動態通道：以最新盤價之 MA20 ± 1.5 倍標準差作為動態入手價/脫手價
            latest_row = df.iloc[-1]
            current_price = round(float(latest_row['Close']), 2)
            ma20 = float(latest_row['MA20'])
            std20 = float(latest_row['STD20']) if not pd.isna(latest_row['STD20']) else 0.0
            
            # 動態推算（若波動太小則保留至少 3% 的通道區間）
            spread = max(std20 * 1.5, current_price * 0.03)
            dynamic_buy = round(ma20 - spread, 2)
            dynamic_sell = round(ma20 + spread, 2)
            
            # 取最近 5 筆交易日做 5 日走勢圖
            last_5 = df.tail(5)
            labels = [idx.strftime("%m/%d") for idx in last_5.index]
            prices = [round(float(p), 2) for p in last_5['Close']]
            
            # 判斷目前價格狀態 (區間高檔 / 甜蜜區間 / 破底超跌)
            if current_price >= dynamic_sell:
                status = "高檔警戒 (達到脫手區)"
                status_color = "red"
            elif current_price <= dynamic_buy:
                status = "甜蜜買點 (超跌可分批)"
                status_color = "green"
            else:
                status = "通道震盪 (觀望持有)"
                status_color = "blue"

            output_data["stocks"][ticker] = {
                "name": name,
                "current_price": current_price,
                "ma20": round(ma20, 2),
                "buy_price": dynamic_buy,
                "sell_price": dynamic_sell,
                "status": status,
                "status_color": status_color,
                "chart_labels": labels,
                "chart_prices": prices
            }
            print(f"✅ {name} 計算完成：現價 {current_price}, 入手價 {dynamic_buy}, 脫手價 {dynamic_sell}")
            
        except Exception as e:
            print(f"❌ 抓取 {ticker} 失敗: {e}")

    # 輸出為 JSON 檔
    with open("stock_data.json", "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)
    print("\n🎉 所有標的更新完成，已寫入 stock_data.json！")

if __name__ == "__main__":
    fetch_and_calculate()
