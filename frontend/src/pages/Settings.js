import React, { useState, useEffect } from 'react';
import Layout from '../components/Layout';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Settings as SettingsIcon, Key, User } from 'lucide-react';
import { toast } from 'sonner';
import api from '../utils/api';

const Settings = ({ user, onLogout }) => {
  const [profile, setProfile] = useState({
    firstName: '',
    lastName: '',
    email: ''
  });
  const [bizChatToken, setBizChatToken] = useState('');
  const [bizChatVendorUID, setBizChatVendorUID] = useState('');
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  
  // Password change
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [changingPassword, setChangingPassword] = useState(false);

  useEffect(() => {
    fetchUserData();
  }, []);

  const fetchUserData = async () => {
    try {
      const response = await api.get('/auth/me');
      const userData = response.data;
      setProfile({
        firstName: userData.firstName,
        lastName: userData.lastName,
        email: userData.email
      });
      setBizChatToken(userData.bizChatToken || '');
      setBizChatVendorUID(userData.bizChatVendorUID || '');
    } catch (error) {
      toast.error('Failed to fetch user data');
    } finally {
      setLoading(false);
    }
  };

  const handleUpdateProfile = async (e) => {
    e.preventDefault();
    setSaving(true);
    try {
      await api.put(`/users/${user.id}`, profile);
      toast.success('Profile updated successfully');
      
      // Update local storage
      const userData = JSON.parse(localStorage.getItem('user'));
      userData.firstName = profile.firstName;
      userData.lastName = profile.lastName;
      localStorage.setItem('user', JSON.stringify(userData));
    } catch (error) {
      toast.error('Failed to update profile');
    } finally {
      setSaving(false);
    }
  };

  const handleUpdateToken = async (e) => {
    e.preventDefault();
    setSaving(true);
    try {
      await api.put(`/users/${user.id}`, { bizChatToken, bizChatVendorUID });
      toast.success('BizChat API credentials updated successfully');
    } catch (error) {
      toast.error('Failed to update API credentials');
    } finally {
      setSaving(false);
    }
  };

  const handleChangePassword = async (e) => {
    e.preventDefault();
    
    if (newPassword !== confirmPassword) {
      toast.error('New passwords do not match');
      return;
    }
    
    if (newPassword.length < 6) {
      toast.error('Password must be at least 6 characters');
      return;
    }
    
    setChangingPassword(true);
    try {
      await api.post('/auth/change-password', {
        currentPassword,
        newPassword
      });
      toast.success('Password changed successfully');
      setCurrentPassword('');
      setNewPassword('');
      setConfirmPassword('');
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to change password');
    } finally {
      setChangingPassword(false);
    }
  };

  if (loading) {
    return (
      <Layout user={user} onLogout={onLogout}>
        <div className="text-center py-12 text-slate-500">Loading settings...</div>
      </Layout>
    );
  }

  return (
    <Layout user={user} onLogout={onLogout}>
      <div className="space-y-6 max-w-3xl">
        <div>
          <h1 className="text-3xl sm:text-4xl font-bold text-slate-900">Settings</h1>
          <p className="text-slate-600 mt-1">Manage your account and API configuration</p>
        </div>

        {/* Profile Settings */}
        <Card className="shadow-lg border-0">
          <CardHeader>
            <div className="flex items-center space-x-3">
              <div className="flex items-center justify-center w-10 h-10 rounded-lg bg-blue-100">
                <User className="h-5 w-5 text-blue-600" />
              </div>
              <div>
                <CardTitle>Profile Information</CardTitle>
                <CardDescription>Update your personal details</CardDescription>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleUpdateProfile} className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="firstName">First Name</Label>
                  <Input
                    id="firstName"
                    value={profile.firstName}
                    onChange={(e) => setProfile({ ...profile, firstName: e.target.value })}
                    required
                    data-testid="first-name-input"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="lastName">Last Name</Label>
                  <Input
                    id="lastName"
                    value={profile.lastName}
                    onChange={(e) => setProfile({ ...profile, lastName: e.target.value })}
                    required
                    data-testid="last-name-input"
                  />
                </div>
              </div>

              <div className="space-y-2">
                <Label htmlFor="email">Email Address</Label>
                <Input
                  id="email"
                  type="email"
                  value={profile.email}
                  disabled
                  className="bg-slate-50"
                  data-testid="email-input"
                />
                <p className="text-xs text-slate-500">Email cannot be changed</p>
              </div>

              <Button type="submit" disabled={saving} data-testid="save-profile-button">
                {saving ? 'Saving...' : 'Save Changes'}
              </Button>
            </form>
          </CardContent>
        </Card>

        {/* API Token Settings */}
        <Card className="shadow-lg border-0">
          <CardHeader>
            <div className="flex items-center space-x-3">
              <div className="flex items-center justify-center w-10 h-10 rounded-lg bg-emerald-100">
                <Key className="h-5 w-5 text-emerald-600" />
              </div>
              <div>
                <CardTitle>BizChat API Configuration</CardTitle>
                <CardDescription>Configure your WhatsApp API access token</CardDescription>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleUpdateToken} className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="bizChatVendorUID">Vendor UID</Label>
                <Input
                  id="bizChatVendorUID"
                  placeholder="e.g., 9a1497da-b76f-4666-a439-70402e99db57"
                  value={bizChatVendorUID}
                  onChange={(e) => setBizChatVendorUID(e.target.value)}
                  data-testid="bizchat-vendor-uid-input"
                />
                <p className="text-sm text-slate-600">
                  Your unique Vendor UID from BizChat dashboard
                </p>
              </div>

              <div className="space-y-2">
                <Label htmlFor="bizChatToken">API Token</Label>
                <Input
                  id="bizChatToken"
                  type="password"
                  placeholder="Enter your BizChat API token"
                  value={bizChatToken}
                  onChange={(e) => setBizChatToken(e.target.value)}
                  data-testid="bizchat-token-input"
                />
                <p className="text-sm text-slate-600">
                  Your BizChat API token for authentication
                </p>
              </div>

              <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                <p className="text-sm text-blue-900 font-medium mb-2">How to get your API token:</p>
                <ol className="text-sm text-blue-800 space-y-1 list-decimal list-inside">
                  <li>Log in to your BizChat dashboard</li>
                  <li>Navigate to API Settings</li>
                  <li>Copy your API token</li>
                  <li>Paste it in the field above</li>
                </ol>
              </div>

              <div className="bg-amber-50 border border-amber-200 rounded-lg p-4">
                <p className="text-sm text-amber-900">
                  <strong>Important:</strong> Each user needs their own Vendor UID and API Token from BizChat.
                </p>
                <p className="text-xs text-amber-800 mt-2">
                  These credentials are unique to your BizChat account and required for sending messages.
                </p>
              </div>

              <Button type="submit" disabled={saving} data-testid="save-token-button">
                {saving ? 'Saving...' : 'Save API Token'}
              </Button>
            </form>
          </CardContent>
        </Card>

        {/* Change Password */}
        <Card className="shadow-lg border-0">
          <CardHeader>
            <div className="flex items-center space-x-3">
              <div className="flex items-center justify-center w-10 h-10 rounded-lg bg-amber-100">
                <Key className="h-5 w-5 text-amber-600" />
              </div>
              <div>
                <CardTitle>Change Password</CardTitle>
                <CardDescription>Update your account password</CardDescription>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleChangePassword} className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="currentPassword">Current Password</Label>
                <Input
                  id="currentPassword"
                  type="password"
                  placeholder="Enter current password"
                  value={currentPassword}
                  onChange={(e) => setCurrentPassword(e.target.value)}
                  required
                  data-testid="current-password-input"
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="newPassword">New Password</Label>
                <Input
                  id="newPassword"
                  type="password"
                  placeholder="Enter new password (min 6 characters)"
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  required
                  minLength={6}
                  data-testid="new-password-input"
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="confirmPassword">Confirm New Password</Label>
                <Input
                  id="confirmPassword"
                  type="password"
                  placeholder="Re-enter new password"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  required
                  minLength={6}
                  data-testid="confirm-password-input"
                />
              </div>

              <Button type="submit" disabled={changingPassword} data-testid="change-password-button">
                {changingPassword ? 'Changing...' : 'Change Password'}
              </Button>
            </form>
          </CardContent>
        </Card>

        {/* Account Info */}
        <Card className="shadow-lg border-0 bg-slate-50">
          <CardHeader>
            <CardTitle>Account Information</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            <div className="flex justify-between py-2 border-b border-slate-200">
              <span className="text-slate-600">Account Type</span>
              <span className="font-medium text-slate-900 capitalize">{user.role}</span>
            </div>
            <div className="flex justify-between py-2">
              <span className="text-slate-600">User ID</span>
              <span className="font-mono text-sm text-slate-900">{user.id}</span>
            </div>
          </CardContent>
        </Card>
      </div>
    </Layout>
  );
};

export default Settings;