import React, { useState, useEffect } from 'react';
import Layout from '../components/Layout';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger, DialogFooter } from '@/components/ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import { Switch } from '@/components/ui/switch';
import { Users, UserPlus, Pause, Play, Trash2, Shield, Loader2, LogIn } from 'lucide-react';
import { toast } from 'sonner';
import api from '../utils/api';

// Feature definitions with labels and descriptions
const FEATURE_DEFINITIONS = {
  bulk_messages: { label: 'Bulk Messages', description: 'Send bulk WhatsApp campaigns' },
  reminders: { label: 'Reminders', description: 'AI-powered reminder bot' },
  contacts: { label: 'Contacts', description: 'Contact management & auto-wishes' },
  templates: { label: 'Templates', description: 'Message template library' },
  campaigns: { label: 'Campaigns', description: 'Campaign history & analytics' },
  indiamart: { label: 'Indiamart', description: 'Indiamart lead integration' },
  chatbot: { label: 'Lead Chatbot', description: 'WhatsApp lead qualification chatbot' },
};

const AdminDashboard = ({ user, onLogout, onLoginAs }) => {
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  const [featuresDialogOpen, setFeaturesDialogOpen] = useState(false);
  const [selectedUser, setSelectedUser] = useState(null);
  const [featuresSaving, setFeaturesSaving] = useState(false);
  const [newUser, setNewUser] = useState({
    email: '',
    password: '',
    firstName: '',
    lastName: '',
    role: 'user'
  });

  useEffect(() => {
    fetchUsers();
  }, []);

  const fetchUsers = async () => {
    try {
      const response = await api.get('/users');
      setUsers(response.data.users);
    } catch (error) {
      toast.error('Failed to fetch users');
    } finally {
      setLoading(false);
    }
  };

  const handleCreateUser = async (e) => {
    e.preventDefault();
    try {
      await api.post('/auth/register', newUser);
      toast.success('User created successfully');
      setCreateDialogOpen(false);
      setNewUser({ email: '', password: '', firstName: '', lastName: '', role: 'user' });
      fetchUsers();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to create user');
    }
  };

  const handlePauseUser = async (userId, isPaused) => {
    try {
      await api.put(`/users/${userId}/pause`, { isPaused: !isPaused });
      toast.success(`User ${!isPaused ? 'paused' : 'unpaused'} successfully`);
      fetchUsers();
    } catch (error) {
      toast.error('Failed to update user status');
    }
  };

  const handleUpdateLimit = async (userId, newLimit) => {
    try {
      await api.put(`/users/${userId}/limit`, { dailyLimit: parseInt(newLimit) });
      toast.success('Daily limit updated successfully');
      fetchUsers();
    } catch (error) {
      toast.error('Failed to update daily limit');
    }
  };

  const handleDeleteUser = async (userId) => {
    if (!window.confirm('Are you sure you want to delete this user? This will also delete all their campaigns and templates.')) {
      return;
    }
    
    try {
      await api.delete(`/users/${userId}`);
      toast.success('User deleted successfully');
      fetchUsers();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to delete user');
    }
  };

  const openFeaturesDialog = (u) => {
    setSelectedUser({
      ...u,
      features: u.features || {
        bulk_messages: true,
        reminders: true,
        contacts: true,
        templates: true,
        campaigns: true,
        indiamart: false,
        chatbot: false
      }
    });
    setFeaturesDialogOpen(true);
  };

  const handleFeatureToggle = (featureKey, enabled) => {
    setSelectedUser(prev => ({
      ...prev,
      features: {
        ...prev.features,
        [featureKey]: enabled
      }
    }));
  };

  const handleSaveFeatures = async () => {
    if (!selectedUser) return;
    
    setFeaturesSaving(true);
    try {
      await api.put(`/users/${selectedUser.id}/features`, selectedUser.features);
      toast.success('Features updated successfully');
      setFeaturesDialogOpen(false);
      fetchUsers();
    } catch (error) {
      toast.error('Failed to update features');
    } finally {
      setFeaturesSaving(false);
    }
  };

  const handleLoginAs = async (targetUser) => {
    try {
      const res = await api.post(`/auth/login-as/${targetUser.id}`);
      if (onLoginAs) {
        onLoginAs(res.data);
      } else {
        localStorage.setItem('token', res.data.token);
        localStorage.setItem('user', JSON.stringify(res.data.user));
        window.location.href = '/';
      }
      toast.success(`Logged in as ${targetUser.firstName || targetUser.email}`);
    } catch {
      toast.error('Failed to login as user');
    }
  };

  const stats = {
    totalUsers: users.length,
    activeUsers: users.filter(u => !u.isPaused).length,
    pausedUsers: users.filter(u => u.isPaused).length,
  };

  const getEnabledFeaturesCount = (u) => {
    const features = u.features || {};
    return Object.values(features).filter(Boolean).length;
  };

  return (
    <Layout user={user} onLogout={onLogout}>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
          <div>
            <h1 className="text-2xl sm:text-3xl font-bold text-slate-900">Admin Dashboard</h1>
            <p className="text-slate-600 mt-1 text-sm">Manage users and feature access</p>
          </div>

          <Dialog open={createDialogOpen} onOpenChange={setCreateDialogOpen}>
            <DialogTrigger asChild>
              <Button className="bg-blue-600 hover:bg-blue-700" data-testid="create-user-button">
                <UserPlus className="h-4 w-4 mr-2" />
                Create User
              </Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>Create New User</DialogTitle>
                <DialogDescription>Add a new user account to the system</DialogDescription>
              </DialogHeader>
              <form onSubmit={handleCreateUser} className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="firstName">First Name</Label>
                    <Input
                      id="firstName"
                      value={newUser.firstName}
                      onChange={(e) => setNewUser({ ...newUser, firstName: e.target.value })}
                      required
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="lastName">Last Name</Label>
                    <Input
                      id="lastName"
                      value={newUser.lastName}
                      onChange={(e) => setNewUser({ ...newUser, lastName: e.target.value })}
                      required
                    />
                  </div>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="email">Email</Label>
                  <Input
                    id="email"
                    type="email"
                    value={newUser.email}
                    onChange={(e) => setNewUser({ ...newUser, email: e.target.value })}
                    required
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="password">Password</Label>
                  <Input
                    id="password"
                    type="password"
                    value={newUser.password}
                    onChange={(e) => setNewUser({ ...newUser, password: e.target.value })}
                    required
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="role">Role</Label>
                  <Select value={newUser.role} onValueChange={(value) => setNewUser({ ...newUser, role: value })}>
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="user">User</SelectItem>
                      <SelectItem value="admin">Admin</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <Button type="submit" className="w-full">Create User</Button>
              </form>
            </DialogContent>
          </Dialog>
        </div>

        {/* Stats Cards */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <Card className="shadow-sm border bg-gradient-to-br from-blue-50 to-blue-100/50">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium text-blue-900">Total Users</CardTitle>
              <Users className="h-4 w-4 text-blue-600" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-blue-900">{stats.totalUsers}</div>
            </CardContent>
          </Card>

          <Card className="shadow-sm border bg-gradient-to-br from-green-50 to-green-100/50">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium text-green-900">Active</CardTitle>
              <Play className="h-4 w-4 text-green-600" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-green-900">{stats.activeUsers}</div>
            </CardContent>
          </Card>

          <Card className="shadow-sm border bg-gradient-to-br from-amber-50 to-amber-100/50">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium text-amber-900">Paused</CardTitle>
              <Pause className="h-4 w-4 text-amber-600" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-amber-900">{stats.pausedUsers}</div>
            </CardContent>
          </Card>
        </div>

        {/* Users Table */}
        <Card className="shadow-sm">
          <CardHeader>
            <CardTitle>Users</CardTitle>
            <CardDescription>Manage user accounts and feature access</CardDescription>
          </CardHeader>
          <CardContent>
            {loading ? (
              <div className="text-center py-8 text-slate-500">Loading users...</div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full" data-testid="users-table">
                  <thead>
                    <tr className="border-b border-slate-200">
                      <th className="text-left py-3 px-3 text-xs font-medium text-slate-600 uppercase">User</th>
                      <th className="text-left py-3 px-3 text-xs font-medium text-slate-600 uppercase hidden sm:table-cell">Role</th>
                      <th className="text-left py-3 px-3 text-xs font-medium text-slate-600 uppercase">Status</th>
                      <th className="text-left py-3 px-3 text-xs font-medium text-slate-600 uppercase hidden md:table-cell">Features</th>
                      <th className="text-left py-3 px-3 text-xs font-medium text-slate-600 uppercase hidden lg:table-cell">Limit</th>
                      <th className="text-left py-3 px-3 text-xs font-medium text-slate-600 uppercase">Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {users.map((u) => (
                      <tr key={u.id} className="border-b border-slate-100 hover:bg-slate-50">
                        <td className="py-3 px-3">
                          <div>
                            <p className="text-sm font-medium text-slate-900">{u.firstName} {u.lastName}</p>
                            <p className="text-xs text-slate-500">{u.email}</p>
                          </div>
                        </td>
                        <td className="py-3 px-3 hidden sm:table-cell">
                          <Badge variant={u.role === 'admin' ? 'default' : 'secondary'} className="text-xs">
                            {u.role}
                          </Badge>
                        </td>
                        <td className="py-3 px-3">
                          <Badge 
                            variant={u.isPaused ? 'destructive' : 'outline'} 
                            className={`text-xs ${!u.isPaused ? 'bg-green-50 text-green-700 border-green-200' : ''}`}
                          >
                            {u.isPaused ? 'Paused' : 'Active'}
                          </Badge>
                        </td>
                        <td className="py-3 px-3 hidden md:table-cell">
                          <Button 
                            variant="ghost" 
                            size="sm" 
                            className="text-xs h-7"
                            onClick={() => openFeaturesDialog(u)}
                          >
                            <Shield className="h-3 w-3 mr-1" />
                            {getEnabledFeaturesCount(u)}/{Object.keys(FEATURE_DEFINITIONS).length}
                          </Button>
                        </td>
                        <td className="py-3 px-3 hidden lg:table-cell">
                          <Select
                            value={u.dailyLimit?.toString() || '1000'}
                            onValueChange={(value) => handleUpdateLimit(u.id, value)}
                          >
                            <SelectTrigger className="w-28 h-8 text-xs">
                              <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                              <SelectItem value="250">250</SelectItem>
                              <SelectItem value="500">500</SelectItem>
                              <SelectItem value="1000">1,000</SelectItem>
                              <SelectItem value="2500">2,500</SelectItem>
                              <SelectItem value="5000">5,000</SelectItem>
                              <SelectItem value="10000">10,000</SelectItem>
                              <SelectItem value="25000">25,000</SelectItem>
                              <SelectItem value="50000">50,000</SelectItem>
                              <SelectItem value="100000">100,000</SelectItem>
                            </SelectContent>
                          </Select>
                        </td>
                        <td className="py-3 px-3">
                          <div className="flex items-center space-x-1">
                            <Button
                              variant="ghost"
                              size="sm"
                              className="h-8 w-8 p-0"
                              onClick={() => handleLoginAs(u)}
                              title="Login as this user"
                              data-testid={`login-as-${u.id}`}
                            >
                              <LogIn className="h-4 w-4 text-blue-600" />
                            </Button>
                            <Button
                              variant="ghost"
                              size="sm"
                              className="h-8 w-8 p-0 md:hidden"
                              onClick={() => openFeaturesDialog(u)}
                              title="Manage Features"
                            >
                              <Shield className="h-4 w-4" />
                            </Button>
                            <Button
                              variant="ghost"
                              size="sm"
                              className="h-8 w-8 p-0"
                              onClick={() => handlePauseUser(u.id, u.isPaused)}
                              title={u.isPaused ? 'Unpause' : 'Pause'}
                              data-testid={`pause-user-${u.id}`}
                            >
                              {u.isPaused ? <Play className="h-4 w-4 text-green-600" /> : <Pause className="h-4 w-4 text-amber-600" />}
                            </Button>
                            <Button
                              variant="ghost"
                              size="sm"
                              className="h-8 w-8 p-0 text-red-600 hover:text-red-700 hover:bg-red-50"
                              onClick={() => handleDeleteUser(u.id)}
                              title="Delete"
                              data-testid={`delete-user-${u.id}`}
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
            )}
          </CardContent>
        </Card>

        {/* Features Dialog */}
        <Dialog open={featuresDialogOpen} onOpenChange={setFeaturesDialogOpen}>
          <DialogContent className="max-w-md">
            <DialogHeader>
              <DialogTitle>Manage Features</DialogTitle>
              <DialogDescription>
                {selectedUser && `Configure feature access for ${selectedUser.firstName} ${selectedUser.lastName}`}
              </DialogDescription>
            </DialogHeader>
            
            <div className="space-y-4 py-4">
              {Object.entries(FEATURE_DEFINITIONS).map(([key, { label, description }]) => (
                <div key={key} className="flex items-center justify-between">
                  <div className="flex-1">
                    <Label className="text-sm font-medium">{label}</Label>
                    <p className="text-xs text-slate-500">{description}</p>
                  </div>
                  <Switch
                    checked={selectedUser?.features?.[key] ?? false}
                    onCheckedChange={(checked) => handleFeatureToggle(key, checked)}
                  />
                </div>
              ))}
            </div>

            <DialogFooter>
              <Button variant="outline" onClick={() => setFeaturesDialogOpen(false)}>
                Cancel
              </Button>
              <Button onClick={handleSaveFeatures} disabled={featuresSaving}>
                {featuresSaving && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
                Save Changes
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>
    </Layout>
  );
};

export default AdminDashboard;
