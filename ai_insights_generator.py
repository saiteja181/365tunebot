"""
AI-Powered Insights Generator
Automatically generates actionable insights and recommendations from query results
This is the GAME-CHANGER feature that transforms the chatbot into an intelligent advisor
"""

from typing import Dict, List, Optional
from config import ask_o4_mini
import json

class AIInsightsGenerator:
    """Generates intelligent insights and recommendations from query results"""

    def __init__(self):
        self.enabled = True
        self.stats = {
            'insights_generated': 0,
            'recommendations_made': 0,
            'cost_savings_identified': 0
        }

    def should_generate_insights(self, query: str, results: List[Dict]) -> bool:
        """Determine if insights would be valuable for this query"""
        if not self.enabled or not results:
            return False

        # Skip for very simple queries
        simple_keywords = ['what', 'list all', 'show all', 'help']
        query_lower = query.lower()

        if any(keyword in query_lower for keyword in simple_keywords):
            if len(results) > 10:  # Generate insights for large result sets
                return True
            return False

        # Generate insights for:
        # - Cost-related queries
        # - Department comparisons
        # - License queries
        # - Status queries (active/inactive)
        # - Activity queries

        insight_keywords = [
            'cost', 'spend', 'price', 'expensive',
            'department', 'compare',
            'license', 'licenses',
            'inactive', 'disabled', 'active',
            'most', 'least', 'highest', 'lowest',
            'count', 'how many'
        ]

        return any(keyword in query_lower for keyword in insight_keywords)

    def generate_insights(self, query: str, sql_query: str, results: List[Dict],
                         row_count: int) -> Optional[Dict]:
        """Generate AI-powered insights and recommendations"""

        if not self.should_generate_insights(query, results):
            return None

        try:
            # Prepare data summary for AI
            data_summary = self._prepare_data_summary(results, row_count)

            prompt = f"""You are an intelligent Microsoft 365 analytics advisor. A user asked a question and received query results. Your job is to provide actionable insights and recommendations.

User Question: {query}

SQL Query: {sql_query}

Data Summary:
{data_summary}

Provide a concise analysis with:
1. **Key Insights** (2-3 bullet points) - What does the data reveal?
2. **Recommendations** (1-2 specific actions) - What should they do?
3. **Cost Savings** (if applicable) - Any potential cost optimizations?

Format your response as JSON:
{{
    "insights": ["insight 1", "insight 2", ...],
    "recommendations": ["recommendation 1", "recommendation 2", ...],
    "cost_savings": "description of potential savings or null",
    "summary": "one-sentence summary"
}}

Keep it concise, actionable, and business-focused."""

            response = ask_o4_mini(prompt)

            # Parse JSON response
            insights_data = self._parse_insights_response(response)

            if insights_data:
                self.stats['insights_generated'] += 1
                if insights_data.get('recommendations'):
                    self.stats['recommendations_made'] += len(insights_data['recommendations'])
                if insights_data.get('cost_savings'):
                    self.stats['cost_savings_identified'] += 1

            return insights_data

        except Exception as e:
            print(f"Error generating insights: {str(e)}")
            return None

    def _prepare_data_summary(self, results: List[Dict], row_count: int) -> str:
        """Prepare a concise summary of the data for AI analysis"""

        if not results:
            return "No results returned"

        # Get sample data (first 5 rows)
        sample_size = min(5, len(results))
        sample_data = results[:sample_size]

        # Get column names
        if results:
            columns = list(results[0].keys())
        else:
            columns = []

        # Calculate basic stats if numeric columns exist
        stats = {}
        for col in columns:
            try:
                values = [float(row[col]) for row in results if row.get(col) is not None and str(row[col]).replace('.', '').isdigit()]
                if values:
                    stats[col] = {
                        'min': min(values),
                        'max': max(values),
                        'avg': sum(values) / len(values),
                        'total': sum(values)
                    }
            except:
                pass

        summary = f"""Total rows: {row_count}
Columns: {', '.join(columns)}

Sample data (first {sample_size} rows):
{json.dumps(sample_data, indent=2, default=str)}
"""

        if stats:
            summary += f"\nNumeric statistics:\n{json.dumps(stats, indent=2)}"

        return summary

    def _parse_insights_response(self, response: str) -> Optional[Dict]:
        """Parse AI response into structured insights"""
        try:
            # Clean up response
            response = response.strip()

            # Remove markdown code blocks if present
            if response.startswith('```json'):
                response = response.replace('```json', '').replace('```', '').strip()
            elif response.startswith('```'):
                response = response.replace('```', '').strip()

            # Parse JSON
            insights = json.loads(response)

            return insights

        except json.JSONDecodeError:
            # Fallback: Try to extract insights manually
            return {
                'insights': [],
                'recommendations': [],
                'cost_savings': None,
                'summary': 'Unable to generate structured insights'
            }

    def format_insights_for_display(self, insights: Dict) -> str:
        """Format insights into a nice display string"""
        if not insights:
            return ""

        output = "\n\n" + "=" * 60 + "\n"
        output += "💡 AI-POWERED INSIGHTS\n"
        output += "=" * 60 + "\n\n"

        # Summary
        if insights.get('summary'):
            output += f"**Summary:** {insights['summary']}\n\n"

        # Key Insights
        if insights.get('insights'):
            output += "**📊 Key Insights:**\n"
            for i, insight in enumerate(insights['insights'], 1):
                output += f"  {i}. {insight}\n"
            output += "\n"

        # Recommendations
        if insights.get('recommendations'):
            output += "**🎯 Recommendations:**\n"
            for i, rec in enumerate(insights['recommendations'], 1):
                output += f"  {i}. {rec}\n"
            output += "\n"

        # Cost Savings
        if insights.get('cost_savings'):
            output += f"**💰 Cost Optimization:**\n  {insights['cost_savings']}\n\n"

        output += "=" * 60 + "\n"

        return output

    def get_stats(self) -> Dict:
        """Get insights generation statistics"""
        return self.stats

    def enable(self):
        """Enable insights generation"""
        self.enabled = True

    def disable(self):
        """Disable insights generation"""
        self.enabled = False
