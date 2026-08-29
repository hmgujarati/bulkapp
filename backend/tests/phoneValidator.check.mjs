import { normalizePhone, processRecipients, dialCodeFor, COUNTRY_OPTIONS } from '/app/frontend/src/utils/phoneValidator.js';
const cases = [
 ['9876543210','IN'], ['919876543210','IN'], ['+91 98765 43210','IN'], ['09876543210','IN'],
 ['12345','IN'], ['abcd','IN'], ['','IN'], ['9198765432','IN'],
 ['5012345678','AE'], ['971501234567','AE'], ['2025550123','US'], ['00000','IN']
];
for (const [p,c] of cases) console.log(JSON.stringify(p), c, '->', normalizePhone(p,c));
const {valid, invalid} = processRecipients([{phone:'9876543210'},{phone:'123'},{phone:'+919812345678'},{phone:'hello'}], 'IN');
console.log('valid', valid, 'invalid', invalid);
console.log('dial IN', dialCodeFor('IN'), 'countries', COUNTRY_OPTIONS.length, COUNTRY_OPTIONS.slice(0,3));
