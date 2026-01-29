'use client';

import { useState, useEffect, useCallback } from 'react';
import { motion } from 'framer-motion';
import {
  Bot,
  FileCode,
  TestTube,
  Shield,
  Rocket,
  ChevronRight,
  CheckCircle2,
  Wrench,
  Loader2,
  Activity,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import { ScrollArea } from '@/components/ui/scroll-area';
import { api, AgentExecution } from '@/lib/api';

interface ActivityItem {
  id: string;
  agent: string;
  action: string;
  details: string;
  timestamp: Date;
  status: 'success' | 'info' | 'warning' | 'error';
}

const agentConfig: Record<string, { icon: React.ComponentType<{ className?: string }>; color: string }> = {
  orchestrator: { icon: Bot, color: 'bg-purple-500' },
  requirements: { icon: FileCode, color: 'bg-indigo-500' },
  planning: { icon: FileCode, color: 'bg-blue-500' },
  architect: { icon: FileCode, color: 'bg-cyan-500' },
  developer: { icon: FileCode, color: 'bg-green-500' },
  code_review: { icon: Wrench, color: 'bg-cyan-500' },
  tester: { icon: TestTube, color: 'bg-blue-500' },
  security: { icon: Shield, color: 'bg-red-500' },
  devops: { icon: Rocket, color: 'bg-orange-500' },
  monitoring: { icon: Activity, color: 'bg-yellow-500' },
};

function formatRelativeTime(date: Date): string {
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMins / 60);
  
  if (diffMins < 1) return 'just now';
  if (diffMins < 60) return `${diffMins}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  return date.toLocaleDateString();
}

interface AgentActivityFeedProps {
  compact?: boolean;
  onNavigate?: (nav: string) => void;
}

export function AgentActivityFeed({ compact = false, onNavigate }: AgentActivityFeedProps) {
  const [activities, setActivities] = useState<ActivityItem[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchActivity = useCallback(async () => {
    try {
      setLoading(true);
      // Fetch all workflows first
      const workflowsResponse = await api.workflows.list(0, 10);
      
      // Collect executions from all workflows
      const allExecutions: ActivityItem[] = [];
      
      for (const workflow of workflowsResponse.items) {
        try {
          const executions = await api.workflows.getExecutions(workflow.id);
          for (const exec of executions) {
            const isSuccess = exec.success === true || exec.status === 'completed';
            const isFailed = exec.success === false || exec.status === 'failed';
            allExecutions.push({
              id: exec.id,
              agent: exec.agent_type,
              action: isSuccess ? 'Completed task' : isFailed ? 'Failed' : 'Processing',
              details: exec.agent_name || exec.agent_type,
              timestamp: new Date(exec.started_at),
              status: isSuccess ? 'success' : isFailed ? 'error' : 'info',
            });
          }
        } catch {
          // Workflow may not have executions yet
        }
      }
      
      // Sort by timestamp descending
      allExecutions.sort((a, b) => b.timestamp.getTime() - a.timestamp.getTime());
      
      setActivities(compact ? allExecutions.slice(0, 5) : allExecutions);
    } catch (error) {
      console.error('Failed to fetch activity:', error);
    } finally {
      setLoading(false);
    }
  }, [compact]);

  useEffect(() => {
    fetchActivity();
    const interval = setInterval(fetchActivity, 15000);
    return () => clearInterval(interval);
  }, [fetchActivity]);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <div className={cn('space-y-4', !compact && 'space-y-6')}>
      {!compact && (
        <div>
          <h1 className="text-3xl font-bold">Agent Activity</h1>
          <p className="text-muted-foreground">
            Real-time feed of agent actions and decisions
          </p>
        </div>
      )}

      {activities.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-8 text-center">
          <Bot className="h-10 w-10 text-muted-foreground mb-3" />
          <h3 className="text-lg font-semibold">No agent activity yet</h3>
          <p className="text-muted-foreground text-sm">
            Start a workflow to see agent activity here
          </p>
        </div>
      ) : (
        <ScrollArea className={cn(compact ? 'h-[300px]' : 'h-[600px]')}>
          <div className="space-y-4 pr-4">
            {activities.map((activity, index) => (
              <ActivityCard key={activity.id} activity={activity} index={index} />
            ))}
          </div>
        </ScrollArea>
      )}

      {compact && activities.length > 0 && (
        <Button variant="ghost" className="w-full" onClick={() => onNavigate?.('activity')}>
          View All Activity
          <ChevronRight className="ml-2 h-4 w-4" />
        </Button>
      )}
    </div>
  );
}

interface ActivityCardProps {
  activity: ActivityItem;
  index: number;
}

function ActivityCard({ activity, index }: ActivityCardProps) {
  const agent = agentConfig[activity.agent] || agentConfig.orchestrator;
  const AgentIcon = agent.icon;
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  const statusColors = {
    success: 'text-green-500',
    info: 'text-blue-500',
    warning: 'text-yellow-500',
    error: 'text-red-500',
  };

  return (
    <motion.div
      initial={{ opacity: 0, x: -10 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ delay: index * 0.05 }}
      className="flex items-start gap-3"
    >
      <Avatar className="h-8 w-8">
        <AvatarFallback className={agent.color}>
          <AgentIcon className="h-4 w-4 text-white" />
        </AvatarFallback>
      </Avatar>

      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className={cn('font-medium text-sm', statusColors[activity.status])}>
            {activity.action}
          </span>
          {activity.status === 'success' && (
            <CheckCircle2 className="h-3 w-3 text-green-500" />
          )}
        </div>
        <p className="text-sm text-muted-foreground truncate">
          {activity.details}
        </p>
        <span className="text-xs text-muted-foreground">
          {mounted ? formatRelativeTime(activity.timestamp) : ''}
        </span>
      </div>
    </motion.div>
  );
}
