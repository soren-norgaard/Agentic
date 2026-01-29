'use client';

import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import {
  Bot,
  FileCode,
  TestTube,
  Shield,
  Rocket,
  ChevronRight,
  CheckCircle2,
  Wrench,
} from 'lucide-react';
import { cn, formatDate } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import { ScrollArea } from '@/components/ui/scroll-area';

interface ActivityItem {
  id: string;
  agent: string;
  action: string;
  details: string;
  timestamp: Date;
  status: 'success' | 'info' | 'warning' | 'error';
}

const agentConfig: Record<string, { icon: React.ComponentType<{ className?: string }>; color: string }> = {
  orchestrator: { icon: Bot, color: 'bg-purple-500' },
  developer: { icon: FileCode, color: 'bg-green-500' },
  tester: { icon: TestTube, color: 'bg-blue-500' },
  security: { icon: Shield, color: 'bg-red-500' },
  devops: { icon: Rocket, color: 'bg-orange-500' },
  code_review: { icon: Wrench, color: 'bg-cyan-500' },
};

const mockActivity: ActivityItem[] = [
  {
    id: '1',
    agent: 'developer',
    action: 'Completed implementation',
    details: 'UserAuthService.ts - OAuth2 integration',
    timestamp: new Date(Date.now() - 5 * 60 * 1000),
    status: 'success',
  },
  {
    id: '2',
    agent: 'code_review',
    action: 'Reviewing code',
    details: 'Checking for security vulnerabilities',
    timestamp: new Date(Date.now() - 10 * 60 * 1000),
    status: 'info',
  },
  {
    id: '3',
    agent: 'tester',
    action: 'Generated test cases',
    details: '15 unit tests, 5 integration tests',
    timestamp: new Date(Date.now() - 20 * 60 * 1000),
    status: 'success',
  },
  {
    id: '4',
    agent: 'orchestrator',
    action: 'Delegated to developer',
    details: 'Story: Implement user authentication',
    timestamp: new Date(Date.now() - 30 * 60 * 1000),
    status: 'info',
  },
  {
    id: '5',
    agent: 'security',
    action: 'Scan complete',
    details: 'No vulnerabilities found',
    timestamp: new Date(Date.now() - 45 * 60 * 1000),
    status: 'success',
  },
];

interface AgentActivityFeedProps {
  compact?: boolean;
}

export function AgentActivityFeed({ compact = false }: AgentActivityFeedProps) {
  const activities = compact ? mockActivity.slice(0, 5) : mockActivity;

  return (
    <div className={cn('space-y-4', !compact && 'space-y-6')}>
      {!compact && (
        <div>
          <h1 className="text-3xl font-bold">Agent Activity</h1>
          <p className="text-muted-foreground">
            Real-time feed of agent actions and decisions
          </p>
        </div>
      )}

      <ScrollArea className={cn(compact ? 'h-[300px]' : 'h-[600px]')}>
        <div className="space-y-4 pr-4">
          {activities.map((activity, index) => (
            <ActivityCard key={activity.id} activity={activity} index={index} />
          ))}
        </div>
      </ScrollArea>

      {compact && (
        <Button variant="ghost" className="w-full">
          View All Activity
          <ChevronRight className="ml-2 h-4 w-4" />
        </Button>
      )}
    </div>
  );
}

interface ActivityCardProps {
  activity: ActivityItem;
  index: number;
}

function ActivityCard({ activity, index }: ActivityCardProps) {
  const agent = agentConfig[activity.agent] || agentConfig.orchestrator;
  const AgentIcon = agent.icon;
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.05 }}
      className="flex gap-3"
    >
      <Avatar className={cn('h-8 w-8 shrink-0', agent.color)}>
        <AvatarFallback className="bg-transparent text-white">
          <AgentIcon className="h-4 w-4" />
        </AvatarFallback>
      </Avatar>

      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className="font-medium capitalize">
            {activity.agent.replace('_', ' ')}
          </span>
          {activity.status === 'success' && (
            <CheckCircle2 className="h-4 w-4 text-green-500" />
          )}
          <span className="text-xs text-muted-foreground" suppressHydrationWarning>
            {mounted ? formatDate(activity.timestamp) : ''}
          </span>
        </div>
        <p className="text-sm">{activity.action}</p>
        <p className="text-sm text-muted-foreground truncate">
          {activity.details}
        </p>
      </div>
    </motion.div>
  );
}
