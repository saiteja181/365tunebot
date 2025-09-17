import React, { useState, useEffect } from 'react';
import axios from 'axios';

const API_BASE_URL = 'http://localhost:8000';

const Dashboard = () => {
  const [metrics, setMetrics] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchDashboardData();
  }, []);

  const fetchDashboardData = async () => {
    try {
      setLoading(true);
      setError(null);
      
      const response = await axios.get(`${API_BASE_URL}/api/dashboard`);
      
      if (response.data.success) {
        setMetrics(response.data.metrics);
      } else {
        setError('Failed to fetch dashboard data');
      }
    } catch (err) {
      setError(`Error: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="metrics">
        <h2>Dashboard Metrics</h2>
        <div className="loading">Loading metrics...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="metrics">
        <h2>Dashboard Metrics</h2>
        <div className="error">{error}</div>
      </div>
    );
  }

  return (
    <div className="metrics">
      <h2>Dashboard Metrics</h2>
      <div className="metrics-grid">
        <div className="metric-item">
          <div className="metric-value">{metrics?.["Total Users"]?.toLocaleString() || 0}</div>
          <div className="metric-label">Total Users</div>
        </div>
        <div className="metric-item">
          <div className="metric-value">{metrics?.["Active Users"]?.toLocaleString() || 0}</div>
          <div className="metric-label">Active Users</div>
        </div>
        <div className="metric-item">
          <div className="metric-value">{metrics?.["Licensed Users"]?.toLocaleString() || 0}</div>
          <div className="metric-label">Licensed Users</div>
        </div>
        <div className="metric-item">
          <div className="metric-value">{metrics?.["Countries"]?.toLocaleString() || 0}</div>
          <div className="metric-label">Countries</div>
        </div>
        <div className="metric-item">
          <div className="metric-value">{metrics?.["Inactive Users"]?.toLocaleString() || 0}</div>
          <div className="metric-label">Inactive Users</div>
        </div>
        <div className="metric-item">
          <div className="metric-value">{metrics?.["Guest Users"]?.toLocaleString() || 0}</div>
          <div className="metric-label">Guest Users</div>
        </div>
        <div className="metric-item">
          <div className="metric-value">{metrics?.["Admin Users"]?.toLocaleString() || 0}</div>
          <div className="metric-label">Admin Users</div>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;