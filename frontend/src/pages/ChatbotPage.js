import React, { useState, useEffect, useCallback } from 'react';
import Layout from '../components/Layout';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Switch } from '@/components/ui/switch';
import { Textarea } from '@/components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
  Bot, Settings, Users2, Plus, Trash2, Edit2,
  Download, Search, Loader2, ChevronUp, ChevronDown,
  Eye, Copy, Link, Zap, MessageSquare
} from 'lucide-react';
import { toast } from 'sonner';
import api from '../utils/api';

// ===== Settings Tab =====
const SettingsTab = () => {
  const [settings, setSettings] = useState(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => { fetchSettings(); }, []);

  const fetchSettings = async () => {
    try {
      const res = await api.get('/chatbot/settings');
      setSettings(res.data);
    } catch { toast.error('Failed to load settings'); }
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      await api.put('/chatbot/settings', settings);
      toast.success('Settings saved');
    } catch { toast.error('Failed to save'); }
    finally { setSaving(false); }
  };

  if (!settings) return <div className="text-center py-8 text-slate-500">Loading...</div>;

  const copyWebhookUrl = () => {
    if (settings.webhookUrl) {
      navigator.clipboard.writeText(settings.webhookUrl);
      toast.success('Webhook URL copied!');
    }
  };

  return (
    <div className="space-y-6">
      {settings.webhookUrl && (
        <Card className="border-blue-200 bg-blue-50/50">
          <CardHeader className="pb-2">
            <CardTitle className="text-lg flex items-center gap-2">
              <Link className="h-5 w-5 text-blue-600" /> Your Webhook URL
            </CardTitle>
            <CardDescription>Set this URL in your BizChat settings to receive messages</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex items-center gap-2">
              <Input data-testid="webhook-url" readOnly value={settings.webhookUrl} className="font-mono text-xs bg-white" />
              <Button variant="outline" size="sm" onClick={copyWebhookUrl} className="shrink-0">
                <Copy className="h-4 w-4 mr-1" /> Copy
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      <Card>
        <CardHeader>
          <CardTitle className="text-lg flex items-center gap-2">
            <Bot className="h-5 w-5" /> Chatbot Status
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <Label className="text-sm font-medium">Enable Chatbot</Label>
              <p className="text-xs text-slate-500">When enabled, trigger keywords will activate your flows</p>
            </div>
            <Switch
              data-testid="chatbot-toggle"
              checked={settings.isActive}
              onCheckedChange={(v) => setSettings({ ...settings, isActive: v })}
            />
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Notifications</CardTitle>
          <CardDescription>Default WhatsApp number to receive lead notifications</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label>Default Notify Phone (with country code)</Label>
            <Input
              data-testid="default-notify-phone"
              placeholder="e.g. 919876543210"
              value={settings.defaultNotifyPhone || ''}
              onChange={(e) => setSettings({ ...settings, defaultNotifyPhone: e.target.value })}
            />
            <p className="text-xs text-slate-500">Each flow can override this with its own number</p>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Follow-up Settings</CardTitle>
          <CardDescription>If a client stops responding mid-flow</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label>Follow-up Delay (minutes)</Label>
              <Input
                data-testid="followup-delay"
                type="number" min="1"
                value={settings.followUpDelayMinutes}
                onChange={(e) => setSettings({ ...settings, followUpDelayMinutes: parseInt(e.target.value) || 15 })}
              />
            </div>
            <div className="space-y-2">
              <Label>Max Follow-ups</Label>
              <Input
                data-testid="max-followups"
                type="number" min="0" max="10"
                value={settings.maxFollowUps}
                onChange={(e) => setSettings({ ...settings, maxFollowUps: parseInt(e.target.value) || 2 })}
              />
            </div>
          </div>
          <div className="space-y-2">
            <Label>Follow-up Message</Label>
            <Textarea
              data-testid="followup-message"
              value={settings.followUpMessage}
              onChange={(e) => setSettings({ ...settings, followUpMessage: e.target.value })}
              rows={2}
            />
          </div>
        </CardContent>
      </Card>

      <Button data-testid="save-settings-btn" onClick={handleSave} disabled={saving} className="w-full">
        {saving && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
        Save Settings
      </Button>
    </div>
  );
};

// ===== Flows Tab =====
const FlowsTab = () => {
  const [flows, setFlows] = useState([]);
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingFlow, setEditingFlow] = useState(null);
  const [form, setForm] = useState({
    name: '', triggerKeywords: [], greetingMessage: '',
    completionMessage: 'Thank you! We have received your details. Our team will get back to you shortly.',
    questions: [], notifyPhone: ''
  });
  const [newTrigger, setNewTrigger] = useState('');
  const [newQuestion, setNewQuestion] = useState({ questionText: '', questionType: 'text', options: [] });
  const [newOption, setNewOption] = useState('');
  const [saving, setSaving] = useState(false);

  const fetchFlows = useCallback(async () => {
    try {
      const res = await api.get('/chatbot/flows');
      setFlows(res.data.flows);
    } catch { toast.error('Failed to load flows'); }
    finally { setLoading(false); }
  }, []);

  useEffect(() => { fetchFlows(); }, [fetchFlows]);

  const openCreate = () => {
    setEditingFlow(null);
    setForm({
      name: '', triggerKeywords: [], greetingMessage: '',
      completionMessage: 'Thank you! We have received your details. Our team will get back to you shortly.',
      questions: [], notifyPhone: ''
    });
    setNewTrigger('');
    setNewQuestion({ questionText: '', questionType: 'text', options: [] });
    setNewOption('');
    setDialogOpen(true);
  };

  const openEdit = (flow) => {
    setEditingFlow(flow);
    setForm({
      name: flow.name,
      triggerKeywords: flow.triggerKeywords || [],
      greetingMessage: flow.greetingMessage || '',
      completionMessage: flow.completionMessage || '',
      questions: flow.questions || [],
      notifyPhone: flow.notifyPhone || ''
    });
    setNewTrigger('');
    setNewQuestion({ questionText: '', questionType: 'text', options: [] });
    setNewOption('');
    setDialogOpen(true);
  };

  const addTrigger = () => {
    if (!newTrigger.trim()) return;
    setForm({ ...form, triggerKeywords: [...form.triggerKeywords, newTrigger.trim()] });
    setNewTrigger('');
  };

  const removeTrigger = (idx) => {
    setForm({ ...form, triggerKeywords: form.triggerKeywords.filter((_, i) => i !== idx) });
  };

  const addQuestion = () => {
    if (!newQuestion.questionText.trim()) { toast.error('Question text required'); return; }
    const q = { ...newQuestion, id: crypto.randomUUID ? crypto.randomUUID() : Date.now().toString() };
    setForm({ ...form, questions: [...form.questions, q] });
    setNewQuestion({ questionText: '', questionType: 'text', options: [] });
    setNewOption('');
  };

  const removeQuestion = (idx) => {
    setForm({ ...form, questions: form.questions.filter((_, i) => i !== idx) });
  };

  const moveQuestion = (idx, dir) => {
    const newQ = [...form.questions];
    const swap = idx + dir;
    if (swap < 0 || swap >= newQ.length) return;
    [newQ[idx], newQ[swap]] = [newQ[swap], newQ[idx]];
    setForm({ ...form, questions: newQ });
  };

  const addOptionToNew = () => {
    if (!newOption.trim()) return;
    setNewQuestion({ ...newQuestion, options: [...newQuestion.options, newOption.trim()] });
    setNewOption('');
  };

  const removeOptionFromNew = (idx) => {
    setNewQuestion({ ...newQuestion, options: newQuestion.options.filter((_, i) => i !== idx) });
  };

  const handleSave = async () => {
    if (!form.name.trim()) { toast.error('Flow name is required'); return; }
    if (form.triggerKeywords.length === 0) { toast.error('At least one trigger keyword is required'); return; }
    setSaving(true);
    try {
      const payload = {
        ...form,
        greetingMessage: form.greetingMessage || null,
        notifyPhone: form.notifyPhone || null
      };
      if (editingFlow) {
        await api.put(`/chatbot/flows/${editingFlow.id}`, payload);
        toast.success('Flow updated');
      } else {
        await api.post('/chatbot/flows', payload);
        toast.success('Flow created');
      }
      setDialogOpen(false);
      fetchFlows();
    } catch { toast.error('Failed to save flow'); }
    finally { setSaving(false); }
  };

  const handleDelete = async (id) => {
    if (!window.confirm('Delete this flow?')) return;
    try {
      await api.delete(`/chatbot/flows/${id}`);
      toast.success('Flow deleted');
      fetchFlows();
    } catch { toast.error('Failed to delete'); }
  };

  const toggleActive = async (flow) => {
    try {
      await api.put(`/chatbot/flows/${flow.id}`, { isActive: !flow.isActive });
      fetchFlows();
    } catch { toast.error('Failed to update'); }
  };

  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center">
        <p className="text-sm text-slate-600">Each flow has a trigger keyword and a set of questions to collect lead data.</p>
        <Button data-testid="add-flow-btn" size="sm" onClick={openCreate}>
          <Plus className="h-4 w-4 mr-1" /> New Flow
        </Button>
      </div>

      {loading ? (
        <div className="text-center py-8 text-slate-500">Loading...</div>
      ) : flows.length === 0 ? (
        <Card className="border-dashed">
          <CardContent className="text-center py-12">
            <Zap className="h-10 w-10 mx-auto text-slate-300 mb-3" />
            <h3 className="font-medium text-slate-700 mb-1">No flows yet</h3>
            <p className="text-slate-500 text-sm mb-4">Create your first flow to start collecting leads via WhatsApp</p>
            <Button size="sm" onClick={openCreate}>
              <Plus className="h-4 w-4 mr-1" /> Create Flow
            </Button>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-3">
          {flows.map((flow) => (
            <Card key={flow.id} className="shadow-sm hover:shadow transition-shadow">
              <CardContent className="py-4">
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 flex-wrap">
                      <h3 className="font-semibold text-sm">{flow.name}</h3>
                      <Badge variant={flow.isActive ? "default" : "secondary"} className="text-xs">
                        {flow.isActive ? 'Active' : 'Inactive'}
                      </Badge>
                    </div>
                    <div className="flex flex-wrap gap-1 mt-2">
                      {flow.triggerKeywords?.map((kw, i) => (
                        <Badge key={i} variant="outline" className="text-xs bg-blue-50 text-blue-700 border-blue-200">
                          {kw}
                        </Badge>
                      ))}
                    </div>
                    <div className="flex gap-4 mt-2 text-xs text-slate-500">
                      <span>{flow.questions?.length || 0} questions</span>
                      {flow.greetingMessage && <span>Has greeting</span>}
                      {flow.notifyPhone && <span>Notify: {flow.notifyPhone}</span>}
                    </div>
                  </div>
                  <div className="flex gap-1 items-center">
                    <Switch
                      checked={flow.isActive}
                      onCheckedChange={() => toggleActive(flow)}
                      data-testid={`flow-toggle-${flow.id}`}
                    />
                    <Button variant="ghost" size="sm" className="h-8 w-8 p-0" onClick={() => openEdit(flow)}>
                      <Edit2 className="h-4 w-4" />
                    </Button>
                    <Button variant="ghost" size="sm" className="h-8 w-8 p-0 text-red-600" onClick={() => handleDelete(flow.id)}>
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                </div>

                {/* Preview questions */}
                {flow.questions?.length > 0 && (
                  <div className="mt-3 pt-3 border-t space-y-1.5">
                    {flow.questions.map((q, idx) => (
                      <div key={idx} className="flex items-start gap-2 text-xs">
                        <span className="text-slate-400 font-mono shrink-0">Q{idx + 1}</span>
                        <span className="text-slate-700">{q.questionText}</span>
                        <Badge variant="secondary" className="text-[10px] shrink-0 capitalize">{q.questionType}</Badge>
                        {q.options?.length > 0 && (
                          <span className="text-slate-400">({q.options.length} options)</span>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Create/Edit Flow Dialog */}
      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>{editingFlow ? 'Edit Flow' : 'New Flow'}</DialogTitle>
          </DialogHeader>
          <div className="space-y-5">
            {/* Flow Name */}
            <div className="space-y-2">
              <Label>Flow Name *</Label>
              <Input
                data-testid="flow-name-input"
                value={form.name}
                onChange={(e) => setForm({ ...form, name: e.target.value })}
                placeholder="e.g. WhatsApp API Inquiry"
              />
            </div>

            {/* Trigger Keywords */}
            <div className="space-y-2">
              <Label>Trigger Keywords *</Label>
              <p className="text-xs text-slate-500">When someone sends any of these words, this flow starts</p>
              <div className="flex flex-wrap gap-1 mb-2">
                {form.triggerKeywords.map((kw, i) => (
                  <Badge key={i} variant="secondary" className="flex items-center gap-1">
                    {kw}
                    <button onClick={() => removeTrigger(i)} className="ml-1 text-red-500 hover:text-red-700">&times;</button>
                  </Badge>
                ))}
              </div>
              <div className="flex gap-2">
                <Input
                  data-testid="trigger-keyword-input"
                  value={newTrigger}
                  onChange={(e) => setNewTrigger(e.target.value)}
                  placeholder="Type keyword and press Enter..."
                  onKeyDown={(e) => { if (e.key === 'Enter') { e.preventDefault(); addTrigger(); } }}
                />
                <Button variant="outline" size="sm" onClick={addTrigger}>Add</Button>
              </div>
            </div>

            {/* Greeting (optional) */}
            <div className="space-y-2">
              <Label>Greeting Message <span className="text-slate-400 text-xs">(optional)</span></Label>
              <Textarea
                data-testid="greeting-input"
                value={form.greetingMessage}
                onChange={(e) => setForm({ ...form, greetingMessage: e.target.value })}
                placeholder="e.g. Hello! Thanks for reaching out about our WhatsApp API service."
                rows={2}
              />
            </div>

            {/* Questions */}
            <div className="space-y-3">
              <Label>Questions</Label>
              <p className="text-xs text-slate-500">These will be asked sequentially after the greeting</p>

              {form.questions.length > 0 && (
                <div className="space-y-2 bg-slate-50 rounded-lg p-3">
                  {form.questions.map((q, idx) => (
                    <div key={idx} className="flex items-start gap-2 bg-white rounded p-2 border">
                      <div className="flex flex-col gap-0.5 pt-0.5">
                        <button onClick={() => moveQuestion(idx, -1)} disabled={idx === 0}
                          className="text-slate-400 hover:text-slate-600 disabled:opacity-30">
                          <ChevronUp className="h-3 w-3" />
                        </button>
                        <button onClick={() => moveQuestion(idx, 1)} disabled={idx === form.questions.length - 1}
                          className="text-slate-400 hover:text-slate-600 disabled:opacity-30">
                          <ChevronDown className="h-3 w-3" />
                        </button>
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <span className="text-xs font-mono text-slate-400">Q{idx + 1}</span>
                          <p className="text-sm truncate">{q.questionText}</p>
                        </div>
                        <div className="flex gap-1 mt-1 flex-wrap">
                          <Badge variant="secondary" className="text-[10px] capitalize">{q.questionType}</Badge>
                          {q.options?.map((opt, oi) => (
                            <span key={oi} className="text-[10px] bg-blue-50 text-blue-700 px-1.5 py-0.5 rounded">{opt}</span>
                          ))}
                        </div>
                      </div>
                      <button onClick={() => removeQuestion(idx)} className="text-red-400 hover:text-red-600 mt-1">
                        <Trash2 className="h-3.5 w-3.5" />
                      </button>
                    </div>
                  ))}
                </div>
              )}

              {/* Add new question inline */}
              <Card className="border-dashed">
                <CardContent className="py-3 space-y-3">
                  <div className="space-y-2">
                    <Input
                      data-testid="new-question-text"
                      value={newQuestion.questionText}
                      onChange={(e) => setNewQuestion({ ...newQuestion, questionText: e.target.value })}
                      placeholder="Type your question here..."
                    />
                  </div>
                  <div className="flex gap-2 items-end">
                    <div className="space-y-1 flex-1">
                      <Label className="text-xs">Answer Type</Label>
                      <Select value={newQuestion.questionType} onValueChange={(v) => setNewQuestion({ ...newQuestion, questionType: v, options: v === 'text' ? [] : newQuestion.options })}>
                        <SelectTrigger className="h-9 text-sm"><SelectValue /></SelectTrigger>
                        <SelectContent>
                          <SelectItem value="text">Text (free type)</SelectItem>
                          <SelectItem value="button">Buttons (up to 3)</SelectItem>
                          <SelectItem value="list">List (up to 10)</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                    <Button size="sm" variant="outline" onClick={addQuestion} data-testid="add-question-btn">
                      <Plus className="h-4 w-4 mr-1" /> Add
                    </Button>
                  </div>

                  {(newQuestion.questionType === 'button' || newQuestion.questionType === 'list') && (
                    <div className="space-y-2">
                      <div className="flex flex-wrap gap-1">
                        {newQuestion.options.map((opt, i) => (
                          <Badge key={i} variant="secondary" className="flex items-center gap-1 text-xs">
                            {opt}
                            <button onClick={() => removeOptionFromNew(i)} className="text-red-500">&times;</button>
                          </Badge>
                        ))}
                      </div>
                      <div className="flex gap-2">
                        <Input
                          data-testid="new-option-input"
                          value={newOption}
                          onChange={(e) => setNewOption(e.target.value)}
                          placeholder="Add option..."
                          className="h-8 text-sm"
                          onKeyDown={(e) => { if (e.key === 'Enter') { e.preventDefault(); addOptionToNew(); } }}
                        />
                        <Button variant="outline" size="sm" className="h-8" onClick={addOptionToNew}>Add</Button>
                      </div>
                    </div>
                  )}
                </CardContent>
              </Card>
            </div>

            {/* Completion Message */}
            <div className="space-y-2">
              <Label>Completion Message</Label>
              <Textarea
                data-testid="completion-input"
                value={form.completionMessage}
                onChange={(e) => setForm({ ...form, completionMessage: e.target.value })}
                rows={2}
              />
            </div>

            {/* Notify Phone */}
            <div className="space-y-2">
              <Label>Notify Phone <span className="text-slate-400 text-xs">(optional, overrides default)</span></Label>
              <Input
                data-testid="flow-notify-phone"
                value={form.notifyPhone}
                onChange={(e) => setForm({ ...form, notifyPhone: e.target.value })}
                placeholder="e.g. 919876543210"
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDialogOpen(false)}>Cancel</Button>
            <Button data-testid="save-flow-btn" onClick={handleSave} disabled={saving}>
              {saving && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
              Save Flow
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};

// ===== Leads Tab =====
const LeadsTab = () => {
  const [leads, setLeads] = useState([]);
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState({});
  const [flows, setFlows] = useState([]);
  const [filters, setFilters] = useState({ status: '', flow_id: '', search: '' });
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [expandedLead, setExpandedLead] = useState(null);
  const [exporting, setExporting] = useState(false);

  useEffect(() => {
    api.get('/chatbot/flows').then(res => setFlows(res.data.flows)).catch(() => {});
  }, []);

  const fetchLeads = useCallback(async () => {
    try {
      const params = { page, limit: 20 };
      if (filters.status) params.status = filters.status;
      if (filters.flow_id) params.flow_id = filters.flow_id;
      if (filters.search) params.search = filters.search;
      const res = await api.get('/chatbot/leads', { params });
      setLeads(res.data.leads);
      setStats(res.data.stats);
      setTotalPages(res.data.totalPages);
    } catch { toast.error('Failed to load leads'); }
    finally { setLoading(false); }
  }, [page, filters]);

  useEffect(() => { fetchLeads(); }, [fetchLeads]);

  const handleExport = async () => {
    setExporting(true);
    try {
      const params = {};
      if (filters.status) params.status = filters.status;
      if (filters.flow_id) params.flow_id = filters.flow_id;
      const res = await api.get('/chatbot/leads/export', { params, responseType: 'blob' });
      const url = window.URL.createObjectURL(new Blob([res.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', 'chatbot_leads.csv');
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
      toast.success('Leads exported');
    } catch { toast.error('Export failed'); }
    finally { setExporting(false); }
  };

  const handleStatusChange = async (leadId, newStatus) => {
    try {
      await api.put(`/chatbot/leads/${leadId}`, { status: newStatus });
      toast.success('Status updated');
      fetchLeads();
    } catch { toast.error('Failed to update'); }
  };

  const handleDelete = async (leadId) => {
    try {
      await api.delete(`/chatbot/leads/${leadId}`);
      toast.success('Lead deleted');
      fetchLeads();
    } catch { toast.error('Failed to delete'); }
  };

  const statusColors = {
    new: 'bg-blue-100 text-blue-700',
    contacted: 'bg-amber-100 text-amber-700',
    qualified: 'bg-green-100 text-green-700',
    unqualified: 'bg-red-100 text-red-700',
  };

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        {[
          { label: 'Total', value: stats.total || 0, color: 'slate' },
          { label: 'New', value: stats.new || 0, color: 'blue' },
          { label: 'Qualified', value: stats.qualified || 0, color: 'green' },
          { label: 'Contacted', value: stats.contacted || 0, color: 'amber' },
        ].map(s => (
          <Card key={s.label} className="shadow-sm">
            <CardContent className="py-3 text-center">
              <p className={`text-2xl font-bold text-${s.color}-700`}>{s.value}</p>
              <p className="text-xs text-slate-500">{s.label}</p>
            </CardContent>
          </Card>
        ))}
      </div>

      <div className="flex flex-col sm:flex-row gap-2">
        <Select value={filters.status || 'all'} onValueChange={(v) => { setFilters({ ...filters, status: v === 'all' ? '' : v }); setPage(1); }}>
          <SelectTrigger className="w-40 h-9 text-sm"><SelectValue placeholder="All Status" /></SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Status</SelectItem>
            <SelectItem value="new">New</SelectItem>
            <SelectItem value="contacted">Contacted</SelectItem>
            <SelectItem value="qualified">Qualified</SelectItem>
            <SelectItem value="unqualified">Unqualified</SelectItem>
          </SelectContent>
        </Select>
        <Select value={filters.flow_id || 'all'} onValueChange={(v) => { setFilters({ ...filters, flow_id: v === 'all' ? '' : v }); setPage(1); }}>
          <SelectTrigger className="w-48 h-9 text-sm"><SelectValue placeholder="All Flows" /></SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Flows</SelectItem>
            {flows.map(f => <SelectItem key={f.id} value={f.id}>{f.name}</SelectItem>)}
          </SelectContent>
        </Select>
        <div className="relative flex-1">
          <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-slate-400" />
          <Input className="pl-9 h-9 text-sm" placeholder="Search leads..." value={filters.search}
            onChange={(e) => { setFilters({ ...filters, search: e.target.value }); setPage(1); }}
          />
        </div>
        <Button data-testid="export-leads-btn" variant="outline" size="sm" onClick={handleExport} disabled={exporting}>
          {exporting ? <Loader2 className="h-4 w-4 mr-1 animate-spin" /> : <Download className="h-4 w-4 mr-1" />}
          Export CSV
        </Button>
      </div>

      {loading ? (
        <div className="text-center py-8 text-slate-500">Loading...</div>
      ) : leads.length === 0 ? (
        <Card className="border-dashed"><CardContent className="text-center py-8">
          <Users2 className="h-8 w-8 mx-auto text-slate-400 mb-2" />
          <p className="text-slate-500 text-sm">No leads yet. Leads appear when clients complete a flow.</p>
        </CardContent></Card>
      ) : (
        <div className="space-y-2">
          {leads.map(lead => (
            <Card key={lead.id} className="shadow-sm">
              <CardContent className="py-3">
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="font-medium text-sm">{lead.clientPhone}</span>
                      {lead.clientName && <span className="text-sm text-slate-600">({lead.clientName})</span>}
                      <span className={`text-xs px-2 py-0.5 rounded-full ${statusColors[lead.status] || 'bg-slate-100'}`}>
                        {lead.status}
                      </span>
                    </div>
                    <div className="flex gap-3 text-xs text-slate-500 mt-1">
                      {lead.flowName && <span>Flow: {lead.flowName}</span>}
                      <span>{new Date(lead.createdAt).toLocaleDateString()}</span>
                    </div>
                  </div>
                  <div className="flex gap-1 items-center">
                    <Button variant="ghost" size="sm" className="h-7 w-7 p-0"
                      onClick={() => setExpandedLead(expandedLead === lead.id ? null : lead.id)}>
                      <Eye className="h-3.5 w-3.5" />
                    </Button>
                    <Select value={lead.status} onValueChange={(v) => handleStatusChange(lead.id, v)}>
                      <SelectTrigger className="h-7 w-28 text-xs"><SelectValue /></SelectTrigger>
                      <SelectContent>
                        <SelectItem value="new">New</SelectItem>
                        <SelectItem value="contacted">Contacted</SelectItem>
                        <SelectItem value="qualified">Qualified</SelectItem>
                        <SelectItem value="unqualified">Unqualified</SelectItem>
                      </SelectContent>
                    </Select>
                    <Button variant="ghost" size="sm" className="h-7 w-7 p-0 text-red-600" onClick={() => handleDelete(lead.id)}>
                      <Trash2 className="h-3.5 w-3.5" />
                    </Button>
                  </div>
                </div>

                {expandedLead === lead.id && lead.answers?.length > 0 && (
                  <div className="mt-3 pt-3 border-t space-y-2">
                    {lead.answers.map((a, i) => (
                      <div key={i} className="text-sm">
                        <p className="text-slate-500 text-xs">{a.questionText}</p>
                        <p className="font-medium">{a.answer}</p>
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {totalPages > 1 && (
        <div className="flex justify-center gap-2">
          <Button variant="outline" size="sm" disabled={page <= 1} onClick={() => setPage(p => p - 1)}>Previous</Button>
          <span className="text-sm text-slate-500 py-1.5">Page {page} of {totalPages}</span>
          <Button variant="outline" size="sm" disabled={page >= totalPages} onClick={() => setPage(p => p + 1)}>Next</Button>
        </div>
      )}
    </div>
  );
};

// ===== MAIN PAGE =====
const ChatbotPage = ({ user, onLogout }) => {
  const [stats, setStats] = useState(null);

  useEffect(() => {
    api.get('/chatbot/stats').then(res => setStats(res.data)).catch(() => {});
  }, []);

  return (
    <Layout user={user} onLogout={onLogout}>
      <div className="space-y-6" data-testid="chatbot-page">
        <div>
          <h1 className="text-2xl sm:text-3xl font-bold text-slate-900">Lead Chatbot</h1>
          <p className="text-slate-600 mt-1 text-sm">Create trigger-based flows to collect leads via WhatsApp</p>
        </div>

        {stats && (
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <Card className="shadow-sm border bg-gradient-to-br from-blue-50 to-blue-100/50">
              <CardContent className="py-3 text-center">
                <p className="text-2xl font-bold text-blue-900">{stats.totalFlows}</p>
                <p className="text-xs text-blue-700">Total Flows</p>
              </CardContent>
            </Card>
            <Card className="shadow-sm border bg-gradient-to-br from-indigo-50 to-indigo-100/50">
              <CardContent className="py-3 text-center">
                <p className="text-2xl font-bold text-indigo-900">{stats.activeFlows}</p>
                <p className="text-xs text-indigo-700">Active Flows</p>
              </CardContent>
            </Card>
            <Card className="shadow-sm border bg-gradient-to-br from-green-50 to-green-100/50">
              <CardContent className="py-3 text-center">
                <p className="text-2xl font-bold text-green-900">{stats.totalLeads}</p>
                <p className="text-xs text-green-700">Total Leads</p>
              </CardContent>
            </Card>
            <Card className="shadow-sm border bg-gradient-to-br from-amber-50 to-amber-100/50">
              <CardContent className="py-3 text-center">
                <p className="text-2xl font-bold text-amber-900">{stats.activeConversations}</p>
                <p className="text-xs text-amber-700">Active Chats</p>
              </CardContent>
            </Card>
          </div>
        )}

        <Tabs defaultValue="flows">
          <TabsList className="grid w-full grid-cols-3 h-10">
            <TabsTrigger value="flows" className="text-xs sm:text-sm" data-testid="tab-flows">
              <Zap className="h-4 w-4 mr-1 hidden sm:block" /> Flows
            </TabsTrigger>
            <TabsTrigger value="leads" className="text-xs sm:text-sm" data-testid="tab-leads">
              <Users2 className="h-4 w-4 mr-1 hidden sm:block" /> Leads
            </TabsTrigger>
            <TabsTrigger value="settings" className="text-xs sm:text-sm" data-testid="tab-settings">
              <Settings className="h-4 w-4 mr-1 hidden sm:block" /> Settings
            </TabsTrigger>
          </TabsList>

          <div className="mt-4">
            <TabsContent value="flows"><FlowsTab /></TabsContent>
            <TabsContent value="leads"><LeadsTab /></TabsContent>
            <TabsContent value="settings"><SettingsTab /></TabsContent>
          </div>
        </Tabs>
      </div>
    </Layout>
  );
};

export default ChatbotPage;
