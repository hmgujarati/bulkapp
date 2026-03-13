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
  Bot, Settings, Package, ListOrdered, Users2, Plus, Trash2, Edit2,
  Upload, Download, Search, GripVertical, Loader2, ChevronDown, ChevronUp,
  Phone, FileText, BarChart3, Eye, Copy, Link
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
              <Link className="h-5 w-5 text-blue-600" /> Chatbot Webhook URL
            </CardTitle>
            <CardDescription>Configure this URL in your BizChat settings to receive client messages</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex items-center gap-2">
              <Input
                data-testid="webhook-url"
                readOnly
                value={settings.webhookUrl}
                className="font-mono text-xs bg-white"
              />
              <Button variant="outline" size="sm" onClick={copyWebhookUrl} className="shrink-0">
                <Copy className="h-4 w-4 mr-1" /> Copy
              </Button>
            </div>
            <p className="text-xs text-blue-600 mt-2">
              Set this as your webhook URL in BizChat so all incoming client messages trigger the chatbot.
            </p>
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
              <p className="text-xs text-slate-500">When enabled, incoming WhatsApp messages will trigger the chatbot flow</p>
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
          <CardTitle className="text-lg">Messages</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label>Greeting Message</Label>
            <Textarea
              data-testid="greeting-message"
              value={settings.greetingMessage}
              onChange={(e) => setSettings({ ...settings, greetingMessage: e.target.value })}
              rows={2}
            />
          </div>
          <div className="space-y-2">
            <Label>Completion Message</Label>
            <Textarea
              data-testid="completion-message"
              value={settings.completionMessage}
              onChange={(e) => setSettings({ ...settings, completionMessage: e.target.value })}
              rows={2}
            />
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Follow-up Settings</CardTitle>
          <CardDescription>If a client stops responding, the bot will send follow-up messages</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label>Follow-up Delay (minutes)</Label>
              <Input
                data-testid="followup-delay"
                type="number"
                min="1"
                value={settings.followUpDelayMinutes}
                onChange={(e) => setSettings({ ...settings, followUpDelayMinutes: parseInt(e.target.value) || 15 })}
              />
            </div>
            <div className="space-y-2">
              <Label>Max Follow-ups</Label>
              <Input
                data-testid="max-followups"
                type="number"
                min="1"
                max="10"
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

      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Notifications</CardTitle>
          <CardDescription>Get notified on WhatsApp when a new lead is captured</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <Label>Notify Main Number</Label>
              <p className="text-xs text-slate-500">Receive all lead notifications</p>
            </div>
            <Switch
              data-testid="notify-main-toggle"
              checked={settings.notifyMainNumber}
              onCheckedChange={(v) => setSettings({ ...settings, notifyMainNumber: v })}
            />
          </div>
          {settings.notifyMainNumber && (
            <div className="space-y-2">
              <Label>Main WhatsApp Number (with country code)</Label>
              <Input
                data-testid="main-notify-phone"
                placeholder="e.g. 919876543210"
                value={settings.mainNotifyPhone || ''}
                onChange={(e) => setSettings({ ...settings, mainNotifyPhone: e.target.value })}
              />
            </div>
          )}
        </CardContent>
      </Card>

      <Button data-testid="save-settings-btn" onClick={handleSave} disabled={saving} className="w-full">
        {saving && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
        Save Settings
      </Button>
    </div>
  );
};

// ===== Categories Tab =====
const CategoriesTab = () => {
  const [categories, setCategories] = useState([]);
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingCat, setEditingCat] = useState(null);
  const [form, setForm] = useState({ name: '', description: '', employeePhone: '', employeeName: '', triggerKeywords: [] });
  const [newTrigger, setNewTrigger] = useState('');

  const fetchCategories = useCallback(async () => {
    try {
      const res = await api.get('/chatbot/categories');
      setCategories(res.data.categories);
    } catch { toast.error('Failed to load categories'); }
    finally { setLoading(false); }
  }, []);

  useEffect(() => { fetchCategories(); }, [fetchCategories]);

  const openCreate = () => {
    setEditingCat(null);
    setForm({ name: '', description: '', employeePhone: '', employeeName: '', triggerKeywords: [] });
    setNewTrigger('');
    setDialogOpen(true);
  };

  const openEdit = (cat) => {
    setEditingCat(cat);
    setForm({ name: cat.name, description: cat.description || '', employeePhone: cat.employeePhone || '', employeeName: cat.employeeName || '', triggerKeywords: cat.triggerKeywords || [] });
    setNewTrigger('');
    setDialogOpen(true);
  };

  const handleSave = async () => {
    if (!form.name.trim()) { toast.error('Name is required'); return; }
    try {
      if (editingCat) {
        await api.put(`/chatbot/categories/${editingCat.id}`, form);
        toast.success('Category updated');
      } else {
        await api.post('/chatbot/categories', form);
        toast.success('Category created');
      }
      setDialogOpen(false);
      fetchCategories();
    } catch { toast.error('Failed to save category'); }
  };

  const handleDelete = async (id) => {
    if (!window.confirm('Delete this category and all its products & questions?')) return;
    try {
      await api.delete(`/chatbot/categories/${id}`);
      toast.success('Category deleted');
      fetchCategories();
    } catch { toast.error('Failed to delete'); }
  };

  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center">
        <p className="text-sm text-slate-600">Define product categories and assign employees for lead routing.</p>
        <Button data-testid="add-category-btn" size="sm" onClick={openCreate}>
          <Plus className="h-4 w-4 mr-1" /> Add Category
        </Button>
      </div>

      {loading ? (
        <div className="text-center py-8 text-slate-500">Loading...</div>
      ) : categories.length === 0 ? (
        <Card className="border-dashed">
          <CardContent className="text-center py-8">
            <Package className="h-8 w-8 mx-auto text-slate-400 mb-2" />
            <p className="text-slate-500 text-sm">No categories yet. Create your first one to get started.</p>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-3">
          {categories.map((cat) => (
            <Card key={cat.id} className="shadow-sm">
              <CardContent className="py-4 flex items-center justify-between">
                <div className="flex-1">
                  <div className="flex items-center gap-2">
                    <h3 className="font-medium text-sm">{cat.name}</h3>
                    {!cat.isActive && <Badge variant="secondary" className="text-xs">Inactive</Badge>}
                  </div>
                  {cat.description && <p className="text-xs text-slate-500 mt-0.5">{cat.description}</p>}
                  <div className="flex gap-3 mt-1.5 text-xs text-slate-500">
                    <span>{cat.productCount || 0} products</span>
                    <span>{cat.questionCount || 0} questions</span>
                    {cat.employeeName && (
                      <span className="flex items-center gap-1">
                        <Phone className="h-3 w-3" /> {cat.employeeName}
                      </span>
                    )}
                  </div>
                  {cat.triggerKeywords?.length > 0 && (
                    <div className="flex flex-wrap gap-1 mt-1.5">
                      {cat.triggerKeywords.map((kw, i) => (
                        <Badge key={i} variant="outline" className="text-xs bg-blue-50 text-blue-700 border-blue-200">{kw}</Badge>
                      ))}
                    </div>
                  )}
                </div>
                <div className="flex gap-1">
                  <Button variant="ghost" size="sm" className="h-8 w-8 p-0" onClick={() => openEdit(cat)}>
                    <Edit2 className="h-4 w-4" />
                  </Button>
                  <Button variant="ghost" size="sm" className="h-8 w-8 p-0 text-red-600" onClick={() => handleDelete(cat.id)}>
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{editingCat ? 'Edit Category' : 'New Category'}</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <div className="space-y-2">
              <Label>Category Name *</Label>
              <Input data-testid="category-name-input" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder="e.g. Mobile Phones" />
            </div>
            <div className="space-y-2">
              <Label>Description</Label>
              <Input value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} placeholder="Brief description" />
            </div>
            <div className="space-y-2">
              <Label>Employee Name (for lead routing)</Label>
              <Input value={form.employeeName} onChange={(e) => setForm({ ...form, employeeName: e.target.value })} placeholder="e.g. John" />
            </div>
            <div className="space-y-2">
              <Label>Employee WhatsApp (with country code)</Label>
              <Input value={form.employeePhone} onChange={(e) => setForm({ ...form, employeePhone: e.target.value })} placeholder="e.g. 919876543210" />
            </div>
            <div className="space-y-2">
              <Label>Trigger Keywords *</Label>
              <p className="text-xs text-slate-500">When a client sends any of these words, this category's chatbot flow starts</p>
              <div className="flex flex-wrap gap-1 mb-2">
                {form.triggerKeywords.map((kw, i) => (
                  <Badge key={i} variant="secondary" className="flex items-center gap-1">
                    {kw}
                    <button onClick={() => setForm({ ...form, triggerKeywords: form.triggerKeywords.filter((_, idx) => idx !== i) })} className="ml-1 text-red-500 hover:text-red-700">&times;</button>
                  </Badge>
                ))}
              </div>
              <div className="flex gap-2">
                <Input
                  data-testid="trigger-keyword-input"
                  value={newTrigger}
                  onChange={(e) => setNewTrigger(e.target.value)}
                  placeholder="e.g. phones, catalog, info..."
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') {
                      e.preventDefault();
                      if (newTrigger.trim()) {
                        setForm({ ...form, triggerKeywords: [...form.triggerKeywords, newTrigger.trim()] });
                        setNewTrigger('');
                      }
                    }
                  }}
                />
                <Button variant="outline" size="sm" onClick={() => {
                  if (newTrigger.trim()) {
                    setForm({ ...form, triggerKeywords: [...form.triggerKeywords, newTrigger.trim()] });
                    setNewTrigger('');
                  }
                }}>Add</Button>
              </div>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDialogOpen(false)}>Cancel</Button>
            <Button data-testid="save-category-btn" onClick={handleSave}>Save</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};

// ===== Products Tab =====
const ProductsTab = () => {
  const [products, setProducts] = useState([]);
  const [categories, setCategories] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedCategory, setSelectedCategory] = useState('all');
  const [search, setSearch] = useState('');
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingProd, setEditingProd] = useState(null);
  const [form, setForm] = useState({ categoryId: '', name: '', description: '', price: '' });
  const [uploading, setUploading] = useState(false);

  const fetchCategories = useCallback(async () => {
    try {
      const res = await api.get('/chatbot/categories');
      setCategories(res.data.categories);
    } catch {}
  }, []);

  const fetchProducts = useCallback(async () => {
    try {
      const params = { page, limit: 50 };
      if (selectedCategory !== 'all') params.category_id = selectedCategory;
      if (search) params.search = search;
      const res = await api.get('/chatbot/products', { params });
      setProducts(res.data.products);
      setTotalPages(res.data.totalPages);
    } catch { toast.error('Failed to load products'); }
    finally { setLoading(false); }
  }, [page, selectedCategory, search]);

  useEffect(() => { fetchCategories(); }, [fetchCategories]);
  useEffect(() => { fetchProducts(); }, [fetchProducts]);

  const openCreate = () => {
    setEditingProd(null);
    setForm({ categoryId: categories[0]?.id || '', name: '', description: '', price: '' });
    setDialogOpen(true);
  };

  const openEdit = (prod) => {
    setEditingProd(prod);
    setForm({ categoryId: prod.categoryId, name: prod.name, description: prod.description || '', price: prod.price || '' });
    setDialogOpen(true);
  };

  const handleSave = async () => {
    if (!form.name.trim() || !form.categoryId) { toast.error('Name and category are required'); return; }
    try {
      if (editingProd) {
        await api.put(`/chatbot/products/${editingProd.id}`, form);
        toast.success('Product updated');
      } else {
        await api.post('/chatbot/products', form);
        toast.success('Product created');
      }
      setDialogOpen(false);
      fetchProducts();
    } catch { toast.error('Failed to save product'); }
  };

  const handleDelete = async (id) => {
    try {
      await api.delete(`/chatbot/products/${id}`);
      toast.success('Deleted');
      fetchProducts();
    } catch { toast.error('Failed to delete'); }
  };

  const handleBulkUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    try {
      const formData = new FormData();
      formData.append('file', file);
      const res = await api.post('/chatbot/products/bulk-upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      toast.success(`Uploaded ${res.data.created} products`);
      if (res.data.errors?.length) {
        toast.error(`${res.data.errors.length} rows had errors`);
      }
      fetchProducts();
      fetchCategories();
    } catch (err) { toast.error(err.response?.data?.detail || 'Upload failed'); }
    finally { setUploading(false); e.target.value = ''; }
  };

  const getCategoryName = (catId) => categories.find(c => c.id === catId)?.name || 'Unknown';

  return (
    <div className="space-y-4">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-2">
        <p className="text-sm text-slate-600">Manage products within categories.</p>
        <div className="flex gap-2">
          <label className="cursor-pointer">
            <input type="file" accept=".csv" className="hidden" onChange={handleBulkUpload} />
            <Button variant="outline" size="sm" asChild disabled={uploading}>
              <span>
                {uploading ? <Loader2 className="h-4 w-4 mr-1 animate-spin" /> : <Upload className="h-4 w-4 mr-1" />}
                CSV Upload
              </span>
            </Button>
          </label>
          <Button data-testid="add-product-btn" size="sm" onClick={openCreate} disabled={categories.length === 0}>
            <Plus className="h-4 w-4 mr-1" /> Add Product
          </Button>
        </div>
      </div>

      <div className="flex gap-2">
        <Select value={selectedCategory} onValueChange={(v) => { setSelectedCategory(v); setPage(1); }}>
          <SelectTrigger className="w-48 h-9 text-sm">
            <SelectValue placeholder="All Categories" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Categories</SelectItem>
            {categories.map(c => <SelectItem key={c.id} value={c.id}>{c.name}</SelectItem>)}
          </SelectContent>
        </Select>
        <div className="relative flex-1">
          <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-slate-400" />
          <Input
            data-testid="product-search"
            className="pl-9 h-9 text-sm"
            placeholder="Search products..."
            value={search}
            onChange={(e) => { setSearch(e.target.value); setPage(1); }}
          />
        </div>
      </div>

      {loading ? (
        <div className="text-center py-8 text-slate-500">Loading...</div>
      ) : products.length === 0 ? (
        <Card className="border-dashed">
          <CardContent className="text-center py-8">
            <Package className="h-8 w-8 mx-auto text-slate-400 mb-2" />
            <p className="text-slate-500 text-sm">No products yet. Add individually or upload a CSV.</p>
            <p className="text-slate-400 text-xs mt-1">CSV format: Category, Product Name, Description, Price</p>
          </CardContent>
        </Card>
      ) : (
        <>
          <div className="border rounded-lg overflow-hidden">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-slate-50 border-b">
                  <th className="text-left py-2.5 px-3 font-medium text-slate-600 text-xs">Product</th>
                  <th className="text-left py-2.5 px-3 font-medium text-slate-600 text-xs hidden sm:table-cell">Category</th>
                  <th className="text-left py-2.5 px-3 font-medium text-slate-600 text-xs hidden md:table-cell">Price</th>
                  <th className="text-right py-2.5 px-3 font-medium text-slate-600 text-xs w-20">Actions</th>
                </tr>
              </thead>
              <tbody>
                {products.map(prod => (
                  <tr key={prod.id} className="border-b last:border-0 hover:bg-slate-50">
                    <td className="py-2 px-3">
                      <p className="font-medium text-slate-900">{prod.name}</p>
                      {prod.description && <p className="text-xs text-slate-500 truncate max-w-xs">{prod.description}</p>}
                    </td>
                    <td className="py-2 px-3 hidden sm:table-cell">
                      <Badge variant="secondary" className="text-xs">{getCategoryName(prod.categoryId)}</Badge>
                    </td>
                    <td className="py-2 px-3 hidden md:table-cell text-slate-600">{prod.price || '-'}</td>
                    <td className="py-2 px-3 text-right">
                      <div className="flex justify-end gap-1">
                        <Button variant="ghost" size="sm" className="h-7 w-7 p-0" onClick={() => openEdit(prod)}>
                          <Edit2 className="h-3.5 w-3.5" />
                        </Button>
                        <Button variant="ghost" size="sm" className="h-7 w-7 p-0 text-red-600" onClick={() => handleDelete(prod.id)}>
                          <Trash2 className="h-3.5 w-3.5" />
                        </Button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {totalPages > 1 && (
            <div className="flex justify-center gap-2">
              <Button variant="outline" size="sm" disabled={page <= 1} onClick={() => setPage(p => p - 1)}>Previous</Button>
              <span className="text-sm text-slate-500 py-1.5">Page {page} of {totalPages}</span>
              <Button variant="outline" size="sm" disabled={page >= totalPages} onClick={() => setPage(p => p + 1)}>Next</Button>
            </div>
          )}
        </>
      )}

      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{editingProd ? 'Edit Product' : 'New Product'}</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <div className="space-y-2">
              <Label>Category *</Label>
              <Select value={form.categoryId} onValueChange={(v) => setForm({ ...form, categoryId: v })}>
                <SelectTrigger><SelectValue placeholder="Select category" /></SelectTrigger>
                <SelectContent>
                  {categories.map(c => <SelectItem key={c.id} value={c.id}>{c.name}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>Product Name *</Label>
              <Input data-testid="product-name-input" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
            </div>
            <div className="space-y-2">
              <Label>Description</Label>
              <Input value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} />
            </div>
            <div className="space-y-2">
              <Label>Price</Label>
              <Input value={form.price} onChange={(e) => setForm({ ...form, price: e.target.value })} placeholder="e.g. 999" />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDialogOpen(false)}>Cancel</Button>
            <Button data-testid="save-product-btn" onClick={handleSave}>Save</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};

// ===== Question Flows Tab =====
const FlowsTab = () => {
  const [categories, setCategories] = useState([]);
  const [selectedCategoryId, setSelectedCategoryId] = useState('');
  const [questions, setQuestions] = useState([]);
  const [loading, setLoading] = useState(false);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingQ, setEditingQ] = useState(null);
  const [form, setForm] = useState({ questionText: '', questionType: 'text', options: [], isRequired: true });
  const [newOption, setNewOption] = useState('');

  useEffect(() => {
    api.get('/chatbot/categories').then(res => {
      setCategories(res.data.categories);
      if (res.data.categories.length > 0) setSelectedCategoryId(res.data.categories[0].id);
    }).catch(() => {});
  }, []);

  const fetchQuestions = useCallback(async () => {
    if (!selectedCategoryId) return;
    setLoading(true);
    try {
      const res = await api.get(`/chatbot/questions/${selectedCategoryId}`);
      setQuestions(res.data.questions);
    } catch { toast.error('Failed to load questions'); }
    finally { setLoading(false); }
  }, [selectedCategoryId]);

  useEffect(() => { fetchQuestions(); }, [fetchQuestions]);

  const openCreate = () => {
    setEditingQ(null);
    setForm({ questionText: '', questionType: 'text', options: [], isRequired: true });
    setDialogOpen(true);
  };

  const openEdit = (q) => {
    setEditingQ(q);
    setForm({ questionText: q.questionText, questionType: q.questionType, options: q.options || [], isRequired: q.isRequired });
    setDialogOpen(true);
  };

  const addOption = () => {
    if (!newOption.trim()) return;
    setForm({ ...form, options: [...form.options, newOption.trim()] });
    setNewOption('');
  };

  const removeOption = (idx) => {
    setForm({ ...form, options: form.options.filter((_, i) => i !== idx) });
  };

  const handleSave = async () => {
    if (!form.questionText.trim()) { toast.error('Question text is required'); return; }
    try {
      const payload = { ...form, categoryId: selectedCategoryId, sortOrder: questions.length };
      if (editingQ) {
        await api.put(`/chatbot/questions/${editingQ.id}`, form);
        toast.success('Question updated');
      } else {
        await api.post('/chatbot/questions', payload);
        toast.success('Question added');
      }
      setDialogOpen(false);
      fetchQuestions();
    } catch { toast.error('Failed to save'); }
  };

  const handleDelete = async (id) => {
    try {
      await api.delete(`/chatbot/questions/${id}`);
      toast.success('Question deleted');
      fetchQuestions();
    } catch { toast.error('Failed to delete'); }
  };

  const moveQuestion = async (idx, direction) => {
    const newQuestions = [...questions];
    const swapIdx = idx + direction;
    if (swapIdx < 0 || swapIdx >= newQuestions.length) return;
    [newQuestions[idx], newQuestions[swapIdx]] = [newQuestions[swapIdx], newQuestions[idx]];
    setQuestions(newQuestions);
    try {
      await api.put(`/chatbot/questions/reorder/${selectedCategoryId}`, newQuestions.map(q => q.id));
    } catch { toast.error('Failed to reorder'); fetchQuestions(); }
  };

  return (
    <div className="space-y-4">
      <p className="text-sm text-slate-600">Define the sequence of qualifying questions for each category.</p>

      {categories.length === 0 ? (
        <Card className="border-dashed"><CardContent className="text-center py-8">
          <p className="text-slate-500 text-sm">Create categories first to set up question flows.</p>
        </CardContent></Card>
      ) : (
        <>
          <div className="flex gap-2 items-center">
            <Select value={selectedCategoryId} onValueChange={setSelectedCategoryId}>
              <SelectTrigger className="w-64 h-9 text-sm"><SelectValue /></SelectTrigger>
              <SelectContent>
                {categories.map(c => <SelectItem key={c.id} value={c.id}>{c.name}</SelectItem>)}
              </SelectContent>
            </Select>
            <Button data-testid="add-question-btn" size="sm" onClick={openCreate}>
              <Plus className="h-4 w-4 mr-1" /> Add Question
            </Button>
          </div>

          {loading ? (
            <div className="text-center py-8 text-slate-500">Loading...</div>
          ) : questions.length === 0 ? (
            <Card className="border-dashed"><CardContent className="text-center py-8">
              <ListOrdered className="h-8 w-8 mx-auto text-slate-400 mb-2" />
              <p className="text-slate-500 text-sm">No questions yet for this category.</p>
            </CardContent></Card>
          ) : (
            <div className="space-y-2">
              {questions.map((q, idx) => (
                <Card key={q.id} className="shadow-sm">
                  <CardContent className="py-3 flex items-start gap-3">
                    <div className="flex flex-col gap-1 pt-1">
                      <Button variant="ghost" size="sm" className="h-6 w-6 p-0" onClick={() => moveQuestion(idx, -1)} disabled={idx === 0}>
                        <ChevronUp className="h-4 w-4" />
                      </Button>
                      <Button variant="ghost" size="sm" className="h-6 w-6 p-0" onClick={() => moveQuestion(idx, 1)} disabled={idx === questions.length - 1}>
                        <ChevronDown className="h-4 w-4" />
                      </Button>
                    </div>
                    <div className="flex-1">
                      <div className="flex items-center gap-2">
                        <span className="text-xs font-mono text-slate-400">Q{idx + 1}</span>
                        <p className="text-sm font-medium">{q.questionText}</p>
                      </div>
                      <div className="flex gap-2 mt-1">
                        <Badge variant="secondary" className="text-xs capitalize">{q.questionType}</Badge>
                        {q.options?.length > 0 && (
                          <span className="text-xs text-slate-500">{q.options.length} options</span>
                        )}
                        {!q.isRequired && <Badge variant="outline" className="text-xs">Optional</Badge>}
                      </div>
                      {q.options?.length > 0 && (
                        <div className="flex flex-wrap gap-1 mt-1.5">
                          {q.options.map((opt, i) => (
                            <span key={i} className="text-xs bg-slate-100 px-2 py-0.5 rounded">{opt}</span>
                          ))}
                        </div>
                      )}
                    </div>
                    <div className="flex gap-1">
                      <Button variant="ghost" size="sm" className="h-7 w-7 p-0" onClick={() => openEdit(q)}>
                        <Edit2 className="h-3.5 w-3.5" />
                      </Button>
                      <Button variant="ghost" size="sm" className="h-7 w-7 p-0 text-red-600" onClick={() => handleDelete(q.id)}>
                        <Trash2 className="h-3.5 w-3.5" />
                      </Button>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </>
      )}

      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{editingQ ? 'Edit Question' : 'Add Question'}</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <div className="space-y-2">
              <Label>Question Text *</Label>
              <Textarea
                data-testid="question-text-input"
                value={form.questionText}
                onChange={(e) => setForm({ ...form, questionText: e.target.value })}
                placeholder="e.g. What is your budget range?"
                rows={2}
              />
            </div>
            <div className="space-y-2">
              <Label>Answer Type</Label>
              <Select value={form.questionType} onValueChange={(v) => setForm({ ...form, questionType: v })}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="text">Free Text (client types answer)</SelectItem>
                  <SelectItem value="button">Buttons (up to 3 options)</SelectItem>
                  <SelectItem value="list">List (more than 3 options)</SelectItem>
                </SelectContent>
              </Select>
            </div>
            {(form.questionType === 'button' || form.questionType === 'list') && (
              <div className="space-y-2">
                <Label>Options</Label>
                <div className="flex flex-wrap gap-1 mb-2">
                  {form.options.map((opt, i) => (
                    <Badge key={i} variant="secondary" className="flex items-center gap-1">
                      {opt}
                      <button onClick={() => removeOption(i)} className="ml-1 text-red-500 hover:text-red-700">&times;</button>
                    </Badge>
                  ))}
                </div>
                <div className="flex gap-2">
                  <Input
                    value={newOption}
                    onChange={(e) => setNewOption(e.target.value)}
                    placeholder="Add option..."
                    onKeyDown={(e) => { if (e.key === 'Enter') { e.preventDefault(); addOption(); } }}
                  />
                  <Button variant="outline" size="sm" onClick={addOption}>Add</Button>
                </div>
              </div>
            )}
            <div className="flex items-center gap-2">
              <Switch checked={form.isRequired} onCheckedChange={(v) => setForm({ ...form, isRequired: v })} />
              <Label>Required</Label>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDialogOpen(false)}>Cancel</Button>
            <Button data-testid="save-question-btn" onClick={handleSave}>Save</Button>
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
  const [filters, setFilters] = useState({ status: '', category_id: '', search: '' });
  const [categories, setCategories] = useState([]);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [expandedLead, setExpandedLead] = useState(null);
  const [exporting, setExporting] = useState(false);

  useEffect(() => {
    api.get('/chatbot/categories').then(res => setCategories(res.data.categories)).catch(() => {});
  }, []);

  const fetchLeads = useCallback(async () => {
    try {
      const params = { page, limit: 20 };
      if (filters.status) params.status = filters.status;
      if (filters.category_id) params.category_id = filters.category_id;
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
      if (filters.category_id) params.category_id = filters.category_id;
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
      {/* Stats */}
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

      {/* Filters */}
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
        <Select value={filters.category_id || 'all'} onValueChange={(v) => { setFilters({ ...filters, category_id: v === 'all' ? '' : v }); setPage(1); }}>
          <SelectTrigger className="w-48 h-9 text-sm"><SelectValue placeholder="All Categories" /></SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Categories</SelectItem>
            {categories.map(c => <SelectItem key={c.id} value={c.id}>{c.name}</SelectItem>)}
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

      {/* Leads List */}
      {loading ? (
        <div className="text-center py-8 text-slate-500">Loading...</div>
      ) : leads.length === 0 ? (
        <Card className="border-dashed"><CardContent className="text-center py-8">
          <Users2 className="h-8 w-8 mx-auto text-slate-400 mb-2" />
          <p className="text-slate-500 text-sm">No leads yet. Leads will appear here when clients complete the chatbot flow.</p>
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
                      {lead.categoryName && <span>Category: {lead.categoryName}</span>}
                      {lead.productName && <span>Product: {lead.productName}</span>}
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
          <p className="text-slate-600 mt-1 text-sm">WhatsApp chatbot to qualify leads and collect information</p>
        </div>

        {stats && (
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <Card className="shadow-sm border bg-gradient-to-br from-blue-50 to-blue-100/50">
              <CardContent className="py-3 text-center">
                <p className="text-2xl font-bold text-blue-900">{stats.categories}</p>
                <p className="text-xs text-blue-700">Categories</p>
              </CardContent>
            </Card>
            <Card className="shadow-sm border bg-gradient-to-br from-indigo-50 to-indigo-100/50">
              <CardContent className="py-3 text-center">
                <p className="text-2xl font-bold text-indigo-900">{stats.products}</p>
                <p className="text-xs text-indigo-700">Products</p>
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

        <Tabs defaultValue="settings">
          <TabsList className="grid w-full grid-cols-5 h-10">
            <TabsTrigger value="settings" className="text-xs sm:text-sm" data-testid="tab-settings">
              <Settings className="h-4 w-4 mr-1 hidden sm:block" /> Settings
            </TabsTrigger>
            <TabsTrigger value="categories" className="text-xs sm:text-sm" data-testid="tab-categories">
              <Package className="h-4 w-4 mr-1 hidden sm:block" /> Categories
            </TabsTrigger>
            <TabsTrigger value="products" className="text-xs sm:text-sm" data-testid="tab-products">
              <Package className="h-4 w-4 mr-1 hidden sm:block" /> Products
            </TabsTrigger>
            <TabsTrigger value="flows" className="text-xs sm:text-sm" data-testid="tab-flows">
              <ListOrdered className="h-4 w-4 mr-1 hidden sm:block" /> Flows
            </TabsTrigger>
            <TabsTrigger value="leads" className="text-xs sm:text-sm" data-testid="tab-leads">
              <Users2 className="h-4 w-4 mr-1 hidden sm:block" /> Leads
            </TabsTrigger>
          </TabsList>

          <div className="mt-4">
            <TabsContent value="settings"><SettingsTab /></TabsContent>
            <TabsContent value="categories"><CategoriesTab /></TabsContent>
            <TabsContent value="products"><ProductsTab /></TabsContent>
            <TabsContent value="flows"><FlowsTab /></TabsContent>
            <TabsContent value="leads"><LeadsTab /></TabsContent>
          </div>
        </Tabs>
      </div>
    </Layout>
  );
};

export default ChatbotPage;
