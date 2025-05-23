import streamlit as st
import requests
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
import json

# Configuration
API_URL = "http://127.0.0.1:8000"  # Update this if your API runs on a different port

def fetch_metrics(metric=None, scid=None, limit=100):
    """Fetch metrics from the API"""
    params = {}
    if metric:
        params['metric'] = metric
    if scid:
        params['scid'] = scid
    params['limit'] = limit
    
    response = requests.get(f"{API_URL}/metrics", params=params)
    if response.status_code == 200:
        return response.json()
    else:
        st.error(f"Error fetching metrics: {response.text}")
        return []

def fetch_health():
    """Fetch API health status"""
    response = requests.get(f"{API_URL}/health")
    if response.status_code == 200:
        return response.json()
    else:
        st.error(f"Error fetching health status: {response.text}")
        return None

# Page config
st.set_page_config(
    page_title="ASTRA V2 Dashboard",
    page_icon="🚀",
    layout="wide"
)

# Title
st.title("🚀 ASTRA V2 Dashboard")
st.markdown("Monitor and analyze spacecraft metrics in real-time")

# Sidebar
st.sidebar.header("Filters")
metric_filter = st.sidebar.text_input("Filter by Metric Name")
scid_filter = st.sidebar.text_input("Filter by Spacecraft ID (SCID)")
limit = st.sidebar.slider("Number of Records", 10, 1000, 100)

# Health Status
st.sidebar.markdown("---")
st.sidebar.subheader("API Health Status")
health_data = fetch_health()
if health_data:
    st.sidebar.metric("Queue Size", health_data["queue_size"])
    st.sidebar.metric("Total Metrics", health_data["total_metrics"])
    st.sidebar.metric("Last Update", health_data["timestamp"])

# Fetch and display metrics
metrics = fetch_metrics(metric_filter, scid_filter, limit)

if metrics:
    # Convert to DataFrame
    df = pd.DataFrame(metrics)
    df['time'] = pd.to_datetime(df['time'])
    
    # Display raw data
    st.subheader("Raw Data")
    st.dataframe(df)
    
    # Time series plot
    st.subheader("Time Series Analysis")
    fig = px.line(df, 
                  x='time', 
                  y='value',
                  color='scid',
                  facet_col='metric',
                  title='Metric Values Over Time')
    st.plotly_chart(fig, use_container_width=True)
    
    # Threshold analysis
    st.subheader("Threshold Analysis")
    df['breach'] = df['value'] > df['threshold']
    breach_counts = df.groupby(['scid', 'metric'])['breach'].sum().reset_index()
    fig2 = px.bar(breach_counts, 
                  x='scid', 
                  y='breach',
                  color='metric',
                  title='Number of Threshold Breaches by Spacecraft and Metric')
    st.plotly_chart(fig2, use_container_width=True)
    
    # Statistics
    st.subheader("Statistics")
    stats = df.groupby(['scid', 'metric']).agg({
        'value': ['mean', 'std', 'min', 'max'],
        'breach': 'sum'
    }).round(2)
    st.dataframe(stats)
    
else:
    st.warning("No metrics found with the current filters")

# Footer
st.markdown("---")
st.markdown("ASTRA V2 Dashboard | Built with Streamlit") 