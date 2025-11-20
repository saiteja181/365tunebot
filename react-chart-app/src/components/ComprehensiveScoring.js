import React, { useState, useEffect } from 'react';
import './ComprehensiveScoring.css';

const ComprehensiveScoring = () => {
  const [scoreData, setScoreData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [activeCategory, setActiveCategory] = useState('security');

  useEffect(() => {
    fetchScoringData();
  }, []);

  const fetchScoringData = async () => {
    try {
      setLoading(true);
      const response = await fetch('http://127.0.0.1:8000/api/scoring/comprehensive');
      const data = await response.json();

      if (data.success) {
        setScoreData(data);
        setError(null);
      } else {
        setError(data.error || 'Failed to fetch scoring data');
      }
    } catch (err) {
      setError('Error fetching scoring data: ' + err.message);
    } finally {
      setLoading(false);
    }
  };

  const getScoreColor = (score) => {
    // All scores now use black for consistency
    return '#000000';
  };

  const getMaturityColor = (level) => {
    // All maturity levels use grayscale
    return '#000000';
  };

  const renderOverallScore = () => {
    if (!scoreData) return null;

    const score = scoreData.overall_score;
    const maturity = scoreData.maturity_level;

    return (
      <div className="overall-score-section">
        <div className="score-card main-score">
          <div className="score-circle">
            <div className="score-value">{score.toFixed(1)}</div>
            <div className="score-label">Overall Score</div>
          </div>
          <div className="maturity-badge">
            <span className="maturity-level">Level {maturity.level}</span>
            <span className="maturity-name">{maturity.name}</span>
          </div>
          <p className="maturity-description">{maturity.description}</p>
        </div>

        <div className="summary-cards">
          <div className="summary-card">
            <div className="summary-value">{scoreData.summary.total_controls_assessed}</div>
            <div className="summary-label">Total Controls</div>
          </div>
          <div className="summary-card">
            <div className="summary-value">{scoreData.summary.total_controls_passing}</div>
            <div className="summary-label">Passing</div>
          </div>
          <div className="summary-card">
            <div className="summary-value">{scoreData.summary.critical_gaps_count}</div>
            <div className="summary-label">Critical Gaps</div>
          </div>
          <div className="summary-card">
            <div className="summary-value">{scoreData.summary.data_based_controls}</div>
            <div className="summary-label">From Database</div>
          </div>
          <div className="summary-card">
            <div className="summary-value">{scoreData.summary.controls_requiring_api}</div>
            <div className="summary-label">Require API</div>
          </div>
        </div>
      </div>
    );
  };

  const renderCategoryTabs = () => {
    if (!scoreData) return null;

    const categories = [
      { key: 'security', name: 'Security', weight: 35 },
      { key: 'compliance', name: 'Compliance', weight: 25 },
      { key: 'identity_management', name: 'Identity', weight: 15 },
      { key: 'collaboration', name: 'Collaboration', weight: 15 },
      { key: 'operations', name: 'Operations', weight: 10 }
    ];

    return (
      <div className="category-tabs">
        {categories.map(cat => {
          const catData = scoreData.categories[cat.key];
          const score = catData?.category_score || 0;

          return (
            <button
              key={cat.key}
              className={`category-tab ${activeCategory === cat.key ? 'active' : ''}`}
              onClick={() => setActiveCategory(cat.key)}
            >
              <div className="tab-name">{cat.name}</div>
              <div className="tab-score">{score.toFixed(1)}</div>
              <div className="tab-weight">{cat.weight}% weight</div>
            </button>
          );
        })}
      </div>
    );
  };

  const renderCategoryDetails = () => {
    if (!scoreData || !activeCategory) return null;

    const catData = scoreData.categories[activeCategory];
    if (!catData || catData.error) {
      return <div className="error-message">{catData?.error || 'Category data not available'}</div>;
    }

    const score = catData.category_score;

    return (
      <div className="category-details">
        <div className="category-header">
          <h3>{catData.category_name}</h3>
          <div className="category-score-box">
            <span className="cat-score">{score.toFixed(1)}</span>
            <span className="cat-weighted">Weighted: {catData.weighted_score.toFixed(2)}</span>
          </div>
        </div>

        <div className="category-progress">
          <div className="progress-bar">
            <div
              className="progress-fill"
              style={{ width: `${score}%` }}
            ></div>
          </div>
          <div className="progress-label">
            {catData.total_points_earned} / {catData.total_points_possible} points
          </div>
        </div>

        <div className="controls-list">
          <h4>Control Assessment</h4>
          {catData.controls.map((control, idx) => (
            <div key={idx} className={`control-item ${control.status.toLowerCase()}`}>
              <div className="control-header">
                <span className="control-name">{control.control}</span>
                <span className={`control-status ${control.status.toLowerCase()}`}>
                  {control.status}
                </span>
              </div>
              <div className="control-details">
                <span className="control-category">{control.category}</span>
                <span className="control-points">
                  {control.points_earned}/{control.points_possible} pts
                </span>
              </div>
              <div className="control-info">{control.details}</div>
              {control.recommendation && (
                <div className="control-recommendation">
                  <strong>Action:</strong> {control.recommendation}
                </div>
              )}
              {control.data_source === 'requires_api' && (
                <div className="control-api-notice">
                  <span className="api-badge">API Required</span>
                  Requires M365/Azure API integration
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    );
  };

  const renderCriticalGaps = () => {
    if (!scoreData || !scoreData.critical_gaps || scoreData.critical_gaps.length === 0) {
      return null;
    }

    return (
      <div className="critical-gaps-section">
        <h3 className="section-title">
          Critical Gaps - Immediate Action Required
        </h3>
        <div className="critical-gaps-list">
          {scoreData.critical_gaps.map((gap, idx) => (
            <div key={idx} className="critical-gap-card">
              <div className="gap-header">
                <span className="gap-control">{gap.control}</span>
                <span className="gap-points">{gap.points_possible} pts</span>
              </div>
              <div className="gap-category">{gap.category}</div>
              <div className="gap-details">{gap.details}</div>
              <div className="gap-recommendation">
                <strong>Immediate Action:</strong> {gap.recommendation}
              </div>
            </div>
          ))}
        </div>
      </div>
    );
  };

  const renderPriorityActions = () => {
    if (!scoreData || !scoreData.top_priority_actions || scoreData.top_priority_actions.length === 0) {
      return null;
    }

    return (
      <div className="priority-actions-section">
        <h3 className="section-title">Top Priority Actions</h3>
        <div className="priority-list">
          {scoreData.top_priority_actions.slice(0, 10).map((action, idx) => (
            <div key={idx} className={`priority-item priority-${action.priority.toLowerCase()}`}>
              <div className="priority-rank">{idx + 1}</div>
              <div className="priority-content">
                <div className="priority-header">
                  <span className="priority-control">{action.control}</span>
                  <span className={`priority-badge ${action.priority.toLowerCase()}`}>
                    {action.priority}
                  </span>
                </div>
                <div className="priority-category">{action.category}</div>
                <div className="priority-action">{action.action}</div>
                <div className="priority-impact">
                  <strong>Impact:</strong> {action.points_impact} points
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    );
  };

  const renderRoadmap = () => {
    if (!scoreData || !scoreData.implementation_roadmap) return null;

    const roadmap = scoreData.implementation_roadmap;

    return (
      <div className="roadmap-section">
        <h3 className="section-title">Implementation Roadmap</h3>
        <div className="roadmap-phases">
          <div className="roadmap-phase phase-1">
            <div className="phase-number">1</div>
            <div className="phase-content">
              <div className="phase-title">Immediate (Days 1-7)</div>
              <div className="phase-description">{roadmap.phase_1_immediate}</div>
            </div>
          </div>
          <div className="roadmap-phase phase-2">
            <div className="phase-number">2</div>
            <div className="phase-content">
              <div className="phase-title">Short-term (Weeks 2-4)</div>
              <div className="phase-description">{roadmap.phase_2_short_term}</div>
            </div>
          </div>
          <div className="roadmap-phase phase-3">
            <div className="phase-number">3</div>
            <div className="phase-content">
              <div className="phase-title">Medium-term (Months 2-3)</div>
              <div className="phase-description">{roadmap.phase_3_medium_term}</div>
            </div>
          </div>
          <div className="roadmap-phase phase-4">
            <div className="phase-number">4</div>
            <div className="phase-content">
              <div className="phase-title">Ongoing</div>
              <div className="phase-description">{roadmap.phase_4_ongoing}</div>
            </div>
          </div>
        </div>
      </div>
    );
  };

  if (loading) {
    return (
      <div className="comprehensive-scoring loading">
        <div className="spinner"></div>
        <p>Loading comprehensive security scoring...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="comprehensive-scoring error">
        <div className="error-box">
          <h3>Error Loading Scoring Data</h3>
          <p>{error}</p>
          <button onClick={fetchScoringData} className="retry-button">
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="comprehensive-scoring">
      <div className="scoring-header">
        <h1>Microsoft 365 Tenant Security & Compliance Score</h1>
        <p className="scoring-subtitle">
          Comprehensive assessment across Security, Compliance, Identity, Collaboration, and Operations
        </p>
        <button onClick={fetchScoringData} className="refresh-button">
          Refresh Score
        </button>
      </div>

      {renderOverallScore()}
      {renderCriticalGaps()}
      {renderCategoryTabs()}
      {renderCategoryDetails()}
      {renderPriorityActions()}
      {renderRoadmap()}

      <div className="scoring-footer">
        <p className="data-source-note">
          <strong>Data Sources:</strong> {scoreData?.summary.data_based_controls} controls assessed from database |
          {' '}{scoreData?.summary.controls_requiring_api} controls require M365/Azure API integration
        </p>
        <p className="timestamp">
          Generated at: {new Date(scoreData?.generated_at).toLocaleString()}
        </p>
      </div>
    </div>
  );
};

export default ComprehensiveScoring;
