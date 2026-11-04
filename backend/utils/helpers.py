"""Helper utilities"""
import re
from typing import Optional

import phonenumbers


def _region_for_dial_code(country_code: Optional[str]) -> Optional[str]:
    cc = re.sub(r'\D', '', country_code or '')
    if not cc:
        return None
    try:
        region = phonenumbers.region_code_for_country_code(int(cc))
    except (ValueError, TypeError):
        return None
    return region if region and region != 'ZZ' else None


def normalize_phone_number(phone: str, country_code: Optional[str] = None) -> str:
    """Normalize to E.164.

    A list can legitimately mix countries, so a number that already carries its
    own country code must never get the selected dial code prefixed on top of it
    (that was turning +971... into +91971...). The selected country is only used
    for numbers typed in local/national form.
    """
    digits = re.sub(r'\D', '', phone or '')
    if not digits:
        return ''

    # 00 is the international access prefix — strip it, it means "+"
    if digits.startswith('00'):
        digits = digits[2:]
    if not digits:
        return ''

    region = _region_for_dial_code(country_code)

    # 1. Local number of the selected country (e.g. 9876543210 with +91)
    if region:
        try:
            parsed = phonenumbers.parse(digits.lstrip('0'), region)
            if (phonenumbers.is_valid_number(parsed)
                    and phonenumbers.region_code_for_number(parsed) == region):
                return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
        except phonenumbers.NumberParseException:
            pass

    # 2. Already an international number of some other country (+971..., +44..., +1...)
    try:
        parsed = phonenumbers.parse('+' + digits, None)
        if phonenumbers.is_valid_number(parsed):
            return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
    except phonenumbers.NumberParseException:
        pass

    # 3. Last resort — keep the old behaviour so nothing silently disappears
    cc = re.sub(r'\D', '', country_code or '')
    if not cc or digits.startswith(cc):
        return '+' + digits
    if len(digits.lstrip('0')) > 10:
        return '+' + digits.lstrip('0')
    return '+' + cc + digits.lstrip('0')
