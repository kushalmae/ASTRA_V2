import streamlit as st
import requests
import pandas as pd
import plotly.express as px
from datetime import datetime
import os
import sys

# Add parent directory to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.config import config

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

# Page setup
st.set_page_config(page_title="ASTRA V2 - Main", page_icon="🚀", layout="wide")
st.title("🚀 ASTRA V2 - Main Dashboard")

# Fetch data
data = fetch_data()
if data:
    df = pd.DataFrame(data)
    df['time'] = pd.to_datetime(df['time'])
    
    # Sidebar filters
    metrics = sorted(df['metric'].unique())
    scids = sorted(df['scid'].unique())
    
    selected_metric = st.sidebar.selectbox("Metric", metrics)
    selected_scid = st.sidebar.selectbox("Spacecraft ID", scids)
    
    # Filter data
    filtered_df = df[
        (df['metric'] == selected_metric) & 
        (df['scid'] == selected_scid)
    ]
    
    # Main plot
    fig = px.line(filtered_df, 
                  x='time', 
                  y='value',
                  title=f'{selected_metric} for SCID {selected_scid}')
    
    # Add threshold line
    fig.add_hline(y=filtered_df['threshold'].iloc[0], 
                  line_dash="dash", 
                  line_color="red",
                  annotation_text="Threshold")
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Statistics
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Current Value", 
                 f"{filtered_df['value'].iloc[-1]:.2f}")
    with col2:
        st.metric("Threshold", 
                 f"{filtered_df['threshold'].iloc[0]:.2f}")
    
    # Raw data
    with st.expander("Raw Data"):
        st.dataframe(filtered_df)
else:
    st.error("No data available. Please check API connection.") 