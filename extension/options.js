const $ = (id) => document.getElementById(id);

async function load() {
  const { baseUrl = "", apiKey = "" } = await browser.storage.local.get(["baseUrl", "apiKey"]);
  $("baseUrl").value = baseUrl;
  $("apiKey").value = apiKey;
}

$("opts").addEventListener("submit", async (e) => {
  e.preventDefault();
  await browser.storage.local.set({
    baseUrl: $("baseUrl").value.trim(),
    apiKey: $("apiKey").value.trim(),
  });
  const s = $("status");
  s.textContent = "Saved.";
  s.hidden = false;
  setTimeout(() => (s.hidden = true), 1500);
});

load();
