import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Send, Clock, Save, AlertCircle } from 'lucide-react';
import { toast } from 'sonner';

import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Switch } from '@/components/ui/switch';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

import Layout from '../components/Layout';
import { RecipientUploader, MediaUploader, TemplateSelector } from '../components/messaging';
import { useRecipients, useMediaUpload } from '../hooks';
import api from '../utils/api';

const LANGUAGES = [
  { value: 'en', label: 'English (en)' },
  { value: 'en_US', label: 'English US (en_US)' },
  { value: 'en_GB', label: 'English UK (en_GB)' },
  { value: 'hi', label: 'Hindi (hi)' },
  { value: 'es', label: 'Spanish (es)' },
  { value: 'fr', label: 'French (fr)' },
  { value: 'de', label: 'German (de)' },
  { value: 'pt', label: 'Portuguese (pt)' },
  { value: 'ar', label: 'Arabic (ar)' },
  { value: 'zh', label: 'Chinese (zh)' },
];

// Template Fields Component
const TemplateFieldsCard = ({ fields, onFieldChange }) => (
  <Card className="shadow-lg border-0">
    <CardHeader>
      <CardTitle>Template Fields</CardTitle>
      <CardDescription>Enter values for template variables (same for all recipients)</CardDescription>
    </CardHeader>
    <CardContent className="space-y-4">
      <Alert className="bg-emerald-50 border-emerald-200">
        <AlertCircle className="h-4 w-4 text-emerald-600" />
        <AlertDescription className="text-emerald-800">
          <strong>Personalization:</strong> Use <code className="bg-emerald-100 px-1 rounded">{'{name}'}</code> to insert recipient's name from Excel.
        </AlertDescription>
      </Alert>
      {[1, 2, 3, 4, 5].map(i => (
        <div key={i} className="space-y-2">
          <Label htmlFor={`field${i}`}>Field {i}</Label>
          <Textarea
            id={`field${i}`}
            placeholder={`Enter text for field ${i}`}
            rows={2}
            value={fields[`field${i}`]}
            onChange={(e) => onFieldChange(`field${i}`, e.target.value)}
            data-testid={`field${i}-input`}
          />
        </div>
      ))}
    </CardContent>
  </Card>
);

const SendMessagesSimple = ({ user, onLogout }) => {
  const navigate = useNavigate();
  const { recipients, parseExcelFile, parseTextInput, addCountryCode, removeDuplicates, removeRecipient, clearRecipients } = useRecipients();
  const { uploadFile, uploading } = useMediaUpload();

  // Campaign state
  const [campaignName, setCampaignName] = useState('');
  const [templateName, setTemplateName] = useState('');
  const [templateLanguage, setTemplateLanguage] = useState('en');
  const [fields, setFields] = useState({ field1: '', field2: '', field3: '', field4: '', field5: '' });
  
  // Media state
  const [mediaType, setMediaType] = useState('none');
  const [headerImage, setHeaderImage] = useState('');
  const [headerVideo, setHeaderVideo] = useState('');
  const [headerDocument, setHeaderDocument] = useState('');
  const [headerDocumentName, setHeaderDocumentName] = useState('');
  const [locationLatitude, setLocationLatitude] = useState('');
  const [locationLongitude, setLocationLongitude] = useState('');
  const [locationName, setLocationName] = useState('');
  const [locationAddress, setLocationAddress] = useState('');
  
  // Scheduling state
  const [isScheduled, setIsScheduled] = useState(false);
  const [scheduledDate, setScheduledDate] = useState('');
  
  // Saved templates
  const [savedTemplates, setSavedTemplates] = useState([]);
  const [selectedSavedTemplate, setSelectedSavedTemplate] = useState('');
  
  // UI state
  const [sending, setSending] = useState(false);

  useEffect(() => {
    fetchSavedTemplates();
  }, []);

  const fetchSavedTemplates = async () => {
    try {
      const response = await api.get('/saved-templates');
      // Handle both array response and {templates: [...]} response
      const data = response.data;
      setSavedTemplates(Array.isArray(data) ? data : data.templates || []);
    } catch (error) {
      console.error('Failed to load saved templates');
    }
  };

  const handleFieldChange = (fieldName, value) => {
    setFields(prev => ({ ...prev, [fieldName]: value }));
  };

  const handleLoadTemplate = (template) => {
    setTemplateName(template.templateName);
    setTemplateLanguage(template.templateLanguage);
    setFields({
      field1: template.field1 || '',
      field2: template.field2 || '',
      field3: template.field3 || '',
      field4: template.field4 || '',
      field5: template.field5 || ''
    });
    
    // Set media
    if (template.header_image) {
      setMediaType('image');
      setHeaderImage(template.header_image);
    } else if (template.header_video) {
      setMediaType('video');
      setHeaderVideo(template.header_video);
    } else if (template.header_document) {
      setMediaType('document');
      setHeaderDocument(template.header_document);
      setHeaderDocumentName(template.header_document_name || '');
    } else if (template.location_latitude && template.location_longitude) {
      setMediaType('location');
      setLocationLatitude(template.location_latitude);
      setLocationLongitude(template.location_longitude);
      setLocationName(template.location_name || '');
      setLocationAddress(template.location_address || '');
    } else {
      setMediaType('none');
    }
  };

  const handleFileUpload = async (file, type) => {
    const result = await uploadFile(file, type);
    if (result) {
      if (type === 'image') setHeaderImage(result.url);
      else if (type === 'video') setHeaderVideo(result.url);
      else if (type === 'document') {
        setHeaderDocument(result.url);
        setHeaderDocumentName(result.fileName);
      }
    }
  };

  const handleSendCampaign = async () => {
    // Validation
    if (!templateName.trim()) {
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
      const recipientsWithData = recipients.map(r => ({
        phone: r.phone,
        name: r.name,
        template_language: templateLanguage,
        field_1: fields.field1 || '',
        field_2: fields.field2 || '',
        field_3: fields.field3 || '',
        field_4: fields.field4 || '',
        field_5: fields.field5 || ''
      }));

      const payload = {
        campaignName,
        templateName,
        recipients: recipientsWithData,
        scheduledAt: isScheduled ? new Date(scheduledDate).toISOString() : null
      };

      // Add media based on type
      if (mediaType === 'image' && headerImage) {
        payload.header_image = headerImage;
      } else if (mediaType === 'video' && headerVideo) {
        payload.header_video = headerVideo;
      } else if (mediaType === 'document' && headerDocument) {
        payload.header_document = headerDocument;
        if (headerDocumentName) payload.header_document_name = headerDocumentName;
      } else if (mediaType === 'location' && locationLatitude && locationLongitude) {
        payload.location_latitude = locationLatitude;
        payload.location_longitude = locationLongitude;
        if (locationName) payload.location_name = locationName;
        if (locationAddress) payload.location_address = locationAddress;
      }

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

  const handleSaveAsTemplate = async () => {
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
        field1: fields.field1,
        field2: fields.field2,
        field3: fields.field3,
        field4: fields.field4,
        field5: fields.field5
      };

      // Add media
      if (mediaType === 'image' && headerImage) {
        templateData.header_image = headerImage;
      } else if (mediaType === 'video' && headerVideo) {
        templateData.header_video = headerVideo;
      } else if (mediaType === 'document' && headerDocument) {
        templateData.header_document = headerDocument;
        if (headerDocumentName) templateData.header_document_name = headerDocumentName;
      } else if (mediaType === 'location' && locationLatitude && locationLongitude) {
        templateData.location_latitude = locationLatitude;
        templateData.location_longitude = locationLongitude;
        if (locationName) templateData.location_name = locationName;
        if (locationAddress) templateData.location_address = locationAddress;
      }

      await api.post('/saved-templates', templateData);
      toast.success('Template saved successfully!');
      fetchSavedTemplates();
    } catch (error) {
      toast.error('Failed to save template: ' + (error.response?.data?.detail || error.message));
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
          {/* Main Form - Left Column */}
          <div className="lg:col-span-2 space-y-6">
            
            {/* Campaign Details */}
            <Card className="shadow-lg border-0">
              <CardHeader>
                <CardTitle>Campaign Details</CardTitle>
                <CardDescription>Configure your campaign and template</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                {/* Load Saved Template */}
                {savedTemplates.length > 0 && (
                  <div className="p-4 bg-blue-50 border border-blue-200 rounded-lg">
                    <TemplateSelector
                      templates={savedTemplates}
                      selectedTemplate={selectedSavedTemplate}
                      onSelectTemplate={setSelectedSavedTemplate}
                      onLoadTemplate={handleLoadTemplate}
                    />
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
                      {LANGUAGES.map(lang => (
                        <SelectItem key={lang.value} value={lang.value}>{lang.label}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </CardContent>
            </Card>

            {/* Template Fields */}
            <TemplateFieldsCard fields={fields} onFieldChange={handleFieldChange} />

            {/* Media Section */}
            <Card className="shadow-lg border-0">
              <CardHeader>
                <CardTitle>Media & Location (Optional)</CardTitle>
                <CardDescription>Choose ONE type: Image, Video, Document, or Location</CardDescription>
              </CardHeader>
              <CardContent>
                <MediaUploader
                  mediaType={mediaType}
                  onMediaTypeChange={setMediaType}
                  headerImage={headerImage}
                  onHeaderImageChange={setHeaderImage}
                  headerVideo={headerVideo}
                  onHeaderVideoChange={setHeaderVideo}
                  headerDocument={headerDocument}
                  onHeaderDocumentChange={setHeaderDocument}
                  headerDocumentName={headerDocumentName}
                  onHeaderDocumentNameChange={setHeaderDocumentName}
                  locationLatitude={locationLatitude}
                  onLocationLatitudeChange={setLocationLatitude}
                  locationLongitude={locationLongitude}
                  onLocationLongitudeChange={setLocationLongitude}
                  locationName={locationName}
                  onLocationNameChange={setLocationName}
                  locationAddress={locationAddress}
                  onLocationAddressChange={setLocationAddress}
                />
              </CardContent>
            </Card>

            {/* Schedule Option */}
            <Card className="shadow-lg border-0">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Clock className="h-5 w-5 text-blue-600" />
                  Schedule Campaign
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex items-center space-x-2">
                  <Switch
                    id="schedule-mode"
                    checked={isScheduled}
                    onCheckedChange={setIsScheduled}
                    data-testid="schedule-toggle"
                  />
                  <Label htmlFor="schedule-mode">Schedule for later</Label>
                </div>
                
                {isScheduled && (
                  <div className="space-y-2">
                    <Label htmlFor="scheduledDate">Schedule Date & Time</Label>
                    <Input
                      id="scheduledDate"
                      type="datetime-local"
                      value={scheduledDate}
                      onChange={(e) => setScheduledDate(e.target.value)}
                      min={new Date().toISOString().slice(0, 16)}
                      data-testid="schedule-datetime"
                    />
                  </div>
                )}
              </CardContent>
            </Card>
          </div>

          {/* Right Column - Recipients */}
          <div className="space-y-6">
            <RecipientUploader
              recipients={recipients}
              onParseExcel={parseExcelFile}
              onParseText={parseTextInput}
              onAddCountryCode={addCountryCode}
              onRemoveDuplicates={removeDuplicates}
              onRemoveRecipient={removeRecipient}
              onClear={clearRecipients}
            />

            {/* Action Buttons */}
            <Card className="shadow-lg border-0">
              <CardContent className="pt-6 space-y-3">
                <Button
                  className="w-full"
                  size="lg"
                  onClick={handleSendCampaign}
                  disabled={sending || uploading || recipients.length === 0}
                  data-testid="send-campaign-btn"
                >
                  {sending ? (
                    <span className="flex items-center gap-2">
                      <span className="animate-spin">⏳</span> Processing...
                    </span>
                  ) : (
                    <span className="flex items-center gap-2">
                      <Send className="h-4 w-4" />
                      {isScheduled ? 'Schedule Campaign' : `Send to ${recipients.length} Recipients`}
                    </span>
                  )}
                </Button>
                
                <Button
                  variant="outline"
                  className="w-full"
                  onClick={handleSaveAsTemplate}
                  disabled={!templateName}
                  data-testid="save-template-btn"
                >
                  <Save className="h-4 w-4 mr-2" />
                  Save as Template
                </Button>
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    </Layout>
  );
};

export default SendMessagesSimple;
