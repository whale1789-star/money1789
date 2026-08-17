import os
import json
import numpy as np
import pandas as pd
import yfinance as yf
from datetime import datetime

# 13 檔監控標的清單（涵蓋原 7 檔 + 新增 6 檔，包含上市 .TW 與上櫃 .TWO）
STOCK_STRATEGY = {
    "2330.TW": {"name": "台積電", "category": "核心權值"},
    "3008.TW": {"name": "大立光", "category": "核心權值"},
    "2317.TW": {"name": "鴻海", "category": "核心權值"},
    "2408.TW": {"name": "南亞科", "category": "記憶體/電子零組件"},
    "2337.TW": {"name": "旺宏", "category": "記憶體/電子零組件"},
    "6770.TW": {"name": "力積電", "category": "記憶體/電子零組件"},
    "8358.TWO": {"name": "金居", "category": "記憶體/電子零組件"},
    "6213.TW": {"name": "聯茂", "category": "記憶體/電子零組件"},
    "6290.TWO": {"name": "良維", "category": "記憶體/電子零組件"},
    "0050.TW": {"name": "元大台灣50", "category": "高股息 & 指數 ETF"},
    "0056.TW": {"name": "元大高股息", "category": "高股息 & 指數 ETF"},
    "00919.TW": {"name": "群益台灣精選高息", "category": "高股息 & 指數 ETF"},
    "00878.TW": {"name": "國泰永續高股息", "category": "高股息 & 指數 ETF"},
}

def fetch_and_calculate():
    output_data = {
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "stocks": {}
    }

    for ticker, meta in STOCK_STRATEGY.items():
        name = meta["name"]
        category = meta["category"]
        print(f"正在抓取 {name} ({ticker}) 的數據...")
        
        try:
            stock = yf.Ticker(ticker)
            # 抓取最近 1 年歷史資料以計算 52 週高低價與 20 日通道
            df = stock.history(period="1y")
            
            if df.empty or len(df) < 20:
                print(f"⚠️ {ticker} 歷史資料不足 20 日，跳過。")
                continue

            # 52 週（1年）歷史高低點
            high_52w = round(float(df['High'].max()), 2)
            low_52w = round(float(df['Low'].min()), 2)

            # 計算 20 日月線 (MA20) 與 20 日標準差 (Std20)
            df['MA20'] = df['Close'].rolling(window=20).mean()
            df['STD20'] = df['Close'].rolling(window=20).std()
            
            latest_row = df.iloc[-1]
            current_price = round(float(latest_row['Close']), 2)
            ma20 = float(latest_row['MA20'])
            std20 = float(latest_row['STD20']) if not pd.isna(latest_row['STD20']) else 0.0
            
            # 動態入手價 / 脫手價
            spread = max(std20 * 1.5, current_price * 0.03)
            dynamic_buy = round(ma20 - spread, 2)
            dynamic_sell = round(ma20 + spread, 2)
            
            # 取最近 5 筆交易日做走勢圖
            last_5 = df.tail(5)
            labels = [idx.strftime("%m/%d") for idx in last_5.index]
            prices = [round(float(p), 2) for p in last_5['Close']]
            
            # 狀態判定
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
                "category": category,
                "current_price": current_price,
                "ma20": round(ma20, 2),
                "buy_price": dynamic_buy,
                "sell_price": dynamic_sell,
                "high_52w": high_52w,
                "low_52w": low_52w,
                "status": status,
                "status_color": status_color,
                "chart_labels": labels,
                "chart_prices": prices
            }
            print(f"✅ {name} 完成：現價 {current_price} | 入手價 {dynamic_buy} | 脫手價 {dynamic_sell} | 52W高 {high_52w}")
            
        except Exception as e:
            print(f"❌ 抓取 {ticker} 失敗: {e}")

    # 輸出為 JSON
    with open("stock_data.json", "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)
    print("\n🎉 全數更新完成，已成功寫入 stock_data.json！")

if __name__ == "__main__":
    fetch_and_calculate()
