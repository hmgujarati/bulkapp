import React, { useState, useEffect, useCallback } from 'react';
import Layout from '../components/Layout';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { ArrowLeft, CheckCircle, XCircle, Clock, Download, Pause, Play, X as CancelIcon, RefreshCw, CheckCheck, Eye, MousePointerClick } from 'lucide-react';
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
  const [clickFilter, setClickFilter] = useState('all'); // 'all' | 'clicked' | 'not_clicked' | <button text>

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

    const headers = ['Phone', 'Name', 'Status', 'Message ID', 'Error', 'Sent At', 'Delivered At', 'Read At', 'Clicked Button', 'Clicked At'];
    const rows = filteredRecipients.map(r => [
      r.phone,
      r.name,
      r.status,
      r.messageId || '',
      r.error || '',
      r.sentAt ? format(new Date(r.sentAt), 'yyyy-MM-dd HH:mm:ss') : '',
      r.deliveredAt ? format(new Date(r.deliveredAt), 'yyyy-MM-dd HH:mm:ss') : '',
      r.readAt ? format(new Date(r.readAt), 'yyyy-MM-dd HH:mm:ss') : '',
      r.clickedButton || '',
      r.clickedAt ? format(new Date(r.clickedAt), 'yyyy-MM-dd HH:mm:ss') : ''
    ]);

    const csv = [headers, ...rows].map(row => row.map(cell => `"${String(cell).replace(/"/g, '""')}"`).join(',')).join('\n');
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    const filterSuffix = clickFilter !== 'all' ? `-${clickFilter.replace(/\s+/g, '_')}` : '';
    a.download = `campaign-${campaign.name}${filterSuffix}-${Date.now()}.csv`;
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
      delivered: 'text-blue-600 bg-blue-50',
      read: 'text-violet-600 bg-violet-50',
      failed: 'text-red-600 bg-red-50',
      pending: 'text-amber-600 bg-amber-50',
    };
    return colors[status] || 'text-slate-600 bg-slate-50';
  };

  // Click breakdown: aggregate clicked buttons across recipients
  const clickedRecipients = (campaign.recipients || []).filter(r => r.clickedButton);
  const clickedCount = clickedRecipients.length;
  const clickBreakdown = Object.entries(
    clickedRecipients.reduce((acc, r) => {
      acc[r.clickedButton] = (acc[r.clickedButton] || 0) + 1;
      return acc;
    }, {})
  )
    .map(([text, count]) => ({ text, count }))
    .sort((a, b) => b.count - a.count);

  // Filtered recipients based on click filter
  const filteredRecipients = (campaign.recipients || []).filter(r => {
    if (clickFilter === 'all') return true;
    if (clickFilter === 'clicked') return !!r.clickedButton;
    if (clickFilter === 'not_clicked') return !r.clickedButton;
    return r.clickedButton === clickFilter;
  });

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
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-6">
          <Card className="shadow-lg border-0 bg-gradient-to-br from-slate-50 to-slate-100">
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium text-slate-700">Total</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold text-slate-900">{campaign.totalCount}</div>
            </CardContent>
          </Card>

          <Card className="shadow-lg border-0 bg-gradient-to-br from-green-50 to-green-100">
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium text-green-900 flex items-center gap-1">
                <CheckCircle className="h-4 w-4" /> Sent
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold text-green-900">{campaign.sentCount}</div>
              <p className="text-sm text-green-700 mt-1">
                {((campaign.sentCount / campaign.totalCount) * 100).toFixed(1)}%
              </p>
            </CardContent>
          </Card>

          <Card className="shadow-lg border-0 bg-gradient-to-br from-blue-50 to-blue-100" data-testid="delivered-card">
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium text-blue-900 flex items-center gap-1">
                <CheckCheck className="h-4 w-4" /> Delivered
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold text-blue-900">{campaign.deliveredCount || 0}</div>
              <p className="text-sm text-blue-700 mt-1">
                {campaign.sentCount > 0 ? `${(((campaign.deliveredCount || 0) / campaign.sentCount) * 100).toFixed(0)}% of sent` : '—'}
              </p>
            </CardContent>
          </Card>

          <Card className="shadow-lg border-0 bg-gradient-to-br from-violet-50 to-violet-100" data-testid="read-card">
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium text-violet-900 flex items-center gap-1">
                <Eye className="h-4 w-4" /> Read
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold text-violet-900">{campaign.readCount || 0}</div>
              <p className="text-sm text-violet-700 mt-1">
                {campaign.sentCount > 0 ? `${(((campaign.readCount || 0) / campaign.sentCount) * 100).toFixed(0)}% of sent` : '—'}
              </p>
            </CardContent>
          </Card>

          <Card className="shadow-lg border-0 bg-gradient-to-br from-red-50 to-red-100">
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium text-red-900 flex items-center gap-1">
                <XCircle className="h-4 w-4" /> Failed
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold text-red-900">{campaign.failedCount}</div>
              <p className="text-sm text-red-700 mt-1">
                {((campaign.failedCount / campaign.totalCount) * 100).toFixed(1)}%
              </p>
            </CardContent>
          </Card>

          <Card className="shadow-lg border-0 bg-gradient-to-br from-amber-50 to-amber-100">
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium text-amber-900 flex items-center gap-1">
                <Clock className="h-4 w-4" /> Pending
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold text-amber-900">{campaign.pendingCount}</div>
              <p className="text-sm text-amber-700 mt-1">Awaiting</p>
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
            <div className="flex items-center justify-between flex-wrap gap-3">
              <div>
                <CardTitle>Recipients</CardTitle>
                <CardDescription>Detailed status for each recipient</CardDescription>
              </div>
              <div className="flex items-center gap-2">
                <Select value={clickFilter} onValueChange={setClickFilter}>
                  <SelectTrigger className="w-56" data-testid="click-filter-select">
                    <SelectValue placeholder="Filter by button click" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All ({campaign.recipients.length})</SelectItem>
                    <SelectItem value="clicked">Clicked any button ({clickedCount})</SelectItem>
                    <SelectItem value="not_clicked">Did NOT click ({campaign.recipients.length - clickedCount})</SelectItem>
                    {clickBreakdown.map(b => (
                      <SelectItem key={b.text} value={b.text}>{b.text} ({b.count})</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>
            {clickBreakdown.length > 0 && (
              <div className="mt-4 flex flex-wrap gap-2" data-testid="click-summary">
                {clickBreakdown.map(b => (
                  <Badge 
                    key={b.text} 
                    variant="secondary" 
                    className="bg-emerald-50 text-emerald-700 border border-emerald-200 px-3 py-1"
                  >
                    <MousePointerClick className="h-3 w-3 mr-1" />
                    {b.text}: <span className="font-bold ml-1">{b.count}</span>
                  </Badge>
                ))}
                <Badge variant="outline" className="px-3 py-1">
                  No click: <span className="font-bold ml-1">{campaign.recipients.length - clickedCount}</span>
                </Badge>
              </div>
            )}
          </CardHeader>
          <CardContent>
            <div className="overflow-x-auto">
              <table className="w-full" data-testid="recipients-table">
                <thead>
                  <tr className="border-b border-slate-200">
                    <th className="text-left py-3 px-4 text-sm font-medium text-slate-700">Phone</th>
                    <th className="text-left py-3 px-4 text-sm font-medium text-slate-700">Name</th>
                    <th className="text-left py-3 px-4 text-sm font-medium text-slate-700">Status</th>
                    <th className="text-left py-3 px-4 text-sm font-medium text-slate-700">Clicked</th>
                    <th className="text-left py-3 px-4 text-sm font-medium text-slate-700">Message ID</th>
                    <th className="text-left py-3 px-4 text-sm font-medium text-slate-700">Sent At</th>
                    <th className="text-left py-3 px-4 text-sm font-medium text-slate-700">Error</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredRecipients.map((recipient, index) => (
                    <tr key={index} className="border-b border-slate-100 hover:bg-slate-50">
                      <td className="py-3 px-4 text-sm font-mono text-slate-900">{recipient.phone}</td>
                      <td className="py-3 px-4 text-sm text-slate-900">{recipient.name || '-'}</td>
                      <td className="py-3 px-4 text-sm">
                        <div className={`inline-flex items-center space-x-1 px-2 py-1 rounded-lg ${getStatusColor(recipient.status)}`}>
                          {recipient.status === 'sent' && <CheckCircle className="h-3 w-3" />}
                          {recipient.status === 'delivered' && <CheckCheck className="h-3 w-3" />}
                          {recipient.status === 'read' && <Eye className="h-3 w-3" />}
                          {recipient.status === 'failed' && <XCircle className="h-3 w-3" />}
                          {recipient.status === 'pending' && <Clock className="h-3 w-3" />}
                          <span className="font-medium">{recipient.status}</span>
                        </div>
                      </td>
                      <td className="py-3 px-4 text-sm">
                        {recipient.clickedButton ? (
                          <div 
                            className="inline-flex items-center space-x-1 px-2 py-1 rounded-lg bg-emerald-50 text-emerald-700"
                            title={recipient.clickedAt ? `Clicked at ${format(new Date(recipient.clickedAt), 'MMM d, HH:mm')}` : ''}
                          >
                            <MousePointerClick className="h-3 w-3" />
                            <span className="font-medium">{recipient.clickedButton}</span>
                          </div>
                        ) : (
                          <span className="text-slate-400">—</span>
                        )}
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