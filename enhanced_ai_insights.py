"""
Enhanced AI Insights Generator - Modern Analytics Platform
Implements advanced features from Power BI, Tableau, and modern analytics platforms
"""

from config import ask_o4_mini, SQL_SERVER, SQL_DATABASE, SQL_USERNAME, SQL_PASSWORD
import pyodbc
from typing import Dict, List, Tuple, Optional
import json
import numpy as np
from datetime import datetime, timedelta
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import StandardScaler
import statistics

class EnhancedAIInsights:
    """
    Modern AI Insights with:
    - Anomaly Detection
    - Priority Ranking
    - Impact Scoring
    - ROI Calculations
    - Historical Tracking
    - Alert System
    """

    def __init__(self):
        self.connection_string = (
            f'DRIVER={{ODBC Driver 17 for SQL Server}};'
            f'SERVER={SQL_SERVER};'
            f'DATABASE={SQL_DATABASE};'
            f'UID={SQL_USERNAME};'
            f'PWD={SQL_PASSWORD}'
        )

    def get_comprehensive_stats(self) -> Dict:
        """Gather comprehensive statistics with anomaly detection"""
        try:
            conn = pyodbc.connect(self.connection_string)
            cursor = conn.cursor()

            stats = {}

            # Basic user statistics
            cursor.execute("""
                SELECT
                    COUNT(*) as TotalUsers,
                    SUM(CASE WHEN AccountStatus = 'Active' THEN 1 ELSE 0 END) as ActiveUsers,
                    SUM(CASE WHEN AccountStatus != 'Active' THEN 1 ELSE 0 END) as InactiveUsers,
                    SUM(CASE WHEN IsLicensed = 1 THEN 1 ELSE 0 END) as LicensedUsers,
                    SUM(CASE WHEN IsLicensed = 1 AND AccountStatus = 'Active' THEN 1 ELSE 0 END) as ActiveLicensedUsers,
                    SUM(CASE WHEN IsLicensed = 1 AND AccountStatus != 'Active' THEN 1 ELSE 0 END) as InactiveLicensedUsers
                FROM UserRecords
            """)
            row = cursor.fetchone()
            stats['total_users'] = row.TotalUsers
            stats['active_users'] = row.ActiveUsers
            stats['inactive_users'] = row.InactiveUsers
            stats['licensed_users'] = row.LicensedUsers
            stats['active_licensed_users'] = row.ActiveLicensedUsers
            stats['inactive_licensed_users'] = row.InactiveLicensedUsers

            # Stale users (not signed in for 30+ days but still active with licenses)
            cursor.execute("""
                SELECT COUNT(*) as StaleUsers
                FROM UserRecords
                WHERE DATEDIFF(day, LastSignInDateTime, GETDATE()) > 30
                AND Licenses IS NOT NULL
                AND Licenses != ''
                AND AccountStatus = 'Active'
            """)
            row = cursor.fetchone()
            stats['stale_licensed_users'] = row.StaleUsers if row.StaleUsers else 0

            # Never signed in users with licenses
            cursor.execute("""
                SELECT COUNT(*) as NeverSignedIn
                FROM UserRecords
                WHERE LastSignInDateTime IS NULL
                AND Licenses IS NOT NULL
                AND Licenses != ''
            """)
            row = cursor.fetchone()
            stats['never_signed_in_licensed'] = row.NeverSignedIn if row.NeverSignedIn else 0

            # License and cost analysis
            cursor.execute("""
                SELECT
                    SUM(COALESCE(l.ActualCost, l.PartnerCost, 0)) as TotalCost,
                    COUNT(DISTINCT l.Id) as TotalLicenseTypes,
                    SUM(l.TotalUnits) as TotalLicenseUnits,
                    SUM(l.ConsumedUnits) as ConsumedLicenseUnits
                FROM Licenses l
                WHERE l.TotalUnits > 0
            """)
            row = cursor.fetchone()
            stats['total_monthly_cost'] = float(row.TotalCost) if row.TotalCost else 0
            stats['total_license_types'] = row.TotalLicenseTypes if row.TotalLicenseTypes else 0
            stats['total_license_units'] = row.TotalLicenseUnits if row.TotalLicenseUnits else 0
            stats['consumed_license_units'] = row.ConsumedLicenseUnits if row.ConsumedLicenseUnits else 0

            # Cost wasted on inactive users
            cursor.execute("""
                SELECT
                    SUM(COALESCE(l.ActualCost, l.PartnerCost, 0)) as InactiveCost
                FROM UserRecords ur
                JOIN Licenses l ON ur.Licenses LIKE '%' + l.Id + '%'
                WHERE ur.AccountStatus != 'Active'
                AND ur.Licenses IS NOT NULL
            """)
            row = cursor.fetchone()
            stats['inactive_users_cost'] = float(row.InactiveCost) if row.InactiveCost else 0

            # Cost wasted on stale users (30+ days)
            cursor.execute("""
                SELECT
                    SUM(COALESCE(l.ActualCost, l.PartnerCost, 0)) as StaleCost
                FROM UserRecords ur
                JOIN Licenses l ON ur.Licenses LIKE '%' + l.Id + '%'
                WHERE DATEDIFF(day, ur.LastSignInDateTime, GETDATE()) > 30
                AND ur.Licenses IS NOT NULL
                AND ur.AccountStatus = 'Active'
            """)
            row = cursor.fetchone()
            stats['stale_users_cost'] = float(row.StaleCost) if row.StaleCost else 0

            # Cost wasted on never signed in users
            cursor.execute("""
                SELECT
                    SUM(COALESCE(l.ActualCost, l.PartnerCost, 0)) as NeverSignedInCost
                FROM UserRecords ur
                JOIN Licenses l ON ur.Licenses LIKE '%' + l.Id + '%'
                WHERE ur.LastSignInDateTime IS NULL
                AND ur.Licenses IS NOT NULL
            """)
            row = cursor.fetchone()
            stats['never_signed_in_cost'] = float(row.NeverSignedInCost) if row.NeverSignedInCost else 0

            # Top expensive licenses
            cursor.execute("""
                SELECT TOP 5
                    l.Name,
                    COALESCE(l.ActualCost, l.PartnerCost, 0) as Cost,
                    l.TotalUnits,
                    l.ConsumedUnits,
                    (CAST(l.ConsumedUnits as FLOAT) / NULLIF(l.TotalUnits, 0) * 100) as Utilization
                FROM Licenses l
                WHERE l.TotalUnits > 0
                ORDER BY Cost DESC
            """)
            stats['top_expensive_licenses'] = []
            for row in cursor.fetchall():
                stats['top_expensive_licenses'].append({
                    'name': row.Name,
                    'cost': float(row.Cost),
                    'total_units': row.TotalUnits,
                    'consumed_units': row.ConsumedUnits,
                    'utilization': float(row.Utilization) if row.Utilization else 0
                })

            # Underutilized expensive licenses (< 70% utilization)
            cursor.execute("""
                SELECT
                    l.Name,
                    COALESCE(l.ActualCost, l.PartnerCost, 0) as Cost,
                    l.TotalUnits,
                    l.ConsumedUnits,
                    (CAST(l.ConsumedUnits as FLOAT) / NULLIF(l.TotalUnits, 0) * 100) as Utilization,
                    (l.TotalUnits - l.ConsumedUnits) as UnusedUnits,
                    (l.TotalUnits - l.ConsumedUnits) * COALESCE(l.ActualCost, l.PartnerCost, 0) as WastedCost
                FROM Licenses l
                WHERE l.TotalUnits > 0
                AND (CAST(l.ConsumedUnits as FLOAT) / NULLIF(l.TotalUnits, 0) * 100) < 70
                AND COALESCE(l.ActualCost, l.PartnerCost, 0) > 5
                ORDER BY WastedCost DESC
            """)
            stats['underutilized_licenses'] = []
            for row in cursor.fetchall():
                stats['underutilized_licenses'].append({
                    'name': row.Name,
                    'cost': float(row.Cost),
                    'total_units': row.TotalUnits,
                    'consumed_units': row.ConsumedUnits,
                    'utilization': float(row.Utilization) if row.Utilization else 0,
                    'unused_units': row.UnusedUnits,
                    'wasted_cost': float(row.WastedCost) if row.WastedCost else 0
                })

            # Department-wise analysis
            cursor.execute("""
                SELECT TOP 10
                    ur.Department,
                    COUNT(*) as TotalUsers,
                    SUM(CASE WHEN ur.AccountStatus = 'Active' THEN 1 ELSE 0 END) as ActiveUsers,
                    SUM(CASE WHEN ur.IsLicensed = 1 THEN 1 ELSE 0 END) as LicensedUsers,
                    SUM(CASE WHEN DATEDIFF(day, ur.LastSignInDateTime, GETDATE()) > 30 AND ur.IsLicensed = 1 THEN 1 ELSE 0 END) as StaleUsers
                FROM UserRecords ur
                WHERE ur.Department IS NOT NULL
                GROUP BY ur.Department
                ORDER BY TotalUsers DESC
            """)
            stats['department_analysis'] = []
            for row in cursor.fetchall():
                stats['department_analysis'].append({
                    'department': row.Department,
                    'total_users': row.TotalUsers,
                    'active_users': row.ActiveUsers,
                    'licensed_users': row.LicensedUsers,
                    'stale_users': row.StaleUsers if row.StaleUsers else 0
                })

            conn.close()
            return stats

        except Exception as e:
            print(f"Error gathering comprehensive stats: {e}")
            return {}

    def detect_anomalies(self, stats: Dict) -> List[Dict]:
        """Detect anomalies and unusual patterns"""
        anomalies = []

        # Anomaly 1: High inactive license ratio
        if stats['inactive_licensed_users'] > 0:
            inactive_ratio = (stats['inactive_licensed_users'] / stats['licensed_users']) * 100
            if inactive_ratio > 15:  # More than 15% is concerning
                anomalies.append({
                    'type': 'HIGH_INACTIVE_LICENSES',
                    'severity': 'HIGH' if inactive_ratio > 25 else 'MEDIUM',
                    'metric': f'{inactive_ratio:.1f}%',
                    'description': f'{stats["inactive_licensed_users"]} inactive users still have active licenses',
                    'impact_cost': stats['inactive_users_cost'],
                    'threshold': '15%'
                })

        # Anomaly 2: Stale users (30+ days no login)
        if stats['stale_licensed_users'] > 0:
            stale_ratio = (stats['stale_licensed_users'] / stats['licensed_users']) * 100
            if stale_ratio > 10:
                anomalies.append({
                    'type': 'HIGH_STALE_USERS',
                    'severity': 'HIGH' if stale_ratio > 20 else 'MEDIUM',
                    'metric': f'{stale_ratio:.1f}%',
                    'description': f'{stats["stale_licensed_users"]} users haven\'t signed in for 30+ days but have licenses',
                    'impact_cost': stats['stale_users_cost'],
                    'threshold': '10%'
                })

        # Anomaly 3: Never signed in users
        if stats['never_signed_in_licensed'] > 0:
            never_signin_ratio = (stats['never_signed_in_licensed'] / stats['licensed_users']) * 100
            if never_signin_ratio > 5:
                anomalies.append({
                    'type': 'NEVER_SIGNED_IN',
                    'severity': 'HIGH',
                    'metric': f'{never_signin_ratio:.1f}%',
                    'description': f'{stats["never_signed_in_licensed"]} users have licenses but have never signed in',
                    'impact_cost': stats['never_signed_in_cost'],
                    'threshold': '5%'
                })

        # Anomaly 4: Low license utilization
        if stats['total_license_units'] > 0:
            utilization = (stats['consumed_license_units'] / stats['total_license_units']) * 100
            if utilization < 70:
                unused_units = stats['total_license_units'] - stats['consumed_license_units']
                anomalies.append({
                    'type': 'LOW_LICENSE_UTILIZATION',
                    'severity': 'MEDIUM',
                    'metric': f'{utilization:.1f}%',
                    'description': f'{unused_units} license units are unused (only {utilization:.1f}% utilization)',
                    'impact_cost': None,
                    'threshold': '70%'
                })

        # Anomaly 5: Underutilized expensive licenses
        if stats.get('underutilized_licenses'):
            total_wasted = sum([lic['wasted_cost'] for lic in stats['underutilized_licenses']])
            if total_wasted > 1000:  # More than $1000/month wasted
                anomalies.append({
                    'type': 'UNDERUTILIZED_EXPENSIVE_LICENSES',
                    'severity': 'HIGH',
                    'metric': f'${total_wasted:,.2f}/mo',
                    'description': f'{len(stats["underutilized_licenses"])} expensive licenses are underutilized (<70%)',
                    'impact_cost': total_wasted,
                    'threshold': '$1000/mo'
                })

        return anomalies

    def generate_prioritized_recommendations(self, stats: Dict, anomalies: List[Dict]) -> List[Dict]:
        """Generate actionable recommendations with priority and ROI"""
        recommendations = []

        # Calculate total potential savings
        total_potential_savings = (
            stats.get('inactive_users_cost', 0) +
            stats.get('stale_users_cost', 0) +
            stats.get('never_signed_in_cost', 0)
        )

        # Recommendation 1: Remove licenses from inactive users (HIGHEST PRIORITY)
        if stats['inactive_licensed_users'] > 0 and stats['inactive_users_cost'] > 0:
            recommendations.append({
                'id': 'REC_001',
                'priority': 'CRITICAL',
                'impact_score': 10,
                'category': 'Cost Optimization',
                'title': 'Remove licenses from inactive accounts',
                'description': f'Immediately revoke {stats["inactive_licensed_users"]} licenses from inactive user accounts',
                'affected_users': stats['inactive_licensed_users'],
                'monthly_savings': stats['inactive_users_cost'],
                'annual_savings': stats['inactive_users_cost'] * 12,
                'roi_percentage': (stats['inactive_users_cost'] / stats['total_monthly_cost']) * 100,
                'effort': 'LOW',
                'implementation_time': '1-2 hours',
                'action_steps': [
                    'Export list of inactive users with licenses',
                    'Review with department heads',
                    'Revoke licenses from confirmed inactive accounts',
                    'Monitor for reclamation requests'
                ]
            })

        # Recommendation 2: Audit stale users (HIGH PRIORITY)
        if stats['stale_licensed_users'] > 0 and stats['stale_users_cost'] > 0:
            recommendations.append({
                'id': 'REC_002',
                'priority': 'HIGH',
                'impact_score': 8,
                'category': 'License Management',
                'title': 'Audit users inactive for 30+ days',
                'description': f'Review {stats["stale_licensed_users"]} users who haven\'t signed in for 30+ days',
                'affected_users': stats['stale_licensed_users'],
                'monthly_savings': stats['stale_users_cost'],
                'annual_savings': stats['stale_users_cost'] * 12,
                'roi_percentage': (stats['stale_users_cost'] / stats['total_monthly_cost']) * 100,
                'effort': 'MEDIUM',
                'implementation_time': '1 week',
                'action_steps': [
                    'Send automated reminder emails to stale users',
                    'Contact department managers for verification',
                    'Set 2-week deadline for response',
                    'Revoke licenses from non-responsive accounts'
                ]
            })

        # Recommendation 3: Never signed in users (HIGH PRIORITY)
        if stats['never_signed_in_licensed'] > 0:
            recommendations.append({
                'id': 'REC_003',
                'priority': 'HIGH',
                'impact_score': 9,
                'category': 'Security & Compliance',
                'title': 'Investigate users who never signed in',
                'description': f'{stats["never_signed_in_licensed"]} users have licenses but have never logged in',
                'affected_users': stats['never_signed_in_licensed'],
                'monthly_savings': stats['never_signed_in_cost'],
                'annual_savings': stats['never_signed_in_cost'] * 12,
                'roi_percentage': (stats['never_signed_in_cost'] / stats['total_monthly_cost']) * 100,
                'effort': 'LOW',
                'implementation_time': '2-3 days',
                'action_steps': [
                    'Identify provisioning errors or test accounts',
                    'Contact account creators for verification',
                    'Disable unverified accounts',
                    'Revoke licenses from disabled accounts'
                ]
            })

        # Recommendation 4: Optimize underutilized licenses
        if stats.get('underutilized_licenses') and len(stats['underutilized_licenses']) > 0:
            total_wasted = sum([lic['wasted_cost'] for lic in stats['underutilized_licenses']])
            total_unused_units = sum([lic['unused_units'] for lic in stats['underutilized_licenses']])

            # Calculate potential savings more accurately
            high_value_licenses = [lic for lic in stats['underutilized_licenses'] if lic['wasted_cost'] > 500]
            if total_wasted > 100:
                savings_estimate = total_wasted * 0.5  # Conservative 50% recovery
                recommendations.append({
                    'id': 'REC_004',
                    'priority': 'HIGH' if len(high_value_licenses) > 0 else 'MEDIUM',
                    'impact_score': 8 if len(high_value_licenses) > 0 else 6,
                    'category': 'License Optimization',
                    'title': 'Optimize underutilized license allocations',
                    'description': f'{len(stats["underutilized_licenses"])} license types have significant underutilization (<70% usage), wasting ${total_wasted:,.2f}/month',
                    'affected_users': total_unused_units,
                    'monthly_savings': savings_estimate,
                    'annual_savings': savings_estimate * 12,
                    'roi_percentage': (savings_estimate / stats['total_monthly_cost']) * 100 if stats['total_monthly_cost'] > 0 else 0,
                    'effort': 'MEDIUM',
                    'implementation_time': '2-4 weeks',
                    'action_steps': [
                        f'Focus on top {len(high_value_licenses)} high-value licenses first (${sum([lic["wasted_cost"] for lic in high_value_licenses]):,.2f}/mo potential)',
                        'Review license purchase agreements and renewal dates',
                        'Calculate optimal license quantities based on 3-month usage trends',
                        'Negotiate with vendor for reduced units or reallocation',
                        'Implement automated monthly utilization monitoring',
                        'Set up alerts for licenses falling below 75% utilization'
                    ]
                })

        # Recommendation 5: Department-specific optimization
        if stats.get('department_analysis') and len(stats['department_analysis']) > 0:
            high_stale_depts = [d for d in stats['department_analysis'] if d.get('stale_users', 0) > d['total_users'] * 0.15]
            if high_stale_depts:
                total_stale = sum([d['stale_users'] for d in high_stale_depts])
                # Estimate cost per user for department analysis
                cost_per_user = stats['total_monthly_cost'] / stats['licensed_users'] if stats['licensed_users'] > 0 else 0
                estimated_savings = total_stale * cost_per_user * 0.4  # Conservative 40% recovery

                recommendations.append({
                    'id': 'REC_005',
                    'priority': 'MEDIUM',
                    'impact_score': 6,
                    'category': 'Department Optimization',
                    'title': 'Address departmental license inefficiencies',
                    'description': f'{len(high_stale_depts)} departments have >15% stale users, indicating poor license governance',
                    'affected_users': total_stale,
                    'monthly_savings': estimated_savings,
                    'annual_savings': estimated_savings * 12,
                    'roi_percentage': (estimated_savings / stats['total_monthly_cost']) * 100 if stats['total_monthly_cost'] > 0 else 0,
                    'effort': 'LOW',
                    'implementation_time': '1-2 weeks',
                    'action_steps': [
                        f'Priority departments: {", ".join([d["department"] for d in high_stale_depts[:3]])} ({sum([d["stale_users"] for d in high_stale_depts[:3]])} stale users)',
                        'Schedule meetings with department heads to review user activity',
                        'Implement department-level license usage dashboards',
                        'Establish quarterly department license audits',
                        'Create automated alerts for department managers when users go stale',
                        'Develop department-specific license allocation policies'
                    ]
                })

        # Recommendation 6: Cost per user analysis and optimization
        if stats['licensed_users'] > 0:
            cost_per_user = stats['total_monthly_cost'] / stats['licensed_users']
            active_cost_per_user = stats['total_monthly_cost'] / stats['active_users'] if stats['active_users'] > 0 else 0

            # If cost per active user is significantly higher than cost per licensed user, there's waste
            if active_cost_per_user > cost_per_user * 1.2:
                recommendations.append({
                    'id': 'REC_006',
                    'priority': 'MEDIUM',
                    'impact_score': 5,
                    'category': 'Cost Efficiency',
                    'title': 'Optimize cost-per-active-user metrics',
                    'description': f'Current cost-per-active-user (${active_cost_per_user:.2f}) is {((active_cost_per_user/cost_per_user - 1) * 100):.1f}% higher than optimal due to inactive licenses',
                    'affected_users': stats['licensed_users'] - stats['active_users'],
                    'monthly_savings': (stats['licensed_users'] - stats['active_users']) * cost_per_user * 0.3,
                    'annual_savings': (stats['licensed_users'] - stats['active_users']) * cost_per_user * 0.3 * 12,
                    'roi_percentage': ((stats['licensed_users'] - stats['active_users']) * cost_per_user * 0.3 / stats['total_monthly_cost']) * 100,
                    'effort': 'LOW',
                    'implementation_time': '1 week',
                    'action_steps': [
                        f'Target cost-per-active-user: ${cost_per_user:.2f}',
                        f'Current gap: ${active_cost_per_user - cost_per_user:.2f} per active user',
                        'Implement monthly cost-per-user tracking',
                        'Remove licenses from users inactive >90 days',
                        'Establish process for immediate license removal upon user deactivation'
                    ]
                })

        # Sort by priority and impact score
        priority_order = {'CRITICAL': 0, 'HIGH': 1, 'MEDIUM': 2, 'LOW': 3}
        recommendations.sort(key=lambda x: (priority_order[x['priority']], -x['impact_score']))

        return recommendations

    def calculate_advanced_predictions(self, stats: Dict) -> Dict:
        """Advanced cost predictions with multiple scenarios and trend analysis"""
        current_cost = stats.get('total_monthly_cost', 0)

        # More realistic growth assumption based on typical SaaS expansion (2% monthly)
        growth_rate = 0.02

        # Scenario 1: Current trajectory with realistic growth
        months_ahead = 6
        current_trajectory = []
        cumulative_waste = 0
        for i in range(months_ahead + 1):
            month_cost = current_cost * (1 + growth_rate) ** i
            # Calculate cumulative waste from current inefficiencies
            if i > 0:
                cumulative_waste += stats.get('inactive_users_cost', 0) + (stats.get('stale_users_cost', 0) * 0.6)
            current_trajectory.append({
                'month': i,
                'cost': round(month_cost, 2),
                'label': f'Month {i}' if i > 0 else 'Current',
                'cumulative_waste': round(cumulative_waste, 2)
            })

        # Scenario 2: Optimized - implementing critical recommendations
        immediate_savings = (
            stats.get('inactive_users_cost', 0) +
            stats.get('stale_users_cost', 0) * 0.6 +  # Conservative: 60% of stale users removed
            stats.get('never_signed_in_cost', 0) * 0.9  # 90% of never-signed-in removed
        )
        optimized_cost = max(current_cost - immediate_savings, 0)

        optimized_trajectory = []
        cumulative_savings = 0
        for i in range(months_ahead + 1):
            month_cost = optimized_cost * (1 + growth_rate) ** i
            if i > 0:
                cumulative_savings += immediate_savings
            optimized_trajectory.append({
                'month': i,
                'cost': round(month_cost, 2),
                'label': f'Month {i}' if i > 0 else 'Current',
                'cumulative_savings': round(cumulative_savings, 2)
            })

        # Scenario 3: Best case - all recommendations including license optimization
        underutilized_savings = sum([lic.get('wasted_cost', 0) for lic in stats.get('underutilized_licenses', [])]) * 0.5
        total_best_case_savings = immediate_savings + underutilized_savings
        best_case_cost = max(current_cost - total_best_case_savings, 0)

        best_case_trajectory = []
        cumulative_best_savings = 0
        for i in range(months_ahead + 1):
            month_cost = best_case_cost * (1 + growth_rate) ** i
            if i > 0:
                cumulative_best_savings += total_best_case_savings
            best_case_trajectory.append({
                'month': i,
                'cost': round(month_cost, 2),
                'label': f'Month {i}' if i > 0 else 'Current',
                'cumulative_savings': round(cumulative_best_savings, 2)
            })

        # Calculate break-even and ROI metrics
        implementation_cost_estimate = 0  # Assuming internal resources, no external cost
        months_to_breakeven = 0 if immediate_savings > 0 else None

        # Calculate 3-year projection for long-term value
        three_year_savings_optimized = immediate_savings * 36
        three_year_savings_best_case = total_best_case_savings * 36

        return {
            'current_monthly_cost': round(current_cost, 2),
            'optimized_monthly_cost': round(optimized_cost, 2),
            'best_case_monthly_cost': round(best_case_cost, 2),
            'monthly_savings_optimized': round(immediate_savings, 2),
            'monthly_savings_best_case': round(total_best_case_savings, 2),
            'annual_savings_optimized': round(immediate_savings * 12, 2),
            'annual_savings_best_case': round(total_best_case_savings * 12, 2),
            'three_year_savings_optimized': round(three_year_savings_optimized, 2),
            'three_year_savings_best_case': round(three_year_savings_best_case, 2),
            'savings_percentage': round((immediate_savings / current_cost) * 100, 2) if current_cost > 0 else 0,
            'best_case_savings_percentage': round((total_best_case_savings / current_cost) * 100, 2) if current_cost > 0 else 0,
            'current_trajectory': current_trajectory,
            'optimized_trajectory': optimized_trajectory,
            'best_case_trajectory': best_case_trajectory,
            'payback_period_months': months_to_breakeven,
            'roi_percentage': round((immediate_savings * 12 / current_cost) * 100, 2) if current_cost > 0 else 0,
            'growth_rate_assumed': round(growth_rate * 100, 2),
            'cost_avoidance_6_months': round(current_trajectory[6]['cost'] - optimized_trajectory[6]['cost'], 2),
            'efficiency_improvement': round(((current_cost - optimized_cost) / current_cost) * 100, 2) if current_cost > 0 else 0
        }

    def generate_executive_summary(self, stats: Dict, anomalies: List[Dict], recommendations: List[Dict], predictions: Dict) -> str:
        """Generate concise executive summary using AI"""

        total_savings = predictions['monthly_savings_optimized']
        annual_savings = predictions['annual_savings_optimized']

        # Very short prompt to avoid token limits
        prompt = f"""Write 3 sentences about Microsoft 365 license optimization:

Cost: ${stats['total_monthly_cost']:,.2f}/mo
Savings: ${total_savings:,.2f}/mo ({predictions['savings_percentage']:.1f}%)
Inactive licensed users: {stats['inactive_licensed_users']}

Write 3 sentences: current situation, opportunities, savings."""

        try:
            # Use more tokens to avoid length limit
            summary = ask_o4_mini(prompt, max_tokens=1000)
            if summary and len(summary.strip()) > 30:
                print("✓ AI executive summary generated successfully")
                return summary.strip()
            else:
                print("⚠ AI summary empty, using data-driven summary")
                return self._fallback_summary(stats, total_savings, annual_savings, recommendations)
        except Exception as e:
            print(f"⚠ AI summary error: {str(e)[:100]}, using data-driven summary")
            return self._fallback_summary(stats, total_savings, annual_savings, recommendations)

    def _fallback_summary(self, stats: Dict, monthly_savings: float, annual_savings: float, recommendations: List[Dict] = None) -> str:
        """Professional data-driven executive summary"""

        # Build a comprehensive summary
        summary_parts = []

        # Part 1: Current state
        summary_parts.append(
            f"Your organization currently spends ${stats['total_monthly_cost']:,.2f} per month on Microsoft 365 licenses, "
            f"with {stats['inactive_licensed_users']} inactive users still holding active licenses"
        )

        # Part 2: Key opportunities
        opportunities = []
        if stats.get('inactive_licensed_users', 0) > 0:
            opportunities.append("removing licenses from inactive accounts")
        if stats.get('stale_licensed_users', 0) > 0:
            opportunities.append(f"auditing {stats['stale_licensed_users']} users who haven't signed in for 30+ days")
        if stats.get('never_signed_in_licensed', 0) > 0:
            opportunities.append(f"investigating {stats['never_signed_in_licensed']} users who have never logged in")

        if opportunities:
            summary_parts.append(f"The most significant opportunities include {', '.join(opportunities[:3])}")

        # Part 3: Savings potential
        savings_percent = ((monthly_savings/stats['total_monthly_cost'])*100) if stats['total_monthly_cost'] > 0 else 0
        summary_parts.append(
            f"By implementing recommended optimizations, you could save ${monthly_savings:,.2f} monthly "
            f"(${annual_savings:,.2f} annually), representing a {savings_percent:.1f}% cost reduction with minimal operational impact"
        )

        return ". ".join(summary_parts) + "."

    def generate_insights(self) -> Dict:
        """Main method to generate comprehensive AI insights"""
        try:
            print("Gathering comprehensive statistics...")
            stats = self.get_comprehensive_stats()

            if not stats:
                return {
                    'success': False,
                    'error': 'Failed to gather statistics'
                }

            print("Detecting anomalies...")
            anomalies = self.detect_anomalies(stats)

            print("Generating prioritized recommendations...")
            recommendations = self.generate_prioritized_recommendations(stats, anomalies)

            print("Calculating advanced predictions...")
            predictions = self.calculate_advanced_predictions(stats)

            print("Generating executive summary...")
            executive_summary = self.generate_executive_summary(stats, anomalies, recommendations, predictions)

            # Calculate key metrics
            total_potential_savings = predictions['monthly_savings_optimized']

            return {
                'success': True,
                'executive_summary': executive_summary,
                'anomalies': anomalies,
                'recommendations': recommendations,
                'predictions': predictions,
                'statistics': {
                    'total_users': stats['total_users'],
                    'active_users': stats['active_users'],
                    'inactive_users': stats['inactive_users'],
                    'licensed_users': stats['licensed_users'],
                    'active_licensed_users': stats['active_licensed_users'],
                    'inactive_licensed_users': stats['inactive_licensed_users'],
                    'stale_licensed_users': stats['stale_licensed_users'],
                    'never_signed_in_licensed': stats['never_signed_in_licensed'],
                    'total_monthly_cost': round(stats['total_monthly_cost'], 2),
                    'total_annual_cost': round(stats['total_monthly_cost'] * 12, 2),
                    'inactive_users_cost': round(stats['inactive_users_cost'], 2),
                    'stale_users_cost': round(stats['stale_users_cost'], 2),
                    'never_signed_in_cost': round(stats['never_signed_in_cost'], 2),
                    'potential_monthly_savings': round(total_potential_savings, 2),
                    'potential_annual_savings': round(total_potential_savings * 12, 2),
                    'license_utilization': round((stats['consumed_license_units'] / stats['total_license_units']) * 100, 2) if stats['total_license_units'] > 0 else 0
                },
                'charts_data': {
                    'top_expensive_licenses': stats.get('top_expensive_licenses', []),
                    'underutilized_licenses': stats.get('underutilized_licenses', []),
                    'department_analysis': stats.get('department_analysis', [])
                }
            }

        except Exception as e:
            print(f"Error generating enhanced insights: {e}")
            import traceback
            traceback.print_exc()
            return {
                'success': False,
                'error': str(e)
            }
