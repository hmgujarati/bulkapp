import React, { useState, useEffect } from 'react';
import Layout from '../components/Layout';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { History, CheckCircle, XCircle, Clock, Eye, Trash2 } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { toast } from 'sonner';
import api from '../utils/api';
import { format } from 'date-fns';

const CampaignHistory = ({ user, onLogout }) => {
  const navigate = useNavigate();
  const [campaigns, setCampaigns] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchCampaigns();
  }, []);

  const fetchCampaigns = async () => {
    try {
      const response = await api.get('/campaigns');
      setCampaigns(response.data.campaigns);
    } catch (error) {
      toast.error('Failed to fetch campaigns');
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (campaignId) => {
    if (!window.confirm('Are you sure you want to delete this campaign? This will not affect your daily message count.')) {
      return;
    }
    
    try {
      await api.delete(`/campaigns/${campaignId}`);
      toast.success('Campaign deleted successfully');
      fetchCampaigns();
    } catch (error) {
      toast.error('Failed to delete campaign');
    }
  };

  const getStatusBadge = (status) => {
    const badges = {
      completed: <Badge variant="success">Completed</Badge>,
      processing: <Badge variant="default">Processing</Badge>,
      pending: <Badge variant="secondary">Pending</Badge>,
      scheduled: <Badge variant="outline">Scheduled</Badge>,
    };
    return badges[status] || <Badge>{status}</Badge>;
  };

  return (
    <Layout user={user} onLogout={onLogout}>
      <div className="space-y-6">
        <div>
          <h1 className="text-3xl sm:text-4xl font-bold text-slate-900">Campaign History</h1>
          <p className="text-slate-600 mt-1">View all your WhatsApp campaigns</p>
        </div>

        {loading ? (
          <Card className="shadow-lg border-0">
            <CardContent className="py-12">
              <div className="text-center text-slate-500">Loading campaigns...</div>
            </CardContent>
          </Card>
        ) : campaigns.length === 0 ? (
          <Card className="shadow-lg border-0">
            <CardContent className="py-12">
              <div className="text-center">
                <History className="h-16 w-16 text-slate-300 mx-auto mb-4" />
                <h3 className="text-lg font-medium text-slate-900 mb-2">No Campaigns Yet</h3>
                <p className="text-slate-600 mb-6">
                  You haven't created any campaigns yet. Start by sending your first bulk message!
                </p>
                <Button onClick={() => navigate('/send')} data-testid="create-campaign-button">
                  Create Campaign
                </Button>
              </div>
            </CardContent>
          </Card>
        ) : (
          <div className="grid grid-cols-1 gap-4">
            {campaigns.map((campaign) => (
              <Card key={campaign.id} className="shadow-lg border-0 hover:shadow-xl transition-shadow" data-testid={`campaign-card-${campaign.id}`}>
                <CardHeader>
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center space-x-3">
                        <CardTitle className="text-xl">{campaign.name}</CardTitle>
                        {getStatusBadge(campaign.status)}
                      </div>
                      <CardDescription className="mt-2">
                        Template: {campaign.templateName} • Created:{' '}
                        {campaign.createdAt ? format(new Date(campaign.createdAt), 'MMM d, yyyy HH:mm') : 'N/A'}
                      </CardDescription>
                    </div>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => navigate(`/campaigns/${campaign.id}`)}
                      data-testid={`view-campaign-${campaign.id}`}
                    >
                      <Eye className="h-4 w-4 mr-2" />
                      View Details
                    </Button>
                  </div>
                </CardHeader>
                <CardContent>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    <div className="bg-slate-50 rounded-lg p-4">
                      <div className="flex items-center space-x-2 text-slate-600 mb-1">
                        <Clock className="h-4 w-4" />
                        <span className="text-sm font-medium">Total</span>
                      </div>
                      <p className="text-2xl font-bold text-slate-900">{campaign.totalCount}</p>
                    </div>

                    <div className="bg-green-50 rounded-lg p-4">
                      <div className="flex items-center space-x-2 text-green-600 mb-1">
                        <CheckCircle className="h-4 w-4" />
                        <span className="text-sm font-medium">Sent</span>
                      </div>
                      <p className="text-2xl font-bold text-green-900">{campaign.sentCount}</p>
                    </div>

                    <div className="bg-red-50 rounded-lg p-4">
                      <div className="flex items-center space-x-2 text-red-600 mb-1">
                        <XCircle className="h-4 w-4" />
                        <span className="text-sm font-medium">Failed</span>
                      </div>
                      <p className="text-2xl font-bold text-red-900">{campaign.failedCount}</p>
                    </div>

                    <div className="bg-amber-50 rounded-lg p-4">
                      <div className="flex items-center space-x-2 text-amber-600 mb-1">
                        <Clock className="h-4 w-4" />
                        <span className="text-sm font-medium">Pending</span>
                      </div>
                      <p className="text-2xl font-bold text-amber-900">{campaign.pendingCount}</p>
                    </div>
                  </div>

                  {campaign.scheduledAt && (
                    <div className="mt-4 p-3 bg-blue-50 border border-blue-200 rounded-lg">
                      <p className="text-sm text-blue-900">
                        <strong>Scheduled for:</strong> {format(new Date(campaign.scheduledAt), 'MMM d, yyyy HH:mm')}
                      </p>
                    </div>
                  )}
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </div>
    </Layout>
  );
};

export default CampaignHistory;