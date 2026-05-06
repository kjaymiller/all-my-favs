(() => {
  const el = document.getElementById("perDayChart");
  if (!el || typeof Chart === "undefined") return;
  const days = JSON.parse(el.dataset.days || "[]");
  const counts = JSON.parse(el.dataset.counts || "[]");
  const styles = getComputedStyle(document.documentElement);
  const accent = styles.getPropertyValue("--accent").trim() || "#7aa2ff";
  const muted = styles.getPropertyValue("--muted").trim() || "#98a0ad";
  const border = styles.getPropertyValue("--border").trim() || "#2a2f3a";
  new Chart(el, {
    type: "bar",
    data: {
      labels: days,
      datasets: [{
        label: "Bookmarks",
        data: counts,
        backgroundColor: accent,
        borderRadius: 4,
        maxBarThickness: 18,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: false }, tooltip: { mode: "index", intersect: false } },
      scales: {
        x: { ticks: { color: muted, maxRotation: 0, autoSkip: true }, grid: { display: false } },
        y: { beginAtZero: true, ticks: { color: muted, precision: 0 }, grid: { color: border } },
      },
    },
  });
})();
