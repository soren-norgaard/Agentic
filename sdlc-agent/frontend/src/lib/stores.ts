import { create } from 'zustand';
import { devtools, persist } from 'zustand/middleware';
import type { Project, Workflow, Task, AgentExecution, HumanInput } from '@/lib/api';

interface WorkflowState {
  // Active workflow being viewed
  activeWorkflowId: string | null;
  setActiveWorkflowId: (id: string | null) => void;

  // Real-time agent activity
  agentActivities: AgentActivity[];
  addAgentActivity: (activity: AgentActivity) => void;
  clearAgentActivities: () => void;

  // Human input requests
  pendingInputs: HumanInput[];
  setPendingInputs: (inputs: HumanInput[]) => void;
  addPendingInput: (input: HumanInput) => void;
  removePendingInput: (inputId: string) => void;

  // Workflow progress
  workflowProgress: Record<string, WorkflowProgress>;
  setWorkflowProgress: (workflowId: string, progress: WorkflowProgress) => void;
}

export interface AgentActivity {
  id: string;
  workflowId: string;
  agentType: string;
  action: string;
  details: string;
  status: 'started' | 'running' | 'completed' | 'failed';
  timestamp: Date;
  duration?: number;
  tokensUsed?: number;
}

export interface WorkflowProgress {
  phase: string;
  completedTasks: number;
  totalTasks: number;
  currentAgent?: string;
  estimatedTimeRemaining?: number;
}

export const useWorkflowStore = create<WorkflowState>()(
  devtools(
    (set) => ({
      activeWorkflowId: null,
      setActiveWorkflowId: (id) => set({ activeWorkflowId: id }),

      agentActivities: [],
      addAgentActivity: (activity) =>
        set((state) => ({
          agentActivities: [activity, ...state.agentActivities].slice(0, 100),
        })),
      clearAgentActivities: () => set({ agentActivities: [] }),

      pendingInputs: [],
      setPendingInputs: (inputs) => set({ pendingInputs: inputs }),
      addPendingInput: (input) =>
        set((state) => ({
          pendingInputs: [...state.pendingInputs, input],
        })),
      removePendingInput: (inputId) =>
        set((state) => ({
          pendingInputs: state.pendingInputs.filter((i) => i.id !== inputId),
        })),

      workflowProgress: {},
      setWorkflowProgress: (workflowId, progress) =>
        set((state) => ({
          workflowProgress: {
            ...state.workflowProgress,
            [workflowId]: progress,
          },
        })),
    }),
    { name: 'workflow-store' }
  )
);

// UI State Store
interface UIState {
  sidebarCollapsed: boolean;
  toggleSidebar: () => void;

  activeView: 'dashboard' | 'projects' | 'workflows' | 'activity' | 'settings';
  setActiveView: (view: UIState['activeView']) => void;

  selectedProjectId: string | null;
  setSelectedProjectId: (id: string | null) => void;

  commandPaletteOpen: boolean;
  setCommandPaletteOpen: (open: boolean) => void;
}

export const useUIStore = create<UIState>()(
  devtools(
    persist(
      (set) => ({
        sidebarCollapsed: false,
        toggleSidebar: () =>
          set((state) => ({ sidebarCollapsed: !state.sidebarCollapsed })),

        activeView: 'dashboard',
        setActiveView: (view) => set({ activeView: view }),

        selectedProjectId: null,
        setSelectedProjectId: (id) => set({ selectedProjectId: id }),

        commandPaletteOpen: false,
        setCommandPaletteOpen: (open) => set({ commandPaletteOpen: open }),
      }),
      { name: 'ui-store' }
    ),
    { name: 'ui-store' }
  )
);

// Notifications Store
interface Notification {
  id: string;
  type: 'info' | 'success' | 'warning' | 'error';
  title: string;
  message?: string;
  timestamp: Date;
  read: boolean;
  actionUrl?: string;
}

interface NotificationState {
  notifications: Notification[];
  unreadCount: number;
  addNotification: (notification: Omit<Notification, 'id' | 'timestamp' | 'read'>) => void;
  markAsRead: (id: string) => void;
  markAllAsRead: () => void;
  removeNotification: (id: string) => void;
  clearAll: () => void;
}

export const useNotificationStore = create<NotificationState>()(
  devtools(
    (set, get) => ({
      notifications: [],
      unreadCount: 0,

      addNotification: (notification) => {
        const newNotification: Notification = {
          ...notification,
          id: crypto.randomUUID(),
          timestamp: new Date(),
          read: false,
        };
        set((state) => ({
          notifications: [newNotification, ...state.notifications].slice(0, 50),
          unreadCount: state.unreadCount + 1,
        }));
      },

      markAsRead: (id) =>
        set((state) => {
          const notification = state.notifications.find((n) => n.id === id);
          if (notification && !notification.read) {
            return {
              notifications: state.notifications.map((n) =>
                n.id === id ? { ...n, read: true } : n
              ),
              unreadCount: Math.max(0, state.unreadCount - 1),
            };
          }
          return state;
        }),

      markAllAsRead: () =>
        set((state) => ({
          notifications: state.notifications.map((n) => ({ ...n, read: true })),
          unreadCount: 0,
        })),

      removeNotification: (id) =>
        set((state) => {
          const notification = state.notifications.find((n) => n.id === id);
          return {
            notifications: state.notifications.filter((n) => n.id !== id),
            unreadCount: notification && !notification.read
              ? Math.max(0, state.unreadCount - 1)
              : state.unreadCount,
          };
        }),

      clearAll: () => set({ notifications: [], unreadCount: 0 }),
    }),
    { name: 'notification-store' }
  )
);
