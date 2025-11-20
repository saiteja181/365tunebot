from config import ask_o4_mini, SQL_SERVER, SQL_DATABASE, SQL_USERNAME, SQL_PASSWORD
import pyodbc
from typing import Dict, List
import json
import numpy as np
from sklearn.linear_model import LinearRegression
from datetime import datetime, timedelta

class AIInsightsGenerator:
    def __init__(self):
        self.connection_string = (
            f'DRIVER={{ODBC Driver 17 for SQL Server}};'
            f'SERVER={SQL_SERVER};'
            f'DATABASE={SQL_DATABASE};'
            f'UID={SQL_USERNAME};'
            f'PWD={SQL_PASSWORD}'
        )

    def get_database_stats(self) -> Dict:
        """Gather key statistics from the database for AI analysis"""
        try:
            conn = pyodbc.connect(self.connection_string)
            cursor = conn.cursor()

            stats = {}

            # Total users and active/inactive breakdown
            cursor.execute("""
                SELECT
                    COUNT(*) as TotalUsers,
                    SUM(CASE WHEN AccountStatus = 'Active' THEN 1 ELSE 0 END) as ActiveUsers,
                    SUM(CASE WHEN AccountStatus != 'Active' THEN 1 ELSE 0 END) as InactiveUsers
                FROM UserRecords
            """)
            row = cursor.fetchone()
            stats['total_users'] = row.TotalUsers
            stats['active_users'] = row.ActiveUsers
            stats['inactive_users'] = row.InactiveUsers

            # Licensed vs unlicensed users
            cursor.execute("""
                SELECT
                    COUNT(*) as LicensedUsers
                FROM UserRecords
                WHERE Licenses IS NOT NULL AND Licenses != ''
            """)
            row = cursor.fetchone()
            stats['licensed_users'] = row.LicensedUsers
            stats['unlicensed_users'] = stats['total_users'] - row.LicensedUsers

            # Inactive users with licenses (waste)
            cursor.execute("""
                SELECT
                    COUNT(*) as InactiveWithLicenses
                FROM UserRecords
                WHERE AccountStatus != 'Active'
                AND Licenses IS NOT NULL
                AND Licenses != ''
            """)
            row = cursor.fetchone()
            stats['inactive_with_licenses'] = row.InactiveWithLicenses

            # Total cost and breakdown
            cursor.execute("""
                SELECT
                    SUM(COALESCE(l.ActualCost, l.PartnerCost)) as TotalCost
                FROM UserRecords ur
                JOIN Licenses l ON ur.Licenses LIKE '%' + l.Id + '%'
                WHERE ur.Licenses IS NOT NULL
            """)
            row = cursor.fetchone()
            stats['total_cost'] = float(row.TotalCost) if row.TotalCost else 0

            # Cost for inactive users with licenses
            cursor.execute("""
                SELECT
                    SUM(COALESCE(l.ActualCost, l.PartnerCost)) as WastedCost
                FROM UserRecords ur
                JOIN Licenses l ON ur.Licenses LIKE '%' + l.Id + '%'
                WHERE ur.AccountStatus != 'Active'
                AND ur.Licenses IS NOT NULL
            """)
            row = cursor.fetchone()
            stats['wasted_cost'] = float(row.WastedCost) if row.WastedCost else 0

            # Top 5 most expensive licenses
            cursor.execute("""
                SELECT TOP 5
                    l.Name,
                    COALESCE(l.ActualCost, l.PartnerCost) as Cost,
                    COUNT(*) as UserCount
                FROM UserRecords ur
                JOIN Licenses l ON ur.Licenses LIKE '%' + l.Id + '%'
                WHERE ur.Licenses IS NOT NULL
                GROUP BY l.Name, COALESCE(l.ActualCost, l.PartnerCost)
                ORDER BY Cost DESC
            """)
            stats['top_expensive_licenses'] = []
            for row in cursor.fetchall():
                stats['top_expensive_licenses'].append({
                    'name': row.Name,
                    'cost': float(row.Cost),
                    'user_count': row.UserCount
                })

            # Department-wise cost breakdown
            cursor.execute("""
                SELECT TOP 5
                    ur.Department,
                    SUM(COALESCE(l.ActualCost, l.PartnerCost)) as DeptCost,
                    COUNT(DISTINCT ur.UserID) as UserCount
                FROM UserRecords ur
                JOIN Licenses l ON ur.Licenses LIKE '%' + l.Id + '%'
                WHERE ur.Licenses IS NOT NULL
                AND ur.Department IS NOT NULL
                GROUP BY ur.Department
                ORDER BY DeptCost DESC
            """)
            stats['top_departments_by_cost'] = []
            for row in cursor.fetchall():
                stats['top_departments_by_cost'].append({
                    'department': row.Department,
                    'cost': float(row.DeptCost),
                    'user_count': row.UserCount
                })

            # Users who haven't signed in recently (30+ days) with licenses
            cursor.execute("""
                SELECT
                    COUNT(*) as StaleUsers
                FROM UserRecords
                WHERE DATEDIFF(day, LastSignInDateTime, GETDATE()) > 30
                AND Licenses IS NOT NULL
                AND Licenses != ''
                AND AccountStatus = 'Active'
            """)
            row = cursor.fetchone()
            stats['stale_licensed_users'] = row.StaleUsers if row.StaleUsers else 0

            conn.close()
            return stats

        except Exception as e:
            print(f"Error gathering database stats: {e}")
            return {}

    def predict_cost_trends(self, stats: Dict) -> Dict:
        """Use linear regression to predict future costs based on current data"""
        try:
            # Simulate historical data based on current stats
            # In a real scenario, you'd have actual historical data
            current_cost = stats.get('total_cost', 0)

            # Create synthetic historical data (last 6 months)
            # Assuming 2-5% monthly growth in costs
            months = 6
            historical_costs = []
            for i in range(months, 0, -1):
                # Work backwards from current cost
                cost_factor = 1 - (i * 0.03)  # ~3% monthly growth
                historical_costs.append(current_cost * cost_factor)

            # Add current cost
            historical_costs.append(current_cost)

            # Prepare data for linear regression
            X = np.array(range(len(historical_costs))).reshape(-1, 1)
            y = np.array(historical_costs)

            # Train model
            model = LinearRegression()
            model.fit(X, y)

            # Predict next 3 months
            future_months = 3
            future_X = np.array(range(len(historical_costs), len(historical_costs) + future_months)).reshape(-1, 1)
            predictions = model.predict(future_X)

            # Calculate trend
            monthly_growth = model.coef_[0]
            growth_rate = (monthly_growth / current_cost) * 100

            return {
                'current_monthly_cost': float(round(current_cost, 2)),
                'predicted_next_month': float(round(predictions[0], 2)),
                'predicted_3_months': float(round(predictions[2], 2)),
                'monthly_growth_rate': float(round(growth_rate, 2)),
                'monthly_growth_amount': float(round(monthly_growth, 2)),
                'potential_annual_cost': float(round(predictions[2] * 12, 2)),
                'trend': 'increasing' if monthly_growth > 0 else 'decreasing'
            }

        except Exception as e:
            print(f"Error predicting cost trends: {e}")
            return {
                'current_monthly_cost': stats.get('total_cost', 0),
                'error': 'Unable to generate predictions'
            }

    def generate_insights(self) -> Dict:
        """Generate AI-powered insights based on database statistics"""
        print("Gathering database statistics for AI insights...")
        stats = self.get_database_stats()

        if not stats:
            return {
                'success': False,
                'error': 'Failed to gather database statistics'
            }

        print(f"Statistics gathered: {json.dumps(stats, indent=2, default=str)}")

        # Generate cost predictions using linear regression
        print("Generating cost predictions...")
        cost_predictions = self.predict_cost_trends(stats)
        print(f"Cost predictions: {cost_predictions}")

        # Create prompt without asking for JSON format
        prompt = f"""Analyze this Microsoft 365 license data and provide 4 categories of insights:

Data:
- Total Users: {stats['total_users']:,}
- Active Users: {stats['active_users']:,}
- Inactive Users: {stats['inactive_users']:,}
- Licensed Users: {stats['licensed_users']:,}
- Inactive users with active licenses: {stats['inactive_with_licenses']:,}
- Monthly Cost: ${stats['total_cost']:,.2f}
- Wasted on inactive users: ${stats['wasted_cost']:,.2f}

Provide exactly 4 insights:
1. One cost optimization recommendation
2. One license management suggestion
3. One security or compliance risk
4. One immediate action item

Keep each insight to one sentence."""

        try:
            print("Generating AI insights...")
            print(f"Prompt: {prompt[:200]}...")

            response = ask_o4_mini(prompt, max_tokens=4000)

            print(f"AI response received: {response[:200] if response else 'EMPTY'}...")
            print(f"Full response length: {len(response) if response else 0}")

            if not response or len(response.strip()) < 10:
                raise ValueError("AI response is empty or too short")

            # Parse text response into structured insights
            lines = response.strip().split('\n')
            insights = {
                'cost_optimization': [],
                'license_management': [],
                'risk_alerts': [],
                'quick_wins': []
            }

            for line in lines:
                line = line.strip()
                if not line:
                    continue
                # Remove numbering and bullets
                line = line.lstrip('1234567890.-*• ')
                if len(line) > 10:  # Valid insight
                    # Categorize based on keywords
                    lower_line = line.lower()
                    if 'cost' in lower_line or 'save' in lower_line or 'spending' in lower_line:
                        insights['cost_optimization'].append(line)
                    elif 'license' in lower_line:
                        insights['license_management'].append(line)
                    elif 'security' in lower_line or 'risk' in lower_line or 'inactive' in lower_line:
                        insights['risk_alerts'].append(line)
                    else:
                        insights['quick_wins'].append(line)

            # Ensure at least one insight in each category
            if not insights['cost_optimization']:
                insights['cost_optimization'].append(f"Remove licenses from {stats['inactive_with_licenses']} inactive users to save ${stats['wasted_cost']:,.2f}/month")
            if not insights['license_management']:
                insights['license_management'].append(f"{stats['unlicensed_users']:,} users are unlicensed - verify licensing needs")
            if not insights['risk_alerts']:
                insights['risk_alerts'].append(f"High number of inactive accounts ({stats['inactive_users']:,}) poses security risk")
            if not insights['quick_wins']:
                insights['quick_wins'].append(f"Immediate action: Disable {stats['inactive_with_licenses']} inactive user licenses")

            return {
                'success': True,
                'insights': insights,
                'cost_predictions': cost_predictions,
                'statistics': {
                    'total_users': stats['total_users'],
                    'active_users': stats['active_users'],
                    'inactive_users': stats['inactive_users'],
                    'licensed_users': stats['licensed_users'],
                    'total_cost': round(stats['total_cost'], 2),
                    'wasted_cost': round(stats['wasted_cost'], 2),
                    'potential_savings': round(stats['wasted_cost'], 2),
                    'inactive_with_licenses': stats['inactive_with_licenses'],
                    'stale_licensed_users': stats['stale_licensed_users']
                }
            }

        except json.JSONDecodeError as e:
            print(f"Failed to parse AI response as JSON: {e}")
            print(f"Response was: {response}")
            raise Exception(f"Failed to parse AI response: {e}")
        except Exception as e:
            print(f"Error generating AI insights: {e}")
            raise

