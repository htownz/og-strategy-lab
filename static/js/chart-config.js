// Chart configuration for OG Signal Bot Dashboard

// Signal History Chart
function initSignalHistoryChart(ctx) {
    // Sample data - in production this would come from the backend
    const labels = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
    const upSignals = [2, 3, 1, 4, 2, 0, 1];
    const downSignals = [1, 2, 3, 1, 1, 0, 2];
    
    new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [
                {
                    label: 'Up Signals',
                    data: upSignals,
                    backgroundColor: 'rgba(40, 167, 69, 0.7)',
                    borderColor: 'rgb(40, 167, 69)',
                    borderWidth: 1
                },
                {
                    label: 'Down Signals',
                    data: downSignals,
                    backgroundColor: 'rgba(220, 53, 69, 0.7)',
                    borderColor: 'rgb(220, 53, 69)',
                    borderWidth: 1
                }
            ]
        },
        options: {
            responsive: true,
            scales: {
                y: {
                    beginAtZero: true,
                    title: {
                        display: true,
                        text: 'Number of Signals'
                    },
                    ticks: {
                        precision: 0
                    }
                },
                x: {
                    title: {
                        display: true,
                        text: 'Day of Week'
                    }
                }
            },
            plugins: {
                legend: {
                    position: 'top',
                },
                title: {
                    display: true,
                    text: 'Weekly Signal History'
                }
            }
        }
    });
}

// P&L Chart
function initPnLChart(ctx) {
    // Sample data - in production this would come from the backend
    const labels = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
    const pnlData = [120, -50, 200, 80, -30, 0, 150];
    
    // Calculate cumulative P&L
    const cumulativeData = [];
    let cumulative = 0;
    pnlData.forEach(value => {
        cumulative += value;
        cumulativeData.push(cumulative);
    });
    
    new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [
                {
                    label: 'Daily P&L',
                    data: pnlData,
                    backgroundColor: 'rgba(0, 123, 255, 0.2)',
                    borderColor: 'rgb(0, 123, 255)',
                    borderWidth: 2,
                    type: 'bar'
                },
                {
                    label: 'Cumulative P&L',
                    data: cumulativeData,
                    backgroundColor: 'rgba(255, 193, 7, 0.1)',
                    borderColor: 'rgb(255, 193, 7)',
                    borderWidth: 2,
                    type: 'line',
                    yAxisID: 'y1'
                }
            ]
        },
        options: {
            responsive: true,
            scales: {
                y: {
                    position: 'left',
                    title: {
                        display: true,
                        text: 'Daily P&L ($)'
                    }
                },
                y1: {
                    position: 'right',
                    title: {
                        display: true,
                        text: 'Cumulative P&L ($)'
                    },
                    grid: {
                        drawOnChartArea: false
                    }
                },
                x: {
                    title: {
                        display: true,
                        text: 'Day of Week'
                    }
                }
            },
            plugins: {
                legend: {
                    position: 'top',
                },
                title: {
                    display: true,
                    text: 'Weekly P&L Performance'
                }
            }
        }
    });
}

// Position Distribution Chart
function initPositionDistributionChart(ctx) {
    // Sample data - in production this would come from the backend
    const data = {
        labels: ['AMD', 'AAPL', 'MSFT', 'TSLA', 'NVDA'],
        datasets: [{
            label: 'Position Value ($)',
            data: [4000, 3500, 2800, 2200, 1800],
            backgroundColor: [
                'rgba(255, 99, 132, 0.7)',
                'rgba(54, 162, 235, 0.7)',
                'rgba(255, 206, 86, 0.7)',
                'rgba(75, 192, 192, 0.7)',
                'rgba(153, 102, 255, 0.7)'
            ],
            borderColor: [
                'rgba(255, 99, 132, 1)',
                'rgba(54, 162, 235, 1)',
                'rgba(255, 206, 86, 1)',
                'rgba(75, 192, 192, 1)',
                'rgba(153, 102, 255, 1)'
            ],
            borderWidth: 1
        }]
    };
    
    new Chart(ctx, {
        type: 'pie',
        data: data,
        options: {
            responsive: true,
            plugins: {
                legend: {
                    position: 'right',
                },
                title: {
                    display: true,
                    text: 'Position Distribution'
                }
            }
        }
    });
}
