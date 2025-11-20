import React, { useState, useEffect } from 'react';
import { BarChart, Bar, LineChart, Line, PieChart, Pie, Cell, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import './AIInsights.css';

const AIInsights = () => {
  const [insights, setInsights] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchInsights();
  }, []);

  const fetchInsights = async () => {
    try {
      setLoading(true);
      const response = await fetch('http://127.0.0.1:8000/api/insights');
      const data = await response.json();

      if (data.success) {
        setInsights(data);
        setError(null);
      } else {
        setError(data.error || 'Failed to load insights');
      }
    } catch (err) {
      setError('Error fetching insights: ' + err.message);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="ai-insights-container">
        <div className="insights-header">
          <h2>AI Insights & Predictions</h2>
          <button onClick={fetchInsights} disabled className="refresh-btn">
            Loading...
          </button>
        </div>
        <div className="loading-spinner">Analyzing your data...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="ai-insights-container">
        <div className="insights-header">
          <h2>AI Insights & Predictions</h2>
          <button onClick={fetchInsights} className="refresh-btn">
            Refresh
          </button>
        </div>
        <div className="error-message">{error}</div>
      </div>
    );
  }

  const { statistics, cost_predictions, insights: insightCategories } = insights || {};

  // Prepare data for Cost Trend Chart
  const costTrendData = cost_predictions ? [
    { month: 'Current', cost: cost_predictions.current_monthly_cost, type: 'actual' },
    { month: 'Next Month', cost: cost_predictions.predicted_next_month, type: 'predicted' },
    { month: '3 Months', cost: cost_predictions.predicted_3_months, type: 'predicted' }
  ] : [];

  // Prepare data for Cost Savings Comparison
  const costSavingsData = statistics ? [
    { name: 'Current Cost', value: statistics.total_cost },
    { name: 'Potential Savings', value: statistics.potential_savings },
    { name: 'Optimized Cost', value: statistics.total_cost - statistics.potential_savings }
  ] : [];

  // Prepare data for User Status Breakdown
  const userStatusData = statistics ? [
    { name: 'Active Users', value: statistics.active_users, color: '#000000' },
    { name: 'Inactive Users', value: statistics.inactive_users, color: '#888888' }
  ] : [];

  // Prepare data for License Usage
  const licenseUsageData = statistics ? [
    { name: 'Licensed', value: statistics.licensed_users, color: '#000000' },
    { name: 'Unlicensed', value: statistics.total_users - statistics.licensed_users, color: '#cccccc' }
  ] : [];

  // Before/After Optimization Data
  const optimizationData = statistics ? [
    {
      category: 'Before Optimization',
      'Active with Licenses': statistics.licensed_users - statistics.inactive_with_licenses,
      'Inactive with Licenses': statistics.inactive_with_licenses,
      'Stale Users': statistics.stale_licensed_users
    },
    {
      category: 'After Optimization',
      'Active with Licenses': statistics.licensed_users - statistics.inactive_with_licenses,
      'Inactive with Licenses': 0,
      'Stale Users': 0
    }
  ] : [];

  return (
    <div className="ai-insights-container">
      <div className="insights-header">
        <h2>AI Insights & Cost Predictions</h2>
        <button onClick={fetchInsights} className="refresh-btn">
          Refresh Analysis
        </button>
      </div>

      {/* Statistics Overview */}
      {statistics && (
        <div className="stats-overview">
          <div className="stat-card">
            <div className="stat-label">Total Users</div>
            <div className="stat-value">{statistics.total_users?.toLocaleString()}</div>
          </div>
          <div className="stat-card">
            <div className="stat-label">Active Users</div>
            <div className="stat-value">{statistics.active_users?.toLocaleString()}</div>
          </div>
          <div className="stat-card">
            <div className="stat-label">Current Monthly Cost</div>
            <div className="stat-value">${statistics.total_cost?.toLocaleString()}</div>
          </div>
          <div className="stat-card highlight">
            <div className="stat-label">Potential Monthly Savings</div>
            <div className="stat-value">${statistics.potential_savings?.toLocaleString()}</div>
          </div>
        </div>
      )}

      {/* Charts Section */}
      <div className="charts-section">
        {/* Cost Trend Prediction Chart */}
        {cost_predictions && (
          <div className="chart-container">
            <h3>Cost Trend Prediction (Linear Regression Model)</h3>
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={costTrendData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e5e5e5" />
                <XAxis dataKey="month" stroke="#000000" />
                <YAxis stroke="#000000" />
                <Tooltip
                  contentStyle={{ background: '#ffffff', border: '2px solid #e5e5e5' }}
                  formatter={(value) => `$${value.toLocaleString()}`}
                />
                <Legend />
                <Line
                  type="monotone"
                  dataKey="cost"
                  stroke="#000000"
                  strokeWidth={3}
                  dot={{ fill: '#000000', r: 6 }}
                  name="Monthly Cost"
                />
              </LineChart>
            </ResponsiveContainer>
            <div className="chart-info">
              <div className="info-item">
                <span className="info-label">Growth Rate:</span>
                <span className="info-value">{cost_predictions.monthly_growth_rate?.toFixed(1)}% per month</span>
              </div>
              <div className="info-item">
                <span className="info-label">Trend:</span>
                <span className="info-value">{cost_predictions.trend === 'increasing' ? 'Increasing' : 'Decreasing'}</span>
              </div>
            </div>
          </div>
        )}

        {/* Before/After Optimization Chart */}
        {statistics && (
          <div className="chart-container">
            <h3>License Optimization Impact</h3>
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={optimizationData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e5e5e5" />
                <XAxis dataKey="category" stroke="#000000" />
                <YAxis stroke="#000000" />
                <Tooltip contentStyle={{ background: '#ffffff', border: '2px solid #e5e5e5' }} />
                <Legend />
                <Bar dataKey="Active with Licenses" stackId="a" fill="#000000" />
                <Bar dataKey="Inactive with Licenses" stackId="a" fill="#888888" />
                <Bar dataKey="Stale Users" stackId="a" fill="#cccccc" />
              </BarChart>
            </ResponsiveContainer>
            <div className="chart-info">
              <div className="info-item">
                <span className="info-label">Licenses to Remove:</span>
                <span className="info-value">{statistics.inactive_with_licenses + statistics.stale_licensed_users}</span>
              </div>
              <div className="info-item">
                <span className="info-label">Estimated Savings:</span>
                <span className="info-value">${statistics.potential_savings?.toLocaleString()}/month</span>
              </div>
            </div>
          </div>
        )}

        {/* User Status Breakdown */}
        {statistics && (
          <div className="chart-container small">
            <h3>User Status Distribution</h3>
            <ResponsiveContainer width="100%" height={250}>
              <PieChart>
                <Pie
                  data={userStatusData}
                  cx="50%"
                  cy="50%"
                  labelLine={false}
                  label={({ name, percent }) => `${name}: ${(percent * 100).toFixed(0)}%`}
                  outerRadius={80}
                  fill="#8884d8"
                  dataKey="value"
                >
                  {userStatusData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          </div>
        )}

        {/* License Usage Breakdown */}
        {statistics && (
          <div className="chart-container small">
            <h3>License Usage Distribution</h3>
            <ResponsiveContainer width="100%" height={250}>
              <PieChart>
                <Pie
                  data={licenseUsageData}
                  cx="50%"
                  cy="50%"
                  labelLine={false}
                  label={({ name, percent }) => `${name}: ${(percent * 100).toFixed(0)}%`}
                  outerRadius={80}
                  fill="#8884d8"
                  dataKey="value"
                >
                  {licenseUsageData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          </div>
        )}

        {/* Cost Breakdown: Current vs Optimized */}
        {statistics && (
          <div className="chart-container">
            <h3>Cost Analysis: Current vs After Optimization</h3>
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={[
                {
                  name: 'Current',
                  'Total Cost': statistics.total_cost,
                  'Wasted Cost': statistics.wasted_cost
                },
                {
                  name: 'After Optimization',
                  'Total Cost': statistics.total_cost - statistics.potential_savings,
                  'Wasted Cost': 0
                }
              ]}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e5e5e5" />
                <XAxis dataKey="name" stroke="#000000" />
                <YAxis stroke="#000000" />
                <Tooltip
                  contentStyle={{ background: '#ffffff', border: '2px solid #e5e5e5' }}
                  formatter={(value) => `$${value.toLocaleString()}`}
                />
                <Legend />
                <Bar dataKey="Total Cost" fill="#000000" />
                <Bar dataKey="Wasted Cost" fill="#cccccc" />
              </BarChart>
            </ResponsiveContainer>
            <div className="chart-info">
              <div className="info-item">
                <span className="info-label">Waste Reduction:</span>
                <span className="info-value">100% (${statistics.wasted_cost?.toLocaleString()} saved)</span>
              </div>
              <div className="info-item">
                <span className="info-label">Cost Efficiency Gain:</span>
                <span className="info-value">{((statistics.potential_savings / statistics.total_cost) * 100).toFixed(1)}%</span>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* AI Insights Sections */}
      {insightCategories && (
        <div className="insights-sections">
          {insightCategories.cost_optimization && insightCategories.cost_optimization.length > 0 && (
            <div className="insight-category">
              <h3>Cost Optimization Recommendations</h3>
              <ul className="insight-list">
                {insightCategories.cost_optimization.map((insight, idx) => (
                  <li key={idx} className="insight-item">
                    {insight}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {insightCategories.license_management && insightCategories.license_management.length > 0 && (
            <div className="insight-category">
              <h3>License Management Suggestions</h3>
              <ul className="insight-list">
                {insightCategories.license_management.map((insight, idx) => (
                  <li key={idx} className="insight-item">
                    {insight}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {insightCategories.risk_alerts && insightCategories.risk_alerts.length > 0 && (
            <div className="insight-category">
              <h3>Risk Alerts</h3>
              <ul className="insight-list">
                {insightCategories.risk_alerts.map((insight, idx) => (
                  <li key={idx} className="insight-item">
                    {insight}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {insightCategories.quick_wins && insightCategories.quick_wins.length > 0 && (
            <div className="insight-category">
              <h3>Quick Wins - Immediate Actions</h3>
              <ul className="insight-list">
                {insightCategories.quick_wins.map((insight, idx) => (
                  <li key={idx} className="insight-item">
                    {insight}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      {/* Key Metrics Summary */}
      {statistics && (
        <div className="metrics-summary">
          <h3>Key Metrics Summary</h3>
          <div className="summary-grid">
            <div className="summary-item">
              <span className="summary-label">Inactive users with licenses</span>
              <span className="summary-value">{statistics.inactive_with_licenses?.toLocaleString()}</span>
            </div>
            <div className="summary-item">
              <span className="summary-label">Stale licensed users (30+ days inactive)</span>
              <span className="summary-value">{statistics.stale_licensed_users?.toLocaleString()}</span>
            </div>
            <div className="summary-item">
              <span className="summary-label">Cost per active user</span>
              <span className="summary-value">${(statistics.total_cost / statistics.active_users).toFixed(2)}</span>
            </div>
            <div className="summary-item">
              <span className="summary-label">License utilization rate</span>
              <span className="summary-value">{((statistics.licensed_users / statistics.total_users) * 100).toFixed(1)}%</span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default AIInsights;
