import React, { useState, useEffect } from 'react';
import axios from 'axios';
import './SchemaManager.css';

const API_BASE_URL = 'http://localhost:8000';

const SchemaManager = () => {
  const [tables, setTables] = useState([]);
  const [selectedTable, setSelectedTable] = useState(null);
  const [columns, setColumns] = useState([]);
  const [statistics, setStatistics] = useState({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [successMessage, setSuccessMessage] = useState('');

  // Form states
  const [showTableForm, setShowTableForm] = useState(false);
  const [showColumnForm, setShowColumnForm] = useState(false);
  const [tableForm, setTableForm] = useState({
    table_name: '',
    description: '',
    business_context: '',
    tags: ''
  });
  const [columnForm, setColumnForm] = useState({
    table_name: '',
    column_name: '',
    description: '',
    data_type: '',
    example_values: '',
    business_rules: ''
  });

  // Search state
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState(null);

  useEffect(() => {
    fetchTables();
  }, []);

  const fetchTables = async () => {
    setLoading(true);
    setError('');
    try {
      const response = await axios.get(`${API_BASE_URL}/api/schema/tables`);
      if (response.data.success) {
        setTables(response.data.tables);
        setStatistics(response.data.statistics);
      }
    } catch (err) {
      setError('Failed to load tables: ' + (err.response?.data?.detail || err.message));
    } finally {
      setLoading(false);
    }
  };

  const fetchTableDetails = async (tableName) => {
    setLoading(true);
    setError('');
    try {
      const response = await axios.get(`${API_BASE_URL}/api/schema/tables/${tableName}`);
      if (response.data.success) {
        setSelectedTable(response.data.table);
        setColumns(response.data.columns);
      }
    } catch (err) {
      setError('Failed to load table details: ' + (err.response?.data?.detail || err.message));
    } finally {
      setLoading(false);
    }
  };

  const handleAddTable = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    setSuccessMessage('');

    try {
      const payload = {
        ...tableForm,
        tags: tableForm.tags ? tableForm.tags.split(',').map(t => t.trim()) : []
      };

      const response = await axios.post(`${API_BASE_URL}/api/schema/tables`, payload);

      if (response.data.success) {
        setSuccessMessage(`Table "${tableForm.table_name}" saved successfully!`);
        setShowTableForm(false);
        setTableForm({ table_name: '', description: '', business_context: '', tags: '' });
        fetchTables();

        setTimeout(() => setSuccessMessage(''), 3000);
      }
    } catch (err) {
      setError('Failed to save table: ' + (err.response?.data?.detail || err.message));
    } finally {
      setLoading(false);
    }
  };

  const handleAddColumn = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    setSuccessMessage('');

    try {
      const response = await axios.post(`${API_BASE_URL}/api/schema/columns`, columnForm);

      if (response.data.success) {
        setSuccessMessage(`Column "${columnForm.column_name}" saved successfully!`);
        setShowColumnForm(false);
        setColumnForm({
          table_name: '',
          column_name: '',
          description: '',
          data_type: '',
          example_values: '',
          business_rules: ''
        });

        // Refresh table details if viewing a table
        if (selectedTable && columnForm.table_name === selectedTable.table_name) {
          fetchTableDetails(selectedTable.table_name);
        }

        fetchTables();
        setTimeout(() => setSuccessMessage(''), 3000);
      }
    } catch (err) {
      setError('Failed to save column: ' + (err.response?.data?.detail || err.message));
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteTable = async (tableName) => {
    if (!window.confirm(`Are you sure you want to delete table "${tableName}" and all its columns?`)) {
      return;
    }

    setLoading(true);
    setError('');

    try {
      const response = await axios.delete(`${API_BASE_URL}/api/schema/tables/${tableName}`);

      if (response.data.success) {
        setSuccessMessage(`Table "${tableName}" deleted successfully!`);
        setSelectedTable(null);
        setColumns([]);
        fetchTables();

        setTimeout(() => setSuccessMessage(''), 3000);
      }
    } catch (err) {
      setError('Failed to delete table: ' + (err.response?.data?.detail || err.message));
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteColumn = async (tableName, columnName) => {
    if (!window.confirm(`Are you sure you want to delete column "${columnName}"?`)) {
      return;
    }

    setLoading(true);
    setError('');

    try {
      const response = await axios.delete(`${API_BASE_URL}/api/schema/columns/${tableName}/${columnName}`);

      if (response.data.success) {
        setSuccessMessage(`Column "${columnName}" deleted successfully!`);
        fetchTableDetails(tableName);
        fetchTables();

        setTimeout(() => setSuccessMessage(''), 3000);
      }
    } catch (err) {
      setError('Failed to delete column: ' + (err.response?.data?.detail || err.message));
    } finally {
      setLoading(false);
    }
  };

  const handleSearch = async () => {
    if (!searchQuery || searchQuery.length < 2) {
      setError('Search query must be at least 2 characters');
      return;
    }

    setLoading(true);
    setError('');

    try {
      const response = await axios.get(`${API_BASE_URL}/api/schema/search?q=${encodeURIComponent(searchQuery)}`);

      if (response.data.success) {
        setSearchResults(response.data.results);
      }
    } catch (err) {
      setError('Search failed: ' + (err.response?.data?.detail || err.message));
    } finally {
      setLoading(false);
    }
  };

  const handleExportCSV = async () => {
    setLoading(true);
    setError('');

    try {
      const response = await axios.get(`${API_BASE_URL}/api/schema/export/csv`);

      if (response.data.success) {
        setSuccessMessage(`Exported to ${response.data.file_path}. Check your project directory.`);
        setTimeout(() => setSuccessMessage(''), 5000);
      }
    } catch (err) {
      setError('Export failed: ' + (err.response?.data?.detail || err.message));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="schema-manager">
      <div className="schema-header">
        <h1>📚 Schema Management</h1>
        <p>Manage custom table and column descriptions for improved AI model understanding</p>

        {statistics && (
          <div className="schema-stats">
            <div className="stat-card">
              <div className="stat-value">{statistics.total_tables || 0}</div>
              <div className="stat-label">Tables</div>
            </div>
            <div className="stat-card">
              <div className="stat-value">{statistics.total_columns || 0}</div>
              <div className="stat-label">Columns</div>
            </div>
          </div>
        )}
      </div>

      {/* Messages */}
      {error && <div className="message-box error-message">{error}</div>}
      {successMessage && <div className="message-box success-message">{successMessage}</div>}

      {/* Search Bar */}
      <div className="search-section">
        <div className="search-bar">
          <input
            type="text"
            placeholder="Search tables and columns..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
          />
          <button onClick={handleSearch} disabled={loading}>
            🔍 Search
          </button>
          <button onClick={() => setSearchResults(null)} className="clear-btn">
            Clear
          </button>
        </div>

        {searchResults && (
          <div className="search-results">
            <h3>Search Results for "{searchQuery}"</h3>
            <div className="results-grid">
              {searchResults.tables && searchResults.tables.length > 0 && (
                <div className="result-section">
                  <h4>Tables ({searchResults.tables.length})</h4>
                  {searchResults.tables.map((result, idx) => (
                    <div key={idx} className="result-item" onClick={() => {
                      fetchTableDetails(result.table_name);
                      setSearchResults(null);
                    }}>
                      <strong>{result.table_name}</strong>
                      <p>{result.description}</p>
                    </div>
                  ))}
                </div>
              )}

              {searchResults.columns && searchResults.columns.length > 0 && (
                <div className="result-section">
                  <h4>Columns ({searchResults.columns.length})</h4>
                  {searchResults.columns.map((result, idx) => (
                    <div key={idx} className="result-item" onClick={() => {
                      fetchTableDetails(result.table_name);
                      setSearchResults(null);
                    }}>
                      <strong>{result.table_name}.{result.column_name}</strong>
                      <p>{result.description}</p>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Action Buttons */}
      <div className="action-buttons">
        <button onClick={() => setShowTableForm(!showTableForm)} className="primary-btn">
          ➕ Add/Edit Table
        </button>
        <button onClick={() => setShowColumnForm(!showColumnForm)} className="primary-btn">
          ➕ Add/Edit Column
        </button>
        <button onClick={handleExportCSV} className="secondary-btn">
          📥 Export to CSV
        </button>
        <button onClick={fetchTables} className="secondary-btn">
          🔄 Refresh
        </button>
      </div>

      {/* Table Form */}
      {showTableForm && (
        <div className="form-modal">
          <div className="form-container">
            <h2>Add/Edit Table Description</h2>
            <form onSubmit={handleAddTable}>
              <div className="form-group">
                <label>Table Name *</label>
                <input
                  type="text"
                  required
                  placeholder="e.g., UserRecords"
                  value={tableForm.table_name}
                  onChange={(e) => setTableForm({...tableForm, table_name: e.target.value})}
                />
              </div>

              <div className="form-group">
                <label>Description *</label>
                <textarea
                  required
                  placeholder="Human-readable description of the table"
                  value={tableForm.description}
                  onChange={(e) => setTableForm({...tableForm, description: e.target.value})}
                  rows="3"
                />
              </div>

              <div className="form-group">
                <label>Business Context</label>
                <textarea
                  placeholder="Business purpose, use cases, etc."
                  value={tableForm.business_context}
                  onChange={(e) => setTableForm({...tableForm, business_context: e.target.value})}
                  rows="2"
                />
              </div>

              <div className="form-group">
                <label>Tags (comma-separated)</label>
                <input
                  type="text"
                  placeholder="e.g., user data, license info, critical"
                  value={tableForm.tags}
                  onChange={(e) => setTableForm({...tableForm, tags: e.target.value})}
                />
              </div>

              <div className="form-actions">
                <button type="submit" disabled={loading} className="submit-btn">
                  {loading ? 'Saving...' : 'Save Table'}
                </button>
                <button type="button" onClick={() => setShowTableForm(false)} className="cancel-btn">
                  Cancel
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Column Form */}
      {showColumnForm && (
        <div className="form-modal">
          <div className="form-container">
            <h2>Add/Edit Column Description</h2>
            <form onSubmit={handleAddColumn}>
              <div className="form-group">
                <label>Table Name *</label>
                <input
                  type="text"
                  required
                  placeholder="e.g., UserRecords"
                  value={columnForm.table_name}
                  onChange={(e) => setColumnForm({...columnForm, table_name: e.target.value})}
                />
              </div>

              <div className="form-group">
                <label>Column Name *</label>
                <input
                  type="text"
                  required
                  placeholder="e.g., UserPrincipalName"
                  value={columnForm.column_name}
                  onChange={(e) => setColumnForm({...columnForm, column_name: e.target.value})}
                />
              </div>

              <div className="form-group">
                <label>Description *</label>
                <textarea
                  required
                  placeholder="What this column represents"
                  value={columnForm.description}
                  onChange={(e) => setColumnForm({...columnForm, description: e.target.value})}
                  rows="3"
                />
              </div>

              <div className="form-group">
                <label>Data Type</label>
                <input
                  type="text"
                  placeholder="e.g., VARCHAR(255), INT, DATETIME"
                  value={columnForm.data_type}
                  onChange={(e) => setColumnForm({...columnForm, data_type: e.target.value})}
                />
              </div>

              <div className="form-group">
                <label>Example Values</label>
                <input
                  type="text"
                  placeholder="e.g., user@contoso.com, john.doe@company.com"
                  value={columnForm.example_values}
                  onChange={(e) => setColumnForm({...columnForm, example_values: e.target.value})}
                />
              </div>

              <div className="form-group">
                <label>Business Rules</label>
                <textarea
                  placeholder="Constraints, validation rules, etc."
                  value={columnForm.business_rules}
                  onChange={(e) => setColumnForm({...columnForm, business_rules: e.target.value})}
                  rows="2"
                />
              </div>

              <div className="form-actions">
                <button type="submit" disabled={loading} className="submit-btn">
                  {loading ? 'Saving...' : 'Save Column'}
                </button>
                <button type="button" onClick={() => setShowColumnForm(false)} className="cancel-btn">
                  Cancel
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Tables List */}
      <div className="tables-section">
        <h2>Tables ({tables.length})</h2>
        <div className="tables-grid">
          {tables.map((table) => (
            <div
              key={table.table_name}
              className={`table-card ${selectedTable?.table_name === table.table_name ? 'selected' : ''}`}
              onClick={() => fetchTableDetails(table.table_name)}
            >
              <div className="table-card-header">
                <h3>{table.table_name}</h3>
                <button
                  className="delete-icon-btn"
                  onClick={(e) => {
                    e.stopPropagation();
                    handleDeleteTable(table.table_name);
                  }}
                  title="Delete table"
                >
                  🗑️
                </button>
              </div>
              <p className="table-description">{table.description || 'No description'}</p>
              <div className="table-meta">
                <span className="column-count">📊 {table.column_count} columns</span>
                {table.tags && table.tags.length > 0 && (
                  <div className="tags">
                    {table.tags.map((tag, idx) => (
                      <span key={idx} className="tag">{tag}</span>
                    ))}
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Selected Table Details */}
      {selectedTable && (
        <div className="table-details">
          <h2>📋 {selectedTable.table_name} - Details</h2>

          <div className="detail-section">
            <h3>Table Information</h3>
            <div className="detail-item">
              <strong>Description:</strong>
              <p>{selectedTable.description || 'N/A'}</p>
            </div>
            {selectedTable.business_context && (
              <div className="detail-item">
                <strong>Business Context:</strong>
                <p>{selectedTable.business_context}</p>
              </div>
            )}
            {selectedTable.tags && selectedTable.tags.length > 0 && (
              <div className="detail-item">
                <strong>Tags:</strong>
                <div className="tags">
                  {selectedTable.tags.map((tag, idx) => (
                    <span key={idx} className="tag">{tag}</span>
                  ))}
                </div>
              </div>
            )}
          </div>

          <div className="columns-section">
            <h3>Columns ({columns.length})</h3>
            {columns.length > 0 ? (
              <div className="columns-table">
                <table>
                  <thead>
                    <tr>
                      <th>Column Name</th>
                      <th>Description</th>
                      <th>Data Type</th>
                      <th>Example Values</th>
                      <th>Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {columns.map((col) => (
                      <tr key={col.column_name}>
                        <td><strong>{col.column_name}</strong></td>
                        <td>{col.description || 'N/A'}</td>
                        <td>{col.data_type || 'N/A'}</td>
                        <td className="example-values">{col.example_values || 'N/A'}</td>
                        <td>
                          <button
                            className="delete-btn-small"
                            onClick={() => handleDeleteColumn(selectedTable.table_name, col.column_name)}
                            title="Delete column"
                          >
                            🗑️
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <p className="no-data">No columns added yet. Click "Add/Edit Column" to add one.</p>
            )}
          </div>
        </div>
      )}

      {loading && <div className="loading-overlay">Loading...</div>}
    </div>
  );
};

export default SchemaManager;
