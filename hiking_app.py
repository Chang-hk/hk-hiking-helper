import os
import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta

st.set_page_config(page_title="香港長輩行山助手", page_icon="⛰️", layout="centered")

# 專為長輩手機閱讀設計：全局放大字體與按鈕高度
st.markdown("""
    <style>
    html, body, [class*="css"] { font-size: 20px !important; }
    h1 { font-size: 32px !important; }
    h2, h3 { font-size: 25px !important; }
    .stButton>button, .stLinkButton>a {
        font-size: 20px !important;
        padding: 12px 20px !important;
        width: 100%;
    }
    </style>
""", unsafe_allow_html=True)

st.title("⛰️ Captain VL 隊長行山路線與天氣助手")

# ==========================================
# 1. 串接香港天文台：即時警告 ＋ 九天天氣預報
# ==========================================
@st.cache_data(ttl=900)
def get_hko_data():
    domain = "https://" + "data." + "weather.gov.hk"
    try:
        w_url = f"{domain}/weatherAPI/opendata/weather.php?dataType=warnsum&lang=tc"
        warnings = requests.get(w_url, timeout=8).json()
        
        fnd_url = f"{domain}/weatherAPI/opendata/weather.php?dataType=fnd&lang=tc"
        nine_day = requests.get(fnd_url, timeout=8).json()
        return warnings, nine_day
    except Exception:
        return None, None

warnings, nine_day = get_hko_data()

if warnings:
    for code, info in warnings.items():
        st.error(f"⚠️ **現正生效警告：{info.get('name')}**（若今日出發請特別留意安全！）")

# --- 預計出發日期選擇器 ---
st.subheader("📅 查詢預計出發日天氣預報")
today = datetime.now().date()
max_date = today + timedelta(days=9)

selected_date = st.date_input(
    "請點選預計行山日期（提供未來 9 天天文台預報）：",
    value=today,
    min_value=today,
    max_value=max_date
)

target_date_str = selected_date.strftime("%Y%m%d")

matched_forecast = None
if nine_day and "weatherForecast" in nine_day:
    for day_info in nine_day["weatherForecast"]:
        if day_info.get("forecastDate") == target_date_str:
            matched_forecast = day_info
            break

if matched_forecast:
    week_day = matched_forecast.get("week", "")
    weather_desc = matched_forecast.get("forecastWeather", "")
    wind_desc = matched_forecast.get("forecastWind", "")
    min_temp = matched_forecast.get("forecastMintemp", {}).get("value", "")
    max_temp = matched_forecast.get("forecastMaxtemp", {}).get("value", "")
    min_rh = matched_forecast.get("forecastMinrh", {}).get("value", "")
    max_rh = matched_forecast.get("forecastMaxrh", {}).get("value", "")
    psr = matched_forecast.get("PSR", "")

    with st.container(border=True):
        st.markdown(f"### 🌤️ {selected_date.strftime('%Y年%m月%d日')}（{week_day}）天氣預報")
        
        c1, c2, c3 = st.columns(3)
        c1.metric("🌡️ 氣溫範圍", f"{min_temp}°C ~ {max_temp}°C")
        c2.metric("💧 相對濕度", f"{min_rh}% ~ {max_rh}%")
        c3.metric("☔ 降雨機率", psr)
        
        st.info(f"**天氣狀況：** {weather_desc}\n\n**風力情況：** {wind_desc}")
        
        if psr in ("中高", "高") or "雨" in weather_desc or "雷" in weather_desc:
            st.warning("🥾 **山友安全貼士：** 該日有較高機會下雨，山路可能濕滑，建議帶備雨具、穿防滑鞋或考慮改期。")
        elif isinstance(max_temp, (int, float)) and max_temp >= 30:
            st.warning("☀️ **山友安全貼士：** 該日天氣炎熱，請帶備充足飲用水與電解質飲品防中暑。")
        else:
            st.success("✨ **山友安全貼士：** 天氣不錯，非常適合相約山友一起出發！")
else:
    st.info("💡 天文台暫時只提供未來 9 天的詳細預報，請選擇 9 天內的日期查看。")

st.divider()

# ==========================================
# 2. 讀取隊長路線資料庫並提供關鍵字搜尋
# ==========================================
try:
    df = pd.read_csv("hiking_trails.csv")
    # 自動過濾：只保留在 gpx/ 資料夾裡有對應原版 .gpx 檔案的路線！
    def has_gpx(name):
        safe_name = str(name).strip().replace("/", "_").replace("\\", "_")
        return os.path.exists(f"gpx/{safe_name}.gpx")
    df = df[df["路線名稱"].apply(has_gpx)]
except FileNotFoundError:
    st.error("⚠️ 找不到路線資料庫 hiking_trails.csv")
    st.stop()

st.subheader("🔍 搜尋你想去的行山地點")
keyword = st.text_input("請輸入地點或關鍵字（例如：大東山、西貢、大嶼山、水塘）：", placeholder="留空則顯示全部推薦路線")

if keyword.strip():
    mask = (
        df["路線名稱"].str.contains(keyword.strip(), case=False, na=False) |
        df["地區關鍵字"].str.contains(keyword.strip(), case=False, na=False)
    )
    results = df[mask]
else:
    results = df
    # 確保即使舊資料沒有「發布日期」欄位也不會報錯
if "發布日期" not in results.columns:
    results["發布日期"] = "近期收錄"
results["發布日期"] = results["發布日期"].fillna("近期收錄")

sort_order = st.radio(
    "📅 路線排序方式：",
    ("🆕 最新發布排最前", "🕰️ 較早發布排最前"),
    horizontal=True
)

if sort_order == "🆕 最新發布排最前":
    # 若有日期則按日期由新到舊排，同時保留最新抓取順序
    results = results.sort_values(by="發布日期", ascending=False)
else:
    results = results.sort_values(by="發布日期", ascending=True)

st.write(f"📋 共找到 **{len(results)}** 條隊長推薦路線：")

# ==========================================
# 3. 逐條顯示大字體路線卡片與影片／GPX 按鈕
# ==========================================
for index, row in results.iterrows():
    with st.container(border=True):
        st.markdown(f"### 🥾 {row['路線名稱']}")
        st.caption(f"📅 影片發布日期：{row['發布日期']}")
        st.write(f"**難度：** {row['難度']} ｜ **預計時間：** {row['預計時間']}")
        st.write(f"**🚌 起步交通：** {row['起步交通']}")
        st.write(f"**💡 路線貼士：** {row['路線亮點與長輩貼士']}")

        col1, col2 = st.columns(2)
        with col1:
            st.link_button("▶️ 觀看隊長影片介紹", str(row["YouTuber介紹連結"]))
        with col2:
            gpx_path = f"gpx/{row['路線名稱']}.gpx"
            if os.path.exists(gpx_path):
                with open(gpx_path, "rb") as f:
                    st.download_button(
                        label="📥 下載 GPX（iPhone 專用）",
                        data=f,
                        file_name=f"{row['路線名稱']}.gpx",
                        mime="application/octet-stream",
                        key=f"gpx_{index}"
                    )
            else:
                st.link_button("🗺️ 搜尋路線圖", str(row["GPX下載連結"]))

st.divider()
with st.expander("📱 教學：點樣將下載嘅 GPX 放入「香港遠足路線」App？"):
    st.write("1. 點擊「📥 下載 GPX」後，按 Safari 右上角或左下角 **藍色向下箭嘴** ➔ 點選該 `.gpx` 檔案。")
    st.write("2. 打開檔案後，點擊右上角 **分享圖示（方格向上箭嘴）**。")
    st.write("3. 向左滑動 App 圖示，點選 **「香港遠足路線」** 即可自動匯入離線地圖！")
