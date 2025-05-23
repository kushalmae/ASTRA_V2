import streamlit as st
import requests
import pandas as pd
from utils.config import config
from datetime import datetime, timedelta

# Configuration
API_URL = config["api_url"]

def fetch_data():
    """Fetch metrics from the API"""
    try:
        response = requests.get(f"{API_URL}/metrics", params={'limit': 300})
        return response.json() if response.status_code == 200 else []
    except Exception as e:
        st.error(f"Error: {str(e)}")
        return []

def get_stoplight_color(value, threshold):
    """Get stoplight color based on value and threshold"""
    if value <= threshold:
        return "🟢"  # Green
    elif value <= threshold * 1.1:  # Within 10% of threshold
        return "🟡"  # Yellow
    else:
        return "🔴"  # Red

def calculate_breaches(df, metric, scid):
    """Calculate number of breaches for a metric/SCID combination"""
    metric_data = df[(df['metric'] == metric) & (df['scid'] == scid)]
    breaches = metric_data[metric_data['value'] > metric_data['threshold']]
    return len(breaches)

def get_time_range(df):
    """Get the time range of the data"""
    if df.empty:
        return "No data"
    start_time = df['time'].min()
    end_time = df['time'].max()
    duration = end_time - start_time
    return f"{start_time.strftime('%Y-%m-%d %H:%M')} to {end_time.strftime('%Y-%m-%d %H:%M')} ({duration})"

# Page setup
st.set_page_config(page_title="ASTRA V2 - Stoplight", page_icon="🚦", layout="wide")
st.title("🚦 Stoplight Status")

# Fetch data
data = fetch_data()
if data:
    df = pd.DataFrame(data)
    df['time'] = pd.to_datetime(df['time'])
    
    # Display time range
    st.sidebar.header("Time Analysis")
    st.sidebar.write("Data Range:", get_time_range(df))
    
    # Get latest values for each metric and SCID
    latest_data = df.sort_values('time').groupby(['metric', 'scid']).last().reset_index()
    
    # Create columns for each metric
    metrics = sorted(latest_data['metric'].unique())
    cols = st.columns(len(metrics))
    
    for idx, metric in enumerate(metrics):
        with cols[idx]:
            st.subheader(metric)
            metric_data = latest_data[latest_data['metric'] == metric]
            
            for _, row in metric_data.iterrows():
                color = get_stoplight_color(row['value'], row['threshold'])
                breaches = calculate_breaches(df, row['metric'], row['scid'])
                
                st.metric(
                    f"{color} SCID {row['scid']}",
                    f"{row['value']:.2f}",
                    f"Threshold: {row['threshold']:.2f} | Breaches: {breaches}"
                )
else:
    st.error("No data available. Please check API connection.") 