'use client';

import { useState, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  GitPullRequest,
  CheckCircle2,
  XCircle,
  AlertCircle,
  Clock,
  RefreshCcw,
  Play,
  FileCode,
  MessageSquare,
  ExternalLink,
  Loader2,
  Shield,
  TestTube2,
  History,
  X,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { api, PRSummary, DashboardSummary, ReviewResponse, QualityCheckResponse, SecurityScanResponse } from '@/lib/api';
import { PRLifecycleTimeline, getDemoLifecycle, type PRLifecycleData, type LifecycleEvent } from './pr-lifecycle-timeline';

// Status badge component
function StatusBadge({ 
  status, 
  type 
}: { 
  status: string; 
  type: 'review' | 'quality' | 'ci' | 'security' 
}) {
  const getConfig = () => {
    if (type === 'review') {
      switch (status) {
        case 'pending': return { icon: Clock, variant: 'outline' as const, label: 'Pending Review' };
        case 'in_progress': return { icon: Loader2, variant: 'secondary' as const, label: 'Reviewing...' };
        case 'reviewed': return { icon: MessageSquare, variant: 'secondary' as const, label: 'Reviewed' };
        case 'approved': return { icon: CheckCircle2, variant: 'default' as const, label: 'Approved' };
        case 'changes_requested': return { icon: AlertCircle, variant: 'destructive' as const, label: 'Changes Requested' };
        default: return { icon: Clock, variant: 'outline' as const, label: 'Unknown' };
      }
    } else if (type === 'quality') {
      switch (status) {
        case 'passing': return { icon: CheckCircle2, variant: 'default' as const, label: 'Passing' };
        case 'warning': return { icon: AlertCircle, variant: 'secondary' as const, label: 'Warning' };
        case 'failing': return { icon: XCircle, variant: 'destructive' as const, label: 'Failing' };
        default: return { icon: Clock, variant: 'outline' as const, label: 'Not Checked' };
      }
    } else if (type === 'security') {
      switch (status) {
        case 'secure': return { icon: Shield, variant: 'default' as const, label: 'Secure' };
        case 'warning': return { icon: AlertCircle, variant: 'secondary' as const, label: 'Warnings' };
        case 'vulnerable': return { icon: XCircle, variant: 'destructive' as const, label: 'Vulnerable' };
        case 'scanning': return { icon: Loader2, variant: 'secondary' as const, label: 'Scanning...' };
        default: return { icon: Clock, variant: 'outline' as const, label: 'Not Scanned' };
      }
    } else {
      switch (status) {
        case 'pending': return { icon: Clock, variant: 'outline' as const, label: 'Pending' };
        case 'running': return { icon: Loader2, variant: 'secondary' as const, label: 'Running' };
        case 'success': return { icon: CheckCircle2, variant: 'default' as const, label: 'Success' };
        case 'failure': return { icon: XCircle, variant: 'destructive' as const, label: 'Failure' };
        default: return { icon: Clock, variant: 'outline' as const, label: 'Unknown' };
      }
    }
  };

  const config = getConfig();
  const Icon = config.icon;

  return (
    <Badge variant={config.variant} className="gap-1">
      <Icon className={cn("h-3 w-3", status === 'in_progress' || status === 'running' ? 'animate-spin' : '')} />
      {config.label}
    </Badge>
  );
}

// Stats card component
function StatsCard({
  title,
  value,
  icon: Icon,
  description,
  variant = 'default',
}: {
  title: string;
  value: number | string;
  icon: React.ComponentType<{ className?: string }>;
  description?: string;
  variant?: 'default' | 'success' | 'warning' | 'danger';
}) {
  const variants = {
    default: 'bg-muted/50',
    success: 'bg-green-500/10 border-green-500/20',
    warning: 'bg-yellow-500/10 border-yellow-500/20',
    danger: 'bg-red-500/10 border-red-500/20',
  };

  return (
    <Card className={cn('transition-colors', variants[variant])}>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-sm font-medium">{title}</CardTitle>
        <Icon className="h-4 w-4 text-muted-foreground" />
      </CardHeader>
      <CardContent>
        <div className="text-2xl font-bold">{value}</div>
        {description && (
          <p className="text-xs text-muted-foreground">{description}</p>
        )}
      </CardContent>
    </Card>
  );
}

// PR Row component with actions
function PRRow({
  pr,
  onTriggerReview,
  onRunQuality,
  onRunSecurity,
  onViewLifecycle,
  isReviewLoading,
  isQualityLoading,
  isSecurityLoading,
}: {
  pr: PRSummary;
  onTriggerReview: (prNumber: number) => void;
  onRunQuality: (prNumber: number) => void;
  onRunSecurity: (prNumber: number) => void;
  onViewLifecycle: (prNumber: number) => void;
  isReviewLoading: boolean;
  isQualityLoading: boolean;
  isSecurityLoading: boolean;
}) {
  return (
    <TableRow>
      <TableCell>
        <div className="flex items-center gap-2">
          <GitPullRequest className="h-4 w-4 text-green-500" />
          <div>
            <button
              onClick={() => onViewLifecycle(pr.number)}
              className="font-medium hover:underline text-left"
            >
              #{pr.number}
            </button>
            <p className="text-sm text-muted-foreground truncate max-w-[300px]">
              {pr.title}
            </p>
          </div>
        </div>
      </TableCell>
      <TableCell>
        <div className="text-sm">
          <span className="text-muted-foreground">{pr.branch}</span>
          <span className="mx-1">→</span>
          <span>{pr.base}</span>
        </div>
      </TableCell>
      <TableCell>
        <div className="flex items-center gap-1 text-sm">
          <span className="text-green-600">+{pr.additions}</span>
          <span className="text-muted-foreground">/</span>
          <span className="text-red-600">-{pr.deletions}</span>
          <span className="text-muted-foreground ml-1">({pr.files_changed} files)</span>
        </div>
      </TableCell>
      <TableCell>
        <StatusBadge status={pr.review_status} type="review" />
      </TableCell>
      <TableCell>
        <StatusBadge status={pr.quality_status} type="quality" />
      </TableCell>
      <TableCell>
        <StatusBadge status={pr.security_status || 'pending'} type="security" />
      </TableCell>
      <TableCell>
        <StatusBadge status={pr.ci_status} type="ci" />
      </TableCell>
      <TableCell>
        <div className="flex items-center gap-2">
          <TooltipProvider>
            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => onViewLifecycle(pr.number)}
                >
                  <History className="h-4 w-4" />
                </Button>
              </TooltipTrigger>
              <TooltipContent>View Lifecycle</TooltipContent>
            </Tooltip>
          </TooltipProvider>

          <TooltipProvider>
            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => onTriggerReview(pr.number)}
                  disabled={isReviewLoading}
                >
                  {isReviewLoading ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    <MessageSquare className="h-4 w-4" />
                  )}
                </Button>
              </TooltipTrigger>
              <TooltipContent>Trigger Code Review</TooltipContent>
            </Tooltip>
          </TooltipProvider>

          <TooltipProvider>
            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => onRunQuality(pr.number)}
                  disabled={isQualityLoading}
                >
                  {isQualityLoading ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    <TestTube2 className="h-4 w-4" />
                  )}
                </Button>
              </TooltipTrigger>
              <TooltipContent>Run Quality Check</TooltipContent>
            </Tooltip>
          </TooltipProvider>

          <TooltipProvider>
            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => onRunSecurity(pr.number)}
                  disabled={isSecurityLoading}
                >
                  {isSecurityLoading ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    <Shield className="h-4 w-4" />
                  )}
                </Button>
              </TooltipTrigger>
              <TooltipContent>Run Security Scan</TooltipContent>
            </Tooltip>
          </TooltipProvider>

          <TooltipProvider>
            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  variant="ghost"
                  size="sm"
                  asChild
                >
                  <a href={pr.html_url} target="_blank" rel="noopener noreferrer">
                    <ExternalLink className="h-4 w-4" />
                  </a>
                </Button>
              </TooltipTrigger>
              <TooltipContent>Open in GitHub</TooltipContent>
            </Tooltip>
          </TooltipProvider>
        </div>
      </TableCell>
    </TableRow>
  );
}

// Result toast/notification component
function ResultNotification({
  result,
  type,
  onDismiss,
}: {
  result: ReviewResponse | QualityCheckResponse | SecurityScanResponse;
  type: 'review' | 'quality' | 'security';
  onDismiss: () => void;
}) {
  const isReview = type === 'review';
  const isQuality = type === 'quality';
  const isSecurity = type === 'security';
  const reviewResult = result as ReviewResponse;
  const qualityResult = result as QualityCheckResponse;
  const securityResult = result as SecurityScanResponse;

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -20 }}
      className="fixed bottom-4 right-4 z-50 max-w-md"
    >
      <Card className="border-2 shadow-lg">
        <CardHeader className="pb-2">
          <CardTitle className="flex items-center gap-2 text-base">
            {result.success ? (
              <CheckCircle2 className="h-5 w-5 text-green-500" />
            ) : (
              <XCircle className="h-5 w-5 text-red-500" />
            )}
            {isReview ? 'Code Review Complete' : isQuality ? 'Quality Check Complete' : 'Security Scan Complete'}
          </CardTitle>
          <CardDescription>PR #{result.pr_number}</CardDescription>
        </CardHeader>
        <CardContent className="space-y-2">
          {isReview && (
            <>
              <p className="text-sm">
                Analyzed {reviewResult.files_analyzed} files, found{' '}
                <span className="font-medium">{reviewResult.findings_count} findings</span>
              </p>
              {reviewResult.review_submitted && (
                <Badge variant="secondary">Review posted to GitHub</Badge>
              )}
            </>
          )}
          {isQuality && (
            <>
              <p className="text-sm">
                Quality status: <StatusBadge status={qualityResult.quality_status} type="quality" />
              </p>
              {qualityResult.test_coverage && (
                <p className="text-sm">
                  Test coverage: {qualityResult.test_coverage.coverage_percentage}%
                </p>
              )}
              {qualityResult.posted_to_github && (
                <Badge variant="secondary">Comment posted to GitHub</Badge>
              )}
            </>
          )}
          {isSecurity && (
            <>
              <div className="flex items-center gap-2 text-sm">
                <Shield className={securityResult.passed ? 'h-4 w-4 text-green-500' : 'h-4 w-4 text-red-500'} />
                <span>Security Score: <span className="font-medium">{securityResult.security_score}</span>/100</span>
              </div>
              <div className="flex gap-2 text-sm flex-wrap">
                {securityResult.critical_count > 0 && (
                  <Badge variant="destructive">{securityResult.critical_count} Critical</Badge>
                )}
                {securityResult.high_count > 0 && (
                  <Badge variant="destructive">{securityResult.high_count} High</Badge>
                )}
                {securityResult.medium_count > 0 && (
                  <Badge variant="secondary">{securityResult.medium_count} Medium</Badge>
                )}
                {securityResult.low_count > 0 && (
                  <Badge variant="outline">{securityResult.low_count} Low</Badge>
                )}
              </div>
              {securityResult.blocking_issues.length > 0 && (
                <p className="text-sm text-red-600 font-medium">
                  ⚠️ {securityResult.blocking_issues.length} blocking issue(s) found
                </p>
              )}
              {securityResult.posted_to_github && (
                <Badge variant="secondary">Report posted to GitHub</Badge>
              )}
            </>
          )}
          <Button variant="ghost" size="sm" onClick={onDismiss} className="w-full mt-2">
            Dismiss
          </Button>
        </CardContent>
      </Card>
    </motion.div>
  );
}

// Main PR Dashboard component
export function PRDashboard() {
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [prs, setPrs] = useState<PRSummary[]>([]);
  const [dashboard, setDashboard] = useState<DashboardSummary | null>(null);
  const [activeTab, setActiveTab] = useState('all');
  const [loadingPRs, setLoadingPRs] = useState<Record<number, 'review' | 'quality' | 'security' | null>>({});
  const [notification, setNotification] = useState<{
    result: ReviewResponse | QualityCheckResponse | SecurityScanResponse;
    type: 'review' | 'quality' | 'security';
  } | null>(null);
  const [selectedLifecycle, setSelectedLifecycle] = useState<PRLifecycleData | null>(null);
  const [lifecycleDialogOpen, setLifecycleDialogOpen] = useState(false);

  const fetchData = useCallback(async () => {
    try {
      const [prList, dashboardData] = await Promise.all([
        api.prs.list('open'),
        api.prs.getDashboard(),
      ]);
      setPrs(prList.prs);
      setDashboard(dashboardData);
    } catch (error) {
      console.error('Failed to fetch PR data:', error);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const handleRefresh = () => {
    setRefreshing(true);
    fetchData();
  };

  const handleViewLifecycle = async (prNumber: number) => {
    const pr = prs.find(p => p.number === prNumber);
    if (pr) {
      try {
        // Fetch real lifecycle data from API
        const lifecycleData = await api.prs.getLifecycle(prNumber);
        
        // Convert API response to component format
        const lifecycle: PRLifecycleData = {
          pr_number: lifecycleData.pr_number,
          title: lifecycleData.title,
          html_url: lifecycleData.html_url,
          branch: lifecycleData.branch,
          base: lifecycleData.base,
          author: { 
            name: lifecycleData.author.name,
            avatar_url: lifecycleData.author.avatar_url,
          },
          current_stage: lifecycleData.current_stage as PRLifecycleData['current_stage'],
          created_at: lifecycleData.created_at,
          merged_at: lifecycleData.merged_at,
          closed_at: lifecycleData.closed_at,
          events: lifecycleData.events.map(event => ({
            id: event.id,
            stage: event.stage as LifecycleEvent['stage'],
            timestamp: event.timestamp,
            actor: {
              type: event.actor.type as 'user' | 'bot' | 'ci',
              name: event.actor.name,
              avatar_url: event.actor.avatar_url,
            },
            details: event.details ? {
              message: event.details.message,
              findings_count: event.details.findings_count,
              files_analyzed: event.details.files_analyzed,
              coverage_percentage: event.details.coverage_percentage,
              security_issues: event.details.security_issues,
              duration_seconds: event.details.duration_seconds,
            } : undefined,
            links: event.links,
          })),
        };
        
        setSelectedLifecycle(lifecycle);
        setLifecycleDialogOpen(true);
      } catch (error) {
        console.error('Failed to fetch lifecycle data:', error);
        // Fallback to demo data if API fails
        const demoData = getDemoLifecycle();
        const lifecycle: PRLifecycleData = {
          ...demoData,
          pr_number: pr.number,
          title: pr.title,
          html_url: pr.html_url,
          branch: pr.branch,
          base: pr.base,
          author: { name: 'developer' },
          current_stage: pr.ci_status === 'success' && pr.review_status === 'approved' 
            ? 'ready_to_merge' 
            : pr.ci_status === 'failure' 
              ? 'ci_failed'
              : pr.review_status === 'pending'
                ? 'code_review_pending'
                : 'ci_passed',
        };
        setSelectedLifecycle(lifecycle);
        setLifecycleDialogOpen(true);
      }
    }
  };

  const handleTriggerReview = async (prNumber: number) => {
    setLoadingPRs((prev) => ({ ...prev, [prNumber]: 'review' }));
    try {
      const result = await api.prs.triggerReview(prNumber);
      setNotification({ result, type: 'review' });
      // Refresh data after review
      await fetchData();
    } catch (error) {
      console.error('Failed to trigger review:', error);
    } finally {
      setLoadingPRs((prev) => ({ ...prev, [prNumber]: null }));
    }
  };

  const handleRunQuality = async (prNumber: number) => {
    setLoadingPRs((prev) => ({ ...prev, [prNumber]: 'quality' }));
    try {
      const result = await api.prs.runQualityCheck(prNumber);
      setNotification({ result, type: 'quality' });
      // Refresh data after quality check
      await fetchData();
    } catch (error) {
      console.error('Failed to run quality check:', error);
    } finally {
      setLoadingPRs((prev) => ({ ...prev, [prNumber]: null }));
    }
  };

  const handleRunSecurity = async (prNumber: number) => {
    setLoadingPRs((prev) => ({ ...prev, [prNumber]: 'security' }));
    try {
      const result = await api.prs.runSecurityScan(prNumber);
      setNotification({ result, type: 'security' });
      // Refresh data after security scan
      await fetchData();
    } catch (error) {
      console.error('Failed to run security scan:', error);
    } finally {
      setLoadingPRs((prev) => ({ ...prev, [prNumber]: null }));
    }
  };

  const filteredPRs = prs.filter((pr) => {
    switch (activeTab) {
      case 'needs_review':
        return pr.review_status === 'pending';
      case 'has_issues':
        return pr.quality_status === 'failing' || pr.ci_status === 'failure';
      default:
        return true;
    }
  });

  if (loading) {
    return (
      <div className="flex h-full items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Pull Requests</h1>
          <p className="text-muted-foreground">
            Monitor and review pull requests
          </p>
        </div>
        <Button onClick={handleRefresh} disabled={refreshing}>
          <RefreshCcw className={cn('mr-2 h-4 w-4', refreshing && 'animate-spin')} />
          Refresh
        </Button>
      </div>

      {/* Stats Cards */}
      {dashboard && (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          <StatsCard
            title="Open PRs"
            value={dashboard.total_open_prs}
            icon={GitPullRequest}
            description="Total open pull requests"
          />
          <StatsCard
            title="Pending Review"
            value={dashboard.pending_reviews}
            icon={Clock}
            description="Awaiting code review"
            variant={dashboard.pending_reviews > 0 ? 'warning' : 'default'}
          />
          <StatsCard
            title="Quality Passing"
            value={dashboard.quality_passing}
            icon={CheckCircle2}
            description="PRs with good quality"
            variant="success"
          />
          <StatsCard
            title="Quality Failing"
            value={dashboard.quality_failing}
            icon={XCircle}
            description="PRs with issues"
            variant={dashboard.quality_failing > 0 ? 'danger' : 'default'}
          />
        </div>
      )}

      {/* PR List */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle>Pull Requests</CardTitle>
            <Tabs value={activeTab} onValueChange={setActiveTab}>
              <TabsList>
                <TabsTrigger value="all">
                  All ({prs.length})
                </TabsTrigger>
                <TabsTrigger value="needs_review">
                  Needs Review ({prs.filter((p) => p.review_status === 'pending').length})
                </TabsTrigger>
                <TabsTrigger value="has_issues">
                  Has Issues ({prs.filter((p) => p.quality_status === 'failing' || p.ci_status === 'failure').length})
                </TabsTrigger>
              </TabsList>
            </Tabs>
          </div>
        </CardHeader>
        <CardContent>
          {filteredPRs.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-12 text-center">
              <GitPullRequest className="h-12 w-12 text-muted-foreground mb-4" />
              <p className="text-muted-foreground">
                {activeTab === 'all'
                  ? 'No open pull requests'
                  : activeTab === 'needs_review'
                  ? 'No PRs pending review'
                  : 'No PRs with issues'}
              </p>
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Pull Request</TableHead>
                  <TableHead>Branch</TableHead>
                  <TableHead>Changes</TableHead>
                  <TableHead>Review</TableHead>
                  <TableHead>Quality</TableHead>
                  <TableHead>Security</TableHead>
                  <TableHead>CI</TableHead>
                  <TableHead>Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredPRs.map((pr) => (
                  <PRRow
                    key={pr.number}
                    pr={pr}
                    onTriggerReview={handleTriggerReview}
                    onRunQuality={handleRunQuality}
                    onRunSecurity={handleRunSecurity}
                    onViewLifecycle={handleViewLifecycle}
                    isReviewLoading={loadingPRs[pr.number] === 'review'}
                    isQualityLoading={loadingPRs[pr.number] === 'quality'}
                    isSecurityLoading={loadingPRs[pr.number] === 'security'}
                  />
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {/* Recent Reviews */}
      {dashboard && dashboard.recent_reviews.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Recent Reviews</CardTitle>
            <CardDescription>Latest code reviews performed</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {dashboard.recent_reviews.map((review, idx) => (
                <div
                  key={idx}
                  className="flex items-center justify-between rounded-lg border p-3"
                >
                  <div className="flex items-center gap-3">
                    <MessageSquare className="h-4 w-4 text-muted-foreground" />
                    <div>
                      <p className="font-medium">PR #{review.pr_number}</p>
                      <p className="text-sm text-muted-foreground truncate max-w-[400px]">
                        {review.pr_title}
                      </p>
                    </div>
                  </div>
                  <div className="text-right">
                    <Badge variant="outline">{review.findings_count} findings</Badge>
                    <p className="text-xs text-muted-foreground mt-1">
                      {new Date(review.created_at).toLocaleDateString()}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Notification */}
      <AnimatePresence>
        {notification && (
          <ResultNotification
            result={notification.result}
            type={notification.type}
            onDismiss={() => setNotification(null)}
          />
        )}
      </AnimatePresence>

      {/* PR Lifecycle Timeline Dialog */}
      <Dialog open={lifecycleDialogOpen} onOpenChange={setLifecycleDialogOpen}>
        <DialogContent className="max-w-3xl max-h-[90vh] overflow-hidden">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <History className="h-5 w-5" />
              PR Lifecycle Timeline
            </DialogTitle>
          </DialogHeader>
          {selectedLifecycle && (
            <div className="overflow-auto max-h-[calc(90vh-100px)]">
              <PRLifecycleTimeline
                lifecycle={selectedLifecycle}
                onClose={() => setLifecycleDialogOpen(false)}
                onTriggerReview={() => {
                  handleTriggerReview(selectedLifecycle.pr_number);
                }}
                onRunQuality={() => {
                  handleRunQuality(selectedLifecycle.pr_number);
                }}
              />
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
