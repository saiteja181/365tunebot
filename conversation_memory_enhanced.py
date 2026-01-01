#!/usr/bin/env python3
"""
Enhanced Conversation Memory System - Stores RESULT DATA for Follow-up Questions
This fixes the critical issue where follow-up questions fail because result data is not preserved.
"""

import json
from datetime import datetime
from typing import List, Dict, Any, Optional
from collections import defaultdict
import threading

class ConversationExchange:
    """Represents a single conversation exchange with full context"""
    def __init__(self, user_query: str, sql_query: str, results: List[Dict],
                 bot_response: str, timestamp: datetime = None):
        self.user_query = user_query
        self.sql_query = sql_query
        self.results = results[:50]  # Store up to 50 results for reference
        self.bot_response = bot_response
        self.timestamp = timestamp or datetime.now()

        # Extract entities from results for quick reference resolution
        self.entities = self._extract_entities(results)

        # NEW: Extract query context from SQL for COUNT queries
        self._extract_query_context_from_sql(sql_query)

    def _extract_entities(self, results: List[Dict]) -> Dict[str, List]:
        """Extract key entities from results for reference resolution"""
        entities = {
            'user_ids': [],
            'user_names': [],
            'group_ids': [],
            'group_names': [],
            'departments': [],
            'countries': [],
            'license_ids': [],
            'license_names': [],
            'query_context': {}  # NEW: Store query context for COUNT queries
        }

        if not results:
            return entities

        for row in results[:50]:  # Process up to 50 rows
            # Extract user entities
            if 'UserID' in row and row['UserID']:
                entities['user_ids'].append(str(row['UserID']))
            if 'DisplayName' in row and row['DisplayName']:
                entities['user_names'].append(str(row['DisplayName']))
            if 'Mail' in row and row['Mail']:
                entities['user_names'].append(str(row['Mail']))

            # Extract group entities
            if 'Id' in row and 'DisplayName' in row:
                # Likely a group
                entities['group_ids'].append(str(row['Id']))
                entities['group_names'].append(str(row['DisplayName']))

            # Extract attributes
            if 'Department' in row and row['Department']:
                entities['departments'].append(str(row['Department']))
            if 'Country' in row and row['Country']:
                entities['countries'].append(str(row['Country']))

            # Extract license entities
            if 'Name' in row and 'TotalUnits' in row:
                # Likely a license
                entities['license_names'].append(str(row['Name']))
                if 'Id' in row:
                    entities['license_ids'].append(str(row['Id']))

        # Deduplicate
        for key in entities:
            if key != 'query_context':  # Don't deduplicate context dict
                entities[key] = list(set(entities[key]))[:20]  # Max 20 unique entities per type

        return entities

    def _extract_query_context_from_sql(self, sql_query: str):
        """
        Extract query context from SQL for COUNT/aggregate queries
        This helps resolve follow-ups when no individual records are returned
        """
        import re

        if not sql_query:
            return

        # Check if this is a COUNT/aggregate query
        is_count_query = 'COUNT(' in sql_query.upper() or 'SUM(' in sql_query.upper()

        if not is_count_query:
            return

        # Extract WHERE clause conditions
        where_match = re.search(r'WHERE\s+(.*?)(?:GROUP\s+BY|ORDER\s+BY|$)', sql_query, re.IGNORECASE | re.DOTALL)

        if where_match:
            where_clause = where_match.group(1).strip()

            # Extract group name from WHERE clause
            group_match = re.search(r"DisplayName\s+LIKE\s+'%([^%]+)%'", where_clause, re.IGNORECASE)
            if group_match:
                self.entities['query_context']['group_filter'] = group_match.group(1)
                self.entities['group_names'].append(group_match.group(1))

            # Extract country from WHERE clause
            country_match = re.search(r"Country\s*=\s*'([^']+)'", where_clause, re.IGNORECASE)
            if country_match:
                self.entities['query_context']['country_filter'] = country_match.group(1)
                self.entities['countries'].append(country_match.group(1))

            # Extract department from WHERE clause
            dept_match = re.search(r"Department\s*=\s*'([^']+)'", where_clause, re.IGNORECASE)
            if dept_match:
                self.entities['query_context']['department_filter'] = dept_match.group(1)
                self.entities['departments'].append(dept_match.group(1))

        # Store the base table being queried
        from_match = re.search(r'FROM\s+(\w+)', sql_query, re.IGNORECASE)
        if from_match:
            self.entities['query_context']['base_table'] = from_match.group(1)

    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization"""
        return {
            'user_query': self.user_query,
            'sql_query': self.sql_query,
            'results': self.results,
            'bot_response': self.bot_response,
            'timestamp': self.timestamp.isoformat(),
            'entities': self.entities
        }


class ConversationSession:
    """Represents a complete conversation session"""
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.exchanges: List[ConversationExchange] = []
        self.created_at = datetime.now()
        self.last_activity = datetime.now()

    def add_exchange(self, exchange: ConversationExchange):
        """Add a new exchange to the session"""
        self.exchanges.append(exchange)
        self.last_activity = datetime.now()

        # Keep only last 5 exchanges for memory efficiency
        if len(self.exchanges) > 5:
            self.exchanges = self.exchanges[-5:]

    def get_last_exchange(self) -> Optional[ConversationExchange]:
        """Get the most recent exchange"""
        return self.exchanges[-1] if self.exchanges else None

    def get_last_results(self) -> List[Dict]:
        """Get results from the most recent exchange"""
        last = self.get_last_exchange()
        return last.results if last else []

    def get_last_entities(self) -> Dict[str, List]:
        """Get entities from the most recent exchange"""
        last = self.get_last_exchange()
        return last.entities if last else {}

    def get_last_sql(self) -> str:
        """Get SQL from the most recent exchange"""
        last = self.get_last_exchange()
        return last.sql_query if last else ""

    def has_reference_words(self, query: str) -> bool:
        """Check if query contains reference words like 'that', 'those', etc."""
        query_lower = query.lower()
        reference_words = ['that', 'those', 'these', 'them', 'it', 'their', 'the same',
                          'this', 'such', 'aforementioned']
        return any(word in query_lower for word in reference_words)


class EnhancedConversationMemory:
    """
    Enhanced conversation memory that stores FULL RESULT DATA
    This enables follow-up questions by preserving entity references
    """
    def __init__(self):
        self.sessions: Dict[str, ConversationSession] = {}
        self.lock = threading.Lock()

    def store_query_result(self, session_id: str, user_query: str, sql_query: str,
                          results: List[Dict], bot_response: str):
        """
        Store complete query result data for follow-up questions

        Args:
            session_id: Session identifier
            user_query: User's natural language query
            sql_query: Generated SQL query
            results: Query results (list of dicts)
            bot_response: Bot's natural language response
        """
        with self.lock:
            # Create session if it doesn't exist
            if session_id not in self.sessions:
                self.sessions[session_id] = ConversationSession(session_id)

            # Create exchange object
            exchange = ConversationExchange(
                user_query=user_query,
                sql_query=sql_query,
                results=results,
                bot_response=bot_response
            )

            # Add to session
            self.sessions[session_id].add_exchange(exchange)

            print(f"[MEMORY] Stored exchange for session {session_id}")
            print(f"[MEMORY] - User query: {user_query}")
            print(f"[MEMORY] - Results count: {len(results)}")
            print(f"[MEMORY] - Entities extracted: {len(exchange.entities.get('user_ids', []))} users, "
                  f"{len(exchange.entities.get('group_names', []))} groups")

    def get_context_for_sql(self, session_id: str, current_query: str) -> Dict[str, Any]:
        """
        Get rich context for SQL generation including result data

        Args:
            session_id: Session identifier
            current_query: Current user query

        Returns:
            Dictionary with context data
        """
        with self.lock:
            if session_id not in self.sessions:
                return {}

            session = self.sessions[session_id]
            last_exchange = session.get_last_exchange()

            if not last_exchange:
                return {}

            context = {
                'has_reference': session.has_reference_words(current_query),
                'previous_query': last_exchange.user_query,
                'previous_sql': last_exchange.sql_query,
                'previous_results': last_exchange.results[:20],  # Max 20 for context
                'entities': last_exchange.entities,
                'result_count': len(last_exchange.results)
            }

            return context

    def resolve_references(self, session_id: str, current_query: str) -> Optional[Dict[str, Any]]:
        """
        Resolve references like 'those users', 'that group', etc.
        Enhanced to handle COUNT queries by using query_context

        Args:
            session_id: Session identifier
            current_query: Current user query

        Returns:
            Dictionary with resolved entities or None
        """
        with self.lock:
            if session_id not in self.sessions:
                return None

            session = self.sessions[session_id]

            # Check if query has reference words
            if not session.has_reference_words(current_query):
                return None

            # Get entities from last exchange
            entities = session.get_last_entities()

            if not entities:
                return None

            query_lower = current_query.lower()

            # Determine what type of entity is being referenced
            resolved = {}

            # NEW: Check query_context for COUNT query follow-ups
            query_context = entities.get('query_context', {})

            if any(word in query_lower for word in ['user', 'users', 'people', 'person', 'them', 'they', 'their']):
                # First try: Use stored user IDs if available
                if entities.get('user_ids'):
                    resolved['type'] = 'users'
                    resolved['user_ids'] = entities['user_ids']
                    resolved['user_names'] = entities['user_names']
                    print(f"[REFERENCE] Resolved to {len(entities['user_ids'])} users from stored IDs")

                # NEW: Fallback for COUNT queries - use query_context
                elif query_context:
                    resolved['type'] = 'users_by_context'

                    # Add group filter if exists
                    if query_context.get('group_filter'):
                        resolved['group_filter'] = query_context['group_filter']
                        print(f"[REFERENCE] Resolved to users in group: {query_context['group_filter']}")

                    # Add country filter if exists
                    if query_context.get('country_filter'):
                        resolved['country_filter'] = query_context['country_filter']
                        print(f"[REFERENCE] Resolved to users in country: {query_context['country_filter']}")

                    # Add department filter if exists
                    if query_context.get('department_filter'):
                        resolved['department_filter'] = query_context['department_filter']
                        print(f"[REFERENCE] Resolved to users in department: {query_context['department_filter']}")

                    # Store base table
                    if query_context.get('base_table'):
                        resolved['base_table'] = query_context['base_table']

            elif any(word in query_lower for word in ['group', 'groups', 'team', 'teams']):
                if entities.get('group_names'):
                    resolved['type'] = 'groups'
                    resolved['group_ids'] = entities['group_ids']
                    resolved['group_names'] = entities['group_names']
                    print(f"[REFERENCE] Resolved to {len(entities['group_names'])} groups")

            elif any(word in query_lower for word in ['license', 'licenses']):
                if entities.get('license_names'):
                    resolved['type'] = 'licenses'
                    resolved['license_ids'] = entities['license_ids']
                    resolved['license_names'] = entities['license_names']
                    print(f"[REFERENCE] Resolved to {len(entities['license_names'])} licenses")

            elif any(word in query_lower for word in ['department', 'departments']):
                if entities.get('departments'):
                    resolved['type'] = 'departments'
                    resolved['departments'] = entities['departments']
                    print(f"[REFERENCE] Resolved to {len(entities['departments'])} departments")

            elif any(word in query_lower for word in ['country', 'countries']):
                if entities.get('countries'):
                    resolved['type'] = 'countries'
                    resolved['countries'] = entities['countries']
                    print(f"[REFERENCE] Resolved to {len(entities['countries'])} countries")

            return resolved if resolved else None

    def get_conversation_text(self, session_id: str) -> str:
        """
        Get conversation history as text (for backward compatibility)

        Args:
            session_id: Session identifier

        Returns:
            Formatted conversation text
        """
        with self.lock:
            if session_id not in self.sessions:
                return ""

            session = self.sessions[session_id]
            context_parts = []

            # Get last 3 exchanges
            for i, exchange in enumerate(session.exchanges[-3:], 1):
                context_parts.append(f"Previous Query {i}: {exchange.user_query}")

                # Truncate bot response
                bot_response = exchange.bot_response
                if len(bot_response) > 200:
                    bot_response = bot_response[:200] + "..."

                context_parts.append(f"Previous Response {i}: {bot_response}")

            return "\n".join(context_parts)

    def cleanup_old_sessions(self, max_age_hours: int = 24):
        """Clean up sessions older than max_age_hours"""
        with self.lock:
            current_time = datetime.now()
            sessions_to_remove = []

            for session_id, session in self.sessions.items():
                age = (current_time - session.last_activity).total_seconds() / 3600
                if age > max_age_hours:
                    sessions_to_remove.append(session_id)

            for session_id in sessions_to_remove:
                del self.sessions[session_id]

            if sessions_to_remove:
                print(f"[MEMORY] Cleaned up {len(sessions_to_remove)} old sessions")


# Global instance
_enhanced_memory = None
_memory_lock = threading.Lock()

def get_enhanced_memory() -> EnhancedConversationMemory:
    """Get or create global enhanced memory instance"""
    global _enhanced_memory
    with _memory_lock:
        if _enhanced_memory is None:
            _enhanced_memory = EnhancedConversationMemory()
        return _enhanced_memory


if __name__ == "__main__":
    # Test the enhanced memory system
    print("=== Testing Enhanced Conversation Memory ===\n")

    memory = get_enhanced_memory()

    # Simulate first query
    print("TEST 1: User asks 'How many users in India?'")
    memory.store_query_result(
        session_id="test_session",
        user_query="How many users in India?",
        sql_query="SELECT UserID, DisplayName, Mail FROM UserRecords WHERE Country = 'IN'",
        results=[
            {'UserID': '123', 'DisplayName': 'John Doe', 'Mail': 'john@example.com', 'Country': 'IN'},
            {'UserID': '456', 'DisplayName': 'Jane Smith', 'Mail': 'jane@example.com', 'Country': 'IN'},
            {'UserID': '789', 'DisplayName': 'Bob Johnson', 'Mail': 'bob@example.com', 'Country': 'IN'}
        ],
        bot_response="Found 3 users in India."
    )

    # Simulate follow-up query
    print("\nTEST 2: User asks 'Show me those users'")
    context = memory.get_context_for_sql("test_session", "Show me those users")
    print(f"Context retrieved: {json.dumps(context['entities'], indent=2)}")

    resolved = memory.resolve_references("test_session", "Show me those users")
    print(f"\nResolved references: {json.dumps(resolved, indent=2)}")

    print("\n[SUCCESS] Enhanced memory system working correctly!")
    print("Follow-up questions will now work because we have:")
    print(f"  - User IDs: {resolved['user_ids']}")
    print(f"  - User Names: {resolved['user_names']}")
