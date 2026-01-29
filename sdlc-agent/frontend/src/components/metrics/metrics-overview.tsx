'use client';

import { useState, useEffect, useCallback } from 'react';
import { motion } from 'framer-motion';
import {
  Activity,
  Zap,
  Clock,
  DollarSign,
  TrendingUp,
  TrendingDown,
  Loader2,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { api, DashboardStats, MetricItem } from '@/lib/api';

interface MetricCardData {
  label: string;
  value: string;
  change: number;
  changeLabel: string;
  icon: React.ComponentType<{ className?: string }>;
  color: string;
}

const iconMap: Record<string, React.ComponentType<{ className?: string }>> = {
  'Active Workflows': Activity,
  'Workflows Completed': Zap,
  'Agent Executions': Clock,
  'LLM Tokens Used': DollarSign,
};

const colorMap: Record<string, string> = {
  'Active Workflows': 'text-green-500',
  'Workflows Completed': 'text-blue-500',
  'Agent Executions': 'text-purple-500',
  'LLM Tokens Used': 'text-orange-500',
};

function convertToMetricCard(metric: MetricItem): MetricCardData {
  return {
    label: metric.label,
    value: metric.value,
    change: metric.change,
    changeLabel: metric.change_label,
    icon: iconMap[metric.label] || Activity,
    color: colorMap[metric.label] || 'text-gray-500',
  };
}

export function MetricsOverview() {
  const [metrics, setMetrics] = useState<MetricCardData[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchMetrics = useCallback(async () => {
    try {
      const stats = await api.stats.dashboard();
      const metricCards: MetricCardData[] = [
        convertToMetricCard(stats.active_workflows),
        convertToMetricCard(stats.tasks_completed),
        convertToMetricCard(stats.avg_cycle_time),
        convertToMetricCard(stats.tokens_used),
      ];
      setMetrics(metricCards);
    } catch (error) {
      console.error('Failed to fetch metrics:', error);
      // Set default empty metrics on error
      setMetrics([
        { label: 'Active Workflows', value: '0', change: 0, changeLabel: 'vs last week', icon: Activity, color: 'text-green-500' },
        { label: 'Workflows Completed', value: '0', change: 0, changeLabel: 'this week', icon: Zap, color: 'text-blue-500' },
        { label: 'Agent Executions', value: '0', change: 0, changeLabel: 'total', icon: Clock, color: 'text-purple-500' },
        { label: 'LLM Tokens Used', value: '0', change: 0, changeLabel: 'total', icon: DollarSign, color: 'text-orange-500' },
      ]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchMetrics();
    // Refresh every 30 seconds
    const interval = setInterval(fetchMetrics, 30000);
    return () => clearInterval(interval);
  }, [fetchMetrics]);

  if (loading) {
    return (
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {[...Array(4)].map((_, i) => (
          <div key={i} className="rounded-lg border bg-card p-6 flex items-center justify-center">
            <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
          </div>
        ))}
      </div>
    );
  }

  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
      {metrics.map((metric, index) => (
        <MetricCardComponent key={metric.label} metric={metric} index={index} />
      ))}
    </div>
  );
}

interface MetricCardComponentProps {
  metric: MetricCardData;
  index: number;
}

function MetricCardComponent({ metric, index }: MetricCardComponentProps) {
  const Icon = metric.icon;
  const isPositive = metric.change >= 0;
  const TrendIcon = isPositive ? TrendingUp : TrendingDown;
  const showTrend = metric.change !== 0;

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
        {showTrend ? (
          <>
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
          </>
        ) : null}
        <span className="text-muted-foreground">{metric.changeLabel}</span>
      </div>
    </motion.div>
  );
}
