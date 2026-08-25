// ---------- Telegram init ----------
const tg = window.Telegram?.WebApp;
if (tg) {
  tg.ready();
  tg.expand();
  tg.setHeaderColor?.("#0e0d1a");
  tg.setBackgroundColor?.("#0e0d1a");
}

// ---------- State ----------
let state = {
  me: null,
  challenges: [],
  joinedIds: new Set(),
  boardChallengeId: null,
  isAdmin: false,
};

// ---------- Helpers ----------
const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => document.querySelectorAll(sel);

function toast(msg) {
  const t = $("#toast");
  t.textContent = msg;
  t.hidden = false;
  clearTimeout(t._timer);
  t._timer = setTimeout(() => (t.hidden = true), 2200);
}
function haptic(type = "medium") { tg?.HapticFeedback?.impactOccurred?.(type); }
function initials(name) { return (name || "?").trim().charAt(0).toUpperCase(); }
function escapeHtml(s) {
  return String(s || "").replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

// ---------- Ekran boshqaruvi ----------
function showScreen(id) {
  ["loading", "register", "pending", "rejected", "main"].forEach((s) => {
    $(`#screen-${s}`).hidden = s !== id;
  });
}

// ---------- Boshlang'ich yuklash ----------
function setLoadingText(msg) {
  const el = document.querySelector("#screen-loading .loader");
  if (el) el.innerHTML = msg;
}

async function fetchMeWithRetry(maxTries = 6) {
  // Render bepul serveri uxlab qolgan bo'lsa uyg'onishini kutamiz.
  for (let i = 1; i <= maxTries; i++) {
    try {
      return await API.me();
    } catch (e) {
      if (i < maxTries) {
        setLoadingText(`Server uyg'onmoqda… (${i}/${maxTries})<br><small style="color:var(--text-dim)">Bepul serverda birinchi ochilish sekin bo'ladi</small>`);
        await new Promise((r) => setTimeout(r, 5000)); // 5 soniya kutib qayta urinamiz
      } else {
        throw e;
      }
    }
  }
}

async function boot() {
  showScreen("loading");
  setLoadingText("Yuklanmoqda…");
  try {
    state.me = await fetchMeWithRetry();
  } catch (e) {
    setLoadingText(
      `Ulanmadi 😕<br><small style="color:var(--text-dim)">${escapeHtml(e.message)}</small><br>` +
      `<button class="btn-ghost" onclick="location.reload()" style="margin-top:16px">Qayta urinish</button>`
    );
    return;
  }

  const status = state.me.user.status;
  state.isAdmin = state.me.user.is_admin;

  // Admin har doim ichkariga kiradi (ro'yxatdan o'tmasa ham)
  if (state.isAdmin) {
    await enterMain();
    return;
  }

  if (status === "new") showScreen("register");
  else if (status === "pending") showScreen("pending");
  else if (status === "rejected") showScreen("rejected");
  else if (status === "approved") await enterMain();
}

// ---------- Ro'yxatdan o'tish ----------
$("#regSubmit").addEventListener("click", async () => {
  const name = $("#regName").value.trim();
  const phone = $("#regPhone").value.trim();
  const errBox = $("#regError");
  errBox.hidden = true;

  if (name.length < 3) { errBox.textContent = "Ismni to'liq kiriting"; errBox.hidden = false; return; }
  if (phone.length < 7) { errBox.textContent = "Telefon raqamni to'g'ri kiriting"; errBox.hidden = false; return; }

  const btn = $("#regSubmit");
  btn.disabled = true;
  btn.textContent = "Yuborilmoqda…";
  try {
    await API.register(name, phone);
    haptic("light");
    showScreen("pending");
  } catch (e) {
    errBox.textContent = e.message;
    errBox.hidden = false;
  } finally {
    btn.disabled = false;
    btn.textContent = "Ariza yuborish";
  }
});

// Kutish ekranida holatni yangilash
$("#pendingRefresh").addEventListener("click", async () => {
  try {
    state.me = await API.me();
    const s = state.me.user.status;
    if (s === "approved") { toast("Tasdiqlandingiz!"); await enterMain(); }
    else if (s === "rejected") showScreen("rejected");
    else toast("Hali kutilmoqda…");
  } catch (e) { toast(e.message); }
});

// ---------- Asosiy ilovaga kirish ----------
async function enterMain() {
  showScreen("main");
  $("#totalPoints").textContent = `${state.me.total_points} ball`;
  state.joinedIds = new Set(state.me.participations.map((p) => p.challenge_id));

  if (state.isAdmin) $("#adminTab").hidden = false;

  try {
    state.challenges = await API.challenges();
  } catch (e) {
    // admin approved emas bo'lishi mumkin emas, lekin himoya uchun
    state.challenges = [];
  }
  renderHome();
  renderChallenges();
}

// ---------- Tab switching ----------
$$(".tab").forEach((btn) => btn.addEventListener("click", () => switchTab(btn.dataset.tab)));
document.addEventListener("click", (e) => {
  const goto = e.target.dataset?.goto;
  if (goto) switchTab(goto);
});
function switchTab(tab) {
  $$(".tab").forEach((b) => b.classList.toggle("active", b.dataset.tab === tab));
  $$(".view").forEach((v) => v.classList.toggle("active", v.id === `view-${tab}`));
  if (tab === "board") renderBoard();
  if (tab === "admin") renderAdmin();
}

// ---------- Home ----------
function renderHome() {
  const box = $("#myChallenges");
  const empty = $("#homeEmpty");
  const mine = state.me?.participations || [];
  if (mine.length === 0) { box.innerHTML = ""; empty.hidden = false; return; }
  empty.hidden = true;
  box.innerHTML = mine.map((p) => `
    <div class="mycard">
      <div class="mycard-top">
        <div class="mycard-emoji">${p.emoji}</div>
        <div>
          <div class="mycard-title">${escapeHtml(p.challenge_title)}</div>
          <div class="mycard-sub">Jami ${p.total_checkins} kun bajarilgan</div>
        </div>
      </div>
      <div class="streak-row">
        <div class="stat"><div class="stat-val flame">${p.current_streak}</div><div class="stat-label">Streak</div></div>
        <div class="stat"><div class="stat-val">${p.best_streak}</div><div class="stat-label">Rekord</div></div>
        <div class="stat"><div class="stat-val">${p.points}</div><div class="stat-label">Ball</div></div>
      </div>
      <button class="btn-checkin ${p.checked_today ? "done" : ""}" data-checkin="${p.challenge_id}" ${p.checked_today ? "disabled" : ""}>
        ${p.checked_today ? "✅ Bugun bajarildi" : "🔥 Bugun bajardim"}
      </button>
    </div>`).join("");
  box.querySelectorAll("[data-checkin]").forEach((btn) =>
    btn.addEventListener("click", () => doCheckin(Number(btn.dataset.checkin))));
}

// ---------- Challenges ----------
function renderChallenges() {
  const list = $("#challengeList");
  list.innerHTML = state.challenges.map((c) => {
    const joined = state.joinedIds.has(c.id);
    return `
      <div class="chcard">
        <div class="chcard-emoji">${c.emoji}</div>
        <div class="chcard-body">
          <div class="chcard-title">${escapeHtml(c.title)}</div>
          <div class="chcard-desc">${escapeHtml(c.description || "")} · ${c.duration_days} kun</div>
        </div>
        <button class="btn-join ${joined ? "joined" : ""}" data-join="${c.id}" ${joined ? "disabled" : ""}>
          ${joined ? "Qo'shilgan" : "Qo'shilish"}
        </button>
      </div>`;
  }).join("");
  list.querySelectorAll("[data-join]").forEach((btn) =>
    btn.addEventListener("click", () => joinChallenge(Number(btn.dataset.join))));
}

// ---------- Leaderboard ----------
function renderBoardPicker() {
  const picker = $("#boardPicker");
  if (state.challenges.length === 0) return;
  if (!state.boardChallengeId) state.boardChallengeId = state.challenges[0].id;
  picker.innerHTML = state.challenges.map((c) =>
    `<button class="bp-chip ${c.id === state.boardChallengeId ? "active" : ""}" data-board="${c.id}">${c.emoji} ${escapeHtml(c.title)}</button>`
  ).join("");
  picker.querySelectorAll("[data-board]").forEach((btn) =>
    btn.addEventListener("click", () => {
      state.boardChallengeId = Number(btn.dataset.board);
      renderBoardPicker(); renderBoard();
    }));
}
async function renderBoard() {
  renderBoardPicker();
  const box = $("#leaderboard");
  box.innerHTML = `<div class="skeleton">Yuklanmoqda…</div>`;
  try {
    const rows = await API.leaderboard(state.boardChallengeId);
    if (rows.length === 0) { box.innerHTML = `<div class="skeleton">Hali ishtirokchi yo'q.</div>`; return; }
    box.innerHTML = rows.map((r) => {
      const top = r.rank <= 3;
      const medal = r.rank === 1 ? "🥇" : r.rank === 2 ? "🥈" : r.rank === 3 ? "🥉" : r.rank;
      const avatar = r.photo_url ? `<img src="${r.photo_url}" alt="">` : initials(r.name);
      return `
        <div class="lrow ${r.is_me ? "me" : ""} ${top ? "top" : ""}">
          <div class="lrank">${medal}</div>
          <div class="lavatar">${avatar}</div>
          <div class="lname">${escapeHtml(r.name)}${r.is_me ? " (siz)" : ""}</div>
          <div class="lstreak">🔥${r.current_streak}</div>
          <div class="lpoints">${r.points}</div>
        </div>`;
    }).join("");
  } catch (e) { box.innerHTML = `<div class="skeleton">Xatolik: ${escapeHtml(e.message)}</div>`; }
}

// ---------- Admin ----------
async function renderAdmin() {
  const box = $("#adminList");
  box.innerHTML = `<div class="skeleton">Yuklanmoqda…</div>`;
  try {
    const pending = await API.adminPending();
    if (pending.length === 0) { box.innerHTML = `<div class="skeleton">Kutayotgan ariza yo'q.</div>`; return; }
    box.innerHTML = pending.map((u) => `
      <div class="admin-card" data-uid="${u.id}">
        <div class="admin-name">${escapeHtml(u.full_name || "—")}</div>
        <div class="admin-phone">${escapeHtml(u.phone || "—")}</div>
        <div class="admin-user">${u.username ? "@" + escapeHtml(u.username) : "username yo'q"} · ID ${u.telegram_id}</div>
        <div class="admin-actions">
          <button class="btn-approve" data-approve="${u.id}">✓ Tasdiqlash</button>
          <button class="btn-reject" data-reject="${u.id}">✕ Rad etish</button>
        </div>
      </div>`).join("");
    box.querySelectorAll("[data-approve]").forEach((btn) =>
      btn.addEventListener("click", () => moderate(Number(btn.dataset.approve), "approve")));
    box.querySelectorAll("[data-reject]").forEach((btn) =>
      btn.addEventListener("click", () => moderate(Number(btn.dataset.reject), "reject")));
  } catch (e) { box.innerHTML = `<div class="skeleton">Xatolik: ${escapeHtml(e.message)}</div>`; }
}
async function moderate(userId, action) {
  haptic("light");
  try {
    await API.adminModerate(userId, action);
    toast(action === "approve" ? "Tasdiqlandi ✓" : "Rad etildi");
    const card = $(`.admin-card[data-uid="${userId}"]`);
    if (card) card.remove();
    if ($("#adminList").children.length === 0)
      $("#adminList").innerHTML = `<div class="skeleton">Kutayotgan ariza yo'q.</div>`;
  } catch (e) { toast(e.message); }
}

// ---------- Actions ----------
async function joinChallenge(id) {
  haptic("light");
  try {
    await API.join(id);
    state.joinedIds.add(id);
    toast("Qo'shildingiz!");
    await refreshMe();
    renderChallenges(); renderHome();
  } catch (e) { toast(e.message); }
}
async function doCheckin(id) {
  haptic("medium");
  try {
    const res = await API.checkin(id);
    if (res.status === "ok") { haptic("heavy"); tg?.HapticFeedback?.notificationOccurred?.("success"); }
    toast(res.message);
    await refreshMe(); renderHome();
  } catch (e) { toast(e.message); }
}
async function refreshMe() {
  state.me = await API.me();
  state.joinedIds = new Set(state.me.participations.map((p) => p.challenge_id));
  $("#totalPoints").textContent = `${state.me.total_points} ball`;
}

boot();
