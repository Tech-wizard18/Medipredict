// static/js/charts.js

/**
 * MediPredict - Charts and Visualization
 * Chart.js integration for data visualization
 */

class MediPredictCharts {
    constructor() {
        this.charts = new Map();
        this.colors = {
            primary: '#4361ee',
            secondary: '#7209b7',
            success: '#4caf50',
            danger: '#f44336',
            warning: '#ff9800',
            info: '#2196f3',
            teal: '#4cc9f0',
            pink: '#f72585',
            orange: '#f8961e',
            green: '#38b000'
        };
        
        this.init();
    }
    
    init() {
        // Initialize all charts on page
        this.initializeCharts();
        
        // Handle window resize
        window.addEventListener('resize', this.debounce(() => {
            this.charts.forEach(chart => {
                chart.resize();
            });
        }, 250));
    }
    
    initializeCharts() {
        // Find all chart canvases
        document.querySelectorAll('.chart-canvas').forEach(canvas => {
            const chartType = canvas.dataset.chartType || 'line';
            const chartId = canvas.id;
            
            switch(chartType) {
                case 'line':
                    this.createLineChart(chartId, canvas);
                    break;
                case 'bar':
                    this.createBarChart(chartId, canvas);
                    break;
                case 'pie':
                    this.createPieChart(chartId, canvas);
                    break;
                case 'doughnut':
                    this.createDoughnutChart(chartId, canvas);
                    break;
                case 'radar':
                    this.createRadarChart(chartId, canvas);
                    break;
                case 'polar':
                    this.createPolarAreaChart(chartId, canvas);
                    break;
                case 'bubble':
                    this.createBubbleChart(chartId, canvas);
                    break;
                case 'scatter':
                    this.createScatterChart(chartId, canvas);
                    break;
                default:
                    console.warn(`Unknown chart type: ${chartType}`);
            }
        });
    }
    
    createLineChart(chartId, canvas) {
        const ctx = canvas.getContext('2d');
        const data = this.getChartData(canvas);
        
        const chart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: data.labels || ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun'],
                datasets: data.datasets || [{
                    label: 'Dataset 1',
                    data: [12, 19, 3, 5, 2, 3],
                    borderColor: this.colors.primary,
                    backgroundColor: 'rgba(67, 97, 238, 0.1)',
                    tension: 0.4,
                    fill: true
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'top',
                    },
                    tooltip: {
                        mode: 'index',
                        intersect: false
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        grid: {
                            drawBorder: false
                        }
                    },
                    x: {
                        grid: {
                            display: false
                        }
                    }
                },
                interaction: {
                    intersect: false,
                    mode: 'nearest'
                }
            }
        });
        
        this.charts.set(chartId, chart);
    }
    
    createBarChart(chartId, canvas) {
        const ctx = canvas.getContext('2d');
        const data = this.getChartData(canvas);
        
        const chart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: data.labels || ['Diabetes', 'Heart', 'Kidney', 'Parkinson', 'Cancer', 'Liver'],
                datasets: data.datasets || [{
                    label: 'Positive Cases',
                    data: [12, 19, 3, 5, 2, 3],
                    backgroundColor: this.colors.primary,
                    borderColor: this.colors.primary,
                    borderWidth: 1
                }, {
                    label: 'Negative Cases',
                    data: [8, 11, 7, 15, 8, 7],
                    backgroundColor: this.colors.secondary,
                    borderColor: this.colors.secondary,
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'top',
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        grid: {
                            drawBorder: false
                        }
                    },
                    x: {
                        grid: {
                            display: false
                        }
                    }
                }
            }
        });
        
        this.charts.set(chartId, chart);
    }
    
    createPieChart(chartId, canvas) {
        const ctx = canvas.getContext('2d');
        const data = this.getChartData(canvas);
        
        const chart = new Chart(ctx, {
            type: 'pie',
            data: {
                labels: data.labels || ['High Risk', 'Medium Risk', 'Low Risk'],
                datasets: [{
                    data: data.values || [30, 50, 20],
                    backgroundColor: [
                        this.colors.danger,
                        this.colors.warning,
                        this.colors.success
                    ],
                    borderWidth: 2,
                    borderColor: '#fff'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'right'
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                const label = context.label || '';
                                const value = context.parsed;
                                const total = context.dataset.data.reduce((a, b) => a + b, 0);
                                const percentage = Math.round((value / total) * 100);
                                return `${label}: ${value} (${percentage}%)`;
                            }
                        }
                    }
                }
            }
        });
        
        this.charts.set(chartId, chart);
    }
    
    createDoughnutChart(chartId, canvas) {
        const ctx = canvas.getContext('2d');
        const data = this.getChartData(canvas);
        
        const chart = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: data.labels || ['Male', 'Female', 'Other'],
                datasets: [{
                    data: data.values || [45, 50, 5],
                    backgroundColor: [
                        this.colors.primary,
                        this.colors.pink,
                        this.colors.teal
                    ],
                    borderWidth: 2,
                    borderColor: '#fff'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                cutout: '70%',
                plugins: {
                    legend: {
                        position: 'right'
                    }
                }
            }
        });
        
        this.charts.set(chartId, chart);
    }
    
    createRadarChart(chartId, canvas) {
        const ctx = canvas.getContext('2d');
        const data = this.getChartData(canvas);
        
        const chart = new Chart(ctx, {
            type: 'radar',
            data: {
                labels: data.labels || ['Diabetes', 'Heart', 'Kidney', 'Liver', 'Cancer', 'Parkinson'],
                datasets: [{
                    label: 'Risk Factors',
                    data: data.values || [65, 59, 90, 81, 56, 55],
                    backgroundColor: 'rgba(67, 97, 238, 0.2)',
                    borderColor: this.colors.primary,
                    pointBackgroundColor: this.colors.primary,
                    pointBorderColor: '#fff',
                    pointHoverBackgroundColor: '#fff',
                    pointHoverBorderColor: this.colors.primary
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    r: {
                        angleLines: {
                            display: true
                        },
                        suggestedMin: 0,
                        suggestedMax: 100
                    }
                }
            }
        });
        
        this.charts.set(chartId, chart);
    }
    
    createPolarAreaChart(chartId, canvas) {
        const ctx = canvas.getContext('2d');
        const data = this.getChartData(canvas);
        
        const chart = new Chart(ctx, {
            type: 'polarArea',
            data: {
                labels: data.labels || ['18-30', '31-45', '46-60', '61+'],
                datasets: [{
                    data: data.values || [11, 16, 7, 3],
                    backgroundColor: [
                        this.colors.primary,
                        this.colors.secondary,
                        this.colors.teal,
                        this.colors.orange
                    ],
                    borderWidth: 2,
                    borderColor: '#fff'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    r: {
                        ticks: {
                            display: false
                        }
                    }
                }
            }
        });
        
        this.charts.set(chartId, chart);
    }
    
    createBubbleChart(chartId, canvas) {
        const ctx = canvas.getContext('2d');
        const data = this.getChartData(canvas);
        
        const chart = new Chart(ctx, {
            type: 'bubble',
            data: {
                datasets: data.datasets || [{
                    label: 'Risk vs Age',
                    data: [
                        {x: 20, y: 30, r: 15},
                        {x: 40, y: 10, r: 10},
                        {x: 30, y: 20, r: 20},
                        {x: 50, y: 40, r: 25},
                        {x: 60, y: 35, r: 30}
                    ],
                    backgroundColor: this.colors.primary,
                    borderColor: this.colors.primary
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    x: {
                        title: {
                            display: true,
                            text: 'Age'
                        }
                    },
                    y: {
                        title: {
                            display: true,
                            text: 'Risk Score'
                        }
                    }
                }
            }
        });
        
        this.charts.set(chartId, chart);
    }
    
    createScatterChart(chartId, canvas) {
        const ctx = canvas.getContext('2d');
        const data = this.getChartData(canvas);
        
        const chart = new Chart(ctx, {
            type: 'scatter',
            data: {
                datasets: data.datasets || [{
                    label: 'Blood Pressure vs Cholesterol',
                    data: [
                        {x: 120, y: 180},
                        {x: 130, y: 200},
                        {x: 140, y: 220},
                        {x: 110, y: 160},
                        {x: 150, y: 240}
                    ],
                    backgroundColor: this.colors.primary,
                    borderColor: this.colors.primary
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    x: {
                        title: {
                            display: true,
                            text: 'Systolic BP'
                        }
                    },
                    y: {
                        title: {
                            display: true,
                            text: 'Cholesterol'
                        }
                    }
                }
            }
        });
        
        this.charts.set(chartId, chart);
    }
    
    getChartData(canvas) {
        // Try to get data from data attributes
        try {
            const dataAttr = canvas.dataset.chartData;
            if (dataAttr) {
                return JSON.parse(dataAttr);
            }
        } catch (e) {
            console.error('Failed to parse chart data:', e);
        }
        
        // Try to get data from a script tag with matching ID
        const dataScript = document.getElementById(`${canvas.id}-data`);
        if (dataScript) {
            try {
                return JSON.parse(dataScript.textContent);
            } catch (e) {
                console.error('Failed to parse chart data from script:', e);
            }
        }
        
        return {};
    }
    
    updateChart(chartId, newData) {
        const chart = this.charts.get(chartId);
        if (chart) {
            chart.data = newData;
            chart.update();
        }
    }
    
    destroyChart(chartId) {
        const chart = this.charts.get(chartId);
        if (chart) {
            chart.destroy();
            this.charts.delete(chartId);
        }
    }
    
    getChartInstance(chartId) {
        return this.charts.get(chartId);
    }
    
    // Utility: Debounce function
    debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }
    
    // Export chart as image
    exportChart(chartId, fileName = 'chart.png') {
        const chart = this.charts.get(chartId);
        if (chart) {
            const link = document.createElement('a');
            link.download = fileName;
            link.href = chart.toBase64Image();
            link.click();
        }
    }
    
    // Print chart
    printChart(chartId) {
        const chart = this.charts.get(chartId);
        if (chart) {
            const win = window.open('');
            win.document.write(`
                <html>
                    <head>
                        <title>Print Chart</title>
                        <style>
                            body { text-align: center; padding: 20px; }
                            img { max-width: 100%; height: auto; }
                        </style>
                    </head>
                    <body>
                        <img src="${chart.toBase64Image()}" />
                        <script>
                            window.onload = function() {
                                window.print();
                                window.onafterprint = function() {
                                    window.close();
                                };
                            };
                        </script>
                    </body>
                </html>
            `);
            win.document.close();
        }
    }
    
    // Create prediction trend chart
    createPredictionTrendChart(canvasId, data) {
        const canvas = document.getElementById(canvasId);
        if (!canvas) return;
        
        const ctx = canvas.getContext('2d');
        const chart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: data.labels,
                datasets: [{
                    label: 'Positive Predictions',
                    data: data.positive,
                    borderColor: this.colors.danger,
                    backgroundColor: 'rgba(244, 67, 54, 0.1)',
                    tension: 0.4,
                    fill: true
                }, {
                    label: 'Total Predictions',
                    data: data.total,
                    borderColor: this.colors.primary,
                    backgroundColor: 'rgba(67, 97, 238, 0.1)',
                    tension: 0.4,
                    fill: true
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'top',
                    },
                    tooltip: {
                        mode: 'index',
                        intersect: false
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        title: {
                            display: true,
                            text: 'Number of Predictions'
                        }
                    },
                    x: {
                        title: {
                            display: true,
                            text: 'Date'
                        }
                    }
                }
            }
        });
        
        this.charts.set(canvasId, chart);
    }
    
    // Create disease distribution chart
    createDiseaseDistributionChart(canvasId, data) {
        const canvas = document.getElementById(canvasId);
        if (!canvas) return;
        
        const ctx = canvas.getContext('2d');
        const chart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: data.labels,
                datasets: [{
                    label: 'Positive Cases',
                    data: data.positive,
                    backgroundColor: this.colors.danger,
                    borderColor: this.colors.danger,
                    borderWidth: 1
                }, {
                    label: 'Negative Cases',
                    data: data.negative,
                    backgroundColor: this.colors.success,
                    borderColor: this.colors.success,
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'top',
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        title: {
                            display: true,
                            text: 'Number of Cases'
                        }
                    },
                    x: {
                        title: {
                            display: true,
                            text: 'Disease Type'
                        }
                    }
                }
            }
        });
        
        this.charts.set(canvasId, chart);
    }
    
    // Create risk score chart
    createRiskScoreChart(canvasId, scores) {
        const canvas = document.getElementById(canvasId);
        if (!canvas) return;
        
        const ctx = canvas.getContext('2d');
        const chart = new Chart(ctx, {
            type: 'radar',
            data: {
                labels: ['Diabetes', 'Heart Disease', 'Kidney Disease', 'Liver Disease', 'Cancer Risk', 'Parkinson'],
                datasets: [{
                    label: 'Your Risk Score',
                    data: scores,
                    backgroundColor: 'rgba(67, 97, 238, 0.2)',
                    borderColor: this.colors.primary,
                    pointBackgroundColor: this.colors.primary,
                    pointBorderColor: '#fff',
                    pointHoverBackgroundColor: '#fff',
                    pointHoverBorderColor: this.colors.primary
                }, {
                    label: 'Average Risk',
                    data: [50, 50, 50, 50, 50, 50],
                    backgroundColor: 'rgba(114, 9, 183, 0.2)',
                    borderColor: this.colors.secondary,
                    pointBackgroundColor: this.colors.secondary,
                    pointBorderColor: '#fff',
                    pointHoverBackgroundColor: '#fff',
                    pointHoverBorderColor: this.colors.secondary
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    r: {
                        angleLines: {
                            display: true
                        },
                        suggestedMin: 0,
                        suggestedMax: 100
                    }
                }
            }
        });
        
        this.charts.set(canvasId, chart);
    }
}

// Initialize charts when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    window.MediPredictCharts = new MediPredictCharts();
});

// Export for module usage
if (typeof module !== 'undefined' && module.exports) {
    module.exports = MediPredictCharts;
}