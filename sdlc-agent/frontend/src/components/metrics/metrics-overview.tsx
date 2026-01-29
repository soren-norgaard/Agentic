'use client';

import { motion } from 'framer-motion';
import {
  Activity,
  Zap,
  Clock,
  DollarSign,
  TrendingUp,
  TrendingDown,
} from 'lucide-react';
import { cn } from '@/lib/utils';

interface MetricCard {
  label: string;
  value: string;
  change: number;
  changeLabel: string;
  icon: React.ComponentType<{ className?: string }>;
  color: string;
}

const metrics: MetricCard[] = [
  {
    label: 'Active Workflows',
    value: '12',
    change: 20,
    changeLabel: 'vs last week',
    icon: Activity,
    color: 'text-green-500',
  },
  {
    label: 'Tasks Completed',
    value: '248',
    change: 15,
    changeLabel: 'this week',
    icon: Zap,
    color: 'text-blue-500',
  },
  {
    label: 'Avg. Cycle Time',
    value: '2.4h',
    change: -12,
    changeLabel: 'faster',
    icon: Clock,
    color: 'text-purple-500',
  },
  {
    label: 'LLM Tokens Used',
    value: '1.2M',
    change: 8,
    changeLabel: 'vs last week',
    icon: DollarSign,
    color: 'text-orange-500',
  },
];

export function MetricsOverview() {
  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
      {metrics.map((metric, index) => (
        <MetricCardComponent key={metric.label} metric={metric} index={index} />
      ))}
    </div>
  );
}

interface MetricCardComponentProps {
  metric: MetricCard;
  index: number;
}

function MetricCardComponent({ metric, index }: MetricCardComponentProps) {
  const Icon = metric.icon;
  const isPositive = metric.change >= 0;
  const TrendIcon = isPositive ? TrendingUp : TrendingDown;

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.1 }}
      className="rounded-lg border bg-card p-6"
    >
      <div className="flex items-center justify-between">
        <span className="text-sm font-medium text-muted-foreground">
          {metric.label}
        </span>
        <Icon className={cn('h-5 w-5', metric.color)} />
      </div>

      <div className="mt-2">
        <span className="text-3xl font-bold">{metric.value}</span>
      </div>

      <div className="mt-2 flex items-center gap-1 text-sm">
        <TrendIcon
          className={cn(
            'h-4 w-4',
            isPositive ? 'text-green-500' : 'text-red-500'
          )}
        />
        <span
          className={cn(
            'font-medium',
            isPositive ? 'text-green-500' : 'text-red-500'
          )}
        >
          {Math.abs(metric.change)}%
        </span>
        <span className="text-muted-foreground">{metric.changeLabel}</span>
      </div>
    </motion.div>
  );
}
