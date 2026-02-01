'use client';

import { useState, useEffect, useCallback } from 'react';
import { motion, AnimatePresence, Reorder } from 'framer-motion';
import {
  BookOpen,
  CheckSquare,
  Bug,
  Zap,
  Layers,
  AlertCircle,
  Clock,
  MessageSquare,
  MoreHorizontal,
  Plus,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Skeleton } from '@/components/ui/skeleton';
import { api, TaskItem } from '@/lib/api';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { TaskDetailDialog } from './task-detail-dialog';
import { CreateTaskDialog } from './create-task-dialog';

interface KanbanBoardProps {
  projectId: string;
}

const COLUMNS = [
  { id: 'backlog', label: 'Backlog', color: 'bg-slate-500' },
  { id: 'todo', label: 'To Do', color: 'bg-blue-500' },
  { id: 'in_progress', label: 'In Progress', color: 'bg-yellow-500' },
  { id: 'in_review', label: 'In Review', color: 'bg-purple-500' },
  { id: 'done', label: 'Done', color: 'bg-green-500' },
] as const;

const taskTypeIcons = {
  epic: Layers,
  story: BookOpen,
  task: CheckSquare,
  bug: Bug,
  spike: Zap,
};

const taskTypeColors = {
  epic: 'text-purple-500 bg-purple-500/10',
  story: 'text-blue-500 bg-blue-500/10',
  task: 'text-green-500 bg-green-500/10',
  bug: 'text-red-500 bg-red-500/10',
  spike: 'text-yellow-500 bg-yellow-500/10',
};

const priorityColors = {
  critical: 'border-l-red-500',
  high: 'border-l-orange-500',
  medium: 'border-l-yellow-500',
  low: 'border-l-gray-400',
};

export function KanbanBoard({ projectId }: KanbanBoardProps) {
  const [tasks, setTasks] = useState<TaskItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [draggingTask, setDraggingTask] = useState<string | null>(null);
  const [selectedTask, setSelectedTask] = useState<TaskItem | null>(null);
  const [detailDialogOpen, setDetailDialogOpen] = useState(false);
  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  const [createDialogStatus, setCreateDialogStatus] = useState<string>('backlog');

  useEffect(() => {
    const fetchTasks = async () => {
      try {
        setLoading(true);
        // Get all non-epic tasks (stories and tasks only)
        const response = await api.tasks.list({
          project_id: projectId,
          page_size: 200,
        });
        // Filter to only show stories and tasks (not epics)
        const workItems = response.items.filter(
          (t) => t.task_type !== 'epic'
        );
        setTasks(workItems);
      } catch (error) {
        console.error('Failed to fetch tasks:', error);
      } finally {
        setLoading(false);
      }
    };

    if (projectId) {
      fetchTasks();
    }
  }, [projectId]);

  const getTasksByStatus = useCallback(
    (status: string) => {
      return tasks.filter((t) => t.status === status);
    },
    [tasks]
  );

  const handleTaskClick = (task: TaskItem) => {
    setSelectedTask(task);
    setDetailDialogOpen(true);
  };

  const handleAddTask = (status: string = 'backlog') => {
    setCreateDialogStatus(status);
    setCreateDialogOpen(true);
  };

  const handleTaskSaved = async () => {
    // Refresh tasks
    try {
      const response = await api.tasks.list({
        project_id: projectId,
        page_size: 200,
      });
      setTasks(response.items.filter((t) => t.task_type !== 'epic'));
    } catch (error) {
      console.error('Failed to refresh tasks:', error);
    }
  };

  const handleDragEnd = async (taskId: string, newStatus: string) => {
    setDraggingTask(null);
    
    // Optimistic update
    setTasks((prev) =>
      prev.map((t) =>
        t.id === taskId ? { ...t, status: newStatus as TaskItem['status'] } : t
      )
    );

    try {
      await api.tasks.move(taskId, newStatus);
    } catch (error) {
      console.error('Failed to move task:', error);
      // Revert on error
      const response = await api.tasks.list({
        project_id: projectId,
        page_size: 200,
      });
      setTasks(response.items.filter((t) => t.task_type !== 'epic'));
    }
  };

  if (loading) {
    return <KanbanSkeleton />;
  }

  const totalTasks = tasks.length;
  const doneTasks = tasks.filter((t) => t.status === 'done').length;
  const inProgressTasks = tasks.filter((t) => t.status === 'in_progress').length;

  return (
    <div className="h-full flex flex-col">
      {/* Header Stats */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-4">
          <h2 className="text-lg font-semibold">Sprint Board</h2>
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <span className="flex items-center gap-1">
              <div className="w-2 h-2 rounded-full bg-green-500" />
              {doneTasks} done
            </span>
            <span className="flex items-center gap-1">
              <div className="w-2 h-2 rounded-full bg-yellow-500" />
              {inProgressTasks} in progress
            </span>
            <span className="flex items-center gap-1">
              <div className="w-2 h-2 rounded-full bg-gray-400" />
              {totalTasks} total
            </span>
          </div>
        </div>

        <Button size="sm" onClick={() => handleAddTask('backlog')}>
          <Plus className="h-4 w-4 mr-1" />
          Add Task
        </Button>
      </div>

      {/* Kanban Columns */}
      <div className="flex-1 overflow-x-auto">
        <div className="flex gap-4 h-full min-w-max pb-4">
          {COLUMNS.map((column) => (
            <KanbanColumn
              key={column.id}
              column={column}
              tasks={getTasksByStatus(column.id)}
              draggingTask={draggingTask}
              onDragStart={setDraggingTask}
              onDrop={(taskId) => handleDragEnd(taskId, column.id)}
              onTaskClick={handleTaskClick}
              onAddTask={() => handleAddTask(column.id)}
            />
          ))}
        </div>
      </div>

      {/* Task Detail Dialog */}
      <TaskDetailDialog
        open={detailDialogOpen}
        onOpenChange={setDetailDialogOpen}
        task={selectedTask}
        onSave={handleTaskSaved}
      />

      {/* Create Task Dialog */}
      <CreateTaskDialog
        open={createDialogOpen}
        onOpenChange={setCreateDialogOpen}
        projectId={projectId}
        initialStatus={createDialogStatus}
        onSuccess={handleTaskSaved}
      />
    </div>
  );
}

interface KanbanColumnProps {
  column: (typeof COLUMNS)[number];
  tasks: TaskItem[];
  draggingTask: string | null;
  onDragStart: (taskId: string) => void;
  onDrop: (taskId: string) => void;
  onTaskClick: (task: TaskItem) => void;
  onAddTask: () => void;
}

function KanbanColumn({
  column,
  tasks,
  draggingTask,
  onDragStart,
  onDrop,
  onTaskClick,
  onAddTask,
}: KanbanColumnProps) {
  const [isOver, setIsOver] = useState(false);
  const totalPoints = tasks.reduce((sum, t) => sum + (t.story_points || 0), 0);

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsOver(true);
  };

  const handleDragLeave = () => {
    setIsOver(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsOver(false);
    const taskId = e.dataTransfer.getData('taskId');
    if (taskId) {
      onDrop(taskId);
    }
  };

  return (
    <div
      className={cn(
        'flex flex-col w-80 rounded-lg border bg-muted/30 transition-colors',
        isOver && 'border-primary bg-primary/5'
      )}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
    >
      {/* Column Header */}
      <div className="flex items-center justify-between p-3 border-b">
        <div className="flex items-center gap-2">
          <div className={cn('w-3 h-3 rounded-full', column.color)} />
          <span className="font-medium">{column.label}</span>
          <Badge variant="secondary" className="text-xs">
            {tasks.length}
          </Badge>
        </div>
        <div className="flex items-center gap-1 text-xs text-muted-foreground">
          {totalPoints > 0 && <span>{totalPoints} pts</span>}
          <Button variant="ghost" size="icon" className="h-6 w-6" onClick={onAddTask}>
            <Plus className="h-4 w-4" />
          </Button>
        </div>
      </div>

      {/* Tasks */}
      <ScrollArea className="flex-1 p-2">
        <div className="space-y-2">
          <AnimatePresence mode="popLayout">
            {tasks.map((task) => (
              <KanbanCard
                key={task.id}
                task={task}
                isDragging={draggingTask === task.id}
                onDragStart={() => onDragStart(task.id)}
                onTaskClick={() => onTaskClick(task)}
              />
            ))}
          </AnimatePresence>

          {tasks.length === 0 && (
            <div className="py-8 text-center text-sm text-muted-foreground">
              No items
            </div>
          )}
        </div>
      </ScrollArea>
    </div>
  );
}

interface KanbanCardProps {
  task: TaskItem;
  isDragging: boolean;
  onDragStart: () => void;
  onTaskClick: () => void;
}

function KanbanCard({ task, isDragging, onDragStart, onTaskClick }: KanbanCardProps) {
  const Icon = taskTypeIcons[task.task_type] || CheckSquare;

  const handleDragStart = (e: React.DragEvent) => {
    e.dataTransfer.setData('taskId', task.id);
    onDragStart();
  };

  return (
    <div
      draggable
      onDragStart={handleDragStart}
      className={cn(
        'rounded-lg border bg-card p-3 cursor-grab active:cursor-grabbing shadow-sm',
        'hover:shadow-md hover:border-primary/50 transition-all',
        'border-l-4',
        priorityColors[task.priority],
        isDragging && 'opacity-50 ring-2 ring-primary'
      )}
    >
      {/* Task Type & ID */}
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <div
            className={cn(
              'flex items-center justify-center w-5 h-5 rounded',
              taskTypeColors[task.task_type]
            )}
          >
            <Icon className="h-3 w-3" />
          </div>
          <span className="text-xs text-muted-foreground uppercase">
            {task.task_type}
          </span>
        </div>

        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" size="icon" className="h-6 w-6">
              <MoreHorizontal className="h-4 w-4" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuItem onClick={onTaskClick}>Edit</DropdownMenuItem>
            <DropdownMenuItem onClick={onTaskClick}>View Details</DropdownMenuItem>
            <DropdownMenuItem className="text-destructive">
              Delete
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>

      {/* Title */}
      <h4 className="font-medium text-sm mb-2 line-clamp-2">{task.title}</h4>

      {/* Description preview */}
      {task.description && (
        <p className="text-xs text-muted-foreground line-clamp-2 mb-3">
          {task.description}
        </p>
      )}

      {/* Labels */}
      {task.labels.length > 0 && (
        <div className="flex flex-wrap gap-1 mb-3">
          {task.labels.slice(0, 3).map((label) => (
            <Badge
              key={label}
              variant="outline"
              className="text-[10px] px-1 py-0"
            >
              {label.replace('skill:', '')}
            </Badge>
          ))}
          {task.labels.length > 3 && (
            <Badge variant="outline" className="text-[10px] px-1 py-0">
              +{task.labels.length - 3}
            </Badge>
          )}
        </div>
      )}

      {/* Footer */}
      <div className="flex items-center justify-between pt-2 border-t">
        <div className="flex items-center gap-2">
          {task.story_points && (
            <Badge variant="secondary" className="text-xs">
              {task.story_points} pts
            </Badge>
          )}
          {task.estimated_hours && (
            <span className="flex items-center gap-1 text-xs text-muted-foreground">
              <Clock className="h-3 w-3" />
              {task.estimated_hours}h
            </span>
          )}
        </div>

        <div className="flex items-center gap-1">
          {task.status === 'blocked' && (
            <AlertCircle className="h-4 w-4 text-red-500" />
          )}
          {task.acceptance_criteria?.length > 0 && (
            <span className="flex items-center gap-1 text-xs text-muted-foreground">
              <CheckSquare className="h-3 w-3" />
              {task.acceptance_criteria.length}
            </span>
          )}
        </div>
      </div>
    </div>
  );
}

function KanbanSkeleton() {
  return (
    <div className="h-full flex flex-col">
      <div className="flex items-center gap-4 mb-4">
        <Skeleton className="h-6 w-32" />
        <Skeleton className="h-4 w-48" />
      </div>

      <div className="flex gap-4 flex-1">
        {COLUMNS.map((column) => (
          <div
            key={column.id}
            className="flex flex-col w-80 rounded-lg border bg-muted/30"
          >
            <div className="p-3 border-b">
              <Skeleton className="h-5 w-24" />
            </div>
            <div className="p-2 space-y-2">
              {[...Array(3)].map((_, i) => (
                <Skeleton key={i} className="h-32 w-full rounded-lg" />
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
