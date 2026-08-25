// ---------- Telegram init ----------
const tg = window.Telegram?.WebApp;
if (tg) {
  tg.ready();
  tg.expand();
  // Telegram temasiga moslash (agar kerak bo'lsa)
  tg.setHeaderColor?.("#0e0d1a");
  tg.setBackgroundColor?.("#0e0d1a");
}

// ---------- State ----------
let state = {
  me: null,
  challenges: [],
  joinedIds: new Set(),
  boardChallengeId: null,
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

function haptic(type = "medium") {
  tg?.HapticFeedback?.impactOccurred?.(type);
}

function initials(name) {
  return (name || "?").trim().charAt(0).toUpperCase();
}

// ---------- Tab switching ----------
$$(".tab").forEach((btn) => {
  btn.addEventListener("click", () => switchTab(btn.dataset.tab));
});
document.addEventListener("click", (e) => {
  const goto = e.target.dataset?.goto;
  if (goto) switchTab(goto);
});

function switchTab(tab) {
  $$(".tab").forEach((b) => b.classList.toggle("active", b.dataset.tab === tab));
  $$(".view").forEach((v) => v.classList.toggle("active", v.id === `view-${tab}`));
  if (tab === "board") renderBoard();
}

// ---------- Render: Home ----------
function renderHome() {
  const box = $("#myChallenges");
  const empty = $("#homeEmpty");
  const mine = state.me?.participations || [];

  if (mine.length === 0) {
    box.innerHTML = "";
    empty.hidden = false;
    return;
  }
  empty.hidden = true;

  box.innerHTML = mine
    .map(
      (p) => `
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
      <button class="btn-checkin ${p.checked_today ? "done" : ""}"
              data-checkin="${p.challenge_id}" ${p.checked_today ? "disabled" : ""}>
        ${p.checked_today ? "✅ Bugun bajarildi" : "🔥 Bugun bajardim"}
      </button>
    </div>`
    )
    .join("");

  box.querySelectorAll("[data-checkin]").forEach((btn) => {
    btn.addEventListener("click", () => doCheckin(Number(btn.dataset.checkin)));
  });
}

// ---------- Render: Challenges ----------
function renderChallenges() {
  const list = $("#challengeList");
  list.innerHTML = state.challenges
    .map((c) => {
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
    })
    .join("");

  list.querySelectorAll("[data-join]").forEach((btn) => {
    btn.addEventListener("click", () => joinChallenge(Number(btn.dataset.join)));
  });
}

// ---------- Render: Leaderboard ----------
function renderBoardPicker() {
  const picker = $("#boardPicker");
  if (state.challenges.length === 0) return;
  if (!state.boardChallengeId) state.boardChallengeId = state.challenges[0].id;

  picker.innerHTML = state.challenges
    .map(
      (c) => `<button class="bp-chip ${c.id === state.boardChallengeId ? "active" : ""}"
                data-board="${c.id}">${c.emoji} ${escapeHtml(c.title)}</button>`
    )
    .join("");

  picker.querySelectorAll("[data-board]").forEach((btn) => {
    btn.addEventListener("click", () => {
      state.boardChallengeId = Number(btn.dataset.board);
      renderBoardPicker();
      renderBoard();
    });
  });
}

async function renderBoard() {
  renderBoardPicker();
  const box = $("#leaderboard");
  box.innerHTML = `<div class="skeleton">Yuklanmoqda…</div>`;
  try {
    const rows = await API.leaderboard(state.boardChallengeId);
    if (rows.length === 0) {
      box.innerHTML = `<div class="skeleton">Hali ishtirokchi yo'q. Birinchi bo'ling!</div>`;
      return;
    }
    box.innerHTML = rows
      .map((r) => {
        const top = r.rank <= 3;
        const medal = r.rank === 1 ? "🥇" : r.rank === 2 ? "🥈" : r.rank === 3 ? "🥉" : r.rank;
        const avatar = r.photo_url
          ? `<img src="${r.photo_url}" alt="">`
          : initials(r.name);
        return `
        <div class="lrow ${r.is_me ? "me" : ""} ${top ? "top" : ""}">
          <div class="lrank">${medal}</div>
          <div class="lavatar">${avatar}</div>
          <div class="lname">${escapeHtml(r.name)}${r.is_me ? " (siz)" : ""}</div>
          <div class="lstreak">🔥${r.current_streak}</div>
          <div class="lpoints">${r.points}</div>
        </div>`;
      })
      .join("");
  } catch (e) {
    box.innerHTML = `<div class="skeleton">Xatolik: ${escapeHtml(e.message)}</div>`;
  }
}

// ---------- Actions ----------
async function joinChallenge(id) {
  haptic("light");
  try {
    await API.join(id);
    state.joinedIds.add(id);
    toast("Qo'shildingiz!");
    await refreshMe();
    renderChallenges();
    renderHome();
  } catch (e) {
    toast(e.message);
  }
}

async function doCheckin(id) {
  haptic("medium");
  try {
    const res = await API.checkin(id);
    if (res.status === "ok") {
      haptic("heavy");
      tg?.HapticFeedback?.notificationOccurred?.("success");
    }
    toast(res.message);
    await refreshMe();
    renderHome();
  } catch (e) {
    toast(e.message);
  }
}

// ---------- Data loading ----------
async function refreshMe() {
  state.me = await API.me();
  state.joinedIds = new Set(state.me.participations.map((p) => p.challenge_id));
  $("#totalPoints").textContent = `${state.me.total_points} ball`;
}

async function init() {
  try {
    const [, challenges] = await Promise.all([refreshMe(), API.challenges()]);
    state.challenges = challenges;
    renderHome();
    renderChallenges();
  } catch (e) {
    toast("Ulanishda xato: " + e.message);
  }
}

// ---------- Utils ----------
function escapeHtml(s) {
  return String(s || "").replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c])
  );
}

init();
