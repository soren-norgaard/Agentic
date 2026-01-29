'use client';

import { useEffect, useRef, useCallback } from 'react';
import { io, Socket } from 'socket.io-client';
import { useWorkflowStore, useNotificationStore, type AgentActivity } from '@/lib/stores';

const WEBSOCKET_URL = process.env.NEXT_PUBLIC_WS_URL || 'http://localhost:8000';

interface ServerToClientEvents {
  'agent:started': (data: AgentEventData) => void;
  'agent:progress': (data: AgentEventData) => void;
  'agent:completed': (data: AgentEventData) => void;
  'agent:failed': (data: AgentEventData) => void;
  'workflow:status': (data: WorkflowStatusData) => void;
  'human_input:required': (data: HumanInputData) => void;
  'task:updated': (data: TaskUpdateData) => void;
  'notification': (data: NotificationData) => void;
}

interface ClientToServerEvents {
  'subscribe:workflow': (workflowId: string) => void;
  'unsubscribe:workflow': (workflowId: string) => void;
  'subscribe:project': (projectId: string) => void;
  'unsubscribe:project': (projectId: string) => void;
}

interface AgentEventData {
  workflowId: string;
  agentType: string;
  action: string;
  details: string;
  tokensUsed?: number;
  duration?: number;
}

interface WorkflowStatusData {
  workflowId: string;
  status: string;
  phase: string;
  progress: {
    completedTasks: number;
    totalTasks: number;
  };
}

interface HumanInputData {
  id: string;
  workflowId: string;
  taskId?: string;
  agentType: string;
  prompt: string;
  inputType: 'approval' | 'choice' | 'text' | 'review' | 'escalation';
  options?: string[];
  timeoutAt?: string;
}

interface TaskUpdateData {
  workflowId: string;
  taskId: string;
  status: string;
  assignedAgent?: string;
}

interface NotificationData {
  type: 'info' | 'success' | 'warning' | 'error';
  title: string;
  message?: string;
  actionUrl?: string;
}

export function useWebSocket() {
  const socketRef = useRef<Socket<ServerToClientEvents, ClientToServerEvents> | null>(null);
  const { addAgentActivity, setWorkflowProgress, addPendingInput } = useWorkflowStore();
  const { addNotification } = useNotificationStore();

  useEffect(() => {
    const socket: Socket<ServerToClientEvents, ClientToServerEvents> = io(WEBSOCKET_URL, {
      transports: ['websocket'],
      autoConnect: true,
      reconnection: true,
      reconnectionAttempts: 5,
      reconnectionDelay: 1000,
    });

    socketRef.current = socket;

    socket.on('connect', () => {
      console.log('WebSocket connected');
    });

    socket.on('disconnect', () => {
      console.log('WebSocket disconnected');
    });

    // Agent events
    socket.on('agent:started', (data) => {
      const activity: AgentActivity = {
        id: crypto.randomUUID(),
        workflowId: data.workflowId,
        agentType: data.agentType,
        action: data.action,
        details: data.details,
        status: 'started',
        timestamp: new Date(),
      };
      addAgentActivity(activity);
    });

    socket.on('agent:progress', (data) => {
      const activity: AgentActivity = {
        id: crypto.randomUUID(),
        workflowId: data.workflowId,
        agentType: data.agentType,
        action: data.action,
        details: data.details,
        status: 'running',
        timestamp: new Date(),
        tokensUsed: data.tokensUsed,
      };
      addAgentActivity(activity);
    });

    socket.on('agent:completed', (data) => {
      const activity: AgentActivity = {
        id: crypto.randomUUID(),
        workflowId: data.workflowId,
        agentType: data.agentType,
        action: data.action,
        details: data.details,
        status: 'completed',
        timestamp: new Date(),
        duration: data.duration,
        tokensUsed: data.tokensUsed,
      };
      addAgentActivity(activity);
    });

    socket.on('agent:failed', (data) => {
      const activity: AgentActivity = {
        id: crypto.randomUUID(),
        workflowId: data.workflowId,
        agentType: data.agentType,
        action: data.action,
        details: data.details,
        status: 'failed',
        timestamp: new Date(),
      };
      addAgentActivity(activity);

      addNotification({
        type: 'error',
        title: `${data.agentType} agent failed`,
        message: data.details,
      });
    });

    // Workflow status updates
    socket.on('workflow:status', (data) => {
      setWorkflowProgress(data.workflowId, {
        phase: data.phase,
        completedTasks: data.progress.completedTasks,
        totalTasks: data.progress.totalTasks,
      });
    });

    // Human input required
    socket.on('human_input:required', (data) => {
      addPendingInput({
        id: data.id,
        workflow_id: data.workflowId,
        task_id: data.taskId,
        agent_type: data.agentType,
        prompt: data.prompt,
        input_type: data.inputType,
        options: data.options,
        timeout_at: data.timeoutAt,
        created_at: new Date().toISOString(),
      });

      addNotification({
        type: 'warning',
        title: 'Human input required',
        message: data.prompt,
      });
    });

    // General notifications
    socket.on('notification', (data) => {
      addNotification(data);
    });

    return () => {
      socket.disconnect();
    };
  }, [addAgentActivity, setWorkflowProgress, addPendingInput, addNotification]);

  const subscribeToWorkflow = useCallback((workflowId: string) => {
    socketRef.current?.emit('subscribe:workflow', workflowId);
  }, []);

  const unsubscribeFromWorkflow = useCallback((workflowId: string) => {
    socketRef.current?.emit('unsubscribe:workflow', workflowId);
  }, []);

  const subscribeToProject = useCallback((projectId: string) => {
    socketRef.current?.emit('subscribe:project', projectId);
  }, []);

  const unsubscribeFromProject = useCallback((projectId: string) => {
    socketRef.current?.emit('unsubscribe:project', projectId);
  }, []);

  return {
    subscribeToWorkflow,
    unsubscribeFromWorkflow,
    subscribeToProject,
    unsubscribeFromProject,
  };
}
