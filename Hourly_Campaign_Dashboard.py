import streamlit as st
import pandas as pd
import altair as alt

# ---- PAGE CONFIG ---- #
st.set_page_config(page_title="Campaign Hourly Performance", layout="wide")

# ---- HEADER ---- #
st.title("📊 Campaign Hourly Performance Dashboard")
st.markdown("""
This dashboard helps you analyze how your marketing campaign metrics change **hour by hour**. 

✅ Select one or more **metrics**, **campaigns**, and **dates** to compare.  
✅ See both **combined hourly trends** and **per-campaign level breakdown**.  
✅ Metrics like Spend, CTR, ROAS, etc., are explained in plain English.
""")

# ---- INPUT FILE ---- #
excel_url = "https://research.buywclothes.com/Ads_Automation_Reports/Amazon/spend_master.csv"
uploaded_file = st.file_uploader("Or upload CSV file", type=["csv"])

if uploaded_file:
    df = pd.read_csv(uploaded_file, parse_dates=['timestamp'])
else:
    df = pd.read_csv(excel_url, parse_dates=['timestamp'])

# ---- TIME FEATURES ---- #
df['timestamp'] = pd.to_datetime(df['timestamp'])
df['date'] = df['timestamp'].dt.date
df['hour_index'] = df['timestamp'].dt.hour

# ---- METRIC DESCRIPTIONS ---- #
metric_descriptions = {
    "Spend": "How much money was spent on ads.",
    "Impressions": "How many times the ad was shown.",
    "Clicks": "How many people clicked the ad.",
    "CTR": "Click-through rate: percentage of impressions that got clicks.",
    "Orders": "How many orders were placed.",
    "Sales": "Total revenue generated.",
    "ACOS": "Ad Cost of Sale (lower is better).",
    "ROAS": "Return on Ad Spend (higher is better).",
    "CPC": "Average Cost per Click.",
    "NTB orders": "New-to-brand customer orders.",
    "vCTR": "Video Click-through Rate"
}

available_metrics = [m for m in metric_descriptions if m in df.columns]
campaign_column = [col for col in df.columns if 'campaign' in col.lower()][0]

# ---- SIDEBAR FILTERS ---- #
st.sidebar.header("🔎 Filters")
selected_campaigns = st.sidebar.multiselect("Select Campaigns", sorted(df[campaign_column].unique()), default=sorted(df[campaign_column].unique()))
selected_dates = st.sidebar.multiselect("Select Dates", sorted(df['date'].unique()), default=sorted(df['date'].unique()))
selected_metrics = st.sidebar.multiselect("Select Metrics", available_metrics, default=["Spend"])

# ---- FILTERED DATA ---- #
df_filtered = df[
    (df[campaign_column].isin(selected_campaigns)) &
    (df['date'].isin(selected_dates))
].copy()

# ---- BUDGET CALCULATIONS ---- #
if 'Spend' in df.columns and 'Budget' in df.columns:
    df_filtered['cumulative_spend'] = df_filtered.groupby([campaign_column, 'date'])['Spend'].cumsum()
    df_filtered['budget_left'] = df_filtered['Budget'] - df_filtered['cumulative_spend']

# ---- COMBINED HOURLY TREND ---- #
st.subheader("🧮 Combined Hourly Trend (All Campaigns)")
combined_hourly = df_filtered.groupby(['date', 'hour_index'])[selected_metrics].sum().reset_index()
combined_hourly['date'] = combined_hourly['date'].astype(str)
combined_hourly = combined_hourly.sort_values(by=['date', 'hour_index'])

for metric in selected_metrics:
    combined_hourly[f"{metric}_delta"] = combined_hourly.groupby('date')[metric].diff()
    combined_hourly[f"{metric}_delta"] = combined_hourly[f"{metric}_delta"].fillna(combined_hourly[metric])

    chart = alt.Chart(combined_hourly).mark_line(point=True).encode(
        x='hour_index:O',
        y=alt.Y(f"{metric}_delta:Q", title=f"Hourly Change in {metric}"),
        color='date:N',
        tooltip=['date', 'hour_index', f"{metric}_delta"]
    ).properties(title=f"Hourly Change in {metric} (All Campaigns)", height=300)
    st.altair_chart(chart, use_container_width=True)

# ---- CAMPAIGN LEVEL ANALYSIS ---- #
st.subheader("📌 Campaign-Level Metric Changes")
for metric in selected_metrics:
    df_grouped = (
        df_filtered
        .groupby([campaign_column, 'date', 'hour_index'])[metric]
        .sum()
        .reset_index()
    )

    df_grouped = df_grouped.sort_values(by=[campaign_column, 'date', 'hour_index'])
    df_grouped['Delta'] = df_grouped.groupby([campaign_column, 'date'])[metric].diff()
    df_grouped['Delta'] = df_grouped['Delta'].fillna(df_grouped[metric])

    df_grouped['date'] = df_grouped['date'].astype(str)
    df_grouped['camp_date'] = df_grouped[campaign_column] + " | " + df_grouped['date']

    chart = (
        alt.Chart(df_grouped)
        .mark_line(point=True)
        .encode(
            x='hour_index:O',
            y=alt.Y('Delta:Q', title=f"Hourly Change in {metric}"),
            color=alt.Color('camp_date:N', legend=alt.Legend(title="Campaign | Date")),
            tooltip=[campaign_column, 'date', 'hour_index', 'Delta']
        )
        .properties(title=f"Hourly Change in {metric} by Campaign & Date", height=300)
    )
    st.altair_chart(chart, use_container_width=True)

# ---- SUMMARY TABLES ---- #
st.subheader("📋 Summary Tables")
col1, col2 = st.columns(2)

with col1:
    st.markdown("**Combined Hourly Metrics (All Campaigns)**")
    st.dataframe(combined_hourly)

with col2:
    st.markdown("**Hourly Delta by Campaign**")
    delta_table = df_filtered.groupby([campaign_column, 'date', 'hour_index'])[selected_metrics].sum().reset_index()
    delta_table = delta_table.sort_values(by=[campaign_column, 'date', 'hour_index'])

    for metric in selected_metrics:
        delta_table[f"{metric} Δ"] = delta_table.groupby([campaign_column, 'date'])[metric].diff()
        delta_table[f"{metric} Δ"] = delta_table[f"{metric} Δ"].fillna(delta_table[metric])

    delta_columns = [campaign_column, 'date', 'hour_index'] + [f"{m} Δ" for m in selected_metrics]
    st.dataframe(delta_table[delta_columns])

# ---- BUDGET LEFT GRAPH ---- #
if 'budget_left' in df_filtered.columns:
    st.subheader("💰 Budget Left Over Time")

    df_filtered['date'] = df_filtered['date'].astype(str)
    df_filtered['camp_date'] = df_filtered[campaign_column] + " | " + df_filtered['date']

    chart = (
        alt.Chart(df_filtered)
        .mark_line(point=True)
        .encode(
            x='hour_index:O',
            y=alt.Y('budget_left:Q', title='Budget Left'),
            color=alt.Color('camp_date:N', legend=alt.Legend(title="Campaign | Date")),
            tooltip=[campaign_column, 'date', 'hour_index', 'budget_left']
        )
        .properties(title="Remaining Budget by Campaign & Date", height=300)
    )
    st.altair_chart(chart, use_container_width=True)

    st.markdown("**📋 Campaign Budget Summary**")
    budget_table = (
        df_filtered
        .groupby([campaign_column, 'date', 'hour_index'])
        .agg({
            'Budget': 'max',
            'cumulative_spend': 'max',
            'budget_left': 'min'
        })
        .reset_index()
    )
    st.dataframe(budget_table)

# ---- METRIC GUIDE ---- #
st.sidebar.markdown("---")
st.sidebar.subheader("ℹ️ Metric Descriptions")
for m in selected_metrics:
    st.sidebar.markdown(f"**{m}**: {metric_descriptions.get(m, 'No description')} ")
