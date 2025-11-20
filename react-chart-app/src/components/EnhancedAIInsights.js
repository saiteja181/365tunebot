import React, { useState, useEffect } from 'react';
import {
  BarChart, Bar, LineChart, Line, PieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend,
  ResponsiveContainer, AreaChart, Area, RadarChart,
  PolarGrid, PolarAngleAxis, PolarRadiusAxis, Radar
} from 'recharts';
import './EnhancedAIInsights.css';

const EnhancedAIInsights = () => {
  const [insights, setInsights] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedRecommendation, setSelectedRecommendation] = useState(null);
  const [expandedRecommendations, setExpandedRecommendations] = useState(new Set());

  useEffect(() => {
    fetchInsights();
  }, []);

  const fetchInsights = async () => {
    try {
      setLoading(true);
      const response = await fetch('http://127.0.0.1:8000/api/insights/enhanced');
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

  const exportToJSON = () => {
    if (!insights) return;
    const dataStr = JSON.stringify(insights, null, 2);
    const dataBlob = new Blob([dataStr], { type: 'application/json' });
    const url = URL.createObjectURL(dataBlob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `ai-insights-${new Date().toISOString().split('T')[0]}.json`;
    link.click();
  };

  const exportToCSV = () => {
    if (!insights || !insights.recommendations) return;

    const headers = ['Priority', 'Category', 'Title', 'Monthly Savings', 'Annual Savings', 'Affected Users', 'Effort', 'Time'];
    const rows = insights.recommendations.map(rec => [
      rec.priority,
      rec.category,
      rec.title,
      `$${rec.monthly_savings?.toFixed(2) || 0}`,
      `$${rec.annual_savings?.toFixed(2) || 0}`,
      rec.affected_users,
      rec.effort,
      rec.implementation_time
    ]);

    const csvContent = [
      headers.join(','),
      ...rows.map(row => row.map(cell => `"${cell}"`).join(','))
    ].join('\n');

    const blob = new Blob([csvContent], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `recommendations-${new Date().toISOString().split('T')[0]}.csv`;
    link.click();
  };

  const toggleRecommendation = (id) => {
    const newExpanded = new Set(expandedRecommendations);
    if (newExpanded.has(id)) {
      newExpanded.delete(id);
    } else {
      newExpanded.add(id);
    }
    setExpandedRecommendations(newExpanded);
  };

  const getSeverityColor = (severity) => {
    const colors = {
      'HIGH': '#000000',
      'CRITICAL': '#000000',
      'MEDIUM': '#666666',
      'LOW': '#999999'
    };
    return colors[severity] || '#000000';
  };

  const getPriorityColor = (priority) => {
    const colors = {
      'CRITICAL': '#000000',
      'HIGH': '#333333',
      'MEDIUM': '#666666',
      'LOW': '#999999'
    };
    return colors[priority] || '#000000';
  };

  if (loading) {
    return (
      <div className="enhanced-insights-container">
        <div className="insights-header">
          <h2>Enhanced AI Insights</h2>
        </div>
        <div className="loading-spinner">Analyzing your data with advanced AI...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="enhanced-insights-container">
        <div className="insights-header">
          <h2>Enhanced AI Insights</h2>
          <button onClick={fetchInsights} className="action-btn">
            Refresh
          </button>
        </div>
        <div className="error-message">{error}</div>
      </div>
    );
  }

  const { executive_summary, statistics, anomalies, recommendations, predictions, charts_data } = insights || {};

  // Prepare cost scenario data
  const costScenarioData = predictions?.current_trajectory?.map((item, idx) => ({
    month: item.label,
    'Current Trajectory': item.cost,
    'After Optimization': predictions.optimized_trajectory[idx]?.cost,
    'Best Case': predictions.best_case_trajectory[idx]?.cost
  })) || [];

  // Prepare savings breakdown data
  const savingsBreakdownData = [
    {
      category: 'Inactive Users',
      amount: statistics?.inactive_users_cost || 0,
      users: statistics?.inactive_licensed_users || 0
    },
    {
      category: 'Stale Users (30+ days)',
      amount: statistics?.stale_users_cost || 0,
      users: statistics?.stale_licensed_users || 0
    },
    {
      category: 'Never Signed In',
      amount: statistics?.never_signed_in_cost || 0,
      users: statistics?.never_signed_in_licensed || 0
    }
  ];

  // Prepare license health radar data
  const licenseHealthData = [
    {
      metric: 'Utilization',
      value: statistics?.license_utilization || 0,
      fullMark: 100
    },
    {
      metric: 'Active Ratio',
      value: statistics?.total_users > 0 ? (statistics.active_users / statistics.total_users) * 100 : 0,
      fullMark: 100
    },
    {
      metric: 'Licensed Ratio',
      value: statistics?.total_users > 0 ? (statistics.licensed_users / statistics.total_users) * 100 : 0,
      fullMark: 100
    },
    {
      metric: 'Efficiency',
      value: statistics?.total_monthly_cost > 0 ? 100 - ((statistics.potential_monthly_savings / statistics.total_monthly_cost) * 100) : 0,
      fullMark: 100
    }
  ];

  return (
    <div className="enhanced-insights-container">
      {/* Header */}
      <div className="insights-header">
        <div className="header-content">
          <h2>Enhanced AI Insights</h2>
          <p className="header-subtitle">Advanced Analytics & Recommendations</p>
        </div>
        <div className="header-actions">
          <button onClick={exportToJSON} className="action-btn secondary">
            Export JSON
          </button>
          <button onClick={exportToCSV} className="action-btn secondary">
            Export CSV
          </button>
          <button onClick={fetchInsights} className="action-btn primary">
            Refresh Analysis
          </button>
        </div>
      </div>

      {/* Executive Summary */}
      {executive_summary && (
        <div className="executive-summary">
          <h3>Executive Summary</h3>
          <p className="summary-text">{executive_summary}</p>
        </div>
      )}

      {/* Key Metrics Dashboard */}
      {statistics && (
        <div className="metrics-grid">
          <div className="metric-card primary">
            <div className="metric-label">Monthly Cost</div>
            <div className="metric-value">${statistics.total_monthly_cost?.toLocaleString()}</div>
            <div className="metric-sub">${(statistics.total_annual_cost || 0)?.toLocaleString()}/year</div>
          </div>
          <div className="metric-card success">
            <div className="metric-label">Potential Monthly Savings</div>
            <div className="metric-value">${statistics.potential_monthly_savings?.toLocaleString()}</div>
            <div className="metric-sub">{predictions?.savings_percentage?.toFixed(1)}% reduction</div>
          </div>
          <div className="metric-card warning">
            <div className="metric-label">Anomalies Detected</div>
            <div className="metric-value">{anomalies?.length || 0}</div>
            <div className="metric-sub">{recommendations?.length || 0} recommendations</div>
          </div>
          <div className="metric-card info">
            <div className="metric-label">License Utilization</div>
            <div className="metric-value">{statistics.license_utilization?.toFixed(1)}%</div>
            <div className="metric-sub">Overall efficiency</div>
          </div>
        </div>
      )}

      {/* Anomaly Alerts */}
      {anomalies && anomalies.length > 0 && (
        <div className="anomalies-section">
          <h3>Anomaly Detection Alerts</h3>
          <div className="anomalies-grid">
            {anomalies.map((anomaly, idx) => (
              <div
                key={idx}
                className={`anomaly-card severity-${anomaly.severity.toLowerCase()}`}
                style={{ borderLeftColor: getSeverityColor(anomaly.severity) }}
              >
                <div className="anomaly-header">
                  <span className="anomaly-type">{anomaly.type.replace(/_/g, ' ')}</span>
                  <span className={`severity-badge ${anomaly.severity.toLowerCase()}`}>
                    {anomaly.severity}
                  </span>
                </div>
                <div className="anomaly-description">{anomaly.description}</div>
                <div className="anomaly-metrics">
                  <div className="anomaly-metric">
                    <span className="metric-label">Current:</span>
                    <span className="metric-value">{anomaly.metric}</span>
                  </div>
                  <div className="anomaly-metric">
                    <span className="metric-label">Threshold:</span>
                    <span className="metric-value">{anomaly.threshold}</span>
                  </div>
                  {anomaly.impact_cost && (
                    <div className="anomaly-metric">
                      <span className="metric-label">Impact:</span>
                      <span className="metric-value">${anomaly.impact_cost?.toLocaleString()}/mo</span>
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Cost Scenario Analysis */}
      {predictions && (
        <div className="chart-section">
          <h3>Cost Projection Scenarios (6-Month Forecast)</h3>
          <ResponsiveContainer width="100%" height={350}>
            <AreaChart data={costScenarioData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e5e5e5" />
              <XAxis dataKey="month" stroke="#000000" />
              <YAxis stroke="#000000" tickFormatter={(value) => `$${(value/1000).toFixed(0)}k`} />
              <Tooltip
                contentStyle={{ background: '#ffffff', border: '2px solid #e5e5e5' }}
                formatter={(value) => `$${value?.toLocaleString()}`}
              />
              <Legend />
              <Area
                type="monotone"
                dataKey="Current Trajectory"
                stackId="1"
                stroke="#cccccc"
                fill="#cccccc"
                fillOpacity={0.6}
              />
              <Area
                type="monotone"
                dataKey="After Optimization"
                stackId="2"
                stroke="#666666"
                fill="#666666"
                fillOpacity={0.6}
              />
              <Area
                type="monotone"
                dataKey="Best Case"
                stackId="3"
                stroke="#000000"
                fill="#000000"
                fillOpacity={0.6}
              />
            </AreaChart>
          </ResponsiveContainer>
          <div className="chart-insights">
            <div className="insight-item">
              <strong>Current Trajectory:</strong> ${predictions.current_trajectory?.[6]?.cost?.toLocaleString()} in 6 months
            </div>
            <div className="insight-item">
              <strong>After Optimization:</strong> ${predictions.optimized_trajectory?.[6]?.cost?.toLocaleString()} (Save ${predictions.monthly_savings_optimized?.toLocaleString()}/mo)
            </div>
            <div className="insight-item">
              <strong>Best Case:</strong> ${predictions.best_case_trajectory?.[6]?.cost?.toLocaleString()} (Save ${predictions.monthly_savings_best_case?.toLocaleString()}/mo)
            </div>
          </div>
        </div>
      )}

      {/* Savings Breakdown */}
      <div className="chart-section">
        <h3>Savings Opportunities Breakdown</h3>
        <ResponsiveContainer width="100%" height={300}>
          <BarChart data={savingsBreakdownData}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e5e5e5" />
            <XAxis dataKey="category" stroke="#000000" />
            <YAxis stroke="#000000" />
            <Tooltip
              contentStyle={{ background: '#ffffff', border: '2px solid #e5e5e5' }}
              formatter={(value, name) => {
                if (name === 'amount') return `$${value?.toLocaleString()}`;
                return value;
              }}
            />
            <Legend />
            <Bar dataKey="amount" fill="#000000" name="Monthly Cost" />
            <Bar dataKey="users" fill="#666666" name="Affected Users" />
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* License Health Radar */}
      <div className="chart-section">
        <h3>License Health Score</h3>
        <ResponsiveContainer width="100%" height={350}>
          <RadarChart data={licenseHealthData}>
            <PolarGrid stroke="#e5e5e5" />
            <PolarAngleAxis dataKey="metric" stroke="#000000" />
            <PolarRadiusAxis stroke="#666666" />
            <Radar
              name="Score"
              dataKey="value"
              stroke="#000000"
              fill="#000000"
              fillOpacity={0.3}
            />
            <Tooltip formatter={(value) => `${value?.toFixed(1)}%`} />
          </RadarChart>
        </ResponsiveContainer>
        <div className="health-score-legend">
          <div>100% = Optimal</div>
          <div>70-99% = Good</div>
          <div>50-69% = Needs Attention</div>
          <div>&lt;50% = Critical</div>
        </div>
      </div>

      {/* Prioritized Recommendations */}
      {recommendations && recommendations.length > 0 && (
        <div className="recommendations-section">
          <h3>Prioritized Recommendations</h3>
          <div className="recommendations-list">
            {recommendations.map((rec) => {
              const isExpanded = expandedRecommendations.has(rec.id);
              return (
                <div
                  key={rec.id}
                  className={`recommendation-card priority-${rec.priority.toLowerCase()}`}
                  style={{ borderLeftColor: getPriorityColor(rec.priority) }}
                >
                  <div className="rec-header" onClick={() => toggleRecommendation(rec.id)}>
                    <div className="rec-title-section">
                      <span className={`priority-badge ${rec.priority.toLowerCase()}`}>
                        {rec.priority}
                      </span>
                      <h4>{rec.title}</h4>
                      <span className="impact-score">Impact Score: {rec.impact_score}/10</span>
                    </div>
                    <div className="expand-icon">{isExpanded ? '−' : '+'}</div>
                  </div>

                  <div className="rec-description">{rec.description}</div>

                  <div className="rec-metrics">
                    <div className="rec-metric">
                      <div className="metric-label">Monthly Savings</div>
                      <div className="metric-value">
                        {rec.monthly_savings ? `$${rec.monthly_savings.toLocaleString()}` : 'TBD'}
                      </div>
                    </div>
                    <div className="rec-metric">
                      <div className="metric-label">Annual Savings</div>
                      <div className="metric-value">
                        {rec.annual_savings ? `$${rec.annual_savings.toLocaleString()}` : 'TBD'}
                      </div>
                    </div>
                    <div className="rec-metric">
                      <div className="metric-label">ROI</div>
                      <div className="metric-value">
                        {rec.roi_percentage ? `${rec.roi_percentage.toFixed(1)}%` : 'N/A'}
                      </div>
                    </div>
                    <div className="rec-metric">
                      <div className="metric-label">Affected Users</div>
                      <div className="metric-value">{rec.affected_users?.toLocaleString()}</div>
                    </div>
                  </div>

                  {isExpanded && (
                    <div className="rec-details">
                      <div className="rec-implementation">
                        <div className="implementation-info">
                          <span className="info-label">Effort:</span>
                          <span className="info-value">{rec.effort}</span>
                        </div>
                        <div className="implementation-info">
                          <span className="info-label">Time Required:</span>
                          <span className="info-value">{rec.implementation_time}</span>
                        </div>
                      </div>

                      {rec.action_steps && rec.action_steps.length > 0 && (
                        <div className="action-steps">
                          <h5>Action Steps:</h5>
                          <ol>
                            {rec.action_steps.map((step, idx) => (
                              <li key={idx}>{step}</li>
                            ))}
                          </ol>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Detailed Statistics */}
      {statistics && (
        <div className="detailed-stats">
          <h3>Detailed Statistics</h3>
          <div className="stats-grid">
            <div className="stat-item">
              <span className="stat-label">Total Users</span>
              <span className="stat-value">{statistics.total_users?.toLocaleString()}</span>
            </div>
            <div className="stat-item">
              <span className="stat-label">Active Users</span>
              <span className="stat-value">{statistics.active_users?.toLocaleString()}</span>
            </div>
            <div className="stat-item">
              <span className="stat-label">Licensed Users</span>
              <span className="stat-value">{statistics.licensed_users?.toLocaleString()}</span>
            </div>
            <div className="stat-item">
              <span className="stat-label">Inactive Licensed Users</span>
              <span className="stat-value">{statistics.inactive_licensed_users?.toLocaleString()}</span>
            </div>
            <div className="stat-item">
              <span className="stat-label">Stale Users (30+ days)</span>
              <span className="stat-value">{statistics.stale_licensed_users?.toLocaleString()}</span>
            </div>
            <div className="stat-item">
              <span className="stat-label">Never Signed In</span>
              <span className="stat-value">{statistics.never_signed_in_licensed?.toLocaleString()}</span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default EnhancedAIInsights;
