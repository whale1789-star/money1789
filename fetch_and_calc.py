import os
import json
import numpy as np
import pandas as pd
import yfinance as yf
from datetime import datetime

STOCK_STRATEGY = {
    # 台股核心權值
    "2330.TW": {"name": "台積電", "category": "台股核心權值", "currency": "TWD"},
    "2308.TW": {"name": "台達電", "category": "台股核心權值", "currency": "TWD"},
    "3008.TW": {"name": "大立光", "category": "台股核心權值", "currency": "TWD"},
    "2317.TW": {"name": "鴻海", "category": "台股核心權值", "currency": "TWD"},
    # 記憶體 / PCB / 電子零組件 / 矽晶圓 / 面板
    "6182.TWO": {"name": "合晶", "category": "記憶體/電子零組件", "currency": "TWD"},
    "3481.TW": {"name": "群創", "category": "記憶體/電子零組件", "currency": "TWD"},
    "2408.TW": {"name": "南亞科", "category": "記憶體/電子零組件", "currency": "TWD"},
    "2337.TW": {"name": "旺宏", "category": "記憶體/電子零組件", "currency": "TWD"},
    "6770.TW": {"name": "力積電", "category": "記憶體/電子零組件", "currency": "TWD"},
    "8358.TWO": {"name": "金居", "category": "記憶體/電子零組件", "currency": "TWD"},
    "6213.TW": {"name": "聯茂", "category": "記憶體/電子零組件", "currency": "TWD"},
    "6290.TWO": {"name": "良維", "category": "記憶體/電子零組件", "currency": "TWD"},
    # 高股息 & 指數 ETF
    "0050.TW": {"name": "元大台灣50", "category": "高股息 & 指數 ETF", "currency": "TWD"},
    "0056.TW": {"name": "元大高股息", "category": "高股息 & 指數 ETF", "currency": "TWD"},
    "00919.TW": {"name": "群益台灣精選高息", "category": "高股息 & 指數 ETF", "currency": "TWD"},
    "00878.TW": {"name": "國泰永續高股息", "category": "高股息 & 指數 ETF", "currency": "TWD"},
    # 美股焦點
    "NVDA": {"name": "輝達 (Nvidia)", "category": "美股焦點", "currency": "USD"},
    "GOOGL": {"name": "Alphabet (Google)", "category": "美股焦點", "currency": "USD"},
    "FCX": {"name": "自由港麥克莫蘭 (FCX)", "category": "美股焦點", "currency": "USD"},
}

def calculate_technical_indicators(df: pd.DataFrame) -> dict:
    """
    計算實戰三大動能指標：
    ① KD：不看高低點，只看鈍化 (連續3日 >=80 高檔鈍化 / <=20 低檔鈍化)
    ② RSI：看 50 多空分界線 (50以上做多，50以下不躁進)
    ③ MACD：先看柱狀體縮放動能，不等滯後交叉
    """
    # 1. RSI (14 日)
    delta = df['Close'].diff()
    gain = delta.where(delta > 0, 0.0).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0.0)).rolling(window=14).mean()
    rs = gain / (loss + 1e-9)
    rsi_series = 100 - (100 / (1 + rs))

    # 2. KD (9, 3, 3)
    low_min = df['Low'].rolling(window=9).min()
    high_max = df['High'].rolling(window=9).max()
    rsv = 100 * ((df['Close'] - low_min) / (high_max - low_min + 1e-9))
    
    k_vals, d_vals = [50.0], [50.0]
    for r in rsv.dropna():
        k = (2 / 3) * k_vals[-1] + (1 / 3) * r
        d = (2 / 3) * d_vals[-1] + (1 / 3) * k
        k_vals.append(k)
        d_vals.append(d)
        
    k_series = pd.Series(k_vals[1:], index=rsv.dropna().index)
    d_series = pd.Series(d_vals[1:], index=rsv.dropna().index)

    # 3. MACD (12, 26, 9)
    ema12 = df['Close'].ewm(span=12, adjust=False).mean()
    ema26 = df['Close'].ewm(span=26, adjust=False).mean()
    dif = ema12 - ema26
    macd_dea = dif.ewm(span=9, adjust=False).mean()
    hist_series = (dif - macd_dea) * 2  # 台灣看盤軟體慣用 2 倍放大

    # 取最新數據進行判定
    latest_k = round(float(k_series.iloc[-1]), 1)
    latest_d = round(float(d_series.iloc[-1]), 1)
    k_hist = [float(val) for val in k_series.tail(3)]

    # KD 鈍化判定
    if len(k_hist) >= 3 and all(val >= 80 for val in k_hist):
        kd_status = "高檔鈍化中：多方動能強勁，不急著賣出！"
    elif len(k_hist) >= 3 and all(val <= 20 for val in k_hist):
        kd_status = "低檔鈍化中：空方慣性仍在，切勿急著接刀！"
    elif latest_k >= 80:
        kd_status = "剛站上 80 高檔區：觀察能否連續鈍化延續漲勢"
    elif latest_k <= 20:
        kd_status = "跌破 20 低檔區：尚未止跌，等待真正轉強訊號"
    else:
        kd_status = "常態波動區間：不以高低檔為買賣依據，看趨勢順勢操作"

    # RSI 50 分界判定
    latest_rsi = round(float(rsi_series.iloc[-1]), 1)
    prev_rsi = round(float(rsi_series.iloc[-2]), 1)
    if latest_rsi >= 50:
        if latest_rsi >= prev_rsi:
            rsi_status = "站穩 50 且走揚：多方佔優勢，順勢偏多思考"
        else:
            rsi_status = "處於 50 多方水位但微幅下彎：留意短線回檔防守"
        if latest_rsi >= 70:
            rsi_status += "（若帶量上攻為強勢與過熱共存，不急著砍單）"
    else:
        if latest_rsi <= prev_rsi:
            rsi_status = "跌破 50 且一路往下：空方主導，保守應對不躁進"
        else:
            rsi_status = "50 之下尋求回勾：尚未突破多空分水嶺，保持觀察"

    # MACD 柱狀動能判定
    latest_hist = round(float(hist_series.iloc[-1]), 2)
    prev_hist = round(float(hist_series.iloc[-2]), 2)
    hist_diff = latest_hist - prev_hist

    if latest_hist >= 0:
        if hist_diff > 0:
            macd_status = "紅柱持續放大：多方動能正在增加，趨勢強勢延續"
        else:
            macd_status = "紅柱開始縮短：多方動能減弱，提早注意回檔風險"
    else:
        if hist_diff > 0:
            macd_status = "負值逐步向 0 靠近：綠柱縮短，空方壓力減輕，觀察轉強契機"
        else:
            macd_status = "綠柱持續放大：空方動能增強，下修壓力尚未減緩"

    return {
        "k": latest_k,
        "d": latest_d,
        "kd_status": kd_status,
        "rsi": latest_rsi,
        "rsi_status": rsi_status,
        "macd_hist": latest_hist,
        "macd_status": macd_status
    }

def fetch_and_calculate():
    output_data = {
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "stocks": {},
        "oversold_stocks": []
    }

    for ticker, meta in STOCK_STRATEGY.items():
        name = meta["name"]
        category = meta["category"]
        currency = meta.get("currency", "TWD")
        print(f"正在抓取 {name} ({ticker}) 的數據...")
        
        try:
            stock = yf.Ticker(ticker)
            df = stock.history(period="1y")
            df = df.dropna(subset=['Close'])
            
            if df.empty or len(df) < 35:
                print(f"⚠️ {ticker} 歷史資料不足，跳過。")
                continue

            # 計算進階指標 (KD, RSI, MACD)
            indicators = calculate_technical_indicators(df)

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

            df = df.dropna(subset=['MA20', 'Upper_Band', 'Lower_Band', 'Close'])

            # 取過去一個月（約 22 個有效交易日）
            month_df = df.tail(22)
            labels = [idx.strftime("%m/%d") for idx in month_df.index]
            prices = [round(float(p), 2) for p in month_df['Close']]
            river_upper = [float(u) for u in month_df['Upper_Band']]
            river_ma = [float(m) for m in month_df['MA20']]
            river_lower = [float(l) for l in month_df['Lower_Band']]

            latest_row = month_df.iloc[-1]
            current_price = round(float(latest_row['Close']), 2)
            dynamic_buy = float(latest_row['Lower_Band'])
            dynamic_sell = float(latest_row['Upper_Band'])
            ma20 = float(latest_row['MA20'])

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

            if is_oversold:
                bias = round(((current_price - ma20) / ma20) * 100, 2)
                discount = round(((dynamic_buy - current_price) / dynamic_buy) * 100, 2)
                output_data["oversold_stocks"].append({
                    "ticker": ticker,
                    "name": name,
                    "category": category,
                    "currency": currency,
                    "current_price": current_price,
                    "lower_band": dynamic_buy,
                    "bias": bias,
                    "discount": discount
                })

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
                "indicators": indicators,
                "chart_labels": labels,
                "chart_prices": prices,
                "river_upper": river_upper,
                "river_ma": river_ma,
                "river_lower": river_lower
            }
            print(f"✅ {name} ({ticker}) 計算完成：現價 {current_price} | 買點下軌 {dynamic_buy}")
            
        except Exception as e:
            print(f"❌ 抓取 {ticker} 失敗: {e}")

    with open("stock_data.json", "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)
    print("\n🎉 資料已清理並完成寫入 stock_data.json！")

if __name__ == "__main__":
    fetch_and_calculate()
