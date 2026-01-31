'use client';

import { useState, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  MessageSquare,
  Bell,
  Clock,
  ChevronRight,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { api, HumanInput } from '@/lib/api';
import { HumanInputDialog } from './human-input-dialog';

interface HumanInputBannerProps {
  workflowId: string;
  workflowName?: string;
  workflowStatus?: string;
  onInputSubmitted?: () => void;
}

function formatTimeAgo(dateStr: string): string {
  const date = new Date(dateStr);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMins / 60);
  const diffDays = Math.floor(diffHours / 24);

  if (diffDays > 0) return `${diffDays}d ago`;
  if (diffHours > 0) return `${diffHours}h ago`;
  if (diffMins > 0) return `${diffMins}m ago`;
  return 'Just now';
}

export function HumanInputBanner({
  workflowId,
  workflowName,
  workflowStatus,
  onInputSubmitted,
}: HumanInputBannerProps) {
  const [pendingInputs, setPendingInputs] = useState<HumanInput[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedInput, setSelectedInput] = useState<HumanInput | null>(null);
  const [dialogOpen, setDialogOpen] = useState(false);

  const fetchInputs = useCallback(async () => {
    try {
      const response = await api.workflows.getInputs(workflowId);
      // Filter to only show unresolved inputs
      const unresolvedInputs = response.items.filter((input) => !input.is_resolved);
      setPendingInputs(unresolvedInputs);
    } catch (error) {
      console.error('Failed to fetch pending inputs:', error);
    } finally {
      setLoading(false);
    }
  }, [workflowId]);

  useEffect(() => {
    fetchInputs();
  }, [fetchInputs]);

  // Poll for inputs when workflow is awaiting input
  useEffect(() => {
    if (workflowStatus !== 'awaiting_input') return;
    const interval = setInterval(fetchInputs, 5000);
    return () => clearInterval(interval);
  }, [workflowStatus, fetchInputs]);

  const handleInputClick = (input: HumanInput) => {
    setSelectedInput(input);
    setDialogOpen(true);
  };

  const handleInputSubmitted = () => {
    fetchInputs();
    onInputSubmitted?.();
  };

  if (loading) {
    return null; // Don't show anything while loading
  }

  if (pendingInputs.length === 0) {
    return null;
  }

  return (
    <>
      <AnimatePresence>
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -10 }}
        >
          <Card className="border-blue-500/50 bg-blue-500/5">
            <CardHeader className="pb-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <div className="relative">
                    <Bell className="h-5 w-5 text-blue-500" />
                    <span className="absolute -top-1 -right-1 flex h-4 w-4 items-center justify-center rounded-full bg-blue-500 text-[10px] font-bold text-white">
                      {pendingInputs.length}
                    </span>
                  </div>
                  <CardTitle className="text-base">Human Input Required</CardTitle>
                </div>
                <Badge variant="outline" className="text-blue-500 border-blue-500/50">
                  Awaiting Response
                </Badge>
              </div>
              <CardDescription className="mt-1">
                This workflow needs your input to continue processing
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-2">
              {pendingInputs.map((input, index) => (
                <motion.button
                  key={input.id}
                  initial={{ opacity: 0, x: -10 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: index * 0.05 }}
                  onClick={() => handleInputClick(input)}
                  className={cn(
                    'w-full flex items-center gap-3 p-3 rounded-lg border bg-card',
                    'hover:bg-accent hover:border-blue-500/50 transition-all text-left'
                  )}
                >
                  <div className="p-2 rounded-full bg-blue-500/10">
                    <MessageSquare className="h-4 w-4 text-blue-500" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="font-medium text-sm capitalize">
                        {input.request_type.replace('_', ' ')}
                      </span>
                      {input.context?.phase && (
                        <Badge variant="secondary" className="text-xs">
                          {input.context.phase}
                        </Badge>
                      )}
                    </div>
                    <p className="text-xs text-muted-foreground truncate mt-0.5">
                      {input.prompt.substring(0, 100)}...
                    </p>
                  </div>
                  <div className="flex items-center gap-2 shrink-0">
                    <span className="text-xs text-muted-foreground flex items-center gap-1">
                      <Clock className="h-3 w-3" />
                      {formatTimeAgo(input.requested_at)}
                    </span>
                    <ChevronRight className="h-4 w-4 text-muted-foreground" />
                  </div>
                </motion.button>
              ))}
            </CardContent>
          </Card>
        </motion.div>
      </AnimatePresence>

      <HumanInputDialog
        open={dialogOpen}
        onOpenChange={setDialogOpen}
        input={selectedInput}
        workflowName={workflowName}
        onSubmit={handleInputSubmitted}
      />
    </>
  );
}

// Compact version for workflow cards in the list
interface HumanInputIndicatorProps {
  workflowId: string;
  workflowName?: string;
  onOpenInput?: (input: HumanInput) => void;
}

export function HumanInputIndicator({
  workflowId,
  workflowName,
  onOpenInput,
}: HumanInputIndicatorProps) {
  const [hasInputs, setHasInputs] = useState(false);
  const [inputCount, setInputCount] = useState(0);
  const [loading, setLoading] = useState(true);
  const [pendingInputs, setPendingInputs] = useState<HumanInput[]>([]);

  const fetchInputs = useCallback(async () => {
    try {
      const response = await api.workflows.getInputs(workflowId);
      const unresolvedInputs = response.items.filter((input) => !input.is_resolved);
      setPendingInputs(unresolvedInputs);
      setHasInputs(unresolvedInputs.length > 0);
      setInputCount(unresolvedInputs.length);
    } catch (error) {
      console.error('Failed to fetch inputs:', error);
    } finally {
      setLoading(false);
    }
  }, [workflowId]);

  useEffect(() => {
    fetchInputs();
  }, [fetchInputs]);

  const handleClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (pendingInputs.length > 0) {
      onOpenInput?.(pendingInputs[0]);
    }
  };

  if (loading || !hasInputs) {
    return null;
  }

  return (
    <motion.button
      initial={{ opacity: 0, scale: 0.9 }}
      animate={{ opacity: 1, scale: 1 }}
      whileHover={{ scale: 1.05 }}
      onClick={handleClick}
      className={cn(
        'flex items-center gap-1.5 px-2.5 py-1 rounded-full',
        'bg-blue-500/10 text-blue-500 hover:bg-blue-500/20',
        'transition-colors text-xs font-medium'
      )}
    >
      <Bell className="h-3 w-3" />
      <span>Input needed</span>
      {inputCount > 1 && (
        <Badge variant="secondary" className="h-4 px-1 text-[10px]">
          {inputCount}
        </Badge>
      )}
    </motion.button>
  );
}
