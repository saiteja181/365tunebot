import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { LineChart, Line, AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, ReferenceLine } from 'recharts';

const CostForecasting = () => {
  const [forecast, setForecast] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [refreshing, setRefreshing] = useState(false);

  const fetchForecast = async () => {
    try {
      setRefreshing(true);
      const response = await axios.get('http://localhost:8000/api/cost/forecast');

      if (response.data.success) {
        setForecast(response.data);
        setError(null);
      } else {
        setError(response.data.error || 'Failed to load cost forecast');
      }
    } catch (err) {
      console.error('Error fetching forecast:', err);
      setError('Failed to connect to cost forecasting service');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    fetchForecast();
    const interval = setInterval(fetchForecast, 300000);
    return () => clearInterval(interval);
  }, []);

  const formatCurrency = (value) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2
    }).format(value || 0);
  };

  // Generate forecast data for Azure-style graph using real historical data
  const generateForecastData = () => {
    if (!forecast || !forecast.current_month) {
      return [];
    }

    const currentCost = forecast.current_month.total_monthly_cost || 0;
    const forecastedCost = forecast.next_month_forecast.forecasted_cost || 0;
    const historicalCosts = forecast.historical_costs || [];

    const data = [];
    const now = new Date();

    // Use real historical data from API
    if (historicalCosts && historicalCosts.length > 0) {
      historicalCosts.forEach((histItem, idx) => {
        const isCurrentMonth = idx === historicalCosts.length - 1;
        const cost = histItem.max_cost || histItem.avg_cost || 0;

        data.push({
          month: histItem.month,
          actualCost: cost,
          forecastedCost: null,
          isActual: true,
          isCurrent: isCurrentMonth
        });
      });
    } else {
      // Fallback: use current month as only data point
      const currentMonthName = now.toLocaleDateString('en-US', { month: 'short', year: 'numeric' });
      data.push({
        month: currentMonthName,
        actualCost: currentCost,
        forecastedCost: null,
        isActual: true,
        isCurrent: true
      });
    }

    // Add forecasted months (next 5 months)
    const growthFactor = 1 + ((forecast.next_month_forecast.change_percent || 0) / 100);
    const baseForecast = forecastedCost;

    for (let i = 1; i <= 5; i++) {
      const date = new Date(now.getFullYear(), now.getMonth() + i, 1);
      const monthName = date.toLocaleDateString('en-US', { month: 'short', year: 'numeric' });

      // Calculate forecasted cost with growth factor applied
      const forecastValue = baseForecast * Math.pow(growthFactor, i - 1);

      // Add confidence range (±10%)
      const lowerBound = forecastValue * 0.9;
      const upperBound = forecastValue * 1.1;

      data.push({
        month: monthName,
        actualCost: null,
        forecastedCost: forecastValue,
        lowerBound: lowerBound,
        upperBound: upperBound,
        isActual: false,
        isForecast: true
      });
    }

    return data;
  };

  const CustomTooltip = ({ active, payload, label }) => {
    if (active && payload && payload.length) {
      const data = payload[0].payload;
      const isActual = data.isActual;
      const isCurrent = data.isCurrent;

      return (
        <div style={{
          background: 'white',
          border: '1px solid #cccccc',
          borderRadius: '8px',
          padding: '12px',
          boxShadow: '0 4px 6px rgba(0,0,0,0.1)'
        }}>
          <div style={{ fontWeight: '600', marginBottom: '8px', color: '#000000' }}>
            {label}
            {isCurrent && <span style={{ color: '#666666', marginLeft: '8px' }}>(Current)</span>}
          </div>
          {isActual ? (
            <div style={{ color: '#000000', fontWeight: '600' }}>
              Actual: {formatCurrency(data.actualCost)}
            </div>
          ) : (
            <>
              <div style={{ color: '#000000', fontWeight: '600' }}>
                Forecasted: {formatCurrency(data.forecastedCost)}
              </div>
              <div style={{ fontSize: '12px', color: '#666666', marginTop: '4px' }}>
                Range: {formatCurrency(data.lowerBound)} - {formatCurrency(data.upperBound)}
              </div>
            </>
          )}
        </div>
      );
    }
    return null;
  };

  const CostCard = ({ title, amount, subtitle, trend, color = '#000000' }) => (
    <div style={{
      background: 'white',
      border: `2px solid ${color}`,
      borderRadius: '12px',
      padding: '24px',
      flex: '1',
      minWidth: '250px'
    }}>
      <div style={{ fontSize: '14px', color: '#666666', marginBottom: '8px', fontWeight: '500' }}>
        {title}
      </div>
      <div style={{ fontSize: '36px', fontWeight: 'bold', color: '#000000', marginBottom: '8px' }}>
        {formatCurrency(amount)}
      </div>
      {subtitle && (
        <div style={{ fontSize: '13px', color: '#666666' }}>
          {subtitle}
        </div>
      )}
      {trend && (
        <div style={{
          marginTop: '12px',
          padding: '8px 12px',
          background: trend.up ? '#f0f0f0' : '#e0e0e0',
          borderRadius: '6px',
          fontSize: '13px',
          color: '#000000',
          fontWeight: '500'
        }}>
          {trend.up ? '▲' : '▼'} {trend.text}
        </div>
      )}
    </div>
  );

  const LicenseBreakdownTable = ({ licenses }) => (
    <div style={{
      background: 'white',
      border: '1px solid #cccccc',
      borderRadius: '12px',
      padding: '24px',
      marginTop: '24px'
    }}>
      <h3 style={{ margin: '0 0 20px 0', fontSize: '20px', fontWeight: '600', color: '#000000' }}>
        License Cost Breakdown
      </h3>
      <div style={{ overflowX: 'auto' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead>
            <tr style={{ background: '#f5f5f5', borderBottom: '2px solid #cccccc' }}>
              <th style={{ padding: '12px', textAlign: 'left', fontSize: '13px', fontWeight: '600', color: '#000000' }}>
                License Name
              </th>
              <th style={{ padding: '12px', textAlign: 'center', fontSize: '13px', fontWeight: '600', color: '#000000' }}>
                Count
              </th>
              <th style={{ padding: '12px', textAlign: 'right', fontSize: '13px', fontWeight: '600', color: '#000000' }}>
                Monthly Cost
              </th>
              <th style={{ padding: '12px', textAlign: 'right', fontSize: '13px', fontWeight: '600', color: '#000000' }}>
                Utilization
              </th>
              <th style={{ padding: '12px', textAlign: 'center', fontSize: '13px', fontWeight: '600', color: '#000000' }}>
                Units (Used/Total)
              </th>
            </tr>
          </thead>
          <tbody>
            {licenses.map((license, idx) => (
              <tr key={idx} style={{ borderBottom: '1px solid #cccccc' }}>
                <td style={{ padding: '12px', fontSize: '14px', color: '#000000', fontWeight: '500' }}>
                  {license.license_name}
                </td>
                <td style={{ padding: '12px', textAlign: 'center', fontSize: '14px', color: '#666666' }}>
                  {license.count}
                </td>
                <td style={{ padding: '12px', textAlign: 'right', fontSize: '14px', color: '#000000', fontWeight: '600' }}>
                  {formatCurrency(license.monthly_cost)}
                </td>
                <td style={{ padding: '12px', textAlign: 'right' }}>
                  <div style={{
                    display: 'inline-block',
                    background: license.utilization_percent >= 80 ? '#e0e0e0' : license.utilization_percent >= 50 ? '#f0f0f0' : '#f5f5f5',
                    color: '#000000',
                    padding: '4px 12px',
                    borderRadius: '12px',
                    fontSize: '13px',
                    fontWeight: '600',
                    border: '1px solid #cccccc'
                  }}>
                    {license.utilization_percent.toFixed(1)}%
                  </div>
                </td>
                <td style={{ padding: '12px', textAlign: 'center', fontSize: '13px', color: '#666666' }}>
                  {license.consumed_units} / {license.total_units}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );

  const OptimizationOpportunities = ({ opportunities }) => {
    if (!opportunities || opportunities.length === 0) {
      return null;
    }

    return (
      <div style={{
        background: 'white',
        border: '2px solid #000000',
        borderRadius: '12px',
        padding: '24px',
        marginTop: '24px'
      }}>
        <h3 style={{ margin: '0 0 16px 0', fontSize: '20px', fontWeight: '600', color: '#000000' }}>
          Cost Optimization Opportunities
        </h3>
        <div style={{ fontSize: '14px', color: '#666666', marginBottom: '20px' }}>
          Potential savings: {formatCurrency(opportunities.reduce((sum, opt) => sum + (opt.potential_monthly_savings || 0), 0))}/month
        </div>

        {opportunities.map((opt, idx) => (
          <div key={idx} style={{
            background: '#f5f5f5',
            border: '1px solid #cccccc',
            borderRadius: '8px',
            padding: '16px',
            marginBottom: '12px'
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start' }}>
              <div style={{ flex: 1 }}>
                <div style={{
                  display: 'inline-block',
                  background: '#e0e0e0',
                  color: '#000000',
                  padding: '4px 12px',
                  borderRadius: '4px',
                  fontSize: '12px',
                  fontWeight: '600',
                  marginBottom: '8px'
                }}>
                  {opt.type}
                </div>
                <h4 style={{ margin: '8px 0', fontSize: '16px', fontWeight: '600', color: '#000000' }}>
                  {opt.license_name}
                </h4>
                <p style={{ margin: '8px 0', fontSize: '14px', color: '#333333' }}>
                  {opt.recommendation}
                </p>
                {opt.utilization_percent !== undefined && (
                  <div style={{ marginTop: '8px', fontSize: '13px', color: '#666666' }}>
                    Current utilization: <strong>{opt.utilization_percent.toFixed(1)}%</strong>
                    {opt.unused_units > 0 && ` (${opt.unused_units} unused units)`}
                  </div>
                )}
              </div>
              {opt.potential_monthly_savings > 0 && (
                <div style={{
                  marginLeft: '16px',
                  textAlign: 'right'
                }}>
                  <div style={{ fontSize: '12px', color: '#000000', fontWeight: '500' }}>
                    POTENTIAL SAVINGS
                  </div>
                  <div style={{ fontSize: '24px', fontWeight: 'bold', color: '#000000' }}>
                    {formatCurrency(opt.potential_monthly_savings)}
                  </div>
                  <div style={{ fontSize: '12px', color: '#666666' }}>per month</div>
                </div>
              )}
            </div>
          </div>
        ))}
      </div>
    );
  };

  if (loading) {
    return (
      <div style={{
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        height: '400px'
      }}>
        <div style={{ textAlign: 'center' }}>
          <div style={{
            width: '48px',
            height: '48px',
            border: '4px solid #e5e7eb',
            borderTop: '4px solid #667eea',
            borderRadius: '50%',
            animation: 'spin 1s linear infinite',
            margin: '0 auto 16px'
          }}></div>
          <div style={{ fontSize: '16px', color: '#6b7280' }}>Analyzing costs...</div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div style={{
        background: '#fee2e2',
        border: '1px solid #dc2626',
        borderRadius: '8px',
        padding: '16px',
        margin: '20px',
        color: '#991b1b'
      }}>
        <strong>Error:</strong> {error}
      </div>
    );
  }

  if (!forecast) {
    return null;
  }

  const { current_month, next_month_forecast, year_forecast, license_breakdown, optimization_opportunities, summary } = forecast;

  return (
    <div style={{ padding: '24px', maxWidth: '1400px', margin: '0 auto' }}>
      <style>
        {`
          @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
          }
        `}
      </style>

      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
        <h2 style={{ margin: 0, fontSize: '28px', fontWeight: '700', color: '#111827' }}>
          Cost Analysis & Forecasting
        </h2>
        <button
          onClick={fetchForecast}
          disabled={refreshing}
          style={{
            background: refreshing ? '#e5e7eb' : '#667eea',
            color: refreshing ? '#9ca3af' : 'white',
            border: 'none',
            padding: '10px 20px',
            borderRadius: '8px',
            fontSize: '14px',
            fontWeight: '600',
            cursor: refreshing ? 'not-allowed' : 'pointer'
          }}
        >
          {refreshing ? 'Refreshing...' : 'Refresh'}
        </button>
      </div>

      <div style={{ display: 'flex', gap: '20px', flexWrap: 'wrap', marginBottom: '24px' }}>
        <CostCard
          title="Current Month"
          amount={current_month.total_monthly_cost}
          subtitle={`${current_month.period} - ${current_month.license_count} active licenses`}
          color="#000000"
        />

        <CostCard
          title="Next Month Forecast"
          amount={next_month_forecast.forecasted_cost}
          subtitle={next_month_forecast.basis}
          trend={{
            up: next_month_forecast.change_amount > 0,
            text: `${next_month_forecast.change_percent >= 0 ? '+' : ''}${next_month_forecast.change_percent}% vs current`
          }}
          color="#000000"
        />

        <CostCard
          title={`${year_forecast.year} Total Year Forecast`}
          amount={year_forecast.total_year_forecast}
          subtitle={year_forecast.basis || `Full 12-month projection`}
          color="#000000"
        />
      </div>

      {/* Azure-style Cost Forecast Graph */}
      <div style={{
        background: 'white',
        border: '1px solid #e5e7eb',
        borderRadius: '12px',
        padding: '24px',
        marginBottom: '24px'
      }}>
        <h3 style={{ margin: '0 0 20px 0', fontSize: '20px', fontWeight: '600', color: '#111827' }}>
          Cost Trend & Forecast
        </h3>
        <div style={{ fontSize: '14px', color: '#6b7280', marginBottom: '16px' }}>
          Historical actuals and forecasted costs for the next 5 months
        </div>
        <ResponsiveContainer width="100%" height={400}>
          <AreaChart data={generateForecastData()} margin={{ top: 10, right: 30, left: 20, bottom: 5 }}>
            <defs>
              <linearGradient id="colorActual" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#000000" stopOpacity={0.2}/>
                <stop offset="95%" stopColor="#000000" stopOpacity={0}/>
              </linearGradient>
              <linearGradient id="colorForecast" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#666666" stopOpacity={0.2}/>
                <stop offset="95%" stopColor="#666666" stopOpacity={0}/>
              </linearGradient>
              <linearGradient id="colorRange" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#f0f0f0" stopOpacity={0.8}/>
                <stop offset="95%" stopColor="#f0f0f0" stopOpacity={0.3}/>
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#cccccc" />
            <XAxis
              dataKey="month"
              stroke="#000000"
              style={{ fontSize: '12px' }}
              angle={-45}
              textAnchor="end"
              height={80}
            />
            <YAxis
              stroke="#000000"
              style={{ fontSize: '12px' }}
              tickFormatter={(value) => `$${value.toFixed(0)}`}
            />
            <Tooltip content={<CustomTooltip />} />
            <Legend
              wrapperStyle={{ paddingTop: '20px' }}
              iconType="line"
            />

            {/* Confidence range area (shown behind forecast) */}
            <Area
              type="monotone"
              dataKey="upperBound"
              stroke="none"
              fill="url(#colorRange)"
              name="Confidence Range"
            />
            <Area
              type="monotone"
              dataKey="lowerBound"
              stroke="none"
              fill="white"
            />

            {/* Actual cost line */}
            <Area
              type="monotone"
              dataKey="actualCost"
              stroke="#000000"
              strokeWidth={3}
              fill="url(#colorActual)"
              name="Actual Cost"
              connectNulls={false}
            />

            {/* Forecasted cost line (dashed) */}
            <Line
              type="monotone"
              dataKey="forecastedCost"
              stroke="#666666"
              strokeWidth={3}
              strokeDasharray="5 5"
              dot={{ fill: '#666666', r: 4 }}
              name="Forecasted Cost"
              connectNulls={false}
            />
          </AreaChart>
        </ResponsiveContainer>
        <div style={{
          display: 'flex',
          gap: '24px',
          marginTop: '16px',
          padding: '16px',
          background: '#f5f5f5',
          borderRadius: '8px',
          fontSize: '13px',
          color: '#000000'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <div style={{ width: '16px', height: '3px', background: '#000000' }}></div>
            <span>Historical Actuals</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <div style={{ width: '16px', height: '3px', background: '#666666', borderTop: '3px dashed #666666' }}></div>
            <span>Forecast</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <div style={{ width: '16px', height: '16px', background: '#e0e0e0', borderRadius: '2px' }}></div>
            <span>Confidence Range (±10%)</span>
          </div>
        </div>
      </div>

      <div style={{
        background: '#000000',
        borderRadius: '12px',
        padding: '24px',
        color: 'white',
        marginBottom: '24px'
      }}>
        <h3 style={{ margin: '0 0 16px 0', fontSize: '20px', fontWeight: '600' }}>
          Full Year Summary (2025)
        </h3>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '20px' }}>
          <div>
            <div style={{ fontSize: '14px', opacity: 0.9, marginBottom: '4px' }}>Actual Months Cost</div>
            <div style={{ fontSize: '28px', fontWeight: 'bold' }}>{formatCurrency(year_forecast.actual_months_cost || year_forecast.year_to_date_cost)}</div>
          </div>
          <div>
            <div style={{ fontSize: '14px', opacity: 0.9, marginBottom: '4px' }}>Forecasted Months Cost</div>
            <div style={{ fontSize: '28px', fontWeight: 'bold' }}>{formatCurrency(year_forecast.forecasted_months_cost || year_forecast.forecasted_remaining_cost)}</div>
          </div>
          <div>
            <div style={{ fontSize: '14px', opacity: 0.9, marginBottom: '4px' }}>Average Monthly</div>
            <div style={{ fontSize: '28px', fontWeight: 'bold' }}>{formatCurrency(year_forecast.average_monthly_cost)}</div>
          </div>
          <div>
            <div style={{ fontSize: '14px', opacity: 0.9, marginBottom: '4px' }}>License Utilization</div>
            <div style={{ fontSize: '28px', fontWeight: 'bold' }}>{current_month.utilization_percent.toFixed(1)}%</div>
          </div>
        </div>
      </div>

      {optimization_opportunities && optimization_opportunities.length > 0 && (
        <OptimizationOpportunities opportunities={optimization_opportunities} />
      )}

      {license_breakdown && license_breakdown.length > 0 && (
        <LicenseBreakdownTable licenses={license_breakdown} />
      )}
    </div>
  );
};

export default CostForecasting;
