'use client';

import { useState } from 'react';
import { motion } from 'framer-motion';
import {
  FolderKanban,
  MoreVertical,
  GitBranch,
  Clock,
  CheckCircle2,
  AlertCircle,
  Plus,
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

interface Project {
  id: string;
  name: string;
  description: string;
  status: 'active' | 'paused' | 'completed' | 'archived';
  repository?: string;
  workflowCount: number;
  lastActivity: string;
}

// Mock data
const mockProjects: Project[] = [
  {
    id: '1',
    name: 'E-Commerce Platform',
    description: 'Full-stack e-commerce application with payment processing',
    status: 'active',
    repository: 'github.com/org/ecommerce',
    workflowCount: 3,
    lastActivity: '2 hours ago',
  },
  {
    id: '2',
    name: 'Analytics Dashboard',
    description: 'Real-time analytics dashboard for business metrics',
    status: 'active',
    repository: 'github.com/org/analytics',
    workflowCount: 1,
    lastActivity: '5 hours ago',
  },
  {
    id: '3',
    name: 'API Gateway',
    description: 'Microservices API gateway with rate limiting',
    status: 'paused',
    workflowCount: 0,
    lastActivity: '2 days ago',
  },
];

const statusConfig = {
  active: { label: 'Active', color: 'bg-green-500', icon: CheckCircle2 },
  paused: { label: 'Paused', color: 'bg-yellow-500', icon: Clock },
  completed: { label: 'Completed', color: 'bg-blue-500', icon: CheckCircle2 },
  archived: { label: 'Archived', color: 'bg-gray-500', icon: AlertCircle },
};

export function ProjectList() {
  const [projects] = useState<Project[]>(mockProjects);
  const [createDialogOpen, setCreateDialogOpen] = useState(false);

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

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {projects.map((project, index) => (
          <ProjectCard key={project.id} project={project} index={index} />
        ))}
      </div>

      <CreateProjectDialog
        open={createDialogOpen}
        onOpenChange={setCreateDialogOpen}
      />
    </div>
  );
}

interface ProjectCardProps {
  project: Project;
  index: number;
}

function ProjectCard({ project, index }: ProjectCardProps) {
  const status = statusConfig[project.status];
  const StatusIcon = status.icon;

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.1 }}
      className="group relative overflow-hidden rounded-lg border bg-card p-6 transition-shadow hover:shadow-lg"
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
            <DropdownMenuItem>View Details</DropdownMenuItem>
            <DropdownMenuItem>Start Workflow</DropdownMenuItem>
            <DropdownMenuItem>Edit Settings</DropdownMenuItem>
            <DropdownMenuItem className="text-destructive">
              Archive Project
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
