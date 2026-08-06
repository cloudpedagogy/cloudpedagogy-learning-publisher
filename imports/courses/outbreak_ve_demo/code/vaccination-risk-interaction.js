(function () {
  "use strict";

  const SELECTOR = '[data-js-interaction="vaccination-risk"]';

  function mount(root) {
    if (root.dataset.initialised === "true") return;
    root.dataset.initialised = "true";

    root.innerHTML = `
      <style>
        .vri { max-width: 760px; padding: 1rem; border: 1px solid #d8dee4; border-radius: .6rem; font: 16px/1.45 system-ui, sans-serif; }
        .vri__controls { display: grid; gap: .9rem; margin-bottom: 1.25rem; }
        .vri label { display: grid; grid-template-columns: minmax(14rem, 1fr) 3fr 3.5rem; gap: .75rem; align-items: center; }
        .vri input { width: 100%; }
        .vri output { font-variant-numeric: tabular-nums; text-align: right; }
        .vri__chart { display: grid; grid-template-columns: 8rem 1fr 4rem; gap: .65rem; align-items: center; }
        .vri__track { height: 2rem; background: #eef1f4; border-radius: .25rem; overflow: hidden; }
        .vri__bar { height: 100%; width: 0; transition: width 120ms ease-out; }
        .vri__bar--vaccinated { background: #2878b5; }
        .vri__bar--unvaccinated { background: #d9544d; }
        .vri__result { margin: 1rem 0 0; padding: .75rem; background: #f6f8fa; border-radius: .35rem; }
        @media (max-width: 560px) {
          .vri label { grid-template-columns: 1fr 4rem; }
          .vri label span { grid-column: 1 / -1; }
          .vri__chart { grid-template-columns: 1fr 3.5rem; }
          .vri__chart > span { grid-column: 1 / -1; }
        }
      </style>
      <section class="vri" aria-labelledby="${root.id}-title">
        <h3 id="${root.id}-title">Explore vaccination and infection risk</h3>
        <p>Move the sliders to compare cases in two equally sized groups of 500 people.</p>
        <div class="vri__controls">
          <label><span>Cases among vaccinated people</span><input data-role="vaccinated" type="range" min="0" max="50" value="5" step="1"><output data-role="vaccinated-value">5</output></label>
          <label><span>Cases among unvaccinated people</span><input data-role="unvaccinated" type="range" min="0" max="50" value="25" step="1"><output data-role="unvaccinated-value">25</output></label>
        </div>
        <div class="vri__chart" role="img" aria-label="Bar chart comparing infection risk">
          <span>Vaccinated</span><div class="vri__track"><div class="vri__bar vri__bar--vaccinated" data-role="vaccinated-bar"></div></div><strong data-role="vaccinated-risk"></strong>
          <span>Unvaccinated</span><div class="vri__track"><div class="vri__bar vri__bar--unvaccinated" data-role="unvaccinated-bar"></div></div><strong data-role="unvaccinated-risk"></strong>
        </div>
        <p class="vri__result" data-role="summary" aria-live="polite"></p>
      </section>`;

    const get = (role) => root.querySelector(`[data-role="${role}"]`);
    const vaccinated = get("vaccinated");
    const unvaccinated = get("unvaccinated");

    function update() {
      const vCases = Number(vaccinated.value);
      const uCases = Number(unvaccinated.value);
      const vRisk = vCases / 500 * 100;
      const uRisk = uCases / 500 * 100;
      const maximumRisk = 10;

      get("vaccinated-value").value = vCases;
      get("unvaccinated-value").value = uCases;
      get("vaccinated-bar").style.width = `${vRisk / maximumRisk * 100}%`;
      get("unvaccinated-bar").style.width = `${uRisk / maximumRisk * 100}%`;
      get("vaccinated-risk").textContent = `${vRisk.toFixed(1)}%`;
      get("unvaccinated-risk").textContent = `${uRisk.toFixed(1)}%`;

      if (vRisk === 0) {
        get("summary").textContent = uRisk === 0
          ? "Both groups currently have zero cases."
          : "No relative-risk ratio is calculated because the vaccinated-group risk is zero.";
      } else {
        const ratio = uRisk / vRisk;
        get("summary").textContent = `In this scenario, infection risk is ${ratio.toFixed(1)} times higher in the unvaccinated group.`;
      }
    }

    vaccinated.addEventListener("input", update);
    unvaccinated.addEventListener("input", update);
    update();
  }

  function initialise() {
    document.querySelectorAll(SELECTOR).forEach(mount);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initialise);
  } else {
    initialise();
  }
}());
