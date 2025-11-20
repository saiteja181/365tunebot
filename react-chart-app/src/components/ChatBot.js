import React, { useState, useRef, useEffect } from 'react';
import axios from 'axios';

// Typewriter component for bot messages
const TypewriterText = ({ text, onComplete, speed = 20 }) => {
  const [displayText, setDisplayText] = useState('');
  const [currentIndex, setCurrentIndex] = useState(0);
  const intervalRef = useRef(null);
  const onCompleteRef = useRef(onComplete);

  // Update the ref when onComplete changes
  useEffect(() => {
    onCompleteRef.current = onComplete;
  }, [onComplete]);

  useEffect(() => {
    if (!text) return;

    setDisplayText('');
    setCurrentIndex(0);

    intervalRef.current = setInterval(() => {
      setCurrentIndex(prevIndex => {
        if (prevIndex < text.length) {
          setDisplayText(text.slice(0, prevIndex + 1));
          return prevIndex + 1;
        } else {
          if (intervalRef.current) {
            clearInterval(intervalRef.current);
            intervalRef.current = null;
          }
          if (onCompleteRef.current) {
            onCompleteRef.current();
          }
          return prevIndex;
        }
      });
    }, speed);

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    };
  }, [text, speed]);

  return (
    <span style={{ minHeight: '1.5em', display: 'inline-block', width: '100%' }}>
      {displayText}
      {currentIndex < text.length && <span className="cursor">|</span>}
    </span>
  );
};

const API_BASE_URL = 'http://localhost:8000';

// Artifact view component for large datasets
const ArtifactView = ({ data, title, onDownload }) => {
  const totalRows = data.length;
  const columns = data.length > 0 ? Object.keys(data[0]) : [];

  const downloadCSV = () => {
    const headers = columns.join(',');
    const rows = data.map(row =>
      columns.map(col => `"${String(row[col] || '').replace(/"/g, '""')}"`).join(',')
    );
    const csvContent = [headers, ...rows].join('\n');

    const blob = new Blob([csvContent], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${title.replace(/[^a-zA-Z0-9]/g, '_')}.csv`;
    a.click();
    window.URL.revokeObjectURL(url);
  };

  return (
    <div className="artifact-view">
      <div className="artifact-header">
        <div className="artifact-info">
          <h4>Data Artifact</h4>
          <p>{totalRows.toLocaleString()} rows × {columns.length} columns</p>
        </div>
        <button className="download-btn" onClick={downloadCSV}>
          Download CSV
        </button>
      </div>

      <div className="artifact-preview">
        <h5>Preview (first 10 rows):</h5>
        <div className="preview-table-container">
          <table className="preview-table">
            <thead>
              <tr>
                {columns.map(col => (
                  <th key={col}>{col}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {data.slice(0, 10).map((row, idx) => (
                <tr key={idx}>
                  {columns.map(col => (
                    <td key={col}>{String(row[col] || '')}</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {totalRows > 10 && (
          <p className="preview-note">
            Showing 10 of {totalRows.toLocaleString()} rows. Download CSV for complete data.
          </p>
        )}
      </div>
    </div>
  );
};

// Animated Table Component for sidebar
const AnimatedTable = ({ data, onComplete }) => {
  const [visibleRows, setVisibleRows] = useState(0);
  const [isComplete, setIsComplete] = useState(false);

  useEffect(() => {
    if (!data || data.length === 0) {
      return;
    }

    setVisibleRows(0);
    setIsComplete(false);

    let currentRow = 0;
    const maxRows = Math.min(data.length, 50); // Limit to 50 rows for performance

    const interval = setInterval(() => {
      if (currentRow < maxRows) {
        currentRow++;
        setVisibleRows(currentRow);
      } else {
        setIsComplete(true);
        clearInterval(interval);
        if (onComplete) onComplete();
      }
    }, 100); // Show new row every 100ms

    return () => clearInterval(interval);
  }, [data, onComplete]);

  if (!data || data.length === 0) return null;

  const columns = Object.keys(data[0]);
  const displayData = data.slice(0, visibleRows);

  return (
    <div className="animated-table-container">
      <table className="data-table">
        <thead>
          <tr>
            {columns.map(key => (
              <th key={key}>{key}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {displayData.map((row, idx) => (
            <tr
              key={idx}
              className={idx === visibleRows - 1 && !isComplete ? "table-row-typing" : ""}
            >
              {Object.entries(row).map(([key, value]) => (
                <td key={key}>{value}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
      {!isComplete && visibleRows > 0 && (
        <div className="table-loading">
          <span className="table-cursor">|</span> Loading more rows...
        </div>
      )}
    </div>
  );
};

// Suggestion Chip component
const SuggestionChip = ({ suggestion, onClick, disabled }) => (
  <button
    className="suggestion-chip"
    onClick={() => onClick(suggestion)}
    disabled={disabled}
  >
    {suggestion}
  </button>
);

// Query classification for sidebar behavior
const classifyQuery = (userQuery) => {
  const query = userQuery.toLowerCase();

  // Queries that should NOT show sidebar (simple counts, yes/no answers)
  const simpleQueries = [
    'how many', 'count of', 'total number', 'do we have', 'is there',
    'are there', 'what is the count', 'how much total', 'what percentage'
  ];

  // Queries that should AUTO-CLOSE sidebar after showing briefly
  const briefShowQueries = [
    'who is', 'which department has the most', 'which country has the most',
    'top department', 'highest', 'lowest', 'most expensive', 'cheapest'
  ];

  // Queries that should ALWAYS show sidebar (detailed lists, analysis)
  const detailedQueries = [
    'show me', 'list', 'display', 'find users', 'breakdown', 'analysis',
    'by department', 'by country', 'activity', 'trends', 'details'
  ];

  if (simpleQueries.some(phrase => query.includes(phrase))) {
    return 'no-sidebar';
  } else if (briefShowQueries.some(phrase => query.includes(phrase))) {
    return 'brief-show';
  } else if (detailedQueries.some(phrase => query.includes(phrase))) {
    return 'show-sidebar';
  } else {
    // Default behavior based on result count
    return 'auto-decide';
  }
};

// Determine if results should be shown as artifact (for downloads/exports)
const shouldShowArtifact = (userQuery, results) => {
  const query = userQuery.toLowerCase();
  const artifactKeywords = ['export', 'download', 'csv', 'excel', 'report', 'full list', 'complete data'];

  return artifactKeywords.some(keyword => query.includes(keyword)) ||
         (results && results.length > 50); // Show artifact for large datasets
};

// Dynamic suggestions generator
const generateSuggestions = (userQuery, hasResults = false) => {
  const query = userQuery.toLowerCase();

  if (query.includes('user') && query.includes('india')) {
    return [
      "Show me users from other countries",
      "What departments do India users work in?",
      "How many active users are there in total?"
    ];
  } else if (query.includes('department')) {
    return [
      "Which department has the most users?",
      "Show me user activity by department",
      "What licenses do IT department users have?"
    ];
  } else if (query.includes('license')) {
    return [
      "Show me license utilization rates",
      "Which licenses are most expensive?",
      "How many unlicensed users do we have?"
    ];
  } else if (query.includes('country') || query.includes('countries')) {
    return [
      "Show me user distribution by country",
      "Which country has the most active users?",
      "What's the average activity per country?"
    ];
  } else if (query.includes('active')) {
    return [
      "Show me inactive users",
      "What makes a user active vs inactive?",
      "Show me user activity trends"
    ];
  }

  // Default suggestions
  return [
    "How many users do we have by country?",
    "Show me license costs by department",
    "Which users haven't signed in recently?"
  ];
};

const ChatBot = () => {
  const [messages, setMessages] = useState([
    {
      id: 1,
      type: 'bot',
      message: 'Hi! I\'m your 365 Tune Bot. Ask me questions about your Microsoft 365 data.',
      timestamp: new Date(),
      isTyping: false
    }
  ]);
  const [inputMessage, setInputMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [sessionId] = useState(() => `session_${Date.now()}_${Math.random()}`);
  const messagesEndRef = useRef(null);
  const [typingMessageId, setTypingMessageId] = useState(null);
  const [sidebarData, setSidebarData] = useState(null);
  const [sidebarTyping, setSidebarTyping] = useState(false);
  const [showInitialSuggestions, setShowInitialSuggestions] = useState(true);
  const [lastUserQuery, setLastUserQuery] = useState('');
  const [sidebarBehavior, setSidebarBehavior] = useState('auto-decide');
  const [showArtifact, setShowArtifact] = useState(false);
  const [autoCloseTimer, setAutoCloseTimer] = useState(null);

  const handleTypingComplete = useRef((messageId) => {
    setTypingMessageId(null);
    setMessages(prev =>
      prev.map(msg =>
        msg.id === messageId ? { ...msg, isTyping: false } : msg
      )
    );

    // Start sidebar table animation after text typing completes
    if (sidebarData && sidebarData.data && sidebarData.data.length > 0) {
      setTimeout(() => {
        setSidebarTyping(true); // This will trigger the AnimatedTable animation
      }, 300); // Small delay before table starts animating
    }
  });

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const sendMessage = async (messageToSend = null) => {
    const actualMessage = messageToSend || inputMessage;
    if (!actualMessage.trim() || isLoading) return;

    setInputMessage('');
    setIsLoading(true);
    setShowInitialSuggestions(false); // Hide initial suggestions after first query
    setLastUserQuery(actualMessage);

    // Add user message to chat
    const userMessage = {
      id: Date.now(),
      type: 'user',
      message: actualMessage,
      timestamp: new Date()
    };
    setMessages(prev => [...prev, userMessage]);

    try {
      const response = await axios.post(`${API_BASE_URL}/api/chat`, {
        message: actualMessage,
        session_id: sessionId
      });

      // Format bot message
      let botText = response.data.message;
      let allResults = response.data.results || [];
      let resultCount = response.data.result_count || allResults.length;

      // Intelligent sidebar behavior based on query type
      const queryClassification = classifyQuery(actualMessage);
      const shouldShowArtifactResult = shouldShowArtifact(actualMessage, allResults);

      if (allResults.length > 0) {
        // Determine if sidebar should be shown based on query classification
        const shouldShowSidebar =
          queryClassification === 'show-sidebar' ||
          (queryClassification === 'auto-decide' && allResults.length <= 10) ||
          (queryClassification === 'brief-show');

        if (shouldShowSidebar || shouldShowArtifactResult) {
          setSidebarData({
            title: `Query Results (${resultCount} records)`,
            data: allResults,
            query: actualMessage,
            behavior: queryClassification,
            showArtifact: shouldShowArtifactResult
          });
          setSidebarBehavior(queryClassification);
          setShowArtifact(shouldShowArtifactResult);
          setSidebarTyping(false);

          // Auto-close for brief show queries
          if (queryClassification === 'brief-show') {
            const timer = setTimeout(() => {
              setSidebarData(null);
              setShowArtifact(false);
            }, 5000); // Auto-close after 5 seconds
            setAutoCloseTimer(timer);
          }
        } else {
          setSidebarData(null); // Don't show sidebar for simple queries
        }
      } else {
        setSidebarData(null); // Clear sidebar if no results
        setShowArtifact(false);
      }

      if (!botText || botText.trim() === "") {
        botText = "Sorry, I couldn't process your request at the moment.";
      }

      const botMessage = {
        id: Date.now() + 1,
        type: 'bot',
        message: botText,
        timestamp: new Date(),
        processing_time: response.data.processing_time,
        result_count: resultCount,
        success: response.data.success,
        isTyping: true,
        suggestions: generateSuggestions(actualMessage, allResults.length > 0)
      };

      setMessages(prev => [...prev, botMessage]);
      setTypingMessageId(botMessage.id);
    } catch (error) {
      const errorMessage = {
        id: Date.now() + 1,
        type: 'bot',
        message: `Sorry, I encountered an error: ${error.message}`,
        timestamp: new Date(),
        success: false,
        isTyping: true,
        suggestions: ["Try asking a different question", "Check your connection", "Rephrase your query"]
      };
      setMessages(prev => [...prev, errorMessage]);
      setTypingMessageId(errorMessage.id);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  const formatTime = (timestamp) => {
    return timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  };

  const initialSuggestions = [
    "How many users do we have?",
    "Show me users from India",
    "Find users in the IT department",
    "How many active users do we have?",
    "Which countries have the most users?"
  ];

  return (
    <div className="claude-chatbot">
      {/* Sidebar for tables/data */}
      <div className={`sidebar ${sidebarData ? 'open' : ''}`}>
        {sidebarData && (
          <>
            <div className="sidebar-header">
              <div className="sidebar-title-area">
                <h3>{sidebarData.title}</h3>
                {sidebarData.behavior === 'brief-show' && (
                  <span className="auto-close-indicator">Auto-closing in 5s</span>
                )}
              </div>
              <div className="sidebar-controls">
                {sidebarData.showArtifact && (
                  <button
                    className="artifact-toggle"
                    onClick={() => setShowArtifact(!showArtifact)}
                    title={showArtifact ? "Show table view" : "Show artifact view"}
                  >
                    {showArtifact ? "📊" : "📋"}
                  </button>
                )}
                <button
                  className="close-sidebar"
                  onClick={() => {
                    setSidebarData(null);
                    setSidebarTyping(false);
                    setShowArtifact(false);
                    if (autoCloseTimer) {
                      clearTimeout(autoCloseTimer);
                      setAutoCloseTimer(null);
                    }
                  }}
                >
                  ×
                </button>
              </div>
            </div>
            <div className="sidebar-content">
              {showArtifact ? (
                <ArtifactView
                  data={sidebarData.data}
                  title={sidebarData.title}
                />
              ) : (
                <div className="data-table-container">
                  {sidebarData.data && sidebarData.data.length > 0 && (
                    <AnimatedTable
                      key={`${sidebarData.query}-${sidebarData.data.length}`}
                      data={sidebarData.data}
                      onComplete={() => setSidebarTyping(false)}
                    />
                  )}
                </div>
              )}
            </div>
          </>
        )}
      </div>

      {/* Main chat area */}
      <div className="chat-main">
        <div className="chat-header">
          <div className="header-content">
            <h1>365 Tune Bot</h1>
            <p>Your intelligent Microsoft 365 data assistant</p>
          </div>
        </div>

        {/* Initial suggestions (shown only before first query) */}
        {showInitialSuggestions && (
          <div className="initial-suggestions">
            <p className="suggestions-label">Try asking:</p>
            <div className="suggestions-grid">
              {initialSuggestions.map((suggestion, index) => (
                <SuggestionChip
                  key={index}
                  suggestion={suggestion}
                  onClick={sendMessage}
                  disabled={isLoading}
                />
              ))}
            </div>
          </div>
        )}

        {/* Chat messages */}
        <div className="chat-messages">
          {messages.map((message) => (
            <div key={message.id} className={`message-wrapper ${message.type}`}>
              <div className="message-content">
                <div className="message-bubble">
                  {message.type === 'bot' && message.isTyping ? (
                    <TypewriterText
                      key={message.id}
                      text={message.message}
                      onComplete={() => handleTypingComplete.current(message.id)}
                      speed={20}
                    />
                  ) : (
                    <div className="message-text" style={{ minHeight: '1.5em' }}>
                      {message.message}
                    </div>
                  )}
                </div>

                {/* Processing time (only after typing) */}
                {message.processing_time && !message.isTyping && (
                  <div className="message-meta">
                    {message.processing_time.toFixed(2)}s
                    {message.result_count > 0 && (
                      <span> • {message.result_count.toLocaleString()} results</span>
                    )}
                  </div>
                )}

                {/* Dynamic suggestions after each bot response */}
                {message.type === 'bot' && message.suggestions && !message.isTyping && (
                  <div className="response-suggestions">
                    <div className="suggestions-container">
                      {message.suggestions.map((suggestion, index) => (
                        <SuggestionChip
                          key={index}
                          suggestion={suggestion}
                          onClick={sendMessage}
                          disabled={isLoading}
                        />
                      ))}
                    </div>
                  </div>
                )}
              </div>
              <div className="message-time">
                {formatTime(message.timestamp)}
              </div>
            </div>
          ))}

          {/* Loading indicator */}
          {isLoading && (
            <div className="message-wrapper bot">
              <div className="message-content">
                <div className="message-bubble loading">
                  <div className="typing-indicator">
                    <span></span>
                    <span></span>
                    <span></span>
                  </div>
                  Processing...
                </div>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Input area */}
        <div className="chat-input-area">
          <div className="input-container">
            <textarea
              value={inputMessage}
              onChange={(e) => setInputMessage(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder="Message 365 Tune Bot..."
              disabled={isLoading}
              className="chat-input"
              rows="1"
            />
            <button
              onClick={() => sendMessage()}
              disabled={!inputMessage.trim() || isLoading}
              className="send-button"
            >
              <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
                <path d="M14.5 1L7 8.5L14.5 1ZM14.5 1L9.5 15L7 8.5L14.5 1Z" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ChatBot;