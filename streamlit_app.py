#!/usr/bin/env python3
"""
Professional NLP Question-Answer System
Single page application with Power BI-style dashboard
"""

import streamlit as st
import pandas as pd
import time
import json
import os
import numpy as np
from datetime import datetime
from main import TextToSQLSystem

# Optional plotly import
try:
    import plotly.express as px
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False

# Page configuration
st.set_page_config(
    page_title="365 Tune Bot",
    page_icon="Bot",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Initialize session state
def initialize_session_state():
    """Initialize all session state variables with proper defaults"""
    if 'system' not in st.session_state:
        st.session_state.system = None
    if 'system_ready' not in st.session_state:
        st.session_state.system_ready = False
    if 'theme' not in st.session_state:
        st.session_state.theme = 'light'
    if 'dashboard_data' not in st.session_state or not isinstance(st.session_state.dashboard_data, dict):
        st.session_state.dashboard_data = {
            'Total Users': 0, 'Active Users': 0, 'Licensed Users': 0, 
            'Countries': 0, 'Inactive Users': 0, 'Guest Users': 0, 'Admin Users': 0,
            'Countries_Data': [], 'Departments_Data': [], 'License_Analysis': [],
            'Activity_Trends': [], 'Security_Analysis': [], 'Cost_Analysis': [],
            'Geographic_Activity': [], 'Mailbox_Analysis': [], 'Login_Patterns': []
        }

# Call initialization
initialize_session_state()

def get_theme_colors():
    """Get colors based on current theme"""
    if st.session_state.theme == 'dark':
        return {
            'bg_primary': '#1e1e1e',
            'bg_secondary': '#2d2d2d',
            'text_primary': '#ffffff',
            'text_secondary': '#cccccc',
            'accent_1': '#667eea',
            'accent_2': '#764ba2',
            'card_bg': '#2d2d2d',
            'border': '#404040'
        }
    else:
        return {
            'bg_primary': '#ffffff',
            'bg_secondary': '#f8f9fa',
            'text_primary': '#333333',
            'text_secondary': '#666666',
            'accent_1': '#667eea',
            'accent_2': '#764ba2',
            'card_bg': '#ffffff',
            'border': '#e1e5e9'
        }

def apply_shadcn_theme():
    """Apply clean black and white theme"""
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
        
        /* Hide sidebar completely */
        .css-1d391kg { display: none; }
        section[data-testid="stSidebar"] { display: none !important; }
        
        /* Root variables - Clean Black and White */
        :root {
            --background: 0 0% 100%;
            --foreground: 0 0% 0%;
            --card: 0 0% 100%;
            --card-foreground: 0 0% 0%;
            --popover: 0 0% 100%;
            --popover-foreground: 0 0% 0%;
            --primary: 0 0% 0%;
            --primary-foreground: 0 0% 100%;
            --secondary: 0 0% 96%;
            --secondary-foreground: 0 0% 0%;
            --muted: 0 0% 96%;
            --muted-foreground: 0 0% 45%;
            --accent: 0 0% 96%;
            --accent-foreground: 0 0% 0%;
            --destructive: 0 84.2% 60.2%;
            --destructive-foreground: 0 0% 100%;
            --border: 0 0% 90%;
            --input: 0 0% 90%;
            --ring: 0 0% 0%;
        }
        
        /* Main app container */
        .stApp {
            background-color: hsl(var(--background));
            color: hsl(var(--foreground));
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
        }
        
        /* Main content area */
        .main > div {
            padding: 2rem 1rem;
            max-width: 1400px;
            margin: 0 auto;
        }
        
        /* Header styling */
        .dashboard-header {
            background: hsl(var(--primary));
            color: hsl(var(--primary-foreground));
            padding: 3rem 2rem;
            border-radius: 8px;
            margin-bottom: 2rem;
            text-align: center;
            border: 2px solid hsl(var(--border));
        }
        
        /* Metric cards */
        .metric-card {
            background: hsl(var(--card));
            border: 2px solid hsl(var(--border));
            padding: 1.5rem;
            border-radius: 8px;
            text-align: center;
            margin-bottom: 1rem;
            transition: all 0.2s;
        }
        
        .metric-card:hover {
            border: 2px solid hsl(var(--foreground));
            transform: translateY(-2px);
        }
        
        .metric-value {
            font-size: 2rem;
            font-weight: 700;
            margin: 0;
            color: hsl(var(--foreground));
        }
        
        .metric-label {
            font-size: 0.875rem;
            color: hsl(var(--muted-foreground));
            margin-top: 0.5rem;
            font-weight: 500;
        }
        
        /* Query section */
        .query-section {
            background: hsl(var(--card));
            border: 1px solid hsl(var(--border));
            padding: 2rem;
            border-radius: 12px;
            margin: 2rem 0;
            box-shadow: 0 1px 3px 0 rgb(0 0 0 / 0.1), 0 1px 2px -1px rgb(0 0 0 / 0.1);
        }
        
        .query-section h2 {
            color: hsl(var(--foreground)) !important;
            font-weight: 600 !important;
            margin-bottom: 0.5rem !important;
        }
        
        .query-section p {
            color: hsl(var(--muted-foreground)) !important;
            margin-bottom: 0 !important;
        }
        
        /* Step cards */
        .step-card {
            background: hsl(var(--card));
            border: 1px solid hsl(var(--border));
            border-left: 4px solid hsl(var(--primary));
            padding: 1rem;
            margin: 1rem 0;
            border-radius: 8px;
        }
        
        /* Input styling */
        .stTextInput > div > div > input {
            border: 1px solid hsl(var(--border));
            border-radius: 8px;
            padding: 0.75rem 1rem;
            font-size: 1rem;
            background-color: hsl(var(--background));
            color: hsl(var(--foreground));
            font-family: inherit;
            transition: border-color 0.2s;
        }
        
        .stTextInput > div > div > input:focus {
            outline: none;
            border-color: hsl(var(--ring));
            box-shadow: 0 0 0 2px hsl(var(--ring) / 0.2);
        }
        
        /* Button styling */
        .stButton > button {
            background: hsl(var(--primary));
            color: hsl(var(--primary-foreground));
            border: 1px solid hsl(var(--border));
            padding: 0.75rem 1.5rem;
            border-radius: 8px;
            font-weight: 500;
            font-size: 0.875rem;
            transition: all 0.2s;
            cursor: pointer;
        }
        
        .stButton > button:hover {
            background: hsl(var(--primary) / 0.9);
            box-shadow: 0 2px 4px 0 rgb(0 0 0 / 0.1);
        }
        
        /* Selectbox styling */
        .stSelectbox > div > div > div {
            background-color: hsl(var(--background));
            border: 1px solid hsl(var(--border));
            border-radius: 8px;
        }
        
        /* Metric styling */
        .stMetric {
            background: hsl(var(--card));
            border: 1px solid hsl(var(--border));
            padding: 1rem;
            border-radius: 8px;
        }
        
        /* Insight box */
        .insight-box {
            background: hsl(var(--secondary));
            color: hsl(var(--secondary-foreground));
            border: 1px solid hsl(var(--border));
            padding: 1.5rem;
            border-radius: 8px;
            margin: 1rem 0;
        }
        
        /* Success/error messages */
        .stAlert > div {
            border-radius: 8px;
        }
        
        /* Typography */
        .css-10trblm, .css-16idsys p, .css-1629p8f h1, .css-1629p8f h2, .css-1629p8f h3 {
            color: hsl(var(--foreground)) !important;
            font-family: 'Inter', sans-serif !important;
        }
        
        /* DataFrame styling */
        .dataframe {
            background-color: hsl(var(--card)) !important;
            border: 1px solid hsl(var(--border)) !important;
            border-radius: 8px !important;
        }
        
        .dataframe th {
            background-color: hsl(var(--muted)) !important;
            color: hsl(var(--muted-foreground)) !important;
            font-weight: 600 !important;
        }
        
        .dataframe td {
            color: hsl(var(--foreground)) !important;
        }
        
        /* Chart containers */
        .js-plotly-plot {
            background-color: hsl(var(--card)) !important;
            border: 1px solid hsl(var(--border)) !important;
            border-radius: 8px !important;
        }
        
        /* Remove default Streamlit padding */
        .css-1kyxreq {
            margin-top: -2rem;
        }
        
        /* Tab styling if any */
        .stTabs > div > div > div > div {
            background: hsl(var(--background));
            border: 1px solid hsl(var(--border));
            border-radius: 8px;
        }
        
        /* Expander styling */
        .streamlit-expanderHeader {
            background-color: hsl(var(--card));
            border: 1px solid hsl(var(--border));
            border-radius: 8px;
        }
        
        /* Progress bar */
        .stProgress > div > div {
            background-color: hsl(var(--primary));
        }
        
        /* Info, success, error styling */
        .stInfo, .stSuccess, .stError, .stWarning {
            border-radius: 8px !important;
            border: 1px solid hsl(var(--border)) !important;
        }
        
        /* Spinner */
        .stSpinner > div {
            border-color: hsl(var(--primary)) !important;
        }
    </style>
    """, unsafe_allow_html=True)

# Apply the theme after defining the function
apply_shadcn_theme()

@st.cache_resource
def initialize_system():
    """Initialize the NLP system"""
    try:
        system = TextToSQLSystem()
        csv_file = "data/enhanced_db_schema.csv"
        
        if not os.path.exists(csv_file):
            return None, f"CSV file not found: {csv_file}"
        
        success = system.initialize_system(csv_file)
        if not success:
            return None, "Failed to initialize system"
        
        return system, "System initialized successfully"
    except Exception as e:
        return None, f"Error initializing system: {str(e)}"

def load_dashboard_data(_system):
    """Load comprehensive Power BI-style analytics data"""
    try:
        if not _system or not hasattr(_system, 'sql_executor'):
            st.error("System not properly initialized")
            return {
                'Total Users': 0, 'Active Users': 0, 'Licensed Users': 0, 
                'Countries': 0, 'Inactive Users': 0, 'Guest Users': 0, 'Admin Users': 0,
                'Countries_Data': [], 'Departments_Data': [], 'License_Analysis': [],
                'Activity_Trends': [], 'Security_Analysis': [], 'Cost_Analysis': [],
                'Geographic_Activity': [], 'Mailbox_Analysis': [], 'Login_Patterns': []
            }
        
        dashboard_data = {}
        
        # Basic Statistics
        basic_queries = [
            ("Total Users", "SELECT COUNT(*) as count FROM UserRecords"),
            ("Active Users", "SELECT COUNT(*) as count FROM UserRecords WHERE AccountStatus = 'Active'"),
            ("Licensed Users", "SELECT COUNT(*) as count FROM UserRecords WHERE IsLicensed = 1"),
            ("Countries", "SELECT COUNT(DISTINCT Country) as count FROM UserRecords WHERE Country IS NOT NULL"),
            ("Inactive Users", "SELECT COUNT(*) as count FROM UserRecords WHERE AccountStatus != 'Active'"),
            ("Guest Users", "SELECT COUNT(*) as count FROM UserRecords WHERE UserType = 'Guest'"),
            ("Admin Users", "SELECT COUNT(*) as count FROM UserRecords WHERE IsAdmin = 1"),
        ]
        
        for label, query in basic_queries:
            try:
                # Execute query and handle result properly
                success, result, execution_info = _system.sql_executor.execute_query(query)
                if success and result and len(result) > 0 and 'count' in result[0]:
                    dashboard_data[label] = result[0]['count']
                else:
                    dashboard_data[label] = 0
            except Exception as e:
                dashboard_data[label] = 0
        
        # Advanced Analytics Queries
        analytics_queries = {
            'Countries_Data': """
                SELECT TOP 15 Country, COUNT(*) as UserCount, 
                       SUM(CASE WHEN AccountStatus = 'Active' THEN 1 ELSE 0 END) as ActiveUsers,
                       SUM(CASE WHEN IsLicensed = 1 THEN 1 ELSE 0 END) as LicensedUsers
                FROM UserRecords 
                WHERE Country IS NOT NULL 
                GROUP BY Country 
                ORDER BY UserCount DESC
            """,
            
            'Departments_Data': """
                SELECT TOP 15 Department, COUNT(*) as UserCount,
                       SUM(CASE WHEN AccountStatus = 'Active' THEN 1 ELSE 0 END) as ActiveUsers,
                       AVG(CAST(EmailSent_D30 as FLOAT)) as AvgEmailsSent30D
                FROM UserRecords 
                WHERE Department IS NOT NULL 
                GROUP BY Department 
                ORDER BY UserCount DESC
            """,
            
            'License_Analysis': """
                SELECT l.Name as LicenseName, l.TotalUnits, l.ConsumedUnits, 
                       l.ActualCost, l.Status,
                       (CAST(l.ConsumedUnits as FLOAT) / NULLIF(l.TotalUnits, 0) * 100) as UtilizationPercent
                FROM Licenses l
                WHERE l.TotalUnits > 0
                ORDER BY l.ActualCost DESC
            """,
            
            'Activity_Trends': """
                SELECT TOP 20 DisplayName, Mail, Country, Department,
                       EmailSent_D7, EmailSent_D30, EmailSent_D90,
                       EmailReceive_D7, EmailReceive_D30, EmailReceive_D90,
                       Meeting_Created_Count_30, Meeting_Interacted_Count_30,
                       LastSignInDateTime
                FROM UserRecords 
                WHERE AccountStatus = 'Active'
                ORDER BY (EmailSent_D30 + EmailReceive_D30 + Meeting_Created_Count_30) DESC
            """,
            
            'Security_Analysis': """
                SELECT 
                    SUM(CASE WHEN IsMFADisabled = 0 OR IsMFADisabled IS NULL THEN 1 ELSE 0 END) as MFAEnabled,
                    SUM(CASE WHEN IsMFADisabled = 1 THEN 1 ELSE 0 END) as MFADisabled,
                    SUM(CASE WHEN IsAdmin = 1 THEN 1 ELSE 0 END) as AdminUsers,
                    SUM(CASE WHEN IsSSPRCapable = 1 THEN 1 ELSE 0 END) as SSPRCapable,
                    COUNT(DISTINCT LastLogin_Country) as LoginCountries
                FROM UserRecords
                WHERE AccountStatus = 'Active'
            """,
            
            'Cost_Analysis': """
                SELECT 
                    SUM(l.ActualCost * l.ConsumedUnits) as TotalCost,
                    AVG(l.ActualCost) as AvgLicenseCost,
                    SUM(CASE WHEN l.ConsumedUnits = 0 THEN l.ActualCost ELSE 0 END) as UnusedLicenseCost,
                    COUNT(DISTINCT l.Name) as UniqueLicenseTypes
                FROM Licenses l
                WHERE l.ActualCost IS NOT NULL AND l.ActualCost > 0
            """,
            
            'Geographic_Activity': """
                SELECT TOP 10 Country, 
                       COUNT(*) as UserCount,
                       AVG(CAST(EmailSent_D30 as FLOAT)) as AvgEmailsSent,
                       AVG(CAST(EmailReceive_D30 as FLOAT)) as AvgEmailsReceived,
                       MAX(LastSignInDateTime) as LastActivity
                FROM UserRecords 
                WHERE Country IS NOT NULL AND AccountStatus = 'Active'
                GROUP BY Country 
                ORDER BY UserCount DESC
            """,
            
            'Mailbox_Analysis': """
                SELECT 
                    AVG(MailBoxSizeInMB) as AvgMailboxSize,
                    MAX(MailBoxSizeInMB) as MaxMailboxSize,
                    SUM(CASE WHEN MailBoxSizeInMB > ProhibitSendQuotaMB * 0.8 THEN 1 ELSE 0 END) as NearQuotaLimit,
                    SUM(CASE WHEN MailBoxSizeInMB >= ProhibitSendQuotaMB THEN 1 ELSE 0 END) as OverQuota
                FROM UserRecords 
                WHERE MailBoxSizeInMB > 0
            """,
            
            'Login_Patterns': """
                SELECT 
                    DATENAME(WEEKDAY, LastSignInDateTime) as DayOfWeek,
                    DATEPART(HOUR, LastSignInDateTime) as HourOfDay,
                    COUNT(*) as LoginCount
                FROM UserRecords 
                WHERE LastSignInDateTime IS NOT NULL 
                    AND LastSignInDateTime >= DATEADD(day, -30, GETDATE())
                GROUP BY DATENAME(WEEKDAY, LastSignInDateTime), DATEPART(HOUR, LastSignInDateTime)
                ORDER BY LoginCount DESC
            """
        }
        
        # Execute analytics queries
        for key, query in analytics_queries.items():
            try:
                success, result, execution_info = _system.sql_executor.execute_query(query)
                if success and result:
                    # Ensure result is a proper list of dictionaries
                    if isinstance(result, list) and len(result) > 0:
                        # Convert any pandas rows to dictionaries if needed
                        clean_result = []
                        for row in result:
                            if hasattr(row, 'to_dict'):
                                clean_result.append(row.to_dict())
                            elif isinstance(row, dict):
                                # Convert to regular dict and handle any special types
                                clean_dict = {}
                                for k, v in row.items():
                                    if v is None or pd.isna(v):
                                        clean_dict[k] = None
                                    elif hasattr(v, 'item'):  # numpy types
                                        clean_dict[k] = v.item()
                                    else:
                                        clean_dict[k] = v
                                clean_result.append(clean_dict)
                            else:
                                clean_result.append(row)
                        dashboard_data[key] = clean_result
                    else:
                        dashboard_data[key] = []
                else:
                    dashboard_data[key] = []
            except Exception as e:
                dashboard_data[key] = []
                print(f"Error executing {key}: {e}")
        
        return dashboard_data
        
    except Exception as e:
        st.error(f"Error loading Power BI analytics data: {e}")
        return {
            'Total Users': 0, 'Active Users': 0, 'Licensed Users': 0, 
            'Countries': 0, 'Inactive Users': 0, 'Guest Users': 0, 'Admin Users': 0,
            'Countries_Data': [], 'Departments_Data': [], 'License_Analysis': [],
            'Activity_Trends': [], 'Security_Analysis': [], 'Cost_Analysis': [],
            'Geographic_Activity': [], 'Mailbox_Analysis': [], 'Login_Patterns': []
        }

def display_dashboard_metrics(data):
    """Display comprehensive Power BI-style metrics"""
    if not isinstance(data, dict):
        st.error(f"Invalid data format for metrics: {type(data)}")
        return
        
    # Row 1: Primary Metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{data.get('Total Users', 0):,}</div>
            <div class="metric-label">Total Users</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        active_users = data.get('Active Users', 0)
        total_users = data.get('Total Users', 1)
        active_percentage = (active_users / total_users * 100) if total_users > 0 else 0
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{active_users:,}</div>
            <div class="metric-label">Active Users ({active_percentage:.1f}%)</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        licensed_users = data.get('Licensed Users', 0)
        licensed_percentage = (licensed_users / total_users * 100) if total_users > 0 else 0
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{licensed_users:,}</div>
            <div class="metric-label">Licensed Users ({licensed_percentage:.1f}%)</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{data.get('Countries', 0)}</div>
            <div class="metric-label">Countries</div>
        </div>
        """, unsafe_allow_html=True)
    
    # Row 2: Security & Administrative Metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        inactive_users = data.get('Inactive Users', 0)
        st.markdown(f"""
        <div class="metric-card" style="background: linear-gradient(135deg, #ff9a56 0%, #ff6b6b 100%);">
            <div class="metric-value">{inactive_users:,}</div>
            <div class="metric-label">Inactive Users</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        guest_users = data.get('Guest Users', 0)
        st.markdown(f"""
        <div class="metric-card" style="background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);">
            <div class="metric-value">{guest_users:,}</div>
            <div class="metric-label">Guest Users</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        admin_users = data.get('Admin Users', 0)
        st.markdown(f"""
        <div class="metric-card" style="background: linear-gradient(135deg, #a8edea 0%, #fed6e3 100%); color: #333;">
            <div class="metric-value" style="color: #333;">{admin_users:,}</div>
            <div class="metric-label" style="color: #333;">Admin Users</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        # Calculate cost from cost analysis data
        cost_data = data.get('Cost_Analysis', [])
        total_cost = cost_data[0].get('TotalCost', 0) if cost_data else 0
        st.markdown(f"""
        <div class="metric-card" style="background: linear-gradient(135deg, #ffeaa7 0%, #fab1a0 100%); color: #333;">
            <div class="metric-value" style="color: #333;">${total_cost:,.0f}</div>
            <div class="metric-label" style="color: #333;">License Costs</div>
        </div>
        """, unsafe_allow_html=True)

def display_dashboard_charts(data):
    """Display comprehensive Power BI-style analytics"""
    if not isinstance(data, dict):
        st.error(f"Invalid data format for charts: {type(data)}")
        return
        
    if not PLOTLY_AVAILABLE:
        st.info("Install Plotly for interactive charts: `pip install plotly`")
        return
        
    # Section 1: Geographic Analytics
    st.markdown("### Geographic Distribution & Activity")
    col1, col2 = st.columns(2)
    
    with col1:
        countries_data = data.get('Countries_Data', [])
        if countries_data and len(countries_data) > 0:
            try:
                # Handle case where data might be nested in first element
                if len(countries_data) == 1 and isinstance(countries_data[0], list):
                    countries_data = countries_data[0]
                
                df_countries = pd.DataFrame(countries_data)
                
                # Debug: check the actual structure
                if df_countries.empty or 'Country' not in df_countries.columns:
                    st.info("Countries Data Structure:")
                    st.write(f"DataFrame shape: {df_countries.shape}")
                    st.write(f"Columns: {list(df_countries.columns)}")
                    st.write("Sample data:", countries_data[:2] if countries_data else "No data")
                    return
                
                if 'Country' in df_countries.columns and 'UserCount' in df_countries.columns:
                    fig = px.bar(
                        df_countries.head(10), 
                        x='Country', 
                        y='UserCount',
                        color='ActiveUsers' if 'ActiveUsers' in df_countries.columns else 'UserCount',
                        title="Users by Country (Top 10)",
                        color_continuous_scale='Viridis'
                    )
                    fig.update_layout(
                        plot_bgcolor='rgba(0,0,0,0)',
                        paper_bgcolor='rgba(0,0,0,0)',
                        font=dict(size=11),
                        showlegend=False
                    )
                    st.plotly_chart(fig, width="stretch")
                else:
                    st.dataframe(df_countries)
            except Exception as e:
                st.error(f"Error displaying countries chart: {str(e)}")
                st.write("Raw countries data sample:", countries_data[:2] if countries_data else "No data")
    
    with col2:
        geo_activity = data.get('Geographic_Activity', [])
        if geo_activity and len(geo_activity) > 0:
            df_geo = pd.DataFrame(geo_activity)
            if 'Country' in df_geo.columns and 'AvgEmailsSent' in df_geo.columns:
                fig = px.scatter(
                    df_geo.head(10),
                    x='AvgEmailsSent',
                    y='AvgEmailsReceived', 
                    size='UserCount',
                    hover_name='Country',
                    title="Email Activity by Country",
                    color='UserCount',
                    color_continuous_scale='Plasma'
                )
                fig.update_layout(
                    plot_bgcolor='rgba(0,0,0,0)',
                    paper_bgcolor='rgba(0,0,0,0)',
                    font=dict(size=11)
                )
                st.plotly_chart(fig, width="stretch")
            else:
                st.dataframe(df_geo)
    
    # Section 2: Department & License Analytics
    st.markdown("### Department Analysis & License Utilization")
    col1, col2 = st.columns(2)
    
    with col1:
        dept_data = data.get('Departments_Data', [])
        if dept_data and len(dept_data) > 0:
            try:
                # Handle case where data might be nested in first element
                if len(dept_data) == 1 and isinstance(dept_data[0], list):
                    dept_data = dept_data[0]
                
                df_dept = pd.DataFrame(dept_data)
                
                # Debug: check the actual structure
                if df_dept.empty or 'Department' not in df_dept.columns:
                    st.info("Department Data Structure:")
                    st.write(f"DataFrame shape: {df_dept.shape}")
                    st.write(f"Columns: {list(df_dept.columns)}")
                    st.write("Sample data:", dept_data[:2] if dept_data else "No data")
                    return
                
                if 'Department' in df_dept.columns and 'UserCount' in df_dept.columns:
                    fig = px.treemap(
                        df_dept.head(10),
                        path=['Department'],
                        values='UserCount',
                        color='ActiveUsers' if 'ActiveUsers' in df_dept.columns else 'UserCount',
                        title="Department Distribution (Treemap)",
                        color_continuous_scale='Blues'
                    )
                    fig.update_layout(font=dict(size=11))
                    st.plotly_chart(fig, width="stretch")
                else:
                    st.dataframe(df_dept)
            except Exception as e:
                st.error(f"Error displaying department chart: {str(e)}")
                st.write("Raw department data sample:", dept_data[:2] if dept_data else "No data")
    
    with col2:
        license_data = data.get('License_Analysis', [])
        if license_data and len(license_data) > 0:
            df_licenses = pd.DataFrame(license_data)
            if 'LicenseName' in df_licenses.columns and 'UtilizationPercent' in df_licenses.columns:
                fig = px.bar(
                    df_licenses.head(10),
                    x='LicenseName',
                    y='UtilizationPercent',
                    color='ActualCost' if 'ActualCost' in df_licenses.columns else 'UtilizationPercent',
                    title="License Utilization %",
                    color_continuous_scale='RdYlGn'
                )
                fig.update_xaxes(tickangle=45)
                fig.update_layout(
                    plot_bgcolor='rgba(0,0,0,0)',
                    paper_bgcolor='rgba(0,0,0,0)',
                    font=dict(size=11)
                )
                st.plotly_chart(fig, width="stretch")
            else:
                st.dataframe(df_licenses)
    

def display_step_card(step_name, description, status, details):
    """Display a step card with status and details"""
    status_colors = {
        'completed': '#28a745',
        'failed': '#dc3545',
        'in_progress': '#ffc107'
    }
    
    status_icons = {
        'completed': '✅',
        'failed': '❌', 
        'in_progress': '⏳'
    }
    
    color = status_colors.get(status, '#6c757d')
    icon = status_icons.get(status, '⚪')
    
    st.markdown(f"""
    <div style="
        border-left: 4px solid {color};
        padding: 1rem;
        margin: 0.5rem 0;
        background: white;
        border-radius: 0 8px 8px 0;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    ">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem;">
            <h4 style="margin: 0; color: #333;">{step_name}</h4>
            <span style="
                background: {color}; 
                color: white; 
                padding: 0.25rem 0.75rem; 
                border-radius: 15px; 
                font-size: 0.8rem;
                font-weight: bold;
            ">{icon} {status.upper()}</span>
        </div>
        <p style="margin: 0.5rem 0; color: #666;">{description}</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Render details using Streamlit markdown for better compatibility
    if details:
        st.markdown(details)

def main():
    # Apply shadcn theme CSS
    apply_shadcn_theme()

    # Header
    st.markdown("""
    <div class="dashboard-header">
        <h1 style="margin: 0; font-size: 2.5rem;">365 Tune Bot</h1>
        <p style="margin: 0.5rem 0 0 0; font-size: 1.2rem; opacity: 0.9;">
            Your intelligent Microsoft 365 data assistant - Ask questions about your data in natural language
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # Initialize system
    if not st.session_state.system_ready:
        with st.spinner("Initializing 365 Tune Bot..."):
            system, message = initialize_system()
            
            if system:
                st.session_state.system = system
                st.session_state.system_ready = True
                st.success("System ready! Loading dashboard...")
            else:
                st.error(f"Error: {message}")
                st.stop()
    
    # Load dashboard data only if system is ready and data is empty
    if (st.session_state.system and st.session_state.system_ready and 
        st.session_state.dashboard_data.get('Total Users', 0) == 0):
        with st.spinner("Loading dashboard insights..."):
            dashboard_data = load_dashboard_data(st.session_state.system)
            if isinstance(dashboard_data, dict):
                st.session_state.dashboard_data.update(dashboard_data)
    
    # Dashboard Section
    st.markdown("## Data Overview")
    
    # Display metrics
    display_dashboard_metrics(st.session_state.dashboard_data)
    
    # Display comprehensive Power BI analytics
    st.markdown("### Power BI Analytics Dashboard")
    display_dashboard_charts(st.session_state.dashboard_data)
    
    
    # Insights section
    total_users = st.session_state.dashboard_data.get('Total Users', 0)
    active_users = st.session_state.dashboard_data.get('Active Users', 0)
    licensed_users = st.session_state.dashboard_data.get('Licensed Users', 0)
    
    if total_users > 0:
        active_percentage = (active_users / total_users) * 100
        licensed_percentage = (licensed_users / total_users) * 100
        
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"""
            <div class="insight-box">
                <h4>User Activity Insight</h4>
                <p><strong>{active_percentage:.1f}%</strong> of users are currently active</p>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            st.markdown(f"""
            <div class="insight-box">
                <h4>Licensing Insight</h4>
                <p><strong>{licensed_percentage:.1f}%</strong> of users have licenses</p>
            </div>
            """, unsafe_allow_html=True)
    
    # Query Interface
    st.markdown("""
    <div class="query-section">
        <h2 style="color: #333; margin-bottom: 1rem;">Ask 365 Tune Bot</h2>
        <p style="color: #666; margin-bottom: 2rem;">
            Chat with your Microsoft 365 data in natural language. Examples: "Show me users from India", "How many active users do we have?", "Find users in IT department"
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # Query input
    col1, col2 = st.columns([4, 1])
    with col1:
        user_query = st.text_input(
            "Ask your question:", 
            placeholder="Type your question here... (e.g., 'Show me all users from India')",
            key="query_input"
        )
    
    with col2:
        ask_button = st.button("Ask", key="ask_button")
    
    # Sample questions as info
    st.markdown("""
    **Try these sample questions:**
    - "Show me users from India"
    - "How many active users do we have?"
    - "Find users in the IT department" 
    - "Show me users with Microsoft 365 licenses"
    - "Which countries have the most users?"
    """)
    
    st.markdown("---")
    
    # Process query
    if ask_button and user_query:
        st.markdown("---")
        st.markdown("## Query Processing")
        
        # Create containers for real-time updates
        progress_bar = st.progress(0)
        status_container = st.container()
        steps_container = st.container()
        results_container = st.container()
        
        start_time = time.time()
        
        with status_container:
            st.info(f"Processing: **{user_query}**")
        
        # Process the query
        result = st.session_state.system.process_query(user_query)
        processing_time = time.time() - start_time
        
        progress_bar.progress(100)
        
        if "error" in result:
            st.error(f"Error: {result['error']}")
        else:
            # Extract results
            faiss_results = result.get("step_1_vector_search", {}).get("results", [])
            sql_query = result.get("step_2_sql_generation", {}).get("sql_query", "")
            execution_info = result.get("step_3_sql_execution", {}).get("execution_info", "")
            sample_results = result.get("step_3_sql_execution", {}).get("sample_results", [])
            final_answer = result.get("step_4_final_answer", {}).get("answer", "")
            
            # Display simplified processing status  
            with steps_container:
                st.markdown("### Processing Status")
                
                # Simple status indicators
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    status = "✅ Complete" if faiss_results else "❌ Failed"
                    st.markdown(f"**1. Table Search**\n{status}")
                    
                with col2:
                    status = "✅ Complete" if sql_query else "❌ Failed"
                    st.markdown(f"**2. Query Generation**\n{status}")
                    
                with col3:
                    status = "✅ Complete" if sample_results else "❌ Failed"
                    st.markdown(f"**3. Data Retrieval**\n{status}")
                    
                with col4:
                    status = "✅ Complete" if final_answer else "❌ Failed"
                    st.markdown(f"**4. Response Generation**\n{status}")
                
                # Technical details in expandable section
                with st.expander("🔧 Technical Details (Optional)", expanded=False):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        # Step 1: Vector Search
                        step1_details = ""
                        if faiss_results:
                            step1_details = f"**Found {len(faiss_results)} relevant tables:**\n\n"
                            for i, table in enumerate(faiss_results[:3], 1):
                                table_name = table.get('table_name', 'Unknown')
                                score = table.get('relevance_score', 0)
                                step1_details += f"{i}. **{table_name}** (relevance: {score:.3f})\n"
                        else:
                            step1_details = "*No relevant tables found*"
                        
                        st.markdown("**Step 1: Vector Database Search**")
                        st.markdown(step1_details)
                        
                        # Step 3: Query Execution
                        step3_details = ""
                        if sample_results:
                            columns_list = ', '.join(list(sample_results[0].keys())[:5]) + ('...' if len(sample_results[0].keys()) > 5 else '') if sample_results else 'N/A'
                            step3_details = f"• **Rows retrieved:** {len(sample_results):,}\n• **Columns:** {columns_list}\n• **Status:** Success"
                        else:
                            step3_details = f"**Execution Info:** {execution_info or 'No results found'}"
                        
                        st.markdown("**Step 3: Query Execution**")
                        st.markdown(step3_details)
                    
                    with col2:
                        # Step 2: SQL Generation (in expandable details only)
                        if sql_query:
                            st.markdown("**Step 2: Generated SQL Query**")
                            st.code(sql_query, language='sql')
                        
                        # Step 4: NLP Processing
                        step4_details = ""
                        if final_answer:
                            step4_details = f"✅ Natural language response generated successfully\n\n*Response length: {len(final_answer)} characters*"
                        else:
                            step4_details = "❌ No final answer generated"
                        
                        st.markdown("**Step 4: NLP Processing**")
                        st.markdown(step4_details)
            
            # Display results
            with results_container:
                st.markdown("### Results")
                
                # Processing summary
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Processing Time", f"{processing_time:.2f}s")
                with col2:
                    st.metric("Tables Found", len(faiss_results))
                with col3:
                    st.metric("Rows Retrieved", len(sample_results))
                with col4:
                    st.metric("Answer Length", len(final_answer) if final_answer else 0)
                
                # Final Answer - Clean presentation without SQL details
                if final_answer:
                    st.markdown("#### 365 Tune Bot Response")
                    st.markdown(f"""
                    <div style="
                        background: hsl(var(--primary));
                        padding: 2rem;
                        border-radius: 8px;
                        color: hsl(var(--primary-foreground));
                        margin: 1rem 0;
                        border: 2px solid hsl(var(--border));
                    ">
                        <h4 style="margin-top: 0; color: hsl(var(--primary-foreground));">💬 Answer:</h4>
                        <div style="font-size: 1.1rem; line-height: 1.6; margin-bottom: 0;">{final_answer}</div>
                    </div>
                    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()