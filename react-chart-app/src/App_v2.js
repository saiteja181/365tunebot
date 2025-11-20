import React, { useState } from 'react';
import Dashboard from './components/Dashboard';
import ChartCard from './components/ChartCard';
import ChatBot from './components/ChatBot';
import ComprehensiveScoring from './components/ComprehensiveScoring';
import EnhancedAIInsights from './components/EnhancedAIInsights';
import './App_v2.css';

function App() {
  const [activeTab, setActiveTab] = useState('dashboard');

  const renderContent = () => {
    switch (activeTab) {
      case 'dashboard':
        return (
          <>
            <Dashboard />
            <div className="charts-grid">
              <ChartCard
                chartType="countries"
                title="Top 10 Countries by User Count"
              />
              <ChartCard
                chartType="departments"
                title="Department Distribution"
              />
            </div>
          </>
        );

      case 'chat':
        return (
          <div className="chat-container">
            <div className="chat-header-info">
              <h2>💬 Smart Assistant</h2>
              <p>Ask questions in natural language. Get insights, recommendations, and cost optimizations automatically.</p>
            </div>
            <ChatBot />
          </div>
        );

      case 'analytics':
        return (
          <div className="analytics-hub">
            <h2 className="section-title">📊 Analytics Hub</h2>
            <p className="section-subtitle">
              Comprehensive security scoring and AI-powered insights for your Microsoft 365 environment
            </p>

            {/* Security Scoring Section */}
            <div className="analytics-section">
              <div className="section-header">
                <h3>🛡️ Security & Compliance Score</h3>
                <p>Real-time security posture analysis</p>
              </div>
              <ComprehensiveScoring />
            </div>

            {/* AI Insights Section */}
            <div className="analytics-section">
              <div className="section-header">
                <h3>💡 AI-Powered Insights</h3>
                <p>Intelligent recommendations and cost optimization opportunities</p>
              </div>
              <EnhancedAIInsights />
            </div>
          </div>
        );

      default:
        return null;
    }
  };

  return (
    <div className="app-container">
      {/* Top Navigation Bar */}
      <nav className="top-nav">
        <div className="nav-brand">
          <span className="brand-icon">🎯</span>
          <div className="brand-text">
            <h1>365 Tune Bot</h1>
            <p>Intelligent M365 Analytics</p>
          </div>
        </div>

        <div className="nav-tabs">
          <button
            className={`nav-tab ${activeTab === 'dashboard' ? 'active' : ''}`}
            onClick={() => setActiveTab('dashboard')}
          >
            <span className="tab-icon">📈</span>
            <span className="tab-label">Dashboard</span>
          </button>

          <button
            className={`nav-tab ${activeTab === 'chat' ? 'active' : ''}`}
            onClick={() => setActiveTab('chat')}
          >
            <span className="tab-icon">💬</span>
            <span className="tab-label">Smart Chat</span>
          </button>

          <button
            className={`nav-tab ${activeTab === 'analytics' ? 'active' : ''}`}
            onClick={() => setActiveTab('analytics')}
          >
            <span className="tab-icon">📊</span>
            <span className="tab-label">Analytics</span>
          </button>
        </div>
      </nav>

      {/* Main Content Area */}
      <main className="main-content">
        {renderContent()}
      </main>

      {/* Footer */}
      <footer className="app-footer">
        <div className="footer-content">
          <p>Powered by 365 Tune Bot • Real-time Microsoft 365 Analytics</p>
          <p className="footer-meta">AI-Enhanced • Secure • Actionable Insights</p>
        </div>
      </footer>
    </div>
  );
}

export default App;
