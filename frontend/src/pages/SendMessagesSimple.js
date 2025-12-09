import React, { useState, useEffect } from 'react';
import Layout from '../components/Layout';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Upload, Send, Calendar, Trash2, Globe, AlertCircle } from 'lucide-react';
import { useDropzone } from 'react-dropzone';
import { toast } from 'sonner';
import * as XLSX from 'xlsx';
import api from '../utils/api';
import { useNavigate } from 'react-router-dom';

const SendMessagesSimple = ({ user, onLogout }) => {
  const navigate = useNavigate();
  
  // Campaign fields
  const [campaignName, setCampaignName] = useState('');
  const [templateName, setTemplateName] = useState('');
  const [templateLanguage, setTemplateLanguage] = useState('en');
  
  // Saved templates
  const [savedTemplates, setSavedTemplates] = useState([]);
  const [selectedSavedTemplate, setSelectedSavedTemplate] = useState('');
  
  // Template fields
  const [field1, setField1] = useState('');
  const [field2, setField2] = useState('');
  const [field3, setField3] = useState('');
  const [field4, setField4] = useState('');
  const [field5, setField5] = useState('');
  
  // Media fields
  const [headerImage, setHeaderImage] = useState('');
  const [headerVideo, setHeaderVideo] = useState('');
  const [headerDocument, setHeaderDocument] = useState('');
  const [headerDocumentName, setHeaderDocumentName] = useState('');
  const [headerField1, setHeaderField1] = useState('');
  const [uploading, setUploading] = useState(false);
  
  // Location fields
  const [locationLatitude, setLocationLatitude] = useState('');
  const [locationLongitude, setLocationLongitude] = useState('');
  const [locationName, setLocationName] = useState('');
  const [locationAddress, setLocationAddress] = useState('');
  
  // Recipients
  const [recipients, setRecipients] = useState([]);
  const [textInput, setTextInput] = useState('');
  const [countryCode, setCountryCode] = useState('91');
  
  // Schedule
  const [scheduledDate, setScheduledDate] = useState('');
  const [sending, setSending] = useState(false);

  useEffect(() => {
    fetchSavedTemplates();
  }, []);

  const fetchSavedTemplates = async () => {
    try {
      const response = await api.get('/saved-templates');
      setSavedTemplates(response.data.templates);
    } catch (error) {
      console.error('Failed to fetch saved templates');
    }
  };

  const handleLoadTemplate = (templateId) => {
    const template = savedTemplates.find(t => t.id === templateId);
    if (template) {
      setSelectedSavedTemplate(templateId);
      setTemplateName(template.templateName);
      setTemplateLanguage(template.templateLanguage);
      setField1(template.field1 || '');
      setField2(template.field2 || '');
      setField3(template.field3 || '');
      setField4(template.field4 || '');
      setField5(template.field5 || '');
      // Load media fields
      setHeaderImage(template.header_image || '');
      setHeaderVideo(template.header_video || '');
      setHeaderDocument(template.header_document || '');
      setHeaderDocumentName(template.header_document_name || '');
      setHeaderField1(template.header_field_1 || '');
      // Load location fields
      setLocationLatitude(template.location_latitude || '');
      setLocationLongitude(template.location_longitude || '');
      setLocationName(template.location_name || '');
      setLocationAddress(template.location_address || '');
      toast.success(`Template "${template.name}" loaded with media & location`);
    }
  };

  // Excel upload
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

      // Get phone column
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

  // Parse text input
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

  // Add country code to all numbers
  const handleAddCountryCode = () => {
    if (!countryCode) {
      toast.error('Please enter a country code');
      return;
    }

    let addedCount = 0;
    let skippedCount = 0;
    
    const updated = recipients.map(r => {
      const phone = r.phone.trim();
      
      // Remove all non-digit characters to check the raw number
      const digitsOnly = phone.replace(/\D/g, '');
      
      // Check if number already has + sign OR already starts with the country code
      if (phone.startsWith('+') || digitsOnly.startsWith(countryCode)) {
        skippedCount++;
        return r;
      }
      
      // Remove leading zeros
      const cleanPhone = digitsOnly.replace(/^0+/, '');
      
      // Add country code
      addedCount++;
      return {
        ...r,
        phone: `+${countryCode}${cleanPhone}`
      };
    });

    setRecipients(updated);
    
    if (addedCount > 0) {
      toast.success(`Country code +${countryCode} added to ${addedCount} number(s). ${skippedCount} already had it.`);
    } else {
      toast.info(`All ${skippedCount} numbers already have country code ${countryCode}`);
    }
  };

  // Remove duplicates
  const handleRemoveDuplicates = () => {
    const seen = new Set();
    const unique = recipients.filter(r => {
      const phone = r.phone.replace(/\D/g, '');
      if (seen.has(phone)) {
        return false;
      }
      seen.add(phone);
      return true;
    });

    const removed = recipients.length - unique.length;
    setRecipients(unique);
    toast.success(`Removed ${removed} duplicate(s). ${unique.length} unique recipients.`);
  };



  // Handle file upload
  const handleFileUpload = async (file, type) => {
    if (!file) return;
    
    setUploading(true);
    try {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('media_type', type);
      
      const response = await api.post('/upload/media', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
        params: { media_type: type }
      });
      
      // Convert relative URL to absolute URL using backend URL
      const backendUrl = process.env.REACT_APP_BACKEND_URL || '';
      const fullUrl = backendUrl + response.data.url;
      
      if (type === 'image') {
        setHeaderImage(fullUrl);
        toast.success('Image uploaded successfully');
      } else if (type === 'video') {
        setHeaderVideo(fullUrl);
        toast.success('Video uploaded successfully');
      } else if (type === 'document') {
        setHeaderDocument(fullUrl);
        setHeaderDocumentName(file.name);
        toast.success('Document uploaded successfully');
      }
    } catch (error) {
      toast.error(`Failed to upload ${type}: ${error.response?.data?.detail || error.message}`);
    } finally {
      setUploading(false);
    }
  };

  // Send messages
  const handleSend = async (isScheduled = false) => {
    // Validation
    if (!campaignName) {
      toast.error('Please enter campaign name');
      return;
    }
    if (!templateName) {
      toast.error('Please enter template name');
      return;
    }
    if (recipients.length === 0) {
      toast.error('Please add recipients');
      return;
    }
    if (isScheduled && !scheduledDate) {
      toast.error('Please select schedule date');
      return;
    }

    setSending(true);
    try {


  // Save current configuration as a template
  const handleSaveAsTemplate = async () => {
    // Validation
    if (!templateName) {
      toast.error('Please enter template name first');
      return;
    }

    const templateNamePrompt = prompt('Enter a name for this template:');
    if (!templateNamePrompt) return;

    try {
      const templateData = {
        name: templateNamePrompt,
        templateName: templateName,
        templateLanguage: templateLanguage,
        field1: field1,
        field2: field2,
        field3: field3,
        field4: field4,
        field5: field5,
        // Media fields
        header_image: headerImage,
        header_video: headerVideo,
        header_document: headerDocument,
        header_document_name: headerDocumentName,
        header_field_1: headerField1,
        // Location fields
        location_latitude: locationLatitude,
        location_longitude: locationLongitude,
        location_name: locationName,
        location_address: locationAddress
      };

      await api.post('/saved-templates', templateData);
      toast.success('Template saved successfully!');
      // Refresh templates list
      fetchSavedTemplates();
    } catch (error) {
      toast.error('Failed to save template: ' + (error.response?.data?.detail || error.message));
    }
  };

      // Prepare recipients with template data
      const recipientsWithData = recipients.map(r => ({
        phone: r.phone,
        name: r.name,
        template_language: templateLanguage,
        field_1: field1 || '',
        field_2: field2 || '',
        field_3: field3 || '',
        field_4: field4 || '',
        field_5: field5 || ''
      }));

      const payload = {
        campaignName,
        templateName,
        recipients: recipientsWithData,
        scheduledAt: isScheduled ? new Date(scheduledDate).toISOString() : null,
        // Add media fields if provided
        ...(headerImage && { header_image: headerImage }),
        ...(headerVideo && { header_video: headerVideo }),
        ...(headerDocument && { header_document: headerDocument }),
        ...(headerDocumentName && { header_document_name: headerDocumentName }),
        ...(headerField1 && { header_field_1: headerField1 }),
        // Add location fields if provided
        ...(locationLatitude && { location_latitude: locationLatitude }),
        ...(locationLongitude && { location_longitude: locationLongitude }),
        ...(locationName && { location_name: locationName }),
        ...(locationAddress && { location_address: locationAddress })
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

  return (
    <Layout user={user} onLogout={onLogout}>
      <div className="space-y-6">
        <div>
          <h1 className="text-3xl sm:text-4xl font-bold text-slate-900">Send Messages</h1>
          <p className="text-slate-600 mt-1">Create and send bulk WhatsApp campaigns</p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Main Form */}
          <div className="lg:col-span-2 space-y-6">
            {/* Campaign Details */}
            <Card className="shadow-lg border-0">
              <CardHeader>
                <CardTitle>Campaign Details</CardTitle>
                <CardDescription>Configure your campaign and template</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                {savedTemplates.length > 0 && (
                  <div className="space-y-2 p-4 bg-blue-50 border border-blue-200 rounded-lg">
                    <Label htmlFor="loadTemplate">Load Saved Template (Optional)</Label>
                    <Select value={selectedSavedTemplate} onValueChange={handleLoadTemplate}>
                      <SelectTrigger data-testid="load-template-select">
                        <SelectValue placeholder="Select a saved template..." />
                      </SelectTrigger>
                      <SelectContent>
                        {savedTemplates.map((template) => (
                          <SelectItem key={template.id} value={template.id}>
                            {template.name}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    <p className="text-xs text-blue-700">
                      Select a template to auto-fill all fields below
                    </p>
                  </div>
                )}
                
                <div className="space-y-2">
                  <Label htmlFor="campaignName">Campaign Name *</Label>
                  <Input
                    id="campaignName"
                    placeholder="e.g., Holiday Promotion 2025"
                    value={campaignName}
                    onChange={(e) => setCampaignName(e.target.value)}
                    data-testid="campaign-name-input"
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="templateName">Template Name *</Label>
                  <Input
                    id="templateName"
                    placeholder="e.g., order_confirmation"
                    value={templateName}
                    onChange={(e) => setTemplateName(e.target.value)}
                    data-testid="template-name-input"
                  />
                  <p className="text-xs text-slate-500">
                    Enter the exact template name approved in your BizChat account
                  </p>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="templateLanguage">Template Language</Label>
                  <Select value={templateLanguage} onValueChange={setTemplateLanguage}>
                    <SelectTrigger data-testid="language-select">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="en">English (en)</SelectItem>
                      <SelectItem value="en_US">English US (en_US)</SelectItem>
                      <SelectItem value="en_GB">English UK (en_GB)</SelectItem>
                      <SelectItem value="hi">Hindi (hi)</SelectItem>
                      <SelectItem value="es">Spanish (es)</SelectItem>
                      <SelectItem value="fr">French (fr)</SelectItem>
                      <SelectItem value="de">German (de)</SelectItem>
                      <SelectItem value="pt">Portuguese (pt)</SelectItem>
                      <SelectItem value="ar">Arabic (ar)</SelectItem>
                      <SelectItem value="zh">Chinese (zh)</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </CardContent>
            </Card>

            {/* Template Fields */}
            <Card className="shadow-lg border-0">
              <CardHeader>
                <CardTitle>Template Fields</CardTitle>
                <CardDescription>Enter values for template variables (same for all recipients)</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <Alert className="bg-emerald-50 border-emerald-200">
                  <AlertCircle className="h-4 w-4 text-emerald-600" />
                  <AlertDescription className="text-emerald-800">
                    <strong>💡 Personalization:</strong> Use <code className="bg-emerald-100 px-1 rounded">{'{name}'}</code> to insert recipient's name from Excel.
                    <br />
                    <span className="text-sm">Example: "Hi {'{name}'}, your order is ready!" becomes "Hi John, your order is ready!"</span>
                  </AlertDescription>
                </Alert>
                <div className="space-y-2">
                  <Label htmlFor="field1">Field 1</Label>
                  <Textarea
                    id="field1"
                    placeholder="Enter text for field 1"
                    rows={2}
                    value={field1}
                    onChange={(e) => setField1(e.target.value)}
                    data-testid="field1-input"
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="field2">Field 2</Label>
                  <Textarea
                    id="field2"
                    placeholder="Enter text for field 2"
                    rows={2}
                    value={field2}
                    onChange={(e) => setField2(e.target.value)}
                    data-testid="field2-input"
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="field3">Field 3</Label>
                  <Textarea
                    id="field3"
                    placeholder="Enter text for field 3"
                    rows={2}
                    value={field3}
                    onChange={(e) => setField3(e.target.value)}
                    data-testid="field3-input"
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="field4">Field 4</Label>
                  <Textarea
                    id="field4"
                    placeholder="Enter text for field 4"
                    rows={2}
                    value={field4}
                    onChange={(e) => setField4(e.target.value)}
                    data-testid="field4-input"
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="field5">Field 5</Label>
                  <Textarea
                    id="field5"
                    placeholder="Enter text for field 5"
                    rows={2}
                    value={field5}
                    onChange={(e) => setField5(e.target.value)}
                    data-testid="field5-input"
                  />
                </div>
              </CardContent>
            </Card>



            {/* Media & Location (Optional) */}
            <Card className="shadow-lg border-0">
              <CardHeader>
                <CardTitle>Media & Location (Optional)</CardTitle>
                <CardDescription>Add images, videos, documents, or location data to your message</CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                {/* Media Section */}
                <div className="space-y-4">
                  <h3 className="font-semibold text-slate-900">Media Attachments</h3>
                  
                  {/* Header Image */}
                  <div className="space-y-2">
                    <Label htmlFor="headerImage">Header Image</Label>
                    <div className="flex gap-2">
                      <Input
                        id="headerImage"
                        type="file"
                        accept="image/*"
                        onChange={(e) => e.target.files[0] && handleFileUpload(e.target.files[0], 'image')}
                        disabled={uploading}
                      />
                      {headerImage && <Button variant="outline" size="sm" onClick={() => window.open(headerImage)}>Preview</Button>}
                    </div>
                    {headerImage && <p className="text-xs text-emerald-600">✓ Image uploaded</p>}
                  </div>

                  {/* Header Video */}
                  <div className="space-y-2">
                    <Label htmlFor="headerVideo">Header Video</Label>
                    <div className="flex gap-2">
                      <Input
                        id="headerVideo"
                        type="file"
                        accept="video/*"
                        onChange={(e) => e.target.files[0] && handleFileUpload(e.target.files[0], 'video')}
                        disabled={uploading}
                      />
                      {headerVideo && <Button variant="outline" size="sm" onClick={() => window.open(headerVideo)}>Preview</Button>}
                    </div>
                    {headerVideo && <p className="text-xs text-emerald-600">✓ Video uploaded</p>}
                  </div>

                  {/* Header Document */}
                  <div className="space-y-2">
                    <Label htmlFor="headerDocument">Header Document</Label>
                    <div className="flex gap-2">
                      <Input
                        id="headerDocument"
                        type="file"
                        accept=".pdf,.doc,.docx,.xls,.xlsx,.txt,.csv"
                        onChange={(e) => e.target.files[0] && handleFileUpload(e.target.files[0], 'document')}
                        disabled={uploading}
                      />
                      {headerDocument && <Button variant="outline" size="sm" onClick={() => window.open(headerDocument)}>Download</Button>}
                    </div>
                    {headerDocument && <p className="text-xs text-emerald-600">✓ Document uploaded: {headerDocumentName}</p>}
                  </div>

                  {/* Header Field 1 */}
                  <div className="space-y-2">
                    <Label htmlFor="headerField1">Header Field 1</Label>
                    <Input
                      id="headerField1"
                      placeholder="Enter header field value"
                      value={headerField1}
                      onChange={(e) => setHeaderField1(e.target.value)}
                    />
                    <p className="text-xs text-slate-500">Use {'{name}'} for personalization</p>
                  </div>

                  {uploading && <p className="text-sm text-blue-600">⏳ Uploading file...</p>}
                </div>

                {/* Location Section */}
                <div className="space-y-4 pt-4 border-t">
                  <h3 className="font-semibold text-slate-900">Location Data</h3>
                  
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label htmlFor="locationLatitude">Latitude</Label>
                      <Input
                        id="locationLatitude"
                        placeholder="e.g., 22.22"
                        value={locationLatitude}
                        onChange={(e) => setLocationLatitude(e.target.value)}
                      />
                    </div>
                    
                    <div className="space-y-2">
                      <Label htmlFor="locationLongitude">Longitude</Label>
                      <Input
                        id="locationLongitude"
                        placeholder="e.g., 22.22"
                        value={locationLongitude}
                        onChange={(e) => setLocationLongitude(e.target.value)}
                      />
                    </div>
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="locationName">Location Name</Label>
                    <Input
                      id="locationName"
                      placeholder="e.g., Our Store"
                      value={locationName}
                      onChange={(e) => setLocationName(e.target.value)}
                    />
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="locationAddress">Location Address</Label>
                    <Textarea
                      id="locationAddress"
                      placeholder="e.g., 123 Main St, City, State"
                      rows={2}
                      value={locationAddress}
                      onChange={(e) => setLocationAddress(e.target.value)}
                    />
                  </div>

                  <Alert className="bg-blue-50 border-blue-200">
                    <AlertCircle className="h-4 w-4 text-blue-600" />
                    <AlertDescription className="text-blue-800 text-sm">
                      <strong>Note:</strong> Media and location fields are optional. They will be sent with all recipients in this campaign.
                    </AlertDescription>
                  </Alert>
                </div>
              </CardContent>
            </Card>

            {/* Add Recipients */}
            <Card className="shadow-lg border-0">
              <CardHeader>
                <CardTitle>Add Recipients</CardTitle>
                <CardDescription>Upload Excel file or paste phone numbers</CardDescription>
              </CardHeader>
              <CardContent>
                <Tabs defaultValue="upload" className="w-full">
                  <TabsList className="grid w-full grid-cols-2">
                    <TabsTrigger value="upload">Upload Excel</TabsTrigger>
                    <TabsTrigger value="paste">Copy Paste</TabsTrigger>
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
                    <Alert className="bg-blue-50 border-blue-200">
                      <AlertDescription className="text-sm text-blue-900">
                        <strong>Expected columns:</strong> phone (required), name (optional)
                      </AlertDescription>
                    </Alert>
                  </TabsContent>

                  <TabsContent value="paste" className="space-y-4">
                    <Textarea
                      placeholder="Paste phone numbers (one per line)&#10;Format: phone, name&#10;Example:&#10;+1234567890, John Doe&#10;9876543210, Jane Smith"
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

                {/* Country Code & Duplicate Actions */}
                {recipients.length > 0 && (
                  <div className="mt-6 space-y-4">
                    <div className="flex items-center space-x-2">
                      <Input
                        placeholder="Country code (e.g., 91, 1, 44)"
                        value={countryCode}
                        onChange={(e) => setCountryCode(e.target.value.replace(/\D/g, ''))}
                        className="flex-1"
                        data-testid="country-code-input"
                      />
                      <Button 
                        variant="outline" 
                        onClick={handleAddCountryCode}
                        data-testid="add-country-code-button"
                      >
                        <Globe className="h-4 w-4 mr-2" />
                        Add Country Code
                      </Button>
                      <Button 
                        variant="outline" 
                        onClick={handleRemoveDuplicates}
                        data-testid="remove-duplicates-button"
                      >
                        <Trash2 className="h-4 w-4 mr-2" />
                        Remove Duplicates
                      </Button>
                    </div>
                  </div>
                )}
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
                  <p className="font-medium text-slate-900">{templateName || 'Not entered'}</p>
                  <p className="text-xs text-slate-500 mt-1">Language: {templateLanguage}</p>
                </div>

                <div>
                  <p className="text-sm text-slate-600">Rate</p>
                  <p className="text-sm font-medium text-slate-900">29 messages/second</p>
                  <p className="text-xs text-slate-500 mt-1">


                  <Button
                    onClick={handleSaveAsTemplate}
                    variant="outline"
                    className="w-full"
                  >
                    <FileText className="h-4 w-4 mr-2" />
                    Save as Template
                  </Button>

                    Est. time: ~{Math.ceil(recipients.length / 29)} seconds
                  </p>
                </div>

                {recipients.length > 0 && (
                  <div>
                    <p className="text-sm text-slate-600 mb-2">Preview Recipients</p>
                    <div className="bg-slate-50 rounded-lg p-3 max-h-48 overflow-y-auto">
                      {recipients.slice(0, 5).map((r, i) => (
                        <div key={i} className="text-sm py-1 border-b border-slate-200 last:border-0">
                          <p className="font-medium text-slate-900">{r.name || 'No name'}</p>
                          <p className="text-slate-500 text-xs">{r.phone}</p>
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
                  <Alert className="bg-blue-50 border-blue-200">
                    <AlertCircle className="h-4 w-4" />
                    <AlertDescription className="text-sm">
                      Large campaign! Processing in batches with real-time progress tracking.
                    </AlertDescription>
                  </Alert>
                )}
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    </Layout>
  );
};

export default SendMessagesSimple;
