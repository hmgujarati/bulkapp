import { parsePhoneNumberFromString, getCountries, getCountryCallingCode } from 'libphonenumber-js';

const regionNames = typeof Intl !== 'undefined' && Intl.DisplayNames
  ? new Intl.DisplayNames(['en'], { type: 'region' })
  : null;

const PRIORITY = ['IN', 'AE', 'US', 'GB', 'SA', 'SG', 'AU', 'CA'];

export const COUNTRY_OPTIONS = (() => {
  const all = getCountries().map((iso) => ({
    iso,
    dial: getCountryCallingCode(iso),
    name: regionNames?.of(iso) || iso,
  }));
  all.sort((a, b) => a.name.localeCompare(b.name));
  const priority = PRIORITY.map((iso) => all.find((c) => c.iso === iso)).filter(Boolean);
  const rest = all.filter((c) => !PRIORITY.includes(c.iso));
  return [...priority, ...rest];
})();

export const dialCodeFor = (iso) => {
  const found = COUNTRY_OPTIONS.find((c) => c.iso === iso);
  return found ? found.dial : '';
};

/**
 * Returns the number in E.164 (with +) or null when it can't be a real number.
 * Tries the raw digits as an international number first, then as a national
 * number of the selected country (so 10-digit Indian numbers get +91).
 */
export const normalizePhone = (raw, countryIso = 'IN') => {
  const cleaned = String(raw ?? '').replace(/[^\d+]/g, '');
  if (!cleaned) return null;

  // A local number of the selected country wins over a coincidental
  // international match (e.g. 5012345678 in AE is not Belize).
  if (!cleaned.startsWith('+')) {
    const national = parsePhoneNumberFromString(cleaned.replace(/^0+/, ''), countryIso);
    if (national?.isValid() && national.country === countryIso) return national.number;
  }

  const withPlus = cleaned.startsWith('+') ? cleaned : `+${cleaned}`;
  const asInternational = parsePhoneNumberFromString(withPlus);
  if (asInternational?.isValid()) return asInternational.number;

  return null;
};

/** Normalizes a recipient list, dropping numbers that can never be delivered. */
export const processRecipients = (list, countryIso = 'IN') => {
  const valid = [];
  const invalid = [];
  list.forEach((r) => {
    const phone = normalizePhone(r.phone, countryIso);
    if (phone) valid.push({ ...r, phone: phone.replace('+', '') });
    else if (String(r.phone ?? '').trim()) invalid.push(String(r.phone).trim());
  });
  return { valid, invalid };
};
