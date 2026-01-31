'use client';

import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  LayoutDashboard,
  FolderKanban,
  GitBranch,
  Activity,
  Settings,
  Moon,
  Sun,
  Bell,
  Search,
  Plus,
  ChevronRight,
  Layers,
  Kanban,
  Home,
  Info,
} from 'lucide-react';
import { useTheme } from 'next-themes';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { Separator } from '@/components/ui/separator';
import { ProjectList } from '@/components/projects/project-list';
import { WorkflowPanel } from '@/components/workflows/workflow-panel';
import { AgentActivityFeed } from '@/components/agents/activity-feed';
import { MetricsOverview } from '@/components/metrics/metrics-overview';
import { CreateProjectDialog } from '@/components/projects/create-project-dialog';
import { BacklogView } from '@/components/backlog/backlog-view';
import { KanbanBoard } from '@/components/backlog/kanban-board';
import { LLMSettings } from '@/components/settings/llm-settings';
import { WorkflowSettings } from '@/components/settings/workflow-settings';
import { GitHubSettings } from '@/components/settings/github-settings';
import { api } from '@/lib/api';

type NavItem = 'dashboard' | 'projects' | 'backlog' | 'board' | 'workflows' | 'activity' | 'settings';

interface NavItemConfig {
  id: NavItem;
  label: string;
  icon: React.ComponentType<{ className?: string }>;
}

const navItems: NavItemConfig[] = [
  { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { id: 'projects', label: 'Projects', icon: FolderKanban },
  { id: 'backlog', label: 'Backlog', icon: Layers },
  { id: 'board', label: 'Board', icon: Kanban },
  { id: 'workflows', label: 'Workflows', icon: GitBranch },
  { id: 'activity', label: 'Activity', icon: Activity },
  { id: 'settings', label: 'Settings', icon: Settings },
];

// Wrapper for BacklogView with project selector
function BacklogViewWrapper({ projectId, onProjectChange }: { projectId: string; onProjectChange: (id: string) => void }) {
  const [projects, setProjects] = useState<Array<{ id: string; name: string }>>([]);
  
  useEffect(() => {
    api.projects.list(0, 50).then(res => {
      setProjects(res.items.map(p => ({ id: p.id, name: p.name })));
      // Auto-select first project if none selected
      if (!projectId && res.items.length > 0) {
        onProjectChange(res.items[0].id);
      }
    });
  }, []);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Product Backlog</h1>
          <p className="text-muted-foreground">Manage epics, stories, and tasks</p>
        </div>
        <select 
          value={projectId} 
          onChange={(e) => onProjectChange(e.target.value)}
          className="px-3 py-2 border rounded-md bg-background"
        >
          <option value="">Select a project...</option>
          {projects.map(p => (
            <option key={p.id} value={p.id}>{p.name}</option>
          ))}
        </select>
      </div>
      {projectId ? (
        <BacklogView projectId={projectId} />
      ) : (
        <div className="flex flex-col items-center justify-center py-12 text-center">
          <Layers className="h-12 w-12 text-muted-foreground mb-4" />
          <p className="text-muted-foreground">Select a project to view its backlog</p>
        </div>
      )}
    </div>
  );
}

// Wrapper for Board/KanbanBoard with project selector  
function BoardViewWrapper({ projectId, onProjectChange }: { projectId: string; onProjectChange: (id: string) => void }) {
  const [projects, setProjects] = useState<Array<{ id: string; name: string }>>([]);
  
  useEffect(() => {
    api.projects.list(0, 50).then(res => {
      setProjects(res.items.map(p => ({ id: p.id, name: p.name })));
      if (!projectId && res.items.length > 0) {
        onProjectChange(res.items[0].id);
      }
    });
  }, []);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Sprint Board</h1>
          <p className="text-muted-foreground">Track work in progress</p>
        </div>
        <select 
          value={projectId} 
          onChange={(e) => onProjectChange(e.target.value)}
          className="px-3 py-2 border rounded-md bg-background"
        >
          <option value="">Select a project...</option>
          {projects.map(p => (
            <option key={p.id} value={p.id}>{p.name}</option>
          ))}
        </select>
      </div>
      {projectId ? (
        <KanbanBoard projectId={projectId} />
      ) : (
        <div className="flex flex-col items-center justify-center py-12 text-center">
          <Kanban className="h-12 w-12 text-muted-foreground mb-4" />
          <p className="text-muted-foreground">Select a project to view its board</p>
        </div>
      )}
    </div>
  );
}

// No project selected state
function NoProjectSelected({ onNavigate }: { onNavigate: () => void }) {
  return (
    <div className="flex h-full flex-col items-center justify-center gap-6">
      <div className="rounded-full bg-muted p-6">
        <FolderKanban className="h-12 w-12 text-muted-foreground" />
      </div>
      <div className="text-center">
        <h2 className="text-xl font-semibold">No Project Selected</h2>
        <p className="mt-2 text-muted-foreground">
          Select a project to view the backlog and board
        </p>
      </div>
      <Button onClick={onNavigate}>
        <FolderKanban className="mr-2 h-4 w-4" />
        Browse Projects
      </Button>
    </div>
  );
}

interface DashboardProps {
  onShowLanding?: () => void;
}

export function Dashboard({ onShowLanding }: DashboardProps) {
  const [activeNav, setActiveNav] = useState<NavItem>('dashboard');
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [createProjectOpen, setCreateProjectOpen] = useState(false);
  const [selectedProjectId, setSelectedProjectId] = useState<string | null>(null);
  const { theme, setTheme } = useTheme();

  const handleShowLanding = () => {
    localStorage.removeItem('sdlc-agent-visited');
    onShowLanding?.();
  };

  return (
    <div className="flex h-screen bg-background">
      {/* Sidebar */}
      <motion.aside
        initial={false}
        animate={{ width: sidebarCollapsed ? 64 : 240 }}
        className="flex flex-col border-r bg-card"
      >
        {/* Logo */}
        <div className="flex h-16 items-center justify-between px-4">
          <AnimatePresence mode="wait">
            {!sidebarCollapsed && (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="flex items-center gap-2"
              >
                <button 
                  onClick={handleShowLanding}
                  className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary text-primary-foreground hover:opacity-80 transition-opacity"
                  title="View Introduction"
                >
                  <GitBranch className="h-5 w-5" />
                </button>
                <span className="font-semibold">SDLC Agent</span>
              </motion.div>
            )}
          </AnimatePresence>
          <Button
            variant="ghost"
            size="icon"
            onClick={() => setSidebarCollapsed(!sidebarCollapsed)}
          >
            <ChevronRight
              className={cn(
                'h-4 w-4 transition-transform',
                sidebarCollapsed && 'rotate-180'
              )}
            />
          </Button>
        </div>

        <Separator />

        {/* Navigation */}
        <nav className="flex-1 p-2">
          <ul className="space-y-1">
            {navItems.map((item) => {
              const Icon = item.icon;
              const isActive = activeNav === item.id;

              return (
                <li key={item.id}>
                  <Button
                    variant={isActive ? 'secondary' : 'ghost'}
                    className={cn(
                      'w-full justify-start',
                      sidebarCollapsed && 'justify-center px-2'
                    )}
                    onClick={() => setActiveNav(item.id)}
                  >
                    <Icon className="h-5 w-5 shrink-0" />
                    <AnimatePresence mode="wait">
                      {!sidebarCollapsed && (
                        <motion.span
                          initial={{ opacity: 0, width: 0 }}
                          animate={{ opacity: 1, width: 'auto' }}
                          exit={{ opacity: 0, width: 0 }}
                          className="ml-3 overflow-hidden"
                        >
                          {item.label}
                        </motion.span>
                      )}
                    </AnimatePresence>
                  </Button>
                </li>
              );
            })}
          </ul>
        </nav>

        {/* Theme Toggle */}
        <div className="p-2">
          <Button
            variant="ghost"
            className={cn(
              'w-full justify-start',
              sidebarCollapsed && 'justify-center px-2'
            )}
            onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
          >
            {theme === 'dark' ? (
              <Sun className="h-5 w-5" />
            ) : (
              <Moon className="h-5 w-5" />
            )}
            <AnimatePresence mode="wait">
              {!sidebarCollapsed && (
                <motion.span
                  initial={{ opacity: 0, width: 0 }}
                  animate={{ opacity: 1, width: 'auto' }}
                  exit={{ opacity: 0, width: 0 }}
                  className="ml-3 overflow-hidden"
                >
                  {theme === 'dark' ? 'Light Mode' : 'Dark Mode'}
                </motion.span>
              )}
            </AnimatePresence>
          </Button>
        </div>
      </motion.aside>

      {/* Main Content */}
      <div className="flex flex-1 flex-col overflow-hidden">
        {/* Top Bar */}
        <header className="flex h-16 items-center justify-between border-b px-6">
          <div className="flex items-center gap-4">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <Input
                placeholder="Search projects, workflows..."
                className="w-80 pl-10"
              />
            </div>
          </div>

          <div className="flex items-center gap-4">
            <Button variant="default" size="sm" onClick={() => setCreateProjectOpen(true)}>
              <Plus className="mr-2 h-4 w-4" />
              New Project
            </Button>

            <Button variant="ghost" size="icon" className="relative">
              <Bell className="h-5 w-5" />
              <span className="absolute right-1 top-1 h-2 w-2 rounded-full bg-destructive" />
            </Button>

            <Separator orientation="vertical" className="h-8" />

            <Avatar>
              <AvatarImage src="/avatar.png" alt="User" />
              <AvatarFallback>U</AvatarFallback>
            </Avatar>
          </div>
        </header>

        {/* Page Content */}
        <main className="flex-1 overflow-auto p-6">
          <AnimatePresence mode="wait">
            <motion.div
              key={activeNav}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              transition={{ duration: 0.2 }}
              className="h-full"
            >
              {activeNav === 'dashboard' && <DashboardView onNavigate={setActiveNav} onSelectProject={setSelectedProjectId} />}
              {activeNav === 'projects' && <ProjectList onSelectProject={(id) => { setSelectedProjectId(id); setActiveNav('backlog'); }} />}
              {activeNav === 'backlog' && <BacklogViewWrapper projectId={selectedProjectId || ''} onProjectChange={setSelectedProjectId} />}
              {activeNav === 'board' && <BoardViewWrapper projectId={selectedProjectId || ''} onProjectChange={setSelectedProjectId} />}
              {activeNav === 'workflows' && <WorkflowPanel />}
              {activeNav === 'activity' && <AgentActivityFeed />}
              {activeNav === 'settings' && <SettingsView />}
            </motion.div>
          </AnimatePresence>
        </main>
      </div>

      {/* Create Project Dialog */}
      <CreateProjectDialog
        open={createProjectOpen}
        onOpenChange={setCreateProjectOpen}
      />
    </div>
  );
}

interface DashboardViewProps {
  onNavigate: (nav: NavItem) => void;
  onSelectProject: (id: string) => void;
}

function DashboardView({ onNavigate, onSelectProject }: DashboardViewProps) {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Dashboard</h1>
        <p className="text-muted-foreground">
          Overview of your SDLC automation system
        </p>
      </div>

      {/* Metrics */}
      <MetricsOverview />

      {/* Two Column Layout */}
      <div className="grid gap-6 lg:grid-cols-2">
        {/* Active Workflows */}
        <div className="rounded-lg border bg-card p-6">
          <h2 className="mb-4 text-lg font-semibold">Active Workflows</h2>
          <WorkflowPanel compact onNavigate={(nav) => onNavigate(nav as NavItem)} />
        </div>

        {/* Recent Activity */}
        <div className="rounded-lg border bg-card p-6">
          <h2 className="mb-4 text-lg font-semibold">Recent Activity</h2>
          <AgentActivityFeed compact onNavigate={(nav) => onNavigate(nav as NavItem)} />
        </div>
      </div>
    </div>
  );
}

function SettingsView() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Settings</h1>
        <p className="text-muted-foreground">
          Configure your SDLC Agent system
        </p>
      </div>

      <div className="grid gap-6 md:grid-cols-2">
        <LLMSettings />
        <WorkflowSettings />
        <GitHubSettings />
      </div>
    </div>
  );
}
