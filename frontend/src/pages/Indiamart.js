import React, { useState, useEffect, useCallback } from 'react';
import Layout from '../components/Layout';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';
import { Switch } from '@/components/ui/switch';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger, DialogFooter } from '@/components/ui/dialog';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { 
  Megaphone, Settings, Copy, RefreshCw, Send, Trash2, Eye, 
  Clock, Check, X, AlertCircle, ChevronLeft, ChevronRight,
  Users, MessageSquare, TrendingUp, Loader2
} from 'lucide-react';
import { toast } from 'sonner';
import api from '../utils/api';

const Indiamart = ({ user, onLogout }) => {
  const [loading, setLoading] = useState(true);
  const [settings, setSettings] = useState(null);
  const [webhookUrl, setWebhookUrl] = useState('');
  const [leads, setLeads] = useState([]);
  const [stats, setStats] = useState({});
  const [pagination, setPagination] = useState({ page: 1, totalPages: 1, total: 0 });
  const [selectedLead, setSelectedLead] = useState(null);
  const [settingsForm, setSettingsForm] = useState({});
  const [showSettingsDialog, setShowSettingsDialog] = useState(false);
  const [saving, setSaving] = useState(false);
  const [statusFilter, setStatusFilter] = useState('all');

  const fetchSettings = useCallback(async () => {
    try {
      const response = await api.get('/indiamart/settings');
      setSettings(response.data.settings);
      setWebhookUrl(response.data.webhookUrl);
      setSettingsForm(response.data.settings);
    } catch (error) {
      console.error('Failed to fetch settings:', error);
    }
  }, []);

  const fetchLeads = useCallback(async (page = 1) => {
    try {
      const params = new URLSearchParams({ page: page.toString(), limit: '15' });
      if (statusFilter && statusFilter !== 'all') params.append('status', statusFilter);
      
      const response = await api.get(`/indiamart/leads?${params}`);
      setLeads(response.data.leads);
      setStats(response.data.stats);
      setPagination({
        page: response.data.page,
        totalPages: response.data.totalPages,
        total: response.data.total
      });
    } catch (error) {
      console.error('Failed to fetch leads:', error);
    }
  }, [statusFilter]);

  useEffect(() => {
    const loadData = async () => {
      setLoading(true);
      await Promise.all([fetchSettings(), fetchLeads()]);
      setLoading(false);
    };
    loadData();
  }, [fetchSettings, fetchLeads]);

  useEffect(() => {
    fetchLeads(1);
  }, [statusFilter, fetchLeads]);

  const handleSaveSettings = async () => {
    setSaving(true);
    try {
      await api.put('/indiamart/settings', settingsForm);
      toast.success('Settings saved successfully');
      setShowSettingsDialog(false);
      fetchSettings();
    } catch (error) {
      toast.error('Failed to save settings');
    } finally {
      setSaving(false);
    }
  };

  const handleCopyWebhook = () => {
    navigator.clipboard.writeText(webhookUrl);
    toast.success('Webhook URL copied to clipboard');
  };

  const handleRegenerateSecret = async () => {
    try {
      await api.post('/indiamart/settings/regenerate-secret');
      toast.success('Webhook secret regenerated');
      fetchSettings();
    } catch (error) {
      toast.error('Failed to regenerate secret');
    }
  };

  const handleResendMessage = async (leadId) => {
    try {
      await api.post(`/indiamart/leads/${leadId}/resend`);
      toast.success('Message queued for sending');
      fetchLeads(pagination.page);
    } catch (error) {
      toast.error('Failed to resend message');
    }
  };

  const handleDeleteLead = async (leadId) => {
    if (!window.confirm('Delete this lead?')) return;
    try {
      await api.delete(`/indiamart/leads/${leadId}`);
      toast.success('Lead deleted');
      fetchLeads(pagination.page);
    } catch (error) {
      toast.error('Failed to delete lead');
    }
  };

  const handleUpdateLeadStatus = async (leadId, status) => {
    try {
      await api.put(`/indiamart/leads/${leadId}`, { status });
      toast.success('Lead status updated');
      fetchLeads(pagination.page);
      setSelectedLead(null);
    } catch (error) {
      toast.error('Failed to update lead');
    }
  };

  const getStatusBadge = (status) => {
    const statusConfig = {
      new: { label: 'New', variant: 'default', className: 'bg-blue-100 text-blue-700' },
      message_sent: { label: 'Sent', variant: 'outline', className: 'bg-green-100 text-green-700' },
      message_failed: { label: 'Failed', variant: 'destructive', className: '' },
      followed_up: { label: 'Followed Up', variant: 'outline', className: 'bg-purple-100 text-purple-700' },
      converted: { label: 'Converted', variant: 'outline', className: 'bg-emerald-100 text-emerald-700' },
      closed: { label: 'Closed', variant: 'secondary', className: '' },
    };
    const config = statusConfig[status] || { label: status, variant: 'secondary', className: '' };
    return <Badge variant={config.variant} className={config.className}>{config.label}</Badge>;
  };

  if (loading) {
    return (
      <Layout user={user} onLogout={onLogout}>
        <div className="flex items-center justify-center h-64">
          <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
        </div>
      </Layout>
    );
  }

  return (
    <Layout user={user} onLogout={onLogout}>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
          <div>
            <h1 className="text-2xl font-bold text-slate-900 flex items-center gap-2">
              <Megaphone className="h-6 w-6 text-orange-500" />
              Indiamart Leads
            </h1>
            <p className="text-slate-600 text-sm mt-1">
              Auto-respond to leads from Indiamart
            </p>
          </div>
          <Button 
            onClick={() => setShowSettingsDialog(true)}
            className="bg-blue-600 hover:bg-blue-700"
            data-testid="indiamart-settings-btn"
          >
            <Settings className="h-4 w-4 mr-2" />
            Settings
          </Button>
        </div>

        {/* Stats Cards */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          <Card className="bg-gradient-to-br from-blue-50 to-blue-100/50">
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs text-blue-600 font-medium">Total Leads</p>
                  <p className="text-2xl font-bold text-blue-900">{stats.total || 0}</p>
                </div>
                <Users className="h-8 w-8 text-blue-400" />
              </div>
            </CardContent>
          </Card>
          <Card className="bg-gradient-to-br from-green-50 to-green-100/50">
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs text-green-600 font-medium">Messages Sent</p>
                  <p className="text-2xl font-bold text-green-900">{stats.messageSent || 0}</p>
                </div>
                <MessageSquare className="h-8 w-8 text-green-400" />
              </div>
            </CardContent>
          </Card>
          <Card className="bg-gradient-to-br from-amber-50 to-amber-100/50">
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs text-amber-600 font-medium">New</p>
                  <p className="text-2xl font-bold text-amber-900">{stats.new || 0}</p>
                </div>
                <AlertCircle className="h-8 w-8 text-amber-400" />
              </div>
            </CardContent>
          </Card>
          <Card className="bg-gradient-to-br from-emerald-50 to-emerald-100/50">
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs text-emerald-600 font-medium">Converted</p>
                  <p className="text-2xl font-bold text-emerald-900">{stats.converted || 0}</p>
                </div>
                <TrendingUp className="h-8 w-8 text-emerald-400" />
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Integration Status */}
        {!settings?.isActive && (
          <Card className="border-amber-200 bg-amber-50">
            <CardContent className="p-4">
              <div className="flex items-start gap-3">
                <AlertCircle className="h-5 w-5 text-amber-600 mt-0.5" />
                <div>
                  <p className="font-medium text-amber-800">Integration Not Active</p>
                  <p className="text-sm text-amber-700">
                    Enable the integration in Settings and add the webhook URL to your Indiamart account.
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Leads Table */}
        <Card>
          <CardHeader className="pb-3">
            <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3">
              <div>
                <CardTitle className="text-lg">Leads</CardTitle>
                <CardDescription>View and manage your Indiamart leads</CardDescription>
              </div>
              <div className="flex items-center gap-2">
                <Select value={statusFilter} onValueChange={setStatusFilter}>
                  <SelectTrigger className="w-36 h-9">
                    <SelectValue placeholder="All Status" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All Status</SelectItem>
                    <SelectItem value="new">New</SelectItem>
                    <SelectItem value="message_sent">Sent</SelectItem>
                    <SelectItem value="message_failed">Failed</SelectItem>
                    <SelectItem value="converted">Converted</SelectItem>
                  </SelectContent>
                </Select>
                <Button variant="outline" size="sm" onClick={() => fetchLeads(pagination.page)}>
                  <RefreshCw className="h-4 w-4" />
                </Button>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            {leads.length === 0 ? (
              <div className="text-center py-12 text-slate-500">
                <Megaphone className="h-12 w-12 mx-auto mb-3 text-slate-300" />
                <p>No leads yet</p>
                <p className="text-sm">Leads from Indiamart will appear here</p>
              </div>
            ) : (
              <>
                <div className="overflow-x-auto">
                  <table className="w-full" data-testid="leads-table">
                    <thead>
                      <tr className="border-b border-slate-200">
                        <th className="text-left py-3 px-3 text-xs font-medium text-slate-600 uppercase">Lead</th>
                        <th className="text-left py-3 px-3 text-xs font-medium text-slate-600 uppercase hidden sm:table-cell">Product</th>
                        <th className="text-left py-3 px-3 text-xs font-medium text-slate-600 uppercase">Status</th>
                        <th className="text-left py-3 px-3 text-xs font-medium text-slate-600 uppercase hidden md:table-cell">Messages</th>
                        <th className="text-left py-3 px-3 text-xs font-medium text-slate-600 uppercase">Actions</th>
                      </tr>
                    </thead>
                    <tbody>
                      {leads.map((lead) => (
                        <tr key={lead.id} className="border-b border-slate-100 hover:bg-slate-50">
                          <td className="py-3 px-3">
                            <div>
                              <p className="font-medium text-slate-900 text-sm">{lead.senderName}</p>
                              <p className="text-xs text-slate-500">{lead.senderMobile}</p>
                              {lead.senderCity && (
                                <p className="text-xs text-slate-400">{lead.senderCity}</p>
                              )}
                            </div>
                          </td>
                          <td className="py-3 px-3 hidden sm:table-cell">
                            <p className="text-sm text-slate-700 truncate max-w-[200px]">
                              {lead.productName || '-'}
                            </p>
                          </td>
                          <td className="py-3 px-3">
                            {getStatusBadge(lead.status)}
                          </td>
                          <td className="py-3 px-3 hidden md:table-cell">
                            <span className="text-sm text-slate-600">{lead.messagesSent || 0}</span>
                          </td>
                          <td className="py-3 px-3">
                            <div className="flex items-center gap-1">
                              <Button
                                variant="ghost"
                                size="sm"
                                className="h-8 w-8 p-0"
                                onClick={() => setSelectedLead(lead)}
                                title="View Details"
                              >
                                <Eye className="h-4 w-4" />
                              </Button>
                              <Button
                                variant="ghost"
                                size="sm"
                                className="h-8 w-8 p-0"
                                onClick={() => handleResendMessage(lead.id)}
                                title="Resend Message"
                              >
                                <Send className="h-4 w-4" />
                              </Button>
                              <Button
                                variant="ghost"
                                size="sm"
                                className="h-8 w-8 p-0 text-red-600"
                                onClick={() => handleDeleteLead(lead.id)}
                                title="Delete"
                              >
                                <Trash2 className="h-4 w-4" />
                              </Button>
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                
                {/* Pagination */}
                {pagination.totalPages > 1 && (
                  <div className="flex items-center justify-between mt-4 pt-4 border-t">
                    <p className="text-sm text-slate-500">
                      Page {pagination.page} of {pagination.totalPages}
                    </p>
                    <div className="flex items-center gap-2">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => fetchLeads(pagination.page - 1)}
                        disabled={pagination.page <= 1}
                      >
                        <ChevronLeft className="h-4 w-4" />
                      </Button>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => fetchLeads(pagination.page + 1)}
                        disabled={pagination.page >= pagination.totalPages}
                      >
                        <ChevronRight className="h-4 w-4" />
                      </Button>
                    </div>
                  </div>
                )}
              </>
            )}
          </CardContent>
        </Card>

        {/* Settings Dialog */}
        <Dialog open={showSettingsDialog} onOpenChange={setShowSettingsDialog}>
          <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
            <DialogHeader>
              <DialogTitle>Indiamart Integration Settings</DialogTitle>
              <DialogDescription>
                Configure auto-reply for Indiamart leads
              </DialogDescription>
            </DialogHeader>

            <Tabs defaultValue="webhook" className="mt-4">
              <TabsList className="grid w-full grid-cols-3">
                <TabsTrigger value="webhook">Webhook</TabsTrigger>
                <TabsTrigger value="message">Message</TabsTrigger>
                <TabsTrigger value="recurring">Recurring</TabsTrigger>
              </TabsList>

              <TabsContent value="webhook" className="space-y-4 mt-4">
                <div className="flex items-center justify-between p-4 bg-slate-50 rounded-lg">
                  <div>
                    <Label className="text-sm font-medium">Integration Active</Label>
                    <p className="text-xs text-slate-500">Enable to receive leads</p>
                  </div>
                  <Switch
                    checked={settingsForm.isActive || false}
                    onCheckedChange={(checked) => setSettingsForm({...settingsForm, isActive: checked})}
                  />
                </div>

                <div className="space-y-2">
                  <Label>Webhook URL</Label>
                  <div className="flex gap-2">
                    <Input value={webhookUrl} readOnly className="font-mono text-xs" />
                    <Button variant="outline" size="sm" onClick={handleCopyWebhook}>
                      <Copy className="h-4 w-4" />
                    </Button>
                  </div>
                  <p className="text-xs text-slate-500">
                    Add this URL to your Indiamart Seller account under Lead Manager → CRM Integration
                  </p>
                </div>

                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <Label>Webhook Secret</Label>
                    <Button variant="ghost" size="sm" onClick={handleRegenerateSecret}>
                      <RefreshCw className="h-3 w-3 mr-1" />
                      Regenerate
                    </Button>
                  </div>
                  <Input value={settingsForm.webhookSecret || ''} readOnly className="font-mono" />
                </div>
              </TabsContent>

              <TabsContent value="message" className="space-y-4 mt-4">
                <div className="flex items-center justify-between p-4 bg-slate-50 rounded-lg">
                  <div>
                    <Label className="text-sm font-medium">Auto-Reply Enabled</Label>
                    <p className="text-xs text-slate-500">Send message when lead arrives</p>
                  </div>
                  <Switch
                    checked={settingsForm.autoReplyEnabled || false}
                    onCheckedChange={(checked) => setSettingsForm({...settingsForm, autoReplyEnabled: checked})}
                  />
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label>Template Name</Label>
                    <Input
                      value={settingsForm.templateName || ''}
                      onChange={(e) => setSettingsForm({...settingsForm, templateName: e.target.value})}
                      placeholder="your_template_name"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label>Variable Count</Label>
                    <Select
                      value={String(settingsForm.templateVariableCount || 1)}
                      onValueChange={(v) => setSettingsForm({...settingsForm, templateVariableCount: parseInt(v)})}
                    >
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {[1,2,3,4,5].map(n => (
                          <SelectItem key={n} value={String(n)}>{n} variable{n>1?'s':''}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                </div>

                <div className="space-y-2">
                  <Label>Send Delay (minutes)</Label>
                  <Input
                    type="number"
                    min="0"
                    value={settingsForm.sendDelay || 0}
                    onChange={(e) => setSettingsForm({...settingsForm, sendDelay: parseInt(e.target.value) || 0})}
                  />
                  <p className="text-xs text-slate-500">0 = send immediately</p>
                </div>

                <div className="space-y-3">
                  <Label>Message Variables</Label>
                  <p className="text-xs text-slate-500">
                    Available placeholders: {'{name}'}, {'{product}'}, {'{message}'}, {'{company}'}, {'{city}'}
                  </p>
                  
                  {[1, 2, 3].slice(0, settingsForm.templateVariableCount || 1).map((n) => (
                    <div key={n} className="space-y-1">
                      <Label className="text-xs">Field {n}</Label>
                      <Textarea
                        value={settingsForm[`messageField${n}`] || ''}
                        onChange={(e) => setSettingsForm({...settingsForm, [`messageField${n}`]: e.target.value})}
                        placeholder={n === 1 ? "Hi {name}, thanks for your inquiry about {product}..." : ""}
                        rows={2}
                      />
                    </div>
                  ))}
                </div>

                <div className="space-y-2">
                  <Label>Header Image URL (optional)</Label>
                  <Input
                    value={settingsForm.headerImage || ''}
                    onChange={(e) => setSettingsForm({...settingsForm, headerImage: e.target.value})}
                    placeholder="https://..."
                  />
                </div>
              </TabsContent>

              <TabsContent value="recurring" className="space-y-4 mt-4">
                <div className="flex items-center justify-between p-4 bg-slate-50 rounded-lg">
                  <div>
                    <Label className="text-sm font-medium">Recurring Messages</Label>
                    <p className="text-xs text-slate-500">Send follow-up messages</p>
                  </div>
                  <Switch
                    checked={settingsForm.recurringEnabled || false}
                    onCheckedChange={(checked) => setSettingsForm({...settingsForm, recurringEnabled: checked})}
                  />
                </div>

                {settingsForm.recurringEnabled && (
                  <>
                    <div className="grid grid-cols-2 gap-4">
                      <div className="space-y-2">
                        <Label>Interval (hours)</Label>
                        <Input
                          type="number"
                          min="1"
                          value={settingsForm.recurringIntervalHours || 24}
                          onChange={(e) => setSettingsForm({...settingsForm, recurringIntervalHours: parseInt(e.target.value) || 24})}
                        />
                      </div>
                      <div className="space-y-2">
                        <Label>Max Messages</Label>
                        <Input
                          type="number"
                          min="1"
                          max="10"
                          value={settingsForm.recurringMaxCount || 3}
                          onChange={(e) => setSettingsForm({...settingsForm, recurringMaxCount: parseInt(e.target.value) || 3})}
                        />
                      </div>
                    </div>

                    <div className="flex items-center justify-between p-3 bg-slate-50 rounded-lg">
                      <div>
                        <Label className="text-sm">Stop on Reply</Label>
                        <p className="text-xs text-slate-500">Stop recurring if buyer replies</p>
                      </div>
                      <Switch
                        checked={settingsForm.recurringStopOnReply !== false}
                        onCheckedChange={(checked) => setSettingsForm({...settingsForm, recurringStopOnReply: checked})}
                      />
                    </div>
                  </>
                )}
              </TabsContent>
            </Tabs>

            <DialogFooter className="mt-6">
              <Button variant="outline" onClick={() => setShowSettingsDialog(false)}>
                Cancel
              </Button>
              <Button onClick={handleSaveSettings} disabled={saving}>
                {saving && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
                Save Settings
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>

        {/* Lead Details Dialog */}
        <Dialog open={!!selectedLead} onOpenChange={() => setSelectedLead(null)}>
          <DialogContent className="max-w-lg">
            <DialogHeader>
              <DialogTitle>Lead Details</DialogTitle>
            </DialogHeader>

            {selectedLead && (
              <div className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <Label className="text-xs text-slate-500">Name</Label>
                    <p className="font-medium">{selectedLead.senderName}</p>
                  </div>
                  <div>
                    <Label className="text-xs text-slate-500">Phone</Label>
                    <p className="font-medium">{selectedLead.senderMobile}</p>
                  </div>
                  <div>
                    <Label className="text-xs text-slate-500">Email</Label>
                    <p>{selectedLead.senderEmail || '-'}</p>
                  </div>
                  <div>
                    <Label className="text-xs text-slate-500">Company</Label>
                    <p>{selectedLead.senderCompany || '-'}</p>
                  </div>
                  <div>
                    <Label className="text-xs text-slate-500">City</Label>
                    <p>{selectedLead.senderCity || '-'}</p>
                  </div>
                  <div>
                    <Label className="text-xs text-slate-500">Status</Label>
                    <p>{getStatusBadge(selectedLead.status)}</p>
                  </div>
                </div>

                <div>
                  <Label className="text-xs text-slate-500">Product</Label>
                  <p>{selectedLead.productName || '-'}</p>
                </div>

                <div>
                  <Label className="text-xs text-slate-500">Message</Label>
                  <p className="text-sm bg-slate-50 p-3 rounded-lg">
                    {selectedLead.queryMessage || 'No message'}
                  </p>
                </div>

                {selectedLead.lastMessageError && (
                  <div className="p-3 bg-red-50 rounded-lg">
                    <Label className="text-xs text-red-600">Last Error</Label>
                    <p className="text-sm text-red-700">{selectedLead.lastMessageError}</p>
                  </div>
                )}

                <div className="flex flex-wrap gap-2 pt-4 border-t">
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => handleUpdateLeadStatus(selectedLead.id, 'followed_up')}
                  >
                    <Check className="h-3 w-3 mr-1" />
                    Mark Followed Up
                  </Button>
                  <Button
                    size="sm"
                    variant="outline"
                    className="text-green-600"
                    onClick={() => handleUpdateLeadStatus(selectedLead.id, 'converted')}
                  >
                    <TrendingUp className="h-3 w-3 mr-1" />
                    Mark Converted
                  </Button>
                  <Button
                    size="sm"
                    variant="outline"
                    className="text-slate-500"
                    onClick={() => handleUpdateLeadStatus(selectedLead.id, 'closed')}
                  >
                    <X className="h-3 w-3 mr-1" />
                    Close
                  </Button>
                </div>
              </div>
            )}
          </DialogContent>
        </Dialog>
      </div>
    </Layout>
  );
};

export default Indiamart;
