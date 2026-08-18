import os
import json
import numpy as np
import pandas as pd
import yfinance as yf
from datetime import datetime

# 追蹤標的清單
STOCK_STRATEGY = {
    # 核心權值 (台股)
    "2330.TW": {"name": "台積電", "category": "核心權值", "currency": "TWD"},
    "3008.TW": {"name": "大立光", "category": "核心權值", "currency": "TWD"},
    "2317.TW": {"name": "鴻海", "category": "核心權值", "currency": "TWD"},
    # 記憶體 / 電子零組件 (台股)
    "2408.TW": {"name": "南亞科", "category": "記憶體/電子零組件", "currency": "TWD"},
    "2337.TW": {"name": "旺宏", "category": "記憶體/電子零組件", "currency": "TWD"},
    "6770.TW": {"name": "力積電", "category": "記憶體/電子零組件", "currency": "TWD"},
    "8358.TWO": {"name": "金居", "category": "記憶體/電子零組件", "currency": "TWD"},
    "6213.TW": {"name": "聯茂", "category": "記憶體/電子零組件", "currency": "TWD"},
    "6290.TWO": {"name": "良維", "category": "記憶體/電子零組件", "currency": "TWD"},
    # 高股息 & 指數 ETF (台股)
    "0050.TW": {"name": "元大台灣50", "category": "高股息 & 指數 ETF", "currency": "TWD"},
    "0056.TW": {"name": "元大高股息", "category": "高股息 & 指數 ETF", "currency": "TWD"},
    "00919.TW": {"name": "群益台灣精選高息", "category": "高股息 & 指數 ETF", "currency": "TWD"},
    "00878.TW": {"name": "國泰永續高股息", "category": "高股息 & 指數 ETF", "currency": "TWD"},
    # 美股重點標的
    "NVDA": {"name": "NVIDIA (輝達)", "category": "美股重點標的", "currency": "USD"},
    "GOOGL": {"name": "Alphabet (Google)", "category": "美股重點標的", "currency": "USD"},
    "FCX": {"name": "Freeport-McMoRan (自由港)", "category": "美股重點標的", "currency": "USD"},
}

def clean_float(val, default=0.0):
    """安全轉換浮點數，防止 NaN 輸出至 JSON"""
    if pd.isna(val) or np.isnan(val) or np.isinf(val):
        return default
    return round(float(val), 2)

def fetch_and_calculate():
    output_data = {
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "stocks": {}
    }

    for ticker, meta in STOCK_STRATEGY.items():
        name = meta["name"]
        category = meta["category"]
        currency = meta["currency"]
        print(f"--> 正在抓取 {name} ({ticker})...")
        
        try:
            stock = yf.Ticker(ticker)
            df = stock.history(period="1y", auto_adjust=True)
            
            if df is None or df.empty:
                print(f"⚠️ {ticker} 無資料，跳過。")
                continue

            # 關鍵修復：剔除 Close 為空值或 NaN 的交易日（如未開盤的佔位列）
            df = df.dropna(subset=['Close'])
            if len(df) < 20:
                print(f"⚠️ {ticker} 有效資料不足 20 筆，跳過。")
                continue

            # 52 週高低價
            high_52w = clean_float(df['High'].max())
            low_52w = clean_float(df['Low'].min())

            # 滾動計算 20 日 MA 與 STD
            df['MA20'] = df['Close'].rolling(window=20).mean()
            df['STD20'] = df['Close'].rolling(window=20).std().fillna(0)
            
            # 動態河流上下軌
            df['Spread'] = np.maximum(df['STD20'] * 1.5, df['Close'] * 0.03)
            df['Upper_Band'] = df['MA20'] + df['Spread']
            df['Lower_Band'] = df['MA20'] - df['Spread']

            # 取最近約 22 筆有效交易日
            month_df = df.tail(22)
            labels = [idx.strftime("%m/%d") for idx in month_df.index]
            prices = [clean_float(p) for p in month_df['Close']]
            river_upper = [clean_float(u) for u in month_df['Upper_Band']]
            river_ma = [clean_float(m) for m in month_df['MA20']]
            river_lower = [clean_float(l) for l in month_df['Lower_Band']]

            # 最新一日有效數據
            latest_row = month_df.iloc[-1]
            current_price = clean_float(latest_row['Close'])
            dynamic_buy = clean_float(latest_row['Lower_Band'])
            dynamic_sell = clean_float(latest_row['Upper_Band'])
            ma20 = clean_float(latest_row['MA20'])

            # 狀態判定
            if current_price >= dynamic_sell:
                status = "高檔警戒 (達到脫手區)"
                status_color = "red"
            elif current_price <= dynamic_buy:
                status = "甜蜜買點 (超跌可分批)"
                status_color = "green"
            else:
                status = "河流震盪 (常態持有)"
                status_color = "blue"

            output_data["stocks"][ticker] = {
                "name": name,
                "category": category,
                "currency": currency,
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
            print(f"✅ {name} 成功！現價: {current_price} {currency}")
            
        except Exception as e:
            print(f"❌ 抓取 {ticker} 失敗: {e}")

    # 寫入 JSON
    with open("stock_data.json", "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)
    print(f"\n🎉 成功產出有效 JSON，共包含 {len(output_data['stocks'])} 檔標的！")

if __name__ == "__main__":
    fetch_and_calculate()
