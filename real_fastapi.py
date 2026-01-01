#!/usr/bin/env python3
"""
Real FastAPI service for 365 Tune Bot with TextToSQLSystem integration
Based on working Streamlit implementation with lazy loading
"""

from fastapi import FastAPI, HTTPException
from auth import get_current_user, get_current_tenant, optional_auth
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from contextlib import asynccontextmanager
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
    # Define dummy class to avoid NameError in type hints
    class TextToSQLSystem:
        pass

# Import tenant security
try:
    from tenant_security import audit_logger, TenantSecurityException
    TENANT_SECURITY_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Could not import tenant security: {e}")
    TENANT_SECURITY_AVAILABLE = False

# Import AI Insights
try:
    from ai_insights import AIInsightsGenerator
    INSIGHTS_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Could not import AIInsightsGenerator: {e}")
    INSIGHTS_AVAILABLE = False

# Import Enhanced AI Insights
try:
    from enhanced_ai_insights import EnhancedAIInsights
    ENHANCED_INSIGHTS_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Could not import EnhancedAIInsights: {e}")
    ENHANCED_INSIGHTS_AVAILABLE = False

# Import Redis Cache Manager
try:
    from redis_cache_manager import get_cache_manager
    CACHE_MANAGER_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Could not import RedisCacheManager: {e}")
    CACHE_MANAGER_AVAILABLE = False

# Import AI Mode Manager
try:
    from ai_mode_manager import get_ai_mode_manager, AIMode
    AI_MODE_MANAGER_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Could not import AIModeManager: {e}")
    AI_MODE_MANAGER_AVAILABLE = False

# Import Enhanced Conversation Memory
try:
    from conversation_memory_enhanced import get_enhanced_memory
    ENHANCED_MEMORY_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Could not import EnhancedMemory: {e}")
    ENHANCED_MEMORY_AVAILABLE = False

# Import Comprehensive Scoring
try:
    from comprehensive_scoring import ComprehensiveTenantScoring
    COMPREHENSIVE_SCORING_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Could not import ComprehensiveTenantScoring: {e}")
    COMPREHENSIVE_SCORING_AVAILABLE = False

# Import Cost Forecasting Engine
try:
    from cost_forecasting_engine import CostForecastingEngine
    COST_FORECASTING_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Could not import CostForecastingEngine: {e}")
    COST_FORECASTING_AVAILABLE = False

# Import Advisory Mode (NEW EXTENSION)
try:
    from advisory_mode import AdvisoryModeHandler
    ADVISORY_MODE_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Could not import AdvisoryModeHandler: {e}")
    ADVISORY_MODE_AVAILABLE = False
    class AdvisoryModeHandler:
        pass

# Import Schema Manager (NEW EXTENSION)
try:
    from schema_manager import SchemaManager
    SCHEMA_MANAGER_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Could not import SchemaManager: {e}")
    SCHEMA_MANAGER_AVAILABLE = False
    class SchemaManager:
        pass

# Import logger
try:
    from logger_config import get_logger
    logger = get_logger(__name__)
except ImportError:
    # Fallback if logger not available
    import logging
    logger = logging.getLogger(__name__)

# Global cleanup task reference
cleanup_task = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Modern lifespan event handler for startup and shutdown"""
    global cleanup_task

    # Startup
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
    cleanup_task = asyncio.create_task(periodic_cleanup())

    yield  # Application runs

    # Shutdown
    if cleanup_task:
        cleanup_task.cancel()
        try:
            await cleanup_task
        except asyncio.CancelledError:
            pass
    print("365 Tune Bot FastAPI - Shutting down...")

app = FastAPI(
    title="365 Tune Bot API - Real Data",
    description="REST API for 365 Tune Bot with real TextToSQL processing",
    version="2.0.0",
    lifespan=lifespan
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

# Redis Cache Manager
cache_manager = None

# AI Mode Manager
ai_mode_manager = None

# Enhanced Conversation Memory
enhanced_memory = None

# TENANT SECURITY: Your tenant code (in production, get from authentication)
DEFAULT_TENANT_CODE = "70b0fb90-1eb4-46d8-b23e-f4104619181b"

# DEPRECATED: Old in-memory conversation memory (kept for fallback)
conversation_memory = {}
memory_lock = threading.Lock()

# NEW EXTENSIONS: Advisory Mode and Schema Manager
advisory_handler: Optional[AdvisoryModeHandler] = None
schema_manager: Optional[SchemaManager] = None

class ConversationEntry:
    def __init__(self, user_message: str, bot_response: str, timestamp: datetime):
        self.user_message = user_message
        self.bot_response = bot_response
        self.timestamp = timestamp

def add_to_conversation_memory(session_id: str, user_message: str, bot_response: str):
    """
    Add conversation to Redis cache (with fallback to in-memory)
    Persistent across server restarts if Redis is available
    """
    # Skip simple greetings and help messages
    if user_message.strip().lower() in ["hello", "hi", "hey", "hello there", "hi there"] or "help" in user_message.lower():
        return

    # Use Redis cache if available
    if CACHE_MANAGER_AVAILABLE and cache_manager:
        success = cache_manager.store_conversation_memory(
            session_id, user_message, bot_response, ttl=86400  # 24 hours
        )
        if success:
            print(f"[OK] Conversation stored in cache for session: {session_id}")
            return

    # Fallback to old in-memory system
    with memory_lock:
        if session_id not in conversation_memory:
            conversation_memory[session_id] = []

        entry = ConversationEntry(user_message, bot_response, datetime.now())
        conversation_memory[session_id].append(entry)

        # Keep only last 3 exchanges
        if len(conversation_memory[session_id]) > 3:
            conversation_memory[session_id] = conversation_memory[session_id][-3:]

def get_conversation_context(session_id: str) -> str:
    """
    Get conversation context from Redis cache (with fallback)
    Context persists across server restarts if Redis is available
    """
    # Try Redis cache first
    if CACHE_MANAGER_AVAILABLE and cache_manager:
        memory = cache_manager.get_conversation_memory(session_id)
        if memory:
            # Format Redis memory entries
            context_parts = []
            for i, entry in enumerate(memory[-3:]):  # Last 3 exchanges
                user_msg = entry.get("user_message", "")
                bot_msg = entry.get("bot_response", "")

                # Truncate if needed
                if len(bot_msg) > 200:
                    bot_msg = bot_msg[:200] + "..."

                context_parts.append(f"Previous Query {i+1}: {user_msg}")
                context_parts.append(f"Previous Response {i+1}: {bot_msg}")

            context = "\n".join(context_parts)
            return context[:800]  # Max 800 chars

    # Fallback to old in-memory system
    with memory_lock:
        if session_id not in conversation_memory or not conversation_memory[session_id]:
            return ""

        # Only use the last 3 exchanges to keep context manageable
        recent_entries = conversation_memory[session_id][-3:]
        context_parts = []

        for i, entry in enumerate(recent_entries):
            user_msg = entry.user_message
            bot_msg = entry.bot_response

            # If bot response contains SQL or data info, preserve that
            if "SQL:" in bot_msg or "users" in bot_msg.lower() or "department" in bot_msg.lower():
                bot_msg = bot_msg[:200] + "..." if len(bot_msg) > 200 else bot_msg
            else:
                bot_msg = bot_msg[:100] + "..." if len(bot_msg) > 100 else bot_msg

            context_parts.append(f"Previous Query {i+1}: {user_msg}")
            context_parts.append(f"Previous Response {i+1}: {bot_msg}")

        context = "\n".join(context_parts)
        if len(context) > 800:
            exchanges_to_keep = 2
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
    ai_mode: Optional[str] = None  # "normal" or "analysis"
    insights: Optional[List[str]] = None  # AI insights (analysis mode)
    recommendations: Optional[List[Dict]] = None  # AI recommendations (analysis mode)
    cached: Optional[bool] = False  # Was this result cached?

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    tenant_code: Optional[str] = None  # Frontend provides tenant code

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
    global system, system_initialized, advisory_handler, schema_manager, cache_manager, ai_mode_manager, enhanced_memory

    with system_lock:
        if system_initialized:
            return True

        if not SYSTEM_AVAILABLE:
            print("TextToSQLSystem not available")
            return False

        try:
            print("Initializing TextToSQLSystem (this may take a moment)...")
            system = TextToSQLSystem()
            csv_file = "data/enhanced_db_schema.csv"

            if not os.path.exists(csv_file):
                print(f"Warning: CSV file not found: {csv_file}")
                return False

            success = system.initialize_system(csv_file)
            if not success:
                print("Failed to initialize TextToSQLSystem")
                return False

            # Initialize Redis Cache Manager
            if CACHE_MANAGER_AVAILABLE and cache_manager is None:
                print("Initializing Redis Cache Manager...")
                cache_manager = get_cache_manager()
                stats = cache_manager.get_cache_stats()
                print(f"[OK] Cache Manager initialized: {stats['cache_type']}")

            # Initialize AI Mode Manager
            if AI_MODE_MANAGER_AVAILABLE and ai_mode_manager is None:
                print("Initializing AI Mode Manager...")
                ai_mode_manager = get_ai_mode_manager()
                print("[OK] AI Mode Manager initialized (Auto-mode enabled)")

            # Initialize Enhanced Conversation Memory (FOLLOW-UP FIX)
            if ENHANCED_MEMORY_AVAILABLE and enhanced_memory is None:
                print("Initializing Enhanced Conversation Memory...")
                enhanced_memory = get_enhanced_memory()
                print("[OK] Enhanced Memory initialized (Follow-up questions enabled)")

            # DISABLED: Advisory Mode and Schema Manager
            # Uncomment below to re-enable these features
            # if ADVISORY_MODE_AVAILABLE and advisory_handler is None:
            #     print("Initializing Advisory Mode Handler...")
            #     advisory_handler = AdvisoryModeHandler(text_to_sql_system=system)
            #     print("Advisory Mode Handler initialized!")
            #
            # if SCHEMA_MANAGER_AVAILABLE and schema_manager is None:
            #     print("Initializing Schema Manager...")
            #     schema_manager = SchemaManager()
            #     print("Schema Manager initialized!")

            system_initialized = True
            print("[OK] TextToSQLSystem initialized successfully!")
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

def load_dashboard_data_real(tenant_code: Optional[str] = None):
    """
    Load dashboard data with Redis caching
    Persistent cache across server restarts if Redis is available
    """
    # SIMPLE MULTI-TENANT: Use provided tenant_code or default
    if not tenant_code:
        tenant_code = DEFAULT_TENANT_CODE

    print(f"[MULTI-TENANT] Loading dashboard for tenant: {tenant_code}")

    # Try Redis cache first
    if CACHE_MANAGER_AVAILABLE and cache_manager:
        cached_data = cache_manager.get_dashboard_data(tenant_code)
        if cached_data:
            return cached_data

    if not ensure_system_ready() or not system:
        return get_fallback_dashboard_data()

    try:
        dashboard_data = {}

        # Basic Statistics with TENANT FILTERING
        basic_queries = [
            ("Total Users", f"SELECT COUNT(*) as count FROM UserRecords WHERE TenantCode = '{tenant_code}'"),
            ("Active Users", f"SELECT COUNT(*) as count FROM UserRecords WHERE TenantCode = '{tenant_code}' AND AccountEnabled = 1"),
            ("Licensed Users", f"SELECT COUNT(*) as count FROM UserRecords WHERE TenantCode = '{tenant_code}' AND IsLicensed = 1"),
            ("Countries", f"SELECT COUNT(DISTINCT Country) as count FROM UserRecords WHERE TenantCode = '{tenant_code}' AND Country IS NOT NULL"),
            ("Inactive Users", f"SELECT COUNT(*) as count FROM UserRecords WHERE TenantCode = '{tenant_code}' AND AccountEnabled = 0"),
            ("Guest Users", f"SELECT COUNT(*) as count FROM UserRecords WHERE TenantCode = '{tenant_code}' AND UserType = 'Guest'"),
            ("Admin Users", f"SELECT COUNT(*) as count FROM UserRecords WHERE TenantCode = '{tenant_code}' AND IsAdmin = 1"),
        ]
        
        for label, query in basic_queries:
            try:
                # TENANT SECURITY: Execute with tenant code
                success, result, execution_info = system.sql_executor.execute_query_secure(
                    query, tenant_code, "dashboard"
                )
                if success and result and len(result) > 0 and 'count' in result[0]:
                    dashboard_data[label] = result[0]['count']
                else:
                    dashboard_data[label] = 0
            except Exception as e:
                print(f"Error executing query for {label}: {e}")
                dashboard_data[label] = 0
        
        # Advanced Analytics Queries with TENANT FILTERING
        analytics_queries = {
            'Countries_Data': f"""
                SELECT TOP 15 Country, COUNT(*) as UserCount,
                       SUM(CASE WHEN AccountEnabled = 1 THEN 1 ELSE 0 END) as ActiveUsers,
                       SUM(CASE WHEN IsLicensed = 1 THEN 1 ELSE 0 END) as LicensedUsers
                FROM UserRecords
                WHERE TenantCode = '{tenant_code}' AND Country IS NOT NULL
                GROUP BY Country
                ORDER BY UserCount DESC
            """,

            'Departments_Data': f"""
                SELECT TOP 15 Department, COUNT(*) as UserCount,
                       SUM(CASE WHEN AccountEnabled = 1 THEN 1 ELSE 0 END) as ActiveUsers,
                       AVG(CAST(EmailSent_D30 as FLOAT)) as AvgEmailsSent30D
                FROM UserRecords
                WHERE TenantCode = '{tenant_code}' AND Department IS NOT NULL
                GROUP BY Department
                ORDER BY UserCount DESC
            """,

            'License_Analysis': f"""
                SELECT l.Name as LicenseName, l.TotalUnits, l.ConsumedUnits,
                       l.ActualCost, l.Status,
                       (CAST(l.ConsumedUnits as FLOAT) / NULLIF(l.TotalUnits, 0) * 100) as UtilizationPercent
                FROM Licenses l
                WHERE l.TenantCode = '{tenant_code}' AND l.TotalUnits > 0
                ORDER BY l.ActualCost DESC
            """
        }
        
        # Execute analytics queries with TENANT SECURITY
        for key, query in analytics_queries.items():
            try:
                success, result, execution_info = system.sql_executor.execute_query_secure(
                    query, tenant_code, "dashboard"
                )
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

        # Cache the results in Redis (300 seconds = 5 minutes)
        if CACHE_MANAGER_AVAILABLE and cache_manager:
            cache_manager.store_dashboard_data(tenant_code, dashboard_data, ttl=300)
            print(f"[OK] Dashboard data cached for tenant: {tenant_code}")

        return dashboard_data
        
    except Exception as e:
        print(f"Error loading dashboard data: {e}")
        return get_fallback_dashboard_data()

def get_fallback_dashboard_data():
    """Fallback dashboard data - returns empty structure when database unavailable"""
    # NO HARDCODED DATA - Return empty structure instead
    return {
        'Total Users': 0, 'Active Users': 0, 'Licensed Users': 0,
        'Countries': 0, 'Inactive Users': 0, 'Guest Users': 0, 'Admin Users': 0,
        'Countries_Data': [],
        'Departments_Data': [],
        'License_Analysis': [],
        'error': 'Database connection unavailable. Please ensure the system is initialized.'
    }

@app.get("/")
async def root():
    """Health check with feature status"""
    cache_stats = None
    if CACHE_MANAGER_AVAILABLE and cache_manager:
        cache_stats = cache_manager.get_cache_stats()

    return {
        "message": "365 Tune Bot FastAPI - Real Data Service (ALL APIs ENABLED)",
        "status": "running",
        "system_initialized": system_initialized,
        "version": "3.0.0 (Phase 2)",
        "active_endpoints": [
            "/",
            "/health",
            "/api/chat",
            "/api/query",
            "/api/dashboard",
            "/api/chart/{chart_type}",
            "/api/licenses",
            "/api/security-score",
            "/api/insights",
            "/api/insights/enhanced",
            "/api/scoring/comprehensive",
            "/api/memory/debug/{session_id}",
            "/api/memory/sessions",
            "/api/schema/tables",
            "/api/schema/tables/{table_name}",
            "/api/schema/columns",
            "/api/schema/search",
            "/api/schema/export/csv",
            "/api/schema/import/csv",
            "/api/schema/statistics",
            "/api/cache/stats",
            "/api/cache/clear",
            "/api/cache/session/{session_id}"
        ],
        "note": "All API endpoints are now enabled"
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

# ============================================================================
# API ENDPOINTS - All endpoints enabled
# ============================================================================
@app.post("/api/query", response_model=QueryResponse)
async def process_query(request: QueryRequest, conversation_context: str = "", session_id: str = "default", tenant_code: str = None, resolved_refs: Dict = None):
    """
    Process natural language query with enhanced memory for follow-up questions
    Features: Query result caching, conversation persistence, reference resolution, intelligent AI mode routing
    """

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

        # DYNAMIC TENANT: Use provided tenant code or default
        if tenant_code is None:
            tenant_code = DEFAULT_TENANT_CODE

        print(f"[MULTI-TENANT] Processing query for tenant: {tenant_code}")

        # Check query result cache first
        cached_result = None
        if CACHE_MANAGER_AVAILABLE and cache_manager:
            cached_result = cache_manager.get_query_result(request.query, tenant_code)
            if cached_result:
                processing_time = time.time() - start_time
                print(f"[CACHE HIT] Returning cached result for query: {request.query[:50]}...")
                return QueryResponse(
                    success=True,
                    processing_time=float(processing_time),
                    result_count=cached_result.get("result_count", 0),
                    final_answer=cached_result.get("final_answer", ""),
                    sql_query=cached_result.get("sql_query", ""),
                    results=cached_result.get("results", [])[:10],
                    cached=True,
                    ai_mode=cached_result.get("ai_mode", "normal")
                )

        # Use the real system with conversation context, session_id, and DYNAMIC TENANT CODE
        result = system.process_query(request.query, conversation_context, session_id=session_id, tenant_code=tenant_code)
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

        # Use AI Mode Manager for intelligent result processing
        final_answer = ""
        ai_mode_info = {}

        if AI_MODE_MANAGER_AVAILABLE and ai_mode_manager and sample_results:
            print("Using AI Mode Manager for result processing...")
            try:
                # Auto-detect mode and process results intelligently
                ai_result = ai_mode_manager.process_query_auto(
                    request.query,
                    sql_query,
                    sample_results,
                    execution_info
                )

                final_answer = ai_result.get("answer", "")
                ai_mode_info = {
                    "mode": ai_result.get("detected_mode", "unknown"),
                    "auto_mode": ai_result.get("auto_mode", False)
                }

                # If Analysis mode, include recommendations
                if ai_result.get("mode") == "analysis":
                    ai_mode_info["insights"] = ai_result.get("insights", [])
                    ai_mode_info["recommendations"] = ai_result.get("recommendations", [])

                print(f"AI Mode: {ai_mode_info.get('mode', 'unknown').upper()}")

            except Exception as e:
                print(f"AI Mode Manager error: {e}")
                # Fall back to old method
                final_answer = result.get("step_4_final_answer", {}).get("answer", "")
        else:
            # Fallback to old result processor
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

        # Prepare response
        response = QueryResponse(
            success=True,
            processing_time=float(processing_time),
            result_count=int(result_count),
            final_answer=str(final_answer or "Query processed successfully"),
            sql_query=str(sql_query) if sql_query else None,
            results=clean_sample_results,
            vector_search_results=vector_results[:5] if vector_results else None,
            execution_info=str(execution_info) if execution_info else None,
            cached=False,
            ai_mode=ai_mode_info.get("mode", "normal"),
            insights=ai_mode_info.get("insights", []) if ai_mode_info.get("mode") == "analysis" else None,
            recommendations=ai_mode_info.get("recommendations", []) if ai_mode_info.get("mode") == "analysis" else None
        )

        # Cache the successful query result for 5 minutes
        if CACHE_MANAGER_AVAILABLE and cache_manager and result_count > 0:
            cache_data = {
                "result_count": result_count,
                "final_answer": final_answer,
                "sql_query": sql_query,
                "results": clean_sample_results,
                "ai_mode": ai_mode_info.get("mode", "normal")
            }
            cache_manager.store_query_result(
                request.query,
                tenant_code,
                clean_sample_results,
                sql_query,
                ttl=300  # 5 minutes
            )

        return response
        
    except Exception as e:
        return QueryResponse(
            success=False,
            processing_time=0.0,
            result_count=0,
            final_answer="",
            error=str(e)
        )

@app.get("/api/dashboard")
async def get_dashboard_data(tenant_code: Optional[str] = None):
    """Get comprehensive dashboard metrics using real data with simple multi-tenant support"""

    try:
        # SIMPLE MULTI-TENANT: Load dashboard data with tenant_code parameter
        dashboard_data = load_dashboard_data_real(tenant_code)
        
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
async def get_chart_data(chart_type: str, tenant_code: Optional[str] = None):
    """Get data for charts using real data with simple multi-tenant support"""

    try:
        # SIMPLE MULTI-TENANT: Load chart data with tenant_code parameter
        dashboard_data = load_dashboard_data_real(tenant_code)
        
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
    """Enhanced chatbot endpoint using real system with multi-tenant support"""

    try:
        start_time = time.time()
        session_id = request.session_id or str(uuid.uuid4())
        message_lower = request.message.lower()

        # Ensure system is ready
        if not ensure_system_ready():
            return ChatResponse(
                success=False,
                message="System is initializing. Please try again in a moment.",
                processing_time=time.time() - start_time,
                session_id=session_id,
                error="System not ready"
            )

        # SIMPLE MULTI-TENANT: Use tenant_code from request or default
        tenant_code = request.tenant_code or DEFAULT_TENANT_CODE
        print(f"[MULTI-TENANT] Processing chat for tenant: {tenant_code}")

        # ADVISORY MODE DISABLED - Uncomment below to re-enable
        # if ADVISORY_MODE_AVAILABLE and advisory_handler:
        #     if advisory_handler.should_enter_advisory_mode(request.message, session_id):
        #         print(f"Advisory Mode activated for session {session_id}")
        #         advisory_response = await advisory_handler.handle_advisory_query(
        #             request.message,
        #             session_id
        #         )
        #         add_to_conversation_memory(
        #             session_id,
        #             request.message,
        #             advisory_response.get('message', '')
        #         )
        #         return ChatResponse(
        #             success=advisory_response.get('success', True),
        #             message=advisory_response.get('message', ''),
        #             processing_time=advisory_response.get('processing_time', time.time() - start_time),
        #             result_count=advisory_response.get('opportunities_count', 0),
        #             session_id=session_id,
        #             results=advisory_response.get('results', [])
        #         )

        # Standard text-to-SQL mode
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
                # Use Enhanced Memory for follow-up questions
                context = ""
                resolved_refs = None

                if ENHANCED_MEMORY_AVAILABLE and enhanced_memory:
                    # Check for reference resolution (e.g., "show me those users")
                    resolved_refs = enhanced_memory.resolve_references(session_id, request.message)

                    if resolved_refs:
                        ref_type = resolved_refs['type']
                        print(f"[FOLLOW-UP] Resolved reference: {ref_type}")

                        # Build augmented context with resolved references
                        context_parts = []

                        # Handle users with stored IDs
                        if ref_type == 'users' and resolved_refs.get('user_ids'):
                            user_ids = resolved_refs['user_ids']
                            ids_str = "', '".join(user_ids[:20])  # Max 20
                            context_parts.append(f"PREVIOUS RESULT - User IDs: {ids_str}")
                            context_parts.append(f"SQL HINT: WHERE UserID IN ('{ids_str}')")
                            print(f"[FOLLOW-UP] Resolved to {len(user_ids)} users")

                        # NEW: Handle users by context (for COUNT query follow-ups)
                        elif ref_type == 'users_by_context':
                            hints = []

                            if resolved_refs.get('group_filter'):
                                group_name = resolved_refs['group_filter']
                                context_parts.append(f"PREVIOUS CONTEXT - Group: {group_name}")
                                hints.append(f"ur.GroupIdsCsv LIKE '%{group_name}%' OR g.DisplayName LIKE '%{group_name}%'")
                                print(f"[FOLLOW-UP] Resolved to users in group: {group_name}")

                            if resolved_refs.get('country_filter'):
                                country = resolved_refs['country_filter']
                                context_parts.append(f"PREVIOUS CONTEXT - Country: {country}")
                                hints.append(f"Country = '{country}'")
                                print(f"[FOLLOW-UP] Resolved to users in country: {country}")

                            if resolved_refs.get('department_filter'):
                                dept = resolved_refs['department_filter']
                                context_parts.append(f"PREVIOUS CONTEXT - Department: {dept}")
                                hints.append(f"Department = '{dept}'")
                                print(f"[FOLLOW-UP] Resolved to users in department: {dept}")

                            if hints:
                                context_parts.append(f"SQL HINT: WHERE {' AND '.join(hints)}")

                            # Add instruction to show users with licenses
                            if 'license' in request.message.lower():
                                context_parts.append("INSTRUCTION: Join UserRecords with Licenses table to show user licenses")
                                context_parts.append("SQL PATTERN: SELECT ur.UserID, ur.DisplayName, l.Name FROM UserRecords ur JOIN Licenses l ON ur.Licenses LIKE '%'+CAST(l.Id AS VARCHAR(50))+'%'")

                        elif ref_type == 'groups' and resolved_refs.get('group_names'):
                            group_names = resolved_refs['group_names']
                            names_str = "', '".join(group_names[:20])
                            context_parts.append(f"PREVIOUS RESULT - Group Names: {names_str}")
                            context_parts.append(f"SQL HINT: WHERE DisplayName IN ('{names_str}')")
                            print(f"[FOLLOW-UP] Resolved to {len(group_names)} groups")

                        elif ref_type == 'licenses' and resolved_refs.get('license_names'):
                            license_names = resolved_refs['license_names']
                            names_str = "', '".join(license_names[:20])
                            context_parts.append(f"PREVIOUS RESULT - License Names: {names_str}")
                            context_parts.append(f"SQL HINT: WHERE Name IN ('{names_str}')")
                            print(f"[FOLLOW-UP] Resolved to {len(license_names)} licenses")

                        elif ref_type == 'departments' and resolved_refs.get('departments'):
                            departments = resolved_refs['departments']
                            depts_str = "', '".join(departments[:20])
                            context_parts.append(f"PREVIOUS RESULT - Departments: {depts_str}")
                            context_parts.append(f"SQL HINT: WHERE Department IN ('{depts_str}')")
                            print(f"[FOLLOW-UP] Resolved to {len(departments)} departments")

                        elif ref_type == 'countries' and resolved_refs.get('countries'):
                            countries = resolved_refs['countries']
                            countries_str = "', '".join(countries[:20])
                            context_parts.append(f"PREVIOUS RESULT - Countries: {countries_str}")
                            context_parts.append(f"SQL HINT: WHERE Country IN ('{countries_str}')")
                            print(f"[FOLLOW-UP] Resolved to {len(countries)} countries")

                        # Combine with regular conversation context
                        regular_context = enhanced_memory.get_conversation_text(session_id)
                        if context_parts:
                            context = "\n".join(context_parts)
                            if regular_context:
                                context = context + "\n\n" + regular_context
                        else:
                            context = regular_context
                    else:
                        # No references to resolve, use regular context
                        context = enhanced_memory.get_conversation_text(session_id)
                else:
                    # Fallback to old context system
                    context = get_conversation_context(session_id)
                    resolved_refs = None

                print(f"Processing query: {request.message}")
                if context:
                    print(f"Using conversation context preview: {context[:100]}...")

                # DYNAMIC TENANT: Process query with dynamic tenant code and resolved references
                query_result = await process_query(
                    QueryRequest(query=request.message),
                    context,
                    session_id,
                    tenant_code,
                    resolved_refs  # Pass resolved references
                )
                processing_time = time.time() - start_time
                
                print(f"Query result success: {query_result.success}")
                if hasattr(query_result, 'final_answer'):
                    print(f"Final answer: {query_result.final_answer[:100]}...")
                
                if query_result.success and hasattr(query_result, 'final_answer') and query_result.final_answer:
                    message = query_result.final_answer

                    # Store results in enhanced memory for follow-up questions
                    if ENHANCED_MEMORY_AVAILABLE and enhanced_memory:
                        # Get SQL query from query_result
                        sql_query = getattr(query_result, 'sql_query', '')
                        results = getattr(query_result, 'results', [])

                        enhanced_memory.store_query_result(
                            session_id=session_id,
                            user_query=request.message,
                            sql_query=sql_query,
                            results=results,
                            bot_response=message
                        )
                        print(f"[MEMORY] Stored {len(results)} results for follow-up questions")
                    else:
                        # Fallback to old memory system
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

@app.get("/api/insights")
async def get_ai_insights():
    """Get AI-powered insights about license usage, costs, and optimization opportunities"""

    try:
        if not INSIGHTS_AVAILABLE:
            return {
                "success": False,
                "error": "AI Insights module not available"
            }

        print("Generating AI insights...")
        insights_generator = AIInsightsGenerator()
        result = insights_generator.generate_insights()

        print(f"Insights generated successfully: {result.get('success', False)}")
        return result

    except Exception as e:
        print(f"Error generating insights: {e}")
        return {
            "success": False,
            "error": str(e)
        }

@app.get("/api/insights/enhanced")
async def get_enhanced_ai_insights():
    """Get enhanced AI-powered insights with anomaly detection, priority ranking, and advanced analytics"""

    try:
        if not ENHANCED_INSIGHTS_AVAILABLE:
            return {
                "success": False,
                "error": "Enhanced AI Insights module not available"
            }

        print("Generating enhanced AI insights...")
        insights_generator = EnhancedAIInsights()
        result = insights_generator.generate_insights()

        print(f"Enhanced insights generated successfully: {result.get('success', False)}")
        return result

    except Exception as e:
        print(f"Error generating enhanced insights: {e}")
        import traceback
        traceback.print_exc()
        return {
            "success": False,
            "error": str(e)
        }

@app.get("/api/scoring/comprehensive")
async def get_comprehensive_scoring(tenant_code: Optional[str] = None):
    """Get comprehensive tenant security & compliance scoring"""

    try:
        if not COMPREHENSIVE_SCORING_AVAILABLE:
            return {
                "success": False,
                "error": "Comprehensive Scoring module not available"
            }

        # Use provided tenant_code or default
        if not tenant_code:
            tenant_code = DEFAULT_TENANT_CODE

        print(f"[MULTI-TENANT] Generating comprehensive scoring for tenant: {tenant_code}")
        scorer = ComprehensiveTenantScoring(tenant_code=tenant_code)
        result = scorer.generate_comprehensive_score()

        # Add tenant info to result
        result['tenant_code'] = tenant_code

        print(f"Comprehensive scoring completed: {result.get('success', False)}")
        if result.get('success'):
            print(f"Overall Score: {result.get('overall_score', 0)}/100")
            print(f"Maturity Level: {result.get('maturity_level', {}).get('name', 'Unknown')}")

        return result

    except Exception as e:
        print(f"Error generating comprehensive scoring: {e}")
        import traceback
        traceback.print_exc()
        return {
            "success": False,
            "error": str(e)
        }

@app.get("/api/cost/forecast")
async def get_cost_forecast(tenant_code: Optional[str] = None):
    """Get comprehensive cost analysis and forecasting"""

    try:
        if not COST_FORECASTING_AVAILABLE:
            return {
                "success": False,
                "error": "Cost Forecasting Engine not available"
            }

        if not tenant_code:
            tenant_code = DEFAULT_TENANT_CODE

        print(f"[COST FORECAST] Generating forecast for tenant: {tenant_code}")
        engine = CostForecastingEngine(tenant_code=tenant_code)
        report = engine.generate_comprehensive_forecast()

        print(f"Cost forecast generated successfully")
        return {
            "success": True,
            **report
        }

    except Exception as e:
        print(f"Error generating cost forecast: {e}")
        import traceback
        traceback.print_exc()
        return {
            "success": False,
            "error": str(e)
        }

@app.get("/api/cost/current-month")
async def get_current_month_cost(tenant_code: Optional[str] = None):
    """Get current month cost breakdown"""

    try:
        if not COST_FORECASTING_AVAILABLE:
            return {
                "success": False,
                "error": "Cost Forecasting Engine not available"
            }

        if not tenant_code:
            tenant_code = DEFAULT_TENANT_CODE

        engine = CostForecastingEngine(tenant_code=tenant_code)
        current = engine.get_current_monthly_cost()

        return {
            "success": True,
            "data": current
        }

    except Exception as e:
        print(f"Error getting current month cost: {e}")
        return {
            "success": False,
            "error": str(e)
        }

@app.get("/api/cost/license-breakdown")
async def get_license_cost_breakdown(tenant_code: Optional[str] = None):
    """Get cost breakdown by license type"""

    try:
        if not COST_FORECASTING_AVAILABLE:
            return {
                "success": False,
                "error": "Cost Forecasting Engine not available"
            }

        if not tenant_code:
            tenant_code = DEFAULT_TENANT_CODE

        engine = CostForecastingEngine(tenant_code=tenant_code)
        breakdown = engine.get_license_breakdown_by_type()

        return {
            "success": True,
            "data": breakdown
        }

    except Exception as e:
        print(f"Error getting license breakdown: {e}")
        return {
            "success": False,
            "error": str(e)
        }

@app.get("/api/licenses")
async def get_license_data(tenant_code: Optional[str] = None):
    """Get license data and metrics with simple multi-tenant support"""

    try:
        # SIMPLE MULTI-TENANT: Use tenant_code parameter or default
        if not tenant_code:
            tenant_code = DEFAULT_TENANT_CODE

        print(f"[MULTI-TENANT] Loading licenses for tenant: {tenant_code}")

        if not ensure_system_ready() or not system:
            # NO HARDCODED DATA - Return empty structure when database unavailable
            return {
                "success": False,
                "licenses": [],
                "error": "System not initialized. Please ensure database connection is available.",
                "source": "Error"
            }

        # TENANT FILTERING in query
        query = f"""
            SELECT l.Name as LicenseName, l.TotalUnits, l.ConsumedUnits,
                   l.ActualCost, l.Status,
                   (CAST(l.ConsumedUnits as FLOAT) / NULLIF(l.TotalUnits, 0) * 100) as UtilizationPercent
            FROM Licenses l
            WHERE l.TenantCode = '{tenant_code}' AND l.TotalUnits > 0
            ORDER BY l.ActualCost DESC
        """

        # TENANT SECURITY: Execute with tenant code
        success, result, execution_info = system.sql_executor.execute_query_secure(
            query, tenant_code, "licenses"
        )
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

# ============================================================================
# NEW EXTENSION: SCHEMA MANAGEMENT ENDPOINTS
# ============================================================================

class SchemaTableRequest(BaseModel):
    table_name: str
    description: str
    business_context: Optional[str] = ""
    tags: Optional[List[str]] = []

class SchemaColumnRequest(BaseModel):
    table_name: str
    column_name: str
    description: str
    data_type: Optional[str] = ""
    example_values: Optional[str] = ""
    business_rules: Optional[str] = ""

@app.get("/api/schema/tables")
async def get_all_tables():
    """Get all tables with custom descriptions"""
    if not SCHEMA_MANAGER_AVAILABLE or not schema_manager:
        raise HTTPException(status_code=503, detail="Schema Manager not available")

    try:
        tables = schema_manager.get_all_tables()
        stats = schema_manager.get_statistics()
        return {
            "success": True,
            "tables": tables,
            "statistics": stats
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

@app.get("/api/schema/tables/{table_name}")
async def get_table_details(table_name: str):
    """Get detailed information about a specific table"""
    if not SCHEMA_MANAGER_AVAILABLE or not schema_manager:
        raise HTTPException(status_code=503, detail="Schema Manager not available")

    try:
        table = schema_manager.get_table_description(table_name)
        if not table:
            raise HTTPException(status_code=404, detail=f"Table {table_name} not found")

        columns = schema_manager.get_all_columns(table_name)
        return {
            "success": True,
            "table": table,
            "columns": columns
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

@app.post("/api/schema/tables")
async def add_or_update_table(request: SchemaTableRequest):
    """Add or update table description"""
    if not SCHEMA_MANAGER_AVAILABLE or not schema_manager:
        raise HTTPException(status_code=503, detail="Schema Manager not available")

    try:
        result = schema_manager.add_table_description(
            table_name=request.table_name,
            description=request.description,
            business_context=request.business_context or "",
            tags=request.tags or []
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

@app.post("/api/schema/columns")
async def add_or_update_column(request: SchemaColumnRequest):
    """Add or update column description"""
    if not SCHEMA_MANAGER_AVAILABLE or not schema_manager:
        raise HTTPException(status_code=503, detail="Schema Manager not available")

    try:
        result = schema_manager.add_column_description(
            table_name=request.table_name,
            column_name=request.column_name,
            description=request.description,
            data_type=request.data_type or "",
            example_values=request.example_values or "",
            business_rules=request.business_rules or ""
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

@app.delete("/api/schema/tables/{table_name}")
async def delete_table(table_name: str):
    """Delete a table and all its columns"""
    if not SCHEMA_MANAGER_AVAILABLE or not schema_manager:
        raise HTTPException(status_code=503, detail="Schema Manager not available")

    try:
        result = schema_manager.delete_table(table_name)
        if not result["success"]:
            raise HTTPException(status_code=404, detail=result["message"])
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

@app.delete("/api/schema/columns/{table_name}/{column_name}")
async def delete_column(table_name: str, column_name: str):
    """Delete a specific column"""
    if not SCHEMA_MANAGER_AVAILABLE or not schema_manager:
        raise HTTPException(status_code=503, detail="Schema Manager not available")

    try:
        result = schema_manager.delete_column(table_name, column_name)
        if not result["success"]:
            raise HTTPException(status_code=404, detail=result["message"])
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

@app.get("/api/schema/search")
async def search_schema(q: str):
    """Search for tables and columns matching a search term"""
    if not SCHEMA_MANAGER_AVAILABLE or not schema_manager:
        raise HTTPException(status_code=503, detail="Schema Manager not available")

    try:
        if not q or len(q) < 2:
            raise HTTPException(status_code=400, detail="Search query must be at least 2 characters")

        results = schema_manager.search_descriptions(q)
        return {
            "success": True,
            "query": q,
            "results": results
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

@app.get("/api/schema/export/csv")
async def export_schema_csv():
    """Export all schema descriptions to CSV"""
    if not SCHEMA_MANAGER_AVAILABLE or not schema_manager:
        raise HTTPException(status_code=503, detail="Schema Manager not available")

    try:
        result = schema_manager.export_to_csv()
        if not result["success"]:
            raise HTTPException(status_code=500, detail=result["message"])
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

@app.post("/api/schema/import/csv")
async def import_schema_csv(csv_file_path: str):
    """Import schema descriptions from CSV file"""
    if not SCHEMA_MANAGER_AVAILABLE or not schema_manager:
        raise HTTPException(status_code=503, detail="Schema Manager not available")

    try:
        if not os.path.exists(csv_file_path):
            raise HTTPException(status_code=404, detail=f"CSV file not found: {csv_file_path}")

        result = schema_manager.import_from_csv(csv_file_path)
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

@app.get("/api/schema/statistics")
async def get_schema_statistics():
    """Get statistics about custom schema descriptions"""
    if not SCHEMA_MANAGER_AVAILABLE or not schema_manager:
        raise HTTPException(status_code=503, detail="Schema Manager not available")

    try:
        stats = schema_manager.get_statistics()
        return {
            "success": True,
            "statistics": stats
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

# ============================================================================
# END OF SCHEMA MANAGEMENT ENDPOINTS
# ============================================================================

# ============================================================================
# CACHE MANAGEMENT ENDPOINTS
# ============================================================================

@app.get("/api/cache/stats")
async def get_cache_statistics():
    """
    Get cache statistics
    Shows cache performance, hit rates, and storage info
    """
    if not CACHE_MANAGER_AVAILABLE or not cache_manager:
        return {
            "success": False,
            "error": "Cache manager not available"
        }

    try:
        stats = cache_manager.get_cache_stats()
        return {
            "success": True,
            "cache_statistics": stats,
            "features": {
                "conversation_memory": True,
                "query_result_caching": True,
                "dashboard_caching": True,
                "session_management": True
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

@app.post("/api/cache/clear")
async def clear_cache(tenant_code: Optional[str] = None, clear_all: bool = False):
    """
    Clear cache entries
    - tenant_code: Clear cache for specific tenant
    - clear_all: Clear entire cache (use with caution!)
    """
    if not CACHE_MANAGER_AVAILABLE or not cache_manager:
        return {
            "success": False,
            "error": "Cache manager not available"
        }

    try:
        if clear_all:
            success = cache_manager.clear_all_cache()
            return {
                "success": success,
                "message": "All cache cleared" if success else "Failed to clear cache"
            }
        elif tenant_code:
            success = cache_manager.clear_tenant_cache(tenant_code)
            return {
                "success": success,
                "message": f"Cache cleared for tenant {tenant_code}" if success else "Failed to clear tenant cache"
            }
        else:
            return {
                "success": False,
                "error": "Please specify tenant_code or set clear_all=true"
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

@app.get("/api/cache/session/{session_id}")
async def get_session_conversation(session_id: str):
    """
    Get conversation history for a session from cache
    """
    if not CACHE_MANAGER_AVAILABLE or not cache_manager:
        return {
            "success": False,
            "error": "Cache manager not available"
        }

    try:
        memory = cache_manager.get_conversation_memory(session_id)
        if memory:
            return {
                "success": True,
                "session_id": session_id,
                "conversation_count": len(memory),
                "conversations": memory
            }
        else:
            return {
                "success": True,
                "session_id": session_id,
                "conversation_count": 0,
                "conversations": []
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

# ============================================================================
# END OF PHASE 2 CACHE MANAGEMENT ENDPOINTS
# ============================================================================

if __name__ == "__main__":
    print("Starting 365 Tune Bot FastAPI with Real Data...")
    uvicorn.run(app, host="127.0.0.1", port=8000)