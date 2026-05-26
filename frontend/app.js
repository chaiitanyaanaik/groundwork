function track(event, properties) {
  try {
    fetch("/api/analytics/event", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ event, properties: properties || {} }),
      keepalive: true,
    }).catch(() => {});
  } catch (_) {}
}

const state = {
  step: 1,
  aspiration: null,
  questions: [],
  roleOptions: [],
  wizardSteps: [],
  wizardIndex: 0,
  wizardAnswers: {},
  lastRequest: null,
  lastResult: null,
};

const feedbackState = {
  rating: null,
  submitted: false,
  submitting: false,
};

const ASPIRATION_ICONS = {
  velocity:
    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" aria-hidden="true"><path d="M4 16l4-6 4 3 4-7 4 10"/><path d="M4 20h16"/></svg>',
  ownership:
    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" aria-hidden="true"><circle cx="9" cy="8" r="3"/><circle cx="16" cy="9" r="2.5"/><path d="M4 20c0-3 2.5-5 5-5s5 2 5 5M13 20c0-2 1.5-3.5 3.5-3.5S20 18 20 20"/></svg>',
  ai: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" aria-hidden="true"><path d="M12 3v3M8 6l2 2M16 6l-2 2"/><rect x="6" y="10" width="12" height="10" rx="2"/><path d="M9 14h6M10 17h4"/></svg>',
  experiment:
    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" aria-hidden="true"><path d="M10 3h4v3l5 9H5l5-9V3z"/><path d="M9 18h6"/></svg>',
  coordination:
    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" aria-hidden="true"><circle cx="12" cy="12" r="3"/><path d="M12 2v3M12 19v3M2 12h3M19 12h3M5 5l2 2M17 17l2 2M19 5l-2 2M7 17l-2 2"/></svg>',
  cohesion:
    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" aria-hidden="true"><rect x="4" y="5" width="16" height="4" rx="1"/><rect x="6" y="10" width="12" height="4" rx="1"/><rect x="8" y="15" width="8" height="4" rx="1"/></svg>',
  execution:
    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" aria-hidden="true"><circle cx="12" cy="13" r="8"/><path d="M12 9v5l3 2"/><path d="M9 3h6"/></svg>',
  workflow:
    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" aria-hidden="true"><path d="M5 7h6v6H5zM13 11h6v6h-6z"/><path d="M11 10H8M16 14h-3"/></svg>',
  plg: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" aria-hidden="true"><path d="M5 18l4-8 4 5 6-11"/></svg>',
  performance:
    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" aria-hidden="true"><path d="M12 3l2.4 5 5.6.8-4 4 1 5.6L12 16l-5 2.4 1-5.6-4-4 5.6-.8L12 3z"/></svg>',
  alignment:
    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" aria-hidden="true"><circle cx="6" cy="12" r="2"/><circle cx="18" cy="6" r="2"/><circle cx="18" cy="18" r="2"/><path d="M8 12h5M13 11l3-4M13 13l3 4"/></svg>',
  builders:
    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" aria-hidden="true"><path d="M14 4l6 6-9 9H5v-6l9-9z"/><path d="M13 5l2 2"/></svg>',
  roadmap:
    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" aria-hidden="true"><path d="M4 6h16M4 12h10M4 18h14"/><circle cx="18" cy="12" r="2"/></svg>',
  trust:
    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" aria-hidden="true"><path d="M12 3l7 4v6c0 4-3 7-7 8-4-1-7-4-7-8V7l7-4z"/><path d="M9 12l2 2 4-4"/></svg>',
  innovation:
    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" aria-hidden="true"><path d="M12 3a6 6 0 016 6c0 2.5-1.5 4-3 5l-1 5H10l-1-5c-1.5-1-3-2.5-3-5a6 6 0 016-6z"/><path d="M10 21h4"/></svg>',
  default:
    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" aria-hidden="true"><circle cx="12" cy="12" r="8"/><path d="M12 8v4l3 2"/></svg>',
};

function aspirationIcon(theme) {
  return ASPIRATION_ICONS[theme] || ASPIRATION_ICONS.default;
}

const ORG_FIELDS = [
  {
    id: "stage",
    label: "Stage",
    options: [
      { id: "", label: "Select stage" },
      { id: "startup", label: "Startup" },
      { id: "scaleup", label: "Scaleup" },
      { id: "enterprise", label: "Enterprise" },
    ],
  },
  {
    id: "size",
    label: "Size",
    options: [
      { id: "", label: "Select size" },
      { id: "small", label: "Small" },
      { id: "medium", label: "Medium" },
      { id: "large", label: "Large" },
    ],
  },
  {
    id: "model",
    label: "Model",
    options: [
      { id: "", label: "Select model" },
      { id: "b2b", label: "B2B" },
      { id: "b2c", label: "B2C" },
      { id: "platform", label: "Platform" },
    ],
  },
];

const $ = (sel) => document.querySelector(sel);
const REVEAL_STAGGER_MS = 380;

function showStep(n) {
  state.step = n;
  document.querySelectorAll(".step").forEach((el) => {
    el.hidden = true;
  });
  $(`#step-${n}`).hidden = false;

  document.querySelectorAll(".site-nav--marketing").forEach((el) => {
    el.hidden = n !== 1;
  });

  const backBtn = $("#wizard-back");
  if (backBtn && n !== 2) backBtn.hidden = true;

  if (n === 1) {
    if (state.aspiration) {
      $("#explore-view").hidden = false;
      document.body.classList.add("is-exploring");
      document.body.dataset.phase = "explore";
      document.body.dataset.theme = state.aspiration.theme || "default";
    } else {
      showLanding();
      document.body.dataset.phase = "landing";
    }
  } else if (n === 2) {
    document.body.classList.remove("is-exploring");
    document.body.dataset.phase = "calibrate";
    if (state.wizardSteps.length) {
      state.wizardIndex = 0;
      renderWizardStep();
    }
  } else {
    document.body.classList.remove("is-exploring");
    document.body.dataset.phase = "results";
    showResultsLoading();
  }

  window.scrollTo({ top: 0, behavior: n === 1 ? "smooth" : "auto" });
}

async function api(path, options = {}) {
  const { signal, returnHeaders, ...rest } = options;
  const res = await fetch(path, {
    headers: { "Content-Type": "application/json", ...rest.headers },
    signal,
    ...rest,
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const err = await res.json();
      detail = err.detail || JSON.stringify(err);
    } catch {
      /* ignore */
    }
    throw new Error(detail);
  }
  const data = await res.json();
  if (returnHeaders) {
    return { data, headers: res.headers };
  }
  return data;
}

function escapeHtml(str) {
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function showLanding() {
  $("#explore-view").hidden = true;
  document.body.classList.remove("is-exploring");
  document.body.removeAttribute("data-theme");
  document.querySelectorAll(".transform-card").forEach((c) => {
    c.classList.remove("is-selected", "is-dimmed");
  });
}

function showExplore(a) {
  $("#explore-view").hidden = false;
  document.body.classList.add("is-exploring");
  document.body.dataset.theme = a.theme || "default";

  $("#explore-chosen-label").textContent = a.label;
  $("#explore-chosen-subtitle").textContent = a.emotional_subtitle;
  $("#tension-truth").textContent = a.operational_truth;

  const layersEl = $("#reflection-layers");
  layersEl.innerHTML = "";
  const layers = a.reflection_layers || [];

  layers.forEach((layer) => {
    const card = document.createElement("article");
    card.className = "reflection-card is-visible";
    card.innerHTML = `
      <h3 class="reflection-card__title">${escapeHtml(layer.title)}</h3>
      <p class="reflection-card__body">${escapeHtml(layer.body)}</p>
    `;
    layersEl.appendChild(card);
  });

  $(".explore-actions").classList.add("is-visible");

  window.scrollTo({ top: 0, behavior: "smooth" });
}

async function loadTransformations() {
  const grid = $("#transform-grid");
  try {
    const data = await api("/api/aspirations");
    grid.innerHTML = "";
    for (const a of data.aspirations) {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "transform-card";
      btn.dataset.id = a.id;
      btn.dataset.theme = a.theme || "default";
      btn.innerHTML = `
        <span class="transform-card__icon">${aspirationIcon(a.theme)}</span>
        <span class="transform-card__label">${escapeHtml(a.label)}</span>
        <span class="transform-card__subtitle">“${escapeHtml(a.emotional_subtitle)}”</span>
      `;
      btn.addEventListener("click", () => selectTransformation(a, btn));
      grid.appendChild(btn);
    }
  } catch (e) {
    grid.innerHTML = `<p class="loading-text">Failed to load: ${escapeHtml(e.message)}</p>`;
  }
}

function selectTransformation(a, clickedBtn) {
  track("aspiration_selected", { aspiration_id: a.id, label: a.label, theme: a.theme });
  state.aspiration = a;
  $("#selected-aspiration-label").textContent = a.label.toLowerCase();

  document.querySelectorAll(".transform-card").forEach((c) => {
    c.classList.toggle("is-selected", c === clickedBtn);
    c.classList.toggle("is-dimmed", c !== clickedBtn);
  });

  document.body.dataset.phase = "explore";
  showExplore(a);
  loadCalibrationForAspiration(a.id);
}

async function continueToCalibration() {
  if (!state.aspiration) return;
  track("calibration_started", { aspiration_id: state.aspiration.id });
  showStep(2);
}

function buildWizardSteps() {
  const roleOptions = [
    ...(state.roleOptions || []).map((o) => ({ id: o.id, label: o.label })),
    { id: "", label: "Prefer not to say" },
  ];

  return [
    {
      layer: "user",
      type: "radio",
      id: "user_role",
      optional: true,
      prompt: "Which best describes your role?",
      options: roleOptions,
    },
    {
      layer: "org",
      type: "org_group",
      optional: true,
      prompt: "A quick picture of your organization",
      framing: "All optional — helps place your answers in context.",
      fields: ORG_FIELDS,
    },
    ...(state.questions || []).map((q, i) => ({
      layer: "operations",
      type: "radio",
      id: q.id,
      optional: false,
      prompt: q.prompt,
      framing: q.framing || "",
      options: q.options.map((o) => ({
        id: o.id,
        label: o.label,
        description: o.description || "",
      })),
      opsIndex: i,
      opsTotal: state.questions.length,
    })),
  ];
}

function captureCurrentWizardStep() {
  const step = state.wizardSteps[state.wizardIndex];
  if (!step) return;
  const form = $("#calibration-form");
  if (step.type === "org_group") {
    for (const field of step.fields) {
      const sel = form.querySelector(`select[name="${field.id}"]`);
      state.wizardAnswers[field.id] = sel ? sel.value : "";
    }
    return;
  }
  if (step.type === "radio") {
    const checked = form.querySelector(`input[name="${step.id}"]:checked`);
    state.wizardAnswers[step.id] = checked ? checked.value : "";
  }
}

function updateWizardProgressBar() {
  const total = state.wizardSteps.length || 1;
  const pct =
    total > 1
      ? Math.round((state.wizardIndex / (total - 1)) * 100)
      : 0;
  const fill = $("#calibrate-progress-fill");
  const bar = $("#calibrate-progress");
  const label = $("#calibrate-progress-label");
  if (fill) fill.style.width = `${pct}%`;
  if (bar) bar.setAttribute("aria-valuenow", String(pct));
  if (label) label.textContent = `Progress — ${pct}%`;
}

function validateWizardStep(index) {
  const step = state.wizardSteps[index];
  if (!step || step.optional || step.type === "org_group") return true;
  if (index === state.wizardIndex) {
    const form = $("#calibration-form");
    const selected = form.querySelector(`input[name="${step.id}"]:checked`);
    return !!selected;
  }
  return !!state.wizardAnswers[step.id];
}

function renderOrgGroupHtml(step) {
  return step.fields
    .map((field) => {
      const opts = field.options
        .map(
          (o) =>
            `<option value="${escapeHtml(o.id)}">${escapeHtml(o.label)}</option>`
        )
        .join("");
      return `
        <label class="wizard-org-field">
          <span class="wizard-org-field__label">${escapeHtml(field.label)}</span>
          <select class="wizard-select" name="${escapeHtml(field.id)}">
            ${opts}
          </select>
        </label>`;
    })
    .join("");
}

function renderWizardStep() {
  const panel = $("#wizard-panel");
  const step = state.wizardSteps[state.wizardIndex];
  if (!step) {
    panel.innerHTML = `<p class="loading-text">No questions loaded.</p>`;
    return;
  }

  const isLastStep = state.wizardIndex === state.wizardSteps.length - 1;

  let inputHtml = "";
  if (step.type === "org_group") {
    inputHtml = `<div class="wizard-org-fields">${renderOrgGroupHtml(step)}</div>`;
  } else {
    const useGrid = step.options.length > 1;
    const radios = step.options
      .map((o) => {
        const desc = o.description
          ? `<span class="wizard-option__desc">${escapeHtml(o.description)}</span>`
          : "";
        return `
        <label class="wizard-option">
          <input type="radio" name="${escapeHtml(step.id)}" value="${escapeHtml(o.id)}" />
          <span class="wizard-option__body">
            <span class="wizard-option__title">${escapeHtml(o.label)}</span>
            ${desc}
          </span>
        </label>`;
      })
      .join("");
    const gridClass = useGrid ? " wizard-options--grid" : " wizard-options--stack";
    inputHtml = `<div class="wizard-options${gridClass}" role="radiogroup" aria-label="${escapeHtml(step.prompt)}">${radios}</div>`;
  }

  const stepClass =
    step.type === "org_group" ? " wizard-step wizard-step--org" : " wizard-step";
  panel.innerHTML = `
    <fieldset class="${stepClass.trim()}">
      <p class="wizard-step__prompt">${escapeHtml(step.prompt)}</p>
      ${
        step.framing
          ? `<p class="wizard-step__framing">${escapeHtml(step.framing)}</p>`
          : ""
      }
      ${inputHtml}
      <p class="wizard-step__hint" id="wizard-hint" hidden></p>
    </fieldset>
  `;

  applyWizardAnswersToStep(step);
  updateWizardProgressBar();

  const backBtn = $("#wizard-back");
  backBtn.hidden = state.wizardIndex === 0;
  if (!backBtn.hidden) backBtn.textContent = "← Back";
  const nextBtn = $("#wizard-next");
  const submitBtn = $("#wizard-submit");
  nextBtn.hidden = isLastStep;
  submitBtn.hidden = !isLastStep;
  nextBtn.setAttribute("aria-hidden", isLastStep ? "true" : "false");
  submitBtn.setAttribute("aria-hidden", isLastStep ? "false" : "true");
  $("#wizard-hint").hidden = true;
}

function applyWizardAnswersToStep(step) {
  const form = $("#calibration-form");
  if (step.type === "org_group") {
    for (const field of step.fields) {
      const val = state.wizardAnswers[field.id];
      if (val === undefined || val === "") continue;
      const sel = form.querySelector(`select[name="${field.id}"]`);
      if (sel) sel.value = val;
    }
    return;
  }
  const val = state.wizardAnswers[step.id];
  if (val === undefined || val === "") return;
  const radio = form.querySelector(`input[name="${step.id}"][value="${val}"]`);
  if (radio) radio.checked = true;
}

function wizardNext() {
  captureCurrentWizardStep();
  if (!validateWizardStep(state.wizardIndex)) {
    const hint = $("#wizard-hint");
    hint.textContent = "Choose an option to continue.";
    hint.hidden = false;
    return;
  }
  if (state.wizardIndex < state.wizardSteps.length - 1) {
    state.wizardIndex += 1;
    renderWizardStep();
    window.scrollTo({ top: 0, behavior: "smooth" });
  }
}

function wizardBack() {
  if (state.wizardIndex === 0) {
    showStep(1);
    return;
  }
  captureCurrentWizardStep();
  state.wizardIndex -= 1;
  renderWizardStep();
  window.scrollTo({ top: 0, behavior: "smooth" });
}

async function loadCalibrationForAspiration(aspirationId) {
  const panel = $("#wizard-panel");
  panel.innerHTML = `<p class="loading-text">Loading…</p>`;

  try {
    const data = await api(
      `/api/calibration/questions?aspiration_id=${encodeURIComponent(aspirationId)}`
    );
    state.questions = data.questions;
    state.roleOptions = data.role_options || [];
    state.wizardSteps = buildWizardSteps();
    state.wizardAnswers = {};
    state.wizardIndex = 0;
    renderWizardStep();
  } catch (e) {
    panel.innerHTML = `<p class="loading-text">Failed to load: ${escapeHtml(e.message)}</p>`;
  }
}

function fillList(el, items) {
  el.innerHTML = "";
  if (!items?.length) {
    el.innerHTML = "<li><em>None identified</em></li>";
    return;
  }
  for (const item of items) {
    const li = document.createElement("li");
    li.textContent = item;
    el.appendChild(li);
  }
}

function fillIconList(el, items, iconName) {
  el.innerHTML = "";
  if (!items?.length) {
    el.innerHTML = '<li class="report-empty"><em>None identified</em></li>';
    return;
  }
  for (const item of items) {
    const li = document.createElement("li");
    li.innerHTML = `<span class="material-symbols-outlined" aria-hidden="true">${iconName}</span><span>${escapeHtml(item)}</span>`;
    el.appendChild(li);
  }
}

const PHASE_ICONS = {
  start: "rocket_launch",
  avoid: "block",
  later: "update",
};

function fillPhaseList(el, items, phase) {
  el.innerHTML = "";
  const icon = PHASE_ICONS[phase] || "check_circle";
  if (!items?.length) {
    el.innerHTML = '<li class="report-empty"><em>None identified</em></li>';
    return;
  }
  for (const item of items) {
    const li = document.createElement("li");
    li.innerHTML = `<span class="material-symbols-outlined" aria-hidden="true">${icon}</span><span>${escapeHtml(item)}</span>`;
    el.appendChild(li);
  }
}

function formatConfidenceLabel(level) {
  const labels = {
    high: "High confidence transformation",
    partial: "Partial confidence transformation",
    low: "Low confidence transformation",
    none: "Limited corpus match",
  };
  return labels[level] || "Transformation insight";
}

function renderMeasureContent(el, items) {
  if (!items?.length) {
    el.innerHTML = "<p class='report-empty'><em>None identified</em></p>";
    return;
  }
  if (items.length === 1) {
    el.innerHTML = `<p>${escapeHtml(items[0])}</p>`;
    return;
  }
  el.innerHTML = `<ul>${items.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>`;
}

function renderCourseCorrect(el, triggers, adaptation) {
  const parts = [];
  if (triggers?.length) {
    parts.push(`<ul>${triggers.map((t) => `<li>${escapeHtml(t)}</li>`).join("")}</ul>`);
  }
  if (adaptation) {
    parts.push(`<p><strong>Typical adaptation:</strong> ${escapeHtml(adaptation)}</p>`);
  }
  el.innerHTML = parts.join("") || "<p class='report-empty'><em>None identified</em></p>";
}

function buildBottleneckNarrative(bottleneck) {
  const parts = [];
  if (bottleneck?.bottleneck) {
    parts.push(`<p>${escapeHtml(bottleneck.bottleneck)}</p>`);
  }
  if (bottleneck?.what_teams_usually_do_next) {
    parts.push(`<p>${escapeHtml(bottleneck.what_teams_usually_do_next)}</p>`);
  }
  if (bottleneck?.unintended_effect) {
    parts.push(`<p><em>${escapeHtml(bottleneck.unintended_effect)}</em></p>`);
  }
  return parts.join("") || "<p class='report-empty'><em>None identified</em></p>";
}

function renderSourceCard(s) {
  const card = document.createElement("article");
  card.className = "report-source-card";
  const title = s.pattern_name || s.source_guest || "Operational pattern";
  card.innerHTML = `
    <h4 class="report-source-card__title">${escapeHtml(title)}</h4>
    <p class="report-source-card__meta">${escapeHtml(s.source_guest || "")}${
      s.source_episode ? ` · ${escapeHtml(s.source_episode)}` : ""
    }</p>
    ${
      s.quote
        ? `<p class="report-source-card__quote">${escapeHtml(s.quote)}</p>`
        : "<p class='report-source-card__quote report-empty'><em>No quote available</em></p>"
    }
  `;
  return card;
}

function buildOrgProfile(form) {
  captureCurrentWizardStep();
  const a = state.wizardAnswers;
  const calibration = {};
  for (const q of state.questions) {
    calibration[q.id] = a[q.id] || "";
  }

  const profile = { calibration };
  if (a.stage) profile.stage = a.stage;
  if (a.size) profile.size = a.size;
  if (a.model) profile.model = a.model;
  if (a.user_role) profile.user_role = a.user_role;
  return profile;
}

function normalizeResult(data) {
  data.what_youre_trying_to_change = data.what_youre_trying_to_change || {
    goal: data.headline || "",
    operational_meaning: data.nuance?.tradeoff || "",
  };
  data.environment_readiness = data.environment_readiness || {
    supporting_conditions: data.adaptation?.keep || [],
    resisting_conditions: data.diagnosis?.organizational_distortions || [],
    readiness_summary: data.nuance?.hidden_illusion || "",
  };
  data.first_bottleneck = data.first_bottleneck || {
    bottleneck:
      data.pressure_simulation?.where_this_collapses?.[0] ||
      data.diagnosis?.collapse_pattern ||
      "",
    what_teams_usually_do_next: "",
    unintended_effect: "",
  };
  data.likely_resistance = data.likely_resistance || {
    patterns: data.pressure_simulation?.under_stress_behaviors || [],
  };
  data.how_to_drive_change = data.how_to_drive_change || {
    start_with: data.adaptation?.steps || [],
    avoid: [],
    introduce_later: [...(data.adaptation?.modify || []), ...(data.adaptation?.add || [])],
  };
  data.what_to_measure = data.what_to_measure || {
    positive_signals: [],
    warning_signs: data.pressure_simulation?.early_warning_signs || [],
  };
  data.when_to_course_correct = data.when_to_course_correct || {
    course_correct_if: data.pressure_simulation?.where_this_collapses || [],
    typical_adaptation: "",
  };
  data.where_this_works_best = data.where_this_works_best || {
    conditions: data.nuance?.works_well_when ? [data.nuance.works_well_when] : [],
  };
  data.core_organizational_insight =
    data.core_organizational_insight || data.closing_insight || "";
  data.sources = data.sources || [];
  data.sources_more = data.sources_more || [];
  data.your_version = data.your_version || {
    title: "",
    keep: data.adaptation?.keep || [],
    modify: data.adaptation?.modify || [],
    add: data.adaptation?.add || data.adaptation?.steps || [],
    watch_for: data.adaptation?.watch_for || [],
  };
  return data;
}

function renderYourVersion(yv) {
  const titleEl = $("#your-version-title");
  if (yv?.title) {
    titleEl.textContent = yv.title;
    titleEl.hidden = false;
  } else {
    titleEl.textContent = "";
    titleEl.hidden = true;
  }
  fillPhaseList($("#your-version-keep"), yv?.keep || [], "start");
  fillPhaseList($("#your-version-modify"), yv?.modify || [], "later");
  fillPhaseList($("#your-version-add"), yv?.add || [], "start");
  fillPhaseList($("#your-version-watch"), yv?.watch_for || [], "avoid");
}

function resetFeedbackUI() {
  feedbackState.rating = null;
  feedbackState.submitted = false;
  feedbackState.submitting = false;

  const section = document.querySelector(".report-feedback");
  if (section) section.classList.remove("is-submitted");

  const up = $("#feedback-thumb-up");
  const down = $("#feedback-thumb-down");
  if (up) {
    up.classList.remove("is-selected");
    up.setAttribute("aria-pressed", "false");
    up.disabled = false;
  }
  if (down) {
    down.classList.remove("is-selected");
    down.setAttribute("aria-pressed", "false");
    down.disabled = false;
  }

  const details = $("#feedback-details");
  if (details) details.hidden = true;

  const thanks = $("#feedback-thanks");
  if (thanks) thanks.hidden = true;

  const err = $("#feedback-error");
  if (err) {
    err.textContent = "";
    err.hidden = true;
  }

  const comment = $("#feedback-comment");
  if (comment) {
    comment.value = "";
    comment.disabled = false;
  }

  const submit = $("#feedback-submit");
  if (submit) {
    submit.disabled = false;
    submit.textContent = "Send feedback";
  }
}

function selectFeedbackRating(rating) {
  if (feedbackState.submitted) return;
  feedbackState.rating = rating;

  const up = $("#feedback-thumb-up");
  const down = $("#feedback-thumb-down");
  up.classList.toggle("is-selected", rating === "up");
  down.classList.toggle("is-selected", rating === "down");
  up.setAttribute("aria-pressed", rating === "up" ? "true" : "false");
  down.setAttribute("aria-pressed", rating === "down" ? "true" : "false");

  $("#feedback-details").hidden = false;
  $("#feedback-error").hidden = true;
}

async function submitFeedback() {
  if (feedbackState.submitted || feedbackState.submitting) return;
  if (!feedbackState.rating) {
    const err = $("#feedback-error");
    err.textContent = "Choose thumbs up or down first.";
    err.hidden = false;
    return;
  }

  feedbackState.submitting = true;
  const btn = $("#feedback-submit");
  btn.disabled = true;
  btn.textContent = "Sending…";

  try {
    const summary = state.lastResult;
    await api("/api/feedback", {
      method: "POST",
      body: JSON.stringify({
        rating: feedbackState.rating,
        comment: $("#feedback-comment").value.trim() || null,
        aspiration_id: state.lastRequest?.aspiration_id ?? state.aspiration?.id ?? null,
        result_summary: summary
          ? {
              confidence: summary.confidence,
              transformation_name: summary.transformation_name,
              synthesis_path: summary.synthesis_path,
            }
          : null,
      }),
    });
    feedbackState.submitted = true;
    document.querySelector(".report-feedback")?.classList.add("is-submitted");
    $("#feedback-details").hidden = true;
    $("#feedback-thanks").hidden = false;
    $("#feedback-thumb-up").disabled = true;
    $("#feedback-thumb-down").disabled = true;
    $("#feedback-comment").disabled = true;
  } catch (e) {
    const err = $("#feedback-error");
    err.textContent = e.message || "Could not send feedback. Try again.";
    err.hidden = false;
    btn.disabled = false;
    btn.textContent = "Send feedback";
  } finally {
    feedbackState.submitting = false;
  }
}

function renderResults(data) {
  resetFeedbackUI();
  normalizeResult(data);

  const gap = $("#gap-notice");
  if (data.gap_notice) {
    gap.textContent = data.gap_notice;
    gap.hidden = false;
  } else {
    gap.hidden = true;
  }

  const badge = $("#confidence-badge");
  const badgeLabel = $("#confidence-badge-label");
  badge.className = `report-badge confidence-${data.confidence}`;
  if (badgeLabel) {
    badgeLabel.textContent = formatConfidenceLabel(data.confidence);
  }

  const title = data.transformation_name || data.philosophy_label || "Transformation";
  $("#transformation-name").textContent = title;

  const change = data.what_youre_trying_to_change || {};
  const readiness = data.environment_readiness || {};
  const goal = change.goal || "";
  const operational = change.operational_meaning || "";

  const headline = data.headline || "";
  $("#hero-lede").textContent =
    headline ||
    operational ||
    readiness.readiness_summary ||
    "How this change behaves under pressure in your org.";

  const goalEl = $("#transformation-goal");
  goalEl.textContent = goal ? `"${goal}"` : "";
  const detailEl = $("#operational-meaning");
  if (operational && operational !== goal) {
    detailEl.textContent = operational;
    detailEl.hidden = false;
  } else {
    detailEl.textContent = "";
    detailEl.hidden = true;
  }

  fillIconList($("#supporting-conditions-list"), readiness.supporting_conditions || [], "check_circle");
  fillIconList($("#resisting-conditions-list"), readiness.resisting_conditions || [], "cancel");

  const readinessSummary = $("#readiness-summary");
  if (readiness.readiness_summary && readiness.readiness_summary !== operational) {
    readinessSummary.textContent = readiness.readiness_summary;
    readinessSummary.hidden = false;
  } else {
    readinessSummary.textContent = "";
    readinessSummary.hidden = true;
  }

  const tradeoffsSection = $("#tradeoffs-section");
  const tradeoffs = data.contradicting_philosophies || [];
  if (tradeoffs.length) {
    fillIconList($("#tradeoffs-list"), tradeoffs, "balance");
    tradeoffsSection.hidden = false;
  } else {
    tradeoffsSection.hidden = true;
  }

  $("#bottleneck-narrative").innerHTML = buildBottleneckNarrative(data.first_bottleneck);

  renderYourVersion(data.your_version);

  fillPhaseList($("#start-with-list"), data.how_to_drive_change?.start_with || [], "start");
  fillPhaseList($("#avoid-list"), data.how_to_drive_change?.avoid || [], "avoid");
  fillPhaseList(
    $("#introduce-later-list"),
    data.how_to_drive_change?.introduce_later || [],
    "later"
  );

  renderMeasureContent($("#positive-signals-content"), data.what_to_measure?.positive_signals || []);
  renderMeasureContent($("#warning-signs-content"), data.what_to_measure?.warning_signs || []);
  renderCourseCorrect(
    $("#course-correct-content"),
    data.when_to_course_correct?.course_correct_if || [],
    data.when_to_course_correct?.typical_adaptation || ""
  );

  const worksSection = document.querySelector(".report-works");
  const worksBest = data.where_this_works_best?.conditions || [];
  if (worksBest.length) {
    fillIconList($("#works-best-conditions-list"), worksBest, "check_circle");
    worksSection.hidden = false;
  } else {
    worksSection.hidden = true;
  }

  const insight = data.core_organizational_insight || "";
  $("#core-organizational-insight").textContent = insight ? `"${insight.replace(/^"|"$/g, "")}"` : "";

  const sourcesEl = $("#sources-list");
  sourcesEl.innerHTML = "";
  for (const s of data.sources || []) {
    sourcesEl.appendChild(renderSourceCard(s));
  }
  if (!data.sources?.length) {
    sourcesEl.innerHTML = "<p class='report-empty'><em>No sources returned</em></p>";
  }

  const moreWrap = $("#sources-more-wrap");
  const moreList = $("#sources-more-list");
  moreList.innerHTML = "";
  if (data.sources_more?.length) {
    for (const s of data.sources_more) {
      moreList.appendChild(renderSourceCard(s));
    }
    moreWrap.hidden = false;
  } else {
    moreWrap.hidden = true;
  }
}

function showResultsLoading() {
  $("#loading-state").hidden = false;
  $("#results").hidden = true;
  $("#error-state").hidden = true;
}

function startLoadingProgress() {
  const statusEl = $("#loading-status");
  const started = Date.now();
  const stages = [
    [0, "Matching patterns to your org…"],
    [6, "Mapping pressure and friction…"],
    [14, "Writing how behavior shifts under stress…"],
    [24, "Almost there…"],
  ];
  const tick = () => {
    const elapsed = Math.floor((Date.now() - started) / 1000);
    let msg = stages[0][1];
    for (const [sec, text] of stages) {
      if (elapsed >= sec) msg = text;
    }
    if (elapsed >= 32) {
      msg = `Still working (${elapsed}s) — we'll show results either way…`;
    }
    statusEl.textContent = msg;
  };
  tick();
  return setInterval(tick, 1000);
}

async function runStressTest() {
  if (!state.aspiration || !state.lastRequest) return;

  showResultsLoading();
  const progressTimer = startLoadingProgress();

  const controller = new AbortController();
  const clientTimeout = setTimeout(() => controller.abort(), 55000);

  try {
    const { data, headers } = await api("/api/stress-test", {
      method: "POST",
      body: JSON.stringify(state.lastRequest),
      signal: controller.signal,
      returnHeaders: true,
    });
    state.lastResult = {
      confidence: data.confidence,
      transformation_name: data.transformation_name || data.philosophy_label,
      synthesis_path: headers.get("X-Synthesis-Path"),
    };
    try {
      renderResults(data);
      $("#results").hidden = false;
      track("stress_test_completed", {
        aspiration_id: state.aspiration?.id,
        confidence: data.confidence,
        transformation_name: data.transformation_name,
      });
    } catch (renderErr) {
      console.error(renderErr);
      $("#error-state").hidden = false;
      $("#error-message").textContent = `Could not display results: ${renderErr.message}`;
    }
  } catch (e) {
    $("#error-state").hidden = false;
    if (e.name === "AbortError") {
      track("stress_test_failed", { aspiration_id: state.aspiration?.id, reason: "timeout" });
      $("#error-message").textContent =
        "Request timed out after 55 seconds. Check your network or set REALITY_CHECK_SKIP_LLM=1 in .env for instant results.";
    } else {
      track("stress_test_failed", { aspiration_id: state.aspiration?.id, reason: e.message });
      $("#error-message").textContent = e.message || String(e);
    }
  } finally {
    clearTimeout(clientTimeout);
    clearInterval(progressTimer);
    $("#loading-state").hidden = true;
  }
}

function bindEvents() {
  $("#calibration-form").addEventListener("submit", (e) => {
    e.preventDefault();
    if (!state.aspiration) return;
    if (!validateWizardStep(state.wizardIndex)) {
      const hint = $("#wizard-hint");
      hint.textContent = "Choose an option to continue.";
      hint.hidden = false;
      return;
    }
    captureCurrentWizardStep();
    for (let i = 0; i < state.wizardSteps.length; i++) {
      const step = state.wizardSteps[i];
      if (step.layer === "operations" && !state.wizardAnswers[step.id]) {
        state.wizardIndex = i;
        renderWizardStep();
        const hint = $("#wizard-hint");
        hint.textContent = "Please answer this question before continuing.";
        hint.hidden = false;
        return;
      }
    }
    state.lastRequest = {
      aspiration_id: state.aspiration.id,
      org_profile: buildOrgProfile(e.target),
    };
    track("stress_test_submitted", {
      aspiration_id: state.aspiration.id,
      label: state.aspiration.label,
    });
    showStep(3);
    runStressTest();
  });

  $("#wizard-next").addEventListener("click", wizardNext);
  $("#wizard-back").addEventListener("click", wizardBack);
  $("#back-to-transform-grid").addEventListener("click", () => {
    state.aspiration = null;
    showLanding();
    document.body.dataset.phase = "landing";
  });
  $("#continue-to-calibration").addEventListener("click", continueToCalibration);

  $("#feedback-thumb-up").addEventListener("click", () => selectFeedbackRating("up"));
  $("#feedback-thumb-down").addEventListener("click", () => selectFeedbackRating("down"));
  $("#feedback-submit").addEventListener("click", submitFeedback);

  const resetFlow = (source) => () => {
    track(source === "try_another" ? "try_another" : "start_over", {
      aspiration_id: state.aspiration?.id,
    });
    state.aspiration = null;
    state.lastRequest = null;
    state.lastResult = null;
    resetFeedbackUI();
    state.questions = [];
    $("#calibration-form").reset();
    $("#wizard-panel").innerHTML =
      '<p class="loading-text">Choose a transformation to continue.</p>';
    state.wizardSteps = [];
    state.wizardIndex = 0;
    state.wizardAnswers = {};
    showLanding();
    showStep(1);
  };

  $("#start-over").addEventListener("click", resetFlow("start_over"));
  $("#try-another").addEventListener("click", resetFlow("try_another"));
  $("#retry-stress-test").addEventListener("click", runStressTest);
}

async function init() {
  track("page_view", { referrer: document.referrer || null });
  bindEvents();
  $("#wizard-panel").innerHTML =
    '<p class="loading-text">Choose a transformation to continue.</p>';
  await loadTransformations();
  showStep(1);
}

init();
