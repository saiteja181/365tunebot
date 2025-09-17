#!/usr/bin/env python3
"""
Real FastAPI service for 365 Tune Bot with TextToSQLSystem integration
Based on working Streamlit implementation with lazy loading
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import uvicorn
import os
import sys
import time
import json
import pandas as pd
from datetime import datetime
import uuid
import asyncio
import threading

# Import the actual system components
try:
    from main import TextToSQLSystem
    SYSTEM_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Could not import TextToSQLSystem: {e}")
    SYSTEM_AVAILABLE = False

# Initialize FastAPI app
app = FastAPI(
    title="365 Tune Bot API - Real Data",
    description="REST API for 365 Tune Bot with real TextToSQL processing",
    version="2.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global system instance with thread-safe access
system: Optional[TextToSQLSystem] = None
system_initialized = False
system_lock = threading.Lock()
dashboard_cache = {}
cache_timestamp = None

# Conversation memory storage - stores last 6 exchanges per session
conversation_memory = {}
memory_lock = threading.Lock()

class ConversationEntry:
    def __init__(self, user_message: str, bot_response: str, timestamp: datetime):
        self.user_message = user_message
        self.bot_response = bot_response
        self.timestamp = timestamp

def add_to_conversation_memory(session_id: str, user_message: str, bot_response: str):
    """Add a conversation exchange to memory, keeping only last 3 exchanges"""
    with memory_lock:
        if session_id not in conversation_memory:
            conversation_memory[session_id] = []
        
        # Skip adding simple greetings and help messages to preserve meaningful context
        if user_message.strip().lower() in ["hello", "hi", "hey", "hello there", "hi there"] or "help" in user_message.lower():
            return
        
        # Add new entry
        entry = ConversationEntry(user_message, bot_response, datetime.now())
        conversation_memory[session_id].append(entry)
        
        # Keep only last 3 exchanges
        if len(conversation_memory[session_id]) > 3:
            conversation_memory[session_id] = conversation_memory[session_id][-3:]

def get_conversation_context(session_id: str) -> str:
    """Get conversation context as a formatted string for the AI"""
    with memory_lock:
        if session_id not in conversation_memory or not conversation_memory[session_id]:
            return ""
        
        # Only use the last 3 exchanges to keep context manageable
        recent_entries = conversation_memory[session_id][-3:]
        context_parts = []
        
        for i, entry in enumerate(recent_entries):
            # For SQL generation context, preserve more information
            # Extract key information from queries
            user_msg = entry.user_message
            bot_msg = entry.bot_response
            
            # If bot response contains SQL or data info, preserve that
            if "SQL:" in bot_msg or "users" in bot_msg.lower() or "department" in bot_msg.lower():
                # Keep more of the response for SQL context
                bot_msg = bot_msg[:200] + "..." if len(bot_msg) > 200 else bot_msg
            else:
                # For non-data responses, keep shorter
                bot_msg = bot_msg[:100] + "..." if len(bot_msg) > 100 else bot_msg
            
            # Always preserve full user questions for context continuity
            context_parts.append(f"Previous Query {i+1}: {user_msg}")
            context_parts.append(f"Previous Response {i+1}: {bot_msg}")
        
        # Allow more context length for better SQL generation
        context = "\n".join(context_parts)
        if len(context) > 800:  # Increased from 300
            # Instead of hard truncating, try to preserve complete exchanges
            exchanges_to_keep = 2  # Keep last 2 exchanges instead of 3 if too long
            recent_entries = conversation_memory[session_id][-exchanges_to_keep:]
            context_parts = []
            
            for i, entry in enumerate(recent_entries):
                user_msg = entry.user_message
                bot_msg = entry.bot_response[:150] + "..." if len(entry.bot_response) > 150 else entry.bot_response
                context_parts.append(f"Previous Query {i+1}: {user_msg}")
                context_parts.append(f"Previous Response {i+1}: {bot_msg}")
            
            context = "\n".join(context_parts)
            
        return context

def cleanup_old_sessions():
    """Clean up sessions older than 24 hours to prevent memory leaks"""
    with memory_lock:
        current_time = datetime.now()
        sessions_to_remove = []
        
        for session_id, entries in conversation_memory.items():
            if entries and (current_time - entries[-1].timestamp).total_seconds() > 86400:  # 24 hours
                sessions_to_remove.append(session_id)
        
        for session_id in sessions_to_remove:
            del conversation_memory[session_id]
        
        if sessions_to_remove:
            print(f"Cleaned up {len(sessions_to_remove)} old conversation sessions")

async def periodic_cleanup():
    """Periodic cleanup task running every hour"""
    while True:
        await asyncio.sleep(3600)  # Wait 1 hour
        cleanup_old_sessions()

# Pydantic models
class QueryRequest(BaseModel):
    query: str

class QueryResponse(BaseModel):
    success: bool
    processing_time: float
    result_count: int
    final_answer: str
    sql_query: Optional[str] = None
    results: List[Dict[str, Any]] = []
    vector_search_results: Optional[List[Dict[str, Any]]] = None
    execution_info: Optional[str] = None
    error: Optional[str] = None

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None

class ChatResponse(BaseModel):
    success: bool
    message: str
    processing_time: float
    result_count: Optional[int] = None
    session_id: str
    error: Optional[str] = None
    results: Optional[List[Dict[str, Any]]] = None

def initialize_system_threadsafe():
    """Thread-safe system initialization"""
    global system, system_initialized
    
    with system_lock:
        if system_initialized:
            return True
            
        if not SYSTEM_AVAILABLE:
            print("TextToSQLSystem not available")
            return False
        
        try:
            print("Initializing TextToSQLSystem (this may take a moment)...")
            system = TextToSQLSystem()
            csv_file = "enhanced_db_schema.csv"
            
            if not os.path.exists(csv_file):
                print(f"Warning: CSV file not found: {csv_file}")
                return False
            
            success = system.initialize_system(csv_file)
            if not success:
                print("Failed to initialize TextToSQLSystem")
                return False
            
            system_initialized = True
            print("TextToSQLSystem initialized successfully!")
            return True
            
        except Exception as e:
            print(f"Error initializing TextToSQLSystem: {str(e)}")
            system = None
            system_initialized = False
            return False

def ensure_system_ready():
    """Ensure system is initialized, initialize if needed"""
    global system_initialized
    if not system_initialized:
        return initialize_system_threadsafe()
    return True

def load_dashboard_data_real():
    """Load dashboard data using the same logic as Streamlit"""
    global dashboard_cache, cache_timestamp
    
    # Cache for 5 minutes
    if cache_timestamp and (time.time() - cache_timestamp) < 300 and dashboard_cache:
        return dashboard_cache
    
    if not ensure_system_ready() or not system:
        return get_fallback_dashboard_data()
    
    try:
        dashboard_data = {}
        
        # Basic Statistics (same as Streamlit)
        basic_queries = [
            ("Total Users", "SELECT COUNT(*) as count FROM UserRecords"),
            ("Active Users", "SELECT COUNT(*) as count FROM UserRecords WHERE AccountStatus = 'Active'"),
            ("Licensed Users", "SELECT COUNT(*) as count FROM UserRecords WHERE IsLicensed = 1"),
            ("Countries", "SELECT COUNT(DISTINCT Country) as count FROM UserRecords WHERE Country IS NOT NULL"),
            ("Inactive Users", "SELECT COUNT(*) as count FROM UserRecords WHERE AccountStatus != 'Active'"),
            ("Guest Users", "SELECT COUNT(*) as count FROM UserRecords WHERE UserType = 'Guest'"),
            ("Admin Users", "SELECT COUNT(*) as count FROM UserRecords WHERE IsAdmin = 1"),
        ]
        
        for label, query in basic_queries:
            try:
                success, result, execution_info = system.sql_executor.execute_query(query)
                if success and result and len(result) > 0 and 'count' in result[0]:
                    dashboard_data[label] = result[0]['count']
                else:
                    dashboard_data[label] = 0
            except Exception as e:
                print(f"Error executing query for {label}: {e}")
                dashboard_data[label] = 0
        
        # Advanced Analytics Queries (same as Streamlit)
        analytics_queries = {
            'Countries_Data': """
                SELECT TOP 15 Country, COUNT(*) as UserCount, 
                       SUM(CASE WHEN AccountStatus = 'Active' THEN 1 ELSE 0 END) as ActiveUsers,
                       SUM(CASE WHEN IsLicensed = 1 THEN 1 ELSE 0 END) as LicensedUsers
                FROM UserRecords 
                WHERE Country IS NOT NULL 
                GROUP BY Country 
                ORDER BY UserCount DESC
            """,
            
            'Departments_Data': """
                SELECT TOP 15 Department, COUNT(*) as UserCount,
                       SUM(CASE WHEN AccountStatus = 'Active' THEN 1 ELSE 0 END) as ActiveUsers,
                       AVG(CAST(EmailSent_D30 as FLOAT)) as AvgEmailsSent30D
                FROM UserRecords 
                WHERE Department IS NOT NULL 
                GROUP BY Department 
                ORDER BY UserCount DESC
            """,
            
            'License_Analysis': """
                SELECT l.Name as LicenseName, l.TotalUnits, l.ConsumedUnits, 
                       l.ActualCost, l.Status,
                       (CAST(l.ConsumedUnits as FLOAT) / NULLIF(l.TotalUnits, 0) * 100) as UtilizationPercent
                FROM Licenses l
                WHERE l.TotalUnits > 0
                ORDER BY l.ActualCost DESC
            """
        }
        
        # Execute analytics queries
        for key, query in analytics_queries.items():
            try:
                success, result, execution_info = system.sql_executor.execute_query(query)
                if success and result:
                    # Clean result data
                    clean_result = []
                    for row in result:
                        if hasattr(row, 'to_dict'):
                            clean_result.append(row.to_dict())
                        elif isinstance(row, dict):
                            clean_dict = {}
                            for k, v in row.items():
                                if v is None or pd.isna(v):
                                    clean_dict[k] = None
                                elif hasattr(v, 'item'):  # numpy types
                                    clean_dict[k] = v.item()
                                else:
                                    clean_dict[k] = v
                            clean_result.append(clean_dict)
                        else:
                            clean_result.append(row)
                    dashboard_data[key] = clean_result
                else:
                    dashboard_data[key] = []
            except Exception as e:
                print(f"Error executing {key}: {e}")
                dashboard_data[key] = []
        
        # Cache the results
        dashboard_cache = dashboard_data
        cache_timestamp = time.time()
        
        return dashboard_data
        
    except Exception as e:
        print(f"Error loading dashboard data: {e}")
        return get_fallback_dashboard_data()

def get_fallback_dashboard_data():
    """Fallback dashboard data"""
    return {
        'Total Users': 1250, 'Active Users': 987, 'Licensed Users': 823, 
        'Countries': 15, 'Inactive Users': 263, 'Guest Users': 45, 'Admin Users': 12,
        'Countries_Data': [
            {"Country": "United States", "UserCount": 345, "ActiveUsers": 290, "LicensedUsers": 280},
            {"Country": "United Kingdom", "UserCount": 123, "ActiveUsers": 100, "LicensedUsers": 95},
            {"Country": "Canada", "UserCount": 89, "ActiveUsers": 75, "LicensedUsers": 70}
        ],
        'Departments_Data': [
            {"Department": "Engineering", "UserCount": 234, "ActiveUsers": 220, "AvgEmailsSent30D": 45.2},
            {"Department": "Sales", "UserCount": 189, "ActiveUsers": 180, "AvgEmailsSent30D": 62.1},
            {"Department": "Marketing", "UserCount": 156, "ActiveUsers": 145, "AvgEmailsSent30D": 38.7}
        ],
        'License_Analysis': [
            {"LicenseName": "Microsoft 365 E3", "TotalUnits": 500, "ConsumedUnits": 423, "ActualCost": 22.50, "UtilizationPercent": 84.6},
            {"LicenseName": "Microsoft 365 E1", "TotalUnits": 300, "ConsumedUnits": 210, "ActualCost": 8.50, "UtilizationPercent": 70.0}
        ]
    }

@app.on_event("startup")
async def startup_event():
    """Initialize the service on startup with eager loading"""
    print("365 Tune Bot FastAPI - Real Data Service Starting...")
    print("Initializing system eagerly to avoid request timeouts...")
    
    # Eager load the system
    success = initialize_system_threadsafe()
    if success:
        print("System initialization completed successfully!")
        
        # Pre-load dashboard data to warm up caches
        try:
            print("Warming up dashboard cache...")
            dashboard_data = load_dashboard_data_real()
            print(f"Dashboard cache warmed: {len(dashboard_data)} data sections loaded")
        except Exception as e:
            print(f"Warning: Could not warm dashboard cache: {e}")
    else:
        print("Warning: System initialization failed - will use fallback mode")
    
    print("Available at: http://127.0.0.1:8000")
    print("API Docs at: http://127.0.0.1:8000/docs")
    
    # Start periodic cleanup of old conversation sessions
    asyncio.create_task(periodic_cleanup())

@app.get("/")
async def root():
    """Health check"""
    return {
        "message": "365 Tune Bot FastAPI - Real Data Service",
        "status": "running",
        "system_initialized": system_initialized,
        "version": "2.0.0",
        "endpoints": [
            "/docs",
            "/api/query",
            "/api/chat", 
            "/api/dashboard",
            "/api/licenses",
            "/api/chart/countries",
            "/api/chart/departments"
        ]
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "system_initialized": system_initialized,
        "system_available": SYSTEM_AVAILABLE
    }

@app.post("/api/query", response_model=QueryResponse)
async def process_query(request: QueryRequest, conversation_context: str = ""):
    """Process natural language query using real TextToSQLSystem"""
    
    try:
        start_time = time.time()
        
        if not ensure_system_ready() or not system:
            # Fallback response
            processing_time = time.time() - start_time
            return QueryResponse(
                success=False,
                processing_time=float(processing_time),
                result_count=0,
                final_answer="System not available. Please try again later.",
                error="TextToSQLSystem not initialized"
            )
        
        # Use the real system with conversation context if provided
        result = system.process_query(request.query, conversation_context)
        processing_time = time.time() - start_time
        
        if "error" in result:
            return QueryResponse(
                success=False,
                processing_time=float(processing_time),
                result_count=0,
                final_answer="I encountered an issue processing your query. Could you try rephrasing it or asking a simpler question?",
                error=result["error"]
            )

        # Extract results from the 4-step process
        vector_results = result.get("step_1_vector_search", {}).get("results", [])
        sql_query = result.get("step_2_sql_generation", {}).get("sql_query", "")
        execution_info = result.get("step_3_sql_execution", {}).get("execution_info", "")
        sample_results = result.get("step_3_sql_execution", {}).get("sample_results", [])
        result_count = int(len(sample_results)) if sample_results else 0
        final_answer = result.get("step_4_final_answer", {}).get("answer", "")

        # Create enhanced fallback answer if none provided
        if not final_answer and sample_results:
            # Use the result processor to generate a better response
            final_answer = system.result_processor._create_enhanced_fallback_response(
                request.query,
                sample_results,
                ""  # No data insights for now
            )
        elif not final_answer and not sample_results:
            # Complete fallback when both SQL generation and execution fail
            final_answer = f"I'm having trouble processing your question '{request.query}'. Could you try rephrasing it? For example, you could ask: 'How many users are there?', 'Show me users by department', or 'Which countries have the most users?'"

        # Clean and convert all data types to ensure JSON serialization
        clean_sample_results = []
        for result in (sample_results[:10] if sample_results else []):
            if isinstance(result, dict):
                clean_result = {}
                for k, v in result.items():
                    if hasattr(v, 'item'):  # numpy types
                        clean_result[k] = v.item()
                    elif isinstance(v, (int, float, str, bool)) or v is None:
                        clean_result[k] = v
                    else:
                        clean_result[k] = str(v)
                clean_sample_results.append(clean_result)
            else:
                clean_sample_results.append(result)

        return QueryResponse(
            success=True,
            processing_time=float(processing_time),
            result_count=int(result_count),
            final_answer=str(final_answer or "Query processed successfully"),
            sql_query=str(sql_query) if sql_query else None,
            results=clean_sample_results,
            vector_search_results=vector_results[:5] if vector_results else None,
            execution_info=str(execution_info) if execution_info else None
        )
        
    except Exception as e:
        return QueryResponse(
            success=False,
            processing_time=0.0,
            result_count=0,
            final_answer="",
            error=str(e)
        )

@app.get("/api/dashboard")
async def get_dashboard_data():
    """Get comprehensive dashboard metrics using real data"""
    
    try:
        # Use cached data if available and fresh (less than 5 minutes old)
        if cache_timestamp and (time.time() - cache_timestamp) < 300 and dashboard_cache:
            dashboard_data = dashboard_cache
        else:
            dashboard_data = load_dashboard_data_real()
        
        return {
            "success": True,
            "metrics": {
                "Total Users": dashboard_data.get('Total Users', 0),
                "Active Users": dashboard_data.get('Active Users', 0),
                "Licensed Users": dashboard_data.get('Licensed Users', 0),
                "Countries": dashboard_data.get('Countries', 0),
                "Inactive Users": dashboard_data.get('Inactive Users', 0),
                "Guest Users": dashboard_data.get('Guest Users', 0),
                "Admin Users": dashboard_data.get('Admin Users', 0)
            },
            "timestamp": datetime.now().isoformat(),
            "source": "Real Data" if system_initialized else "Fallback"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

@app.get("/api/chart/{chart_type}")
async def get_chart_data(chart_type: str):
    """Get data for charts using real data"""
    
    try:
        # Use cached data if available and fresh
        if cache_timestamp and (time.time() - cache_timestamp) < 300 and dashboard_cache:
            dashboard_data = dashboard_cache
        else:
            dashboard_data = load_dashboard_data_real()
        
        if chart_type == "countries":
            result = dashboard_data.get('Countries_Data', [])
            # Transform to expected format
            chart_data = []
            for item in result:
                if isinstance(item, dict) and 'Country' in item and 'UserCount' in item:
                    chart_data.append({
                        "Country": item['Country'],
                        "UserCount": item['UserCount']
                    })
            result = chart_data[:10]  # Top 10
            
        elif chart_type == "departments":
            result = dashboard_data.get('Departments_Data', [])
            # Transform to expected format
            chart_data = []
            for item in result:
                if isinstance(item, dict) and 'Department' in item and 'UserCount' in item:
                    chart_data.append({
                        "Department": item['Department'],
                        "UserCount": item['UserCount']
                    })
            result = chart_data[:10]  # Top 10
            
        else:
            raise HTTPException(status_code=400, detail="Invalid chart type")
        
        return {
            "success": True,
            "chart_type": chart_type,
            "data": result,
            "count": len(result),
            "source": "Real Data" if system_initialized else "Fallback"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

@app.post("/api/chat", response_model=ChatResponse)
async def chat_with_bot(request: ChatRequest):
    """Enhanced chatbot endpoint using real system"""
    
    try:
        start_time = time.time()
        session_id = request.session_id or str(uuid.uuid4())
        message_lower = request.message.lower()
        
        # Only respond with greeting for very simple greetings, not questions containing greeting words
        if request.message.strip().lower() in ["hello", "hi", "hey", "hello there", "hi there"]:
            message = "Hello! I'm the 365 Tune Bot. I can help you analyze your Microsoft 365 data with natural language queries. Ask me anything about users, departments, countries, or licenses!"
            processing_time = time.time() - start_time
            
            return ChatResponse(
                success=True,
                message=message,
                processing_time=processing_time,
                session_id=session_id
            )
        
        elif "help" in message_lower:
            message = """I can help you with queries like:
            - 'How many users are there?'
            - 'Show me active users'
            - 'List users by department'
            - 'Which countries have the most users?'
            - 'How many licensed users do we have?'
            
            Just ask your question in natural language!"""
            processing_time = time.time() - start_time
            
            return ChatResponse(
                success=True,
                message=message,
                processing_time=processing_time,
                session_id=session_id
            )
        
        else:
            try:
                # Get conversation context for this session
                context = get_conversation_context(session_id)
                print(f"Processing query: {request.message}")
                if context:
                    print(f"Using conversation context (last {len(conversation_memory.get(session_id, []))} exchanges)")
                    print(f"Context preview: {context[:100]}...")
                
                # Process query with conversation context
                query_result = await process_query(QueryRequest(query=request.message), context)
                processing_time = time.time() - start_time
                
                print(f"Query result success: {query_result.success}")
                if hasattr(query_result, 'final_answer'):
                    print(f"Final answer: {query_result.final_answer[:100]}...")
                
                if query_result.success and hasattr(query_result, 'final_answer') and query_result.final_answer:
                    message = query_result.final_answer
                    
                    # Add this exchange to conversation memory
                    add_to_conversation_memory(session_id, request.message, message)
                    
                    return ChatResponse(
                        success=True,
                        message=message,
                        processing_time=processing_time,
                        result_count=int(getattr(query_result, 'result_count', 0) or 0),
                        session_id=session_id,
                        results=getattr(query_result, 'results', [])
                    )
                else:
                    error_msg = getattr(query_result, 'error', 'Unknown error occurred')
                    error_response = f"Sorry, I encountered an error: {error_msg}"
                    
                    # Still add to memory even for errors to maintain context
                    add_to_conversation_memory(session_id, request.message, error_response)
                    
                    return ChatResponse(
                        success=False,
                        message=error_response,
                        processing_time=processing_time,
                        result_count=0,
                        session_id=session_id,
                        error=error_msg
                    )
            
            except Exception as query_error:
                print(f"Error in query processing: {str(query_error)}")
                processing_time = time.time() - start_time
                error_response = "Sorry, there was an unexpected error processing your query."
                
                # Still add to memory
                add_to_conversation_memory(session_id, request.message, error_response)
                
                return ChatResponse(
                    success=False,
                    message=error_response,
                    processing_time=processing_time,
                    result_count=0,
                    session_id=session_id,
                    error=str(query_error)
                )
        
    except Exception as e:
        return ChatResponse(
            success=False,
            message=f"Sorry, something went wrong: {str(e)}",
            processing_time=0.0,
            result_count=0,
            session_id=request.session_id or str(uuid.uuid4()),
            error=str(e)
        )

@app.get("/api/memory/debug/{session_id}")
async def debug_conversation_memory(session_id: str):
    """Debug endpoint to check conversation memory for a session"""
    with memory_lock:
        if session_id in conversation_memory:
            entries = []
            for entry in conversation_memory[session_id]:
                entries.append({
                    "user_message": entry.user_message,
                    "bot_response": entry.bot_response[:100] + "..." if len(entry.bot_response) > 100 else entry.bot_response,
                    "timestamp": entry.timestamp.isoformat()
                })
            return {
                "session_id": session_id,
                "entry_count": len(entries),
                "entries": entries,
                "context": get_conversation_context(session_id)
            }
        else:
            return {"session_id": session_id, "entry_count": 0, "entries": [], "context": ""}

@app.get("/api/memory/sessions")
async def list_active_sessions():
    """List all active conversation sessions"""
    with memory_lock:
        sessions = []
        for session_id, entries in conversation_memory.items():
            if entries:
                sessions.append({
                    "session_id": session_id,
                    "entry_count": len(entries),
                    "last_activity": entries[-1].timestamp.isoformat()
                })
        return {"active_sessions": len(sessions), "sessions": sessions}

@app.get("/api/licenses")
async def get_license_data():
    """Get license data and metrics"""
    
    try:
        if not ensure_system_ready() or not system:
            # Fallback data
            return {
                "success": True,
                "licenses": [
                    {
                        "license_name": "Microsoft 365 E3",
                        "total_units": 500,
                        "consumed_units": 423,
                        "actual_cost": 22.50,
                        "utilization_percent": 84.6,
                        "status": "Active"
                    },
                    {
                        "license_name": "Microsoft 365 E1", 
                        "total_units": 300,
                        "consumed_units": 210,
                        "actual_cost": 8.50,
                        "utilization_percent": 70.0,
                        "status": "Active"
                    }
                ],
                "source": "Fallback"
            }
        
        query = """
            SELECT l.Name as LicenseName, l.TotalUnits, l.ConsumedUnits, 
                   l.ActualCost, l.Status,
                   (CAST(l.ConsumedUnits as FLOAT) / NULLIF(l.TotalUnits, 0) * 100) as UtilizationPercent
            FROM Licenses l
            WHERE l.TotalUnits > 0
            ORDER BY l.ActualCost DESC
        """
        
        success, result, execution_info = system.sql_executor.execute_query(query)
        if success and result:
            licenses = []
            for row in result:
                # Clean and format data to avoid type errors
                clean_dict = {}
                for k, v in row.items():
                    if v is None or pd.isna(v):
                        clean_dict[k] = None
                    elif hasattr(v, 'item'):  # numpy types
                        clean_dict[k] = v.item()
                    else:
                        clean_dict[k] = v
                
                # Get raw values
                total_units = int(clean_dict.get('TotalUnits') or 0)
                consumed_units = int(clean_dict.get('ConsumedUnits') or 0)
                actual_cost = float(clean_dict.get('ActualCost') or 0)
                
                # Data validation and correction
                # Fix cases where consumed > total (data integrity issue)
                if consumed_units > total_units and total_units > 0:
                    print(f"WARNING: License '{clean_dict.get('LicenseName')}' has consumed ({consumed_units}) > total ({total_units}). Capping to total.")
                    consumed_units = total_units
                
                # Calculate corrected utilization percentage
                if total_units > 0:
                    utilization_percent = min((consumed_units / total_units) * 100, 100.0)
                else:
                    utilization_percent = 0.0
                
                license_data = {
                    "license_name": clean_dict.get('LicenseName', ''),
                    "total_units": total_units,
                    "consumed_units": consumed_units,
                    "actual_cost": actual_cost,
                    "utilization_percent": round(utilization_percent, 2),
                    "status": clean_dict.get('Status', 'Unknown')
                }
                licenses.append(license_data)
            
            return {
                "success": True,
                "licenses": licenses,
                "source": "Real Data"
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to fetch license data")
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

if __name__ == "__main__":
    print("Starting 365 Tune Bot FastAPI with Real Data...")
    uvicorn.run(app, host="127.0.0.1", port=8000)