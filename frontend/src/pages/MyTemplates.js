import React, { useState, useEffect } from 'react';
import { Plus, FileText, Edit, Trash2 } from 'lucide-react';
import { toast } from 'sonner';

import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";

import Layout from '../components/Layout';
import { MediaUploader } from '../components/messaging';
import { useMediaUpload } from '../hooks';
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
];

const INITIAL_FORM_DATA = {
  name: '',
  templateName: '',
  templateLanguage: 'en',
  field1: '', field2: '', field3: '', field4: '', field5: '',
  header_image: '', header_video: '', header_document: '',
  header_document_name: '', header_field_1: '',
  location_latitude: '', location_longitude: '',
  location_name: '', location_address: ''
};

// Template Card Component
const TemplateCard = ({ template, onEdit, onDelete }) => (
  <Card className="shadow-lg border-0 hover:shadow-xl transition-shadow" data-testid={`template-card-${template.id}`}>
    <CardHeader>
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <CardTitle className="text-lg">{template.name}</CardTitle>
          <CardDescription className="mt-1">
            {template.templateName} ({template.templateLanguage})
          </CardDescription>
        </div>
      </div>
    </CardHeader>
    <CardContent>
      <div className="space-y-2 mb-4">
        {[1, 2, 3].map(i => {
          const field = template[`field${i}`];
          return field ? (
            <div key={i} className="text-sm">
              <span className="font-medium text-slate-600">Field {i}:</span>
              <p className="text-slate-700 truncate">{field}</p>
            </div>
          ) : null;
        })}
      </div>
      <div className="flex space-x-2">
        <Button variant="outline" size="sm" className="flex-1" onClick={() => onEdit(template)}>
          <Edit className="h-4 w-4 mr-1" /> Edit
        </Button>
        <Button
          variant="outline"
          size="sm"
          className="text-red-600 hover:text-red-700 hover:bg-red-50"
          onClick={() => onDelete(template.id)}
        >
          <Trash2 className="h-4 w-4" />
        </Button>
      </div>
    </CardContent>
  </Card>
);

// Template Fields Component
const TemplateFields = ({ formData, onChange }) => (
  <div className="space-y-3">
    {[1, 2, 3, 4, 5].map(i => (
      <div key={i} className="space-y-2">
        <Label htmlFor={`field${i}`}>Field {i}</Label>
        <Textarea
          id={`field${i}`}
          rows={2}
          value={formData[`field${i}`]}
          onChange={(e) => onChange({ ...formData, [`field${i}`]: e.target.value })}
        />
      </div>
    ))}
  </div>
);

const MyTemplates = ({ user, onLogout }) => {
  const [templates, setTemplates] = useState([]);
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingTemplate, setEditingTemplate] = useState(null);
  const [formData, setFormData] = useState(INITIAL_FORM_DATA);
  const [mediaType, setMediaType] = useState('none');
  const { uploadFile, uploading } = useMediaUpload();

  useEffect(() => {
    fetchTemplates();
  }, []);

  const fetchTemplates = async () => {
    try {
      const response = await api.get('/saved-templates');
      // Handle both array response and {templates: [...]} response
      const data = response.data;
      setTemplates(Array.isArray(data) ? data : data.templates || []);
    } catch (error) {
      toast.error('Failed to load templates');
    } finally {
      setLoading(false);
    }
  };

  const handleFileUpload = async (file, type) => {
    const result = await uploadFile(file, type);
    if (result) {
      if (type === 'image') setFormData(f => ({ ...f, header_image: result.url }));
      else if (type === 'video') setFormData(f => ({ ...f, header_video: result.url }));
      else if (type === 'document') setFormData(f => ({ ...f, header_document: result.url, header_document_name: result.fileName }));
    }
  };

  const detectMediaType = (template) => {
    if (template.header_image) return 'image';
    if (template.header_video) return 'video';
    if (template.header_document) return 'document';
    if (template.location_latitude && template.location_longitude) return 'location';
    return 'none';
  };

  const handleOpenDialog = (template = null) => {
    if (template) {
      setEditingTemplate(template);
      setMediaType(detectMediaType(template));
      setFormData({
        name: template.name,
        templateName: template.templateName,
        templateLanguage: template.templateLanguage,
        field1: template.field1 || '', field2: template.field2 || '',
        field3: template.field3 || '', field4: template.field4 || '',
        field5: template.field5 || '',
        header_image: template.header_image || '',
        header_video: template.header_video || '',
        header_document: template.header_document || '',
        header_document_name: template.header_document_name || '',
        header_field_1: template.header_field_1 || '',
        location_latitude: template.location_latitude || '',
        location_longitude: template.location_longitude || '',
        location_name: template.location_name || '',
        location_address: template.location_address || ''
      });
    } else {
      setEditingTemplate(null);
      setMediaType('none');
      setFormData(INITIAL_FORM_DATA);
    }
    setDialogOpen(true);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      if (editingTemplate) {
        await api.put(`/saved-templates/${editingTemplate.id}`, formData);
        toast.success('Template updated successfully');
      } else {
        await api.post('/saved-templates', formData);
        toast.success('Template saved successfully');
      }
      setDialogOpen(false);
      fetchTemplates();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to save template');
    }
  };

  const handleDelete = async (templateId) => {
    if (!window.confirm('Are you sure you want to delete this template?')) return;
    try {
      await api.delete(`/saved-templates/${templateId}`);
      toast.success('Template deleted successfully');
      fetchTemplates();
    } catch (error) {
      toast.error('Failed to delete template');
    }
  };

  return (
    <Layout user={user} onLogout={onLogout}>
      <div className="space-y-6">
        <div className="flex justify-between items-center">
          <div>
            <h1 className="text-3xl sm:text-4xl font-bold text-slate-900">My Templates</h1>
            <p className="text-slate-600 mt-1">Save and reuse your message templates</p>
          </div>
          
          <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
            <DialogTrigger asChild>
              <Button onClick={() => handleOpenDialog()} data-testid="create-template-button">
                <Plus className="h-4 w-4 mr-2" /> New Template
              </Button>
            </DialogTrigger>
            <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
              <DialogHeader>
                <DialogTitle>{editingTemplate ? 'Edit Template' : 'Create New Template'}</DialogTitle>
                <DialogDescription>Save your template configuration to reuse later</DialogDescription>
              </DialogHeader>
              
              <form onSubmit={handleSubmit} className="space-y-4">
                {/* Basic Info */}
                <div className="space-y-2">
                  <Label htmlFor="name">Template Name (Your Reference) *</Label>
                  <Input
                    id="name"
                    placeholder="e.g., Holiday Sale Promo"
                    value={formData.name}
                    onChange={(e) => setFormData({...formData, name: e.target.value})}
                    required
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="templateName">BizChat Template Name *</Label>
                  <Input
                    id="templateName"
                    placeholder="e.g., order_confirmation"
                    value={formData.templateName}
                    onChange={(e) => setFormData({...formData, templateName: e.target.value})}
                    required
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="templateLanguage">Language</Label>
                  <Select
                    value={formData.templateLanguage}
                    onValueChange={(value) => setFormData({...formData, templateLanguage: value})}
                  >
                    <SelectTrigger><SelectValue /></SelectTrigger>
                    <SelectContent>
                      {LANGUAGES.map(lang => (
                        <SelectItem key={lang.value} value={lang.value}>{lang.label}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                {/* Template Fields */}
                <div className="border-t pt-4">
                  <h3 className="font-medium mb-3">Template Fields</h3>
                  <TemplateFields formData={formData} onChange={setFormData} />
                </div>

                {/* Media Section */}
                <div className="space-y-4 pt-4 border-t mt-4">
                  <h3 className="font-semibold text-slate-900">Media & Location (Optional)</h3>
                  <MediaUploader
                    mediaType={mediaType}
                    onMediaTypeChange={setMediaType}
                    headerImage={formData.header_image}
                    onHeaderImageChange={(v) => setFormData({...formData, header_image: v})}
                    headerVideo={formData.header_video}
                    onHeaderVideoChange={(v) => setFormData({...formData, header_video: v})}
                    headerDocument={formData.header_document}
                    onHeaderDocumentChange={(v) => setFormData({...formData, header_document: v})}
                    headerDocumentName={formData.header_document_name}
                    onHeaderDocumentNameChange={(v) => setFormData({...formData, header_document_name: v})}
                    locationLatitude={formData.location_latitude}
                    onLocationLatitudeChange={(v) => setFormData({...formData, location_latitude: v})}
                    locationLongitude={formData.location_longitude}
                    onLocationLongitudeChange={(v) => setFormData({...formData, location_longitude: v})}
                    locationName={formData.location_name}
                    onLocationNameChange={(v) => setFormData({...formData, location_name: v})}
                    locationAddress={formData.location_address}
                    onLocationAddressChange={(v) => setFormData({...formData, location_address: v})}
                  />
                </div>

                <div className="flex space-x-2 pt-4">
                  <Button type="submit" className="flex-1" disabled={uploading}>
                    {editingTemplate ? 'Update Template' : 'Save Template'}
                  </Button>
                  <Button type="button" variant="outline" onClick={() => setDialogOpen(false)}>
                    Cancel
                  </Button>
                </div>
              </form>
            </DialogContent>
          </Dialog>
        </div>

        {/* Templates List */}
        {loading ? (
          <div className="text-center py-12 text-slate-500">Loading templates...</div>
        ) : templates.length === 0 ? (
          <Card className="shadow-lg border-0">
            <CardContent className="py-12">
              <div className="text-center">
                <FileText className="h-16 w-16 text-slate-300 mx-auto mb-4" />
                <h3 className="text-lg font-medium text-slate-900 mb-2">No Templates Yet</h3>
                <p className="text-slate-600 mb-6">
                  Create your first template to save time when sending bulk messages
                </p>
                <Button onClick={() => handleOpenDialog()}>
                  <Plus className="h-4 w-4 mr-2" /> Create First Template
                </Button>
              </div>
            </CardContent>
          </Card>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {templates.map((template) => (
              <TemplateCard
                key={template.id}
                template={template}
                onEdit={handleOpenDialog}
                onDelete={handleDelete}
              />
            ))}
          </div>
        )}
      </div>
    </Layout>
  );
};

export default MyTemplates;
