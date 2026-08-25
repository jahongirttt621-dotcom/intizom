"""
Telegram Mini App initData validatsiyasi.

Mini App frontend har so'rovda `initData` string yuboradi. Uni server tomonda
bot token bilan tekshirish SHART — aks holda istalgan odam soxta telegram_id
yuborib boshqa odam nomidan check-in qilishi mumkin.

Rasmiy algoritm:
https://core.telegram.org/bots/webapps#validating-data-received-via-the-mini-app
"""

import hashlib
import hmac
import json
import time
from urllib.parse import parse_qsl

from app.config import settings

# initData qancha vaqt amal qiladi (sekund). 24 soat.
_MAX_AGE_SECONDS = 86400


def _secret_key(bot_token: str) -> bytes:
    """WebApp uchun secret key = HMAC_SHA256(bot_token, key='WebAppData')."""
    return hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()


def validate_init_data(init_data: str) -> dict:
    """
    initData string'ni tekshiradi va tekshiruvdan o'tsa `user` dict'ni qaytaradi.

    Xato bo'lsa ValueError ko'taradi.
    """
    if not init_data:
        raise ValueError("initData bo'sh")

    # query-string ko'rinishida: "user=...&auth_date=...&hash=..."
    parsed = dict(parse_qsl(init_data, keep_blank_values=True))

    received_hash = parsed.pop("hash", None)
    if not received_hash:
        raise ValueError("hash mavjud emas")

    # data_check_string: kalitlar alfavit tartibida, "key=value" satrlar \n bilan
    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(parsed.items()))

    secret = _secret_key(settings.BOT_TOKEN)
    computed_hash = hmac.new(secret, data_check_string.encode(), hashlib.sha256).hexdigest()

    # hmac.compare_digest — timing attack'dan himoya
    if not hmac.compare_digest(computed_hash, received_hash):
        raise ValueError("hash mos kelmadi — soxta yoki buzilgan initData")

    # auth_date eskirganini tekshirish (replay attack'dan himoya)
    auth_date = int(parsed.get("auth_date", "0"))
    if time.time() - auth_date > _MAX_AGE_SECONDS:
        raise ValueError("initData eskirgan")

    user_raw = parsed.get("user")
    if not user_raw:
        raise ValueError("user ma'lumoti yo'q")

    return json.loads(user_raw)
