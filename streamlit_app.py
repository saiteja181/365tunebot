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
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS for professional look
st.markdown("""
<style>
    .main > div {
        padding-top: 2rem;
    }
    
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.5rem;
        border-radius: 10px;
        color: white;
        text-align: center;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        margin-bottom: 1rem;
    }
    
    .metric-value {
        font-size: 2rem;
        font-weight: bold;
        margin: 0;
    }
    
    .metric-label {
        font-size: 0.9rem;
        opacity: 0.9;
        margin-top: 0.5rem;
    }
    
    .dashboard-header {
        background: linear-gradient(90deg, #1e3c72 0%, #2a5298 100%);
        padding: 2rem;
        border-radius: 15px;
        color: white;
        margin-bottom: 2rem;
        text-align: center;
    }
    
    .query-section {
        background: white;
        padding: 2rem;
        border-radius: 15px;
        box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
        border: 1px solid #e1e5e9;
        margin: 2rem 0;
    }
    
    .step-card {
        background: #f8f9fa;
        border-left: 4px solid #007bff;
        padding: 1rem;
        margin: 1rem 0;
        border-radius: 5px;
    }
    
    .stTextInput > div > div > input {
        border-radius: 25px;
        border: 2px solid #e1e5e9;
        padding: 1rem 1.5rem;
        font-size: 1.1rem;
    }
    
    .stButton > button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        padding: 0.75rem 2rem;
        border-radius: 25px;
        font-weight: bold;
        font-size: 1.1rem;
        width: 100%;
        transition: all 0.3s;
    }
    
    .stButton > button:hover {
        box-shadow: 0 5px 15px rgba(102, 126, 234, 0.4);
        transform: translateY(-2px);
    }
    
    .insight-box {
        background: linear-gradient(135deg, #ff9a56 0%, #ff6b6b 100%);
        color: white;
        padding: 1.5rem;
        border-radius: 10px;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
# Initialize session state with defaults
def initialize_session_state():
    """Initialize all session state variables with proper defaults"""
    if 'system' not in st.session_state:
        st.session_state.system = None
    if 'system_ready' not in st.session_state:
        st.session_state.system_ready = False
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

@st.cache_resource
def initialize_system():
    """Initialize the NLP system"""
    try:
        system = TextToSQLSystem()
        csv_file = "enhanced_db_schema.csv"
        
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
        st.info("📊 Install Plotly for interactive charts: `pip install plotly`")
        return
        
    # Section 1: Geographic Analytics
    st.markdown("### 🌍 Geographic Distribution & Activity")
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
    st.markdown("### 🏢 Department Analysis & License Utilization")
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
    # Header
    st.markdown("""
    <div class="dashboard-header">
        <h1 style="margin: 0; font-size: 2.5rem;">🤖 365 Tune Bot</h1>
        <p style="margin: 0.5rem 0 0 0; font-size: 1.2rem; opacity: 0.9;">
            Your intelligent Microsoft 365 data assistant - Ask questions about your data in natural language
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # Initialize system
    if not st.session_state.system_ready:
        with st.spinner("🚀 Initializing 365 Tune Bot..."):
            system, message = initialize_system()
            
            if system:
                st.session_state.system = system
                st.session_state.system_ready = True
                st.success("✅ System ready! Loading dashboard...")
            else:
                st.error(f"❌ {message}")
                st.stop()
    
    # Load dashboard data only if system is ready and data is empty
    if (st.session_state.system and st.session_state.system_ready and 
        st.session_state.dashboard_data.get('Total Users', 0) == 0):
        with st.spinner("📈 Loading dashboard insights..."):
            dashboard_data = load_dashboard_data(st.session_state.system)
            if isinstance(dashboard_data, dict):
                st.session_state.dashboard_data.update(dashboard_data)
    
    # Dashboard Section
    st.markdown("## 📈 Data Overview")
    
    # Display metrics
    display_dashboard_metrics(st.session_state.dashboard_data)
    
    # Display comprehensive Power BI analytics
    st.markdown("### 📊 Power BI Analytics Dashboard")
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
                <h4>💡 User Activity Insight</h4>
                <p><strong>{active_percentage:.1f}%</strong> of users are currently active</p>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            st.markdown(f"""
            <div class="insight-box">
                <h4>📝 Licensing Insight</h4>
                <p><strong>{licensed_percentage:.1f}%</strong> of users have licenses</p>
            </div>
            """, unsafe_allow_html=True)
    
    # Query Interface
    st.markdown("""
    <div class="query-section">
        <h2 style="color: #333; margin-bottom: 1rem;">🤖 Ask 365 Tune Bot</h2>
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
        ask_button = st.button("🔍 Ask", key="ask_button")
    
    # Sample questions as info
    st.markdown("""
    **💡 Try these sample questions:**
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
        st.markdown("## 🔍 Query Processing")
        
        # Create containers for real-time updates
        progress_bar = st.progress(0)
        status_container = st.container()
        steps_container = st.container()
        results_container = st.container()
        
        start_time = time.time()
        
        with status_container:
            st.info(f"🔍 Processing: **{user_query}**")
        
        # Process the query
        result = st.session_state.system.process_query(user_query)
        processing_time = time.time() - start_time
        
        progress_bar.progress(100)
        
        if "error" in result:
            st.error(f"❌ Error: {result['error']}")
        else:
            # Extract results
            faiss_results = result.get("step_1_vector_search", {}).get("results", [])
            sql_query = result.get("step_2_sql_generation", {}).get("sql_query", "")
            execution_info = result.get("step_3_sql_execution", {}).get("execution_info", "")
            sample_results = result.get("step_3_sql_execution", {}).get("sample_results", [])
            final_answer = result.get("step_4_final_answer", {}).get("answer", "")
            
            # Display intermediate steps
            with steps_container:
                st.markdown("### 🔄 Processing Steps")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    # Step 1: Vector Search
                    step1_details = ""
                    if faiss_results:
                        step1_details = f"📊 **Found {len(faiss_results)} relevant tables:**\n\n"
                        for i, table in enumerate(faiss_results[:3], 1):
                            table_name = table.get('table_name', 'Unknown')
                            score = table.get('relevance_score', 0)
                            preview = table.get('schema_preview', 'No preview')[:100]
                            step1_details += f"{i}. **{table_name}** (relevance: {score:.3f})\n"
                            step1_details += f"   *{preview}...*\n\n"
                    else:
                        step1_details = "*No relevant tables found*"
                    
                    display_step_card(
                        "Step 1: Vector Database Search",
                        "Finding relevant tables using semantic search",
                        "completed" if faiss_results else "failed",
                        step1_details
                    )
                    
                    # Step 3: Query Execution
                    step3_details = ""
                    if sample_results:
                        columns_list = ', '.join(list(sample_results[0].keys())[:5]) + ('...' if len(sample_results[0].keys()) > 5 else '') if sample_results else 'N/A'
                        step3_details = f"✅ **Execution Results:**\n\n• **Rows retrieved:** {len(sample_results):,}\n• **Columns:** {columns_list}\n• **Status:** ✅ Success"
                    else:
                        step3_details = f"⚠️ **Execution Info:**\n\n{execution_info or 'No results found'}"
                    
                    display_step_card(
                        "Step 3: Query Execution",
                        "Running SQL query against database",
                        "completed" if sample_results else "failed",
                        step3_details
                    )
                
                with col2:
                    # Step 2: SQL Generation
                    step2_details = ""
                    if sql_query:
                        step2_details = f"🔧 **Generated SQL Query:**\n\n```sql\n{sql_query}\n```\n\n*Query length: {len(sql_query)} characters*"
                    else:
                        step2_details = "*No SQL query generated*"
                    
                    display_step_card(
                        "Step 2: SQL Query Generation",
                        "Converting natural language to SQL query",
                        "completed" if sql_query else "failed",
                        step2_details
                    )
                    
                    # Step 4: NLP Processing
                    step4_details = ""
                    if final_answer:
                        answer_preview = final_answer[:150] + '...' if len(final_answer) > 150 else final_answer
                        step4_details = f"💬 **Answer Preview:**\n\n> {answer_preview}\n\n*Answer length: {len(final_answer)} characters*"
                    else:
                        step4_details = "*No final answer generated*"
                    
                    display_step_card(
                        "Step 4: NLP Processing",
                        "Converting results to natural language",
                        "completed" if final_answer else "failed",
                        step4_details
                    )
            
            # Display results
            with results_container:
                st.markdown("### 🎯 Results")
                
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
                
                # Final Answer
                if final_answer:
                    st.markdown("#### 🤖 365 Tune Bot Response")
                    st.markdown(f"""
                    <div style="
                        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                        padding: 2rem;
                        border-radius: 15px;
                        color: white;
                        margin: 1rem 0;
                    ">
                        <h4 style="margin-top: 0; color: white;">💬 365 Tune Bot Says:</h4>
                        <p style="font-size: 1.1rem; line-height: 1.6; margin-bottom: 0;">{final_answer}</p>
                    </div>
                    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()