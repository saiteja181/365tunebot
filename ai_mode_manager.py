#!/usr/bin/env python3
"""
AI Mode Manager - Dual Mode System for Query Processing
Supports Normal Mode (summarization) and Analysis Mode (deep analysis + suggestions)
"""

import json
from typing import Dict, List, Any, Optional
from enum import Enum
import requests
from config import SUBSCRIPTION_KEY, DEPLOYMENT, AZURE_OPENAI_ENDPOINT


class AIMode(Enum):
    """AI Processing Modes"""
    NORMAL = "normal"  # Quick summarization
    ANALYSIS = "analysis"  # Deep analysis with suggestions


class AIModeManager:
    """
    Manages dual AI modes for query result processing:
    - Normal Mode: Fast NLP summarization of results
    - Analysis Mode: Deep analysis with cost optimization suggestions
    """

    def __init__(self):
        self.subscription_key = SUBSCRIPTION_KEY
        self.deployment_name = DEPLOYMENT
        self.endpoint = AZURE_OPENAI_ENDPOINT
        self.api_url = f"{self.endpoint}/openai/deployments/{self.deployment_name}/chat/completions?api-version=2023-05-15"

    def _call_azure_openai(self, messages: List[Dict], temperature: float = 0.3,
                          max_tokens: int = 1000) -> str:
        """Make API call to Azure OpenAI"""
        try:
            headers = {
                "Content-Type": "application/json",
                "api-key": self.subscription_key
            }

            payload = {
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "top_p": 0.95,
                "frequency_penalty": 0,
                "presence_penalty": 0
            }

            response = requests.post(self.api_url, headers=headers, json=payload, timeout=30)
            response.raise_for_status()

            result = response.json()
            return result["choices"][0]["message"]["content"].strip()

        except Exception as e:
            print(f"Error calling Azure OpenAI: {e}")
            return ""

    # ============================================================================
    # NORMAL MODE - Fast Summarization
    # ============================================================================

    def process_normal_mode(self, user_query: str, sql_query: str, results: List[Dict],
                           execution_info: str = "") -> Dict:
        """
        Normal Mode: Quick, clean summarization of query results
        Focus: Answer the user's question clearly and concisely
        """
        if not results:
            return {
                "mode": "normal",
                "success": True,
                "answer": "No results found for your query.",
                "summary": "The query executed successfully but returned no data."
            }

        # Prepare data summary
        result_count = len(results)
        sample_data = results[:5]  # Show first 5 rows

        # Create prompt for normal mode
        prompt = f"""You are a helpful data analyst assistant. The user asked: "{user_query}"

The SQL query returned {result_count} results.

Sample data (first 5 rows):
{json.dumps(sample_data, indent=2, default=str)}

Your task:
1. Provide a clear, direct answer to the user's question
2. Summarize the key findings from the data
3. Use natural language, avoid technical jargon
4. Be concise but informative (2-4 sentences)
5. If showing numbers, format them clearly

Respond in a friendly, conversational tone."""

        messages = [
            {
                "role": "system",
                "content": "You are a data analyst who explains query results in simple, clear language."
            },
            {
                "role": "user",
                "content": prompt
            }
        ]

        # Get AI response
        ai_answer = self._call_azure_openai(messages, temperature=0.3, max_tokens=500)

        if not ai_answer:
            # Fallback response
            ai_answer = self._create_fallback_summary(user_query, results)

        return {
            "mode": "normal",
            "success": True,
            "answer": ai_answer,
            "result_count": result_count,
            "sample_data": sample_data[:3],  # Return top 3 for display
            "execution_info": execution_info
        }

    # ============================================================================
    # ANALYSIS MODE - Deep Analysis with Suggestions
    # ============================================================================

    def process_analysis_mode(self, user_query: str, sql_query: str, results: List[Dict],
                             execution_info: str = "") -> Dict:
        """
        Analysis Mode: Deep analysis with insights and actionable suggestions
        Focus: Provide strategic insights, trends, and optimization recommendations
        """
        if not results:
            return {
                "mode": "analysis",
                "success": True,
                "answer": "No data available for analysis.",
                "insights": [],
                "suggestions": []
            }

        # Prepare comprehensive data for analysis
        result_count = len(results)
        sample_data = results[:10]  # More data for analysis

        # Detect query context (cost, users, licenses, etc.)
        query_context = self._detect_query_context(user_query, results)

        # Create advanced prompt for analysis mode
        prompt = f"""You are a senior data analyst and business consultant specializing in Microsoft 365 cost optimization and license management.

USER QUESTION: "{user_query}"

QUERY CONTEXT: {query_context}

DATA RETRIEVED: {result_count} records

SAMPLE DATA:
{json.dumps(sample_data, indent=2, default=str)}

Your task is to provide a COMPREHENSIVE ANALYSIS with:

1. **EXECUTIVE SUMMARY**: Direct answer to the user's question (2-3 sentences)

2. **KEY INSIGHTS**: Analyze the data and identify:
   - Important patterns or trends
   - Notable statistics or outliers
   - Potential concerns or opportunities

3. **ACTIONABLE RECOMMENDATIONS**: Provide 3-5 specific, actionable suggestions for:
   - Cost optimization opportunities
   - License utilization improvements
   - Risk mitigation strategies
   - Efficiency improvements

4. **IMPACT ASSESSMENT**: For each recommendation, estimate:
   - Potential cost savings (if applicable)
   - Implementation difficulty (Easy/Medium/Hard)
   - Priority level (High/Medium/Low)

Format your response as:

SUMMARY:
[Your executive summary]

INSIGHTS:
• [Insight 1]
• [Insight 2]
• [Insight 3]

RECOMMENDATIONS:
1. [Recommendation 1]
   Impact: [Cost savings/benefit]
   Difficulty: [Easy/Medium/Hard]
   Priority: [High/Medium/Low]

2. [Recommendation 2]
   ...

Be specific, data-driven, and actionable. Use numbers from the data to support your analysis."""

        messages = [
            {
                "role": "system",
                "content": """You are a Microsoft 365 cost optimization expert and data strategist.
You provide deep analysis, identify optimization opportunities, and give actionable recommendations
based on license usage, user activity, and cost data. Your advice saves companies money and improves efficiency."""
            },
            {
                "role": "user",
                "content": prompt
            }
        ]

        # Get AI analysis (higher token limit for detailed response)
        ai_analysis = self._call_azure_openai(messages, temperature=0.4, max_tokens=1500)

        if not ai_analysis:
            # Fallback analysis
            return self._create_fallback_analysis(user_query, results, query_context)

        # Parse the analysis into structured format
        parsed_analysis = self._parse_analysis_response(ai_analysis, results)

        return {
            "mode": "analysis",
            "success": True,
            "answer": parsed_analysis["summary"],
            "full_analysis": ai_analysis,
            "insights": parsed_analysis["insights"],
            "recommendations": parsed_analysis["recommendations"],
            "result_count": result_count,
            "sample_data": sample_data[:5],
            "query_context": query_context,
            "execution_info": execution_info
        }

    # ============================================================================
    # HELPER METHODS
    # ============================================================================

    def _detect_query_context(self, query: str, results: List[Dict]) -> str:
        """Detect the context of the query for better analysis"""
        query_lower = query.lower()

        # Check data columns
        columns = results[0].keys() if results else []
        has_cost = any('cost' in str(col).lower() or 'price' in str(col).lower() for col in columns)
        has_license = any('license' in str(col).lower() for col in columns)
        has_user = any('user' in str(col).lower() for col in columns)

        contexts = []

        if 'cost' in query_lower or 'expense' in query_lower or 'spending' in query_lower or has_cost:
            contexts.append("Cost Analysis")

        if 'license' in query_lower or 'subscription' in query_lower or has_license:
            contexts.append("License Management")

        if 'user' in query_lower or 'employee' in query_lower or has_user:
            contexts.append("User Analytics")

        if 'optimization' in query_lower or 'optimize' in query_lower or 'reduce' in query_lower:
            contexts.append("Optimization Opportunity")

        if 'forecast' in query_lower or 'predict' in query_lower or 'trend' in query_lower:
            contexts.append("Forecasting & Trends")

        return " & ".join(contexts) if contexts else "General Analysis"

    def _parse_analysis_response(self, ai_response: str, results: List[Dict]) -> Dict:
        """Parse the AI analysis into structured format"""
        lines = ai_response.split('\n')

        summary = ""
        insights = []
        recommendations = []

        current_section = None
        current_recommendation = {}

        for line in lines:
            line = line.strip()

            if line.startswith('SUMMARY:'):
                current_section = 'summary'
                continue
            elif line.startswith('INSIGHTS:'):
                current_section = 'insights'
                continue
            elif line.startswith('RECOMMENDATIONS:'):
                current_section = 'recommendations'
                continue

            if current_section == 'summary' and line:
                summary += line + " "

            elif current_section == 'insights' and line.startswith('•'):
                insights.append(line[1:].strip())

            elif current_section == 'recommendations':
                if line and line[0].isdigit() and '.' in line:
                    # Start of new recommendation
                    if current_recommendation:
                        recommendations.append(current_recommendation)
                    current_recommendation = {"text": line.split('.', 1)[1].strip() if '.' in line else line}

                elif line.startswith('Impact:'):
                    current_recommendation['impact'] = line.replace('Impact:', '').strip()
                elif line.startswith('Difficulty:'):
                    current_recommendation['difficulty'] = line.replace('Difficulty:', '').strip()
                elif line.startswith('Priority:'):
                    current_recommendation['priority'] = line.replace('Priority:', '').strip()

        # Add last recommendation
        if current_recommendation:
            recommendations.append(current_recommendation)

        return {
            "summary": summary.strip(),
            "insights": insights,
            "recommendations": recommendations
        }

    def _create_fallback_summary(self, user_query: str, results: List[Dict]) -> str:
        """Create a basic summary when AI call fails"""
        result_count = len(results)

        if result_count == 1:
            return f"I found 1 result matching your query about {user_query}."
        elif result_count <= 10:
            return f"I found {result_count} results matching your query about {user_query}."
        else:
            return f"I found {result_count} results matching your query about {user_query}. Showing the top results."

    def _create_fallback_analysis(self, user_query: str, results: List[Dict],
                                  query_context: str) -> Dict:
        """Create fallback analysis when AI call fails"""
        result_count = len(results)

        # Calculate basic statistics
        insights = [
            f"Dataset contains {result_count} records",
            f"Query context: {query_context}"
        ]

        # Try to identify cost opportunities if cost data exists
        recommendations = []

        if results:
            columns = results[0].keys()

            # Check for cost-related data
            for col in columns:
                if 'cost' in str(col).lower() and results:
                    try:
                        total_cost = sum(float(r.get(col, 0) or 0) for r in results)
                        avg_cost = total_cost / len(results)

                        insights.append(f"Total cost identified: ${total_cost:,.2f}")
                        insights.append(f"Average cost per item: ${avg_cost:,.2f}")

                        if avg_cost > 20:
                            recommendations.append({
                                "text": "Review high-cost licenses for optimization opportunities",
                                "impact": "Potential 10-15% cost savings",
                                "difficulty": "Medium",
                                "priority": "High"
                            })
                    except:
                        pass

        if not recommendations:
            recommendations = [{
                "text": "Conduct detailed license utilization review",
                "impact": "Identify unused or underutilized licenses",
                "difficulty": "Easy",
                "priority": "Medium"
            }]

        return {
            "mode": "analysis",
            "success": True,
            "answer": f"Analysis complete for {query_context}. Found {result_count} records with actionable insights.",
            "full_analysis": "Fallback analysis generated due to AI service unavailability.",
            "insights": insights,
            "recommendations": recommendations,
            "result_count": result_count,
            "query_context": query_context
        }

    def auto_detect_mode(self, user_query: str, sql_query: str, results: List[Dict]) -> AIMode:
        """
        INTELLIGENT MODE DETECTION: Let AI decide whether to use Normal or Analysis mode

        Flow:
        1. First AI call analyzes the query intent and data
        2. AI decides: Simple summary needed OR deep analysis with suggestions needed
        3. Return the appropriate mode
        """
        if not results:
            # No data = simple response
            return AIMode.NORMAL

        # Prepare context for AI decision
        result_count = len(results)
        sample_data = results[:3]

        # ANALYSIS MODE: Need insights, recommendations, or interpretation from data
        # Keywords that STRONGLY indicate ANALYSIS need (asks for interpretation/action)
        strong_analysis_keywords = [
            'optimize', 'optimization', 'reduce cost', 'save money', 'save cost',
            'cost saving', 'reduce spending', 'reduce expense', 'cut cost',
            'waste', 'unused', 'underutilized', 'recommendation', 'recommend',
            'suggest', 'suggestion', 'improve', 'improvement', 'opportunity',
            'how can i', 'how to reduce', 'how to save', 'ways to',
            'should i', 'what can i do', 'what should', 'advice', 'advise'
        ]

        # NORMAL MODE: Just show the direct extracted data
        # Keywords that indicate user wants direct data (no analysis needed)
        direct_data_keywords = [
            'show me', 'list', 'display', 'get', 'find', 'how many', 'count',
            'who are', 'which', 'what are', 'tell me about', 'give me'
        ]

        # Keywords that MAY indicate analysis (depends on context)
        moderate_analysis_keywords = [
            'efficiency', 'analyze', 'analysis', 'forecast', 'predict',
            'trend', 'expensive', 'high cost', 'insights', 'understand'
        ]

        # Check for keywords
        query_lower = user_query.lower()
        has_strong_keyword = any(keyword in query_lower for keyword in strong_analysis_keywords)
        has_direct_keyword = any(keyword in query_lower for keyword in direct_data_keywords)
        has_moderate_keyword = any(keyword in query_lower for keyword in moderate_analysis_keywords)

        # ANALYSIS MODE: User asks for insights, recommendations, or interpretation
        if has_strong_keyword:
            print(f"[AI] Analysis keyword detected - user needs insights/recommendations - forcing ANALYSIS mode")
            return AIMode.ANALYSIS

        # NORMAL MODE: User asks for direct data display (list, show, count, etc.)
        if has_direct_keyword and not has_moderate_keyword:
            print(f"[AI] Direct data keyword detected - user wants raw data - using NORMAL mode")
            return AIMode.NORMAL

        # Check if data has cost/license information
        has_cost_data = False
        has_utilization_data = False
        if results and len(results) > 0:
            columns = results[0].keys() if results[0] else []
            has_cost_data = any('cost' in str(col).lower() or 'price' in str(col).lower() or 'spend' in str(col).lower() for col in columns)
            has_utilization_data = any('utilization' in str(col).lower() or 'consumed' in str(col).lower() for col in columns)

        # If moderate keyword + cost data = ANALYSIS
        if has_moderate_keyword and (has_cost_data or has_utilization_data):
            print(f"[AI] Moderate keyword with cost/utilization data - forcing ANALYSIS mode")
            return AIMode.ANALYSIS

        # Create decision prompt for AI
        decision_prompt = f"""You are an AI router that decides how to process data queries.

USER QUERY: "{user_query}"
SQL EXECUTED: {sql_query[:200]}...
RESULT COUNT: {result_count}
SAMPLE DATA: {json.dumps(sample_data, default=str)}

Your task: Decide if this query needs:

A) NORMAL MODE - Direct data display (user wants to SEE the extracted information)
   Examples: "show me users", "list licenses", "how many users", "count active users"
   Purpose: Just format and present the data clearly to the user

B) ANALYSIS MODE - Insights and recommendations (user wants INTERPRETATION of the data)
   Examples: "how can I optimize cost", "should I reduce licenses", "recommend improvements"
   Purpose: Analyze the data and provide actionable insights/suggestions

**CRITICAL DECISION RULES**:

Choose ANALYSIS MODE when user asks for:
- Optimization, recommendations, or suggestions ("optimize", "recommend", "suggest")
- Interpretation or advice ("should I", "how can I", "what can I do")
- Analysis or insights ("analyze", "insights", "understand why")
- Cost-saving opportunities or improvements

Choose NORMAL MODE when user asks for:
- Direct data display ("show me", "list", "display", "find")
- Counts or statistics ("how many", "count", "number of")
- Simple lookups ("who are", "which users", "what licenses")
- No interpretation or action needed - just show the data

Respond with EXACTLY one word: either "NORMAL" or "ANALYSIS"

Your decision:"""

        messages = [
            {
                "role": "system",
                "content": "You are a query intent classifier. Respond with only one word: NORMAL or ANALYSIS."
            },
            {
                "role": "user",
                "content": decision_prompt
            }
        ]

        try:
            # Get AI decision
            ai_decision = self._call_azure_openai(messages, temperature=0.1, max_tokens=10)
            ai_decision = ai_decision.strip().upper()

            print(f"[AI] AI Mode Decision: {ai_decision}")

            if "ANALYSIS" in ai_decision:
                return AIMode.ANALYSIS
            else:
                return AIMode.NORMAL

        except Exception as e:
            print(f"Error in mode detection, using fallback logic: {e}")
            # Fallback: Use keyword-based detection
            if has_analysis_keyword or result_count > 20:
                return AIMode.ANALYSIS
            else:
                return AIMode.NORMAL

    def process_query_auto(self, user_query: str, sql_query: str,
                          results: List[Dict], execution_info: str = "") -> Dict:
        """
        AUTO-MODE: Let AI decide the processing mode

        Flow:
        1. AI analyzes query → Decides mode
        2. Route to Normal or Analysis mode
        3. Return processed result
        """
        # Step 1: Let AI decide the mode
        detected_mode = self.auto_detect_mode(user_query, sql_query, results)

        print(f"[OK] Auto-detected mode: {detected_mode.value.upper()}")

        # Step 2: Process based on detected mode
        if detected_mode == AIMode.NORMAL:
            result = self.process_normal_mode(user_query, sql_query, results, execution_info)
        else:
            result = self.process_analysis_mode(user_query, sql_query, results, execution_info)

        # Add mode detection info
        result['detected_mode'] = detected_mode.value
        result['auto_mode'] = True

        return result

    def process_query_with_mode(self, mode: AIMode, user_query: str, sql_query: str,
                               results: List[Dict], execution_info: str = "") -> Dict:
        """
        Main entry point - process query based on selected mode
        """
        if mode == AIMode.NORMAL:
            return self.process_normal_mode(user_query, sql_query, results, execution_info)
        elif mode == AIMode.ANALYSIS:
            return self.process_analysis_mode(user_query, sql_query, results, execution_info)
        else:
            raise ValueError(f"Unknown AI mode: {mode}")


# Global instance
_ai_mode_instance = None

def get_ai_mode_manager() -> AIModeManager:
    """Get or create global AI mode manager instance"""
    global _ai_mode_instance
    if _ai_mode_instance is None:
        _ai_mode_instance = AIModeManager()
    return _ai_mode_instance


if __name__ == "__main__":
    # Test the AI mode manager
    print("Testing AI Mode Manager...")
    print("=" * 60)

    manager = get_ai_mode_manager()

    # Test data
    test_query = "Show me the top 5 most expensive licenses"
    test_sql = "SELECT TOP 5 * FROM Licenses ORDER BY ActualCost DESC"
    test_results = [
        {"LicenseName": "Microsoft 365 E5", "TotalUnits": 500, "ConsumedUnits": 350, "ActualCost": 57.0},
        {"LicenseName": "Microsoft 365 E3", "TotalUnits": 1000, "ConsumedUnits": 850, "ActualCost": 36.0},
        {"LicenseName": "Power BI Pro", "TotalUnits": 200, "ConsumedUnits": 180, "ActualCost": 10.0}
    ]

    # Test Normal Mode
    print("\n1. Testing NORMAL MODE...")
    normal_result = manager.process_query_with_mode(
        AIMode.NORMAL, test_query, test_sql, test_results
    )
    print(f"Mode: {normal_result['mode']}")
    print(f"Answer: {normal_result['answer']}")

    # Test Analysis Mode
    print("\n2. Testing ANALYSIS MODE...")
    analysis_result = manager.process_query_with_mode(
        AIMode.ANALYSIS, test_query, test_sql, test_results
    )
    print(f"Mode: {analysis_result['mode']}")
    print(f"Summary: {analysis_result['answer']}")
    print(f"Insights: {len(analysis_result['insights'])} found")
    print(f"Recommendations: {len(analysis_result['recommendations'])} provided")

    print("\n[OK] AI Mode Manager test complete!")
