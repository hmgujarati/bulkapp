import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { 
  Bell, Plus, Phone, Clock, Settings, Trash2, Edit2, 
  Calendar, Filter, ChevronDown, Search, AlertCircle,
  CheckCircle, XCircle, Loader2, MessageSquare, FileText,
  Copy, ExternalLink, BookOpen, RefreshCw, RotateCcw
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
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
  DialogFooter,
} from "@/components/ui/dialog";
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Checkbox } from '@/components/ui/checkbox';
import { toast } from 'sonner';
import api from '../utils/api';
import Layout from '../components/Layout';

const WEEKDAYS = [
  { value: 0, label: 'Mon' },
  { value: 1, label: 'Tue' },
  { value: 2, label: 'Wed' },
  { value: 3, label: 'Thu' },
  { value: 4, label: 'Fri' },
  { value: 5, label: 'Sat' },
  { value: 6, label: 'Sun' }
];

const Reminders = ({ user, onLogout }) => {
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState('reminders');
  const [reminders, setReminders] = useState([]);
  const [numbers, setNumbers] = useState([]);
  const [timezones, setTimezones] = useState([]);
  const [settings, setSettings] = useState({ hasApiKey: false });
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState('all');
  
  // Dialog states
  const [showAddNumber, setShowAddNumber] = useState(false);
  const [showAddReminder, setShowAddReminder] = useState(false);
  const [showSettings, setShowSettings] = useState(false);
  
  // Form states
  const [numberForm, setNumberForm] = useState({ phone: '', name: '', timezone: 'Asia/Kolkata', isDefault: false });
  const [reminderForm, setReminderForm] = useState({ 
    numberId: '', 
    naturalLanguageInput: '',
    recurrenceType: 'none',
    recurrenceInterval: 1,
    recurrenceWeekdays: []
  });
  const [settingsForm, setSettingsForm] = useState({ openaiApiKey: '', defaultTemplateId: '' });
  const [formLoading, setFormLoading] = useState(false);

  useEffect(() => {
    loadData();
  }, [filter]);

  const loadData = async () => {
    try {
      setLoading(true);
      const [numbersRes, remindersRes, settingsRes, timezonesRes] = await Promise.all([
        api.get('/reminder-numbers'),
        api.get(`/reminders?filter=${filter}`),
        api.get('/reminders/settings'),
        api.get('/reminder-numbers/timezones')
      ]);
      
      setNumbers(numbersRes.data.numbers || []);
      setReminders(remindersRes.data.reminders || []);
      setSettings(settingsRes.data);
      setTimezones(timezonesRes.data.timezones || []);
    } catch (error) {
      toast.error('Failed to load data');
    } finally {
      setLoading(false);
    }
  };

  const handleAddNumber = async (e) => {
    e.preventDefault();
    setFormLoading(true);
    try {
      await api.post('/reminder-numbers', numberForm);
      toast.success('Phone number added successfully');
      setShowAddNumber(false);
      setNumberForm({ phone: '', name: '', timezone: 'Asia/Kolkata', isDefault: false });
      loadData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to add number');
    } finally {
      setFormLoading(false);
    }
  };

  const handleDeleteNumber = async (numberId) => {
    if (!confirm('Are you sure you want to delete this number?')) return;
    try {
      await api.delete(`/reminder-numbers/${numberId}`);
      toast.success('Number deleted successfully');
      loadData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to delete number');
    }
  };

  const handleCreateReminder = async (e) => {
    e.preventDefault();
    if (!settings.hasApiKey) {
      toast.error('Please configure your OpenAI API key in settings first');
      setShowSettings(true);
      return;
    }
    setFormLoading(true);
    try {
      const payload = {
        numberId: reminderForm.numberId,
        naturalLanguageInput: reminderForm.naturalLanguageInput,
        recurrenceType: reminderForm.recurrenceType !== 'none' ? reminderForm.recurrenceType : null,
        recurrenceInterval: reminderForm.recurrenceInterval,
        recurrenceWeekdays: reminderForm.recurrenceWeekdays.length > 0 ? reminderForm.recurrenceWeekdays : null
      };
      const response = await api.post('/reminders', payload);
      const recurrenceMsg = reminderForm.recurrenceType !== 'none' ? ` (${reminderForm.recurrenceType})` : '';
      toast.success(`Reminder created: ${response.data.reminder.title}${recurrenceMsg}`);
      setShowAddReminder(false);
      setReminderForm({ 
        numberId: '', 
        naturalLanguageInput: '',
        recurrenceType: 'none',
        recurrenceInterval: 1,
        recurrenceWeekdays: []
      });
      loadData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to create reminder');
    } finally {
      setFormLoading(false);
    }
  };

  const handleDeleteReminder = async (reminderId) => {
    if (!confirm('Are you sure you want to delete this reminder?')) return;
    try {
      await api.delete(`/reminders/${reminderId}`);
      toast.success('Reminder deleted successfully');
      loadData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to delete reminder');
    }
  };

  const handleSaveSettings = async (e) => {
    e.preventDefault();
    setFormLoading(true);
    try {
      const updateData = {};
      if (settingsForm.openaiApiKey) updateData.openaiApiKey = settingsForm.openaiApiKey;
      if (settingsForm.defaultTemplateId) updateData.defaultTemplateId = settingsForm.defaultTemplateId;
      
      await api.put('/reminders/settings', updateData);
      toast.success('Settings saved successfully');
      setShowSettings(false);
      setSettingsForm({ openaiApiKey: '', defaultTemplateId: '' });
      loadData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to save settings');
    } finally {
      setFormLoading(false);
    }
  };

  const getStatusBadge = (status) => {
    switch (status) {
      case 'pending':
        return <Badge variant="outline" className="bg-yellow-50 text-yellow-700 border-yellow-200"><Clock className="w-3 h-3 mr-1" /> Pending</Badge>;
      case 'sent':
        return <Badge variant="outline" className="bg-green-50 text-green-700 border-green-200"><CheckCircle className="w-3 h-3 mr-1" /> Sent</Badge>;
      case 'failed':
        return <Badge variant="outline" className="bg-red-50 text-red-700 border-red-200"><XCircle className="w-3 h-3 mr-1" /> Failed</Badge>;
      default:
        return <Badge variant="outline">{status}</Badge>;
    }
  };

  const getRecurrenceBadge = (recurrence) => {
    if (!recurrence || recurrence.type === 'none') return null;
    
    let label = '';
    switch (recurrence.type) {
      case 'daily':
        label = recurrence.interval > 1 ? `Every ${recurrence.interval} days` : 'Daily';
        break;
      case 'weekly':
        if (recurrence.weekdays && recurrence.weekdays.length > 0) {
          const days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
          label = recurrence.weekdays.map(d => days[d]).join(', ');
        } else {
          label = recurrence.interval > 1 ? `Every ${recurrence.interval} weeks` : 'Weekly';
        }
        break;
      case 'monthly':
        label = recurrence.interval > 1 ? `Every ${recurrence.interval} months` : 'Monthly';
        break;
      case 'custom':
        label = `Every ${recurrence.interval} days`;
        break;
      default:
        return null;
    }
    
    return (
      <Badge variant="outline" className="bg-purple-50 text-purple-700 border-purple-200">
        <RefreshCw className="w-3 h-3 mr-1" /> {label}
      </Badge>
    );
  };

  const formatDateTime = (dateStr) => {
    const date = new Date(dateStr);
    return date.toLocaleString('en-IN', {
      day: 'numeric',
      month: 'short',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  return (
    <Layout user={user} onLogout={onLogout}>
      <div data-testid="reminders-page">
        {/* Page Title */}
        <div className="mb-8">
          <h2 className="text-3xl font-bold text-slate-900 flex items-center">
            <Bell className="w-8 h-8 mr-3 text-blue-600" />
            Reminder Bot
          </h2>
          <p className="text-slate-600 mt-1">Set reminders using natural language and send them via WhatsApp</p>
        </div>

        {/* API Key Warning */}
        {!settings.hasApiKey && (
          <Card className="mb-6 border-yellow-200 bg-yellow-50">
            <CardContent className="flex items-center p-4">
              <AlertCircle className="w-5 h-5 text-yellow-600 mr-3" />
              <div className="flex-1">
                <p className="text-yellow-800 font-medium">OpenAI API Key Required</p>
                <p className="text-yellow-700 text-sm">Configure your OpenAI API key to use natural language reminders.</p>
              </div>
              <Button onClick={() => setShowSettings(true)} variant="outline" className="border-yellow-300">
                Configure Now
              </Button>
            </CardContent>
          </Card>
        )}

        {/* Tabs */}
        <div className="flex space-x-4 mb-6">
          <Button
            variant={activeTab === 'reminders' ? 'default' : 'outline'}
            onClick={() => setActiveTab('reminders')}
            data-testid="tab-reminders"
          >
            <Bell className="w-4 h-4 mr-2" /> Reminders
          </Button>
          <Button
            variant={activeTab === 'numbers' ? 'default' : 'outline'}
            onClick={() => setActiveTab('numbers')}
            data-testid="tab-numbers"
          >
            <Phone className="w-4 h-4 mr-2" /> Phone Numbers
          </Button>
          <Button
            variant={activeTab === 'templates' ? 'default' : 'outline'}
            onClick={() => setActiveTab('templates')}
            data-testid="tab-templates"
          >
            <FileText className="w-4 h-4 mr-2" /> Template Guide
          </Button>
        </div>

        {/* Reminders Tab */}
        {activeTab === 'reminders' && (
          <div>
            {/* Actions Bar */}
            <div className="flex justify-between items-center mb-6">
              <div className="flex items-center space-x-4">
                <Select value={filter} onValueChange={setFilter}>
                  <SelectTrigger className="w-40" data-testid="filter-select">
                    <Filter className="w-4 h-4 mr-2" />
                    <SelectValue placeholder="Filter" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All</SelectItem>
                    <SelectItem value="today">Today</SelectItem>
                    <SelectItem value="week">This Week</SelectItem>
                    <SelectItem value="pending">Pending</SelectItem>
                    <SelectItem value="sent">Sent</SelectItem>
                    <SelectItem value="failed">Failed</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="flex items-center space-x-2">
                <Button variant="outline" onClick={() => setShowSettings(true)} data-testid="reminder-settings-btn">
                  <Settings className="w-4 h-4 mr-2" /> API Settings
                </Button>
                <Button onClick={() => setShowAddReminder(true)} data-testid="add-reminder-btn">
                  <Plus className="w-4 h-4 mr-2" /> New Reminder
                </Button>
              </div>
            </div>

            {/* Reminders List */}
            {loading ? (
              <div className="flex justify-center py-12">
                <Loader2 className="w-8 h-8 animate-spin text-blue-600" />
              </div>
            ) : reminders.length === 0 ? (
              <Card>
                <CardContent className="flex flex-col items-center justify-center py-12">
                  <Bell className="w-12 h-12 text-slate-300 mb-4" />
                  <p className="text-slate-500 text-lg">No reminders yet</p>
                  <p className="text-slate-400 text-sm mb-4">Create your first reminder to get started</p>
                  <Button onClick={() => setShowAddReminder(true)}>
                    <Plus className="w-4 h-4 mr-2" /> Create Reminder
                  </Button>
                </CardContent>
              </Card>
            ) : (
              <div className="space-y-4">
                {reminders.map((reminder) => (
                  <Card key={reminder.id} className="hover:shadow-md transition-shadow" data-testid={`reminder-${reminder.id}`}>
                    <CardContent className="p-4">
                      <div className="flex items-start justify-between">
                        <div className="flex-1">
                          <div className="flex items-center flex-wrap gap-2 mb-2">
                            <h3 className="font-semibold text-slate-900">{reminder.title}</h3>
                            {getStatusBadge(reminder.status)}
                            {getRecurrenceBadge(reminder.recurrence)}
                          </div>
                          <p className="text-slate-600 text-sm mb-2">{reminder.message}</p>
                          <div className="flex items-center space-x-4 text-xs text-slate-500">
                            <span className="flex items-center">
                              <Phone className="w-3 h-3 mr-1" />
                              {reminder.contactName} ({reminder.phone})
                            </span>
                            <span className="flex items-center">
                              <Clock className="w-3 h-3 mr-1" />
                              {formatDateTime(reminder.scheduledAt)}
                            </span>
                          </div>
                          {reminder.error && (
                            <p className="text-red-500 text-xs mt-2">Error: {reminder.error}</p>
                          )}
                        </div>
                        <div className="flex space-x-2">
                          <Button
                            variant="ghost"
                            size="sm"
                            className="text-red-500 hover:text-red-700"
                            onClick={() => handleDeleteReminder(reminder.id)}
                            data-testid={`delete-reminder-${reminder.id}`}
                          >
                            <Trash2 className="w-4 h-4" />
                          </Button>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Phone Numbers Tab */}
        {activeTab === 'numbers' && (
          <div>
            <div className="flex justify-between items-center mb-6">
              <p className="text-slate-600">Manage phone numbers that can receive reminders</p>
              <Button onClick={() => setShowAddNumber(true)} data-testid="add-number-btn">
                <Plus className="w-4 h-4 mr-2" /> Add Number
              </Button>
            </div>

            {loading ? (
              <div className="flex justify-center py-12">
                <Loader2 className="w-8 h-8 animate-spin text-blue-600" />
              </div>
            ) : numbers.length === 0 ? (
              <Card>
                <CardContent className="flex flex-col items-center justify-center py-12">
                  <Phone className="w-12 h-12 text-slate-300 mb-4" />
                  <p className="text-slate-500 text-lg">No phone numbers added</p>
                  <p className="text-slate-400 text-sm mb-4">Add a phone number to start sending reminders</p>
                  <Button onClick={() => setShowAddNumber(true)}>
                    <Plus className="w-4 h-4 mr-2" /> Add Number
                  </Button>
                </CardContent>
              </Card>
            ) : (
              <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                {numbers.map((number) => (
                  <Card key={number.id} className="hover:shadow-md transition-shadow" data-testid={`number-${number.id}`}>
                    <CardContent className="p-4">
                      <div className="flex items-start justify-between">
                        <div>
                          <div className="flex items-center space-x-2 mb-1">
                            <h3 className="font-semibold text-slate-900">{number.name}</h3>
                            {number.isDefault && (
                              <Badge variant="secondary" className="text-xs">Default</Badge>
                            )}
                          </div>
                          <p className="text-slate-600">{number.phone}</p>
                          <p className="text-xs text-slate-400 mt-1">
                            <Clock className="w-3 h-3 inline mr-1" />
                            {number.timezone}
                          </p>
                        </div>
                        <Button
                          variant="ghost"
                          size="sm"
                          className="text-red-500 hover:text-red-700"
                          onClick={() => handleDeleteNumber(number.id)}
                          data-testid={`delete-number-${number.id}`}
                        >
                          <Trash2 className="w-4 h-4" />
                        </Button>
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Template Guide Tab */}
        {activeTab === 'templates' && (
          <div data-testid="template-guide-section">
            {/* Approved Template Card */}
            <Card className="mb-6 border-green-200 bg-green-50">
              <CardContent className="flex items-center p-4">
                <CheckCircle className="w-5 h-5 text-green-600 mr-3" />
                <div className="flex-1">
                  <p className="text-green-800 font-medium">Your Template is Approved!</p>
                  <p className="text-green-700 text-sm">The template below has been approved by Meta and is ready to use.</p>
                </div>
              </CardContent>
            </Card>

            {/* The Approved Template */}
            <Card className="mb-6">
              <CardHeader>
                <CardTitle className="flex items-center text-lg">
                  <FileText className="w-5 h-5 mr-2 text-green-600" />
                  Your Approved Template
                </CardTitle>
                <CardDescription>This template is approved and configured for your reminders</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="border rounded-lg p-4 bg-slate-50">
                  <div className="flex justify-between items-start mb-3">
                    <div>
                      <Badge className="bg-green-100 text-green-800 border-green-200 mb-2">APPROVED</Badge>
                      <h4 className="font-semibold text-slate-900">Reminder Alert</h4>
                      <p className="text-xs text-slate-500">Template Name: <code className="bg-slate-200 px-1 rounded">reminder_alert</code></p>
                      <p className="text-xs text-slate-500">Language: <code className="bg-slate-200 px-1 rounded">en_US</code> | Category: <code className="bg-slate-200 px-1 rounded">UTILITY</code></p>
                    </div>
                    <Button 
                      variant="outline" 
                      size="sm"
                      onClick={() => {
                        navigator.clipboard.writeText('Hi There!\n\nReminder: {{1}}\nTime: {{2}}\nDate: {{3}}\n\n- Your WhatsApp Assistant');
                        toast.success('Template copied!');
                      }}
                    >
                      <Copy className="w-3 h-3 mr-1" /> Copy
                    </Button>
                  </div>
                  <div className="bg-white border rounded p-4 font-mono text-sm">
                    <p className="text-slate-600 mb-2">Header: <span className="text-slate-900 font-semibold">Reminder Alert</span></p>
                    <div className="text-slate-900 whitespace-pre-line border-t pt-2">Hi There!

Reminder: {'{{1}}'}
Time: {'{{2}}'}
Date: {'{{3}}'}

- Your WhatsApp Assistant</div>
                  </div>
                  <div className="mt-3 space-y-1">
                    <p className="text-xs text-slate-600"><span className="font-medium">{'{{1}}'}</span> = Reminder message (e.g., "Call John")</p>
                    <p className="text-xs text-slate-600"><span className="font-medium">{'{{2}}'}</span> = Time (e.g., "3:00 PM")</p>
                    <p className="text-xs text-slate-600"><span className="font-medium">{'{{3}}'}</span> = Date (e.g., "25 Feb 2025")</p>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Configuration Steps */}
            <Card className="mb-6">
              <CardHeader>
                <CardTitle className="flex items-center text-lg">
                  <Settings className="w-5 h-5 mr-2 text-blue-600" />
                  Configure Your Template
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  <div className="flex items-start space-x-3">
                    <div className="flex-shrink-0 w-6 h-6 bg-blue-600 text-white rounded-full flex items-center justify-center text-sm font-medium">1</div>
                    <div>
                      <p className="font-medium text-slate-900">Open API Settings</p>
                      <p className="text-sm text-slate-600">Click the button below to open settings</p>
                      <Button variant="outline" size="sm" className="mt-2" onClick={() => setShowSettings(true)}>
                        <Settings className="w-3 h-3 mr-1" /> Open API Settings
                      </Button>
                    </div>
                  </div>
                  <div className="flex items-start space-x-3">
                    <div className="flex-shrink-0 w-6 h-6 bg-blue-600 text-white rounded-full flex items-center justify-center text-sm font-medium">2</div>
                    <div>
                      <p className="font-medium text-slate-900">Enter Template Name</p>
                      <p className="text-sm text-slate-600">In the "Default Meta Template ID" field, enter: <code className="bg-slate-100 px-2 py-0.5 rounded">reminder_alert</code></p>
                    </div>
                  </div>
                  <div className="flex items-start space-x-3">
                    <div className="flex-shrink-0 w-6 h-6 bg-blue-600 text-white rounded-full flex items-center justify-center text-sm font-medium">3</div>
                    <div>
                      <p className="font-medium text-slate-900">Save Settings</p>
                      <p className="text-sm text-slate-600">Click Save and you're all set!</p>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* How It Works */}
            <Card>
              <CardHeader>
                <CardTitle className="text-base">How Templates Work</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-3 text-sm text-slate-600">
                  <div className="flex items-start space-x-2">
                    <Clock className="w-4 h-4 text-blue-500 mt-0.5" />
                    <p><strong>Within 24-hour window:</strong> Messages are sent as free-form session messages</p>
                  </div>
                  <div className="flex items-start space-x-2">
                    <Bell className="w-4 h-4 text-purple-500 mt-0.5" />
                    <p><strong>Outside 24-hour window:</strong> Messages use your approved template automatically</p>
                  </div>
                  <div className="flex items-start space-x-2">
                    <CheckCircle className="w-4 h-4 text-green-500 mt-0.5" />
                    <p><strong>Variables filled automatically:</strong> The bot fills in reminder, time, and date for you</p>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        )}
                    <li className="flex items-start"><XCircle className="w-4 h-4 mr-2 text-red-500 flex-shrink-0 mt-0.5" /> Include URLs in utility templates</li>
                    <li className="flex items-start"><XCircle className="w-4 h-4 mr-2 text-red-500 flex-shrink-0 mt-0.5" /> Use ALL CAPS or excessive punctuation</li>
                    <li className="flex items-start"><XCircle className="w-4 h-4 mr-2 text-red-500 flex-shrink-0 mt-0.5" /> Make templates too long</li>
                    <li className="flex items-start"><XCircle className="w-4 h-4 mr-2 text-red-500 flex-shrink-0 mt-0.5" /> Use wrong variable format like {'{1}'} or {'[1]'}</li>
                  </ul>
                </CardContent>
              </Card>
            </div>

            {/* Status Reference */}
            <Card className="mt-6">
              <CardHeader>
                <CardTitle className="text-base">Template Status Reference</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="grid gap-3 md:grid-cols-4">
                  <div className="flex items-center space-x-2">
                    <Badge className="bg-green-100 text-green-800">Approved</Badge>
                    <span className="text-sm text-slate-600">Ready to use</span>
                  </div>
                  <div className="flex items-center space-x-2">
                    <Badge className="bg-yellow-100 text-yellow-800">Pending</Badge>
                    <span className="text-sm text-slate-600">Under review (24-48h)</span>
                  </div>
                  <div className="flex items-center space-x-2">
                    <Badge className="bg-red-100 text-red-800">Rejected</Badge>
                    <span className="text-sm text-slate-600">Modify and resubmit</span>
                  </div>
                  <div className="flex items-center space-x-2">
                    <Badge className="bg-gray-100 text-gray-800">Paused</Badge>
                    <span className="text-sm text-slate-600">Check quality rating</span>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        )}

      {/* Add Number Dialog */}
      <Dialog open={showAddNumber} onOpenChange={setShowAddNumber}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Add Phone Number</DialogTitle>
            <DialogDescription>
              Add a phone number that can receive reminders
            </DialogDescription>
          </DialogHeader>
          <form onSubmit={handleAddNumber}>
            <div className="space-y-4 py-4">
              <div>
                <Label htmlFor="phone">Phone Number</Label>
                <Input
                  id="phone"
                  placeholder="+91 98765 43210"
                  value={numberForm.phone}
                  onChange={(e) => setNumberForm({ ...numberForm, phone: e.target.value })}
                  required
                  data-testid="number-phone-input"
                />
              </div>
              <div>
                <Label htmlFor="name">Contact Name</Label>
                <Input
                  id="name"
                  placeholder="John Doe"
                  value={numberForm.name}
                  onChange={(e) => setNumberForm({ ...numberForm, name: e.target.value })}
                  required
                  data-testid="number-name-input"
                />
              </div>
              <div>
                <Label htmlFor="timezone">Timezone</Label>
                <Select
                  value={numberForm.timezone}
                  onValueChange={(v) => setNumberForm({ ...numberForm, timezone: v })}
                >
                  <SelectTrigger data-testid="number-timezone-select">
                    <SelectValue placeholder="Select timezone" />
                  </SelectTrigger>
                  <SelectContent>
                    {timezones.map((tz) => (
                      <SelectItem key={tz} value={tz}>{tz}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setShowAddNumber(false)}>
                Cancel
              </Button>
              <Button type="submit" disabled={formLoading} data-testid="save-number-btn">
                {formLoading ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : null}
                Add Number
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* Add Reminder Dialog */}
      <Dialog open={showAddReminder} onOpenChange={setShowAddReminder}>
        <DialogContent className="sm:max-w-lg max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Create Reminder</DialogTitle>
            <DialogDescription>
              Use natural language to set a reminder. Example: &quot;remind me to call John at 10am tomorrow&quot;
            </DialogDescription>
          </DialogHeader>
          <form onSubmit={handleCreateReminder}>
            <div className="space-y-4 py-4">
              <div>
                <Label htmlFor="numberId">Send To</Label>
                <Select
                  value={reminderForm.numberId}
                  onValueChange={(v) => setReminderForm({ ...reminderForm, numberId: v })}
                >
                  <SelectTrigger data-testid="reminder-number-select">
                    <SelectValue placeholder="Select phone number" />
                  </SelectTrigger>
                  <SelectContent>
                    {numbers.map((num) => (
                      <SelectItem key={num.id} value={num.id}>
                        {num.name} ({num.phone})
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div>
                <Label htmlFor="naturalLanguageInput">What would you like to be reminded about?</Label>
                <Textarea
                  id="naturalLanguageInput"
                  placeholder="e.g., remind me to call Harsh at 10am tomorrow"
                  value={reminderForm.naturalLanguageInput}
                  onChange={(e) => setReminderForm({ ...reminderForm, naturalLanguageInput: e.target.value })}
                  required
                  rows={3}
                  data-testid="reminder-input"
                />
                <p className="text-xs text-slate-500 mt-1">
                  AI will parse your input. You can also say &quot;daily&quot; or &quot;every Monday&quot; for recurring reminders.
                </p>
              </div>

              {/* Recurrence Options */}
              <div className="border rounded-lg p-4 bg-slate-50">
                <Label className="flex items-center mb-3">
                  <RefreshCw className="w-4 h-4 mr-2 text-purple-600" />
                  Repeat (Optional)
                </Label>
                <div className="space-y-3">
                  <Select
                    value={reminderForm.recurrenceType}
                    onValueChange={(v) => setReminderForm({ 
                      ...reminderForm, 
                      recurrenceType: v,
                      recurrenceWeekdays: v === 'weekly' ? reminderForm.recurrenceWeekdays : []
                    })}
                  >
                    <SelectTrigger data-testid="recurrence-type-select">
                      <SelectValue placeholder="No repeat" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="none">No repeat</SelectItem>
                      <SelectItem value="daily">Daily</SelectItem>
                      <SelectItem value="weekly">Weekly</SelectItem>
                      <SelectItem value="monthly">Monthly</SelectItem>
                      <SelectItem value="custom">Custom (every X days)</SelectItem>
                    </SelectContent>
                  </Select>

                  {/* Custom interval */}
                  {(reminderForm.recurrenceType === 'custom' || reminderForm.recurrenceType === 'daily') && (
                    <div className="flex items-center space-x-2">
                      <span className="text-sm text-slate-600">Every</span>
                      <Input
                        type="number"
                        min="1"
                        max="365"
                        value={reminderForm.recurrenceInterval}
                        onChange={(e) => setReminderForm({ ...reminderForm, recurrenceInterval: parseInt(e.target.value) || 1 })}
                        className="w-20"
                        data-testid="recurrence-interval-input"
                      />
                      <span className="text-sm text-slate-600">
                        {reminderForm.recurrenceType === 'daily' ? 'day(s)' : 'days'}
                      </span>
                    </div>
                  )}

                  {/* Weekly interval */}
                  {reminderForm.recurrenceType === 'weekly' && (
                    <div className="space-y-2">
                      <div className="flex items-center space-x-2">
                        <span className="text-sm text-slate-600">Every</span>
                        <Input
                          type="number"
                          min="1"
                          max="52"
                          value={reminderForm.recurrenceInterval}
                          onChange={(e) => setReminderForm({ ...reminderForm, recurrenceInterval: parseInt(e.target.value) || 1 })}
                          className="w-20"
                          data-testid="recurrence-weeks-input"
                        />
                        <span className="text-sm text-slate-600">week(s)</span>
                      </div>
                      <div>
                        <span className="text-sm text-slate-600 block mb-2">On these days:</span>
                        <div className="flex flex-wrap gap-2">
                          {WEEKDAYS.map((day) => (
                            <label 
                              key={day.value} 
                              className={`flex items-center justify-center w-10 h-10 rounded-full cursor-pointer transition-colors ${
                                reminderForm.recurrenceWeekdays.includes(day.value)
                                  ? 'bg-blue-600 text-white'
                                  : 'bg-slate-200 text-slate-700 hover:bg-slate-300'
                              }`}
                            >
                              <input
                                type="checkbox"
                                className="sr-only"
                                checked={reminderForm.recurrenceWeekdays.includes(day.value)}
                                onChange={(e) => {
                                  if (e.target.checked) {
                                    setReminderForm({
                                      ...reminderForm,
                                      recurrenceWeekdays: [...reminderForm.recurrenceWeekdays, day.value].sort()
                                    });
                                  } else {
                                    setReminderForm({
                                      ...reminderForm,
                                      recurrenceWeekdays: reminderForm.recurrenceWeekdays.filter(d => d !== day.value)
                                    });
                                  }
                                }}
                              />
                              <span className="text-xs font-medium">{day.label}</span>
                            </label>
                          ))}
                        </div>
                      </div>
                    </div>
                  )}

                  {/* Monthly interval */}
                  {reminderForm.recurrenceType === 'monthly' && (
                    <div className="flex items-center space-x-2">
                      <span className="text-sm text-slate-600">Every</span>
                      <Input
                        type="number"
                        min="1"
                        max="12"
                        value={reminderForm.recurrenceInterval}
                        onChange={(e) => setReminderForm({ ...reminderForm, recurrenceInterval: parseInt(e.target.value) || 1 })}
                        className="w-20"
                        data-testid="recurrence-months-input"
                      />
                      <span className="text-sm text-slate-600">month(s)</span>
                    </div>
                  )}

                  {reminderForm.recurrenceType !== 'none' && (
                    <p className="text-xs text-purple-600 mt-2">
                      This reminder will repeat until you manually delete it.
                    </p>
                  )}
                </div>
              </div>
            </div>
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setShowAddReminder(false)}>
                Cancel
              </Button>
              <Button type="submit" disabled={formLoading || !reminderForm.numberId} data-testid="create-reminder-btn">
                {formLoading ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : null}
                Create Reminder
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* Settings Dialog */}
      <Dialog open={showSettings} onOpenChange={setShowSettings}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Reminder Settings</DialogTitle>
            <DialogDescription>
              Configure your OpenAI API key and default template
            </DialogDescription>
          </DialogHeader>
          <form onSubmit={handleSaveSettings}>
            <div className="space-y-4 py-4">
              <div>
                <div className="flex items-center justify-between mb-2">
                  <Label htmlFor="openaiApiKey">OpenAI API Key</Label>
                  {settings.hasApiKey && (
                    <Badge variant="outline" className="bg-green-50 text-green-700 border-green-200">
                      <CheckCircle className="w-3 h-3 mr-1" /> Configured
                    </Badge>
                  )}
                </div>
                <Input
                  id="openaiApiKey"
                  type="password"
                  placeholder={settings.hasApiKey ? "Enter new key to update..." : "sk-..."}
                  value={settingsForm.openaiApiKey}
                  onChange={(e) => setSettingsForm({ ...settingsForm, openaiApiKey: e.target.value })}
                  data-testid="openai-key-input"
                />
                <p className="text-xs text-slate-500 mt-1">
                  {settings.hasApiKey 
                    ? "Leave empty to keep current key, or enter a new key to update"
                    : "Required for natural language parsing"
                  }
                  {' '}<a href="https://platform.openai.com/api-keys" target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline">
                    Get key from OpenAI
                  </a>
                </p>
              </div>
              <div>
                <Label htmlFor="defaultTemplateId">Default Meta Template ID</Label>
                <Input
                  id="defaultTemplateId"
                  placeholder={settings.defaultTemplateId || "reminder_template"}
                  value={settingsForm.defaultTemplateId}
                  onChange={(e) => setSettingsForm({ ...settingsForm, defaultTemplateId: e.target.value })}
                  data-testid="template-id-input"
                />
                <p className="text-xs text-slate-500 mt-1">
                  Pre-approved WhatsApp template name for sending reminders
                  {settings.defaultTemplateId && (
                    <span className="block mt-1 text-green-600">Current: {settings.defaultTemplateId}</span>
                  )}
                </p>
              </div>
            </div>
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setShowSettings(false)}>
                Cancel
              </Button>
              <Button type="submit" disabled={formLoading} data-testid="save-settings-btn">
                {formLoading ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : null}
                {settings.hasApiKey ? 'Update Settings' : 'Save Settings'}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
      </div>
    </Layout>
  );
};

export default Reminders;
