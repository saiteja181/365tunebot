"""
Microsoft 365 Cost Analysis & Forecasting Engine

Analyzes historical license costs and forecasts future spending:
- Monthly cost breakdown
- Next month forecast
- Year-to-date and full year projections
- Cost trends and optimization opportunities
"""

from config import SQL_SERVER, SQL_DATABASE, SQL_USERNAME, SQL_PASSWORD
import pyodbc
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
import json


@dataclass
class CostForecast:
    """Cost forecast data structure"""
    period: str
    forecasted_cost: float
    confidence_level: str
    basis: str


@dataclass
class MonthlyCost:
    """Monthly cost data structure"""
    month: str
    total_cost: float
    license_count: int
    average_cost_per_license: float


class CostForecastingEngine:
    """
    Intelligent cost analysis and forecasting engine for Microsoft 365 licenses.

    Provides historical analysis and predictive forecasting based on actual license costs.
    """

    def __init__(self, tenant_code: str = None):
        """
        Initialize cost forecasting engine.

        Args:
            tenant_code: Tenant code for data filtering
        """
        self.tenant_code = tenant_code
        self.connection_string = (
            f'DRIVER={{ODBC Driver 17 for SQL Server}};'
            f'SERVER={SQL_SERVER};'
            f'DATABASE={SQL_DATABASE};'
            f'UID={SQL_USERNAME};'
            f'PWD={SQL_PASSWORD}'
        )

        if not tenant_code:
            print("WARNING: No tenant_code provided. Analysis will include all tenants.")

    def _get_tenant_filter(self) -> str:
        """Generate SQL WHERE clause for tenant filtering"""
        if not self.tenant_code:
            return ""
        return f"TenantCode = '{self.tenant_code}'"

    def _execute_query(self, query: str) -> List[tuple]:
        """Execute SQL query and return results"""
        try:
            with pyodbc.connect(self.connection_string) as conn:
                cursor = conn.cursor()
                cursor.execute(query)
                return cursor.fetchall()
        except Exception as e:
            print(f"Query execution error: {str(e)}")
            return []

    def get_current_monthly_cost(self) -> Dict:
        """
        Get current month's cost from the latest snapshot in TenantSummaries.

        TotalSpend represents the current monthly cost at that point in time,
        not cumulative daily costs. We just take the most recent value.

        Returns:
            Dictionary with current month's latest cost
        """
        tenant_filter = self._get_tenant_filter()
        where_clause = f"WHERE {tenant_filter}" if tenant_filter else ""

        now = datetime.now()
        current_year = now.year
        current_month = now.month
        current_day = now.day

        current_month_str = f"{current_year}-{current_month:02d}"

        # Get the latest/highest cost from current month
        query = f"""
        SELECT TOP 1
            CONVERT(VARCHAR, CaptureDate, 120) as CaptureDate,
            ISNULL(TotalSpend, 0) as TotalMonthlyCost,
            TotalLicenseCount,
            TotalUsers,
            TotalActiveUsers,
            TotalLicensedUsers
        FROM TenantSummaries
        {where_clause}
        {"AND" if where_clause else "WHERE"} FORMAT(CaptureDate, 'yyyy-MM') = '{current_month_str}'
        ORDER BY TotalSpend DESC, CaptureDate DESC
        """

        result = self._execute_query(query)

        if result and result[0]:
            capture_date, total_cost, licenses, users, active, licensed = result[0]

            # Calculate utilization
            utilization = 0.0
            if users and users > 0 and active:
                utilization = (active / users * 100)

            avg_cost_per_license = (total_cost / licenses) if licenses and licenses > 0 else 0

            return {
                'period': now.strftime('%B %Y'),
                'total_monthly_cost': round(float(total_cost or 0), 2),
                'license_count': int(licenses or 0),
                'average_cost_per_license': round(avg_cost_per_license, 2),
                'total_users': int(users or 0),
                'active_users': int(active or 0),
                'licensed_users': int(licensed or 0),
                'utilization_percent': round(utilization, 2),
                'data_source': 'TenantSummaries (latest snapshot)',
                'last_capture_date': capture_date
            }

        return {
            'period': now.strftime('%B %Y'),
            'total_monthly_cost': 0.0,
            'license_count': 0,
            'average_cost_per_license': 0.0,
            'total_users': 0,
            'active_users': 0,
            'licensed_users': 0,
            'utilization_percent': 0.0,
            'data_source': 'TenantSummaries',
            'last_capture_date': None
        }

    def get_license_breakdown_by_type(self) -> List[Dict]:
        """
        Get cost breakdown by license type.

        Returns:
            List of license types with costs and counts
        """
        tenant_filter = self._get_tenant_filter()
        where_clause = f"WHERE {tenant_filter}" if tenant_filter else ""

        query = f"""
        SELECT
            Name as license_name,
            COUNT(*) as count,
            SUM(COALESCE(ActualCost, PartnerCost, 0)) as total_cost,
            AVG(COALESCE(ActualCost, PartnerCost, 0)) as avg_cost,
            SUM(ConsumedUnits) as consumed,
            SUM(TotalUnits) as total_units
        FROM Licenses
        {where_clause}
        {"AND" if where_clause else "WHERE"} Status = 'Enabled'
        GROUP BY Name
        ORDER BY total_cost DESC
        """

        results = self._execute_query(query)

        breakdown = []
        for row in results:
            name, count, total_cost, avg_cost, consumed, total = row
            utilization = (consumed / total * 100) if total and total > 0 else 0

            breakdown.append({
                'license_name': name,
                'count': int(count or 0),
                'monthly_cost': float(total_cost or 0),
                'average_cost': float(avg_cost or 0),
                'utilization_percent': float(utilization),
                'consumed_units': int(consumed or 0),
                'total_units': int(total or 0)
            })

        return breakdown

    def get_historical_monthly_costs(self, months: int = 3) -> List[Dict]:
        """
        Get historical monthly costs from TenantSummaries table.

        Args:
            months: Number of months to retrieve

        Returns:
            List of monthly cost data
        """
        tenant_filter = self._get_tenant_filter()
        where_clause = f"WHERE {tenant_filter}" if tenant_filter else ""

        query = f"""
        SELECT TOP {months}
            FORMAT(CaptureDate, 'yyyy-MM') as YearMonth,
            AVG(ISNULL(TotalSpend, 0)) as AvgMonthlyCost,
            MAX(ISNULL(TotalSpend, 0)) as MaxMonthlyCost,
            COUNT(*) as RecordCount
        FROM TenantSummaries
        {where_clause}
        GROUP BY FORMAT(CaptureDate, 'yyyy-MM')
        ORDER BY YearMonth DESC
        """

        results = self._execute_query(query)

        monthly_costs = []
        for row in results:
            if row:
                monthly_costs.append({
                    'month': row[0],
                    'avg_cost': float(row[1] or 0),
                    'max_cost': float(row[2] or 0),
                    'record_count': int(row[3] or 0)
                })

        return monthly_costs

    def forecast_next_month(self) -> Dict:
        """
        Forecast next month's license costs.

        Based on:
        - Last 3 months historical costs from TenantSummaries
        - Current active licenses
        - Average cost trends
        - Utilization patterns

        Returns:
            Dictionary with forecast details
        """
        current = self.get_current_monthly_cost()

        # Get last 3 months historical data
        historical_costs = self.get_historical_monthly_costs(months=3)

        # Calculate forecast based on historical trend
        if historical_costs and len(historical_costs) >= 2:
            # Use historical data to calculate trend
            costs = [h['max_cost'] for h in historical_costs if h['max_cost'] > 0]

            if len(costs) >= 2:
                # Calculate average growth rate
                growth_rates = []
                for i in range(len(costs) - 1):
                    if costs[i+1] > 0:
                        growth_rate = (costs[i] - costs[i+1]) / costs[i+1]
                        growth_rates.append(growth_rate)

                avg_growth_rate = sum(growth_rates) / len(growth_rates) if growth_rates else 0
                growth_factor = 1 + avg_growth_rate

                # Clamp growth factor between 0.8 and 1.2 (max 20% change)
                growth_factor = max(0.8, min(1.2, growth_factor))

                # Use most recent historical cost
                base_cost = costs[0]
                forecasted_cost = base_cost * growth_factor

                basis = f'Based on last {len(costs)} months trend (avg growth: {avg_growth_rate*100:.1f}%)'
                confidence_level = 'High' if len(costs) >= 3 else 'Medium'
            else:
                # Fallback to current cost with utilization-based growth
                base_cost = current['total_monthly_cost']
                growth_factor = 1.0

                if current['utilization_percent'] > 90:
                    growth_factor = 1.05  # 5% growth expected
                elif current['utilization_percent'] > 80:
                    growth_factor = 1.02  # 2% growth expected

                forecasted_cost = base_cost * growth_factor
                basis = 'Based on current license allocation and utilization trends'
                confidence_level = 'Medium'
        else:
            # No historical data - use current cost with utilization-based growth
            base_cost = current['total_monthly_cost']
            growth_factor = 1.0

            if current['utilization_percent'] > 90:
                growth_factor = 1.05  # 5% growth expected
            elif current['utilization_percent'] > 80:
                growth_factor = 1.02  # 2% growth expected

            forecasted_cost = base_cost * growth_factor
            basis = 'Based on current license allocation (no historical data available)'
            confidence_level = 'Low'

        return {
            'period': 'Next Month',
            'forecasted_cost': round(forecasted_cost, 2),
            'current_cost': base_cost,
            'change_amount': round(forecasted_cost - base_cost, 2),
            'change_percent': round((growth_factor - 1) * 100, 2),
            'basis': basis,
            'confidence_level': confidence_level,
            'historical_months': len(historical_costs) if historical_costs else 0
        }

    def forecast_year_total(self) -> Dict:
        """
        Calculate total year forecast (all 12 months) using TenantSummaries data.

        Calculates the complete yearly total by:
        - Taking actual costs for months with data
        - Projecting remaining months based on average

        Returns:
            Dictionary with full year forecast (12 months total)
        """
        tenant_filter = self._get_tenant_filter()
        where_clause = f"WHERE {tenant_filter}" if tenant_filter else ""

        current_year = datetime.now().year
        current_month = datetime.now().month

        # Get actual costs for all months in current year (only count months with cost > 0)
        ytd_query = f"""
        SELECT
            SUM(MonthlyCost) as YearToDateCost,
            AVG(MonthlyCost) as AvgMonthlyCost,
            COUNT(*) as MonthsWithData
        FROM (
            SELECT DISTINCT
                FORMAT(CaptureDate, 'yyyy-MM') as YearMonth,
                MAX(ISNULL(TotalSpend, 0)) as MonthlyCost
            FROM TenantSummaries
            {where_clause}
            {"AND" if where_clause else "WHERE"} YEAR(CaptureDate) = {current_year}
            GROUP BY FORMAT(CaptureDate, 'yyyy-MM')
            HAVING MAX(ISNULL(TotalSpend, 0)) > 0
        ) as MonthlyData
        """

        result = self._execute_query(ytd_query)

        if result and result[0]:
            ytd_cost, avg_monthly, months_with_data = result[0]
            ytd_cost = float(ytd_cost or 0)
            avg_monthly = float(avg_monthly or 0)
            months_with_data = int(months_with_data or 0)

            # Calculate remaining months (total 12 months in a year)
            remaining_months = 12 - months_with_data

            # Forecast remaining months using average of existing months
            remaining_forecast = avg_monthly * remaining_months if remaining_months > 0 else 0

            # Total year = actual months + forecasted remaining months
            total_year_forecast = ytd_cost + remaining_forecast

            return {
                'year': current_year,
                'total_year_forecast': round(total_year_forecast, 2),
                'actual_months_cost': round(ytd_cost, 2),
                'forecasted_months_cost': round(remaining_forecast, 2),
                'months_with_actual_data': months_with_data,
                'months_forecasted': remaining_months,
                'average_monthly_cost': round(avg_monthly, 2),
                'basis': f'{months_with_data} actual months + {remaining_months} forecasted months = 12 months total',
                'confidence_level': 'High' if months_with_data >= 3 else 'Medium',
                'data_source': 'TenantSummaries'
            }

        # Fallback if no data
        current = self.get_current_monthly_cost()
        estimated_year_total = current['total_monthly_cost'] * 12

        return {
            'year': current_year,
            'total_year_forecast': round(estimated_year_total, 2),
            'actual_months_cost': 0.0,
            'forecasted_months_cost': round(estimated_year_total, 2),
            'months_with_actual_data': 0,
            'months_forecasted': 12,
            'average_monthly_cost': current['total_monthly_cost'],
            'basis': 'Estimated - no historical data available',
            'confidence_level': 'Low',
            'data_source': 'TenantSummaries'
        }

    def get_cost_optimization_opportunities(self) -> List[Dict]:
        """
        Identify opportunities to reduce costs.

        Returns:
            List of optimization recommendations
        """
        tenant_filter = self._get_tenant_filter()
        where_clause = f"WHERE {tenant_filter}" if tenant_filter else ""

        opportunities = []

        # 1. Under-utilized licenses
        query = f"""
        SELECT
            Name,
            COUNT(*) as count,
            SUM(COALESCE(ActualCost, PartnerCost, 0)) as cost,
            SUM(ConsumedUnits) as consumed,
            SUM(TotalUnits) as total,
            (CAST(SUM(ConsumedUnits) AS FLOAT) / NULLIF(SUM(TotalUnits), 0) * 100) as utilization
        FROM Licenses
        {where_clause}
        {"AND" if where_clause else "WHERE"} Status = 'Enabled'
        GROUP BY Name
        HAVING (CAST(SUM(ConsumedUnits) AS FLOAT) / NULLIF(SUM(TotalUnits), 0) * 100) < 70
        ORDER BY cost DESC
        """

        results = self._execute_query(query)

        for row in results:
            name, count, cost, consumed, total, utilization = row
            unused_units = total - consumed
            potential_savings = (cost / total * unused_units) if total > 0 else 0

            opportunities.append({
                'type': 'Under-utilized License',
                'license_name': name,
                'utilization_percent': round(float(utilization or 0), 1),
                'unused_units': int(unused_units or 0),
                'current_cost': float(cost or 0),
                'potential_monthly_savings': round(float(potential_savings or 0), 2),
                'recommendation': f'Review {name} allocation. Consider reducing total units or redistributing.'
            })

        # 2. Trial licenses that should be converted or removed
        query = f"""
        SELECT
            Name,
            COUNT(*) as count,
            SUM(COALESCE(ActualCost, PartnerCost, 0)) as cost
        FROM Licenses
        {where_clause}
        {"AND" if where_clause else "WHERE"} IsTrial = 1
        GROUP BY Name
        """

        results = self._execute_query(query)

        for row in results:
            name, count, cost = row
            opportunities.append({
                'type': 'Trial License',
                'license_name': name,
                'count': int(count or 0),
                'current_cost': float(cost or 0),
                'recommendation': f'Convert or remove {count} trial licenses for {name}'
            })

        return opportunities

    def get_historical_costs_for_graph(self, months: int = 6) -> List[Dict]:
        """
        Get historical monthly costs for graphing purposes.

        Args:
            months: Number of historical months to retrieve

        Returns:
            List of monthly cost data sorted by date (oldest first)
        """
        historical_data = self.get_historical_monthly_costs(months=months)

        # Reverse to get oldest first (for graphing left to right)
        historical_data.reverse()

        return historical_data

    def generate_comprehensive_forecast(self) -> Dict:
        """
        Generate complete cost analysis and forecast report.

        Returns:
            Comprehensive dictionary with all cost data and forecasts
        """
        print(f"Generating cost forecast{f' for tenant: {self.tenant_code}' if self.tenant_code else ''}...")

        current_cost = self.get_current_monthly_cost()
        next_month = self.forecast_next_month()
        year_forecast = self.forecast_year_total()
        license_breakdown = self.get_license_breakdown_by_type()
        optimizations = self.get_cost_optimization_opportunities()
        historical_costs = self.get_historical_costs_for_graph(months=6)

        total_savings_potential = sum(
            opt.get('potential_monthly_savings', 0)
            for opt in optimizations
            if 'potential_monthly_savings' in opt
        )

        report = {
            'generated_at': datetime.now().isoformat(),
            'tenant_code': self.tenant_code,
            'current_month': current_cost,
            'next_month_forecast': next_month,
            'year_forecast': year_forecast,
            'license_breakdown': license_breakdown,
            'optimization_opportunities': optimizations,
            'historical_costs': historical_costs,  # Add historical data for graph
            'summary': {
                'current_monthly_cost': current_cost['total_monthly_cost'],
                'forecasted_next_month': next_month['forecasted_cost'],
                'forecasted_year_total': year_forecast['total_year_forecast'],
                'total_licenses': current_cost['license_count'],
                'utilization_rate': current_cost['utilization_percent'],
                'optimization_savings_potential': round(total_savings_potential, 2),
                'optimizations_count': len(optimizations),
                'historical_months_available': len(historical_costs)
            }
        }

        print(f"Cost forecast generated successfully")
        print(f"  - Current monthly cost: ${current_cost['total_monthly_cost']:.2f}")
        print(f"  - Next month forecast: ${next_month['forecasted_cost']:.2f}")
        print(f"  - Year forecast: ${year_forecast['total_year_forecast']:.2f}")
        print(f"  - Optimization potential: ${total_savings_potential:.2f}/month")
        print(f"  - Historical months: {len(historical_costs)}")

        return report


if __name__ == "__main__":
    DEFAULT_TENANT_CODE = "70b0fb90-1eb4-46d8-b23e-f4104619181b"

    engine = CostForecastingEngine(tenant_code=DEFAULT_TENANT_CODE)
    report = engine.generate_comprehensive_forecast()

    print("\n" + "="*80)
    print("COST FORECAST REPORT")
    print("="*80)
    print(json.dumps(report['summary'], indent=2))
