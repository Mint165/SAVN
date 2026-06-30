document.addEventListener('DOMContentLoaded', function() {
  console.log("HeartBits Dashboard JS: Initializing...");

  // ─── SAFETY CHECKS ─────────────────────────────────────
  if (typeof Chart === 'undefined') {
    console.error("Chart.js not found! Ensure the library is loaded in base.html.");
    return;
  }

  if (typeof dates === 'undefined' || !dates || !dates.length) {
    console.warn("No chart data available (dates is empty or undefined).");
    return;
  }

  // ─── CONFIGURATION ──────────────────────────────────────
  var lang = localStorage.getItem('lang') || 'vi';
  var isDark = document.documentElement.getAttribute('data-theme') === 'dark';
  var gridColor = isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.06)';
  var textColor = isDark ? '#94A3B8' : '#64748B';
  var pointStroke = isDark ? '#1E293B' : '#FFFFFF';
  var hasTrend = dates.length > 1;

  // Chart.js Global Defaults (v3/v4 compatible)
  Chart.defaults.color = textColor;
  Chart.defaults.font.family = "'Inter', system-ui, -apple-system, sans-serif";
  Chart.defaults.font.size = 13;
  Chart.defaults.font.weight = '500';

  // Bilingual chart labels
  var lbl = {
    systolic: lang === 'en' ? 'Systolic' : 'Tâm thu',
    diastolic: lang === 'en' ? 'Diastolic' : 'Tâm trương',
    risk: lang === 'en' ? 'Risk (%)' : 'Nguy cơ (%)',
    glucose: lang === 'en' ? 'Blood Glucose (mg/dL)' : 'Đường huyết (mg/dL)'
  };

  var baseOpts = {
    responsive: true,
    maintainAspectRatio: false, // Allow CSS to control height
    interaction: {
        intersect: false,
        mode: 'index',
    },
    animation: { 
        duration: 1000, 
        easing: 'easeOutQuart' 
    },
    plugins: { 
        legend: { 
            position: 'bottom', 
            labels: { 
                padding: 20, 
                usePointStyle: true, 
                pointStyle: 'circle',
                font: { weight: '600' }
            } 
        },
        tooltip: {
            backgroundColor: isDark ? '#1E293B' : '#FFFFFF',
            titleColor: isDark ? '#F1F5F9' : '#1F2937',
            bodyColor: isDark ? '#94A3B8' : '#64748B',
            borderColor: gridColor,
            borderWidth: 1,
            padding: 12,
            boxPadding: 6,
            usePointStyle: true,
            callbacks: {
                label: function(context) {
                    let label = context.dataset.label || '';
                    if (label) label += ': ';
                    if (context.parsed.y !== null) label += context.parsed.y;
                    return label;
                }
            }
        }
    },
    scales: {
      x: { 
          grid: { display: false }, 
          ticks: { color: textColor, padding: 8 } 
      },
      y: { 
          grid: { color: gridColor, drawBorder: false }, 
          ticks: { color: textColor, padding: 8 } 
      }
    }
  };

  function mkGrad(ctx, c1, c2) {
    if (!ctx) return c1;
    try {
        var g = ctx.createLinearGradient(0, 0, 0, 300);
        g.addColorStop(0, c1); 
        g.addColorStop(1, c2); 
        return g;
    } catch(e) { return c1; }
  }

  function lineOpts(color, fillColor, pointRadius, hoverRadius) {
    return {
      borderColor: color,
      backgroundColor: hasTrend ? fillColor : 'transparent',
      fill: hasTrend,
      tension: 0, // Sharper lines
      spanGaps: true,
      showLine: true, // Always show line even if 1 point (Chart.js handles it)
      borderWidth: 3,
      pointRadius: hasTrend ? pointRadius : 6,
      pointHoverRadius: hasTrend ? hoverRadius : 8,
      pointBackgroundColor: color,
      pointBorderColor: pointStroke,
      pointBorderWidth: 2,
      clip: 10
    };
  }

  // ─── INITIALIZATION ─────────────────────────────────────
  
  // BP Chart
  var bpCtx = document.getElementById('bpChart');
  if (bpCtx) {
    var bc = bpCtx.getContext('2d');
    window.bpChart = new Chart(bc, {
      type: 'line',
      data: {
        labels: dates,
        datasets: [
          Object.assign({ 
              label: lbl.systolic, 
              data: typeof systolicD !== 'undefined' ? systolicD : [] 
          }, lineOpts('#EF4444', mkGrad(bc, 'rgba(239,68,68,0.15)', 'rgba(239,68,68,0)'), 4, 6)),
          Object.assign({ 
              label: lbl.diastolic, 
              data: typeof diastolicD !== 'undefined' ? diastolicD : [] 
          }, lineOpts('#10B981', mkGrad(bc, 'rgba(16,185,129,0.15)', 'rgba(16,185,129,0)'), 4, 6))
        ]
      },
      options: JSON.parse(JSON.stringify(baseOpts)) // Deep clone for safety
    });
    window.bpChart.options.scales.y.beginAtZero = false;
    window.bpChart.update();
  }

  // Risk Chart
  var riskCtx = document.getElementById('riskChart');
  if (riskCtx) {
    var rc = riskCtx.getContext('2d');
    window.riskChart = new Chart(rc, {
      type: 'line',
      data: {
        labels: dates,
        datasets: [Object.assign({
          label: lbl.risk,
          data: typeof strokeScores !== 'undefined' ? strokeScores : [],
          segment: { 
              borderColor: function(ctx) { 
                  return ctx.p0.parsed.y >= 75 || ctx.p1.parsed.y >= 75 ? '#DC2626' : undefined; 
              },
              borderDash: function(ctx) {
                  return ctx.p0.parsed.y >= 55 || ctx.p1.parsed.y >= 55 ? [5, 5] : undefined;
              }
          }
        }, lineOpts('#F59E0B', mkGrad(rc, 'rgba(245,158,11,0.15)', 'rgba(245,158,11,0)'), 5, 7))]
      },
      options: JSON.parse(JSON.stringify(baseOpts))
    });
    window.riskChart.options.scales.y.beginAtZero = true;
    window.riskChart.options.scales.y.max = 100;
    window.riskChart.update();
  }

  // Glucose Chart
  var glCtx = document.getElementById('glucoseChart');
  if (glCtx) {
    var gc = glCtx.getContext('2d');
    window.glucoseChart = new Chart(gc, {
      type: 'line',
      data: {
        labels: dates,
        datasets: [Object.assign({
          label: lbl.glucose,
          data: typeof glucoseD !== 'undefined' ? glucoseD : []
        }, lineOpts('#8B5CF6', mkGrad(gc, 'rgba(139,92,246,0.15)', 'rgba(139,92,246,0)'), 4, 6))]
      },
      options: JSON.parse(JSON.stringify(baseOpts))
    });
    window.glucoseChart.options.scales.y.beginAtZero = false;
    window.glucoseChart.update();
  }

  // ─── EVENT HANDLERS ─────────────────────────────────────

  window.addEventListener('languageChanged', function() {
    var l = localStorage.getItem('lang') || 'vi';
    var isEn = l === 'en';
    
    if (window.bpChart) {
      window.bpChart.data.datasets[0].label = isEn ? 'Systolic' : 'Tâm thu';
      window.bpChart.data.datasets[1].label = isEn ? 'Diastolic' : 'Tâm trương';
      window.bpChart.update();
    }
    if (window.riskChart) {
      window.riskChart.data.datasets[0].label = isEn ? 'Risk (%)' : 'Nguy cơ (%)';
      window.riskChart.update();
    }
    if (window.glucoseChart) {
      window.glucoseChart.data.datasets[0].label = isEn ? 'Blood Glucose (mg/dL)' : 'Đường huyết (mg/dL)';
      window.glucoseChart.update();
    }
  });

  // Theme support
  window.addEventListener('themeChanged', function() {
    var isDark = document.documentElement.getAttribute('data-theme') === 'dark';
    var newGrid = isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.06)';
    var newText = isDark ? '#94A3B8' : '#64748B';

    [window.bpChart, window.riskChart, window.glucoseChart].forEach(function(chart) {
        if (!chart) return;
        chart.options.scales.x.ticks.color = newText;
        chart.options.scales.y.ticks.color = newText;
        chart.options.scales.y.grid.color = newGrid;
        chart.options.plugins.legend.labels.color = newText;
        chart.update();
    });
  });
});
