import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
from database import init_db, get_latest_reading, get_history

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Missoula Air Quality",
    page_icon="🌬️",
    layout="wide"
)

init_db()

# ── AQI colour helpers ────────────────────────────────────────────────────────
def aqi_color(aqi):
    if aqi is None:
        return "#cccccc"
    if aqi <= 50:   return "#00e400"   # Good
    if aqi <= 100:  return "#ffff00"   # Moderate
    if aqi <= 150:  return "#ff7e00"   # Unhealthy for Sensitive Groups
    if aqi <= 200:  return "#ff0000"   # Unhealthy
    if aqi <= 300:  return "#8f3f97"   # Very Unhealthy
    return "#7e0023"                   # Hazardous

def aqi_label(aqi):
    if aqi is None:        return "No Data"
    if aqi <= 50:          return "Good"
    if aqi <= 100:         return "Moderate"
    if aqi <= 150:         return "Unhealthy for Sensitive Groups"
    if aqi <= 200:         return "Unhealthy"
    if aqi <= 300:         return "Very Unhealthy"
    return "Hazardous"

# ── Header ────────────────────────────────────────────────────────────────────
st.title("🌬️ Missoula, MT — Air Quality Monitor")
st.caption(f"Data sourced from AirNow (EPA) · Last refreshed: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")

st.divider()

# ── Current reading ───────────────────────────────────────────────────────────
latest = get_latest_reading()

if latest:
    aqi_val   = latest["aqi"]
    color     = aqi_color(aqi_val)
    label     = aqi_label(aqi_val)
    timestamp = latest["timestamp"]
    pollutant = latest["pollutant"]

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown(f"""
        <div style='background:{color};padding:24px;border-radius:12px;text-align:center;'>
            <h1 style='color:#000;margin:0;font-size:64px;'>{aqi_val}</h1>
            <p style='color:#000;margin:4px 0 0;font-size:18px;font-weight:bold;'>AQI</p>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.metric("Status",    label)
        st.metric("Pollutant", pollutant)

    with col3:
        st.metric("Location",      latest["location"])
        st.metric("Last Reading",  timestamp[:16].replace("T", " ") + " UTC")

else:
    st.warning("No data yet. The poller hasn't run, or no readings are available.")

st.divider()

# ── Historical chart ──────────────────────────────────────────────────────────
st.subheader("📈 AQI History (last 30 days)")

# Pull 30 days of data so weekly averages and unhealthy day counts are meaningful
history = get_history(hours=720)

if history:
    df = pd.DataFrame(history)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = df.sort_values("timestamp")

    # One line per pollutant
    fig = go.Figure()
    for pollutant in df["pollutant"].unique():
        subset = df[df["pollutant"] == pollutant]
        fig.add_trace(go.Scatter(
            x=subset["timestamp"],
            y=subset["aqi"],
            mode="lines+markers",
            name=pollutant,
            line=dict(width=2),
            marker=dict(size=5)
        ))

    # AQI threshold bands
    bands = [
        (0,   50,  "#00e400", "Good"),
        (51,  100, "#ffff00", "Moderate"),
        (101, 150, "#ff7e00", "USG"),
        (151, 200, "#ff0000", "Unhealthy"),
    ]
    for low, high, color, name in bands:
        fig.add_hrect(y0=low, y1=high, fillcolor=color, opacity=0.07,
                      line_width=0, annotation_text=name,
                      annotation_position="right")

    fig.update_layout(
        xaxis_title="Time (UTC)",
        yaxis_title="AQI",
        legend_title="Pollutant",
        height=420,
        margin=dict(l=20, r=20, t=20, b=20),
        plot_bgcolor="#0e1117",
        paper_bgcolor="#0e1117",
        font_color="#fafafa",
        xaxis=dict(gridcolor="#2a2a2a"),
        yaxis=dict(gridcolor="#2a2a2a"),
    )
    st.plotly_chart(fig, use_container_width=True)

    # Raw data expander
    with st.expander("View raw data"):
        st.dataframe(
            df[["timestamp","pollutant","aqi","category","location"]].sort_values("timestamp", ascending=False),
            use_container_width=True,
            hide_index=True
        )
else:
    st.info("Not enough data yet for a historical chart. Check back after the poller has run a few times.")

st.divider()

# ── Weekly averages ───────────────────────────────────────────────────────────
st.subheader("📅 Weekly AQI Averages")

weekly_history = get_history(hours=720)
if weekly_history:
    wdf = pd.DataFrame(weekly_history)
    wdf["timestamp"] = pd.to_datetime(wdf["timestamp"])
    wdf["week"] = wdf["timestamp"].dt.to_period("W").apply(lambda r: str(r.start_time.date()))

    weekly_avg = (
        wdf.groupby(["week", "pollutant"])["aqi"]
        .mean()
        .round(1)
        .reset_index()
        .rename(columns={"aqi": "avg_aqi", "week": "Week Starting"})
    )

    fig2 = go.Figure()
    for pollutant in weekly_avg["pollutant"].unique():
        subset = weekly_avg[weekly_avg["pollutant"] == pollutant]
        fig2.add_trace(go.Bar(
            x=subset["Week Starting"],
            y=subset["avg_aqi"],
            name=pollutant,
        ))

    fig2.update_layout(
        xaxis_title="Week",
        yaxis_title="Average AQI",
        barmode="group",
        height=320,
        margin=dict(l=20, r=20, t=20, b=20),
        plot_bgcolor="#0e1117",
        paper_bgcolor="#0e1117",
        font_color="#fafafa",
        xaxis=dict(gridcolor="#2a2a2a"),
        yaxis=dict(gridcolor="#2a2a2a"),
    )
    st.plotly_chart(fig2, use_container_width=True)
else:
    st.info("Not enough data yet for weekly averages.")

st.divider()

# ── Days above Unhealthy ──────────────────────────────────────────────────────
st.subheader("🚨 Days Above 'Unhealthy' (AQI > 150)")

if weekly_history:
    udf = pd.DataFrame(weekly_history)
    udf["timestamp"] = pd.to_datetime(udf["timestamp"])
    udf["date"] = udf["timestamp"].dt.date

    # A day counts if ANY reading that day exceeded 150
    unhealthy_days = (
        udf.groupby("date")["aqi"]
        .max()
        .reset_index()
    )
    days_over = (unhealthy_days["aqi"] > 150).sum()
    total_days = unhealthy_days["date"].nunique()

    col1, col2 = st.columns(2)
    with col1:
        color = "#ff0000" if days_over > 0 else "#00e400"
        st.markdown(f"""
        <div style='background:{color};padding:20px;border-radius:12px;text-align:center;'>
            <h1 style='color:#000;margin:0;font-size:56px;'>{days_over}</h1>
            <p style='color:#000;margin:4px 0 0;font-size:16px;font-weight:bold;'>
                Unhealthy Days (last 30 days)
            </p>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        pct = round((days_over / total_days * 100), 1) if total_days > 0 else 0
        st.metric("Total days tracked", total_days)
        st.metric("% of days unhealthy", f"{pct}%")

    # Show which specific dates were unhealthy
    bad_days = unhealthy_days[unhealthy_days["aqi"] > 150].sort_values("date", ascending=False)
    if not bad_days.empty:
        with st.expander(f"View {len(bad_days)} unhealthy day(s)"):
            st.dataframe(bad_days.rename(columns={"date": "Date", "aqi": "Peak AQI"}),
                         use_container_width=True, hide_index=True)
else:
    st.info("Not enough data yet to count unhealthy days.")

# ── Footer ────────────────────────────────────────────────────────────────────
st.divider()
st.caption("Built with Streamlit · AirNow EPA API · Jetstream2")
