import React, { useState, useEffect, useCallback } from 'react';
import { 
  Users, Plus, Search, Upload, Settings, Trash2, Edit2,
  Calendar, Gift, Heart, Phone, Mail, Filter, ChevronDown,
  Loader2, AlertCircle, CheckCircle, FolderPlus, Tag
} from 'lucide-react';
import { toast } from 'sonner';

import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Switch } from '@/components/ui/switch';
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
  DialogFooter,
} from "@/components/ui/dialog";
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from "@/components/ui/tabs";

import Layout from '../components/Layout';
import api from '../utils/api';
import * as XLSX from 'xlsx';

const TIMEZONES = [
  'Asia/Kolkata', 'Asia/Dubai', 'Asia/Singapore', 'Asia/Tokyo',
  'Europe/London', 'Europe/Paris', 'America/New_York', 'America/Los_Angeles'
];

const GROUP_COLORS = [
  '#3B82F6', '#10B981', '#F59E0B', '#EF4444', '#8B5CF6', 
  '#EC4899', '#06B6D4', '#84CC16'
];

const Contacts = ({ user, onLogout }) => {
  const [activeTab, setActiveTab] = useState('contacts');
  const [contacts, setContacts] = useState([]);
  const [groups, setGroups] = useState([]);
  const [settings, setSettings] = useState(null);
  const [upcoming, setUpcoming] = useState({ birthdays: [], anniversaries: [] });
  const [loading, setLoading] = useState(true);
  const [total, setTotal] = useState(0);
  
  // Filters
  const [search, setSearch] = useState('');
  const [selectedGroup, setSelectedGroup] = useState('');
  
  // Dialogs
  const [showContactDialog, setShowContactDialog] = useState(false);
  const [showGroupDialog, setShowGroupDialog] = useState(false);
  const [showSettingsDialog, setShowSettingsDialog] = useState(false);
  const [showImportDialog, setShowImportDialog] = useState(false);
  
  // Form states
  const [editingContact, setEditingContact] = useState(null);
  const [editingGroup, setEditingGroup] = useState(null);
  const [contactForm, setContactForm] = useState({
    name: '', email: '', phone: '', dob: '', anniversary: '',
    groupId: '', notes: '', sendBirthdayWish: true, sendAnniversaryWish: true
  });
  const [groupForm, setGroupForm] = useState({ name: '', description: '', color: '#3B82F6' });
  const [settingsForm, setSettingsForm] = useState({
    defaultCountryCode: '+91',
    birthdayEnabled: true, birthdayTime: '09:00', birthdayTemplateName: '',
    birthdayMessagePreview: 'Happy Birthday {{name}}! Wishing you a wonderful day!',
    anniversaryEnabled: true, anniversaryTime: '09:00', anniversaryTemplateName: '',
    anniversaryMessagePreview: 'Happy Anniversary {{name}}! Wishing you many more years!',
    timezone: 'Asia/Kolkata'
  });
  const [importData, setImportData] = useState([]);
  const [formLoading, setFormLoading] = useState(false);

  useEffect(() => {
    loadData();
  }, [search, selectedGroup]);

  const loadData = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (search) params.append('search', search);
      if (selectedGroup && selectedGroup !== 'all') params.append('group_id', selectedGroup);
      
      const [contactsRes, groupsRes, settingsRes, upcomingRes] = await Promise.all([
        api.get(`/contacts?${params.toString()}`),
        api.get('/contacts/groups'),
        api.get('/contacts/settings/auto-messages'),
        api.get('/contacts/stats/upcoming?days=30')
      ]);
      
      setContacts(contactsRes.data.contacts || []);
      setTotal(contactsRes.data.total || 0);
      setGroups(groupsRes.data.groups || []);
      setSettings(settingsRes.data.settings);
      setSettingsForm(settingsRes.data.settings);
      setUpcoming(upcomingRes.data);
    } catch (error) {
      toast.error('Failed to load data');
    } finally {
      setLoading(false);
    }
  };

  // Contact handlers
  const handleOpenContactDialog = (contact = null) => {
    if (contact) {
      setEditingContact(contact);
      setContactForm({
        name: contact.name || '',
        email: contact.email || '',
        phone: contact.phone || '',
        dob: contact.dob || '',
        anniversary: contact.anniversary || '',
        groupId: contact.groupId || '',
        notes: contact.notes || '',
        sendBirthdayWish: contact.sendBirthdayWish !== false,
        sendAnniversaryWish: contact.sendAnniversaryWish !== false
      });
    } else {
      setEditingContact(null);
      setContactForm({
        name: '', email: '', phone: '', dob: '', anniversary: '',
        groupId: '', notes: '', sendBirthdayWish: true, sendAnniversaryWish: true
      });
    }
    setShowContactDialog(true);
  };

  const handleSaveContact = async (e) => {
    e.preventDefault();
    setFormLoading(true);
    try {
      if (editingContact) {
        await api.put(`/contacts/${editingContact.id}`, contactForm);
        toast.success('Contact updated');
      } else {
        await api.post('/contacts', contactForm);
        toast.success('Contact created');
      }
      setShowContactDialog(false);
      loadData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to save contact');
    } finally {
      setFormLoading(false);
    }
  };

  const handleDeleteContact = async (contactId) => {
    if (!window.confirm('Delete this contact?')) return;
    try {
      await api.delete(`/contacts/${contactId}`);
      toast.success('Contact deleted');
      loadData();
    } catch (error) {
      toast.error('Failed to delete contact');
    }
  };

  // Group handlers
  const handleOpenGroupDialog = (group = null) => {
    if (group) {
      setEditingGroup(group);
      setGroupForm({ name: group.name, description: group.description || '', color: group.color });
    } else {
      setEditingGroup(null);
      setGroupForm({ name: '', description: '', color: '#3B82F6' });
    }
    setShowGroupDialog(true);
  };

  const handleSaveGroup = async (e) => {
    e.preventDefault();
    setFormLoading(true);
    try {
      if (editingGroup) {
        await api.put(`/contacts/groups/${editingGroup.id}`, groupForm);
        toast.success('Group updated');
      } else {
        await api.post('/contacts/groups', groupForm);
        toast.success('Group created');
      }
      setShowGroupDialog(false);
      loadData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to save group');
    } finally {
      setFormLoading(false);
    }
  };

  const handleDeleteGroup = async (groupId) => {
    if (!window.confirm('Delete this group? Contacts will be ungrouped.')) return;
    try {
      await api.delete(`/contacts/groups/${groupId}`);
      toast.success('Group deleted');
      loadData();
    } catch (error) {
      toast.error('Failed to delete group');
    }
  };

  // Settings handlers
  const handleSaveSettings = async (e) => {
    e.preventDefault();
    setFormLoading(true);
    try {
      await api.put('/contacts/settings/auto-messages', settingsForm);
      toast.success('Settings saved');
      setShowSettingsDialog(false);
      loadData();
    } catch (error) {
      toast.error('Failed to save settings');
    } finally {
      setFormLoading(false);
    }
  };

  // Import handlers
  const handleFileUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    
    try {
      const data = await file.arrayBuffer();
      const workbook = XLSX.read(data);
      const worksheet = workbook.Sheets[workbook.SheetNames[0]];
      const jsonData = XLSX.utils.sheet_to_json(worksheet);
      
      const parsed = jsonData.map(row => ({
        name: String(row.Name || row.name || '').trim(),
        email: String(row.Email || row.email || '').trim(),
        phone: String(row.Phone || row.phone || row['Phone Number'] || '').trim(),
        dob: row.DOB || row.dob || row.Birthday || row['Date of Birth'] || '',
        anniversary: row.Anniversary || row.anniversary || '',
        groupId: '',
        sendBirthdayWish: true,
        sendAnniversaryWish: true
      })).filter(c => c.name && c.phone);
      
      setImportData(parsed);
      toast.success(`Parsed ${parsed.length} contacts`);
    } catch (error) {
      toast.error('Failed to parse file');
    }
  };

  const handleImport = async () => {
    if (importData.length === 0) return;
    setFormLoading(true);
    try {
      const res = await api.post('/contacts/bulk-import', {
        contacts: importData,
        defaultCountryCode: settings?.defaultCountryCode || '+91'
      });
      toast.success(`Imported ${res.data.imported} contacts, ${res.data.skipped} duplicates skipped`);
      setShowImportDialog(false);
      setImportData([]);
      loadData();
    } catch (error) {
      toast.error('Import failed');
    } finally {
      setFormLoading(false);
    }
  };

  const formatDate = (dateStr) => {
    if (!dateStr) return '-';
    try {
      return new Date(dateStr).toLocaleDateString('en-IN', { day: 'numeric', month: 'short' });
    } catch {
      return dateStr;
    }
  };

  return (
    <Layout user={user} onLogout={onLogout}>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
          <div>
            <h1 className="text-3xl sm:text-4xl font-bold text-slate-900">Contacts</h1>
            <p className="text-slate-600 mt-1">Manage contacts and auto birthday/anniversary wishes</p>
          </div>
          <div className="flex gap-2">
            <Button variant="outline" onClick={() => setShowSettingsDialog(true)} data-testid="settings-btn">
              <Settings className="w-4 h-4 mr-2" /> Settings
            </Button>
            <Button variant="outline" onClick={() => setShowImportDialog(true)} data-testid="import-btn">
              <Upload className="w-4 h-4 mr-2" /> Import
            </Button>
            <Button onClick={() => handleOpenContactDialog()} data-testid="add-contact-btn">
              <Plus className="w-4 h-4 mr-2" /> Add Contact
            </Button>
          </div>
        </div>

        {/* Upcoming Events Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <Card className="border-pink-200 bg-gradient-to-br from-pink-50 to-white">
            <CardHeader className="pb-2">
              <CardTitle className="text-lg flex items-center text-pink-700">
                <Gift className="w-5 h-5 mr-2" /> Upcoming Birthdays
              </CardTitle>
            </CardHeader>
            <CardContent>
              {upcoming.birthdays.length > 0 ? (
                <div className="space-y-2">
                  {upcoming.birthdays.slice(0, 3).map((b, i) => (
                    <div key={i} className="flex justify-between items-center text-sm">
                      <span className="font-medium">{b.contact.name}</span>
                      <Badge variant="outline" className="bg-pink-100 text-pink-700">
                        {b.daysUntil === 0 ? 'Today!' : `${b.daysUntil} days`}
                      </Badge>
                    </div>
                  ))}
                  {upcoming.totalBirthdays > 3 && (
                    <p className="text-xs text-pink-600">+{upcoming.totalBirthdays - 3} more in next 30 days</p>
                  )}
                </div>
              ) : (
                <p className="text-sm text-slate-500">No upcoming birthdays</p>
              )}
            </CardContent>
          </Card>

          <Card className="border-red-200 bg-gradient-to-br from-red-50 to-white">
            <CardHeader className="pb-2">
              <CardTitle className="text-lg flex items-center text-red-700">
                <Heart className="w-5 h-5 mr-2" /> Upcoming Anniversaries
              </CardTitle>
            </CardHeader>
            <CardContent>
              {upcoming.anniversaries.length > 0 ? (
                <div className="space-y-2">
                  {upcoming.anniversaries.slice(0, 3).map((a, i) => (
                    <div key={i} className="flex justify-between items-center text-sm">
                      <span className="font-medium">{a.contact.name}</span>
                      <Badge variant="outline" className="bg-red-100 text-red-700">
                        {a.daysUntil === 0 ? 'Today!' : `${a.daysUntil} days`}
                      </Badge>
                    </div>
                  ))}
                  {upcoming.totalAnniversaries > 3 && (
                    <p className="text-xs text-red-600">+{upcoming.totalAnniversaries - 3} more in next 30 days</p>
                  )}
                </div>
              ) : (
                <p className="text-sm text-slate-500">No upcoming anniversaries</p>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Tabs */}
        <Tabs value={activeTab} onValueChange={setActiveTab}>
          <TabsList>
            <TabsTrigger value="contacts" data-testid="tab-contacts">
              <Users className="w-4 h-4 mr-2" /> Contacts ({total})
            </TabsTrigger>
            <TabsTrigger value="groups" data-testid="tab-groups">
              <Tag className="w-4 h-4 mr-2" /> Groups ({groups.length})
            </TabsTrigger>
          </TabsList>

          {/* Contacts Tab */}
          <TabsContent value="contacts" className="mt-4">
            {/* Filters */}
            <div className="flex gap-3 mb-4">
              <div className="relative flex-1 max-w-sm">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                <Input
                  placeholder="Search contacts..."
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  className="pl-9"
                  data-testid="search-input"
                />
              </div>
                <Select value={selectedGroup} onValueChange={setSelectedGroup}>
                <SelectTrigger className="w-48" data-testid="group-filter">
                  <SelectValue placeholder="All Groups" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Groups</SelectItem>
                  {groups.map(g => (
                    <SelectItem key={g.id} value={g.id}>{g.name}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {/* Contacts List */}
            {loading ? (
              <div className="text-center py-12"><Loader2 className="w-8 h-8 animate-spin mx-auto text-slate-400" /></div>
            ) : contacts.length === 0 ? (
              <Card>
                <CardContent className="py-12 text-center">
                  <Users className="w-12 h-12 text-slate-300 mx-auto mb-4" />
                  <h3 className="text-lg font-medium text-slate-700 mb-2">No contacts yet</h3>
                  <p className="text-slate-500 mb-4">Add contacts or import from Excel</p>
                  <Button onClick={() => handleOpenContactDialog()}>
                    <Plus className="w-4 h-4 mr-2" /> Add Contact
                  </Button>
                </CardContent>
              </Card>
            ) : (
              <div className="grid gap-3">
                {contacts.map(contact => (
                  <Card key={contact.id} className="hover:shadow-md transition-shadow" data-testid={`contact-${contact.id}`}>
                    <CardContent className="p-4">
                      <div className="flex items-center justify-between">
                        <div className="flex-1">
                          <div className="flex items-center gap-2 mb-1">
                            <h3 className="font-semibold text-slate-900">{contact.name}</h3>
                            {contact.groupName && (
                              <Badge variant="outline" style={{ borderColor: groups.find(g => g.id === contact.groupId)?.color }}>
                                {contact.groupName}
                              </Badge>
                            )}
                          </div>
                          <div className="flex flex-wrap gap-4 text-sm text-slate-500">
                            <span className="flex items-center"><Phone className="w-3 h-3 mr-1" />{contact.phone}</span>
                            {contact.email && <span className="flex items-center"><Mail className="w-3 h-3 mr-1" />{contact.email}</span>}
                            {contact.dob && <span className="flex items-center"><Gift className="w-3 h-3 mr-1 text-pink-500" />{formatDate(contact.dob)}</span>}
                            {contact.anniversary && <span className="flex items-center"><Heart className="w-3 h-3 mr-1 text-red-500" />{formatDate(contact.anniversary)}</span>}
                          </div>
                        </div>
                        <div className="flex gap-1">
                          <Button variant="ghost" size="sm" onClick={() => handleOpenContactDialog(contact)}>
                            <Edit2 className="w-4 h-4" />
                          </Button>
                          <Button variant="ghost" size="sm" className="text-red-500" onClick={() => handleDeleteContact(contact.id)}>
                            <Trash2 className="w-4 h-4" />
                          </Button>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            )}
          </TabsContent>

          {/* Groups Tab */}
          <TabsContent value="groups" className="mt-4">
            <div className="flex justify-end mb-4">
              <Button onClick={() => handleOpenGroupDialog()} data-testid="add-group-btn">
                <FolderPlus className="w-4 h-4 mr-2" /> New Group
              </Button>
            </div>

            {groups.length === 0 ? (
              <Card>
                <CardContent className="py-12 text-center">
                  <Tag className="w-12 h-12 text-slate-300 mx-auto mb-4" />
                  <h3 className="text-lg font-medium text-slate-700 mb-2">No groups yet</h3>
                  <p className="text-slate-500">Create groups to organize your contacts</p>
                </CardContent>
              </Card>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {groups.map(group => (
                  <Card key={group.id} className="hover:shadow-md transition-shadow" style={{ borderLeftWidth: 4, borderLeftColor: group.color }}>
                    <CardContent className="p-4">
                      <div className="flex justify-between items-start">
                        <div>
                          <h3 className="font-semibold text-slate-900">{group.name}</h3>
                          <p className="text-sm text-slate-500">{group.contactCount || 0} contacts</p>
                          {group.description && <p className="text-xs text-slate-400 mt-1">{group.description}</p>}
                        </div>
                        <div className="flex gap-1">
                          <Button variant="ghost" size="sm" onClick={() => handleOpenGroupDialog(group)}>
                            <Edit2 className="w-4 h-4" />
                          </Button>
                          <Button variant="ghost" size="sm" className="text-red-500" onClick={() => handleDeleteGroup(group.id)}>
                            <Trash2 className="w-4 h-4" />
                          </Button>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            )}
          </TabsContent>
        </Tabs>

        {/* Contact Dialog */}
        <Dialog open={showContactDialog} onOpenChange={setShowContactDialog}>
          <DialogContent className="max-w-lg max-h-[90vh] overflow-y-auto">
            <DialogHeader>
              <DialogTitle>{editingContact ? 'Edit Contact' : 'Add Contact'}</DialogTitle>
            </DialogHeader>
            <form onSubmit={handleSaveContact} className="space-y-4">
              <div className="grid grid-cols-2 gap-3">
                <div className="col-span-2">
                  <Label>Name *</Label>
                  <Input value={contactForm.name} onChange={e => setContactForm({...contactForm, name: e.target.value})} required />
                </div>
                <div className="col-span-2">
                  <Label>Phone *</Label>
                  <Input value={contactForm.phone} onChange={e => setContactForm({...contactForm, phone: e.target.value})} required placeholder="Phone number (country code will be added if missing)" />
                </div>
                <div className="col-span-2">
                  <Label>Email</Label>
                  <Input type="email" value={contactForm.email} onChange={e => setContactForm({...contactForm, email: e.target.value})} />
                </div>
                <div>
                  <Label>Date of Birth</Label>
                  <Input type="date" value={contactForm.dob} onChange={e => setContactForm({...contactForm, dob: e.target.value})} />
                </div>
                <div>
                  <Label>Anniversary</Label>
                  <Input type="date" value={contactForm.anniversary} onChange={e => setContactForm({...contactForm, anniversary: e.target.value})} />
                </div>
                <div className="col-span-2">
                  <Label>Group</Label>
                  <Select value={contactForm.groupId || 'none'} onValueChange={v => setContactForm({...contactForm, groupId: v === 'none' ? '' : v})}>
                    <SelectTrigger><SelectValue placeholder="No group" /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="none">No group</SelectItem>
                      {groups.map(g => <SelectItem key={g.id} value={g.id}>{g.name}</SelectItem>)}
                    </SelectContent>
                  </Select>
                </div>
                <div className="col-span-2">
                  <Label>Notes</Label>
                  <Textarea value={contactForm.notes} onChange={e => setContactForm({...contactForm, notes: e.target.value})} rows={2} />
                </div>
                <div className="flex items-center space-x-2">
                  <Switch checked={contactForm.sendBirthdayWish} onCheckedChange={v => setContactForm({...contactForm, sendBirthdayWish: v})} />
                  <Label>Send Birthday Wish</Label>
                </div>
                <div className="flex items-center space-x-2">
                  <Switch checked={contactForm.sendAnniversaryWish} onCheckedChange={v => setContactForm({...contactForm, sendAnniversaryWish: v})} />
                  <Label>Send Anniversary Wish</Label>
                </div>
              </div>
              <DialogFooter>
                <Button type="button" variant="outline" onClick={() => setShowContactDialog(false)}>Cancel</Button>
                <Button type="submit" disabled={formLoading}>
                  {formLoading && <Loader2 className="w-4 h-4 mr-2 animate-spin" />}
                  {editingContact ? 'Update' : 'Create'}
                </Button>
              </DialogFooter>
            </form>
          </DialogContent>
        </Dialog>

        {/* Group Dialog */}
        <Dialog open={showGroupDialog} onOpenChange={setShowGroupDialog}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>{editingGroup ? 'Edit Group' : 'Create Group'}</DialogTitle>
            </DialogHeader>
            <form onSubmit={handleSaveGroup} className="space-y-4">
              <div>
                <Label>Group Name *</Label>
                <Input value={groupForm.name} onChange={e => setGroupForm({...groupForm, name: e.target.value})} required />
              </div>
              <div>
                <Label>Description</Label>
                <Input value={groupForm.description} onChange={e => setGroupForm({...groupForm, description: e.target.value})} />
              </div>
              <div>
                <Label>Color</Label>
                <div className="flex gap-2 mt-2">
                  {GROUP_COLORS.map(c => (
                    <button key={c} type="button" className={`w-8 h-8 rounded-full border-2 ${groupForm.color === c ? 'border-slate-900' : 'border-transparent'}`} style={{ backgroundColor: c }} onClick={() => setGroupForm({...groupForm, color: c})} />
                  ))}
                </div>
              </div>
              <DialogFooter>
                <Button type="button" variant="outline" onClick={() => setShowGroupDialog(false)}>Cancel</Button>
                <Button type="submit" disabled={formLoading}>{editingGroup ? 'Update' : 'Create'}</Button>
              </DialogFooter>
            </form>
          </DialogContent>
        </Dialog>

        {/* Settings Dialog */}
        <Dialog open={showSettingsDialog} onOpenChange={setShowSettingsDialog}>
          <DialogContent className="max-w-lg max-h-[90vh] overflow-y-auto">
            <DialogHeader>
              <DialogTitle>Auto-Message Settings</DialogTitle>
              <DialogDescription>Configure automatic birthday and anniversary wishes</DialogDescription>
            </DialogHeader>
            <form onSubmit={handleSaveSettings} className="space-y-6">
              <div>
                <Label>Default Country Code</Label>
                <Input value={settingsForm.defaultCountryCode} onChange={e => setSettingsForm({...settingsForm, defaultCountryCode: e.target.value})} placeholder="+91" />
              </div>
              <div>
                <Label>Timezone</Label>
                <Select value={settingsForm.timezone} onValueChange={v => setSettingsForm({...settingsForm, timezone: v})}>
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>
                    {TIMEZONES.map(tz => <SelectItem key={tz} value={tz}>{tz}</SelectItem>)}
                  </SelectContent>
                </Select>
              </div>

              <div className="border rounded-lg p-4 space-y-3">
                <div className="flex items-center justify-between">
                  <Label className="flex items-center"><Gift className="w-4 h-4 mr-2 text-pink-500" /> Birthday Wishes</Label>
                  <Switch checked={settingsForm.birthdayEnabled} onCheckedChange={v => setSettingsForm({...settingsForm, birthdayEnabled: v})} />
                </div>
                {settingsForm.birthdayEnabled && (
                  <>
                    <div className="grid grid-cols-2 gap-3">
                      <div>
                        <Label className="text-xs">Send Time</Label>
                        <Input type="time" value={settingsForm.birthdayTime} onChange={e => setSettingsForm({...settingsForm, birthdayTime: e.target.value})} />
                      </div>
                      <div>
                        <Label className="text-xs">Template Name</Label>
                        <Input value={settingsForm.birthdayTemplateName} onChange={e => setSettingsForm({...settingsForm, birthdayTemplateName: e.target.value})} placeholder="birthday_wish" />
                      </div>
                    </div>
                    <div>
                      <Label className="text-xs">Message Preview</Label>
                      <Textarea value={settingsForm.birthdayMessagePreview} onChange={e => setSettingsForm({...settingsForm, birthdayMessagePreview: e.target.value})} rows={2} />
                      <p className="text-xs text-slate-500 mt-1">Use {'{{name}}'} for contact name</p>
                    </div>
                  </>
                )}
              </div>

              <div className="border rounded-lg p-4 space-y-3">
                <div className="flex items-center justify-between">
                  <Label className="flex items-center"><Heart className="w-4 h-4 mr-2 text-red-500" /> Anniversary Wishes</Label>
                  <Switch checked={settingsForm.anniversaryEnabled} onCheckedChange={v => setSettingsForm({...settingsForm, anniversaryEnabled: v})} />
                </div>
                {settingsForm.anniversaryEnabled && (
                  <>
                    <div className="grid grid-cols-2 gap-3">
                      <div>
                        <Label className="text-xs">Send Time</Label>
                        <Input type="time" value={settingsForm.anniversaryTime} onChange={e => setSettingsForm({...settingsForm, anniversaryTime: e.target.value})} />
                      </div>
                      <div>
                        <Label className="text-xs">Template Name</Label>
                        <Input value={settingsForm.anniversaryTemplateName} onChange={e => setSettingsForm({...settingsForm, anniversaryTemplateName: e.target.value})} placeholder="anniversary_wish" />
                      </div>
                    </div>
                    <div>
                      <Label className="text-xs">Message Preview</Label>
                      <Textarea value={settingsForm.anniversaryMessagePreview} onChange={e => setSettingsForm({...settingsForm, anniversaryMessagePreview: e.target.value})} rows={2} />
                    </div>
                  </>
                )}
              </div>

              <DialogFooter>
                <Button type="button" variant="outline" onClick={() => setShowSettingsDialog(false)}>Cancel</Button>
                <Button type="submit" disabled={formLoading}>Save Settings</Button>
              </DialogFooter>
            </form>
          </DialogContent>
        </Dialog>

        {/* Import Dialog */}
        <Dialog open={showImportDialog} onOpenChange={setShowImportDialog}>
          <DialogContent className="max-w-lg">
            <DialogHeader>
              <DialogTitle>Import Contacts</DialogTitle>
              <DialogDescription>Upload Excel/CSV with columns: Name, Email, Phone, DOB, Anniversary</DialogDescription>
            </DialogHeader>
            <div className="space-y-4">
              <Input type="file" accept=".xlsx,.xls,.csv" onChange={handleFileUpload} />
              {importData.length > 0 && (
                <div className="border rounded-lg p-3 max-h-48 overflow-y-auto">
                  <p className="text-sm font-medium mb-2">{importData.length} contacts ready to import</p>
                  {importData.slice(0, 5).map((c, i) => (
                    <p key={i} className="text-xs text-slate-600">{c.name} - {c.phone}</p>
                  ))}
                  {importData.length > 5 && <p className="text-xs text-slate-400">...and {importData.length - 5} more</p>}
                </div>
              )}
            </div>
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => { setShowImportDialog(false); setImportData([]); }}>Cancel</Button>
              <Button onClick={handleImport} disabled={importData.length === 0 || formLoading}>
                {formLoading && <Loader2 className="w-4 h-4 mr-2 animate-spin" />}
                Import {importData.length} Contacts
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>
    </Layout>
  );
};

export default Contacts;
