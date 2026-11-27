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

# --- 第一部分：香港未來九天天氣預報（全球 CDN 穩定接口 ＋ 天文台官方連結） ---
st.subheader("🌤️ 香港未來天氣預報")

@st.cache_data(ttl=1800)
def get_hk_weather_cdn():
    # 使用全球 CDN 節點氣象接口，不受雲端機房 IP 限制
    url = "https://wttr.in"
    res = requests.get(url, headers={"User-Agent": "curl/7.81.0"}, timeout=10)
    return res.json().get("weather", [])

weekdays_zh = ("週一", "週二", "週三", "週四", "週五", "週六", "週日")

try:
    w_days = get_hk_weather_cdn()
    if w_days:
        cols = st.columns(len(w_days))
        for i, day in enumerate(w_days):
            d_str = day["date"]
            dt = datetime.date.fromisoformat(d_str)
            w_day = weekdays_zh[dt.weekday()]
            min_c = day["mintempC"]
            max_c = day["maxtempC"]
            # 取中午時段的天氣描述
            hourly = day.get("hourly", [{}])
            mid_slot = hourly[len(hourly)//2] if hourly else {}
            desc_en = mid_slot.get("weatherDesc", [{}]).get("value", "").lower()
            
            if "rain" in desc_en or "shower" in desc_en or "drizzle" in desc_en:
                desc_zh = "🌧️ 有雨路滑小心"
            elif "thunder" in desc_en:
                desc_zh = "⛈️ 雷暴不宜行山"
            elif "fog" in desc_en or "mist" in desc_en:
                desc_zh = "🌫️ 有霧能見度低"
            elif "cloud" in desc_en or "overcast" in desc_en:
                desc_zh = "⛅ 多雲間晴"
            else:
                desc_zh = "☀️ 天晴乾燥"

            with cols[i]:
                with st.container(border=True):
                    st.markdown(f"**{d_str[5:].replace('-', '/')} ({w_day})**")
                    st.write(f"🌡️ {min_c}°C - {max_c}°C")
                    st.caption(desc_zh)
except Exception:
    pass

st.link_button("🔭 查看香港天文台官方「九天天氣預報」完整圖表", "https://www.hko.gov.hk")
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
