import React, { useState } from 'react';
import Dashboard from './components/Dashboard';
import ChartCard from './components/ChartCard';
import ChatBot from './components/ChatBot';
import LicenseMetrics from './components/LicenseMetrics';
import AIInsights from './components/AIInsights';
import EnhancedAIInsights from './components/EnhancedAIInsights';
import ComprehensiveScoring from './components/ComprehensiveScoring';

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
      case 'scoring':
        return <ComprehensiveScoring />;
      case 'insights':
        return <AIInsights />;
      case 'enhanced-insights':
        return <EnhancedAIInsights />;
      case 'chat':
        return <ChatBot />;
      case 'licenses':
        return <LicenseMetrics />;
      default:
        return null;
    }
  };

  return (
    <div className="container">
      <div className="header">
        <h1>365 Tune Bot - Analytics Dashboard</h1>
        <p>Your intelligent Microsoft 365 data assistant with comprehensive analytics</p>
        
        {/* Navigation Tabs */}
        <div className="nav-tabs">
          <button
            className={`nav-tab ${activeTab === 'dashboard' ? 'active' : ''}`}
            onClick={() => setActiveTab('dashboard')}
          >
            Dashboard
          </button>
          <button
            className={`nav-tab ${activeTab === 'scoring' ? 'active' : ''}`}
            onClick={() => setActiveTab('scoring')}
          >
            Security Score
          </button>
          <button
            className={`nav-tab ${activeTab === 'enhanced-insights' ? 'active' : ''}`}
            onClick={() => setActiveTab('enhanced-insights')}
          >
            Enhanced AI Insights
          </button>
          <button
            className={`nav-tab ${activeTab === 'insights' ? 'active' : ''}`}
            onClick={() => setActiveTab('insights')}
          >
            Basic Insights
          </button>
          <button
            className={`nav-tab ${activeTab === 'chat' ? 'active' : ''}`}
            onClick={() => setActiveTab('chat')}
          >
            Chat Bot
          </button>
          <button
            className={`nav-tab ${activeTab === 'licenses' ? 'active' : ''}`}
            onClick={() => setActiveTab('licenses')}
          >
            License Analytics
          </button>
        </div>
      </div>
      
      {renderContent()}
      
      {/* Footer */}
      <div className="footer">
        <p>Powered by 365 Tune Bot FastAPI Service • Real-time Microsoft 365 Analytics</p>
      </div>
    </div>
  );
}

export default App;