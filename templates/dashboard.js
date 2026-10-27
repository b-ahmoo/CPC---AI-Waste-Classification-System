// dashboard.js
// Statistical dashboard for the AI waste management system.
// Uses mock classification records for now. When the real classifier
// results are available, only getClassifications() needs to change.

// ---------------------------------------------------------------
// 1. CONFIG: match these IDs to the elements in your HTML
// ---------------------------------------------------------------
const CONFIG = {
  USE_MOCK_DATA: true,
  API_URL: "/api/classifications",       // for later, when real data exists
  ids: {
    totalCard: "total-classifications",  // <span id="total-classifications">
    categoriesCard: "waste-categories",  // <span id="waste-categories">
    accuracyCard: "classification-accuracy",
    categoryChart: "categoryChart",      // <canvas id="categoryChart">
    activityChart: "activityChart",      // <canvas id="activityChart">
    note: "data-note",                   // <p id="data-note">
  },
  categories: ["Plastic", "Paper", "Glass", "Metal", "Organic", "E-waste"],
};

// ---------------------------------------------------------------
// 2. MOCK DATA: shaped like real classifier output
// ---------------------------------------------------------------
// Each record = one image classified by the model.
// { id, predicted, actual, confidence, timestamp }
function generateMockClassifications(count = 250, days = 14) {
  const records = [];
  const now = Date.now();
  // Weights make the distribution look realistic (more plastic than e-waste)
  const weights = [0.30, 0.22, 0.10, 0.12, 0.20, 0.06];

  for (let i = 0; i < count; i++) {
    const actual = weightedPick(CONFIG.categories, weights);
    const correct = Math.random() < 0.87; // ~87% mock accuracy
    const predicted = correct
      ? actual
      : randomItem(CONFIG.categories.filter((c) => c !== actual));

    records.push({
      id: i + 1,
      predicted,
      actual,
      confidence: +(correct ? 0.7 + Math.random() * 0.3 : 0.4 + Math.random() * 0.35).toFixed(2),
      timestamp: new Date(now - Math.random() * days * 86400000).toISOString(),
    });
  }
  return records;
}

function weightedPick(items, weights) {
  let r = Math.random();
  for (let i = 0; i < items.length; i++) {
    r -= weights[i];
    if (r <= 0) return items[i];
  }
  return items[items.length - 1];
}

function randomItem(arr) {
  return arr[Math.floor(Math.random() * arr.length)];
}

// ---------------------------------------------------------------
// 3. DATA SOURCE: the only function that changes for real data
// ---------------------------------------------------------------
async function getClassifications() {
  if (CONFIG.USE_MOCK_DATA) {
    return generateMockClassifications();
  }
  const res = await fetch(CONFIG.API_URL);
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

// ---------------------------------------------------------------
// 4. STATISTICS: computed from records, works for mock or real
// ---------------------------------------------------------------
function computeStats(records) {
  const total = records.length;

  const byCategory = {};
  CONFIG.categories.forEach((c) => (byCategory[c] = 0));
  records.forEach((r) => (byCategory[r.predicted] = (byCategory[r.predicted] || 0) + 1));

  const labelled = records.filter((r) => r.actual);
  const correct = labelled.filter((r) => r.predicted === r.actual).length;
  const accuracy = labelled.length ? (correct / labelled.length) * 100 : 0;

  const byDay = {};
  records.forEach((r) => {
    const day = r.timestamp.slice(0, 10); // YYYY-MM-DD
    byDay[day] = (byDay[day] || 0) + 1;
  });
  const days = Object.keys(byDay).sort();

  return {
    total,
    categoryCount: Object.values(byCategory).filter((n) => n > 0).length,
    accuracy,
    byCategory,
    activity: { labels: days, values: days.map((d) => byDay[d]) },
  };
}

// ---------------------------------------------------------------
// 5. RENDERING
// ---------------------------------------------------------------
let categoryChart = null;
let activityChart = null;

function setText(id, value) {
  const el = document.getElementById(id);
  if (el) el.textContent = value;
  else console.warn(`Element #${id} not found`);
}

function renderCards(stats) {
  setText(CONFIG.ids.totalCard, stats.total.toLocaleString());
  setText(CONFIG.ids.categoriesCard, stats.categoryCount);
  setText(CONFIG.ids.accuracyCard, stats.accuracy.toFixed(1) + "%");
}

function renderCategoryChart(stats) {
  const ctx = document.getElementById(CONFIG.ids.categoryChart);
  if (!ctx) return;
  if (categoryChart) categoryChart.destroy();

  categoryChart = new Chart(ctx, {
    type: "doughnut",
    data: {
      labels: Object.keys(stats.byCategory),
      datasets: [{
        data: Object.values(stats.byCategory),
        backgroundColor: ["#174c3c", "#248365", "#5fae8c", "#a3cfb8", "#c9a227", "#8a9a91"],
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { position: "bottom" } },
    },
  });
}

function renderActivityChart(stats) {
  const ctx = document.getElementById(CONFIG.ids.activityChart);
  if (!ctx) return;
  if (activityChart) activityChart.destroy();

  activityChart = new Chart(ctx, {
    type: "line",
    data: {
      labels: stats.activity.labels,
      datasets: [{
        label: "Classifications per day",
        data: stats.activity.values,
        borderColor: "#248365",
        backgroundColor: "rgba(36,131,101,0.15)",
        fill: true,
        tension: 0.3,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: { y: { beginAtZero: true, ticks: { precision: 0 } } },
    },
  });
}

// ---------------------------------------------------------------
// 6. INIT
// ---------------------------------------------------------------
async function loadDashboard() {
  try {
    const records = await getClassifications();
    const stats = computeStats(records);
    renderCards(stats);
    renderCategoryChart(stats);
    renderActivityChart(stats);
    setText(
      CONFIG.ids.note,
      CONFIG.USE_MOCK_DATA
        ? "Showing mock data. Live statistics will appear once classification data is connected."
        : "Showing live classification data."
    );
  } catch (err) {
    console.error("Failed to load dashboard data:", err);
    setText(CONFIG.ids.note, "Could not load classification data.");
  }
}

document.addEventListener("DOMContentLoaded", loadDashboard);
