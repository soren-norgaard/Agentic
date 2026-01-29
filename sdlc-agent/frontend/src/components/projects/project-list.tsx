'use client';

import { useState, useEffect, useCallback } from 'react';
import { motion } from 'framer-motion';
import {
  FolderKanban,
  MoreVertical,
  GitBranch,
  Clock,
  CheckCircle2,
  AlertCircle,
  Plus,
  Loader2,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { CreateProjectDialog } from '@/components/projects/create-project-dialog';
import { api, Project as ApiProject } from '@/lib/api';

interface Project {
  id: string;
  name: string;
  description: string;
  status: 'active' | 'paused' | 'completed' | 'archived' | 'draft';
  repository?: string;
  workflowCount: number;
  lastActivity: string;
}

const statusConfig = {
  draft: { label: 'Draft', color: 'bg-gray-400', icon: Clock },
  active: { label: 'Active', color: 'bg-green-500', icon: CheckCircle2 },
  paused: { label: 'Paused', color: 'bg-yellow-500', icon: Clock },
  completed: { label: 'Completed', color: 'bg-blue-500', icon: CheckCircle2 },
  archived: { label: 'Archived', color: 'bg-gray-500', icon: AlertCircle },
};

function formatRelativeTime(dateStr: string): string {
  const date = new Date(dateStr);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMins / 60);
  const diffDays = Math.floor(diffHours / 24);
  
  if (diffMins < 1) return 'just now';
  if (diffMins < 60) return `${diffMins} minutes ago`;
  if (diffHours < 24) return `${diffHours} hours ago`;
  if (diffDays < 7) return `${diffDays} days ago`;
  return date.toLocaleDateString();
}

export function ProjectList({ onSelectProject }: { onSelectProject?: (id: string) => void }) {
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [createDialogOpen, setCreateDialogOpen] = useState(false);

  const fetchProjects = useCallback(async () => {
    try {
      setLoading(true);
      const response = await api.projects.list(0, 50);
      const mappedProjects: Project[] = response.items.map((p: ApiProject) => ({
        id: p.id,
        name: p.name,
        description: p.description || '',
        status: p.status as Project['status'],
        repository: p.repository_url || undefined,
        workflowCount: 0, // TODO: get from API
        lastActivity: formatRelativeTime(p.updated_at),
      }));
      setProjects(mappedProjects);
    } catch (error) {
      console.error('Failed to fetch projects:', error);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchProjects();
  }, [fetchProjects]);

  const handleProjectCreated = () => {
    fetchProjects();
  };

  const handleDeleteProject = async (projectId: string) => {
    try {
      await api.projects.delete(projectId);
      fetchProjects();
    } catch (error) {
      console.error('Failed to delete project:', error);
    }
  };

  const handleArchiveProject = async (projectId: string) => {
    try {
      await api.projects.update(projectId, { status: 'archived' });
      fetchProjects();
    } catch (error) {
      console.error('Failed to archive project:', error);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Projects</h1>
          <p className="text-muted-foreground">
            Manage your software development projects
          </p>
        </div>
        <Button onClick={() => setCreateDialogOpen(true)}>
          <Plus className="mr-2 h-4 w-4" />
          New Project
        </Button>
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        </div>
      ) : projects.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-12 text-center">
          <FolderKanban className="h-12 w-12 text-muted-foreground mb-4" />
          <h3 className="text-lg font-semibold">No projects yet</h3>
          <p className="text-muted-foreground mb-4">
            Create your first project to get started
          </p>
          <Button onClick={() => setCreateDialogOpen(true)}>
            <Plus className="mr-2 h-4 w-4" />
            New Project
          </Button>
        </div>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {projects.map((project, index) => (
            <ProjectCard 
              key={project.id} 
              project={project} 
              index={index}
              onDelete={handleDeleteProject}
              onArchive={handleArchiveProject}
              onSelect={onSelectProject}
            />
          ))}
        </div>
      )}

      <CreateProjectDialog
        open={createDialogOpen}
        onOpenChange={setCreateDialogOpen}
        onSuccess={handleProjectCreated}
      />
    </div>
  );
}

interface ProjectCardProps {
  project: Project;
  index: number;
  onDelete: (id: string) => void;
  onArchive: (id: string) => void;
  onSelect?: (id: string) => void;
}

function ProjectCard({ project, index, onDelete, onArchive, onSelect }: ProjectCardProps) {
  const status = statusConfig[project.status];
  const StatusIcon = status.icon;

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.1 }}
      className="group relative overflow-hidden rounded-lg border bg-card p-6 transition-shadow hover:shadow-lg cursor-pointer"
      onClick={() => onSelect?.(project.id)}
    >
      {/* Status indicator */}
      <div
        className={cn('absolute left-0 top-0 h-1 w-full', status.color)}
        aria-hidden
      />

      <div className="flex items-start justify-between">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10">
            <FolderKanban className="h-5 w-5 text-primary" />
          </div>
          <div>
            <h3 className="font-semibold">{project.name}</h3>
            <Badge variant="outline" className="mt-1">
              <StatusIcon className="mr-1 h-3 w-3" />
              {status.label}
            </Badge>
          </div>
        </div>

        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button
              variant="ghost"
              size="icon"
              className="opacity-0 transition-opacity group-hover:opacity-100"
            >
              <MoreVertical className="h-4 w-4" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuItem onClick={() => window.alert(`View details for ${project.name}`)}>
              View Details
            </DropdownMenuItem>
            <DropdownMenuItem onClick={() => window.alert(`Start workflow for ${project.name}`)}>
              Start Workflow
            </DropdownMenuItem>
            <DropdownMenuItem onClick={() => onArchive(project.id)}>
              Archive Project
            </DropdownMenuItem>
            <DropdownMenuItem 
              className="text-destructive"
              onClick={() => onDelete(project.id)}
            >
              Delete Project
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>

      <p className="mt-4 line-clamp-2 text-sm text-muted-foreground">
        {project.description}
      </p>

      <div className="mt-4 flex items-center gap-4 text-sm text-muted-foreground">
        {project.repository && (
          <div className="flex items-center gap-1">
            <GitBranch className="h-4 w-4" />
            <span className="truncate">{project.repository}</span>
          </div>
        )}
      </div>

      <div className="mt-4 flex items-center justify-between border-t pt-4 text-sm">
        <span className="text-muted-foreground">
          {project.workflowCount} workflow{project.workflowCount !== 1 && 's'}
        </span>
        <span className="text-muted-foreground">{project.lastActivity}</span>
      </div>
    </motion.div>
  );
}
