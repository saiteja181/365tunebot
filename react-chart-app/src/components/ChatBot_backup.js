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
    <span>
      {displayText}
      {currentIndex < text.length && <span className="cursor">|</span>}
    </span>
  );
};

const API_BASE_URL = 'http://localhost:8000';

// Show More Results Button component
function ShowMoreResultsButton({ message }) {
  const [expanded, setExpanded] = useState(false);
  if (!message) return null;
  if (!expanded) {
    return (
      <button className="show-more-btn" style={{ marginTop: '1em' }} onClick={() => setExpanded(true)}>
        Show More Results
      </button>
    );
  }
  // Show all results in a table
  return (
    <div className="chatbot-table-preview" style={{ marginTop: '1em', overflowX: 'auto' }}>
      <table style={{ borderCollapse: 'collapse', width: '100%' }}>
        <thead>
          <tr>
            {message.previewTable.columns.map(col => (
              <th key={col} style={{ border: '1px solid #ccc', padding: '4px', background: '#f5f5f5' }}>{col}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {message.allResults.map((row, i) => (
            <tr key={i}>
              {message.previewTable.columns.map(col => (
                <td key={col} style={{ border: '1px solid #eee', padding: '4px' }}>{row[col]}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
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

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const sendMessage = async () => {
    if (!inputMessage.trim() || isLoading) return;

    const messageToSend = inputMessage;
    setInputMessage('');
    setIsLoading(true);

    // Add user message to chat
    const userMessage = {
      id: Date.now(),
      type: 'user',
      message: messageToSend,
      timestamp: new Date()
    };
    setMessages(prev => [...prev, userMessage]);

    try {
      const response = await axios.post(`${API_BASE_URL}/api/chat`, {
        message: messageToSend,
        session_id: sessionId
      });

      // Format a more conversational bot message
      let botText = response.data.message;
      let previewTable = null;
      let showMore = false;
      let allResults = response.data.results || [];
      let resultCount = response.data.result_count || allResults.length;

      // If more than 20 results, show only 20 and enable 'Show More'
      if (resultCount > 20) {
        showMore = true;
      }

      // Prepare table preview (up to 20 rows or all if less)
      const displayResults = showMore ? allResults.slice(0, 20) : allResults;
      if (displayResults.length > 0) {
        const columns = Object.keys(displayResults[0]);
        previewTable = { columns, rows: displayResults };
      }

      // Only use fallback if botText is truly empty
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
        previewTable: previewTable,
        showMore: showMore,
        allResults: allResults,
        isTyping: true
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
        isTyping: true
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

  const sampleQuestions = [
    "How many users do we have?",
    "Show me users from India",
    "Find users in the IT department",
    "How many active users do we have?",
    "Which countries have the most users?"
  ];

  const handleSampleQuestion = (question) => {
    setInputMessage(question);
  };

  const handleTypingComplete = useRef((messageId) => {
    setTypingMessageId(null);
    setMessages(prev =>
      prev.map(msg =>
        msg.id === messageId ? { ...msg, isTyping: false } : msg
      )
    );
  });

  return (
    <div className="chatbot">
      <div className="chatbot-header">
        <h3>365 Tune Bot Chat</h3>
        <p>Ask questions about your Microsoft 365 data in natural language</p>
      </div>

      <div className="sample-questions">
        <h4>Try these sample questions:</h4>
        <div className="sample-questions-grid">
          {sampleQuestions.map((question, index) => (
            <button
              key={index}
              className="sample-question-btn"
              onClick={() => handleSampleQuestion(question)}
              disabled={isLoading}
            >
              {question}
            </button>
          ))}
        </div>
      </div>

      <div className="chat-messages">
        {messages.map((message, idx) => (
          <div key={message.id} className={`message ${message.type}`}>
            <div className="message-content">
              <div className="message-text">
                {message.type === 'bot' && message.isTyping ? (
                  <TypewriterText
                    key={message.id}
                    text={message.message}
                    onComplete={() => handleTypingComplete.current(message.id)}
                    speed={20}
                  />
                ) : (
                  message.message
                )}
                {/* Show preview table if available and typing is complete */}
                {message.previewTable && !message.isTyping && (
                  <div className="chatbot-table-preview" style={{ marginTop: '1em', overflowX: 'auto' }}>
                    <table style={{ borderCollapse: 'collapse', width: '100%' }}>
                      <thead>
                        <tr>
                          {message.previewTable.columns.map(col => (
                            <th key={col} style={{ border: '1px solid #ccc', padding: '4px', background: '#f5f5f5' }}>{col}</th>
                          ))}
                        </tr>
                      </thead>
                      <tbody>
                        {message.previewTable.rows.map((row, i) => (
                          <tr key={i}>
                            {message.previewTable.columns.map(col => (
                              <td key={col} style={{ border: '1px solid #eee', padding: '4px' }}>{row[col]}</td>
                            ))}
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
                {/* Show More button if needed and typing is complete */}
                {message.showMore && !message.isTyping && (
                  <ShowMoreResultsButton message={message} />
                )}
              </div>
              {message.processing_time && !message.isTyping && (
                <div className="message-meta">
                  Processed in {message.processing_time.toFixed(2)}s
                  {message.result_count !== undefined && message.result_count > 0 && (
                    <span> • Found {message.result_count.toLocaleString()} results</span>
                  )}
                </div>
              )}
            </div>
            <div className="message-time">
              {formatTime(message.timestamp)}
            </div>
          </div>
        ))}
        
        {isLoading && (
          <div className="message bot">
            <div className="message-content">
              <div className="message-text">
                <div className="typing-indicator">
                  <span></span>
                  <span></span>
                  <span></span>
                </div>
                Processing your query...
              </div>
            </div>
          </div>
        )}
        
        <div ref={messagesEndRef} />
      </div>

      <div className="chat-input-container">
        <div className="chat-input">
          <textarea
            value={inputMessage}
            onChange={(e) => setInputMessage(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder="Ask me anything about your Microsoft 365 data..."
            disabled={isLoading}
            rows="2"
          />
          <button 
            onClick={sendMessage} 
            disabled={!inputMessage.trim() || isLoading}
            className="send-btn"
          >
            {isLoading ? 'Sending...' : 'Send'}
          </button>
        </div>
        <div className="chat-help">
          Press Enter to send • Shift+Enter for new line
        </div>
      </div>
    </div>
  );
};

export default ChatBot;