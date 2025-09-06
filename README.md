# Text-to-SQL System with Vector Database Retrieval

A sophisticated system that converts natural language questions into SQL queries using vector similarity search and Azure OpenAI.

## Features

- 🔍 **Vector Search**: Uses FAISS to find relevant database tables based on query similarity
- ⚡ **SQL Generation**: Leverages Azure OpenAI to generate accurate SQL queries
- 🎯 **Query Execution**: Executes queries on SQL Server using pyodbc
- 💡 **Natural Language Response**: Converts SQL results back to readable answers
- 📊 **Intermediate Results**: Shows all steps of the process for transparency

## Quick Start

1. **Setup**:
   ```bash
   python setup.py
   ```

2. **Run the system**:
   ```bash
   python main.py enhanced_db_schema.csv
   ```

3. **Start asking questions**:
   ```
   💬 Your question: How many users are there?
   💬 Your question: Show me the top 5 products by price
   💬 Your question: What are the most recent orders?
   ```

## System Architecture

The system processes queries through 4 main steps:

### Step 1: Vector Search 🔍
- Converts your question into embeddings
- Searches the vector database (FAISS) for relevant tables
- Returns the most similar table schemas

### Step 2: SQL Generation ⚡
- Uses Azure OpenAI with retrieved schemas as context
- Generates precise SQL queries based on your question
- Follows SQL Server syntax standards

### Step 3: Query Execution 🎯
- Connects to SQL Server using pyodbc
- Executes the generated query
- Handles errors with retry logic

### Step 4: Natural Language Response 💡
- Processes SQL results using Azure OpenAI
- Generates human-readable answers
- Provides insights and summaries

## Configuration

Update `config.py` with your credentials:

```python
# Azure OpenAI Configuration
AZURE_ENDPOINT = "your-endpoint"
SUBSCRIPTION_KEY = "your-key"

# SQL Server Configuration  
SQL_SERVER = 'your-server'
SQL_DATABASE = 'your-database'
SQL_USERNAME = 'your-username'
SQL_PASSWORD = 'your-password'
```

## CSV Schema Format

Your `enhanced_db_schema.csv` should have columns:
- `table_name`: Name of the database table
- `column_name`: Name of the column
- `data_type`: SQL data type
- `description`: Description of what the column contains

## Commands

- `test` - Test database connection
- `quit`/`exit` - Exit the program

## File Structure

```
├── main.py                 # Main application entry point
├── config.py              # Configuration and Azure OpenAI client
├── schema_processor.py    # CSV processing and schema extraction
├── vector_db.py           # FAISS vector database functionality
├── sql_generator.py       # SQL query generation using Azure OpenAI
├── sql_executor.py        # SQL Server connection and execution
├── result_processor.py    # Result processing and natural language response
├── setup.py              # Setup script
├── requirements.txt       # Python dependencies
└── enhanced_db_schema.csv # Your database schema file
```