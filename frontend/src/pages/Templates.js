import React, { useState, useEffect } from 'react';
import Layout from '../components/Layout';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { FileText, RefreshCw } from 'lucide-react';
import { toast } from 'sonner';
import api from '../utils/api';

const Templates = ({ user, onLogout }) => {
  const [templates, setTemplates] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchTemplates();
  }, []);

  const fetchTemplates = async () => {
    setLoading(true);
    try {
      const response = await api.get('/templates');
      if (response.data.templates) {
        setTemplates(response.data.templates);
      } else {
        setTemplates([]);
      }
    } catch (error) {
      if (error.response?.status === 400) {
        toast.error('Please configure your BizChat API token in Settings first');
      } else {
        toast.error('Failed to fetch templates');
      }
      setTemplates([]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Layout user={user} onLogout={onLogout}>
      <div className="space-y-6">
        <div className="flex justify-between items-center">
          <div>
            <h1 className="text-3xl sm:text-4xl font-bold text-slate-900">Message Templates</h1>
            <p className="text-slate-600 mt-1">View your approved WhatsApp message templates</p>
          </div>
          <Button onClick={fetchTemplates} variant="outline" data-testid="refresh-templates-button">
            <RefreshCw className="h-4 w-4 mr-2" />
            Refresh
          </Button>
        </div>

        {loading ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {[1, 2, 3].map((i) => (
              <Card key={i} className="shadow-lg border-0">
                <CardHeader>
                  <div className="h-6 bg-slate-200 rounded animate-shimmer mb-2"></div>
                  <div className="h-4 bg-slate-100 rounded animate-shimmer w-3/4"></div>
                </CardHeader>
                <CardContent>
                  <div className="h-20 bg-slate-50 rounded animate-shimmer"></div>
                </CardContent>
              </Card>
            ))}
          </div>
        ) : templates.length === 0 ? (
          <Card className="shadow-lg border-0">
            <CardContent className="py-12">
              <div className="text-center">
                <FileText className="h-16 w-16 text-slate-300 mx-auto mb-4" />
                <h3 className="text-lg font-medium text-slate-900 mb-2">No Templates Found</h3>
                <p className="text-slate-600 mb-4">
                  You don't have any approved templates yet. Please create and get templates approved in your
                  BizChat dashboard.
                </p>
                <p className="text-sm text-slate-500">
                  Make sure you've configured your BizChat API token in Settings.
                </p>
              </div>
            </CardContent>
          </Card>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {templates.map((template, index) => (
              <Card key={index} className="shadow-lg border-0 hover:shadow-xl transition-shadow" data-testid={`template-card-${index}`}>
                <CardHeader>
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <CardTitle className="text-lg">{template.name || `Template ${index + 1}`}</CardTitle>
                      <CardDescription className="mt-1">
                        {template.language || 'English'}
                      </CardDescription>
                    </div>
                    <Badge
                      variant={template.status === 'APPROVED' ? 'success' : 'secondary'}
                      className="ml-2"
                    >
                      {template.status || 'Unknown'}
                    </Badge>
                  </div>
                </CardHeader>
                <CardContent>
                  <div className="space-y-3">
                    {template.components && template.components.length > 0 ? (
                      <div>
                        <p className="text-sm font-medium text-slate-700 mb-2">Components:</p>
                        <div className="space-y-2">
                          {template.components.map((component, i) => (
                            <div key={i} className="bg-slate-50 rounded-lg p-3">
                              <p className="text-xs font-medium text-slate-600 uppercase mb-1">
                                {component.type}
                              </p>
                              {component.text && (
                                <p className="text-sm text-slate-700">{component.text}</p>
                              )}
                              {component.format && (
                                <p className="text-xs text-slate-500 mt-1">Format: {component.format}</p>
                              )}
                            </div>
                          ))}
                        </div>
                      </div>
                    ) : (
                      <p className="text-sm text-slate-500">Template details not available</p>
                    )}

                    {template.category && (
                      <div className="pt-2 border-t border-slate-200">
                        <p className="text-xs text-slate-500">
                          Category: <span className="font-medium text-slate-700">{template.category}</span>
                        </p>
                      </div>
                    )}
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

export default Templates;