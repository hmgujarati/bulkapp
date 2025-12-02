import React, { useState, useEffect } from 'react';
import Layout from '../components/Layout';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { MessageSquare, Send, CheckCircle, XCircle, Clock } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import api from '../utils/api';
import { toast } from 'sonner';

const UserDashboard = ({ user, onLogout }) => {
  const navigate = useNavigate();
  const [campaigns, setCampaigns] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchRecentCampaigns();
  }, []);

  const fetchRecentCampaigns = async () => {
    try {
      const response = await api.get('/campaigns');
      setCampaigns(response.data.campaigns.slice(0, 5));
    } catch (error) {
      toast.error('Failed to fetch campaigns');
    } finally {
      setLoading(false);
    }
  };

  const stats = {
    totalCampaigns: campaigns.length,
    totalSent: campaigns.reduce((sum, c) => sum + c.sentCount, 0),
    totalFailed: campaigns.reduce((sum, c) => sum + c.failedCount, 0),
  };

  return (
    <Layout user={user} onLogout={onLogout}>
      <div className="space-y-6">
        {/* Welcome Section */}
        <div>
          <h1 className="text-3xl sm:text-4xl font-bold text-slate-900">
            Welcome back, {user.firstName}!
          </h1>
          <p className="text-slate-600 mt-1">Manage your WhatsApp campaigns from here</p>
        </div>

        {/* Quick Actions */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <Card
            className="shadow-lg border-0 bg-gradient-to-br from-blue-600 to-indigo-700 text-white cursor-pointer hover:shadow-xl transition-shadow"
            onClick={() => navigate('/send')}
            data-testid="quick-action-send"
          >
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-blue-100 text-sm font-medium">Quick Action</p>
                  <h3 className="text-2xl font-bold mt-1">Send Messages</h3>
                  <p className="text-blue-100 text-sm mt-2">Create a new campaign</p>
                </div>
                <Send className="h-12 w-12 opacity-80" />
              </div>
            </CardContent>
          </Card>

          <Card
            className="shadow-lg border-0 bg-gradient-to-br from-emerald-600 to-teal-700 text-white cursor-pointer hover:shadow-xl transition-shadow"
            onClick={() => navigate('/templates')}
            data-testid="quick-action-templates"
          >
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-emerald-100 text-sm font-medium">Explore</p>
                  <h3 className="text-2xl font-bold mt-1">View Templates</h3>
                  <p className="text-emerald-100 text-sm mt-2">See approved templates</p>
                </div>
                <MessageSquare className="h-12 w-12 opacity-80" />
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Stats Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <Card className="shadow-lg border-0 bg-gradient-to-br from-purple-50 to-purple-100">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium text-purple-900">Total Campaigns</CardTitle>
              <MessageSquare className="h-5 w-5 text-purple-600" />
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold text-purple-900">{stats.totalCampaigns}</div>
            </CardContent>
          </Card>

          <Card className="shadow-lg border-0 bg-gradient-to-br from-green-50 to-green-100">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium text-green-900">Messages Sent</CardTitle>
              <CheckCircle className="h-5 w-5 text-green-600" />
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold text-green-900">{stats.totalSent}</div>
            </CardContent>
          </Card>

          <Card className="shadow-lg border-0 bg-gradient-to-br from-red-50 to-red-100">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium text-red-900">Failed Messages</CardTitle>
              <XCircle className="h-5 w-5 text-red-600" />
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold text-red-900">{stats.totalFailed}</div>
            </CardContent>
          </Card>
        </div>

        {/* Recent Campaigns */}
        <Card className="shadow-lg border-0">
          <CardHeader>
            <div className="flex justify-between items-center">
              <div>
                <CardTitle>Recent Campaigns</CardTitle>
                <CardDescription>Your latest WhatsApp campaigns</CardDescription>
              </div>
              <Button variant="outline" onClick={() => navigate('/campaigns')} data-testid="view-all-campaigns">
                View All
              </Button>
            </div>
          </CardHeader>
          <CardContent>
            {loading ? (
              <div className="text-center py-8 text-slate-500">Loading campaigns...</div>
            ) : campaigns.length === 0 ? (
              <div className="text-center py-12">
                <MessageSquare className="h-12 w-12 text-slate-300 mx-auto mb-4" />
                <p className="text-slate-500 mb-4">No campaigns yet</p>
                <Button onClick={() => navigate('/send')} data-testid="create-first-campaign">
                  Create Your First Campaign
                </Button>
              </div>
            ) : (
              <div className="space-y-3">
                {campaigns.map((campaign) => (
                  <div
                    key={campaign.id}
                    className="flex items-center justify-between p-4 border border-slate-200 rounded-lg hover:bg-slate-50 cursor-pointer"
                    onClick={() => navigate(`/campaigns/${campaign.id}`)}
                    data-testid={`campaign-${campaign.id}`}
                  >
                    <div className="flex-1">
                      <h4 className="font-medium text-slate-900">{campaign.name}</h4>
                      <p className="text-sm text-slate-500 mt-1">
                        Template: {campaign.templateName}
                      </p>
                    </div>
                    <div className="flex items-center space-x-4 text-sm">
                      <div className="text-center">
                        <div className="flex items-center space-x-1 text-green-600">
                          <CheckCircle className="h-4 w-4" />
                          <span className="font-medium">{campaign.sentCount}</span>
                        </div>
                        <p className="text-xs text-slate-500">Sent</p>
                      </div>
                      <div className="text-center">
                        <div className="flex items-center space-x-1 text-red-600">
                          <XCircle className="h-4 w-4" />
                          <span className="font-medium">{campaign.failedCount}</span>
                        </div>
                        <p className="text-xs text-slate-500">Failed</p>
                      </div>
                      <div className="text-center">
                        <div className="flex items-center space-x-1 text-amber-600">
                          <Clock className="h-4 w-4" />
                          <span className="font-medium">{campaign.pendingCount}</span>
                        </div>
                        <p className="text-xs text-slate-500">Pending</p>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </Layout>
  );
};

export default UserDashboard;