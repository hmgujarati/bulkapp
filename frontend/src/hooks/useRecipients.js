import { useState, useCallback } from 'react';
import { toast } from 'sonner';
import * as XLSX from 'xlsx';
import { processRecipients } from '../utils/phoneValidator';

export const useRecipients = () => {
  const [recipients, setRecipients] = useState([]);
  const [country, setCountry] = useState('IN');
  const [invalidNumbers, setInvalidNumbers] = useState([]);

  // Normalize + drop numbers that can never be delivered
  const applyList = useCallback((list, countryIso) => {
    const { valid, invalid } = processRecipients(list, countryIso);
    setRecipients(valid);
    setInvalidNumbers(invalid);

    if (invalid.length > 0) {
      toast.success(`Loaded ${valid.length} valid recipients. Removed ${invalid.length} invalid number(s).`);
    } else {
      toast.success(`Loaded ${valid.length} recipients`);
    }
    return valid;
  }, []);

  // Parse Excel file
  const parseExcelFile = useCallback(async (file, countryIso = country) => {
    if (!file) return;

    try {
      const data = await file.arrayBuffer();
      const workbook = XLSX.read(data);
      const worksheet = workbook.Sheets[workbook.SheetNames[0]];
      const jsonData = XLSX.utils.sheet_to_json(worksheet);

      if (jsonData.length === 0) {
        toast.error('Excel file is empty');
        return;
      }

      const columns = Object.keys(jsonData[0]);
      const phoneCol = columns.find(c => c.toLowerCase().includes('phone'));
      const nameCol = columns.find(c => c.toLowerCase().includes('name'));

      if (!phoneCol) {
        toast.error('Could not find phone column');
        return;
      }

      const rows = jsonData.map(row => ({
        phone: String(row[phoneCol] || '').trim(),
        name: row[nameCol] ? String(row[nameCol]).trim() : ''
      })).filter(r => r.phone);

      applyList(rows, countryIso);
    } catch (error) {
      toast.error('Failed to parse Excel file');
    }
  }, [applyList, country]);

  // Parse text input (one number per line, optional ", name")
  const parseTextInput = useCallback((text, countryIso = country) => {
    const rows = text.split('\n').filter(line => line.trim()).map(line => {
      const parts = line.split(',').map(p => p.trim());
      return { phone: parts[0] || '', name: parts[1] || '' };
    }).filter(r => r.phone);

    applyList(rows, countryIso);
  }, [applyList, country]);

  // Re-apply country code / validation to the current list (e.g. after changing country)
  const reapplyCountry = useCallback((countryIso) => {
    if (recipients.length === 0) {
      toast.error('Add some numbers first');
      return;
    }
    const { valid, invalid } = processRecipients(recipients, countryIso);
    setRecipients(valid);
    setInvalidNumbers(invalid);
    toast.success(
      invalid.length > 0
        ? `${valid.length} numbers fixed for the selected country. Removed ${invalid.length} invalid.`
        : `All ${valid.length} numbers are valid for the selected country`
    );
  }, [recipients]);

  // Remove duplicates
  const removeDuplicates = useCallback(() => {
    const seen = new Set();
    const unique = recipients.filter(r => {
      const phone = r.phone.replace(/\D/g, '');
      if (seen.has(phone)) return false;
      seen.add(phone);
      return true;
    });

    const removed = recipients.length - unique.length;
    setRecipients(unique);
    toast.success(`Removed ${removed} duplicate(s). ${unique.length} unique recipients.`);
  }, [recipients]);

  const removeRecipient = useCallback((index) => {
    setRecipients(prev => prev.filter((_, i) => i !== index));
  }, []);

  const clearRecipients = useCallback(() => {
    setRecipients([]);
    setInvalidNumbers([]);
  }, []);

  return {
    recipients,
    setRecipients,
    country,
    setCountry,
    invalidNumbers,
    parseExcelFile,
    parseTextInput,
    reapplyCountry,
    removeDuplicates,
    removeRecipient,
    clearRecipients
  };
};

export default useRecipients;
