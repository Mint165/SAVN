// ─── HeartBits Digital Twin: Future Risk Simulation Engine ──────
// Simulates future stroke risk based on current health data.
// Renders an animated bar chart with staggered transitions.

var HBDigitalTwin = (function () {
  'use strict';

  // ─── Internal State ──────────────────────────────────────
  var _config = null;
  var _projections = null;

  // Time horizons for projection
  var HORIZONS = [
    { key: '3m',  months: 3,  years: 0.25 },
    { key: '6m',  months: 6,  years: 0.5  },
    { key: '1y',  months: 12, years: 1    },
    { key: '2y',  months: 24, years: 2    },
    { key: '5y',  months: 60, years: 5    }
  ];

  // i18n label keys for each horizon
  var HORIZON_I18N = {
    '3m': 'time_3m',
    '6m': 'time_6m',
    '1y': 'time_1y',
    '2y': 'time_2y',
    '5y': 'time_5y'
  };

  // ─── Risk Factor Calculation ─────────────────────────────
  // Returns annual risk change rate (% per year) based on health data.
  function _calcAnnualDrift(cfg) {
    var drift = 0;

    // 1. Age drift: +1.5%/year after age 55
    if (cfg.age > 55) {
      drift += 1.5;
    }

    // 2. Blood pressure factor: +3%/year if hypertensive
    if (cfg.systolic >= 140 || cfg.diastolic >= 90) {
      drift += 3;
    }

    // 3. Glucose factor: +2%/year if elevated
    if (cfg.glucose > 140) {
      drift += 2;
    }

    // 4. BMI factor: +1%/year if obese
    if (cfg.bmi > 30) {
      drift += 1;
    }

    // 5. Smoking factor
    var smoking = (cfg.smokingStatus || '').toLowerCase();
    if (smoking === 'smokes' || smoking === 'currently smoking') {
      drift += 2.5;
    } else if (smoking === 'formerly smoked') {
      drift += 0.5;
    }

    // 6. Heart disease: +2%/year
    if (cfg.heartDisease === 1) {
      drift += 2;
    }

    // 7. Exercise benefit: -0.5% per streak day, capped at -5%
    var exerciseBenefit = Math.min(cfg.exerciseStreak * 0.5, 5);
    drift -= exerciseBenefit;

    return drift;
  }

  // Clamp value between min and max
  function _clamp(val, min, max) {
    return Math.max(min, Math.min(max, val));
  }

  // ─── init(config) ────────────────────────────────────────
  function init(config) {
    _config = {
      currentRisk:    config.currentRisk    || 0,
      age:            config.age            || 50,
      systolic:       config.systolic       || 120,
      diastolic:      config.diastolic      || 80,
      glucose:        config.glucose        || 100,
      bmi:            config.bmi            || 22,
      smokingStatus:  config.smokingStatus  || 'never smoked',
      heartDisease:   config.heartDisease   || 0,
      exerciseStreak: config.exerciseStreak || 0
    };

    // Pre-compute projections
    _projections = _computeProjections();
  }

  // ─── getProjections() ────────────────────────────────────
  function _computeProjections() {
    if (!_config) return [];

    var annualDrift = _calcAnnualDrift(_config);
    var results = [];

    for (var i = 0; i < HORIZONS.length; i++) {
      var h = HORIZONS[i];
      var futureRisk = _config.currentRisk + (annualDrift * h.years);
      futureRisk = Math.round(_clamp(futureRisk, 0, 100));

      var delta = futureRisk - _config.currentRisk;
      var trend = delta > 0 ? 'up' : (delta < 0 ? 'down' : 'stable');

      results.push({
        label: h.key,
        months: h.months,
        risk: futureRisk,
        delta: delta,
        trend: trend
      });
    }

    return results;
  }

  function getProjections() {
    return _projections || [];
  }

  // ─── Color Helpers ───────────────────────────────────────
  // Returns the appropriate CSS color based on risk level
  function _riskColor(risk) {
    if (risk < 30) return 'var(--success)';
    if (risk < 60) return 'var(--warning)';
    return 'var(--danger)';
  }

  // Returns a translucent background for risk level
  function _riskBg(risk) {
    if (risk < 30) return 'rgba(16,185,129,0.15)';
    if (risk < 60) return 'rgba(245,158,11,0.15)';
    return 'rgba(239,68,68,0.15)';
  }

  // ─── i18n Helper ─────────────────────────────────────────
  function _t(key) {
    var lang = localStorage.getItem('lang') || 'vi';
    if (typeof I18N !== 'undefined' && I18N[lang] && I18N[lang][key]) {
      return I18N[lang][key];
    }
    return key;
  }

  // ─── renderCard(containerId) ─────────────────────────────
  function renderCard(containerId) {
    var container = document.getElementById(containerId);
    if (!container) return;

    var projections = getProjections();
    if (!projections.length) return;

    // Build the card HTML
    container.innerHTML = _buildCardHTML(projections);

    // Animate bars with staggered delay
    requestAnimationFrame(function () {
      setTimeout(function () {
        _animateBars(container, projections);
      }, 50);
    });

    // Listen for language changes to update labels
    window.addEventListener('languageChanged', function () {
      _updateLabels(container, projections);
    });
  }

  // ─── Build Card HTML ─────────────────────────────────────
  function _buildCardHTML(projections) {
    var maxRisk = 0;
    for (var i = 0; i < projections.length; i++) {
      if (projections[i].risk > maxRisk) maxRisk = projections[i].risk;
    }

    var html = '';

    // Header
    html += '<div class="dt-header">';
    html += '  <h4 class="dt-title"><i class="fa-solid fa-flask-vial"></i> ';
    html += '  <span data-i18n="digital_twin_title">' + _t('digital_twin_title') + '</span></h4>';
    html += '  <p class="dt-desc" data-i18n="dt_desc">' + _t('dt_desc') + '</p>';
    html += '</div>';

    // Chart area
    html += '<div class="dt-chart">';

    // Baseline reference line
    var baselineBottom = _config.currentRisk + '%';
    html += '<div class="dt-baseline" style="bottom:' + baselineBottom + '">';
    html += '  <span class="dt-baseline-label">' + _config.currentRisk + '%</span>';
    html += '</div>';

    // Bars
    html += '<div class="dt-bars">';
    for (var j = 0; j < projections.length; j++) {
      var p = projections[j];
      var deltaStr = (p.delta >= 0 ? '+' : '') + p.delta;
      var deltaClass = p.delta > 0 ? 'dt-delta-up' : (p.delta < 0 ? 'dt-delta-down' : 'dt-delta-stable');
      var i18nKey = HORIZON_I18N[p.label];

      html += '<div class="dt-bar-group">';
      html += '  <div class="dt-bar-label" data-i18n="' + i18nKey + '">' + _t(i18nKey) + '</div>';
      html += '  <div class="dt-bar-wrapper">';
      html += '    <div class="dt-bar" data-index="' + j + '" style="height:0%;background:' + _riskColor(p.risk) + '">';
      html += '      <span class="dt-bar-value">' + p.risk + '%</span>';
      html += '    </div>';
      html += '  </div>';
      html += '  <div class="dt-delta ' + deltaClass + '">' + deltaStr + '</div>';
      html += '</div>';
    }
    html += '</div>'; // .dt-bars
    html += '</div>'; // .dt-chart

    // Advice text
    var adviceKey, adviceClass;
    if (maxRisk < 30) {
      adviceKey = 'dt_advice_good';
      adviceClass = 'dt-advice-good';
    } else if (maxRisk < 60) {
      adviceKey = 'dt_advice_warn';
      adviceClass = 'dt-advice-warn';
    } else {
      adviceKey = 'dt_advice_danger';
      adviceClass = 'dt-advice-danger';
    }

    html += '<div class="dt-advice ' + adviceClass + '">';
    html += '  <i class="fa-solid ' + (maxRisk < 30 ? 'fa-circle-check' : (maxRisk < 60 ? 'fa-triangle-exclamation' : 'fa-circle-exclamation')) + '"></i> ';
    html += '  <span data-i18n="' + adviceKey + '">' + _t(adviceKey) + '</span>';
    html += '</div>';

    return html;
  }

  // ─── Animate Bars ────────────────────────────────────────
  function _animateBars(container, projections) {
    var bars = container.querySelectorAll('.dt-bar');
    for (var i = 0; i < bars.length; i++) {
      (function (bar, idx) {
        setTimeout(function () {
          bar.style.height = projections[idx].risk + '%';
        }, idx * 120); // 120ms stagger between bars
      })(bars[i], i);
    }
  }

  // ─── Update Labels on Language Change ────────────────────
  function _updateLabels(container, projections) {
    if (!container) return;

    // Update data-i18n elements inside the card
    var els = container.querySelectorAll('[data-i18n]');
    var lang = localStorage.getItem('lang') || 'vi';
    var dict = (typeof I18N !== 'undefined' && I18N[lang]) ? I18N[lang] : {};

    for (var i = 0; i < els.length; i++) {
      var key = els[i].getAttribute('data-i18n');
      if (dict[key]) {
        els[i].textContent = dict[key];
      }
    }
  }

  // ─── Inject Scoped Styles ────────────────────────────────
  // Styles are injected once to avoid external CSS dependency
  (function _injectStyles() {
    if (document.getElementById('hb-dt-styles')) return;

    var css = '';

    // Container
    css += '.dt-header { margin-bottom: 1rem; }';
    css += '.dt-title { font-size: 1rem; font-weight: 700; margin: 0 0 .35rem; display: flex; align-items: center; gap: .5rem; color: var(--text); }';
    css += '.dt-title i { color: var(--primary); }';
    css += '.dt-desc { font-size: .82rem; color: var(--text-muted); margin: 0; line-height: 1.5; }';

    // Chart area
    css += '.dt-chart { position: relative; height: 200px; margin: 1.25rem 0; padding: 0 .5rem; }';

    // Baseline
    css += '.dt-baseline { position: absolute; left: 0; right: 0; border-top: 2px dashed var(--text-muted); opacity: .4; z-index: 1; pointer-events: none; }';
    css += '.dt-baseline-label { position: absolute; right: 0; top: -18px; font-size: .7rem; font-weight: 700; color: var(--text-muted); }';

    // Bars container
    css += '.dt-bars { display: flex; align-items: flex-end; justify-content: space-around; height: 100%; gap: .5rem; position: relative; z-index: 2; }';

    // Bar group
    css += '.dt-bar-group { display: flex; flex-direction: column; align-items: center; flex: 1; height: 100%; gap: .35rem; }';
    css += '.dt-bar-label { font-size: .72rem; font-weight: 700; color: var(--text-muted); text-transform: uppercase; letter-spacing: .3px; white-space: nowrap; order: -1; }';
    css += '.dt-bar-wrapper { flex: 1; width: 100%; max-width: 48px; display: flex; align-items: flex-end; }';

    // Individual bar
    css += '.dt-bar { width: 100%; border-radius: .5rem .5rem .25rem .25rem; position: relative; min-height: 4px; transition: height .8s cubic-bezier(.34,1.56,.64,1); }';
    css += '.dt-bar-value { position: absolute; top: -20px; left: 50%; transform: translateX(-50%); font-size: .75rem; font-weight: 800; color: var(--text); white-space: nowrap; }';

    // Delta indicator
    css += '.dt-delta { font-size: .72rem; font-weight: 700; border-radius: .35rem; padding: .15rem .4rem; }';
    css += '.dt-delta-up { color: var(--danger); background: rgba(239,68,68,0.1); }';
    css += '.dt-delta-down { color: var(--success); background: rgba(16,185,129,0.1); }';
    css += '.dt-delta-stable { color: var(--text-muted); background: var(--border); }';

    // Advice
    css += '.dt-advice { display: flex; align-items: flex-start; gap: .6rem; padding: .85rem 1rem; border-radius: .75rem; font-size: .85rem; font-weight: 600; line-height: 1.5; margin-top: .25rem; }';
    css += '.dt-advice-good { background: rgba(16,185,129,0.08); border: 1px solid rgba(16,185,129,0.2); color: var(--success); }';
    css += '.dt-advice-warn { background: rgba(245,158,11,0.08); border: 1px solid rgba(245,158,11,0.2); color: var(--warning); }';
    css += '.dt-advice-danger { background: rgba(239,68,68,0.08); border: 1px solid rgba(239,68,68,0.2); color: var(--danger); }';

    // Dark theme overrides
    css += '[data-theme=dark] .dt-advice-good { background: rgba(16,185,129,0.12); border-color: rgba(16,185,129,0.25); }';
    css += '[data-theme=dark] .dt-advice-warn { background: rgba(245,158,11,0.12); border-color: rgba(245,158,11,0.25); }';
    css += '[data-theme=dark] .dt-advice-danger { background: rgba(239,68,68,0.12); border-color: rgba(239,68,68,0.25); }';
    css += '[data-theme=dark] .dt-bar-value { color: var(--text); }';

    // Responsive
    css += '@media(max-width:480px) {';
    css += '  .dt-chart { height: 160px; }';
    css += '  .dt-bar-label { font-size: .65rem; }';
    css += '  .dt-bar-value { font-size: .68rem; }';
    css += '  .dt-bar-wrapper { max-width: 36px; }';
    css += '}';

    var style = document.createElement('style');
    style.id = 'hb-dt-styles';
    style.textContent = css;
    document.head.appendChild(style);
  })();

  // ─── Public API ──────────────────────────────────────────
  return {
    init: init,
    getProjections: getProjections,
    renderCard: renderCard
  };
})();
