/*
 * Self-contained SIR epidemic model interaction for Learning Publisher.
 * No external libraries, network requests, modules, workers, or server required.
 */
(function () {
  "use strict";

  var SELECTOR = '[data-js-interaction="sir-model"], #sir-model';

  function clamp(value, min, max) {
    return Math.min(max, Math.max(min, value));
  }

  function escapeHtml(value) {
    return String(value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function simulate(settings) {
    var dt = 0.1;
    var steps = Math.ceil(settings.days / dt);
    var s = settings.population - settings.initialInfected;
    var i = settings.initialInfected;
    var r = 0;
    var points = [{ day: 0, s: s, i: i, r: r }];

    for (var step = 1; step <= steps; step += 1) {
      var newInfections = settings.beta * s * i / settings.population * dt;
      var newRecoveries = settings.gamma * i * dt;
      newInfections = Math.min(newInfections, s);
      newRecoveries = Math.min(newRecoveries, i + newInfections);
      s -= newInfections;
      i += newInfections - newRecoveries;
      r += newRecoveries;

      if (step % 10 === 0 || step === steps) {
        points.push({ day: Math.min(step * dt, settings.days), s: s, i: i, r: r });
      }
    }
    return points;
  }

  function initialise(container, index) {
    if (container.dataset.sirInitialised === "true") return;
    container.dataset.sirInitialised = "true";

    var uid = (container.id || "sir-model-" + (index + 1)).replace(/[^A-Za-z0-9_-]/g, "-");
    if (!container.id) container.id = uid;
    var titleId = uid + "-title";
    var descId = uid + "-description";
    var liveId = uid + "-live";

    container.classList.add("sir-model-interaction");
    container.setAttribute("role", "region");
    container.setAttribute("aria-labelledby", titleId);
    container.innerHTML =
      '<style>' +
      '#' + uid + '{--sir-blue:#2563eb;--sir-red:#dc2626;--sir-green:#16803c;--sir-ink:#172033;--sir-muted:#526174;--sir-line:#d7deea;--sir-bg:#f7f9fc;font:16px/1.45 system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;color:var(--sir-ink);border:1px solid var(--sir-line);border-radius:14px;padding:clamp(14px,3vw,24px);background:#fff;box-sizing:border-box;max-width:980px}' +
      '#' + uid + ' *{box-sizing:border-box}' +
      '#' + uid + ' h3{margin:0 0 4px;font-size:1.35rem}' +
      '#' + uid + ' .sir-intro{margin:0 0 18px;color:var(--sir-muted)}' +
      '#' + uid + ' .sir-layout{display:grid;grid-template-columns:minmax(230px,300px) minmax(0,1fr);gap:22px;align-items:start}' +
      '#' + uid + ' .sir-controls{background:var(--sir-bg);border-radius:10px;padding:15px}' +
      '#' + uid + ' .sir-field{display:block;margin:0 0 14px;font-weight:650}' +
      '#' + uid + ' .sir-field span{float:right;font-variant-numeric:tabular-nums;color:var(--sir-muted)}' +
      '#' + uid + ' input[type=range]{display:block;width:100%;margin:7px 0 0;accent-color:#5b5bd6}' +
      '#' + uid + ' .sir-presets{display:flex;flex-wrap:wrap;gap:7px;margin:2px 0 14px}' +
      '#' + uid + ' button{border:1px solid #aeb9ca;border-radius:7px;background:#fff;color:var(--sir-ink);padding:7px 10px;cursor:pointer;font:inherit}' +
      '#' + uid + ' button:hover{background:#edf2f8}' +
      '#' + uid + ' button:focus-visible,#' + uid + ' input:focus-visible{outline:3px solid #f3b61f;outline-offset:2px}' +
      '#' + uid + ' .sir-r0{border-top:1px solid var(--sir-line);padding-top:12px;margin-top:4px}' +
      '#' + uid + ' .sir-r0 strong{font-size:1.25rem}' +
      '#' + uid + ' .sir-chart-wrap{min-width:0}' +
      '#' + uid + ' svg{display:block;width:100%;height:auto;overflow:visible}' +
      '#' + uid + ' .sir-grid{stroke:#dfe5ee;stroke-width:1}' +
      '#' + uid + ' .sir-axis{stroke:#7b8798;stroke-width:1.2}' +
      '#' + uid + ' .sir-label{fill:#526174;font-size:12px}' +
      '#' + uid + ' .sir-line{fill:none;stroke-width:3;vector-effect:non-scaling-stroke}' +
      '#' + uid + ' .sir-legend{display:flex;flex-wrap:wrap;gap:14px;margin:8px 0 12px}' +
      '#' + uid + ' .sir-key::before{content:"";display:inline-block;width:18px;height:4px;border-radius:2px;margin-right:6px;vertical-align:middle;background:var(--key)}' +
      '#' + uid + ' .sir-cards{display:grid;grid-template-columns:repeat(3,1fr);gap:9px}' +
      '#' + uid + ' .sir-card{border:1px solid var(--sir-line);border-radius:8px;padding:9px}' +
      '#' + uid + ' .sir-card span{display:block;color:var(--sir-muted);font-size:.84rem}' +
      '#' + uid + ' .sir-card strong{font-size:1.05rem;font-variant-numeric:tabular-nums}' +
      '#' + uid + ' .sir-note{margin:12px 0 0;color:var(--sir-muted);font-size:.9rem}' +
      '@media(max-width:720px){#' + uid + ' .sir-layout{grid-template-columns:1fr}#' + uid + ' .sir-cards{grid-template-columns:1fr}}' +
      '</style>' +
      '<h3 id="' + titleId + '">Explore an SIR epidemic model</h3>' +
      '<p class="sir-intro" id="' + descId + '">Adjust the assumptions to see how people move between susceptible, infectious and recovered groups.</p>' +
      '<div class="sir-layout">' +
      '<form class="sir-controls" onsubmit="return false">' +
      '<label class="sir-field">Population <span data-value="population"></span><input name="population" type="range" min="100" max="10000" step="100" value="5000"></label>' +
      '<label class="sir-field">Initially infectious <span data-value="initialInfected"></span><input name="initialInfected" type="range" min="1" max="500" step="1" value="10"></label>' +
      '<label class="sir-field">Transmission rate, β <span data-value="beta"></span><input name="beta" type="range" min="0.05" max="1" step="0.01" value="0.30"></label>' +
      '<label class="sir-field">Recovery rate, γ <span data-value="gamma"></span><input name="gamma" type="range" min="0.03" max="0.50" step="0.01" value="0.10"></label>' +
      '<label class="sir-field">Simulation length <span data-value="days"></span><input name="days" type="range" min="30" max="365" step="5" value="160"></label>' +
      '<div><strong>Example scenarios</strong><div class="sir-presets"><button type="button" data-preset="controlled">Controlled</button><button type="button" data-preset="seasonal">Seasonal</button><button type="button" data-preset="fast">Fast spread</button><button type="button" data-preset="reset">Reset</button></div></div>' +
      '<div class="sir-r0">Basic reproduction number: <strong data-r0></strong><div data-r0-message></div></div>' +
      '</form>' +
      '<div class="sir-chart-wrap">' +
      '<svg viewBox="0 0 680 390" role="img" aria-labelledby="' + titleId + ' ' + descId + '"><g data-grid></g><g data-paths></g></svg>' +
      '<div class="sir-legend" aria-hidden="true"><span class="sir-key" style="--key:var(--sir-blue)">Susceptible</span><span class="sir-key" style="--key:var(--sir-red)">Infectious</span><span class="sir-key" style="--key:var(--sir-green)">Recovered</span></div>' +
      '<div class="sir-cards"><div class="sir-card"><span>Peak infectious</span><strong data-peak></strong></div><div class="sir-card"><span>Peak occurs</span><strong data-peak-day></strong></div><div class="sir-card"><span>Eventually infected</span><strong data-ever></strong></div></div>' +
      '<p class="sir-note">This is a simplified deterministic model. It assumes a well-mixed population and lasting immunity.</p>' +
      '<p id="' + liveId + '" class="sir-live" aria-live="polite" style="position:absolute;width:1px;height:1px;padding:0;margin:-1px;overflow:hidden;clip:rect(0,0,0,0);white-space:nowrap;border:0"></p>' +
      '</div></div>';

    var form = container.querySelector("form");
    var grid = container.querySelector("[data-grid]");
    var paths = container.querySelector("[data-paths]");
    var presets = {
      controlled: { beta: 0.08, gamma: 0.12 },
      seasonal: { beta: 0.25, gamma: 0.10 },
      fast: { beta: 0.60, gamma: 0.10 },
      reset: { population: 5000, initialInfected: 10, beta: 0.30, gamma: 0.10, days: 160 }
    };

    function settingsFromForm() {
      var population = Number(form.elements.population.value);
      return {
        population: population,
        initialInfected: clamp(Number(form.elements.initialInfected.value), 1, population - 1),
        beta: Number(form.elements.beta.value),
        gamma: Number(form.elements.gamma.value),
        days: Number(form.elements.days.value)
      };
    }

    function pathFor(data, key, x, y) {
      return data.map(function (point, pointIndex) {
        return (pointIndex ? "L" : "M") + x(point.day).toFixed(2) + "," + y(point[key]).toFixed(2);
      }).join(" ");
    }

    function draw() {
      var settings = settingsFromForm();
      form.elements.initialInfected.max = Math.min(500, settings.population - 1);
      if (Number(form.elements.initialInfected.value) !== settings.initialInfected) {
        form.elements.initialInfected.value = settings.initialInfected;
      }
      var data = simulate(settings);
      var left = 62, right = 660, top = 18, bottom = 340;
      var x = function (day) { return left + day / settings.days * (right - left); };
      var y = function (count) { return bottom - count / settings.population * (bottom - top); };
      var gridHtml = "";
      for (var fraction = 0; fraction <= 1.0001; fraction += 0.25) {
        var yy = y(settings.population * fraction);
        gridHtml += '<line class="sir-grid" x1="' + left + '" y1="' + yy + '" x2="' + right + '" y2="' + yy + '"></line>';
        gridHtml += '<text class="sir-label" x="' + (left - 9) + '" y="' + (yy + 4) + '" text-anchor="end">' + Math.round(fraction * 100) + '%</text>';
      }
      for (var tick = 0; tick <= 4; tick += 1) {
        var day = settings.days * tick / 4;
        var xx = x(day);
        gridHtml += '<line class="sir-grid" x1="' + xx + '" y1="' + top + '" x2="' + xx + '" y2="' + bottom + '"></line>';
        gridHtml += '<text class="sir-label" x="' + xx + '" y="' + (bottom + 22) + '" text-anchor="middle">' + Math.round(day) + '</text>';
      }
      gridHtml += '<line class="sir-axis" x1="' + left + '" y1="' + bottom + '" x2="' + right + '" y2="' + bottom + '"></line>';
      gridHtml += '<line class="sir-axis" x1="' + left + '" y1="' + top + '" x2="' + left + '" y2="' + bottom + '"></line>';
      gridHtml += '<text class="sir-label" x="' + ((left + right) / 2) + '" y="382" text-anchor="middle">Day</text>';
      grid.innerHTML = gridHtml;
      paths.innerHTML =
        '<path class="sir-line" stroke="var(--sir-blue)" d="' + pathFor(data, "s", x, y) + '"></path>' +
        '<path class="sir-line" stroke="var(--sir-red)" d="' + pathFor(data, "i", x, y) + '"></path>' +
        '<path class="sir-line" stroke="var(--sir-green)" d="' + pathFor(data, "r", x, y) + '"></path>';

      var peak = data.reduce(function (best, point) { return point.i > best.i ? point : best; }, data[0]);
      var last = data[data.length - 1];
      var r0 = settings.beta / settings.gamma;
      var format = new Intl.NumberFormat(undefined, { maximumFractionDigits: 0 });
      var labels = {
        population: format.format(settings.population),
        initialInfected: format.format(settings.initialInfected),
        beta: settings.beta.toFixed(2),
        gamma: settings.gamma.toFixed(2),
        days: settings.days + " days"
      };
      Object.keys(labels).forEach(function (name) {
        container.querySelector('[data-value="' + name + '"]').textContent = labels[name];
      });
      container.querySelector("[data-r0]").textContent = r0.toFixed(2);
      container.querySelector("[data-r0-message]").textContent = r0 > 1 ? "Infections can initially grow." : r0 < 1 ? "Infections should decline." : "The epidemic is at the threshold.";
      container.querySelector("[data-peak]").textContent = format.format(Math.round(peak.i)) + " (" + (peak.i / settings.population * 100).toFixed(1) + "%)";
      container.querySelector("[data-peak-day]").textContent = "Day " + Math.round(peak.day);
      container.querySelector("[data-ever]").textContent = format.format(Math.round(last.r)) + " (" + (last.r / settings.population * 100).toFixed(1) + "%)";
      container.querySelector("[aria-live]").textContent = "Model updated. R nought " + r0.toFixed(2) + ". Peak infectious " + format.format(Math.round(peak.i)) + " on day " + Math.round(peak.day) + ".";
    }

    form.addEventListener("input", draw);
    form.addEventListener("click", function (event) {
      var button = event.target.closest("[data-preset]");
      if (!button) return;
      var values = presets[button.dataset.preset];
      Object.keys(values).forEach(function (name) { form.elements[name].value = values[name]; });
      draw();
    });
    draw();
  }

  function start() {
    Array.prototype.forEach.call(document.querySelectorAll(SELECTOR), initialise);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", start, { once: true });
  } else {
    start();
  }
}());
