const LANG = window.COPY2IMAGE_LANG || "zh";
const ALT_LANG = window.COPY2IMAGE_ALT_LANG || (LANG === "zh" ? "en" : "zh");
const THEME_KEY = "copy2image_theme";

const t = {
  loading: LANG === "zh" ? "加载中..." : "Loading...",
  saving: LANG === "zh" ? "保存中..." : "Saving...",
  loadFailed: LANG === "zh" ? "加载设置失败" : "Failed to load settings",
  saveFailed: LANG === "zh" ? "保存设置失败" : "Failed to save settings",
  saved: LANG === "zh" ? "设置已保存，后续任务将使用新参数。" : "Settings saved. New runs will use these values.",
  reloaded: LANG === "zh" ? "已重新加载设置。" : "Settings reloaded.",
  showSecret: LANG === "zh" ? "显示 API Key" : "Show API Key",
  hideSecret: LANG === "zh" ? "隐藏 API Key" : "Hide API Key",
};

function prefersReducedMotion() {
  return Boolean(window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches);
}

function themeIconSvg(isDark) {
  if (isDark) {
    return `
      <span class="btn-icon-wrap" aria-hidden="true">
        <svg class="btn-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
          <circle cx="12" cy="12" r="4.2"></circle>
          <path d="M12 2v2.2"></path>
          <path d="M12 19.8V22"></path>
          <path d="m4.9 4.9 1.5 1.5"></path>
          <path d="m17.6 17.6 1.5 1.5"></path>
          <path d="M2 12h2.2"></path>
          <path d="M19.8 12H22"></path>
          <path d="m4.9 19.1 1.5-1.5"></path>
          <path d="m17.6 6.4 1.5-1.5"></path>
        </svg>
      </span>
    `;
  }
  return `
    <span class="btn-icon-wrap" aria-hidden="true">
      <svg class="btn-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
        <path d="M21 12.8A9 9 0 1 1 11.2 3 7 7 0 0 0 21 12.8Z"></path>
      </svg>
    </span>
  `;
}

function secretIconSvg(visible) {
  if (visible) {
    return `
      <svg class="btn-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
        <path d="M3 3 21 21"></path>
        <path d="M10.6 10.6A3 3 0 0 0 13.4 13.4"></path>
        <path d="M9.9 5.1A11.2 11.2 0 0 1 12 4.9c4.7 0 8.8 2.9 10.4 7.1a11.7 11.7 0 0 1-3.1 4.8"></path>
        <path d="M6.7 6.7A11.6 11.6 0 0 0 1.6 12C3.2 16.2 7.3 19.1 12 19.1c1.8 0 3.5-.4 5-1.1"></path>
      </svg>
    `;
  }
  return `
    <svg class="btn-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
      <path d="M1.6 12C3.2 7.8 7.3 4.9 12 4.9s8.8 2.9 10.4 7.1c-1.6 4.2-5.7 7.1-10.4 7.1S3.2 16.2 1.6 12Z"></path>
      <circle cx="12" cy="12" r="3"></circle>
    </svg>
  `;
}

function applyTheme(theme, animate = false) {
  const body = document.body;
  const root = document.documentElement;
  const isDark = theme === "dark";
  const canAnimate = animate && !prefersReducedMotion();

  if (canAnimate) body.classList.add("theme-switching");
  root.setAttribute("data-theme", isDark ? "dark" : "light");

  const btn = document.getElementById("theme-toggle");
  if (btn) {
    btn.innerHTML = themeIconSvg(isDark);
    btn.setAttribute(
      "aria-label",
      LANG === "zh" ? (isDark ? "切换到浅色" : "切换到深色") : (isDark ? "Switch to light" : "Switch to dark")
    );
    btn.title = btn.getAttribute("aria-label") || "";
  }

  localStorage.setItem(THEME_KEY, isDark ? "dark" : "light");
  if (canAnimate) {
    window.setTimeout(() => body.classList.remove("theme-switching"), 280);
  }
}

function initTheme() {
  const saved = localStorage.getItem(THEME_KEY);
  const prefersDark = window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches;
  const theme = saved === "dark" || saved === "light" ? saved : (prefersDark ? "dark" : "light");
  applyTheme(theme, false);
}

function normalize(value) {
  if (typeof value !== "string") return null;
  const v = value.trim();
  return v ? v : null;
}

function setStatus(kind, message) {
  const el = document.getElementById("settings-status");
  if (!el) return;
  el.classList.remove("hidden", "status-info", "status-success", "status-error");
  el.classList.add(`status-${kind || "info"}`);
  el.textContent = message;
}

function setButtonLoading(button, loading) {
  if (!button) return;
  button.classList.toggle("btn-loading", loading);
  button.disabled = loading;
}

function fillForm(data) {
  const text = data?.text || {};
  const image = data?.image || {};

  const byId = (id) => document.getElementById(id);
  byId("text-api-key").value = text.api_key || "";
  byId("text-base-url").value = text.base_url || "";
  byId("text-model").value = text.model || "";

  byId("image-api-key").value = image.api_key || "";
  byId("image-base-url").value = image.base_url || "";
  byId("image-model").value = image.model || "";
  byId("image-provider").value = image.provider || "";
  byId("image-dialect").value = image.image_api_dialect || "";
}

function readFormPayload() {
  const byId = (id) => document.getElementById(id);
  return {
    text: {
      api_key: normalize(byId("text-api-key").value),
      base_url: normalize(byId("text-base-url").value),
      model: normalize(byId("text-model").value),
    },
    image: {
      api_key: normalize(byId("image-api-key").value),
      base_url: normalize(byId("image-base-url").value),
      model: normalize(byId("image-model").value),
      provider: normalize(byId("image-provider").value),
      image_api_dialect: normalize(byId("image-dialect").value),
    },
  };
}

async function fetchSettings() {
  const res = await fetch("/api/settings");
  const data = await res.json();
  if (!res.ok) throw new Error(typeof data?.detail === "string" ? data.detail : JSON.stringify(data));
  return data;
}

async function saveSettings(payload) {
  const res = await fetch("/api/settings", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(typeof data?.detail === "string" ? data.detail : JSON.stringify(data));
  return data?.settings || data;
}

async function switchLanguage(lang) {
  const res = await fetch("/api/lang", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ lang }),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(typeof data?.detail === "string" ? data.detail : JSON.stringify(data));
}

async function loadAndRenderSettings(messageAfterLoad = null) {
  setStatus("info", t.loading);
  const data = await fetchSettings();
  fillForm(data);
  setStatus("success", messageAfterLoad || t.reloaded);
}

function wireThemeToggle() {
  const btn = document.getElementById("theme-toggle");
  if (!btn) return;
  btn.addEventListener("click", () => {
    const current = document.documentElement.getAttribute("data-theme") === "dark" ? "dark" : "light";
    applyTheme(current === "dark" ? "light" : "dark", true);
  });
}

function updateSecretToggle(toggle, input) {
  const visible = input.type === "text";
  toggle.innerHTML = secretIconSvg(visible);
  const label = visible ? t.hideSecret : t.showSecret;
  toggle.setAttribute("aria-label", label);
  toggle.title = label;
}

function wireSecretToggles() {
  const toggles = Array.from(document.querySelectorAll(".secret-toggle"));
  toggles.forEach((toggle) => {
    const targetId = toggle.getAttribute("data-target");
    if (!targetId) return;
    const input = document.getElementById(targetId);
    if (!(input instanceof HTMLInputElement)) return;
    updateSecretToggle(toggle, input);
    toggle.addEventListener("click", () => {
      input.type = input.type === "password" ? "text" : "password";
      updateSecretToggle(toggle, input);
      input.focus();
      const len = input.value.length;
      try {
        input.setSelectionRange(len, len);
      } catch (_) {
        // no-op
      }
    });
  });
}

function wireLanguageToggle() {
  const btn = document.getElementById("lang-toggle");
  if (!btn) return;
  btn.addEventListener("click", async () => {
    const oldText = btn.textContent;
    btn.disabled = true;
    document.body.classList.add("page-switching");
    try {
      await switchLanguage(ALT_LANG);
      window.location.reload();
    } catch (err) {
      btn.disabled = false;
      btn.textContent = oldText;
      document.body.classList.remove("page-switching");
      setStatus("error", `${t.saveFailed}: ${String(err)}`);
    }
  });
}

function wireFormActions() {
  const form = document.getElementById("settings-form");
  const saveBtn = document.getElementById("save-settings-btn");
  const reloadBtn = document.getElementById("reload-settings-btn");
  if (!form || !saveBtn || !reloadBtn) return;

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    setButtonLoading(saveBtn, true);
    reloadBtn.disabled = true;
    setStatus("info", t.saving);
    try {
      const payload = readFormPayload();
      const saved = await saveSettings(payload);
      fillForm(saved);
      setStatus("success", t.saved);
    } catch (err) {
      setStatus("error", `${t.saveFailed}: ${String(err)}`);
    } finally {
      setButtonLoading(saveBtn, false);
      reloadBtn.disabled = false;
    }
  });

  reloadBtn.addEventListener("click", async () => {
    reloadBtn.disabled = true;
    try {
      await loadAndRenderSettings(t.reloaded);
    } catch (err) {
      setStatus("error", `${t.loadFailed}: ${String(err)}`);
    } finally {
      reloadBtn.disabled = false;
    }
  });
}

async function init() {
  initTheme();
  wireThemeToggle();
  wireSecretToggles();
  wireLanguageToggle();
  wireFormActions();
  try {
    await loadAndRenderSettings();
  } catch (err) {
    setStatus("error", `${t.loadFailed}: ${String(err)}`);
  }
}

init();

