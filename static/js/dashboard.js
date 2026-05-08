document.addEventListener('DOMContentLoaded', function() {

  // ─── CHARTS ────────────────────────────────────────────
  if (typeof dates === 'undefined' || !dates.length) return;

  var lang = localStorage.getItem('lang') || 'vi';
  var isDark = document.documentElement.getAttribute('data-theme') === 'dark';
  var gridColor = isDark ? 'rgba(255,255,255,0.05)' : 'rgba(0,0,0,0.05)';
  var textColor = isDark ? '#94A3B8' : '#6B7280';
  var pointStroke = isDark ? '#0F172A' : '#FFFFFF';
  var hasTrend = dates.length > 1;

  Chart.defaults.color = textColor;
  Chart.defaults.font.family = "'Inter', sans-serif";
  Chart.defaults.font.size = 13;

  // Bilingual chart labels
  var lbl = {
    systolic: lang === 'en' ? 'Systolic' : 'Tâm thu',
    diastolic: lang === 'en' ? 'Diastolic' : 'Tâm trương',
    risk: lang === 'en' ? 'Risk (%)' : 'Nguy cơ (%)',
    glucose: lang === 'en' ? 'Blood Glucose (mg/dL)' : 'Đường huyết (mg/dL)'
  };

  var baseOpts = {
    responsive: true,
    animation: { duration: 900, easing: 'easeInOutQuart' },
    plugins: { legend: { position: 'bottom', labels: { padding: 16, usePointStyle: true, pointStyle: 'circle' } } },
    scales: {
      x: { grid: { color: gridColor }, ticks: { color: textColor } },
      y: { grid: { color: gridColor }, ticks: { color: textColor } }
    }
  };

  function mkGrad(ctx, c1, c2) {
    var g = ctx.createLinearGradient(0, 0, 0, 260);
    g.addColorStop(0, c1); g.addColorStop(1, c2); return g;
  }

  function lineOpts(color, fillColor, pointRadius, hoverRadius) {
    return {
      borderColor: color,
      backgroundColor: hasTrend ? fillColor : 'transparent',
      fill: hasTrend,
      tension: 0,
      spanGaps: true,
      showLine: hasTrend,
      borderWidth: 2.5,
      pointRadius: hasTrend ? pointRadius : Math.max(pointRadius + 3, 7),
      pointHoverRadius: hasTrend ? hoverRadius : Math.max(hoverRadius + 2, 9),
      pointBackgroundColor: color,
      pointBorderColor: pointStroke,
      pointBorderWidth: 2,
      clip: 12
    };
  }

  // BP Chart
  var bpCtx = document.getElementById('bpChart');
  if (bpCtx) {
    var bc = bpCtx.getContext('2d');
    window.bpChart = new Chart(bc, {
      type: 'line',
      data: {
        labels: dates,
        datasets: [
          Object.assign({ label: lbl.systolic, data: systolicD }, lineOpts('#EF4444', mkGrad(bc, 'rgba(239,68,68,0.2)', 'rgba(239,68,68,0)'), 4, 7)),
          Object.assign({ label: lbl.diastolic, data: diastolicD }, lineOpts('#10B981', mkGrad(bc, 'rgba(16,185,129,0.2)', 'rgba(16,185,129,0)'), 4, 7))
        ]
      },
      options: Object.assign({}, baseOpts, { scales: { x: baseOpts.scales.x, y: Object.assign({}, baseOpts.scales.y, { beginAtZero: false }) } })
    });
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
          data: strokeScores,
          segment: { borderColor: function(c) { return c.p0.parsed.y >= 75 ? '#EF4444' : undefined; } }
        }, lineOpts('#F59E0B', mkGrad(rc, 'rgba(245,158,11,0.2)', 'rgba(245,158,11,0)'), 5, 8))]
      },
      options: Object.assign({}, baseOpts, { scales: { x: baseOpts.scales.x, y: Object.assign({}, baseOpts.scales.y, { beginAtZero: true, max: 100 }) } })
    });
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
          data: glucoseD
        }, lineOpts('#A78BFA', mkGrad(gc, 'rgba(167,139,250,0.2)', 'rgba(167,139,250,0)'), 4, 7))]
      },
      options: Object.assign({}, baseOpts, { scales: { x: baseOpts.scales.x, y: Object.assign({}, baseOpts.scales.y, { beginAtZero: false }) } })
    });
  }

  // Update chart labels on language switch
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
});
