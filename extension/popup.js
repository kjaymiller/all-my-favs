const $ = (id) => document.getElementById(id);

async function getConfig() {
  const { baseUrl = "", apiKey = "" } = await browser.storage.local.get(["baseUrl", "apiKey"]);
  return { baseUrl: baseUrl.replace(/\/$/, ""), apiKey };
}

async function init() {
  const tabs = await browser.tabs.query({ active: true, currentWindow: true });
  const tab = tabs[0];
  if (tab) {
    $("url").value = tab.url || "";
    $("title").value = tab.title || "";
  }
  const { baseUrl, apiKey } = await getConfig();
  if (!baseUrl || !apiKey) {
    setStatus("Set base URL + API key in Settings.", true);
    $("submit").disabled = true;
  }
}

function setStatus(msg, isError = false) {
  const el = $("status");
  el.textContent = msg;
  el.hidden = false;
  el.classList.toggle("error", isError);
}

$("open-options").addEventListener("click", (e) => {
  e.preventDefault();
  browser.runtime.openOptionsPage();
});

$("save").addEventListener("submit", async (e) => {
  e.preventDefault();
  const { baseUrl, apiKey } = await getConfig();
  if (!baseUrl || !apiKey) return setStatus("Configure the extension first.", true);

  const tags = $("tags").value
    .split(",")
    .map((t) => t.trim().toLowerCase())
    .filter(Boolean);
  const payload = {
    url: $("url").value,
    title: $("title").value || null,
    notes: $("notes").value || null,
    tags,
    source: "firefox-ext",
  };
  $("submit").disabled = true;
  setStatus("Saving…");
  try {
    const res = await fetch(`${baseUrl}/api/bookmarks`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${apiKey}`,
      },
      body: JSON.stringify(payload),
    });
    if (!res.ok) {
      const text = await res.text().catch(() => "");
      throw new Error(`${res.status} ${res.statusText} ${text}`);
    }
    setStatus("Saved.");
    setTimeout(() => window.close(), 600);
  } catch (err) {
    setStatus(`Failed: ${err.message}`, true);
    $("submit").disabled = false;
  }
});

init();
