'use client';

import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  GitPullRequest,
  GitMerge,
  CheckCircle2,
  XCircle,
  AlertCircle,
  Clock,
  Eye,
  MessageSquare,
  Shield,
  TestTube2,
  Rocket,
  ChevronDown,
  ChevronRight,
  ExternalLink,
  Bot,
  User,
  Loader2,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { ScrollArea } from '@/components/ui/scroll-area';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip';

// Lifecycle stage type
export type LifecycleStage = 
  | 'created'
  | 'ci_running'
  | 'ci_passed'
  | 'ci_failed'
  | 'code_review_pending'
  | 'code_review_in_progress'
  | 'code_review_approved'
  | 'code_review_changes_requested'
  | 'quality_check_running'
  | 'quality_check_passed'
  | 'quality_check_failed'
  | 'security_scan_running'
  | 'security_scan_passed'
  | 'security_scan_failed'
  | 'ready_to_merge'
  | 'merging'
  | 'merged'
  | 'closed';

export interface LifecycleEvent {
  id: string;
  stage: LifecycleStage;
  timestamp: string;
  actor: {
    type: 'user' | 'bot' | 'ci';
    name: string;
    avatar_url?: string;
  };
  details?: {
    message?: string;
    findings_count?: number;
    files_analyzed?: number;
    coverage_percentage?: number;
    security_issues?: number;
    duration_seconds?: number;
  };
  links?: {
    label: string;
    url: string;
  }[];
}

export interface PRLifecycleData {
  pr_number: number;
  title: string;
  html_url: string;
  branch: string;
  base: string;
  author: {
    name: string;
    avatar_url?: string;
  };
  current_stage: LifecycleStage;
  events: LifecycleEvent[];
  created_at: string;
  merged_at?: string;
  closed_at?: string;
}

// Stage configuration
const stageConfig: Record<LifecycleStage, {
  icon: React.ComponentType<{ className?: string }>;
  label: string;
  color: string;
  bgColor: string;
}> = {
  created: { icon: GitPullRequest, label: 'PR Created', color: 'text-blue-500', bgColor: 'bg-blue-500/10' },
  ci_running: { icon: Loader2, label: 'CI Running', color: 'text-yellow-500', bgColor: 'bg-yellow-500/10' },
  ci_passed: { icon: CheckCircle2, label: 'CI Passed', color: 'text-green-500', bgColor: 'bg-green-500/10' },
  ci_failed: { icon: XCircle, label: 'CI Failed', color: 'text-red-500', bgColor: 'bg-red-500/10' },
  code_review_pending: { icon: Eye, label: 'Review Pending', color: 'text-gray-500', bgColor: 'bg-gray-500/10' },
  code_review_in_progress: { icon: MessageSquare, label: 'Review In Progress', color: 'text-yellow-500', bgColor: 'bg-yellow-500/10' },
  code_review_approved: { icon: CheckCircle2, label: 'Review Approved', color: 'text-green-500', bgColor: 'bg-green-500/10' },
  code_review_changes_requested: { icon: AlertCircle, label: 'Changes Requested', color: 'text-orange-500', bgColor: 'bg-orange-500/10' },
  quality_check_running: { icon: TestTube2, label: 'Quality Check Running', color: 'text-yellow-500', bgColor: 'bg-yellow-500/10' },
  quality_check_passed: { icon: CheckCircle2, label: 'Quality Check Passed', color: 'text-green-500', bgColor: 'bg-green-500/10' },
  quality_check_failed: { icon: AlertCircle, label: 'Quality Issues', color: 'text-orange-500', bgColor: 'bg-orange-500/10' },
  security_scan_running: { icon: Shield, label: 'Security Scan Running', color: 'text-yellow-500', bgColor: 'bg-yellow-500/10' },
  security_scan_passed: { icon: Shield, label: 'Security Passed', color: 'text-green-500', bgColor: 'bg-green-500/10' },
  security_scan_failed: { icon: Shield, label: 'Security Issues', color: 'text-red-500', bgColor: 'bg-red-500/10' },
  ready_to_merge: { icon: Rocket, label: 'Ready to Merge', color: 'text-purple-500', bgColor: 'bg-purple-500/10' },
  merging: { icon: GitMerge, label: 'Merging', color: 'text-purple-500', bgColor: 'bg-purple-500/10' },
  merged: { icon: GitMerge, label: 'Merged', color: 'text-purple-600', bgColor: 'bg-purple-600/10' },
  closed: { icon: XCircle, label: 'Closed', color: 'text-gray-500', bgColor: 'bg-gray-500/10' },
};

// Timeline event component
function TimelineEvent({ event, isLast }: { event: LifecycleEvent; isLast: boolean }) {
  const [expanded, setExpanded] = useState(false);
  const config = stageConfig[event.stage];
  const Icon = config.icon;
  const isRunning = event.stage.includes('running') || event.stage.includes('in_progress');

  return (
    <div className="relative flex gap-4">
      {/* Timeline line */}
      {!isLast && (
        <div className="absolute left-5 top-10 w-0.5 h-full bg-border" />
      )}
      
      {/* Event marker */}
      <div className={cn(
        'relative z-10 flex h-10 w-10 items-center justify-center rounded-full border-2',
        config.bgColor,
        config.color,
        'border-current'
      )}>
        <Icon className={cn('h-5 w-5', isRunning && 'animate-spin')} />
      </div>
      
      {/* Event content */}
      <div className="flex-1 pb-6">
        <button
          onClick={() => setExpanded(!expanded)}
          className="flex items-center gap-2 text-left w-full"
        >
          <div className="flex-1">
            <p className="font-medium">{config.label}</p>
            <p className="text-sm text-muted-foreground">
              {new Date(event.timestamp).toLocaleString()}
            </p>
          </div>
          <div className="flex items-center gap-2">
            {event.actor.type === 'bot' && (
              <Badge variant="outline" className="gap-1">
                <Bot className="h-3 w-3" />
                {event.actor.name}
              </Badge>
            )}
            {event.actor.type === 'user' && (
              <Badge variant="outline" className="gap-1">
                <User className="h-3 w-3" />
                {event.actor.name}
              </Badge>
            )}
            {event.details && (
              expanded ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />
            )}
          </div>
        </button>
        
        {/* Expanded details */}
        <AnimatePresence>
          {expanded && event.details && (
            <motion.div
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: 'auto', opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              className="overflow-hidden"
            >
              <div className="mt-3 p-3 bg-muted/50 rounded-lg space-y-2">
                {event.details.message && (
                  <p className="text-sm">{event.details.message}</p>
                )}
                {event.details.files_analyzed !== undefined && (
                  <p className="text-sm">
                    <span className="text-muted-foreground">Files analyzed:</span>{' '}
                    {event.details.files_analyzed}
                  </p>
                )}
                {event.details.findings_count !== undefined && (
                  <p className="text-sm">
                    <span className="text-muted-foreground">Findings:</span>{' '}
                    <span className={event.details.findings_count > 0 ? 'text-orange-500' : 'text-green-500'}>
                      {event.details.findings_count}
                    </span>
                  </p>
                )}
                {event.details.coverage_percentage !== undefined && (
                  <p className="text-sm">
                    <span className="text-muted-foreground">Test coverage:</span>{' '}
                    <span className={event.details.coverage_percentage >= 80 ? 'text-green-500' : 'text-orange-500'}>
                      {event.details.coverage_percentage}%
                    </span>
                  </p>
                )}
                {event.details.security_issues !== undefined && (
                  <p className="text-sm">
                    <span className="text-muted-foreground">Security issues:</span>{' '}
                    <span className={event.details.security_issues > 0 ? 'text-red-500' : 'text-green-500'}>
                      {event.details.security_issues}
                    </span>
                  </p>
                )}
                {event.details.duration_seconds !== undefined && (
                  <p className="text-sm text-muted-foreground">
                    Duration: {Math.round(event.details.duration_seconds)}s
                  </p>
                )}
                {event.links && event.links.length > 0 && (
                  <div className="flex gap-2 pt-2">
                    {event.links.map((link, i) => (
                      <a
                        key={i}
                        href={link.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-sm text-primary hover:underline inline-flex items-center gap-1"
                      >
                        {link.label}
                        <ExternalLink className="h-3 w-3" />
                      </a>
                    ))}
                  </div>
                )}
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}

// Stage progress indicator
function StageProgress({ currentStage, events }: { currentStage: LifecycleStage; events: LifecycleEvent[] }) {
  const stages: LifecycleStage[] = [
    'created',
    'ci_passed',
    'code_review_approved',
    'quality_check_passed',
    'security_scan_passed',
    'merged',
  ];
  
  const stageOrder = stages.reduce((acc, stage, i) => {
    acc[stage] = i;
    return acc;
  }, {} as Record<LifecycleStage, number>);
  
  // Find the highest completed stage
  const completedStages = new Set(events.map(e => e.stage));
  let currentIndex = 0;
  for (let i = 0; i < stages.length; i++) {
    if (completedStages.has(stages[i])) {
      currentIndex = i + 1;
    }
  }
  
  // Handle failure states
  const hasCIFailed = completedStages.has('ci_failed');
  const hasReviewChanges = completedStages.has('code_review_changes_requested');
  const hasQualityFailed = completedStages.has('quality_check_failed');
  const hasSecurityFailed = completedStages.has('security_scan_failed');

  return (
    <div className="flex items-center justify-between gap-2 mb-6">
      {stages.map((stage, i) => {
        const config = stageConfig[stage];
        const Icon = config.icon;
        const isCompleted = i < currentIndex;
        const isCurrent = i === currentIndex;
        const isFailed = 
          (stage === 'ci_passed' && hasCIFailed) ||
          (stage === 'code_review_approved' && hasReviewChanges) ||
          (stage === 'quality_check_passed' && hasQualityFailed) ||
          (stage === 'security_scan_passed' && hasSecurityFailed);
        
        return (
          <TooltipProvider key={stage}>
            <Tooltip>
              <TooltipTrigger asChild>
                <div className="flex flex-col items-center gap-1 flex-1">
                  <div className={cn(
                    'h-8 w-8 rounded-full flex items-center justify-center border-2 transition-all',
                    isCompleted && !isFailed && 'bg-green-500 border-green-500 text-white',
                    isCurrent && !isFailed && 'bg-blue-500/20 border-blue-500 text-blue-500',
                    isFailed && 'bg-red-500 border-red-500 text-white',
                    !isCompleted && !isCurrent && !isFailed && 'bg-muted border-muted-foreground/30 text-muted-foreground',
                  )}>
                    {isFailed ? (
                      <XCircle className="h-4 w-4" />
                    ) : isCompleted ? (
                      <CheckCircle2 className="h-4 w-4" />
                    ) : (
                      <Icon className="h-4 w-4" />
                    )}
                  </div>
                  {i < stages.length - 1 && (
                    <div className={cn(
                      'absolute h-0.5 w-full max-w-[80px]',
                      isCompleted ? 'bg-green-500' : 'bg-muted-foreground/30',
                    )} style={{ left: '50%', top: '12px' }} />
                  )}
                  <span className="text-xs text-muted-foreground text-center">
                    {config.label.replace('Passed', '').replace('Approved', '').trim()}
                  </span>
                </div>
              </TooltipTrigger>
              <TooltipContent>{config.label}</TooltipContent>
            </Tooltip>
          </TooltipProvider>
        );
      })}
    </div>
  );
}

// Main PR Lifecycle Timeline component
interface PRLifecycleTimelineProps {
  lifecycle: PRLifecycleData;
  onClose?: () => void;
  onTriggerReview?: () => void;
  onRunQuality?: () => void;
  onRunSecurity?: () => void;
}

export function PRLifecycleTimeline({
  lifecycle,
  onClose,
  onTriggerReview,
  onRunQuality,
  onRunSecurity,
}: PRLifecycleTimelineProps) {
  const config = stageConfig[lifecycle.current_stage];
  const isMerged = lifecycle.current_stage === 'merged';
  const isClosed = lifecycle.current_stage === 'closed';

  return (
    <Card className="w-full max-w-2xl">
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-3">
            <div className={cn(
              'h-12 w-12 rounded-full flex items-center justify-center',
              config.bgColor,
            )}>
              <GitPullRequest className={cn('h-6 w-6', config.color)} />
            </div>
            <div>
              <CardTitle className="flex items-center gap-2">
                <a
                  href={lifecycle.html_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="hover:underline"
                >
                  #{lifecycle.pr_number}
                </a>
                <Badge variant={isMerged ? 'default' : isClosed ? 'secondary' : 'outline'}>
                  {config.label}
                </Badge>
              </CardTitle>
              <CardDescription className="mt-1">
                {lifecycle.title}
              </CardDescription>
            </div>
          </div>
          <a
            href={lifecycle.html_url}
            target="_blank"
            rel="noopener noreferrer"
            className="text-muted-foreground hover:text-foreground"
          >
            <ExternalLink className="h-5 w-5" />
          </a>
        </div>
        
        <div className="flex items-center gap-4 mt-4 text-sm text-muted-foreground">
          <span>{lifecycle.branch} → {lifecycle.base}</span>
          <span>by {lifecycle.author.name}</span>
          <span>{new Date(lifecycle.created_at).toLocaleDateString()}</span>
        </div>
      </CardHeader>
      
      <CardContent>
        {/* Stage progress bar */}
        <StageProgress currentStage={lifecycle.current_stage} events={lifecycle.events} />
        
        {/* Action buttons */}
        {!isMerged && !isClosed && (
          <div className="flex gap-2 mb-6">
            {onTriggerReview && (
              <Button variant="outline" size="sm" onClick={onTriggerReview}>
                <Eye className="h-4 w-4 mr-2" />
                Trigger Review
              </Button>
            )}
            {onRunQuality && (
              <Button variant="outline" size="sm" onClick={onRunQuality}>
                <TestTube2 className="h-4 w-4 mr-2" />
                Run Quality Check
              </Button>
            )}
            {onRunSecurity && (
              <Button variant="outline" size="sm" onClick={onRunSecurity}>
                <Shield className="h-4 w-4 mr-2" />
                Run Security Scan
              </Button>
            )}
          </div>
        )}
        
        {/* Timeline */}
        <ScrollArea className="h-[400px] pr-4">
          <div className="space-y-0">
            {lifecycle.events.map((event, i) => (
              <TimelineEvent
                key={event.id}
                event={event}
                isLast={i === lifecycle.events.length - 1}
              />
            ))}
          </div>
        </ScrollArea>
        
        {/* Summary footer */}
        {isMerged && lifecycle.merged_at && (
          <div className="mt-4 pt-4 border-t flex items-center justify-between">
            <div className="flex items-center gap-2 text-green-600">
              <GitMerge className="h-5 w-5" />
              <span className="font-medium">Merged</span>
            </div>
            <span className="text-sm text-muted-foreground">
              {new Date(lifecycle.merged_at).toLocaleString()}
            </span>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

// Demo/sample lifecycle data for testing
export function getDemoLifecycle(): PRLifecycleData {
  return {
    pr_number: 276,
    title: 'feat(rbac): Implement Role-Based Access Control system',
    html_url: 'https://github.com/soren-norgaard/Agentic/pull/276',
    branch: 'feature/rbac-implementation',
    base: 'main',
    author: { name: 'developer' },
    current_stage: 'merged',
    created_at: '2026-02-01T10:00:00Z',
    merged_at: '2026-02-02T14:30:00Z',
    events: [
      {
        id: '1',
        stage: 'created',
        timestamp: '2026-02-01T10:00:00Z',
        actor: { type: 'user', name: 'developer' },
        details: { message: 'Pull request created from feature/rbac-implementation' },
      },
      {
        id: '2',
        stage: 'ci_running',
        timestamp: '2026-02-01T10:01:00Z',
        actor: { type: 'ci', name: 'GitHub Actions' },
      },
      {
        id: '3',
        stage: 'ci_passed',
        timestamp: '2026-02-01T10:15:00Z',
        actor: { type: 'ci', name: 'GitHub Actions' },
        details: { duration_seconds: 840, message: 'All 105 tests passed' },
        links: [{ label: 'View CI Run', url: 'https://github.com/actions' }],
      },
      {
        id: '4',
        stage: 'code_review_pending',
        timestamp: '2026-02-01T10:15:30Z',
        actor: { type: 'bot', name: 'SDLC Agent' },
      },
      {
        id: '5',
        stage: 'code_review_in_progress',
        timestamp: '2026-02-01T10:16:00Z',
        actor: { type: 'bot', name: 'Code Review Agent' },
      },
      {
        id: '6',
        stage: 'code_review_approved',
        timestamp: '2026-02-01T10:25:00Z',
        actor: { type: 'bot', name: 'Code Review Agent' },
        details: {
          files_analyzed: 12,
          findings_count: 2,
          message: 'Code review approved with minor suggestions',
        },
      },
      {
        id: '7',
        stage: 'quality_check_running',
        timestamp: '2026-02-01T10:25:30Z',
        actor: { type: 'bot', name: 'Quality Agent' },
      },
      {
        id: '8',
        stage: 'quality_check_passed',
        timestamp: '2026-02-01T10:30:00Z',
        actor: { type: 'bot', name: 'Quality Agent' },
        details: {
          coverage_percentage: 85,
          findings_count: 0,
          message: 'Quality checks passed',
        },
      },
      {
        id: '9',
        stage: 'security_scan_running',
        timestamp: '2026-02-01T10:30:30Z',
        actor: { type: 'bot', name: 'Security Agent' },
      },
      {
        id: '10',
        stage: 'security_scan_passed',
        timestamp: '2026-02-01T10:35:00Z',
        actor: { type: 'bot', name: 'Security Agent' },
        details: {
          security_issues: 0,
          message: 'No security vulnerabilities detected',
        },
      },
      {
        id: '11',
        stage: 'ready_to_merge',
        timestamp: '2026-02-01T10:35:30Z',
        actor: { type: 'bot', name: 'SDLC Agent' },
        details: { message: 'All checks passed. PR is ready to merge.' },
      },
      {
        id: '12',
        stage: 'merged',
        timestamp: '2026-02-02T14:30:00Z',
        actor: { type: 'user', name: 'admin' },
        details: { message: 'Pull request merged to main' },
      },
    ],
  };
}
