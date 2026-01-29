'use client';

import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  ChevronRight,
  ChevronDown,
  Plus,
  MoreHorizontal,
  Layers,
  BookOpen,
  CheckSquare,
  Bug,
  Zap,
  AlertCircle,
  Clock,
  User,
  Tag,
  GripVertical,
  Github,
  Loader2,
  ExternalLink,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';
import { Skeleton } from '@/components/ui/skeleton';
import { api, TaskItem, TaskStats, GitHubConfig } from '@/lib/api';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';

interface BacklogViewProps {
  projectId: string;
}

const taskTypeIcons = {
  epic: Layers,
  story: BookOpen,
  task: CheckSquare,
  bug: Bug,
  spike: Zap,
};

const taskTypeColors = {
  epic: 'bg-purple-500/10 text-purple-500 border-purple-500/20',
  story: 'bg-blue-500/10 text-blue-500 border-blue-500/20',
  task: 'bg-green-500/10 text-green-500 border-green-500/20',
  bug: 'bg-red-500/10 text-red-500 border-red-500/20',
  spike: 'bg-yellow-500/10 text-yellow-500 border-yellow-500/20',
};

const priorityColors = {
  critical: 'bg-red-500',
  high: 'bg-orange-500',
  medium: 'bg-yellow-500',
  low: 'bg-gray-400',
};

const statusColors = {
  backlog: 'bg-slate-500',
  todo: 'bg-blue-500',
  in_progress: 'bg-yellow-500',
  in_review: 'bg-purple-500',
  done: 'bg-green-500',
  blocked: 'bg-red-500',
};

export function BacklogView({ projectId }: BacklogViewProps) {
  const [tasks, setTasks] = useState<TaskItem[]>([]);
  const [stats, setStats] = useState<TaskStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [expandedEpics, setExpandedEpics] = useState<Set<string>>(new Set());
  const [view, setView] = useState<'hierarchy' | 'list'>('hierarchy');
  const [githubConfig, setGithubConfig] = useState<GitHubConfig | null>(null);
  const [syncing, setSyncing] = useState(false);
  const [syncResult, setSyncResult] = useState<{ success: boolean; message: string } | null>(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        const [hierarchyData, statsData] = await Promise.all([
          api.tasks.getHierarchy(projectId),
          api.tasks.getStats(projectId),
        ]);
        setTasks(hierarchyData);
        setStats(statsData);
        // Expand all epics by default
        setExpandedEpics(new Set(hierarchyData.map(t => t.id)));
        
        // Check GitHub configuration
        try {
          const config = await api.github.getConfig();
          setGithubConfig(config);
        } catch {
          // GitHub not configured - that's ok
        }
      } catch (error) {
        console.error('Failed to fetch backlog:', error);
      } finally {
        setLoading(false);
      }
    };

    if (projectId) {
      fetchData();
    }
  }, [projectId]);

  const handleSyncToGitHub = async () => {
    setSyncing(true);
    setSyncResult(null);
    try {
      const result = await api.github.syncProject(projectId);
      setSyncResult({
        success: result.success,
        message: `Synced ${result.synced_count} items to GitHub${result.failed_count > 0 ? `, ${result.failed_count} failed` : ''}`,
      });
    } catch (error) {
      setSyncResult({
        success: false,
        message: error instanceof Error ? error.message : 'Failed to sync to GitHub',
      });
    } finally {
      setSyncing(false);
      // Clear message after 5 seconds
      setTimeout(() => setSyncResult(null), 5000);
    }
  };

  const toggleEpic = (epicId: string) => {
    setExpandedEpics(prev => {
      const next = new Set(prev);
      if (next.has(epicId)) {
        next.delete(epicId);
      } else {
        next.add(epicId);
      }
      return next;
    });
  };

  if (loading) {
    return <BacklogSkeleton />;
  }

  const progressPercentage = stats
    ? Math.round((stats.completed_story_points / Math.max(stats.total_story_points, 1)) * 100)
    : 0;

  return (
    <div className="space-y-6">
      {/* Stats Overview */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Total Items
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats?.total || 0}</div>
            <div className="flex gap-2 mt-2">
              {Object.entries(stats?.by_type || {}).map(([type, count]) => (
                <Badge key={type} variant="secondary" className="text-xs">
                  {type}: {count}
                </Badge>
              ))}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Story Points
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {stats?.completed_story_points || 0}
              <span className="text-muted-foreground font-normal text-lg">
                /{stats?.total_story_points || 0}
              </span>
            </div>
            <Progress value={progressPercentage} className="mt-2" />
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              By Status
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex flex-wrap gap-1">
              {Object.entries(stats?.by_status || {}).map(([status, count]) => (
                <Badge
                  key={status}
                  variant="outline"
                  className="text-xs"
                >
                  <span
                    className={cn(
                      'w-2 h-2 rounded-full mr-1',
                      statusColors[status as keyof typeof statusColors] || 'bg-gray-400'
                    )}
                  />
                  {status.replace('_', ' ')}: {count}
                </Badge>
              ))}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              By Priority
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex flex-wrap gap-1">
              {Object.entries(stats?.by_priority || {}).map(([priority, count]) => (
                <Badge
                  key={priority}
                  variant="outline"
                  className="text-xs"
                >
                  <span
                    className={cn(
                      'w-2 h-2 rounded-full mr-1',
                      priorityColors[priority as keyof typeof priorityColors] || 'bg-gray-400'
                    )}
                  />
                  {priority}: {count}
                </Badge>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* View Toggle & Actions */}
      <div className="flex justify-between items-center">
        <h2 className="text-lg font-semibold">Product Backlog</h2>
        <div className="flex gap-2 items-center">
          {/* GitHub Sync */}
          {githubConfig?.configured && (
            <Button
              variant="outline"
              size="sm"
              onClick={handleSyncToGitHub}
              disabled={syncing || tasks.length === 0}
              className="border-purple-500/30 text-purple-400 hover:bg-purple-500/10"
            >
              {syncing ? (
                <>
                  <Loader2 className="h-4 w-4 mr-1 animate-spin" />
                  Syncing...
                </>
              ) : (
                <>
                  <Github className="h-4 w-4 mr-1" />
                  Sync to GitHub
                </>
              )}
            </Button>
          )}
          
          {/* View Toggle */}
          <Button
            variant={view === 'hierarchy' ? 'secondary' : 'ghost'}
            size="sm"
            onClick={() => setView('hierarchy')}
          >
            <Layers className="h-4 w-4 mr-1" />
            Hierarchy
          </Button>
          <Button
            variant={view === 'list' ? 'secondary' : 'ghost'}
            size="sm"
            onClick={() => setView('list')}
          >
            <CheckSquare className="h-4 w-4 mr-1" />
            List
          </Button>
        </div>
      </div>

      {/* Sync Result Notification */}
      {syncResult && (
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0 }}
          className={cn(
            'p-3 rounded-lg flex items-center gap-2 text-sm',
            syncResult.success
              ? 'bg-green-500/10 text-green-400 border border-green-500/20'
              : 'bg-red-500/10 text-red-400 border border-red-500/20'
          )}
        >
          {syncResult.success ? (
            <Github className="h-4 w-4" />
          ) : (
            <AlertCircle className="h-4 w-4" />
          )}
          {syncResult.message}
        </motion.div>
      )}

      {/* Backlog Items */}
      {tasks.length === 0 ? (
        <Card className="p-12">
          <div className="text-center text-muted-foreground">
            <Layers className="h-12 w-12 mx-auto mb-4 opacity-50" />
            <h3 className="text-lg font-medium mb-2">No items in backlog</h3>
            <p className="text-sm">
              Run a workflow to generate epics, stories, and tasks
            </p>
          </div>
        </Card>
      ) : (
        <div className="space-y-3">
          <AnimatePresence mode="popLayout">
            {tasks.map((epic) => (
              <EpicRow
                key={epic.id}
                epic={epic}
                expanded={expandedEpics.has(epic.id)}
                onToggle={() => toggleEpic(epic.id)}
              />
            ))}
          </AnimatePresence>
        </div>
      )}
    </div>
  );
}

interface EpicRowProps {
  epic: TaskItem;
  expanded: boolean;
  onToggle: () => void;
}

function EpicRow({ epic, expanded, onToggle }: EpicRowProps) {
  const Icon = taskTypeIcons[epic.task_type] || CheckSquare;
  const hasChildren = epic.children && epic.children.length > 0;
  const childCount = epic.children?.length || epic.children_count || 0;
  const totalPoints = epic.children?.reduce((sum, c) => sum + (c.story_points || 0), 0) || 0;
  const donePoints = epic.children?.filter(c => c.status === 'done').reduce((sum, c) => sum + (c.story_points || 0), 0) || 0;
  const progress = totalPoints > 0 ? Math.round((donePoints / totalPoints) * 100) : 0;

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: -10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -10 }}
      className="group"
    >
      {/* Epic Header */}
      <div
        className={cn(
          'flex items-center gap-3 p-4 rounded-lg border bg-card transition-colors',
          'hover:border-primary/50 hover:bg-accent/50'
        )}
      >
        {hasChildren && (
          <Button
            variant="ghost"
            size="icon"
            className="h-6 w-6"
            onClick={onToggle}
          >
            {expanded ? (
              <ChevronDown className="h-4 w-4" />
            ) : (
              <ChevronRight className="h-4 w-4" />
            )}
          </Button>
        )}
        {!hasChildren && <div className="w-6" />}

        <div
          className={cn(
            'flex items-center justify-center w-8 h-8 rounded border',
            taskTypeColors[epic.task_type]
          )}
        >
          <Icon className="h-4 w-4" />
        </div>

        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className="font-medium truncate">{epic.title}</span>
            <Badge variant="outline" className="text-xs">
              {epic.task_type.toUpperCase()}
            </Badge>
          </div>
          {epic.description && (
            <p className="text-sm text-muted-foreground truncate mt-0.5">
              {epic.description}
            </p>
          )}
        </div>

        {/* Progress */}
        {hasChildren && (
          <div className="flex items-center gap-3">
            <div className="w-24">
              <Progress value={progress} className="h-2" />
            </div>
            <span className="text-xs text-muted-foreground w-12">
              {donePoints}/{totalPoints} pts
            </span>
          </div>
        )}

        {/* Story Points */}
        {epic.story_points && (
          <Badge variant="secondary" className="ml-2">
            {epic.story_points} pts
          </Badge>
        )}

        {/* Priority Indicator */}
        <span
          className={cn(
            'w-2 h-2 rounded-full',
            priorityColors[epic.priority]
          )}
          title={epic.priority}
        />

        {/* Child Count */}
        {hasChildren && (
          <span className="text-xs text-muted-foreground">
            {childCount} items
          </span>
        )}

        {/* Actions */}
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button
              variant="ghost"
              size="icon"
              className="h-8 w-8 opacity-0 group-hover:opacity-100"
            >
              <MoreHorizontal className="h-4 w-4" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuItem>Edit</DropdownMenuItem>
            <DropdownMenuItem>Add Story</DropdownMenuItem>
            <DropdownMenuItem className="text-destructive">Delete</DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>

      {/* Children (Stories/Tasks) */}
      <AnimatePresence>
        {expanded && hasChildren && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="ml-8 pl-4 border-l-2 border-muted mt-2 space-y-2"
          >
            {epic.children?.map((child) => (
              <TaskRow key={child.id} task={child} />
            ))}
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}

interface TaskRowProps {
  task: TaskItem;
}

function TaskRow({ task }: TaskRowProps) {
  const Icon = taskTypeIcons[task.task_type] || CheckSquare;

  return (
    <motion.div
      layout
      initial={{ opacity: 0, x: -10 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: -10 }}
      className={cn(
        'flex items-center gap-3 p-3 rounded-lg border bg-card/50 transition-colors group',
        'hover:border-primary/50 hover:bg-accent/50'
      )}
    >
      <GripVertical className="h-4 w-4 text-muted-foreground opacity-0 group-hover:opacity-100 cursor-grab" />

      <div
        className={cn(
          'flex items-center justify-center w-6 h-6 rounded border',
          taskTypeColors[task.task_type]
        )}
      >
        <Icon className="h-3 w-3" />
      </div>

      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium truncate">{task.title}</span>
          {task.status === 'blocked' && (
            <AlertCircle className="h-4 w-4 text-red-500" />
          )}
        </div>
        {task.description && (
          <p className="text-xs text-muted-foreground truncate mt-0.5">
            {task.description}
          </p>
        )}
      </div>

      {/* Labels */}
      {task.labels.length > 0 && (
        <div className="flex gap-1">
          {task.labels.slice(0, 2).map((label) => (
            <Badge key={label} variant="outline" className="text-xs">
              {label}
            </Badge>
          ))}
        </div>
      )}

      {/* Status Badge */}
      <Badge
        variant="secondary"
        className={cn(
          'text-xs capitalize',
          task.status === 'done' && 'bg-green-500/10 text-green-500',
          task.status === 'in_progress' && 'bg-yellow-500/10 text-yellow-500',
          task.status === 'blocked' && 'bg-red-500/10 text-red-500'
        )}
      >
        {task.status.replace('_', ' ')}
      </Badge>

      {/* Story Points */}
      {task.story_points && (
        <Badge variant="outline" className="text-xs">
          {task.story_points} pts
        </Badge>
      )}

      {/* Priority */}
      <span
        className={cn(
          'w-2 h-2 rounded-full',
          priorityColors[task.priority]
        )}
        title={task.priority}
      />

      {/* Actions */}
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button
            variant="ghost"
            size="icon"
            className="h-6 w-6 opacity-0 group-hover:opacity-100"
          >
            <MoreHorizontal className="h-4 w-4" />
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end">
          <DropdownMenuItem>Edit</DropdownMenuItem>
          <DropdownMenuItem>Move to Sprint</DropdownMenuItem>
          <DropdownMenuItem className="text-destructive">Delete</DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
    </motion.div>
  );
}

function BacklogSkeleton() {
  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        {[...Array(4)].map((_, i) => (
          <Card key={i}>
            <CardHeader className="pb-2">
              <Skeleton className="h-4 w-24" />
            </CardHeader>
            <CardContent>
              <Skeleton className="h-8 w-16 mb-2" />
              <Skeleton className="h-2 w-full" />
            </CardContent>
          </Card>
        ))}
      </div>

      <div className="space-y-3">
        {[...Array(3)].map((_, i) => (
          <Skeleton key={i} className="h-20 w-full rounded-lg" />
        ))}
      </div>
    </div>
  );
}
