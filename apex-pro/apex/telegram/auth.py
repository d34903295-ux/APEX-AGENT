"""Telegram access control: user whitelist + TOTP-style second factor.

A pure-python TOTP (RFC 6238) so we don't add a dependency. Pair the
TELEGRAM_2FA_SECRET (base32) with any authenticator app (Google Authenticator,
Aegis, etc.) to gate dangerous commands (withdraw, go-live, degen).
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import struct
import time

from apex.config import get_settings


def is_whitelisted(user_id: int) -> bool:
    allowed = get_settings().telegram_allowed_ids
    # If no whitelist is configured, deny everyone (fail closed).
    return bool(allowed) and user_id in allowed


def _totp(secret_b32: str, when: int | None = None, step: int = 30, digits: int = 6) -> str:
    key = base64.b32decode(secret_b32.upper() + "=" * (-len(secret_b32) % 8))
    counter = int((when or time.time()) // step)
    msg = struct.pack(">Q", counter)
    digest = hmac.new(key, msg, hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    code = (struct.unpack(">I", digest[offset:offset + 4])[0] & 0x7FFFFFFF) % (10 ** digits)
    return str(code).zfill(digits)


def verify_2fa(code: str) -> bool:
    secret = get_settings().telegram_2fa_secret
    if not secret:
        # No 2FA configured -> treat as not-verified for dangerous ops.
        return False
    code = code.strip()
    now = int(time.time())
    # Accept current and adjacent windows for clock skew.
    return any(_totp(secret, now + drift) == code for drift in (-30, 0, 30))
