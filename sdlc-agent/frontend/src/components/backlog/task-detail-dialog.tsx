'use client';

import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import {
  Save,
  Loader2,
  X,
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
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Separator } from '@/components/ui/separator';
import { api, TaskItem } from '@/lib/api';

interface TaskDetailDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  task: TaskItem | null;
  onSave?: (updatedTask: TaskItem) => void;
}

const taskTypeIcons = {
  epic: Layers,
  story: BookOpen,
  task: CheckSquare,
  bug: Bug,
  spike: Zap,
};

const taskTypeColors = {
  epic: 'bg-purple-500/10 text-purple-500 border-purple-500/30',
  story: 'bg-blue-500/10 text-blue-500 border-blue-500/30',
  task: 'bg-green-500/10 text-green-500 border-green-500/30',
  bug: 'bg-red-500/10 text-red-500 border-red-500/30',
  spike: 'bg-yellow-500/10 text-yellow-500 border-yellow-500/30',
};

const statusOptions = [
  { value: 'backlog', label: 'Backlog' },
  { value: 'todo', label: 'To Do' },
  { value: 'in_progress', label: 'In Progress' },
  { value: 'in_review', label: 'In Review' },
  { value: 'done', label: 'Done' },
  { value: 'blocked', label: 'Blocked' },
];

const priorityOptions = [
  { value: 'critical', label: 'Critical', color: 'bg-red-500' },
  { value: 'high', label: 'High', color: 'bg-orange-500' },
  { value: 'medium', label: 'Medium', color: 'bg-yellow-500' },
  { value: 'low', label: 'Low', color: 'bg-green-500' },
];

export function TaskDetailDialog({
  open,
  onOpenChange,
  task,
  onSave,
}: TaskDetailDialogProps) {
  const [formData, setFormData] = useState<Partial<TaskItem>>({});
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);
  const [hasChanges, setHasChanges] = useState(false);

  // Reset form when task changes
  useEffect(() => {
    if (task) {
      setFormData({
        title: task.title,
        description: task.description || '',
        status: task.status,
        priority: task.priority,
        story_points: task.story_points,
        estimated_hours: task.estimated_hours,
        technical_notes: task.technical_notes || '',
        labels: task.labels || [],
        acceptance_criteria: task.acceptance_criteria || [],
      });
      setError(null);
      setSuccess(false);
      setHasChanges(false);
    }
  }, [task]);

  const handleChange = (field: keyof TaskItem, value: unknown) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
    setHasChanges(true);
    setSuccess(false);
  };

  const handleSave = async () => {
    if (!task) return;

    setSaving(true);
    setError(null);

    try {
      const updatedTask = await api.tasks.update(task.id, formData);
      setSuccess(true);
      setHasChanges(false);
      onSave?.(updatedTask);
      setTimeout(() => setSuccess(false), 2000);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save changes');
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async () => {
    if (!task) return;
    if (!confirm(`Are you sure you want to delete "${task.title}"?`)) return;

    setSaving(true);
    setError(null);

    try {
      await api.tasks.delete(task.id);
      onOpenChange(false);
      onSave?.(task); // Trigger refresh
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete task');
      setSaving(false);
    }
  };

  if (!task) return null;

  const Icon = taskTypeIcons[task.task_type] || CheckSquare;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <div className="flex items-center gap-3">
            <div
              className={cn(
                'flex items-center justify-center w-10 h-10 rounded-lg border',
                taskTypeColors[task.task_type]
              )}
            >
              <Icon className="h-5 w-5" />
            </div>
            <div className="flex-1">
              <DialogTitle className="flex items-center gap-2">
                <Badge variant="outline" className="text-xs uppercase">
                  {task.task_type}
                </Badge>
                <span className="text-muted-foreground text-sm font-normal">
                  {task.id.slice(0, 8)}
                </span>
              </DialogTitle>
              <DialogDescription className="mt-1">
                Created {new Date(task.created_at).toLocaleDateString()} · Updated{' '}
                {new Date(task.updated_at).toLocaleDateString()}
              </DialogDescription>
            </div>
          </div>
        </DialogHeader>

        <div className="space-y-6 py-4">
          {/* Title */}
          <div className="space-y-2">
            <Label htmlFor="title">Title</Label>
            <Input
              id="title"
              value={formData.title || ''}
              onChange={(e) => handleChange('title', e.target.value)}
              placeholder="Task title"
            />
          </div>

          {/* Description */}
          <div className="space-y-2">
            <Label htmlFor="description">Description</Label>
            <Textarea
              id="description"
              value={formData.description || ''}
              onChange={(e) => handleChange('description', e.target.value)}
              placeholder="Detailed description of the task..."
              rows={4}
            />
          </div>

          {/* Status & Priority Row */}
          <div className="grid grid-cols-2 gap-4">
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
                        <span
                          className={cn('w-2 h-2 rounded-full', option.color)}
                        />
                        {option.label}
                      </div>
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>

          {/* Story Points & Estimated Hours */}
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="story_points">Story Points</Label>
              <Input
                id="story_points"
                type="number"
                min="0"
                value={formData.story_points || ''}
                onChange={(e) =>
                  handleChange(
                    'story_points',
                    e.target.value ? parseInt(e.target.value) : undefined
                  )
                }
                placeholder="e.g., 3"
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="estimated_hours">Estimated Hours</Label>
              <Input
                id="estimated_hours"
                type="number"
                min="0"
                step="0.5"
                value={formData.estimated_hours || ''}
                onChange={(e) =>
                  handleChange(
                    'estimated_hours',
                    e.target.value ? parseFloat(e.target.value) : undefined
                  )
                }
                placeholder="e.g., 4"
              />
            </div>
          </div>

          {/* Technical Notes */}
          <div className="space-y-2">
            <Label htmlFor="technical_notes">Technical Notes</Label>
            <Textarea
              id="technical_notes"
              value={formData.technical_notes || ''}
              onChange={(e) => handleChange('technical_notes', e.target.value)}
              placeholder="Implementation details, technical considerations..."
              rows={3}
            />
          </div>

          {/* Acceptance Criteria (Read-only for now) */}
          {task.acceptance_criteria && task.acceptance_criteria.length > 0 && (
            <div className="space-y-2">
              <Label>Acceptance Criteria</Label>
              <Card>
                <CardContent className="pt-4 space-y-3">
                  {task.acceptance_criteria.map((criterion, index) => (
                    <div
                      key={index}
                      className="text-sm bg-muted/50 rounded-lg p-3 space-y-1"
                    >
                      {criterion.Given && (
                        <p>
                          <span className="font-medium text-blue-400">Given</span>{' '}
                          {criterion.Given}
                        </p>
                      )}
                      {criterion.When && (
                        <p>
                          <span className="font-medium text-yellow-400">When</span>{' '}
                          {criterion.When}
                        </p>
                      )}
                      {criterion.Then && (
                        <p>
                          <span className="font-medium text-green-400">Then</span>{' '}
                          {criterion.Then}
                        </p>
                      )}
                    </div>
                  ))}
                </CardContent>
              </Card>
            </div>
          )}

          {/* Labels */}
          {task.labels && task.labels.length > 0 && (
            <div className="space-y-2">
              <Label>Labels</Label>
              <div className="flex flex-wrap gap-2">
                {task.labels.map((label) => (
                  <Badge key={label} variant="secondary">
                    {label}
                  </Badge>
                ))}
              </div>
            </div>
          )}

          {/* External ID (GitHub Issue) */}
          {task.external_id && (
            <div className="space-y-2">
              <Label>GitHub Issue</Label>
              <Badge variant="outline" className="text-muted-foreground">
                {task.external_id}
              </Badge>
            </div>
          )}
        </div>

        {/* Error/Success Messages */}
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

        {success && (
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            className="flex items-center gap-2 text-sm text-green-400 bg-green-500/10 border border-green-500/20 rounded-lg p-3"
          >
            <CheckCircle className="h-4 w-4" />
            Changes saved successfully!
          </motion.div>
        )}

        <Separator />

        <DialogFooter className="flex justify-between sm:justify-between">
          <Button
            variant="destructive"
            onClick={handleDelete}
            disabled={saving}
            className="opacity-70 hover:opacity-100"
          >
            Delete
          </Button>
          <div className="flex gap-2">
            <Button variant="outline" onClick={() => onOpenChange(false)}>
              {hasChanges ? 'Cancel' : 'Close'}
            </Button>
            <Button onClick={handleSave} disabled={saving || !hasChanges}>
              {saving ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Saving...
                </>
              ) : (
                <>
                  <Save className="h-4 w-4 mr-2" />
                  Save Changes
                </>
              )}
            </Button>
          </div>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
