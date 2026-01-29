'use client';

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
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';

interface Workflow {
  id: string;
  name: string;
  projectName: string;
  status: 'pending' | 'running' | 'paused' | 'awaiting_input' | 'completed' | 'failed';
  phase: string;
  progress: number;
  startedAt?: string;
  duration?: string;
}

const mockWorkflows: Workflow[] = [
  {
    id: '1',
    name: 'Feature Implementation',
    projectName: 'E-Commerce Platform',
    status: 'running',
    phase: 'development',
    progress: 45,
    startedAt: '10:30 AM',
    duration: '2h 15m',
  },
  {
    id: '2',
    name: 'Bug Fix Sprint',
    projectName: 'E-Commerce Platform',
    status: 'awaiting_input',
    phase: 'code_review',
    progress: 70,
    startedAt: '9:00 AM',
    duration: '3h 45m',
  },
  {
    id: '3',
    name: 'Dashboard MVP',
    projectName: 'Analytics Dashboard',
    status: 'paused',
    phase: 'testing',
    progress: 60,
    startedAt: 'Yesterday',
    duration: '8h 30m',
  },
];

const statusConfig = {
  pending: { label: 'Pending', color: 'text-muted-foreground', icon: Clock },
  running: { label: 'Running', color: 'text-green-500', icon: Loader2, animate: true },
  paused: { label: 'Paused', color: 'text-yellow-500', icon: Pause },
  awaiting_input: { label: 'Awaiting Input', color: 'text-blue-500', icon: Clock },
  completed: { label: 'Completed', color: 'text-green-500', icon: CheckCircle2 },
  failed: { label: 'Failed', color: 'text-red-500', icon: XCircle },
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

interface WorkflowPanelProps {
  compact?: boolean;
}

export function WorkflowPanel({ compact = false }: WorkflowPanelProps) {
  const workflows = compact ? mockWorkflows.slice(0, 3) : mockWorkflows;

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
        </div>
      )}

      <div className="space-y-3">
        {workflows.map((workflow, index) => (
          <WorkflowCard
            key={workflow.id}
            workflow={workflow}
            index={index}
            compact={compact}
          />
        ))}
      </div>

      {compact && workflows.length > 0 && (
        <Button variant="ghost" className="w-full">
          View All Workflows
          <ChevronRight className="ml-2 h-4 w-4" />
        </Button>
      )}
    </div>
  );
}

interface WorkflowCardProps {
  workflow: Workflow;
  index: number;
  compact?: boolean;
}

function WorkflowCard({ workflow, index, compact }: WorkflowCardProps) {
  const status = statusConfig[workflow.status];
  const StatusIcon = status.icon;
  const phaseColor = phaseColors[workflow.phase] || 'bg-gray-500';

  return (
    <motion.div
      initial={{ opacity: 0, x: -20 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ delay: index * 0.05 }}
      className="rounded-lg border bg-card p-4 transition-shadow hover:shadow-md"
    >
      <div className="flex items-start justify-between gap-4">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <h3 className="font-medium truncate">{workflow.name}</h3>
            <StatusIcon
              className={cn(
                'h-4 w-4 shrink-0',
                status.color,
                status.animate && 'animate-spin'
              )}
            />
          </div>
          <p className="text-sm text-muted-foreground truncate">
            {workflow.projectName}
          </p>
        </div>

        <div className="flex items-center gap-2 shrink-0">
          <Badge className={cn('text-white', phaseColor)}>
            {workflow.phase.replace('_', ' ')}
          </Badge>
          {!compact && (
            <div className="flex gap-1">
              {workflow.status === 'running' && (
                <Button variant="ghost" size="icon" className="h-8 w-8">
                  <Pause className="h-4 w-4" />
                </Button>
              )}
              {workflow.status === 'paused' && (
                <Button variant="ghost" size="icon" className="h-8 w-8">
                  <Play className="h-4 w-4" />
                </Button>
              )}
              <Button variant="ghost" size="icon" className="h-8 w-8">
                <Square className="h-4 w-4" />
              </Button>
            </div>
          )}
        </div>
      </div>

      <div className="mt-3">
        <div className="flex items-center justify-between text-sm mb-1">
          <span className="text-muted-foreground">Progress</span>
          <span className="font-medium">{workflow.progress}%</span>
        </div>
        <Progress value={workflow.progress} className="h-2" />
      </div>

      {!compact && workflow.startedAt && (
        <div className="mt-3 flex items-center justify-between text-sm text-muted-foreground">
          <span>Started: {workflow.startedAt}</span>
          <span>Duration: {workflow.duration}</span>
        </div>
      )}

      {workflow.status === 'awaiting_input' && (
        <div className="mt-3 rounded-lg bg-blue-500/10 p-3">
          <p className="text-sm font-medium text-blue-500">
            Human input required
          </p>
          <p className="text-sm text-muted-foreground mt-1">
            Code review approval needed
          </p>
          <div className="mt-2 flex gap-2">
            <Button size="sm" variant="default">
              Approve
            </Button>
            <Button size="sm" variant="outline">
              Request Changes
            </Button>
          </div>
        </div>
      )}
    </motion.div>
  );
}
