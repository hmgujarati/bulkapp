import React, { useState, useEffect } from 'react';
import Layout from '../components/Layout';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Progress } from '@/components/ui/progress';
import { Upload, Send, FileText, Calendar, Pause, Play, AlertCircle } from 'lucide-react';
import { useDropzone } from 'react-dropzone';
import { toast } from 'sonner';
import * as XLSX from 'xlsx';
import api from '../utils/api';
import { useNavigate } from 'react-router-dom';

const SendMessagesNew = ({ user, onLogout }) => {
  const navigate = useNavigate();
  const [templates, setTemplates] = useState([]);
  const [selectedTemplate, setSelectedTemplate] = useState('');
  const [campaignName, setCampaignName] = useState('');
  const [countryCode, setCountryCode] = useState('+1');
  const [recipients, setRecipients] = useState([]);
  const [textInput, setTextInput] = useState('');
  const [scheduledDate, setScheduledDate] = useState('');
  const [loading, setLoading] = useState(false);
  const [sending, setSending] = useState(false);
  
  // Template mode: 'fetch' or 'manual'
  const [templateMode, setTemplateMode] = useState('manual');
  const [manualTemplateName, setManualTemplateName] = useState('');
  const [templateLanguage, setTemplateLanguage] = useState('en');
  
  // Template parameters - can be global or column-mapped
  const [paramMode, setParamMode] = useState('global'); // 'global' or 'mapped'
  const [templateParams, setTemplateParams] = useState({
    field_1: '',
    field_2: '',
    field_3: '',
    field_4: '',
    field_5: '',
    header_image: '',
    header_video: '',
    header_document: '',
    button_0: '',
    button_1: ''
  });
  const [excelColumns, setExcelColumns] = useState([]);
  const [columnMapping, setColumnMapping] = useState({});

  useEffect(() => {
    fetchTemplates();
  }, []);

  const fetchTemplates = async () => {
    setLoading(true);
    try {
      const response = await api.get('/templates');
      if (response.data.templates) {
        setTemplates(response.data.templates);
      }
    } catch (error) {
      if (error.response?.status === 400) {
        toast.error('Please configure your BizChat API credentials in Settings first');
      } else {
        toast.error('Failed to fetch templates');
      }
    } finally {
      setLoading(false);
    }
  };

  const onDrop = async (acceptedFiles) => {
    const file = acceptedFiles[0];
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

      // Get column names
      const columns = Object.keys(jsonData[0]);
      setExcelColumns(columns);

      // Auto-detect phone and name columns
      const phoneCol = columns.find(c => c.toLowerCase().includes('phone'));
      const nameCol = columns.find(c => c.toLowerCase().includes('name'));

      if (!phoneCol) {
        toast.error('Could not find phone column. Please ensure your Excel has a "phone" column');
        return;
      }

      // Format recipients with all columns
      const formattedRecipients = jsonData.map(row => {
        const recipient = {};
        columns.forEach(col => {
          recipient[col] = row[col];
        });
        return recipient;
      }).filter(r => r[phoneCol]);

      setRecipients(formattedRecipients);
      toast.success(`Loaded ${formattedRecipients.length} recipients with ${columns.length} columns`);
    } catch (error) {
      toast.error('Failed to parse Excel file');
    }
  };

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx'],
      'application/vnd.ms-excel': ['.xls'],
      'text/csv': ['.csv']
    },
    multiple: false
  });

  const handleTextInput = () => {
    const lines = textInput.split('\n').filter(line => line.trim());
    const parsed = lines.map(line => {
      const parts = line.split(',').map(p => p.trim());
      return {
        phone: parts[0] || '',
        name: parts[1] || '',
        field_1: parts[2] || '',
        field_2: parts[3] || '',
        field_3: parts[4] || '',
      };
    }).filter(r => r.phone);

    setRecipients(parsed);
    setExcelColumns(['phone', 'name', 'field_1', 'field_2', 'field_3']);
    toast.success(`Loaded ${parsed.length} recipients`);
  };

  const handleSend = async (isScheduled = false) => {
    if (!campaignName) {
      toast.error('Please enter a campaign name');
      return;
    }
    
    // Check template based on mode
    const templateName = templateMode === 'manual' ? manualTemplateName : selectedTemplate;
    if (!templateName) {
      toast.error('Please enter or select a template name');
      return;
    }
    
    if (recipients.length === 0) {
      toast.error('Please add recipients');
      return;
    }
    if (isScheduled && !scheduledDate) {
      toast.error('Please select a schedule date');
      return;
    }

    setSending(true);
    try {
      // Apply country code and template parameters to all recipients
      const recipientsWithData = recipients.map(r => {
        const recipientData = {
          phone: r.phone.startsWith('+') ? r.phone : `${countryCode}${r.phone}`,
          name: r.name || '',
          template_language: templateLanguage
        };
        
        // If using global parameters, apply to all recipients
        if (paramMode === 'global') {
          Object.keys(templateParams).forEach(key => {
            if (templateParams[key]) {
              recipientData[key] = templateParams[key];
            }
          });
        } else {
          // If using column mapping, get values from recipient's Excel data
          Object.keys(columnMapping).forEach(paramKey => {
            const columnName = columnMapping[paramKey];
            if (columnName && r[columnName]) {
              recipientData[paramKey] = r[columnName];
            }
          });
        }
        
        return recipientData;
      });

      const payload = {
        campaignName,
        templateName: templateName,
        recipients: recipientsWithData,
        countryCode: null, // Already applied above
        scheduledAt: isScheduled ? new Date(scheduledDate).toISOString() : null
      };

      const response = await api.post('/messages/send', payload);
      toast.success(
        isScheduled 
          ? 'Campaign scheduled successfully!' 
          : `Campaign started! ${response.data.dailyUsage}/${response.data.dailyLimit} messages used today`
      );
      navigate(`/campaigns/${response.data.campaignId}`);
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to send messages');
    } finally {
      setSending(false);
    }
  };

  const renderTemplateParameterInputs = () => {
    if (!selectedTemplate) return null;

    return (
      <div className="space-y-4">
        <h4 className="font-medium text-slate-900">Template Parameters</h4>
        <p className="text-sm text-slate-600">
          Map your Excel columns to template fields. Use column names from your uploaded file.
        </p>
        
        {excelColumns.length > 0 && (
          <div className="bg-blue-50 p-3 rounded-lg">
            <p className="text-sm font-medium text-blue-900 mb-2">Available columns:</p>
            <div className="flex flex-wrap gap-2">
              {excelColumns.map(col => (
                <span key={col} className="px-2 py-1 bg-blue-100 text-blue-800 text-xs rounded">
                  {col}
                </span>
              ))}
            </div>
          </div>
        )}

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {['field_1', 'field_2', 'field_3', 'field_4', 'field_5'].map((field, idx) => (
            <div key={field} className="space-y-2">
              <Label htmlFor={field}>Body Field {idx + 1}</Label>
              <Input
                id={field}
                placeholder={`Column name for ${field} (e.g., first_name)`}
                value={templateParams[field] || ''}
                onChange={(e) => setTemplateParams({...templateParams, [field]: e.target.value})}
              />
            </div>
          ))}

          <div className="space-y-2">
            <Label htmlFor="header_image">Header Image URL</Label>
            <Input
              id="header_image"
              placeholder="https://example.com/image.jpg"
              value={templateParams.header_image || ''}
              onChange={(e) => setTemplateParams({...templateParams, header_image: e.target.value})}
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="header_video">Header Video URL</Label>
            <Input
              id="header_video"
              placeholder="https://example.com/video.mp4"
              value={templateParams.header_video || ''}
              onChange={(e) => setTemplateParams({...templateParams, header_video: e.target.value})}
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="button_0">Button 0 Parameter</Label>
            <Input
              id="button_0"
              placeholder="Column name for button"
              value={templateParams.button_0 || ''}
              onChange={(e) => setTemplateParams({...templateParams, button_0: e.target.value})}
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="button_1">Button 1 Parameter</Label>
            <Input
              id="button_1"
              placeholder="Column name for button"
              value={templateParams.button_1 || ''}
              onChange={(e) => setTemplateParams({...templateParams, button_1: e.target.value})}
            />
          </div>
        </div>
      </div>
    );
  };

  return (
    <Layout user={user} onLogout={onLogout}>
      <div className="space-y-6">
        <div>
          <h1 className="text-3xl sm:text-4xl font-bold text-slate-900">Send Messages</h1>
          <p className="text-slate-600 mt-1">Create and send bulk WhatsApp campaigns with dynamic templates</p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Configuration Section */}
          <div className="lg:col-span-2 space-y-6">
            {/* Campaign Details */}
            <Card className="shadow-lg border-0">
              <CardHeader>
                <CardTitle>Campaign Details</CardTitle>
                <CardDescription>Configure your campaign settings</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="campaignName">Campaign Name</Label>
                  <Input
                    id="campaignName"
                    placeholder="e.g., Holiday Promotion 2025"
                    value={campaignName}
                    onChange={(e) => setCampaignName(e.target.value)}
                    data-testid="campaign-name-input"
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="template">WhatsApp Template</Label>
                  <Select value={selectedTemplate} onValueChange={setSelectedTemplate}>
                    <SelectTrigger data-testid="template-select">
                      <SelectValue placeholder="Select a template" />
                    </SelectTrigger>
                    <SelectContent>
                      {loading ? (
                        <SelectItem value="loading" disabled>Loading templates...</SelectItem>
                      ) : templates.length === 0 ? (
                        <SelectItem value="none" disabled>No templates available</SelectItem>
                      ) : (
                        templates.map((template) => (
                          <SelectItem key={template.name} value={template.name}>
                            {template.name}
                          </SelectItem>
                        ))
                      )}
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="countryCode">Country Code</Label>
                  <Input
                    id="countryCode"
                    placeholder="e.g., +1, +91"
                    value={countryCode}
                    onChange={(e) => setCountryCode(e.target.value)}
                    data-testid="country-code-input"
                  />
                  <p className="text-xs text-slate-500">
                    Will be added to numbers that don't start with +
                  </p>
                </div>
              </CardContent>
            </Card>

            {/* Template Parameters */}
            {selectedTemplate && (
              <Card className="shadow-lg border-0">
                <CardHeader>
                  <CardTitle>Template Configuration</CardTitle>
                  <CardDescription>Configure dynamic fields for your template</CardDescription>
                </CardHeader>
                <CardContent>
                  {renderTemplateParameterInputs()}
                </CardContent>
              </Card>
            )}

            {/* Recipients */}
            <Card className="shadow-lg border-0">
              <CardHeader>
                <CardTitle>Add Recipients</CardTitle>
                <CardDescription>Upload Excel file or paste numbers</CardDescription>
              </CardHeader>
              <CardContent>
                <Tabs defaultValue="upload" className="w-full">
                  <TabsList className="grid w-full grid-cols-2">
                    <TabsTrigger value="upload">Upload File</TabsTrigger>
                    <TabsTrigger value="paste">Paste Numbers</TabsTrigger>
                  </TabsList>

                  <TabsContent value="upload" className="space-y-4">
                    <div
                      {...getRootProps()}
                      className={`border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors ${
                        isDragActive ? 'border-blue-500 bg-blue-50' : 'border-slate-300 hover:border-blue-400'
                      }`}
                      data-testid="file-dropzone"
                    >
                      <input {...getInputProps()} />
                      <Upload className="h-12 w-12 text-slate-400 mx-auto mb-4" />
                      {isDragActive ? (
                        <p className="text-blue-600">Drop the file here...</p>
                      ) : (
                        <div>
                          <p className="text-slate-700 font-medium mb-2">
                            Drag & drop an Excel file here, or click to select
                          </p>
                          <p className="text-sm text-slate-500">
                            Supports .xlsx, .xls, .csv files
                          </p>
                        </div>
                      )}
                    </div>
                    <div className="bg-amber-50 border border-amber-200 rounded-lg p-3">
                      <p className="text-sm text-amber-900">
                        <strong>Tip:</strong> Include columns like: phone, name, field_1, field_2, etc.
                        All columns will be available for template mapping.
                      </p>
                    </div>
                  </TabsContent>

                  <TabsContent value="paste" className="space-y-4">
                    <Textarea
                      placeholder="Paste data (one per line, comma-separated)&#10;Format: phone, name, field1, field2, field3&#10;Example:&#10;+1234567890, John Doe, Value1, Value2, Value3&#10;+9876543210, Jane Smith, ValueA, ValueB, ValueC"
                      rows={8}
                      value={textInput}
                      onChange={(e) => setTextInput(e.target.value)}
                      data-testid="text-input-textarea"
                    />
                    <Button onClick={handleTextInput} className="w-full" data-testid="parse-text-button">
                      Parse Data
                    </Button>
                  </TabsContent>
                </Tabs>
              </CardContent>
            </Card>

            {/* Schedule */}
            <Card className="shadow-lg border-0">
              <CardHeader>
                <CardTitle>Schedule (Optional)</CardTitle>
                <CardDescription>Send messages at a specific time</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  <Label htmlFor="scheduledDate">Schedule Date & Time</Label>
                  <Input
                    id="scheduledDate"
                    type="datetime-local"
                    value={scheduledDate}
                    onChange={(e) => setScheduledDate(e.target.value)}
                    data-testid="schedule-datetime-input"
                  />
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Preview Section */}
          <div className="space-y-6">
            <Card className="shadow-lg border-0 sticky top-24">
              <CardHeader>
                <CardTitle>Campaign Summary</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div>
                  <p className="text-sm text-slate-600">Recipients</p>
                  <p className="text-2xl font-bold text-slate-900">{recipients.length}</p>
                </div>

                <div>
                  <p className="text-sm text-slate-600">Template</p>
                  <p className="font-medium text-slate-900">{selectedTemplate || 'Not selected'}</p>
                </div>

                <div>
                  <p className="text-sm text-slate-600">Rate Limit</p>
                  <p className="text-sm font-medium text-slate-900">29 messages/second</p>
                  <p className="text-xs text-slate-500 mt-1">
                    Est. time: ~{Math.ceil(recipients.length / 29)} seconds
                  </p>
                </div>

                {recipients.length > 0 && (
                  <div>
                    <p className="text-sm text-slate-600 mb-2">Preview Recipients</p>
                    <div className="bg-slate-50 rounded-lg p-3 max-h-48 overflow-y-auto">
                      {recipients.slice(0, 5).map((r, i) => (
                        <div key={i} className="text-sm py-1">
                          <span className="font-medium">{r.name || 'No name'}</span>
                          <span className="text-slate-500 ml-2">{r.phone}</span>
                        </div>
                      ))}
                      {recipients.length > 5 && (
                        <p className="text-xs text-slate-500 mt-2">+{recipients.length - 5} more</p>
                      )}
                    </div>
                  </div>
                )}

                <div className="space-y-2 pt-4">
                  <Button
                    onClick={() => handleSend(false)}
                    disabled={sending || recipients.length === 0}
                    className="w-full bg-blue-600 hover:bg-blue-700"
                    data-testid="send-now-button"
                  >
                    <Send className="h-4 w-4 mr-2" />
                    {sending ? 'Sending...' : 'Send Now'}
                  </Button>

                  {scheduledDate && (
                    <Button
                      onClick={() => handleSend(true)}
                      disabled={sending || recipients.length === 0}
                      variant="outline"
                      className="w-full"
                      data-testid="schedule-button"
                    >
                      <Calendar className="h-4 w-4 mr-2" />
                      Schedule Campaign
                    </Button>
                  )}
                </div>

                {recipients.length > 10000 && (
                  <div className="bg-blue-50 border border-blue-200 rounded-lg p-3">
                    <AlertCircle className="h-4 w-4 text-blue-600 inline mr-2" />
                    <span className="text-sm text-blue-900">
                      Large campaign detected! Processing will be done in batches with real-time progress tracking.
                    </span>
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    </Layout>
  );
};

export default SendMessagesNew;
