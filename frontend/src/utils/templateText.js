// WhatsApp/Meta rejects template parameters containing newlines, tabs or 4+
// consecutive spaces, so variable fields must stay single-line.
export const sanitizeTemplateField = (value) =>
  String(value ?? '')
    .replace(/[\r\n\t]+/g, ' ')
    .replace(/ {4,}/g, ' ');

export const MAX_TEMPLATE_FIELDS = 15;
export const MIN_TEMPLATE_FIELDS = 5;
export const FIELD_NUMBERS = Array.from({ length: MAX_TEMPLATE_FIELDS }, (_, i) => i + 1);

export const emptyFields = () =>
  Object.fromEntries(FIELD_NUMBERS.map(i => [`field${i}`, '']));

export const fieldsFromTemplate = (template) =>
  Object.fromEntries(FIELD_NUMBERS.map(i => [`field${i}`, template?.[`field${i}`] || '']));

// Highest field number that has a value (0 if none)
export const highestFilledField = (fields) =>
  FIELD_NUMBERS.reduce((max, i) => (String(fields?.[`field${i}`] || '').trim() ? i : max), 0);

// Highest {{n}} placeholder in a BizChat template's body (null if unknown)
export const countTemplateVariables = (components) => {
  let comps = components;
  if (typeof comps === 'string') {
    try { comps = JSON.parse(comps); } catch { /* scan raw text below */ }
  }
  let text = '';
  if (Array.isArray(comps)) {
    const body = comps.filter(c => String(c?.type || '').toLowerCase() === 'body');
    text = (body.length ? body : comps).map(c => c?.text || '').join(' ');
  } else if (typeof comps === 'string') {
    text = comps;
  }
  const nums = [...text.matchAll(/\{\{\s*(\d+)\s*\}\}/g)].map(m => Number(m[1]));
  return nums.length ? Math.min(Math.max(...nums), MAX_TEMPLATE_FIELDS) : null;
};
