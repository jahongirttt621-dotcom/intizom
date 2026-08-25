# Intizom — ommaviy odat challenge (Telegram Mini App)

Foydalanuvchilar challenge tanlaydi, har kuni check-in qiladi, streak yig'adi va ommaviy reytingda raqobatlashadi.

## Struktura

```
intizom/
├── backend/               # Python: bot + API + scheduler (bitta process)
│   ├── app/
│   │   ├── main.py        # kirish nuqtasi (FastAPI + bot + scheduler)
│   │   ├── bot.py         # Telegram bot, Mini App tugmasi
│   │   ├── auth.py        # Telegram initData validatsiyasi (xavfsizlik)
│   │   ├── services.py    # streak, check-in, reyting logikasi
│   │   ├── config.py      # sozlamalar (.env)
│   │   ├── database.py    # SQLAlchemy
│   │   ├── models/models.py
│   │   └── routers/api.py # REST API
│   ├── requirements.txt
│   └── .env.example
└── webapp/                # Mini App frontend (statik: HTML/CSS/JS)
    ├── index.html
    ├── css/style.css
    └── js/{api.js, app.js}
```

## 1. Bot yaratish

1. Telegramda [@BotFather](https://t.me/BotFather) → `/newbot` → token oling.
2. `/newapp` yoki `/setmenubutton` orqali Mini App URL'ni ulang (webapp joylashgan https manzil).

## 2. Backend ishga tushirish

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env      # va ichini to'ldiring (BOT_TOKEN, WEBAPP_URL)
python -m app.main
```

Bu bitta buyruq bot, API (`:8000`) va schedulerni birga ishga tushiradi.

## 3. Frontend deploy (GitHub Pages)

1. `webapp/js/api.js` ichida `API_BASE` ni backend URL'ingizga o'zgartiring.
2. Repozitoriyni GitHub'ga push qiling.
3. Settings → Pages → manba sifatida `main` branch tanlang.
4. Chiqqan URL (`https://username.github.io/intizom/webapp/`) ni `.env` dagi `WEBAPP_URL` ga va BotFather'ga qo'ying.

> Mini App faqat **https** ustida ishlaydi. Backend ham https bo'lishi kerak
> (VPS + nginx + sertifikat, yoki test uchun `cloudflared tunnel` / `ngrok`).

## 4. Test qilish

Botga `/start` → "Ilovani ochish" → challenge tanlash → check-in → reyting.

## Xavfsizlik

- Frontend har so'rovda `X-Init-Data` header yuboradi.
- Backend uni bot token bilan HMAC orqali tekshiradi (`auth.py`).
- Tekshiruvsiz hech kim boshqa foydalanuvchi nomidan check-in qila olmaydi.

## Sozlash

`.env` orqali:
- `CHECKIN_START_HOUR` / `CHECKIN_END_HOUR` — check-in vaqt oynasi (masalan erta turish uchun 5–8).
- `TIMEZONE` — streak hisoblash uchun vaqt mintaqasi.
- Yangi challenge qo'shish: DB'ga `challenges` jadvaliga yozing yoki `services.seed_default_challenges` ni tahrirlang.
