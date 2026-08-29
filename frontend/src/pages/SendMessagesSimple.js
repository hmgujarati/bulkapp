import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Send, Clock, Save, AlertCircle, RefreshCw, CalendarClock } from 'lucide-react';
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
  { value: 'gu', label: 'Gujarati (gu)' },
  { value: 'mr', label: 'Marathi (mr)' },
  { value: 'ta', label: 'Tamil (ta)' },
  { value: 'te', label: 'Telugu (te)' },
  { value: 'kn', label: 'Kannada (kn)' },
  { value: 'bn', label: 'Bengali (bn)' },
  { value: 'pa', label: 'Punjabi (pa)' },
  { value: 'ur', label: 'Urdu (ur)' },
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

const localNowForInput = () => {
  const d = new Date();
  return new Date(d.getTime() - d.getTimezoneOffset() * 60000).toISOString().slice(0, 16);
};

const SendMessagesSimple = ({ user, onLogout }) => {
  const navigate = useNavigate();
  const { recipients, parseExcelFile, parseTextInput, addCountryCode, removeDuplicates, removeRecipient, clearRecipients } = useRecipients();
  const { uploadFile, uploading } = useMediaUpload();

  // Campaign state
  const [campaignName, setCampaignName] = useState('');
  const [templateName, setTemplateName] = useState('');
  const [templateReference, setTemplateReference] = useState('');
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
  
  // Drip (daily batch) state
  const [dripEnabled, setDripEnabled] = useState(false);
  const [dripPerDay, setDripPerDay] = useState('');
  const [dripStartDate, setDripStartDate] = useState('');
  
  // Saved templates
  const [savedTemplates, setSavedTemplates] = useState([]);
  const [selectedSavedTemplate, setSelectedSavedTemplate] = useState('');
  
  // BizChat live templates (for auto-language detection)
  const [bizchatTemplates, setBizchatTemplates] = useState([]);
  const [loadingBizchatTemplates, setLoadingBizchatTemplates] = useState(false);
  const [selectedBizchatTemplate, setSelectedBizchatTemplate] = useState('');
  
  // UI state
  const [sending, setSending] = useState(false);
  const [accountDailyLimit, setAccountDailyLimit] = useState(undefined);

  useEffect(() => {
    fetchSavedTemplates();
    api.get('/auth/me')
      .then(res => setAccountDailyLimit(res.data?.dailyLimit))
      .catch(() => {});
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

  const fetchBizchatTemplates = async () => {
    setLoadingBizchatTemplates(true);
    try {
      const response = await api.get('/templates');
      setBizchatTemplates(response.data.templates || []);
      if ((response.data.templates || []).length === 0) {
        toast.info('No templates found in your BizChat account');
      } else {
        toast.success(`Loaded ${response.data.templates.length} templates`);
      }
    } catch (error) {
      const msg = error.response?.data?.detail || 'Failed to fetch templates';
      toast.error(msg);
    } finally {
      setLoadingBizchatTemplates(false);
    }
  };

  const handlePickBizchatTemplate = (templateName) => {
    setSelectedBizchatTemplate(templateName);
    const chosen = bizchatTemplates.find(t => t.name === templateName);
    if (chosen) {
      setTemplateName(chosen.name);
      if (chosen.language) {
        setTemplateLanguage(chosen.language);
      }
    }
  };

  const handleFieldChange = (fieldName, value) => {
    setFields(prev => ({ ...prev, [fieldName]: value }));
  };

  const handleLoadTemplate = (template) => {
    setTemplateName(template.templateName);
    setTemplateReference(template.name || '');
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

  const dripPerDayNum = parseInt(dripPerDay, 10) || 0;
  const accountLimit = accountDailyLimit !== undefined ? accountDailyLimit : user?.dailyLimit;
  const dripExceedsAccount = dripEnabled && dripPerDayNum > 0 && accountLimit !== undefined && accountLimit !== -1 && dripPerDayNum > accountLimit;
  const dripDays = dripEnabled && dripPerDayNum > 0 && recipients.length > 0 ? Math.ceil(recipients.length / dripPerDayNum) : 0;
  const dripFinishDate = dripDays > 0
    ? new Date((dripStartDate ? new Date(dripStartDate) : new Date()).getTime() + (dripDays - 1) * 86400000)
    : null;

  const handleSendCampaign = async () => {
    // Validation
    if (!campaignName.trim()) {
      toast.error('Please enter a campaign name');
      return;
    }
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
    if (dripEnabled) {
      if (dripPerDayNum < 1) {
        toast.error('Please enter how many messages to send per day');
        return;
      }
      if (dripExceedsAccount) {
        toast.error(`Messages per day (${dripPerDayNum}) cannot exceed your account daily limit (${accountLimit})`);
        return;
      }
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
        templateReference: templateReference || null,
        recipients: recipientsWithData,
        scheduledAt: isScheduled && !dripEnabled ? new Date(scheduledDate).toISOString() : null,
        dripEnabled,
        dripDailyLimit: dripEnabled ? dripPerDayNum : null,
        dripStartAt: dripEnabled && dripStartDate ? new Date(dripStartDate).toISOString() : null
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
        dripEnabled
          ? `Campaign created! Sending ${dripPerDayNum.toLocaleString()}/day — finishes in ${dripDays} day${dripDays > 1 ? 's' : ''}`
          : isScheduled 
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
        templateName: templateName,        templateLanguage: templateLanguage,
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
                  <div className="flex gap-2">
                    <Select 
                      value={selectedBizchatTemplate}
                      onValueChange={handlePickBizchatTemplate}
                    >
                      <SelectTrigger 
                        className="flex-1" 
                        data-testid="bizchat-template-picker"
                      >
                        <SelectValue placeholder={
                          bizchatTemplates.length === 0 
                            ? "Load your BizChat templates →" 
                            : "Pick from BizChat (auto-fills language)"
                        } />
                      </SelectTrigger>
                      <SelectContent>
                        {loadingBizchatTemplates ? (
                          <SelectItem value="loading" disabled>Loading...</SelectItem>
                        ) : bizchatTemplates.length === 0 ? (
                          <SelectItem value="none" disabled>Click Refresh to load</SelectItem>
                        ) : (
                          bizchatTemplates.map((t) => (
                            <SelectItem key={`${t.name}-${t.language}`} value={t.name}>
                              {t.name}
                              {t.language && (
                                <span className="text-xs text-slate-500 ml-2">({t.language})</span>
                              )}
                            </SelectItem>
                          ))
                        )}
                      </SelectContent>
                    </Select>
                    <Button
                      type="button"
                      variant="outline"
                      size="icon"
                      onClick={fetchBizchatTemplates}
                      disabled={loadingBizchatTemplates}
                      data-testid="refresh-bizchat-templates-btn"
                      title="Refresh BizChat templates"
                    >
                      <RefreshCw className={`h-4 w-4 ${loadingBizchatTemplates ? 'animate-spin' : ''}`} />
                    </Button>
                  </div>
                  <Input
                    id="templateName"
                    placeholder="e.g., order_confirmation"
                    value={templateName}
                    onChange={(e) => {
                      setTemplateName(e.target.value);
                      setSelectedBizchatTemplate('');
                    }}
                    data-testid="template-name-input"
                  />
                  <p className="text-xs text-slate-500">
                    Pick from BizChat above (recommended — auto-fills language and avoids typos) or type manually.
                  </p>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="templateReference">Template Name (Your Reference)</Label>
                  <Input
                    id="templateReference"
                    placeholder="e.g., Diwali Offer – Gold Buyers"
                    value={templateReference}
                    onChange={(e) => setTemplateReference(e.target.value)}
                    data-testid="template-reference-input"
                  />
                  <p className="text-xs text-slate-500">
                    Optional friendly name shown in Campaign Details next to the BizChat template name.
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

            {/* Daily Batch (Drip) Sending */}
            <Card className="shadow-lg border-0">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <CalendarClock className="h-5 w-5 text-emerald-600" />
                  Daily Sending Limit
                </CardTitle>
                <CardDescription>
                  Split a large list across multiple days — e.g. 3,000 per day out of 20,000 numbers
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex items-center space-x-2">
                  <Switch
                    id="drip-mode"
                    checked={dripEnabled}
                    onCheckedChange={setDripEnabled}
                    data-testid="drip-toggle"
                  />
                  <Label htmlFor="drip-mode">Send only a set number of messages per day</Label>
                </div>

                {dripEnabled && (
                  <div className="space-y-4" data-testid="drip-settings">
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                      <div className="space-y-2">
                        <Label htmlFor="dripPerDay">Messages per day *</Label>
                        <Input
                          id="dripPerDay"
                          type="number"
                          min="1"
                          placeholder="e.g., 3000"
                          value={dripPerDay}
                          onChange={(e) => setDripPerDay(e.target.value)}
                          data-testid="drip-per-day-input"
                        />
                        {accountLimit !== undefined && (
                          <p className="text-xs text-slate-500">
                            Your account limit: {accountLimit === -1 ? 'Unlimited' : accountLimit.toLocaleString()} / day
                          </p>
                        )}
                      </div>
                      <div className="space-y-2">
                        <Label htmlFor="dripStartDate">Daily start time</Label>
                        <Input
                          id="dripStartDate"
                          type="datetime-local"
                          value={dripStartDate}
                          onChange={(e) => setDripStartDate(e.target.value)}
                          min={localNowForInput()}
                          data-testid="drip-start-input"
                        />
                        <p className="text-xs text-slate-500">
                          Leave empty to start now. Each following batch starts at this same time daily.
                        </p>
                      </div>
                    </div>

                    {dripExceedsAccount && (
                      <Alert className="bg-red-50 border-red-200" data-testid="drip-limit-warning">
                        <AlertCircle className="h-4 w-4 text-red-600" />
                        <AlertDescription className="text-red-800">
                          {dripPerDayNum.toLocaleString()} per day is more than your account daily limit of{' '}
                          {accountLimit.toLocaleString()}. Lower it or ask the admin to raise your limit.
                        </AlertDescription>
                      </Alert>
                    )}

                    {dripDays > 0 && !dripExceedsAccount && (
                      <Alert className="bg-emerald-50 border-emerald-200" data-testid="drip-estimate">
                        <AlertCircle className="h-4 w-4 text-emerald-600" />
                        <AlertDescription className="text-emerald-800">
                          {recipients.length.toLocaleString()} recipients at {dripPerDayNum.toLocaleString()}/day →{' '}
                          <strong>campaign will finish in {dripDays} day{dripDays > 1 ? 's' : ''}</strong>
                          {dripFinishDate && ` (around ${dripFinishDate.toLocaleDateString()})`}.
                        </AlertDescription>
                      </Alert>
                    )}
                  </div>
                )}
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
                    disabled={dripEnabled}
                    data-testid="schedule-toggle"
                  />
                  <Label htmlFor="schedule-mode">Schedule for later</Label>
                </div>
                {dripEnabled && (
                  <p className="text-xs text-slate-500" data-testid="schedule-disabled-note">
                    Disabled — the daily sending limit above controls when this campaign starts.
                  </p>
                )}
                
                {isScheduled && (
                  <div className="space-y-2">
                    <Label htmlFor="scheduledDate">Schedule Date & Time</Label>
                    <Input
                      id="scheduledDate"
                      type="datetime-local"
                      value={scheduledDate}
                      onChange={(e) => setScheduledDate(e.target.value)}
                      min={localNowForInput()}
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
                  disabled={sending || uploading || recipients.length === 0 || !campaignName.trim() || dripExceedsAccount}
                  data-testid="send-campaign-btn"
                >
                  {sending ? (
                    <span className="flex items-center gap-2">
                      <span className="animate-spin">⏳</span> Processing...
                    </span>
                  ) : (
                    <span className="flex items-center gap-2">
                      <Send className="h-4 w-4" />
                      {dripEnabled && dripPerDayNum > 0
                        ? `Send ${dripPerDayNum.toLocaleString()}/day to ${recipients.length.toLocaleString()}`
                        : isScheduled ? 'Schedule Campaign' : `Send to ${recipients.length} Recipients`}
                    </span>
                  )}
                </Button>
                {!campaignName.trim() && (
                  <p className="text-xs text-red-600" data-testid="campaign-name-required-note">
                    Campaign name is required before sending.
                  </p>
                )}
                
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
