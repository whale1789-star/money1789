import os
import json
import numpy as np
import pandas as pd
import yfinance as yf
from datetime import datetime

# 追蹤與掃描標的清單（涵蓋上市 .TW 與上櫃 .TWO，可持續擴充）
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
        "stocks": {},
        "oversold_stocks": []  # 儲存跌破河流下緣的推薦標的
    }

    for ticker, meta in STOCK_STRATEGY.items():
        name = meta["name"]
        category = meta["category"]
        print(f"正在抓取 {name} ({ticker}) 的數據...")
        
        try:
            stock = yf.Ticker(ticker)
            df = stock.history(period="1y")
            
            if df.empty or len(df) < 25:
                print(f"⚠️ {ticker} 歷史資料不足，跳過。")
                continue

            # 52 週歷史高低點
            high_52w = round(float(df['High'].max()), 2)
            low_52w = round(float(df['Low'].min()), 2)

            # 滾動計算 20 日月線 (MA20) 與標準差 (STD20)
            df['MA20'] = df['Close'].rolling(window=20).mean()
            df['STD20'] = df['Close'].rolling(window=20).std().fillna(0)
            
            # 動態河流上下軌：MA20 ± 1.5 倍標準差 (最低保留 3% 寬度防線)
            df['Spread'] = np.maximum(df['STD20'] * 1.5, df['Close'] * 0.03)
            df['Upper_Band'] = (df['MA20'] + df['Spread']).round(2)
            df['Lower_Band'] = (df['MA20'] - df['Spread']).round(2)
            df['MA20'] = df['MA20'].round(2)

            # 取過去一個月（約 22 個交易日）走勢數據
            month_df = df.tail(22)
            labels = [idx.strftime("%m/%d") for idx in month_df.index]
            prices = [round(float(p), 2) for p in month_df['Close']]
            river_upper = [float(u) for u in month_df['Upper_Band']]
            river_ma = [float(m) for m in month_df['MA20']]
            river_lower = [float(l) for l in month_df['Lower_Band']]

            # 最新一日數據
            latest_row = df.iloc[-1]
            current_price = round(float(latest_row['Close']), 2)
            dynamic_buy = float(latest_row['Lower_Band'])
            dynamic_sell = float(latest_row['Upper_Band'])
            ma20 = float(latest_row['MA20'])

            # 狀態判定與超跌掃描
            is_oversold = current_price <= dynamic_buy
            if current_price >= dynamic_sell:
                status = "高檔警戒 (達到脫手區)"
                status_color = "red"
            elif is_oversold:
                status = "甜蜜買點 (超跌可分批)"
                status_color = "green"
            else:
                status = "河流震盪 (常態持有)"
                status_color = "blue"

            # 若跌破或觸及河流下軌，加入推薦清單
            if is_oversold:
                bias = round(((current_price - ma20) / ma20) * 100, 2)
                discount = round(((dynamic_buy - current_price) / dynamic_buy) * 100, 2)
                output_data["oversold_stocks"].append({
                    "ticker": ticker,
                    "name": name,
                    "category": category,
                    "current_price": current_price,
                    "lower_band": dynamic_buy,
                    "bias": bias,
                    "discount": discount
                })

            output_data["stocks"][ticker] = {
                "name": name,
                "category": category,
                "current_price": current_price,
                "ma20": ma20,
                "buy_price": dynamic_buy,
                "sell_price": dynamic_sell,
                "high_52w": high_52w,
                "low_52w": low_52w,
                "status": status,
                "status_color": status_color,
                "chart_labels": labels,
                "chart_prices": prices,
                "river_upper": river_upper,
                "river_ma": river_ma,
                "river_lower": river_lower
            }
            print(f"✅ {name} 計算完成：現價 {current_price} | 下軌 {dynamic_buy} | 超跌狀態: {is_oversold}")
            
        except Exception as e:
            print(f"❌ 抓取 {ticker} 失敗: {e}")

    # 輸出至 JSON
    with open("stock_data.json", "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)
    print("\n🎉 全市場掃描與動態河流數據計算完成，已寫入 stock_data.json！")

if __name__ == "__main__":
    fetch_and_calculate()
