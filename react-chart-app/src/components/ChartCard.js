import React, { useState, useEffect } from 'react';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  ArcElement,
  Title,
  Tooltip,
  Legend,
} from 'chart.js';
import { Bar, Pie } from 'react-chartjs-2';
import axios from 'axios';

ChartJS.register(
  CategoryScale,
  LinearScale,
  BarElement,
  ArcElement,
  Title,
  Tooltip,
  Legend
);

const API_BASE_URL = 'http://localhost:8000';

const ChartCard = ({ chartType, title }) => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchChartData();
  }, [chartType]);

  const fetchChartData = async () => {
    try {
      setLoading(true);
      setError(null);
      
      const response = await axios.get(`${API_BASE_URL}/api/chart/${chartType}`);
      
      if (response.data.success) {
        const chartData = response.data.data;
        
        if (chartType === 'countries') {
          setData({
            labels: chartData.map(item => item.Country),
            datasets: [
              {
                label: 'Users',
                data: chartData.map(item => item.UserCount),
                backgroundColor: [
                  '#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0', '#9966FF',
                  '#FF9F40', '#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0'
                ],
                borderColor: [
                  '#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0', '#9966FF',
                  '#FF9F40', '#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0'
                ],
                borderWidth: 1,
              },
            ],
          });
        } else if (chartType === 'departments') {
          setData({
            labels: chartData.map(item => item.Department),
            datasets: [
              {
                label: 'Users',
                data: chartData.map(item => item.UserCount),
                backgroundColor: [
                  '#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0', '#9966FF',
                  '#FF9F40', '#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0'
                ],
                borderColor: [
                  '#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0', '#9966FF',
                  '#FF9F40', '#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0'
                ],
                borderWidth: 1,
              },
            ],
          });
        }
      } else {
        setError('Failed to fetch chart data');
      }
    } catch (err) {
      setError(`Error: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const options = {
    responsive: true,
    plugins: {
      legend: {
        position: 'top',
      },
      title: {
        display: true,
        text: title,
      },
    },
    scales: chartType === 'countries' ? {
      y: {
        beginAtZero: true,
      },
    } : {},
  };

  if (loading) {
    return (
      <div className="chart-card">
        <div className="chart-title">{title}</div>
        <div className="loading">Loading chart data...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="chart-card">
        <div className="chart-title">{title}</div>
        <div className="error">{error}</div>
      </div>
    );
  }

  return (
    <div className="chart-card">
      <div className="chart-title">{title}</div>
      {data && (
        chartType === 'countries' ? 
          <Bar data={data} options={options} /> : 
          <Pie data={data} options={options} />
      )}
    </div>
  );
};

export default ChartCard;