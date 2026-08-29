import React, { useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Upload, Trash2, ShieldCheck, AlertTriangle } from 'lucide-react';
import { useDropzone } from 'react-dropzone';
import { COUNTRY_OPTIONS } from '../../utils/phoneValidator';

const RecipientUploader = ({
  recipients,
  country,
  onCountryChange,
  invalidNumbers = [],
  onParseExcel,
  onParseText,
  onReapplyCountry,
  onRemoveDuplicates,
  onRemoveRecipient,
  onClear
}) => {
  const [textInput, setTextInput] = useState('');
  const [countryQuery, setCountryQuery] = useState('');

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop: (files) => files[0] && onParseExcel(files[0], country),
    accept: {
      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx'],
      'application/vnd.ms-excel': ['.xls'],
      'text/csv': ['.csv']
    },
    multiple: false
  });

  const selected = COUNTRY_OPTIONS.find((c) => c.iso === country);
  const filtered = countryQuery
    ? COUNTRY_OPTIONS.filter((c) =>
        c.name.toLowerCase().includes(countryQuery.toLowerCase()) || c.dial.includes(countryQuery.replace('+', ''))
      )
    : COUNTRY_OPTIONS;

  return (
    <Card data-testid="recipient-uploader">
      <CardHeader>
        <CardTitle className="text-lg flex items-center">
          <Upload className="h-5 w-5 mr-2 text-blue-600" />
          Recipients
        </CardTitle>
        <CardDescription>
          Numbers are checked automatically — the country code is added and invalid numbers are removed
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Country selector — drives the code added to local numbers */}
        <div className="space-y-2">
          <label className="text-sm font-medium text-slate-700">Country of these numbers</label>
          <div className="flex gap-2">
            <Input
              placeholder="Search country or code"
              value={countryQuery}
              onChange={(e) => setCountryQuery(e.target.value)}
              className="w-40"
              data-testid="country-search-input"
            />
            <select
              value={country}
              onChange={(e) => onCountryChange(e.target.value)}
              className="flex-1 h-10 rounded-md border border-slate-200 bg-white px-3 text-sm"
              data-testid="country-select"
            >
              {filtered.map((c) => (
                <option key={c.iso} value={c.iso}>
                  {c.name} (+{c.dial})
                </option>
              ))}
            </select>
          </div>
          <p className="text-xs text-slate-500">
            Local numbers get +{selected?.dial} added automatically. Numbers that already have a
            country code are kept as they are.
          </p>
        </div>

        <Tabs defaultValue="excel">
          <TabsList className="grid w-full grid-cols-2">
            <TabsTrigger value="excel" data-testid="excel-tab">Excel Upload</TabsTrigger>
            <TabsTrigger value="text" data-testid="text-tab">Text Input</TabsTrigger>
          </TabsList>

          <TabsContent value="excel" className="mt-4">
            <div
              {...getRootProps()}
              className={`border-2 border-dashed rounded-lg p-6 text-center cursor-pointer transition-colors
                ${isDragActive ? 'border-blue-500 bg-blue-50' : 'border-slate-300 hover:border-blue-400'}`}
              data-testid="excel-dropzone"
            >
              <input {...getInputProps()} />
              <Upload className="h-8 w-8 mx-auto mb-2 text-slate-400" />
              {isDragActive ? (
                <p className="text-blue-600">Drop the file here...</p>
              ) : (
                <div>
                  <p className="text-slate-600">Drag & drop Excel/CSV file here</p>
                  <p className="text-sm text-slate-400 mt-1">or click to browse</p>
                </div>
              )}
            </div>
            <p className="text-xs text-slate-500 mt-2">
              File should have columns: phone, name (optional)
            </p>
          </TabsContent>

          <TabsContent value="text" className="mt-4 space-y-3">
            <Textarea
              placeholder="Enter phone numbers (one per line)&#10;Format: phone, name (optional)&#10;Example:&#10;9876543210, John&#10;8765432109"
              value={textInput}
              onChange={(e) => setTextInput(e.target.value)}
              rows={5}
              data-testid="text-input"
            />
            <Button onClick={() => onParseText(textInput, country)} variant="outline" className="w-full" data-testid="parse-text-btn">
              Parse Numbers
            </Button>
          </TabsContent>
        </Tabs>

        {invalidNumbers.length > 0 && (
          <div className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm" data-testid="invalid-numbers-alert">
            <p className="flex items-center gap-2 font-medium text-amber-900">
              <AlertTriangle className="h-4 w-4" />
              {invalidNumbers.length} invalid number(s) removed automatically
            </p>
            <p className="mt-1 font-mono text-xs text-amber-800 break-all">
              {invalidNumbers.slice(0, 8).join(', ')}
              {invalidNumbers.length > 8 && ` +${invalidNumbers.length - 8} more`}
            </p>
          </div>
        )}

        {recipients.length > 0 && (
          <div className="space-y-3 pt-4 border-t">
            <div className="flex flex-wrap gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => onReapplyCountry(country)}
                data-testid="reapply-country-btn"
              >
                <ShieldCheck className="h-4 w-4 mr-1" />
                Re-check with +{selected?.dial}
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={onRemoveDuplicates}
                data-testid="remove-duplicates-btn"
              >
                Remove Duplicates
              </Button>
            </div>

            <div className="border rounded-lg max-h-48 overflow-y-auto">
              <table className="w-full text-sm">
                <thead className="bg-slate-50 sticky top-0">
                  <tr>
                    <th className="px-3 py-2 text-left">#</th>
                    <th className="px-3 py-2 text-left">Phone</th>
                    <th className="px-3 py-2 text-left">Name</th>
                    <th className="px-3 py-2 w-10"></th>
                  </tr>
                </thead>
                <tbody>
                  {recipients.slice(0, 100).map((r, i) => (
                    <tr key={i} className="border-t hover:bg-slate-50">
                      <td className="px-3 py-1.5 text-slate-500">{i + 1}</td>
                      <td className="px-3 py-1.5 font-mono text-xs">{r.phone}</td>
                      <td className="px-3 py-1.5">{r.name || '-'}</td>
                      <td className="px-3 py-1.5">
                        <button
                          onClick={() => onRemoveRecipient(i)}
                          className="text-red-500 hover:text-red-700"
                          data-testid={`remove-recipient-${i}`}
                        >
                          <Trash2 className="h-3 w-3" />
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {recipients.length > 100 && (
                <div className="px-3 py-2 text-sm text-slate-500 bg-slate-50 border-t">
                  Showing first 100 of {recipients.length} recipients
                </div>
              )}
            </div>

            <div className="flex justify-between items-center text-sm">
              <span className="text-slate-600">
                Total: <strong data-testid="recipient-count">{recipients.length}</strong> valid recipients
              </span>
              <Button variant="ghost" size="sm" onClick={onClear} className="text-red-500" data-testid="clear-recipients-btn">
                Clear All
              </Button>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
};

export default RecipientUploader;
