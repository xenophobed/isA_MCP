/**
 * React SDK Visualization Components
 * Example implementation for consuming the Python data visualization service JSON specs
 */

import React from 'react';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  LineElement,
  PointElement,
  ArcElement,
  Title,
  Tooltip,
  Legend,
} from 'chart.js';
import { Bar, Line, Pie, Scatter } from 'react-chartjs-2';
import {
  BarChart,
  LineChart,
  PieChart,
  ScatterChart,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip as RechartsTooltip,
  Legend as RechartsLegend,
  Bar as RechartsBar,
  Line as RechartsLine,
  Cell,
} from 'recharts';

// Register Chart.js components
ChartJS.register(
  CategoryScale,
  LinearScale,
  BarElement,
  LineElement,
  PointElement,
  ArcElement,
  Title,
  Tooltip,
  Legend
);

// TypeScript interfaces for the Python service JSON output
interface VisualizationData {
  labels: string[];
  datasets: any[];
  metadata: Record<string, any>;
}

interface VisualizationConfig {
  responsive: boolean;
  maintainAspectRatio?: boolean;
  plugins?: Record<string, any>;
  scales?: Record<string, any>;
}

interface VisualizationSpec {
  id: string;
  type: 'bar' | 'line' | 'pie' | 'scatter' | 'table' | 'metric';
  title: string;
  description: string;
  data: VisualizationData;
  config: VisualizationConfig;
  library: 'chartjs' | 'recharts' | 'nivo';
  component_props: Record<string, any>;
  insights: string[];
  confidence_score: number;
}

interface DataVisualizationProps {
  specification: VisualizationSpec;
  height?: number;
  width?: string | number;
  showInsights?: boolean;
  showTitle?: boolean;
}

// Chart.js Bar Component
const ChartJSBarChart: React.FC<{ spec: VisualizationSpec; height?: number }> = ({ 
  spec, 
  height = 400 
}) => {
  const chartData = {
    labels: spec.data.labels,
    datasets: spec.data.datasets,
  };

  const options = {
    responsive: spec.config.responsive,
    maintainAspectRatio: spec.config.maintainAspectRatio || false,
    plugins: {
      title: {
        display: true,
        text: spec.title,
      },
      legend: {
        position: 'top' as const,
      },
      tooltip: {
        mode: 'index' as const,
        intersect: false,
      },
      ...spec.config.plugins,
    },
    scales: {
      x: {
        beginAtZero: true,
      },
      y: {
        beginAtZero: true,
      },
      ...spec.config.scales,
    },
  };

  return (
    <div style={{ height }}>
      <Bar data={chartData} options={options} />
    </div>
  );
};

// Chart.js Line Component
const ChartJSLineChart: React.FC<{ spec: VisualizationSpec; height?: number }> = ({ 
  spec, 
  height = 400 
}) => {
  const chartData = {
    labels: spec.data.labels,
    datasets: spec.data.datasets,
  };

  const options = {
    responsive: spec.config.responsive,
    maintainAspectRatio: spec.config.maintainAspectRatio || false,
    plugins: {
      title: {
        display: true,
        text: spec.title,
      },
      legend: {
        position: 'top' as const,
      },
    },
    scales: {
      x: {
        display: true,
        title: {
          display: true,
          text: 'Time Period',
        },
      },
      y: {
        display: true,
        title: {
          display: true,
          text: 'Value',
        },
      },
    },
    interaction: {
      mode: 'index' as const,
      intersect: false,
    },
    elements: {
      line: {
        tension: 0.1,
      },
    },
  };

  return (
    <div style={{ height }}>
      <Line data={chartData} options={options} />
    </div>
  );
};

// Chart.js Pie Component
const ChartJSPieChart: React.FC<{ spec: VisualizationSpec; height?: number }> = ({ 
  spec, 
  height = 400 
}) => {
  const chartData = {
    labels: spec.data.labels,
    datasets: spec.data.datasets,
  };

  const options = {
    responsive: spec.config.responsive,
    maintainAspectRatio: spec.config.maintainAspectRatio || false,
    plugins: {
      title: {
        display: true,
        text: spec.title,
      },
      legend: {
        position: 'right' as const,
      },
      tooltip: {
        callbacks: {
          label: function(context: any) {
            const label = context.label || '';
            const value = context.parsed;
            const total = context.dataset.data.reduce((a: number, b: number) => a + b, 0);
            const percentage = ((value / total) * 100).toFixed(1);
            return `${label}: ${value} (${percentage}%)`;
          },
        },
      },
    },
  };

  return (
    <div style={{ height }}>
      <Pie data={chartData} options={options} />
    </div>
  );
};

// Chart.js Scatter Component
const ChartJSScatterChart: React.FC<{ spec: VisualizationSpec; height?: number }> = ({ 
  spec, 
  height = 400 
}) => {
  const chartData = {
    datasets: spec.data.datasets,
  };

  const options = {
    responsive: spec.config.responsive,
    maintainAspectRatio: spec.config.maintainAspectRatio || false,
    plugins: {
      title: {
        display: true,
        text: spec.title,
      },
      legend: {
        position: 'top' as const,
      },
    },
    scales: {
      x: {
        type: 'linear' as const,
        position: 'bottom' as const,
        title: {
          display: true,
          text: spec.data.labels[0] || 'X Axis',
        },
      },
      y: {
        title: {
          display: true,
          text: spec.data.labels[1] || 'Y Axis',
        },
      },
    },
  };

  return (
    <div style={{ height }}>
      <Scatter data={chartData} options={options} />
    </div>
  );
};

// Recharts Bar Component
const RechartsBarChart: React.FC<{ spec: VisualizationSpec; height?: number }> = ({ 
  spec, 
  height = 400 
}) => {
  // Transform data for Recharts format
  const rechartsData = spec.data.labels.map((label, index) => ({
    name: label,
    value: spec.data.datasets[0].data[index],
  }));

  return (
    <BarChart width={800} height={height} data={rechartsData}>
      <CartesianGrid strokeDasharray="3 3" />
      <XAxis dataKey="name" />
      <YAxis />
      <RechartsTooltip />
      <RechartsLegend />
      <RechartsBar dataKey="value" fill="#3B82F6" />
    </BarChart>
  );
};

// Recharts Line Component
const RechartsLineChart: React.FC<{ spec: VisualizationSpec; height?: number }> = ({ 
  spec, 
  height = 400 
}) => {
  // Transform data for Recharts format
  const rechartsData = spec.data.labels.map((label, index) => {
    const dataPoint: any = { name: label };
    spec.data.datasets.forEach((dataset, datasetIndex) => {
      dataPoint[dataset.label || `series${datasetIndex}`] = dataset.data[index];
    });
    return dataPoint;
  });

  const colors = ['#3B82F6', '#EF4444', '#10B981', '#F59E0B', '#8B5CF6'];

  return (
    <LineChart width={800} height={height} data={rechartsData}>
      <CartesianGrid strokeDasharray="3 3" />
      <XAxis dataKey="name" />
      <YAxis />
      <RechartsTooltip />
      <RechartsLegend />
      {spec.data.datasets.map((dataset, index) => (
        <RechartsLine
          key={index}
          type="monotone"
          dataKey={dataset.label || `series${index}`}
          stroke={colors[index % colors.length]}
          strokeWidth={2}
          dot={{ r: 4 }}
        />
      ))}
    </LineChart>
  );
};

// Metric Display Component
const MetricDisplay: React.FC<{ spec: VisualizationSpec }> = ({ spec }) => {
  const value = spec.data.datasets[0]?.value;
  const label = spec.data.datasets[0]?.label;
  const format = spec.data.metadata?.format;

  const formatValue = (val: number) => {
    if (format === 'currency') {
      return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD',
      }).format(val);
    }
    if (format === 'percentage') {
      return `${val.toFixed(1)}%`;
    }
    return new Intl.NumberFormat('en-US').format(val);
  };

  return (
    <div className="metric-display" style={{
      padding: '2rem',
      textAlign: 'center',
      border: '1px solid #e5e7eb',
      borderRadius: '8px',
      backgroundColor: '#f9fafb',
    }}>
      <h3 style={{ margin: '0 0 1rem 0', color: '#374151' }}>{spec.title}</h3>
      <div style={{
        fontSize: '3rem',
        fontWeight: 'bold',
        color: '#1f2937',
        marginBottom: '0.5rem',
      }}>
        {formatValue(value)}
      </div>
      <div style={{ color: '#6b7280', fontSize: '1rem' }}>{label}</div>
    </div>
  );
};

// Data Table Component
const DataTable: React.FC<{ spec: VisualizationSpec }> = ({ spec }) => {
  const data = spec.data.datasets[0]?.data || [];
  const columns = spec.data.datasets[0]?.columns || [];
  const isPaginated = spec.data.metadata?.paginated;

  const [currentPage, setCurrentPage] = React.useState(1);
  const itemsPerPage = 50;
  
  const startIndex = (currentPage - 1) * itemsPerPage;
  const endIndex = startIndex + itemsPerPage;
  const currentData = isPaginated ? data.slice(startIndex, endIndex) : data;
  const totalPages = Math.ceil(data.length / itemsPerPage);

  return (
    <div className="data-table">
      <h3 style={{ marginBottom: '1rem' }}>{spec.title}</h3>
      <div style={{ overflowX: 'auto' }}>
        <table style={{
          width: '100%',
          borderCollapse: 'collapse',
          border: '1px solid #e5e7eb',
        }}>
          <thead>
            <tr style={{ backgroundColor: '#f9fafb' }}>
              {columns.map((column: string, index: number) => (
                <th
                  key={index}
                  style={{
                    padding: '0.75rem',
                    textAlign: 'left',
                    borderBottom: '1px solid #e5e7eb',
                    fontWeight: '600',
                  }}
                >
                  {column}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {currentData.map((row: any, rowIndex: number) => (
              <tr key={rowIndex} style={{
                borderBottom: '1px solid #e5e7eb',
              }}>
                {columns.map((column: string, colIndex: number) => (
                  <td
                    key={colIndex}
                    style={{
                      padding: '0.75rem',
                      borderRight: colIndex < columns.length - 1 ? '1px solid #e5e7eb' : 'none',
                    }}
                  >
                    {row[column]}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      
      {isPaginated && totalPages > 1 && (
        <div style={{
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
          gap: '1rem',
          marginTop: '1rem',
        }}>
          <button
            onClick={() => setCurrentPage(Math.max(1, currentPage - 1))}
            disabled={currentPage === 1}
            style={{
              padding: '0.5rem 1rem',
              border: '1px solid #d1d5db',
              borderRadius: '4px',
              backgroundColor: currentPage === 1 ? '#f3f4f6' : 'white',
              cursor: currentPage === 1 ? 'not-allowed' : 'pointer',
            }}
          >
            Previous
          </button>
          <span>
            Page {currentPage} of {totalPages}
          </span>
          <button
            onClick={() => setCurrentPage(Math.min(totalPages, currentPage + 1))}
            disabled={currentPage === totalPages}
            style={{
              padding: '0.5rem 1rem',
              border: '1px solid #d1d5db',
              borderRadius: '4px',
              backgroundColor: currentPage === totalPages ? '#f3f4f6' : 'white',
              cursor: currentPage === totalPages ? 'not-allowed' : 'pointer',
            }}
          >
            Next
          </button>
        </div>
      )}
    </div>
  );
};

// Insights Panel Component
const InsightsPanel: React.FC<{ insights: string[]; confidence: number }> = ({ 
  insights, 
  confidence 
}) => {
  return (
    <div style={{
      marginTop: '1rem',
      padding: '1rem',
      backgroundColor: '#f0f9ff',
      borderRadius: '8px',
      border: '1px solid #0ea5e9',
    }}>
      <h4 style={{ margin: '0 0 0.5rem 0', color: '#0369a1' }}>
        Data Insights (Confidence: {(confidence * 100).toFixed(0)}%)
      </h4>
      <ul style={{ margin: 0, paddingLeft: '1.5rem' }}>
        {insights.map((insight, index) => (
          <li key={index} style={{ marginBottom: '0.25rem', color: '#075985' }}>
            {insight}
          </li>
        ))}
      </ul>
    </div>
  );
};

// Main Data Visualization Component
const DataVisualization: React.FC<DataVisualizationProps> = ({
  specification,
  height = 400,
  width = '100%',
  showInsights = true,
  showTitle = true,
}) => {
  const renderChart = () => {
    const { type, library } = specification;

    // Chart.js implementations
    if (library === 'chartjs') {
      switch (type) {
        case 'bar':
          return <ChartJSBarChart spec={specification} height={height} />;
        case 'line':
          return <ChartJSLineChart spec={specification} height={height} />;
        case 'pie':
          return <ChartJSPieChart spec={specification} height={height} />;
        case 'scatter':
          return <ChartJSScatterChart spec={specification} height={height} />;
        case 'metric':
          return <MetricDisplay spec={specification} />;
        case 'table':
          return <DataTable spec={specification} />;
        default:
          return <div>Unsupported chart type: {type}</div>;
      }
    }

    // Recharts implementations
    if (library === 'recharts') {
      switch (type) {
        case 'bar':
          return <RechartsBarChart spec={specification} height={height} />;
        case 'line':
          return <RechartsLineChart spec={specification} height={height} />;
        case 'metric':
          return <MetricDisplay spec={specification} />;
        case 'table':
          return <DataTable spec={specification} />;
        default:
          return <div>Recharts implementation for {type} not available</div>;
      }
    }

    return <div>Unsupported library: {library}</div>;
  };

  return (
    <div style={{ width }}>
      {showTitle && (
        <div style={{ marginBottom: '1rem' }}>
          <h2 style={{ margin: '0 0 0.5rem 0' }}>{specification.title}</h2>
          <p style={{ margin: 0, color: '#6b7280' }}>{specification.description}</p>
        </div>
      )}
      
      {renderChart()}
      
      {showInsights && specification.insights.length > 0 && (
        <InsightsPanel 
          insights={specification.insights} 
          confidence={specification.confidence_score} 
        />
      )}
    </div>
  );
};

// Example usage component
const ExampleUsage: React.FC = () => {
  // Example data from your Python service
  const sampleVisualizationSpec: VisualizationSpec = {
    id: "viz_20241230_143022",
    type: "bar",
    title: "Sales Analysis - Comparison",
    description: "Analysis of sales (4 records)",
    library: "chartjs",
    data: {
      labels: ["iPhone 15", "Samsung Galaxy", "Google Pixel"],
      datasets: [{
        label: "Total Sales",
        data: [120000, 84000, 41000],
        backgroundColor: ["#3B82F6", "#EF4444", "#10B981"],
        borderColor: "#3B82F6",
        borderWidth: 1
      }],
      metadata: {}
    },
    config: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          position: "top"
        }
      }
    },
    component_props: {
      height: 400,
      type: "bar"
    },
    insights: [
      "Dataset contains 3 product categories",
      "iPhone 15 leads with 120,000 units sold",
      "Bar chart enables easy comparison across products"
    ],
    confidence_score: 0.88
  };

  return (
    <div style={{ padding: '2rem' }}>
      <h1>Data Visualization Examples</h1>
      
      {/* Basic usage */}
      <DataVisualization 
        specification={sampleVisualizationSpec}
        height={400}
        showInsights={true}
      />
      
      {/* Alternative with different library */}
      <div style={{ marginTop: '2rem' }}>
        <DataVisualization 
          specification={{
            ...sampleVisualizationSpec,
            library: 'recharts',
            title: 'Same Data with Recharts'
          }}
          height={400}
          showInsights={false}
        />
      </div>
    </div>
  );
};

export default DataVisualization;
export { ExampleUsage, type VisualizationSpec };