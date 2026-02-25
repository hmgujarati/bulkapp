import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { 
  Bell, Plus, Phone, Clock, Settings, Trash2, Edit2, 
  Calendar, Filter, ChevronDown, Search, AlertCircle,
  CheckCircle, XCircle, Loader2, MessageSquare, FileText,
  Copy, ExternalLink, BookOpen
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
import { toast } from 'sonner';
import api from '../utils/api';
import Layout from '../components/Layout';

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
  const [reminderForm, setReminderForm] = useState({ numberId: '', naturalLanguageInput: '' });
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
      const response = await api.post('/reminders', reminderForm);
      toast.success(`Reminder created: ${response.data.reminder.title}`);
      setShowAddReminder(false);
      setReminderForm({ numberId: '', naturalLanguageInput: '' });
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
                          <div className="flex items-center space-x-3 mb-2">
                            <h3 className="font-semibold text-slate-900">{reminder.title}</h3>
                            {getStatusBadge(reminder.status)}
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
            <Card className="mb-6 border-blue-200 bg-blue-50">
              <CardContent className="flex items-center p-4">
                <BookOpen className="w-5 h-5 text-blue-600 mr-3" />
                <div className="flex-1">
                  <p className="text-blue-800 font-medium">Why do you need Meta Templates?</p>
                  <p className="text-blue-700 text-sm">WhatsApp requires pre-approved templates for messages sent outside the 24-hour window. Follow this guide to get your templates approved.</p>
                </div>
              </CardContent>
            </Card>

            {/* Quick Start Section */}
            <Card className="mb-6">
              <CardHeader>
                <CardTitle className="flex items-center text-lg">
                  <FileText className="w-5 h-5 mr-2 text-green-600" />
                  Quick Start: Get Your Template Approved
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  <div className="flex items-start space-x-3">
                    <div className="flex-shrink-0 w-6 h-6 bg-blue-600 text-white rounded-full flex items-center justify-center text-sm font-medium">1</div>
                    <div>
                      <p className="font-medium text-slate-900">Go to Meta Business Manager</p>
                      <p className="text-sm text-slate-600">Navigate to WhatsApp Manager → Message Templates</p>
                      <a href="https://business.facebook.com" target="_blank" rel="noopener noreferrer" className="text-sm text-blue-600 hover:underline flex items-center mt-1">
                        Open Meta Business Suite <ExternalLink className="w-3 h-3 ml-1" />
                      </a>
                    </div>
                  </div>
                  <div className="flex items-start space-x-3">
                    <div className="flex-shrink-0 w-6 h-6 bg-blue-600 text-white rounded-full flex items-center justify-center text-sm font-medium">2</div>
                    <div>
                      <p className="font-medium text-slate-900">Create a new template</p>
                      <p className="text-sm text-slate-600">Select <Badge variant="outline">UTILITY</Badge> category and copy one of the templates below</p>
                    </div>
                  </div>
                  <div className="flex items-start space-x-3">
                    <div className="flex-shrink-0 w-6 h-6 bg-blue-600 text-white rounded-full flex items-center justify-center text-sm font-medium">3</div>
                    <div>
                      <p className="font-medium text-slate-900">Submit and wait for approval</p>
                      <p className="text-sm text-slate-600">Approval usually takes 24-48 hours</p>
                    </div>
                  </div>
                  <div className="flex items-start space-x-3">
                    <div className="flex-shrink-0 w-6 h-6 bg-blue-600 text-white rounded-full flex items-center justify-center text-sm font-medium">4</div>
                    <div>
                      <p className="font-medium text-slate-900">Configure in API Settings</p>
                      <p className="text-sm text-slate-600">Enter your template name in the API Settings dialog</p>
                      <Button variant="outline" size="sm" className="mt-2" onClick={() => setShowSettings(true)}>
                        <Settings className="w-3 h-3 mr-1" /> Open API Settings
                      </Button>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Ready-to-Use Templates */}
            <Card className="mb-6">
              <CardHeader>
                <CardTitle className="flex items-center text-lg">
                  <Copy className="w-5 h-5 mr-2 text-purple-600" />
                  Ready-to-Use Templates (Copy & Paste)
                </CardTitle>
                <CardDescription>These templates are designed for high approval rates. Copy and submit to Meta.</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-6">
                  {/* Template 1 */}
                  <div className="border rounded-lg p-4 bg-slate-50">
                    <div className="flex justify-between items-start mb-3">
                      <div>
                        <Badge className="bg-green-100 text-green-800 border-green-200 mb-2">RECOMMENDED</Badge>
                        <h4 className="font-semibold text-slate-900">Simple Reminder</h4>
                        <p className="text-xs text-slate-500">Template Name: <code className="bg-slate-200 px-1 rounded">reminder_alert</code></p>
                      </div>
                      <Button 
                        variant="outline" 
                        size="sm"
                        onClick={() => {
                          navigator.clipboard.writeText('Reminder: {{1}}');
                          toast.success('Template copied!');
                        }}
                      >
                        <Copy className="w-3 h-3 mr-1" /> Copy
                      </Button>
                    </div>
                    <div className="bg-white border rounded p-3 font-mono text-sm">
                      <p className="text-slate-600">Category: <span className="text-slate-900">UTILITY</span></p>
                      <p className="text-slate-600 mt-2">Body:</p>
                      <p className="text-slate-900 mt-1">Reminder: {'{{1}}'}</p>
                    </div>
                    <p className="text-xs text-slate-500 mt-2">{'{{1}}'} = The reminder message (e.g., "Call John at 3pm")</p>
                  </div>

                  {/* Template 2 */}
                  <div className="border rounded-lg p-4 bg-slate-50">
                    <div className="flex justify-between items-start mb-3">
                      <div>
                        <h4 className="font-semibold text-slate-900">Detailed Reminder</h4>
                        <p className="text-xs text-slate-500">Template Name: <code className="bg-slate-200 px-1 rounded">scheduled_reminder</code></p>
                      </div>
                      <Button 
                        variant="outline" 
                        size="sm"
                        onClick={() => {
                          navigator.clipboard.writeText('Hi {{1}},\n\nThis is your scheduled reminder:\n{{2}}\n\nTime: {{3}}');
                          toast.success('Template copied!');
                        }}
                      >
                        <Copy className="w-3 h-3 mr-1" /> Copy
                      </Button>
                    </div>
                    <div className="bg-white border rounded p-3 font-mono text-sm">
                      <p className="text-slate-600">Category: <span className="text-slate-900">UTILITY</span></p>
                      <p className="text-slate-600">Header: <span className="text-slate-900">Reminder</span></p>
                      <p className="text-slate-600 mt-2">Body:</p>
                      <div className="text-slate-900 mt-1 whitespace-pre-line">Hi {'{{1}}'},

This is your scheduled reminder:
{'{{2}}'}

Time: {'{{3}}'}</div>
                    </div>
                    <p className="text-xs text-slate-500 mt-2">{'{{1}}'} = Name, {'{{2}}'} = Message, {'{{3}}'} = Time</p>
                  </div>

                  {/* Template 3 */}
                  <div className="border rounded-lg p-4 bg-slate-50">
                    <div className="flex justify-between items-start mb-3">
                      <div>
                        <h4 className="font-semibold text-slate-900">Professional Reminder</h4>
                        <p className="text-xs text-slate-500">Template Name: <code className="bg-slate-200 px-1 rounded">reminder_notification</code></p>
                      </div>
                      <Button 
                        variant="outline" 
                        size="sm"
                        onClick={() => {
                          navigator.clipboard.writeText('Hello {{1}},\n\nYou have a reminder: {{2}}\n\nScheduled for: {{3}}\n\nReply STOP to unsubscribe.');
                          toast.success('Template copied!');
                        }}
                      >
                        <Copy className="w-3 h-3 mr-1" /> Copy
                      </Button>
                    </div>
                    <div className="bg-white border rounded p-3 font-mono text-sm">
                      <p className="text-slate-600">Category: <span className="text-slate-900">UTILITY</span></p>
                      <p className="text-slate-600 mt-2">Body:</p>
                      <div className="text-slate-900 mt-1 whitespace-pre-line">Hello {'{{1}}'},

You have a reminder: {'{{2}}'}

Scheduled for: {'{{3}}'}

Reply STOP to unsubscribe.</div>
                    </div>
                    <p className="text-xs text-slate-500 mt-2">Including "Reply STOP" increases approval chances</p>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Tips Section */}
            <div className="grid gap-4 md:grid-cols-2">
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center text-base text-green-700">
                    <CheckCircle className="w-4 h-4 mr-2" /> Do's
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <ul className="text-sm space-y-2 text-slate-600">
                    <li className="flex items-start"><CheckCircle className="w-4 h-4 mr-2 text-green-500 flex-shrink-0 mt-0.5" /> Use UTILITY category for reminders</li>
                    <li className="flex items-start"><CheckCircle className="w-4 h-4 mr-2 text-green-500 flex-shrink-0 mt-0.5" /> Keep messages clear and concise</li>
                    <li className="flex items-start"><CheckCircle className="w-4 h-4 mr-2 text-green-500 flex-shrink-0 mt-0.5" /> Use professional, neutral language</li>
                    <li className="flex items-start"><CheckCircle className="w-4 h-4 mr-2 text-green-500 flex-shrink-0 mt-0.5" /> Provide accurate sample content</li>
                    <li className="flex items-start"><CheckCircle className="w-4 h-4 mr-2 text-green-500 flex-shrink-0 mt-0.5" /> Use {'{{1}}'} format for variables</li>
                  </ul>
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center text-base text-red-700">
                    <XCircle className="w-4 h-4 mr-2" /> Don'ts
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <ul className="text-sm space-y-2 text-slate-600">
                    <li className="flex items-start"><XCircle className="w-4 h-4 mr-2 text-red-500 flex-shrink-0 mt-0.5" /> Use promotional/marketing language</li>
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
        <DialogContent className="sm:max-w-lg">
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
                  AI will parse your input and schedule the reminder automatically
                </p>
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
