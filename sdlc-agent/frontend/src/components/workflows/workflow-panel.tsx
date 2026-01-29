'use client';

import { useState, useEffect, useCallback } from 'react';
import { motion } from 'framer-motion';
import {
  Play,
  Pause,
  Square,
  Clock,
  CheckCircle2,
  XCircle,
  Loader2,
  ChevronRight,
  Trash2,
  Plus,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { api, Workflow as ApiWorkflow, Project } from '@/lib/api';
import { CreateWorkflowDialog } from '@/components/workflows/create-workflow-dialog';

interface Workflow {
  id: string;
  name: string;
  projectName: string;
  status: 'pending' | 'running' | 'paused' | 'awaiting_input' | 'completed' | 'failed' | 'cancelled';
  phase: string;
  progress: number;
  startedAt?: string;
  duration?: string;
}

const statusConfig = {
  pending: { label: 'Pending', color: 'text-muted-foreground', icon: Clock },
  running: { label: 'Running', color: 'text-green-500', icon: Loader2, animate: true },
  paused: { label: 'Paused', color: 'text-yellow-500', icon: Pause },
  awaiting_input: { label: 'Awaiting Input', color: 'text-blue-500', icon: Clock },
  completed: { label: 'Completed', color: 'text-green-500', icon: CheckCircle2 },
  failed: { label: 'Failed', color: 'text-red-500', icon: XCircle },
  cancelled: { label: 'Cancelled', color: 'text-gray-500', icon: Square },
};

const phaseColors: Record<string, string> = {
  requirements: 'bg-purple-500',
  planning: 'bg-blue-500',
  design: 'bg-yellow-500',
  development: 'bg-green-500',
  code_review: 'bg-cyan-500',
  testing: 'bg-blue-400',
  security: 'bg-red-500',
  deployment: 'bg-purple-600',
  monitoring: 'bg-orange-500',
};

function formatDuration(startedAt: string): string {
  const start = new Date(startedAt);
  const now = new Date();
  const diffMs = now.getTime() - start.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMins / 60);
  
  if (diffHours > 0) {
    return `${diffHours}h ${diffMins % 60}m`;
  }
  return `${diffMins}m`;
}

function formatStartTime(startedAt: string): string {
  const date = new Date(startedAt);
  const now = new Date();
  const isToday = date.toDateString() === now.toDateString();
  
  if (isToday) {
    return date.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' });
  }
  return 'Yesterday';
}

function calculateProgress(status: string): number {
  switch (status) {
    case 'pending': return 0;
    case 'running': return 50;
    case 'paused': return 50;
    case 'awaiting_input': return 70;
    case 'completed': return 100;
    case 'failed': return 100;
    case 'cancelled': return 100;
    default: return 0;
  }
}

interface WorkflowPanelProps {
  compact?: boolean;
  onNavigate?: (nav: string) => void;
}

export function WorkflowPanel({ compact = false, onNavigate }: WorkflowPanelProps) {
  const [workflows, setWorkflows] = useState<Workflow[]>([]);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState<string | null>(null);
  const [projectsMap, setProjectsMap] = useState<Record<string, string>>({});
  const [createDialogOpen, setCreateDialogOpen] = useState(false);

  const fetchWorkflows = useCallback(async () => {
    try {
      setLoading(true);
      
      // Fetch projects first to get names
      const projectsResponse = await api.projects.list(0, 100);
      const projMap: Record<string, string> = {};
      projectsResponse.items.forEach((p: Project) => {
        projMap[p.id] = p.name;
      });
      setProjectsMap(projMap);
      
      const response = await api.workflows.list(0, compact ? 3 : 50);
      const mappedWorkflows: Workflow[] = response.items.map((w: ApiWorkflow) => ({
        id: w.id,
        name: w.name,
        projectName: projMap[w.project_id] || 'Unknown Project',
        status: w.status as Workflow['status'],
        phase: 'development',
        progress: calculateProgress(w.status),
        startedAt: w.started_at ? formatStartTime(w.started_at) : undefined,
        duration: w.started_at ? formatDuration(w.started_at) : undefined,
      }));
      setWorkflows(mappedWorkflows);
    } catch (error) {
      console.error('Failed to fetch workflows:', error);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchWorkflows();
  }, [fetchWorkflows]);

  // Polling - pause when dialog is open
  useEffect(() => {
    if (createDialogOpen) return; // Don't poll when dialog is open
    
    const interval = setInterval(fetchWorkflows, 10000);
    return () => clearInterval(interval);
  }, [fetchWorkflows, createDialogOpen]);

  const handleAction = async (workflowId: string, action: 'start' | 'pause' | 'resume' | 'cancel') => {
    try {
      setActionLoading(workflowId);
      await api.workflows.action(workflowId, action);
      await fetchWorkflows();
    } catch (error) {
      console.error(`Failed to ${action} workflow:`, error);
    } finally {
      setActionLoading(null);
    }
  };

  const handleDelete = async (workflowId: string) => {
    try {
      setActionLoading(workflowId);
      await api.workflows.delete(workflowId);
      await fetchWorkflows();
    } catch (error) {
      console.error('Failed to delete workflow:', error);
      alert('Cannot delete a running workflow. Cancel it first.');
    } finally {
      setActionLoading(null);
    }
  };

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
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold">Workflows</h1>
            <p className="text-muted-foreground">
              Active SDLC automation workflows
            </p>
          </div>
          <Button onClick={() => setCreateDialogOpen(true)}>
            <Plus className="mr-2 h-4 w-4" />
            New Workflow
          </Button>
        </div>
      )}

      {workflows.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-8 text-center">
          <Clock className="h-10 w-10 text-muted-foreground mb-3" />
          <h3 className="text-lg font-semibold">No workflows yet</h3>
          <p className="text-muted-foreground text-sm mb-4">
            Create a workflow to start your SDLC automation
          </p>
          <Button onClick={() => setCreateDialogOpen(true)}>
            <Plus className="mr-2 h-4 w-4" />
            New Workflow
          </Button>
        </div>
      ) : (
        <div className="space-y-3">
          {workflows.map((workflow, index) => (
            <WorkflowCard
              key={workflow.id}
              workflow={workflow}
              index={index}
              compact={compact}
              onAction={handleAction}
              onDelete={handleDelete}
              actionLoading={actionLoading}
            />
          ))}
        </div>
      )}

      {compact && workflows.length > 0 && (
        <Button variant="ghost" className="w-full" onClick={() => onNavigate?.('workflows')}>
          View All Workflows
          <ChevronRight className="ml-2 h-4 w-4" />
        </Button>
      )}

      <CreateWorkflowDialog
        open={createDialogOpen}
        onOpenChange={setCreateDialogOpen}
        onSuccess={fetchWorkflows}
      />
    </div>
  );
}

interface WorkflowCardProps {
  workflow: Workflow;
  onAction: (workflowId: string, action: 'start' | 'pause' | 'resume' | 'cancel') => void;
  onDelete: (workflowId: string) => void;
  actionLoading: string | null;
  index: number;
  compact: boolean;
}

function WorkflowCard({ workflow, index, compact, onAction, onDelete, actionLoading }: WorkflowCardProps) {
  const config = statusConfig[workflow.status] || statusConfig.pending;
  const StatusIcon = config.icon;
  const isLoading = actionLoading === workflow.id;

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.05 }}
      className="rounded-lg border bg-card p-4 transition-colors hover:bg-accent/50"
    >
      <div className="flex items-start justify-between gap-4">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <StatusIcon
              className={cn(
                'h-4 w-4',
                config.color,
                (config as { animate?: boolean }).animate && 'animate-spin'
              )}
            />
            <h3 className="font-medium truncate">{workflow.name}</h3>
          </div>

          <p className="text-sm text-muted-foreground truncate mt-1">
            {workflow.projectName}
          </p>

          {!compact && (
            <div className="mt-3 space-y-2">
              <div className="flex items-center gap-2">
                <Badge
                  variant="secondary"
                  className={cn('text-xs', phaseColors[workflow.phase])}
                >
                  {workflow.phase}
                </Badge>
                {workflow.startedAt && (
                  <span className="text-xs text-muted-foreground">
                    Started {workflow.startedAt}
                  </span>
                )}
                {workflow.duration && (
                  <span className="text-xs text-muted-foreground">
                    • {workflow.duration}
                  </span>
                )}
              </div>

              <Progress value={workflow.progress} className="h-2" />
            </div>
          )}
        </div>

        {!compact && workflow.status === 'running' && (
          <div className="flex gap-1">
            <Button 
              size="icon" 
              variant="ghost" 
              className="h-8 w-8"
              onClick={() => onAction(workflow.id, 'pause')}
              disabled={isLoading}
            >
              {isLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Pause className="h-4 w-4" />}
            </Button>
            <Button 
              size="icon" 
              variant="ghost" 
              className="h-8 w-8"
              onClick={() => onAction(workflow.id, 'cancel')}
              disabled={isLoading}
            >
              <Square className="h-4 w-4" />
            </Button>
          </div>
        )}

        {!compact && workflow.status === 'paused' && (
          <Button 
            size="icon" 
            variant="ghost" 
            className="h-8 w-8"
            onClick={() => onAction(workflow.id, 'resume')}
            disabled={isLoading}
          >
            {isLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Play className="h-4 w-4" />}
          </Button>
        )}

        {!compact && workflow.status === 'pending' && (
          <Button 
            size="icon" 
            variant="ghost" 
            className="h-8 w-8"
            onClick={() => onAction(workflow.id, 'start')}
            disabled={isLoading}
          >
            {isLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Play className="h-4 w-4" />}
          </Button>
        )}

        {/* Delete button for non-running workflows */}
        {!compact && !['running'].includes(workflow.status) && (
          <Button 
            size="icon" 
            variant="ghost" 
            className="h-8 w-8 text-destructive hover:text-destructive"
            onClick={() => onDelete(workflow.id)}
            disabled={isLoading}
            title="Delete workflow"
          >
            {isLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Trash2 className="h-4 w-4" />}
          </Button>
        )}
      </div>
    </motion.div>
  );
}
