"""Helper utilities"""
import re
from typing import Optional


def normalize_phone_number(phone: str, country_code: Optional[str] = None) -> str:
    """Normalize to E.164. Adds the country code only when the number is a local number.

    `digits.startswith(country_code)` alone is unreliable — an Indian mobile like
    9198765432 legitimately starts with 91 — so length is checked too.
    """
    digits = re.sub(r'\D', '', phone or '')
    if not digits:
        return ''

    cc = re.sub(r'\D', '', country_code or '')
    if not cc:
        return '+' + digits

    # Already international (country code + a full national number)
    if digits.startswith(cc) and len(digits) > 10:
        return '+' + digits

    return '+' + cc + digits.lstrip('0')
