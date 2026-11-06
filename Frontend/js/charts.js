/**
 * WeatherIQ - Chart Utilities powered by Chart.js 4.x
 */

class WeatherCharts {
  constructor() {
    this.instances = {};
    this.colors = {
      blue: '#2563eb',
      lightBlue: '#60a5fa',
      cyan: '#06b6d4',
      amber: '#f59e0b',
      red: '#ef4444',
      emerald: '#10b981',
      purple: '#8b5cf6',
      grid: getComputedStyle(document.documentElement).getPropertyValue('--chart-grid').trim(),
      textMuted: getComputedStyle(document.documentElement).getPropertyValue('--chart-text').trim(),
      textLight: getComputedStyle(document.documentElement).getPropertyValue('--color-text-primary').trim()
    };

    this.defaultOptions = {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          labels: {
            color: this.colors.textMuted,
            font: { family: 'Inter', size: 12 }
          }
        },
        tooltip: {
          backgroundColor: getComputedStyle(document.documentElement).getPropertyValue('--chart-tooltip-bg').trim(),
          titleColor: getComputedStyle(document.documentElement).getPropertyValue('--color-text-primary').trim(),
          bodyColor: getComputedStyle(document.documentElement).getPropertyValue('--chart-text').trim(),
          borderColor: getComputedStyle(document.documentElement).getPropertyValue('--chart-tooltip-border').trim(),
          borderWidth: 1,
          padding: 10,
          boxPadding: 4,
          usePointStyle: true
        }
      },
      scales: {
        x: {
          grid: { color: this.colors.grid },
          ticks: { color: this.colors.textMuted, font: { family: 'Inter', size: 11 } }
        },
        y: {
          grid: { color: this.colors.grid },
          ticks: { color: this.colors.textMuted, font: { family: 'Inter', size: 11 } }
        }
      }
    };

    window.addEventListener('weatheriq:themechange', () => this.updateTheme());
  }

  updateTheme() {
    const styles = getComputedStyle(document.documentElement);
    this.colors.grid = styles.getPropertyValue('--chart-grid').trim();
    this.colors.textMuted = styles.getPropertyValue('--chart-text').trim();
    this.colors.textLight = styles.getPropertyValue('--color-text-primary').trim();
    this.defaultOptions.scales.x.grid.color = this.colors.grid;
    this.defaultOptions.scales.x.ticks.color = this.colors.textMuted;
    this.defaultOptions.scales.y.grid.color = this.colors.grid;
    this.defaultOptions.scales.y.ticks.color = this.colors.textMuted;
    this.defaultOptions.plugins.legend.labels.color = this.colors.textMuted;
    this.defaultOptions.plugins.tooltip.backgroundColor = styles.getPropertyValue('--chart-tooltip-bg').trim();
    this.defaultOptions.plugins.tooltip.titleColor = this.colors.textLight;
    this.defaultOptions.plugins.tooltip.bodyColor = this.colors.textMuted;
    this.defaultOptions.plugins.tooltip.borderColor = styles.getPropertyValue('--chart-tooltip-border').trim();

    Object.values(this.instances).forEach(chart => {
      chart.options.plugins.legend.labels.color = this.colors.textMuted;
      chart.options.plugins.tooltip.backgroundColor = this.defaultOptions.plugins.tooltip.backgroundColor;
      chart.options.plugins.tooltip.titleColor = this.colors.textLight;
      chart.options.plugins.tooltip.bodyColor = this.colors.textMuted;
      chart.options.plugins.tooltip.borderColor = this.defaultOptions.plugins.tooltip.borderColor;
      Object.values(chart.options.scales || {}).forEach(scale => {
        if (scale.grid) scale.grid.color = this.colors.grid;
        if (scale.ticks) scale.ticks.color = this.colors.textMuted;
        if (scale.title) scale.title.color = this.colors.textMuted;
      });
      chart.update('none');
    });
  }

  destroyChart(id) {
    if (this.instances[id]) {
      this.instances[id].destroy();
      delete this.instances[id];
    }
  }

  renderHourlyTemp(canvasId, labels, dataPoints) {
    this.destroyChart(canvasId);
    const ctx = document.getElementById(canvasId);
    if (!ctx) return;

    this.instances[canvasId] = new Chart(ctx, {
      type: 'line',
      data: {
        labels: labels,
        datasets: [{
          label: 'Temperature (°C)',
          data: dataPoints,
          borderColor: this.colors.cyan,
          backgroundColor: 'rgba(6, 182, 212, 0.15)',
          fill: true,
          tension: 0.35,
          pointRadius: 3,
          pointHoverRadius: 6
        }]
      },
      options: {
        ...this.defaultOptions,
        plugins: {
          ...this.defaultOptions.plugins,
          title: { display: false }
        }
      }
    });
  }

  render5DayForecast(canvasId, labels, temps, rainProb) {
    this.destroyChart(canvasId);
    const ctx = document.getElementById(canvasId);
    if (!ctx) return;

    this.instances[canvasId] = new Chart(ctx, {
      type: 'bar',
      data: {
        labels: labels,
        datasets: [
          {
            type: 'line',
            label: 'Avg Temp (°C)',
            data: temps,
            borderColor: this.colors.amber,
            backgroundColor: 'transparent',
            tension: 0.3,
            yAxisID: 'y'
          },
          {
            type: 'bar',
            label: 'Rainfall Probability (%)',
            data: rainProb,
            backgroundColor: 'rgba(37, 99, 235, 0.55)',
            borderColor: this.colors.blue,
            borderWidth: 1,
            borderRadius: 4,
            yAxisID: 'y1'
          }
        ]
      },
      options: {
        ...this.defaultOptions,
        scales: {
          x: this.defaultOptions.scales.x,
          y: {
            ...this.defaultOptions.scales.y,
            title: { display: true, text: 'Temp (°C)', color: this.colors.textMuted }
          },
          y1: {
            position: 'right',
            grid: { drawOnChartArea: false },
            ticks: { color: this.colors.textMuted, callback: v => `${v}%` },
            min: 0,
            max: 100,
            title: { display: true, text: 'Rain %', color: this.colors.textMuted }
          }
        }
      }
    });
  }

  renderComparison(canvasId, labels, datasets) {
    this.destroyChart(canvasId);
    const ctx = document.getElementById(canvasId);
    if (!ctx) return;

    this.instances[canvasId] = new Chart(ctx, {
      type: 'bar',
      data: {
        labels: labels,
        datasets: datasets
      },
      options: {
        ...this.defaultOptions,
        plugins: {
          ...this.defaultOptions.plugins
        },
        scales: {
          x: this.defaultOptions.scales.x,
          y: {
            ...this.defaultOptions.scales.y,
            title: { display: true, text: 'Temperature (°C)', color: this.colors.textMuted }
          },
          y1: {
            position: 'right',
            grid: { drawOnChartArea: false },
            min: 0,
            max: 100,
            ticks: { color: this.colors.textMuted, callback: value => `${value}%` },
            title: { display: true, text: 'Humidity (%)', color: this.colors.textMuted }
          }
        }
      }
    });
  }

  renderTimeSeries(canvasId, labels, datasets, yAxisTitle, secondaryAxis) {
    this.destroyChart(canvasId);
    const ctx = document.getElementById(canvasId);
    if (!ctx) return;

    const hasSecondaryAxis = datasets.some(dataset => dataset.yAxisID === 'y1');
    const scales = {
      x: this.defaultOptions.scales.x,
      y: {
        ...this.defaultOptions.scales.y,
        title: { display: true, text: yAxisTitle, color: this.colors.textMuted },
        min: hasSecondaryAxis ? undefined : secondaryAxis && secondaryAxis.min,
        max: hasSecondaryAxis ? undefined : secondaryAxis && secondaryAxis.max
      }
    };

    if (hasSecondaryAxis) {
      scales.y1 = {
        position: 'right',
        grid: { drawOnChartArea: false },
        ticks: { color: this.colors.textMuted },
        title: {
          display: true,
          text: secondaryAxis && secondaryAxis.title,
          color: this.colors.textMuted
        },
        min: secondaryAxis && secondaryAxis.min,
        max: secondaryAxis && secondaryAxis.max
      };
    }

    this.instances[canvasId] = new Chart(ctx, {
      type: 'line',
      data: { labels, datasets },
      options: {
        ...this.defaultOptions,
        interaction: { mode: 'index', intersect: false },
        plugins: { ...this.defaultOptions.plugins },
        scales
      }
    });
  }

  renderTrend(canvasId, label, labels, dataPoints, color = 'blue') {
    this.destroyChart(canvasId);
    const ctx = document.getElementById(canvasId);
    if (!ctx) return;

    const chosenColor = this.colors[color] || this.colors.blue;

    this.instances[canvasId] = new Chart(ctx, {
      type: 'line',
      data: {
        labels: labels,
        datasets: [{
          label: label,
          data: dataPoints,
          borderColor: chosenColor,
          backgroundColor: `${chosenColor}22`,
          fill: true,
          tension: 0.3
        }]
      },
      options: this.defaultOptions
    });
  }
}

window.weatherCharts = new WeatherCharts();
