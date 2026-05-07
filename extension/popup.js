const $ = (id) => document.getElementById(id);

async function getConfig() {
  const { baseUrl = "", apiKey = "" } = await browser.storage.local.get(["baseUrl", "apiKey"]);
  return { baseUrl: baseUrl.replace(/\/$/, ""), apiKey };
}

function setStatus(msg, kind = "info") {
  const el = $("status");
  el.textContent = msg;
  el.hidden = false;
  el.classList.remove("error", "info", "ok");
  el.classList.add(kind);
}

function showBadge(text, kind) {
  const el = $("badge");
  el.textContent = text;
  el.classList.remove("saved", "new");
  el.classList.add(kind);
  el.hidden = false;
}

async function lookupExisting(baseUrl, apiKey, url) {
  const res = await fetch(
    `${baseUrl}/api/bookmarks/lookup?url=${encodeURIComponent(url)}`,
    { headers: { Authorization: `Bearer ${apiKey}` } },
  );
  if (res.status === 404) return null;
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.json();
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
    setStatus("Set base URL + API key in Settings.", "error");
    $("submit").disabled = true;
    return;
  }

  if (!$("url").value) return;

  // Check whether this URL is already saved.
  try {
    const existing = await lookupExisting(baseUrl, apiKey, $("url").value);
    if (existing) {
      showBadge("✓ Already saved", "saved");
      $("submit").textContent = "Update";
      // Pre-fill from the stored record so the user is editing, not overwriting blindly.
      if (existing.title) $("title").value = existing.title;
      if (existing.notes) $("notes").value = existing.notes;
      if (existing.tags && existing.tags.length) {
        $("tags").value = existing.tags.join(", ");
      }
      const link = $("open-existing");
      link.href = `${baseUrl}/bookmarks?q=${encodeURIComponent(existing.url)}`;
      link.hidden = false;
    } else {
      showBadge("New", "new");
      $("submit").textContent = "Save";
    }
  } catch (err) {
    // Lookup failure is non-fatal — fall back to blind save.
    setStatus(`Lookup failed: ${err.message}`, "error");
  }
}

$("open-options").addEventListener("click", (e) => {
  e.preventDefault();
  browser.runtime.openOptionsPage();
});

$("open-existing").addEventListener("click", (e) => {
  e.preventDefault();
  browser.tabs.create({ url: e.currentTarget.href });
});

$("save").addEventListener("submit", async (e) => {
  e.preventDefault();
  const { baseUrl, apiKey } = await getConfig();
  if (!baseUrl || !apiKey) return setStatus("Configure the extension first.", "error");

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
  setStatus("Saving…", "info");
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
    setStatus("Saved.", "ok");
    setTimeout(() => window.close(), 600);
  } catch (err) {
    setStatus(`Failed: ${err.message}`, "error");
    $("submit").disabled = false;
  }
});

init();
