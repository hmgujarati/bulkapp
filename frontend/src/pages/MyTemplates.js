import React, { useState, useEffect } from 'react';
import Layout from '../components/Layout';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { Plus, Edit, Trash2, FileText } from 'lucide-react';
import { toast } from 'sonner';
import api from '../utils/api';

const MyTemplates = ({ user, onLogout }) => {
  const [templates, setTemplates] = useState([]);
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingTemplate, setEditingTemplate] = useState(null);
  
  const [mediaType, setMediaType] = useState('none'); // Track selected media type
  
  const [formData, setFormData] = useState({
    name: '',
    templateName: '',
    templateLanguage: 'en',
    field1: '',
    field2: '',
    field3: '',
    field4: '',
    field5: '',
    // Media fields
    header_image: '',
    header_video: '',
    header_document: '',
    header_document_name: '',
    header_field_1: '',
    // Location fields
    location_latitude: '',
    location_longitude: '',
    location_name: '',
    location_address: ''
  });

  useEffect(() => {
    fetchTemplates();
  }, []);

  const fetchTemplates = async () => {
    try {
      const response = await api.get('/saved-templates');
      setTemplates(response.data.templates);
    } catch (error) {
      toast.error('Failed to fetch templates');
    } finally {
      setLoading(false);
    }
  };

  const handleOpenDialog = (template = null) => {
    if (template) {
      setEditingTemplate(template);
      
      // Detect media type
      if (template.header_image) {
        setMediaType('image');
      } else if (template.header_video) {
        setMediaType('video');
      } else if (template.header_document) {
        setMediaType('document');
      } else if (template.location_latitude && template.location_longitude) {
        setMediaType('location');
      } else {
        setMediaType('none');
      }
      
      setFormData({
        name: template.name,
        templateName: template.templateName,
        templateLanguage: template.templateLanguage,
        field1: template.field1 || '',
        field2: template.field2 || '',
        field3: template.field3 || '',
        field4: template.field4 || '',
        field5: template.field5 || '',
        // Media fields
        header_image: template.header_image || '',
        header_video: template.header_video || '',
        header_document: template.header_document || '',
        header_document_name: template.header_document_name || '',
        header_field_1: template.header_field_1 || '',
        // Location fields
        location_latitude: template.location_latitude || '',
        location_longitude: template.location_longitude || '',
        location_name: template.location_name || '',
        location_address: template.location_address || ''
      });
    } else {
      setEditingTemplate(null);
      setMediaType('none');
      setFormData({
        name: '',
        templateName: '',
        templateLanguage: 'en',
        field1: '',
        field2: '',
        field3: '',
        field4: '',
        field5: '',
        // Media fields
        header_image: '',
        header_video: '',
        header_document: '',
        header_document_name: '',
        header_field_1: '',
        // Location fields
        location_latitude: '',
        location_longitude: '',
        location_name: '',
        location_address: ''
      });
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
                <Plus className="h-4 w-4 mr-2" />
                New Template
              </Button>
            </DialogTrigger>
            <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
              <DialogHeader>
                <DialogTitle>{editingTemplate ? 'Edit Template' : 'Create New Template'}</DialogTitle>
                <DialogDescription>
                  Save your template configuration to reuse later
                </DialogDescription>
              </DialogHeader>
              
              <form onSubmit={handleSubmit} className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="name">Template Name (Your Reference) *</Label>
                  <Input
                    id="name"
                    placeholder="e.g., Holiday Sale Promo"
                    value={formData.name}
                    onChange={(e) => setFormData({...formData, name: e.target.value})}
                    required
                  />
                  <p className="text-xs text-slate-500">A friendly name to identify this template</p>
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
                    <SelectTrigger>
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
                    </SelectContent>
                  </Select>
                </div>

                <div className="border-t pt-4">
                  <h3 className="font-medium mb-3">Template Fields</h3>
                  
                  <div className="space-y-3">
                    <div className="space-y-2">
                      <Label htmlFor="field1">Field 1</Label>
                      <Textarea
                        id="field1"
                        rows={2}
                        value={formData.field1}
                        onChange={(e) => setFormData({...formData, field1: e.target.value})}
                      />
                    </div>

                    <div className="space-y-2">
                      <Label htmlFor="field2">Field 2</Label>
                      <Textarea
                        id="field2"
                        rows={2}
                        value={formData.field2}
                        onChange={(e) => setFormData({...formData, field2: e.target.value})}
                      />
                    </div>

                    <div className="space-y-2">
                      <Label htmlFor="field3">Field 3</Label>
                      <Textarea
                        id="field3"
                        rows={2}
                        value={formData.field3}
                        onChange={(e) => setFormData({...formData, field3: e.target.value})}
                      />
                    </div>

                    <div className="space-y-2">
                      <Label htmlFor="field4">Field 4</Label>
                      <Textarea
                        id="field4"
                        rows={2}
                        value={formData.field4}
                        onChange={(e) => setFormData({...formData, field4: e.target.value})}
                      />
                    </div>

                    <div className="space-y-2">
                      <Label htmlFor="field5">Field 5</Label>
                      <Textarea
                        id="field5"
                        rows={2}
                        value={formData.field5}
                        onChange={(e) => setFormData({...formData, field5: e.target.value})}
                      />
                    </div>
                  </div>
                </div>


                {/* Media & Location Fields */}
                <div className="space-y-4 pt-4 border-t mt-4">
                  <h3 className="font-semibold text-slate-900">Media & Location (Optional)</h3>
                  
                  {/* Media Type Selector */}
                  <div>
                    <Label htmlFor="mediaType">Select Type (only ONE)</Label>
                    <Select value={mediaType} onValueChange={setMediaType}>
                      <SelectTrigger>
                        <SelectValue placeholder="None" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="none">None</SelectItem>
                        <SelectItem value="image">📷 Image</SelectItem>
                        <SelectItem value="video">🎥 Video</SelectItem>
                        <SelectItem value="document">📄 Document</SelectItem>
                        <SelectItem value="location">📍 Location</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>

                  {/* Show fields based on type */}
                  {mediaType === 'image' && (
                    <div className="space-y-2">
                      <Label htmlFor="header_image">Image URL</Label>
                      <Input
                        id="header_image"
                        placeholder="https://domain.com/uploads/images/..."
                        value={formData.header_image}
                        onChange={(e) => setFormData({...formData, header_image: e.target.value})}
                      />
                    </div>
                  )}

                  {mediaType === 'video' && (
                    <div className="space-y-2">
                      <Label htmlFor="header_video">Video URL</Label>
                      <Input
                        id="header_video"
                        placeholder="https://domain.com/uploads/videos/..."
                        value={formData.header_video}
                        onChange={(e) => setFormData({...formData, header_video: e.target.value})}
                      />
                    </div>
                  )}

                  {mediaType === 'document' && (
                    <div className="space-y-2">
                      <Label htmlFor="header_document">Document URL</Label>
                      <Input
                        id="header_document"
                        placeholder="https://domain.com/uploads/documents/..."
                        value={formData.header_document}
                        onChange={(e) => setFormData({...formData, header_document: e.target.value})}
                      />
                      <Label htmlFor="header_document_name">Document Name</Label>
                      <Input
                        id="header_document_name"
                        placeholder="e.g., catalog.pdf"
                        value={formData.header_document_name}
                        onChange={(e) => setFormData({...formData, header_document_name: e.target.value})}
                      />
                    </div>
                  )}

                  {mediaType === 'location' && (
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <Label htmlFor="location_latitude">Latitude</Label>
                        <Input
                          id="location_latitude"
                          placeholder="e.g., 22.22"
                          value={formData.location_latitude}
                          onChange={(e) => setFormData({...formData, location_latitude: e.target.value})}
                        />
                      </div>
                      <div>
                        <Label htmlFor="location_longitude">Longitude</Label>
                        <Input
                          id="location_longitude"
                          placeholder="e.g., 22.22"
                          value={formData.location_longitude}
                          onChange={(e) => setFormData({...formData, location_longitude: e.target.value})}
                        />
                      </div>
                      <div>
                        <Label htmlFor="location_name">Location Name</Label>
                        <Input
                          id="location_name"
                          placeholder="e.g., Our Store"
                          value={formData.location_name}
                          onChange={(e) => setFormData({...formData, location_name: e.target.value})}
                        />
                      </div>
                      <div>
                        <Label htmlFor="location_address">Address</Label>
                        <Input
                          id="location_address"
                          placeholder="e.g., 123 Main St"
                          value={formData.location_address}
                          onChange={(e) => setFormData({...formData, location_address: e.target.value})}
                        />
                      </div>
                    </div>
                  )}

                  <p className="text-xs text-slate-500 pt-2">
                    💡 Upload in Send Messages → Copy URL → Paste here
                  </p>
                </div>


                <div className="flex space-x-2 pt-4">
                  <Button type="submit" className="flex-1">
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
                  <Plus className="h-4 w-4 mr-2" />
                  Create First Template
                </Button>
              </div>
            </CardContent>
          </Card>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {templates.map((template) => (
              <Card key={template.id} className="shadow-lg border-0 hover:shadow-xl transition-shadow">
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
                    {template.field1 && (
                      <div className="text-sm">
                        <span className="font-medium text-slate-600">Field 1:</span>
                        <p className="text-slate-700 truncate">{template.field1}</p>
                      </div>
                    )}
                    {template.field2 && (
                      <div className="text-sm">
                        <span className="font-medium text-slate-600">Field 2:</span>
                        <p className="text-slate-700 truncate">{template.field2}</p>
                      </div>
                    )}
                    {template.field3 && (
                      <div className="text-sm">
                        <span className="font-medium text-slate-600">Field 3:</span>
                        <p className="text-slate-700 truncate">{template.field3}</p>
                      </div>
                    )}
                  </div>
                  
                  <div className="flex space-x-2">
                    <Button
                      variant="outline"
                      size="sm"
                      className="flex-1"
                      onClick={() => handleOpenDialog(template)}
                    >
                      <Edit className="h-4 w-4 mr-1" />
                      Edit
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      className="text-red-600 hover:text-red-700 hover:bg-red-50"
                      onClick={() => handleDelete(template.id)}
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </div>
    </Layout>
  );
};

export default MyTemplates;
