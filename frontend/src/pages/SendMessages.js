import React, { useState, useEffect } from 'react';
import Layout from '../components/Layout';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Upload, Send, FileText, Calendar } from 'lucide-react';
import { useDropzone } from 'react-dropzone';
import { toast } from 'sonner';
import * as XLSX from 'xlsx';
import api from '../utils/api';
import { useNavigate } from 'react-router-dom';

const SendMessages = ({ user, onLogout }) => {
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
        toast.error('Please configure your BizChat API token in Settings first');
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

      const formattedRecipients = jsonData.map(row => ({
        phone: row.phone || row.Phone || row.PHONE || '',
        name: row.name || row.Name || row.NAME || ''
      })).filter(r => r.phone);

      setRecipients(formattedRecipients);
      toast.success(`Loaded ${formattedRecipients.length} recipients`);
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
        name: parts[1] || ''
      };
    }).filter(r => r.phone);

    setRecipients(parsed);
    toast.success(`Loaded ${parsed.length} recipients`);
  };

  const handleSend = async (isScheduled = false) => {
    if (!campaignName) {
      toast.error('Please enter a campaign name');
      return;
    }
    if (!selectedTemplate) {
      toast.error('Please select a template');
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
      const payload = {
        campaignName,
        templateName: selectedTemplate,
        recipients,
        countryCode: countryCode || null,
        scheduledAt: isScheduled ? new Date(scheduledDate).toISOString() : null
      };

      const response = await api.post('/messages/send', payload);
      toast.success(isScheduled ? 'Campaign scheduled successfully!' : 'Campaign started successfully!');
      navigate(`/campaigns/${response.data.campaignId}`);
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to send messages');
    } finally {
      setSending(false);
    }
  };

  return (
    <Layout user={user} onLogout={onLogout}>
      <div className="space-y-6">
        <div>
          <h1 className="text-3xl sm:text-4xl font-bold text-slate-900">Send Messages</h1>
          <p className="text-slate-600 mt-1">Create and send bulk WhatsApp campaigns</p>
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
                  <Label htmlFor="countryCode">Country Code (Optional)</Label>
                  <Input
                    id="countryCode"
                    placeholder="e.g., +1, +91"
                    value={countryCode}
                    onChange={(e) => setCountryCode(e.target.value)}
                    data-testid="country-code-input"
                  />
                  <p className="text-xs text-slate-500">
                    Will be added to numbers that don't have a country code
                  </p>
                </div>
              </CardContent>
            </Card>

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
                    <p className="text-sm text-slate-500">
                      <strong>Expected columns:</strong> phone, name
                    </p>
                  </TabsContent>

                  <TabsContent value="paste" className="space-y-4">
                    <Textarea
                      placeholder="Paste phone numbers (one per line)&#10;Format: phone, name&#10;Example:&#10;+1234567890, John Doe&#10;+9876543210, Jane Smith"
                      rows={8}
                      value={textInput}
                      onChange={(e) => setTextInput(e.target.value)}
                      data-testid="text-input-textarea"
                    />
                    <Button onClick={handleTextInput} className="w-full" data-testid="parse-text-button">
                      Parse Numbers
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
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    </Layout>
  );
};

export default SendMessages;