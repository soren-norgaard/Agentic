'use client';

import { useState } from 'react';
import { motion } from 'framer-motion';
import {
  Save,
  Loader2,
  CheckCircle,
  AlertCircle,
  Layers,
  BookOpen,
  CheckSquare,
  Bug,
  Zap,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';
import { Label } from '@/components/ui/label';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { api } from '@/lib/api';

interface CreateTaskDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  projectId: string;
  initialStatus?: string;
  onSuccess?: () => void;
}

const taskTypeOptions = [
  { value: 'task', label: 'Task', icon: CheckSquare, color: 'text-green-500' },
  { value: 'story', label: 'Story', icon: BookOpen, color: 'text-blue-500' },
  { value: 'bug', label: 'Bug', icon: Bug, color: 'text-red-500' },
  { value: 'spike', label: 'Spike', icon: Zap, color: 'text-yellow-500' },
];

const statusOptions = [
  { value: 'backlog', label: 'Backlog' },
  { value: 'todo', label: 'To Do' },
  { value: 'in_progress', label: 'In Progress' },
  { value: 'in_review', label: 'In Review' },
  { value: 'done', label: 'Done' },
];

const priorityOptions = [
  { value: 'critical', label: 'Critical', color: 'bg-red-500' },
  { value: 'high', label: 'High', color: 'bg-orange-500' },
  { value: 'medium', label: 'Medium', color: 'bg-yellow-500' },
  { value: 'low', label: 'Low', color: 'bg-green-500' },
];

export function CreateTaskDialog({
  open,
  onOpenChange,
  projectId,
  initialStatus = 'backlog',
  onSuccess,
}: CreateTaskDialogProps) {
  const [formData, setFormData] = useState({
    title: '',
    description: '',
    task_type: 'task' as 'task' | 'story' | 'bug' | 'spike',
    status: initialStatus,
    priority: 'medium',
    story_points: undefined as number | undefined,
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const resetForm = () => {
    setFormData({
      title: '',
      description: '',
      task_type: 'task',
      status: initialStatus,
      priority: 'medium',
      story_points: undefined,
    });
    setError(null);
  };

  const handleChange = (field: string, value: unknown) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
  };

  const handleCreate = async () => {
    if (!formData.title.trim()) {
      setError('Title is required');
      return;
    }

    setSaving(true);
    setError(null);

    try {
      await api.tasks.create({
        project_id: projectId,
        title: formData.title.trim(),
        description: formData.description.trim() || undefined,
        task_type: formData.task_type,
        status: formData.status,
        priority: formData.priority,
        story_points: formData.story_points,
      });
      
      resetForm();
      onOpenChange(false);
      onSuccess?.();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create task');
    } finally {
      setSaving(false);
    }
  };

  const handleOpenChange = (newOpen: boolean) => {
    if (!newOpen) {
      resetForm();
    }
    onOpenChange(newOpen);
  };

  const TaskTypeIcon = taskTypeOptions.find(t => t.value === formData.task_type)?.icon || CheckSquare;

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <TaskTypeIcon className={cn('h-5 w-5', taskTypeOptions.find(t => t.value === formData.task_type)?.color)} />
            Create New Task
          </DialogTitle>
          <DialogDescription>
            Add a new task to the sprint board.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-4">
          {/* Title */}
          <div className="space-y-2">
            <Label htmlFor="title">Title *</Label>
            <Input
              id="title"
              value={formData.title}
              onChange={(e) => handleChange('title', e.target.value)}
              placeholder="What needs to be done?"
              autoFocus
            />
          </div>

          {/* Description */}
          <div className="space-y-2">
            <Label htmlFor="description">Description</Label>
            <Textarea
              id="description"
              value={formData.description}
              onChange={(e) => handleChange('description', e.target.value)}
              placeholder="Add more details about this task..."
              rows={3}
            />
          </div>

          {/* Type & Status Row */}
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="task_type">Type</Label>
              <Select
                value={formData.task_type}
                onValueChange={(value) => handleChange('task_type', value)}
              >
                <SelectTrigger id="task_type">
                  <SelectValue placeholder="Select type" />
                </SelectTrigger>
                <SelectContent>
                  {taskTypeOptions.map((option) => (
                    <SelectItem key={option.value} value={option.value}>
                      <div className="flex items-center gap-2">
                        <option.icon className={cn('h-4 w-4', option.color)} />
                        {option.label}
                      </div>
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label htmlFor="status">Status</Label>
              <Select
                value={formData.status}
                onValueChange={(value) => handleChange('status', value)}
              >
                <SelectTrigger id="status">
                  <SelectValue placeholder="Select status" />
                </SelectTrigger>
                <SelectContent>
                  {statusOptions.map((option) => (
                    <SelectItem key={option.value} value={option.value}>
                      {option.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>

          {/* Priority & Story Points Row */}
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="priority">Priority</Label>
              <Select
                value={formData.priority}
                onValueChange={(value) => handleChange('priority', value)}
              >
                <SelectTrigger id="priority">
                  <SelectValue placeholder="Select priority" />
                </SelectTrigger>
                <SelectContent>
                  {priorityOptions.map((option) => (
                    <SelectItem key={option.value} value={option.value}>
                      <div className="flex items-center gap-2">
                        <span className={cn('w-2 h-2 rounded-full', option.color)} />
                        {option.label}
                      </div>
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label htmlFor="story_points">Story Points</Label>
              <Input
                id="story_points"
                type="number"
                min="0"
                max="100"
                value={formData.story_points ?? ''}
                onChange={(e) =>
                  handleChange(
                    'story_points',
                    e.target.value ? parseInt(e.target.value) : undefined
                  )
                }
                placeholder="e.g., 3"
              />
            </div>
          </div>
        </div>

        {/* Error Message */}
        {error && (
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            className="flex items-center gap-2 text-sm text-red-400 bg-red-500/10 border border-red-500/20 rounded-lg p-3"
          >
            <AlertCircle className="h-4 w-4" />
            {error}
          </motion.div>
        )}

        <DialogFooter>
          <Button variant="outline" onClick={() => handleOpenChange(false)}>
            Cancel
          </Button>
          <Button onClick={handleCreate} disabled={saving || !formData.title.trim()}>
            {saving ? (
              <>
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                Creating...
              </>
            ) : (
              <>
                <CheckSquare className="h-4 w-4 mr-2" />
                Create Task
              </>
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
