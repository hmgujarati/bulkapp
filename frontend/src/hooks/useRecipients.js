import { useState, useCallback } from 'react';
import { toast } from 'sonner';
import * as XLSX from 'xlsx';

export const useRecipients = () => {
  const [recipients, setRecipients] = useState([]);

  // Parse Excel file
  const parseExcelFile = useCallback(async (file) => {
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

      const formattedRecipients = jsonData.map(row => ({
        phone: String(row[phoneCol] || '').trim(),
        name: row[nameCol] ? String(row[nameCol]).trim() : ''
      })).filter(r => r.phone);

      setRecipients(formattedRecipients);
      toast.success(`Loaded ${formattedRecipients.length} recipients`);
    } catch (error) {
      toast.error('Failed to parse Excel file');
    }
  }, []);

  // Parse text input (comma-separated lines)
  const parseTextInput = useCallback((text) => {
    const lines = text.split('\n').filter(line => line.trim());
    const parsed = lines.map(line => {
      const parts = line.split(',').map(p => p.trim());
      return {
        phone: parts[0] || '',
        name: parts[1] || ''
      };
    }).filter(r => r.phone);

    setRecipients(parsed);
    toast.success(`Loaded ${parsed.length} recipients`);
  }, []);

  // Add country code to all numbers
  const addCountryCode = useCallback((countryCode) => {
    if (!countryCode) {
      toast.error('Please enter a country code');
      return;
    }

    let addedCount = 0;
    let skippedCount = 0;

    const updated = recipients.map(r => {
      const phone = r.phone.trim();
      const digitsOnly = phone.replace(/\D/g, '');

      if (phone.startsWith('+') || digitsOnly.startsWith(countryCode)) {
        skippedCount++;
        return r;
      }

      const cleanPhone = digitsOnly.replace(/^0+/, '');
      addedCount++;
      return { ...r, phone: `+${countryCode}${cleanPhone}` };
    });

    setRecipients(updated);

    if (addedCount > 0) {
      toast.success(`Country code +${countryCode} added to ${addedCount} number(s). ${skippedCount} already had it.`);
    } else {
      toast.info(`All ${skippedCount} numbers already have country code ${countryCode}`);
    }
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

  // Remove a single recipient
  const removeRecipient = useCallback((index) => {
    setRecipients(prev => prev.filter((_, i) => i !== index));
  }, []);

  // Clear all recipients
  const clearRecipients = useCallback(() => {
    setRecipients([]);
  }, []);

  return {
    recipients,
    setRecipients,
    parseExcelFile,
    parseTextInput,
    addCountryCode,
    removeDuplicates,
    removeRecipient,
    clearRecipients
  };
};

export default useRecipients;
