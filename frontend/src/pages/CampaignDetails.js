import React, { useState, useEffect, useCallback } from 'react';
import Layout from '../components/Layout';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { ArrowLeft, CheckCircle, XCircle, Clock, Download, Pause, Play, X as CancelIcon, RefreshCw } from 'lucide-react';
import { useNavigate, useParams } from 'react-router-dom';
import { toast } from 'sonner';
import api from '../utils/api';
import { format } from 'date-fns';

const CampaignDetails = ({ user, onLogout }) => {
  const navigate = useNavigate();
  const { id } = useParams();
  const [campaign, setCampaign] = useState(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const fetchCampaign = useCallback(async (silent = false) => {
    if (!silent) setLoading(true);
    try {
      const response = await api.get(`/campaigns/${id}`);
      setCampaign(response.data);
    } catch (error) {
      if (!silent) {
        toast.error('Failed to fetch campaign details');
        navigate('/campaigns');
      }
    } finally {
      if (!silent) setLoading(false);
      setRefreshing(false);
    }
  }, [id, navigate]);

  useEffect(() => {
    fetchCampaign();
  }, [fetchCampaign]);

  useEffect(() => {
    // Auto-refresh for processing campaigns
    if (campaign && campaign.status === 'processing') {
      const interval = setInterval(() => {
        fetchCampaign(true);
      }, 3000); // Refresh every 3 seconds
      
      return () => clearInterval(interval);
    }
  }, [campaign?.status, fetchCampaign]);

  const handlePause = async () => {
    try {
      await api.post(`/campaigns/${id}/pause`);
      toast.success('Campaign paused');
      fetchCampaign(true);
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to pause campaign');
    }
  };

  const handleResume = async () => {
    try {
      await api.post(`/campaigns/${id}/resume`);
      toast.success('Campaign resumed');
      fetchCampaign(true);
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to resume campaign');
    }
  };

  const handleCancel = async () => {
    if (!window.confirm('Are you sure you want to cancel this campaign?')) return;
    
    try {
      await api.post(`/campaigns/${id}/cancel`);
      toast.success('Campaign cancelled');
      fetchCampaign(true);
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to cancel campaign');
    }
  };

  const handleRefresh = () => {
    setRefreshing(true);
    fetchCampaign(true);
  };

  const downloadCSV = () => {
    if (!campaign) return;

    const headers = ['Phone', 'Name', 'Status', 'Message ID', 'Error', 'Sent At'];
    const rows = campaign.recipients.map(r => [
      r.phone,
      r.name,
      r.status,
      r.messageId || '',
      r.error || '',
      r.sentAt ? format(new Date(r.sentAt), 'yyyy-MM-dd HH:mm:ss') : ''
    ]);

    const csv = [headers, ...rows].map(row => row.map(cell => `"${cell}"`).join(',')).join('\n');
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `campaign-${campaign.name}-${Date.now()}.csv`;
    a.click();
    window.URL.revokeObjectURL(url);
  };

  if (loading) {
    return (
      <Layout user={user} onLogout={onLogout}>
        <div className="text-center py-12 text-slate-500">Loading campaign details...</div>
      </Layout>
    );
  }

  if (!campaign) {
    return (
      <Layout user={user} onLogout={onLogout}>
        <div className="text-center py-12 text-slate-500">Campaign not found</div>
      </Layout>
    );
  }

  const getStatusColor = (status) => {
    const colors = {
      sent: 'text-green-600 bg-green-50',
      failed: 'text-red-600 bg-red-50',
      pending: 'text-amber-600 bg-amber-50',
    };
    return colors[status] || 'text-slate-600 bg-slate-50';
  };

  return (
    <Layout user={user} onLogout={onLogout}>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between flex-wrap gap-4">
          <div className="flex items-center space-x-4">
            <Button variant="ghost" onClick={() => navigate('/campaigns')} data-testid="back-button">
              <ArrowLeft className="h-5 w-5" />
            </Button>
            <div>
              <h1 className="text-3xl sm:text-4xl font-bold text-slate-900">{campaign.name}</h1>
              <p className="text-slate-600 mt-1">Campaign Details</p>
            </div>
          </div>
          
          <div className="flex items-center space-x-2">
            <Button 
              variant="outline" 
              size="sm" 
              onClick={handleRefresh}
              disabled={refreshing}
              data-testid="refresh-button"
            >
              <RefreshCw className={`h-4 w-4 mr-2 ${refreshing ? 'animate-spin' : ''}`} />
              Refresh
            </Button>
            
            {campaign.status === 'processing' && (
              <Button 
                variant="outline" 
                size="sm" 
                onClick={handlePause}
                data-testid="pause-button"
              >
                <Pause className="h-4 w-4 mr-2" />
                Pause
              </Button>
            )}
            
            {campaign.status === 'paused' && (
              <Button 
                variant="outline" 
                size="sm" 
                onClick={handleResume}
                className="border-green-500 text-green-600 hover:bg-green-50"
                data-testid="resume-button"
              >
                <Play className="h-4 w-4 mr-2" />
                Resume
              </Button>
            )}
            
            {['processing', 'paused', 'pending'].includes(campaign.status) && (
              <Button 
                variant="outline" 
                size="sm" 
                onClick={handleCancel}
                className="border-red-500 text-red-600 hover:bg-red-50"
                data-testid="cancel-button"
              >
                <CancelIcon className="h-4 w-4 mr-2" />
                Cancel
              </Button>
            )}
            
            <Button variant="outline" size="sm" onClick={downloadCSV} data-testid="download-csv-button">
              <Download className="h-4 w-4 mr-2" />
              Export CSV
            </Button>
          </div>
        </div>

        {/* Real-time Progress */}
        {campaign.status === 'processing' && (
          <Alert className="bg-blue-50 border-blue-200">
            <AlertDescription>
              <div className="space-y-2">
                <div className="flex justify-between text-sm font-medium">
                  <span>Campaign in progress...</span>
                  <span>{campaign.sentCount + campaign.failedCount}/{campaign.totalCount}</span>
                </div>
                <Progress 
                  value={((campaign.sentCount + campaign.failedCount) / campaign.totalCount) * 100} 
                  className="h-2"
                />
                <p className="text-xs text-slate-600">
                  Sending at 29 messages/second • Est. remaining: ~{Math.ceil(campaign.pendingCount / 29)}s
                </p>
              </div>
            </AlertDescription>
          </Alert>
        )}

        {campaign.status === 'paused' && (
          <Alert className="bg-amber-50 border-amber-200">
            <AlertDescription className="text-amber-900">
              Campaign is paused. Click "Resume" to continue sending messages.
            </AlertDescription>
          </Alert>
        )}

        {/* Summary Cards */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
          <Card className="shadow-lg border-0 bg-gradient-to-br from-slate-50 to-slate-100">
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium text-slate-700">Total Recipients</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold text-slate-900">{campaign.totalCount}</div>
            </CardContent>
          </Card>

          <Card className="shadow-lg border-0 bg-gradient-to-br from-green-50 to-green-100">
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium text-green-900">Successfully Sent</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold text-green-900">{campaign.sentCount}</div>
              <p className="text-sm text-green-700 mt-1">
                {((campaign.sentCount / campaign.totalCount) * 100).toFixed(1)}% success rate
              </p>
            </CardContent>
          </Card>

          <Card className="shadow-lg border-0 bg-gradient-to-br from-red-50 to-red-100">
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium text-red-900">Failed</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold text-red-900">{campaign.failedCount}</div>
              <p className="text-sm text-red-700 mt-1">
                {((campaign.failedCount / campaign.totalCount) * 100).toFixed(1)}% failed
              </p>
            </CardContent>
          </Card>

          <Card className="shadow-lg border-0 bg-gradient-to-br from-amber-50 to-amber-100">
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium text-amber-900">Pending</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold text-amber-900">{campaign.pendingCount}</div>
              <p className="text-sm text-amber-700 mt-1">Awaiting processing</p>
            </CardContent>
          </Card>
        </div>

        {/* Campaign Info */}
        <Card className="shadow-lg border-0">
          <CardHeader>
            <CardTitle>Campaign Information</CardTitle>
          </CardHeader>
          <CardContent className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <p className="text-sm text-slate-600 mb-1">Template</p>
              <p className="font-medium text-slate-900">{campaign.templateName}</p>
            </div>
            <div>
              <p className="text-sm text-slate-600 mb-1">Status</p>
              <Badge variant={campaign.status === 'completed' ? 'success' : 'default'}>
                {campaign.status}
              </Badge>
            </div>
            <div>
              <p className="text-sm text-slate-600 mb-1">Created At</p>
              <p className="font-medium text-slate-900">
                {campaign.createdAt ? format(new Date(campaign.createdAt), 'MMM d, yyyy HH:mm') : 'N/A'}
              </p>
            </div>
            {campaign.completedAt && (
              <div>
                <p className="text-sm text-slate-600 mb-1">Completed At</p>
                <p className="font-medium text-slate-900">
                  {format(new Date(campaign.completedAt), 'MMM d, yyyy HH:mm')}
                </p>
              </div>
            )}
            {campaign.scheduledAt && (
              <div>
                <p className="text-sm text-slate-600 mb-1">Scheduled For</p>
                <p className="font-medium text-slate-900">
                  {format(new Date(campaign.scheduledAt), 'MMM d, yyyy HH:mm')}
                </p>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Recipients List */}
        <Card className="shadow-lg border-0">
          <CardHeader>
            <CardTitle>Recipients</CardTitle>
            <CardDescription>Detailed status for each recipient</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="overflow-x-auto">
              <table className="w-full" data-testid="recipients-table">
                <thead>
                  <tr className="border-b border-slate-200">
                    <th className="text-left py-3 px-4 text-sm font-medium text-slate-700">Phone</th>
                    <th className="text-left py-3 px-4 text-sm font-medium text-slate-700">Name</th>
                    <th className="text-left py-3 px-4 text-sm font-medium text-slate-700">Status</th>
                    <th className="text-left py-3 px-4 text-sm font-medium text-slate-700">Message ID</th>
                    <th className="text-left py-3 px-4 text-sm font-medium text-slate-700">Sent At</th>
                    <th className="text-left py-3 px-4 text-sm font-medium text-slate-700">Error</th>
                  </tr>
                </thead>
                <tbody>
                  {campaign.recipients.map((recipient, index) => (
                    <tr key={index} className="border-b border-slate-100 hover:bg-slate-50">
                      <td className="py-3 px-4 text-sm font-mono text-slate-900">{recipient.phone}</td>
                      <td className="py-3 px-4 text-sm text-slate-900">{recipient.name || '-'}</td>
                      <td className="py-3 px-4 text-sm">
                        <div className={`inline-flex items-center space-x-1 px-2 py-1 rounded-lg ${getStatusColor(recipient.status)}`}>
                          {recipient.status === 'sent' && <CheckCircle className="h-3 w-3" />}
                          {recipient.status === 'failed' && <XCircle className="h-3 w-3" />}
                          {recipient.status === 'pending' && <Clock className="h-3 w-3" />}
                          <span className="font-medium">{recipient.status}</span>
                        </div>
                      </td>
                      <td className="py-3 px-4 text-sm text-slate-600 font-mono">
                        {recipient.messageId ? recipient.messageId.slice(0, 20) + '...' : '-'}
                      </td>
                      <td className="py-3 px-4 text-sm text-slate-600">
                        {recipient.sentAt ? format(new Date(recipient.sentAt), 'MMM d, HH:mm') : '-'}
                      </td>
                      <td className="py-3 px-4 text-sm text-red-600">
                        {recipient.error ? recipient.error.slice(0, 50) : '-'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      </div>
    </Layout>
  );
};

export default CampaignDetails;