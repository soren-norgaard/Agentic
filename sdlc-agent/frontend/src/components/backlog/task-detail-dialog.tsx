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
  FileText,
  ChevronDown,
  ChevronRight,
  Sparkles,
  Code,
  FileCode,
  ClipboardList,
  TestTube,
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
import { ScrollArea } from '@/components/ui/scroll-area';
import { api, TaskItem, Artifact } from '@/lib/api';

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
  const [artifacts, setArtifacts] = useState<Artifact[]>([]);
  const [artifactsExpanded, setArtifactsExpanded] = useState(false);
  const [expandedArtifacts, setExpandedArtifacts] = useState<Set<string>>(new Set());
  const [loadingArtifacts, setLoadingArtifacts] = useState(false);
  const [generatingBrief, setGeneratingBrief] = useState(false);

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
      setArtifacts([]);
      setArtifactsExpanded(false);
      setExpandedArtifacts(new Set());
    }
  }, [task]);

  // Fetch all artifacts for this task
  useEffect(() => {
    const fetchArtifacts = async () => {
      if (!task) return;
      
      setLoadingArtifacts(true);
      try {
        const taskArtifacts = await api.tasks.getArtifacts(task.id);
        setArtifacts(taskArtifacts || []);
      } catch (err) {
        console.error('Failed to fetch artifacts:', err);
      } finally {
        setLoadingArtifacts(false);
      }
    };
    
    fetchArtifacts();
  }, [task]);

  const handleGenerateBrief = async () => {
    if (!task) return;
    
    setGeneratingBrief(true);
    setError(null);
    
    try {
      const result = await api.tasks.generateBrief(task.id);
      setSuccess(true);
      // Show message about workflow
      alert(`Developer brief generation started!\n\nWorkflow ID: ${result.workflow_id}\n\n${result.message}`);
      setTimeout(() => setSuccess(false), 2000);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to generate developer brief');
    } finally {
      setGeneratingBrief(false);
    }
  };

  const toggleArtifactExpanded = (artifactId: string) => {
    setExpandedArtifacts(prev => {
      const next = new Set(prev);
      if (next.has(artifactId)) {
        next.delete(artifactId);
      } else {
        next.add(artifactId);
      }
      return next;
    });
  };

  const getArtifactIcon = (type: string) => {
    switch (type) {
      case 'developer_brief':
        return FileText;
      case 'code':
        return Code;
      case 'architecture':
        return FileCode;
      case 'requirements':
        return ClipboardList;
      case 'test':
        return TestTube;
      default:
        return FileText;
    }
  };

  const getArtifactColor = (type: string) => {
    switch (type) {
      case 'developer_brief':
        return 'text-purple-500';
      case 'code':
        return 'text-green-500';
      case 'architecture':
        return 'text-blue-500';
      case 'requirements':
        return 'text-yellow-500';
      case 'test':
        return 'text-cyan-500';
      default:
        return 'text-gray-500';
    }
  };

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

          {/* Artifacts Section */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <button
                type="button"
                onClick={() => setArtifactsExpanded(!artifactsExpanded)}
                className="flex items-center gap-2 text-sm font-medium hover:text-primary transition-colors"
              >
                {artifactsExpanded ? (
                  <ChevronDown className="h-4 w-4" />
                ) : (
                  <ChevronRight className="h-4 w-4" />
                )}
                <FileText className="h-4 w-4 text-purple-500" />
                Artifacts ({artifacts.length})
                {loadingArtifacts && <Loader2 className="h-3 w-3 animate-spin" />}
              </button>
              <Button
                variant="outline"
                size="sm"
                onClick={handleGenerateBrief}
                disabled={generatingBrief}
                className="text-xs"
              >
                {generatingBrief ? (
                  <>
                    <Loader2 className="h-3 w-3 mr-1 animate-spin" />
                    Generating...
                  </>
                ) : (
                  <>
                    <Sparkles className="h-3 w-3 mr-1" />
                    Generate Brief
                  </>
                )}
              </Button>
            </div>
            
            {artifactsExpanded && (
              <Card className="border-purple-500/20">
                <CardContent className="pt-4">
                  {artifacts.length === 0 ? (
                    <p className="text-sm text-muted-foreground text-center py-4">
                      No artifacts yet. Click &quot;Generate Brief&quot; to create a developer brief.
                    </p>
                  ) : (
                    <div className="space-y-3">
                      {artifacts.map((artifact) => {
                        const ArtifactIcon = getArtifactIcon(artifact.artifact_type);
                        const isExpanded = expandedArtifacts.has(artifact.id);
                        return (
                          <div key={artifact.id} className="border rounded-lg overflow-hidden">
                            <button
                              type="button"
                              onClick={() => toggleArtifactExpanded(artifact.id)}
                              className="w-full flex items-center gap-2 p-3 text-left hover:bg-muted/50 transition-colors"
                            >
                              {isExpanded ? (
                                <ChevronDown className="h-4 w-4 shrink-0" />
                              ) : (
                                <ChevronRight className="h-4 w-4 shrink-0" />
                              )}
                              <ArtifactIcon className={cn('h-4 w-4 shrink-0', getArtifactColor(artifact.artifact_type))} />
                              <span className="flex-1 text-sm font-medium truncate">{artifact.name}</span>
                              <Badge variant="outline" className="text-xs">
                                {artifact.artifact_type.replace('_', ' ')}
                              </Badge>
                              <span className="text-xs text-muted-foreground">
                                v{artifact.version}
                              </span>
                            </button>
                            {isExpanded && artifact.content && (
                              <div className="border-t bg-muted/30">
                                <ScrollArea className="max-h-[300px]">
                                  <pre className="whitespace-pre-wrap text-xs font-sans p-4 overflow-x-auto">
                                    {artifact.content}
                                  </pre>
                                </ScrollArea>
                              </div>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  )}
                </CardContent>
              </Card>
            )}
          </div>

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
