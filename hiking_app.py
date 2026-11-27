import os
import requests
import pandas as pd
import streamlit as st

st.set_page_config(page_title="香港行山助手", page_icon="⛰️", layout="wide")

# 長輩友善超大字體與清晰按鈕樣式
st.markdown("""
<style>
html, body, [class*="css"] { font-size: 20px !important; }
h1 { font-size: 34px !important; color: #1B5E20 !important; }
h2 { font-size: 26px !important; color: #2E7D32 !important; }
h3 { font-size: 24px !important; }
.stButton>button, .stDownloadButton>button {
    font-size: 20px !important;
    padding: 12px 20px !important;
    border-radius: 10px !important;
    width: 100% !important;
}
</style>
""", unsafe_allow_html=True)

st.title("⛰️ 香港行山路線與未來九天天氣助手")
st.caption("資料來源：Captain VL 隊長郊遊頻道 ｜ 香港天文台官方天氣預報")

# --- 第一部分：香港未來九天天氣預報與出遊建議 ---
st.subheader("🌤️ 香港未來九天天氣與出遊建議")

@st.cache_data(ttl=1800)
def fetch_hk_9day_forecast():
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    # 1. 優先連線香港天文台官方 9 天預報接口
    try:
        hko_url = "https://www.weather.gov.hk"
        r = requests.get(hko_url, headers=headers, timeout=6)
        if r.status_code == 200 and r.text.strip():
            f_list = r.json().get("weatherForecast", [])
            if len(f_list) >= 9:
                result = []
                for d in f_list[:9]:
                    d_fmt = f"{d['forecastDate'][:4]}-{d['forecastDate'][4:6]}-{d['forecastDate'][6:8]}"
                    result.append({
                        "date": d_fmt,
                        "week": d["week"],
                        "min_c": d["forecastMintemp"]["value"],
                        "max_c": d["forecastMaxtemp"]["value"],
                        "desc": d["forecastWeather"],
                        "rain_prob": d.get("PSR", "低")
                    })
                return result
    except Exception:
        pass

    # 2. 雲端備援：Open-Meteo 抓取香港尖沙咀總部未來 9 天預報
    om_url = "https://open-meteo.com"
    om = requests.get(om_url, headers=headers, timeout=8).json().get("daily", {})
    weekdays_zh = ("星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日")
    times = om.get("time", [])
    probs = om.get("precipitation_probability_max", [])
    result = []
    for i, d_str in enumerate(times):
        dt = datetime.date.fromisoformat(d_str)
        code = om["weathercode"][i]
        prob = probs[i] if (i < len(probs) and probs[i] is not None) else 0
        if code in (0, 1): desc = "天晴乾燥，陽光充沛"
        elif code in (2, 3): desc = "大致多雲，間中有陽光"
        elif code in (45, 48): desc = "早晚有霧，能見度較低"
        elif code in (51, 53, 55, 61, 63, 65, 80, 81, 82): desc = "有驟雨，山路可能濕滑"
        else: desc = "有狂風雷暴及大雨"
        result.append({
            "date": d_str,
            "week": weekdays_zh[dt.weekday()],
            "min_c": round(om["temperature_2m_min"][i]),
            "max_c": round(om["temperature_2m_max"][i]),
            "desc": desc,
            "rain_prob": f"{prob}%"
        })
    return result

try:
    days_9 = fetch_hk_9day_forecast()
    if days_9:
        day_options = [f"{d['date']} ({d['week']})" for d in days_9]
        selected_label = st.selectbox("📅 請選擇打算行山的日期（未來九天）：", day_options, index=0)
        sel_idx = day_options.index(selected_label)
        sel_day = days_9[sel_idx]

        with st.container(border=True):
            c_weather, c_advice = st.columns([1.2, 1.3])
            with c_weather:
                st.markdown(f"### 🗓️ {sel_day['date']}（{sel_day['week']}）")
                st.write(f"🌡️ **氣溫預測：** {sel_day['min_c']}°C ～ {sel_day['max_c']}°C")
                st.write(f"☔ **降雨機率：** {sel_day['rain_prob']}")
                st.write(f"☁️ **天氣概況：** {sel_day['desc']}")

            with c_advice:
                desc_txt = sel_day["desc"]
                max_temp = int(sel_day["max_c"])
                if any(w in desc_txt for w in ("雷暴", "大雨", "狂風")):
                    st.error("🚫 **出遊建議：強烈不建議行山！**\n\n預測有雷暴或大雨，山區易有山洪及雷擊風險，請改期再出發。")
                elif any(w in desc_txt for w in ("雨", "濕滑")):
                    st.warning("⚠️ **出遊建議：不建議走崎嶇山路**\n\n預計有雨路滑，長輩若要外出建議改走市區平緩海濱或水塘石屎路，並帶備雨具及防滑鞋。")
                elif max_temp >= 32:
                    st.warning("🥵 **出遊建議：天氣酷熱，僅宜清晨短途**\n\n氣溫偏高易中暑，建議早上 8 點前出發並選擇有樹蔭路線，帶足 1.5 公升水。")
                elif "霧" in desc_txt:
                    st.warning("🌫️ **出遊建議：山區有霧，宜選熟悉大路**\n\n能見度較低，請避免前往無明顯路標的荒山野嶺。")
                else:
                    st.success("✅ **出遊建議：非常適合行山出遊！**\n\n天色穩定舒適，長輩可安心按體力挑選心水路線，記得帶備適量食水與防曬。")
except Exception as e:
    st.warning(f"天氣資料更新中，請稍後重新整理")

st.divider()

# --- 第二部分：搜尋與日期排序 ---
try:
    df = pd.read_csv("hiking_trails.csv")
except FileNotFoundError:
    st.error("⚠️ 找不到路線資料庫 hiking_trails.csv，請確認已上傳至 GitHub。")
    st.stop()

st.subheader("🔍 搜尋與排序香港行山路線")

if "發布日期" not in df.columns:
    df["發布日期"] = "近期收錄"
df["發布日期"] = df["發布日期"].fillna("近期收錄")
df["排序用日期"] = pd.to_datetime(df["發布日期"], errors="coerce")

col_search, col_sort = st.columns(2)
with col_search:
    keyword = st.text_input("輸入地點或山名：", placeholder="例如：大東山、西貢、水塘（留空顯示全部）")
with col_sort:
    sort_order = st.selectbox(
        "📅 排序方式：",
        ("🆕 最新發布排最前", "🕰️ 較早發布排最前"),
        index=0
    )

if keyword.strip():
    mask = (
        df["路線名稱"].str.contains(keyword.strip(), case=False, na=False) |
        df["地區關鍵字"].str.contains(keyword.strip(), case=False, na=False)
    )
    results = df[mask].copy()
else:
    results = df.copy()

is_asc = (sort_order == "🕰️ 較早發布排最前")
results = results.sort_values(by="排序用日期", ascending=is_asc, na_position="last")

st.write(f"📋 共顯示 **{len(results)}** 條香港行山路線：")

# --- 第三部分：路線卡片列表 ---
for index, row in results.iterrows():
    with st.container(border=True):
        col1, col2 = st.columns([3, 1])

        with col1:
            st.markdown(f"### 🥾 {row['路線名稱']}")
            st.caption(f"📅 影片發布日期：{row['發布日期']} ｜ 📍 地區：{row['地區關鍵字']}")
            st.write(f"**難度：** {row['難度']} ｜ **預計時間：** {row['預計時間']}")
            st.write(f"🚌 **起步交通：** {row['起步交通']}")
            st.write(f"💡 **路線貼士：** {row['路線亮點與長輩貼士']}")
            st.link_button("▶️ 觀看 Captain VL 隊長實地行山影片", str(row["YouTuber介紹連結"]))

        with col2:
            safe_name = str(row['路線名稱']).strip().replace("/", "_").replace("\\", "_")
            matched_gpx = None
            if os.path.exists("gpx"):
                for fname in os.listdir("gpx"):
                    if fname.lower() == f"{safe_name.lower()}.gpx":
                        matched_gpx = os.path.join("gpx", fname)
                        break

            if matched_gpx:
                st.success("✅ **隊長實走原版完整軌跡**")
                with open(matched_gpx, "rb") as f:
                    st.download_button(
                        label="📥 下載隊長原版 GPX（iPhone 專用）",
                        data=f,
                        file_name=f"{safe_name}.gpx",
                        mime="application/octet-stream",
                        key=f"gpx_{index}"
                    )
            else:
                st.info("ℹ️ **影片未提供 QR Code，已參考影片介紹自動生成 GPX 參考點**")
                lat, lon = "22.3193", "114.1694"
                try:
                    geo_url = f"https://openstreetmap.org{safe_name}+Hong+Kong&format=json&limit=1"
                    geo_res = requests.get(geo_url, headers={"User-Agent": "HKHikingHelper/1.0"}, timeout=2).json()
                    if geo_res:
                        lat, lon = geo_res[0]["lat"], geo_res[0]["lon"]
                except Exception:
                    pass

                fallback_gpx = f'''<?xml version="1.0" encoding="UTF-8"?>
<gpx version="1.1" creator="Captain VL Hiking Helper" xmlns="http://topografix.com">
  <metadata>
    <name>{safe_name}（參考路線）</name>
    <desc>{row['起步交通']}｜{row['路線亮點與長輩貼士']}</desc>
  </metadata>
  <wpt lat="{lat}" lon="{lon}">
    <name>{safe_name}（影片介紹參考地標）</name>
    <desc>起步交通：{row['起步交通']}｜貼士：{row['路線亮點與長輩貼士']}</desc>
  </wpt>
</gpx>'''
                st.download_button(
                    label="📥 下載參考介紹 GPX（iPhone 專用）",
                    data=fallback_gpx.encode("utf-8"),
                    file_name=f"{safe_name}_參考路線.gpx",
                    mime="application/octet-stream",
                    key=f"fb_gpx_{index}"
                )
