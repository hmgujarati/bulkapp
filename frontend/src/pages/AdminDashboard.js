import React, { useState, useEffect } from 'react';
import Layout from '../components/Layout';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import { Users, UserPlus, Pause, Play, Settings as SettingsIcon, Trash2 } from 'lucide-react';
import { toast } from 'sonner';
import api from '../utils/api';

const AdminDashboard = ({ user, onLogout }) => {
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [createDialogOpen, setCreateDialogOpen] = useState(false);
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
    if (window.confirm('Are you sure you want to delete this user? This action cannot be undone.')) {
      try {
        await api.delete(`/users/${userId}`);
        toast.success('User deleted successfully');
        fetchUsers();
      } catch (error) {
        toast.error('Failed to delete user');
      }
    }
  };

  const stats = {
    totalUsers: users.length,
    activeUsers: users.filter(u => !u.isPaused).length,
    pausedUsers: users.filter(u => u.isPaused).length,
  };

  return (
    <Layout user={user} onLogout={onLogout}>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex justify-between items-center">
          <div>
            <h1 className="text-3xl sm:text-4xl font-bold text-slate-900">Admin Dashboard</h1>
            <p className="text-slate-600 mt-1">Manage users and monitor system</p>
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
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <Card className="shadow-lg border-0 bg-gradient-to-br from-blue-50 to-blue-100">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium text-blue-900">Total Users</CardTitle>
              <Users className="h-5 w-5 text-blue-600" />
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold text-blue-900">{stats.totalUsers}</div>
            </CardContent>
          </Card>

          <Card className="shadow-lg border-0 bg-gradient-to-br from-green-50 to-green-100">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium text-green-900">Active Users</CardTitle>
              <Play className="h-5 w-5 text-green-600" />
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold text-green-900">{stats.activeUsers}</div>
            </CardContent>
          </Card>

          <Card className="shadow-lg border-0 bg-gradient-to-br from-amber-50 to-amber-100">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium text-amber-900">Paused Users</CardTitle>
              <Pause className="h-5 w-5 text-amber-600" />
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold text-amber-900">{stats.pausedUsers}</div>
            </CardContent>
          </Card>
        </div>

        {/* Users Table */}
        <Card className="shadow-lg border-0">
          <CardHeader>
            <CardTitle>Users</CardTitle>
            <CardDescription>Manage all user accounts</CardDescription>
          </CardHeader>
          <CardContent>
            {loading ? (
              <div className="text-center py-8 text-slate-500">Loading users...</div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full" data-testid="users-table">
                  <thead>
                    <tr className="border-b border-slate-200">
                      <th className="text-left py-3 px-4 text-sm font-medium text-slate-700">Name</th>
                      <th className="text-left py-3 px-4 text-sm font-medium text-slate-700">Email</th>
                      <th className="text-left py-3 px-4 text-sm font-medium text-slate-700">Role</th>
                      <th className="text-left py-3 px-4 text-sm font-medium text-slate-700">Status</th>
                      <th className="text-left py-3 px-4 text-sm font-medium text-slate-700">Daily Limit</th>
                      <th className="text-left py-3 px-4 text-sm font-medium text-slate-700">Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {users.map((u) => (
                      <tr key={u.id} className="border-b border-slate-100 hover:bg-slate-50">
                        <td className="py-3 px-4 text-sm text-slate-900">{u.firstName} {u.lastName}</td>
                        <td className="py-3 px-4 text-sm text-slate-600">{u.email}</td>
                        <td className="py-3 px-4 text-sm">
                          <Badge variant={u.role === 'admin' ? 'default' : 'secondary'}>
                            {u.role}
                          </Badge>
                        </td>
                        <td className="py-3 px-4 text-sm">
                          <Badge variant={u.isPaused ? 'destructive' : 'success'}>
                            {u.isPaused ? 'Paused' : 'Active'}
                          </Badge>
                        </td>
                        <td className="py-3 px-4 text-sm">
                          <Select
                            defaultValue={u.dailyLimit.toString()}
                            onValueChange={(value) => handleUpdateLimit(u.id, value)}
                          >
                            <SelectTrigger className="w-32">
                              <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                              <SelectItem value="250">250 (Tier 1)</SelectItem>
                              <SelectItem value="1000">1,000 (Tier 2)</SelectItem>
                              <SelectItem value="10000">10,000 (Tier 3)</SelectItem>
                              <SelectItem value="100000">100,000 (Tier 4)</SelectItem>
                            </SelectContent>
                          </Select>
                        </td>
                        <td className="py-3 px-4 text-sm">
                          <div className="flex space-x-2">
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => handlePauseUser(u.id, u.isPaused)}
                              data-testid={`pause-user-${u.id}`}
                            >
                              {u.isPaused ? <Play className="h-4 w-4" /> : <Pause className="h-4 w-4" />}
                            </Button>
                            <Button
                              variant="ghost"
                              size="sm"
                              className="text-red-600 hover:text-red-700 hover:bg-red-50"
                              onClick={() => handleDeleteUser(u.id)}
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
      </div>
    </Layout>
  );
};

export default AdminDashboard;