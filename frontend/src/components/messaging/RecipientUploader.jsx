import React, { useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Upload, Globe, Trash2 } from 'lucide-react';
import { useDropzone } from 'react-dropzone';

const RecipientUploader = ({
  recipients,
  onParseExcel,
  onParseText,
  onAddCountryCode,
  onRemoveDuplicates,
  onRemoveRecipient,
  onClear
}) => {
  const [textInput, setTextInput] = useState('');
  const [countryCode, setCountryCode] = useState('91');

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop: (files) => files[0] && onParseExcel(files[0]),
    accept: {
      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx'],
      'application/vnd.ms-excel': ['.xls'],
      'text/csv': ['.csv']
    },
    multiple: false
  });

  const handleTextSubmit = () => {
    onParseText(textInput);
  };

  return (
    <Card data-testid="recipient-uploader">
      <CardHeader>
        <CardTitle className="text-lg flex items-center">
          <Upload className="h-5 w-5 mr-2 text-blue-600" />
          Recipients
        </CardTitle>
        <CardDescription>Upload phone numbers to send messages to</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <Tabs defaultValue="excel">
          <TabsList className="grid w-full grid-cols-2">
            <TabsTrigger value="excel">Excel Upload</TabsTrigger>
            <TabsTrigger value="text">Text Input</TabsTrigger>
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
            <Button onClick={handleTextSubmit} variant="outline" className="w-full" data-testid="parse-text-btn">
              Parse Numbers
            </Button>
          </TabsContent>
        </Tabs>

        {/* Country Code & Actions */}
        {recipients.length > 0 && (
          <div className="space-y-3 pt-4 border-t">
            <div className="flex gap-2">
              <div className="flex items-center gap-1">
                <Globe className="h-4 w-4 text-slate-500" />
                <span className="text-sm">+</span>
                <Input
                  type="text"
                  value={countryCode}
                  onChange={(e) => setCountryCode(e.target.value.replace(/\D/g, ''))}
                  className="w-16"
                  placeholder="91"
                  data-testid="country-code-input"
                />
              </div>
              <Button
                variant="outline"
                size="sm"
                onClick={() => onAddCountryCode(countryCode)}
                data-testid="add-country-code-btn"
              >
                Add Code
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

            {/* Recipients List */}
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
                Total: <strong>{recipients.length}</strong> recipients
              </span>
              <Button variant="ghost" size="sm" onClick={onClear} className="text-red-500">
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
