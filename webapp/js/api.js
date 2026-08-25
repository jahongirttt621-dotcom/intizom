// Backend API manzili — o'zingiznikiga o'zgartiring (VPS yoki tunnel URL).
const API_BASE = "https://YOUR-BACKEND-URL.com";

const tg = window.Telegram?.WebApp;

// Har so'rovga Telegram initData'ni header sifatida qo'shamiz — server tekshiradi.
async function apiRequest(path, method = "GET", body = null) {
  const headers = {
    "Content-Type": "application/json",
    "X-Init-Data": tg?.initData || "",
  };
  const opts = { method, headers };
  if (body) opts.body = JSON.stringify(body);

  const res = await fetch(`${API_BASE}${path}`, opts);
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Xatolik" }));
    throw new Error(err.detail || `HTTP ${res.status}`);
  }
  return res.json();
}

const API = {
  me: () => apiRequest("/api/me"),
  register: (full_name, phone) => apiRequest("/api/register", "POST", { full_name, phone }),
  challenges: () => apiRequest("/api/challenges"),
  join: (challenge_id) => apiRequest("/api/join", "POST", { challenge_id }),
  checkin: (challenge_id, note = null) => apiRequest("/api/checkin", "POST", { challenge_id, note }),
  leaderboard: (challenge_id) => apiRequest(`/api/leaderboard/${challenge_id}`),
  adminPending: () => apiRequest("/api/admin/pending"),
  adminModerate: (user_id, action) => apiRequest("/api/admin/moderate", "POST", { user_id, action }),
};
