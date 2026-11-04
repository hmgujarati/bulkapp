// WhatsApp/Meta rejects template parameters containing newlines, tabs or 4+
// consecutive spaces, so variable fields must stay single-line.
export const sanitizeTemplateField = (value) =>
  String(value ?? '')
    .replace(/[\r\n\t]+/g, ' ')
    .replace(/ {4,}/g, ' ');
