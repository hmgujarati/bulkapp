"""Helper utilities"""
import re
from typing import Optional


def normalize_phone_number(phone: str, country_code: Optional[str] = None) -> str:
    """Normalize a phone number by removing non-digit characters and adding country code"""
    # Remove all non-digit characters
    phone = re.sub(r'\D', '', phone)
    
    # If phone already has a country code (starts with proper length), return as is
    if phone.startswith('1') and len(phone) >= 10:  # US/Canada
        return '+' + phone
    if len(phone) >= 10 and not country_code:
        return '+' + phone
    
    # Add country code if provided and phone doesn't start with it
    if country_code:
        country_code = re.sub(r'\D', '', country_code)
        if not phone.startswith(country_code):
            phone = country_code + phone
    
    return '+' + phone if not phone.startswith('+') else phone
