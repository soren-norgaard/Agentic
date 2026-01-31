'use client';

import { useState, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Play,
  Pause,
  CheckCircle2,
  XCircle,
  Loader2,
  Clock,
  ArrowRight,
  ChevronDown,
  ChevronRight,
  Bot,
  Cpu,
  FileCode,
  Shield,
  TestTube,
  Rocket,
  Eye,
  MessageSquare,
  Zap,
  AlertCircle,
  RefreshCw,
  FileText,
  Activity,
  PlayCircle,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { api, Workflow, AgentExecution } from '@/lib/api';
import { HumanInputBanner } from './human-input-banner';
import { RequirementsView } from './requirements-view';
import { DeveloperBriefsView } from './developer-briefs-view';
import { ReviewBriefsView } from './review-briefs-view';
import { useToast } from '@/hooks/use-toast';

// Agent configuration
const agentConfig: Record<string, { icon: typeof Bot; color: string; bgColor: string; label: string }> = {
  orchestrator: { icon: Cpu, color: 'text-purple-500', bgColor: 'bg-purple-500/10', label: 'Orchestrator' },
  requirements: { icon: FileCode, color: 'text-blue-500', bgColor: 'bg-blue-500/10', label: 'Requirements' },
  planning: { icon: Clock, color: 'text-cyan-500', bgColor: 'bg-cyan-500/10', label: 'Planning' },
  development: { icon: Zap, color: 'text-green-500', bgColor: 'bg-green-500/10', label: 'Development' },
  code_review: { icon: Eye, color: 'text-yellow-500', bgColor: 'bg-yellow-500/10', label: 'Code Review' },
  testing: { icon: TestTube, color: 'text-orange-500', bgColor: 'bg-orange-500/10', label: 'Testing' },
  security: { icon: Shield, color: 'text-red-500', bgColor: 'bg-red-500/10', label: 'Security' },
  deployment: { icon: Rocket, color: 'text-indigo-500', bgColor: 'bg-indigo-500/10', label: 'Deployment' },
};

const phaseOrder = ['requirements', 'planning', 'development', 'code_review', 'testing', 'security', 'deployment'];

interface WorkflowExecutionViewProps {
  workflowId: string;
  onClose?: () => void;
}

export function WorkflowExecutionView({ workflowId, onClose }: WorkflowExecutionViewProps) {
  const [workflow, setWorkflow] = useState<Workflow | null>(null);
  const [executions, setExecutions] = useState<AgentExecution[]>([]);
  const [loading, setLoading] = useState(true);
  const [expandedAgent, setExpandedAgent] = useState<string | null>(null);
  const [continuing, setContinuing] = useState(false);
  const [pollingPaused, setPollingPaused] = useState(false);
  const [maxIterations, setMaxIterations] = useState<number>(100);
  const [activeTab, setActiveTab] = useState<string>('execution');
  const { toast } = useToast();

  const fetchData = useCallback(async () => {
    try {
      const [wf, execs] = await Promise.all([
        api.workflows.get(workflowId),
        api.workflows.getExecutions(workflowId),
      ]);
      setWorkflow(wf);
      // Sort by started_at ascending (oldest first)
      const sorted = [...execs].sort((a, b) => 
        new Date(a.started_at).getTime() - new Date(b.started_at).getTime()
      );
      setExecutions(sorted);
    } catch (error) {
      console.error('Failed to fetch workflow data:', error);
    } finally {
      setLoading(false);
    }
  }, [workflowId]);

  useEffect(() => {
    fetchData();
    // Fetch max iterations setting
    api.settings.getWorkflowConfig().then(config => {
      setMaxIterations(config.max_iterations);
    }).catch(() => {
      // Use default if fetch fails
      setMaxIterations(100);
    });
  }, [fetchData]);

  // Poll for updates when workflow is running (pause when user toggles)
  useEffect(() => {
    if (workflow?.status !== 'running' || pollingPaused) return;
    const interval = setInterval(fetchData, 5000);
    return () => clearInterval(interval);
  }, [workflow?.status, fetchData, pollingPaused]);

  // Get current/active agent
  const activeExecution = executions.find(e => !e.completed_at);
  const currentPhase = activeExecution?.agent_type || 
    (executions.length > 0 ? executions[executions.length - 1]?.agent_type : 'requirements');

  // Calculate progress
  const completedPhases = new Set(executions.filter(e => e.success).map(e => e.agent_type));
  const progressPercent = (completedPhases.size / phaseOrder.length) * 100;

  // Format duration
  const formatDuration = (startedAt: string, completedAt?: string) => {
    const start = new Date(startedAt);
    const end = completedAt ? new Date(completedAt) : new Date();
    const diffMs = end.getTime() - start.getTime();
    const diffSecs = Math.floor(diffMs / 1000);
    const mins = Math.floor(diffSecs / 60);
    const secs = diffSecs % 60;
    if (mins > 0) return `${mins}m ${secs}s`;
    return `${secs}s`;
  };

  // Format timestamp
  const formatTime = (timestamp: string) => {
    return new Date(timestamp).toLocaleTimeString('en-US', { 
      hour: 'numeric', 
      minute: '2-digit',
      second: '2-digit'
    });
  };

  // Get tokens and iterations from workflow state (primary) or executions (fallback)
  const executionTokens = executions.reduce((sum, e) => sum + (e.tokens_used || 0), 0);
  const executionIterations = executions.reduce((sum, e) => sum + (e.iterations || 0), 0);
  
  // Prefer workflow.current_state values as they're more accurate
  const totalTokens = (workflow?.current_state?.tokens_used as number) || executionTokens || 0;
  const currentIteration = (workflow?.current_state?.iteration_count as number) || executionIterations || 0;

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (!workflow) {
    return (
      <div className="flex items-center justify-center h-96 text-muted-foreground">
        Workflow not found
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h2 className="text-2xl font-bold flex items-center gap-3">
            {workflow.status === 'running' && (
              <span className="relative flex h-3 w-3">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75"></span>
                <span className="relative inline-flex rounded-full h-3 w-3 bg-green-500"></span>
              </span>
            )}
            {workflow.name}
          </h2>
          <p className="text-muted-foreground mt-1">
            Started {workflow.started_at ? formatTime(workflow.started_at) : 'Not started'}
            {workflow.started_at && ` • Duration: ${formatDuration(workflow.started_at, workflow.completed_at || undefined)}`}
          </p>
        </div>
        <div className="flex items-center gap-2">
          {/* Polling control - only show when running */}
          {workflow.status === 'running' && (
            <>
              <Button
                variant="outline"
                size="sm"
                onClick={() => setPollingPaused(!pollingPaused)}
                className="gap-1.5"
              >
                {pollingPaused ? (
                  <>
                    <Play className="h-3.5 w-3.5" />
                    Resume Updates
                  </>
                ) : (
                  <>
                    <Pause className="h-3.5 w-3.5" />
                    Pause Updates
                  </>
                )}
              </Button>
              {pollingPaused && (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={fetchData}
                  className="gap-1.5"
                >
                  <RefreshCw className="h-3.5 w-3.5" />
                  Refresh
                </Button>
              )}
            </>
          )}
          
          <Badge variant={workflow.status === 'running' ? 'default' : workflow.status === 'completed' ? 'outline' : 'destructive'}>
            {workflow.status}{pollingPaused && workflow.status === 'running' ? ' (paused)' : ''}
          </Badge>
          
          {/* Continue Workflow Button - show when completed or paused */}
          {(workflow.status === 'completed' || workflow.status === 'paused') && (
            <Button
              variant="default"
              size="sm"
              disabled={continuing}
              onClick={async () => {
                setContinuing(true);
                try {
                  // Determine next phase based on completed phases
                  const phases = ['requirements', 'planning', 'development', 'code_review', 'testing', 'security', 'deployment'];
                  const completedPhasesList = Array.from(completedPhases);
                  let nextPhase = 'development';
                  
                  for (const phase of phases) {
                    if (!completedPhasesList.includes(phase)) {
                      nextPhase = phase;
                      break;
                    }
                  }

                  await api.workflows.continue(workflowId, nextPhase);
                  toast({
                    title: 'Workflow Continued',
                    description: `Continuing to ${nextPhase} phase...`,
                  });
                  fetchData();
                } catch (error) {
                  console.error('Failed to continue workflow:', error);
                  toast({
                    title: 'Failed to continue',
                    description: 'Could not continue workflow. Please try again.',
                    variant: 'destructive',
                  });
                } finally {
                  setContinuing(false);
                }
              }}
            >
              {continuing ? (
                <>
                  <Loader2 className="h-4 w-4 mr-1 animate-spin" />
                  Continuing...
                </>
              ) : (
                <>
                  <PlayCircle className="h-4 w-4 mr-1" />
                  Continue Workflow
                </>
              )}
            </Button>
          )}
          
          {/* Retry Button - show when failed */}
          {workflow.status === 'failed' && (
            <Button
              variant="default"
              size="sm"
              disabled={continuing}
              onClick={async () => {
                setContinuing(true);
                try {
                  await api.workflows.action(workflowId, 'retry');
                  toast({
                    title: 'Workflow Retrying',
                    description: 'Workflow has been restarted.',
                  });
                  fetchData();
                } catch (error) {
                  console.error('Failed to retry workflow:', error);
                  toast({
                    title: 'Failed to retry',
                    description: 'Could not retry workflow. Please try again.',
                    variant: 'destructive',
                  });
                } finally {
                  setContinuing(false);
                }
              }}
            >
              {continuing ? (
                <>
                  <Loader2 className="h-4 w-4 mr-1 animate-spin" />
                  Retrying...
                </>
              ) : (
                <>
                  <RefreshCw className="h-4 w-4 mr-1" />
                  Retry Workflow
                </>
              )}
            </Button>
          )}
          
          <Button variant="ghost" size="sm" onClick={fetchData}>
            <RefreshCw className="h-4 w-4" />
          </Button>
        </div>
      </div>

      {/* Human Input Banner - show when awaiting input */}
      {workflow.status === 'awaiting_input' && (
        <HumanInputBanner
          workflowId={workflowId}
          workflowName={workflow.name}
          workflowStatus={workflow.status}
          onInputSubmitted={fetchData}
        />
      )}

      {/* Phase Progress Bar */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex items-center justify-between mb-4">
            <span className="text-sm font-medium">Phase Progress</span>
            <div className="flex items-center gap-4">
              {workflow?.status === 'running' && (
                <span className="text-sm text-blue-500 font-medium">
                  Iteration {currentIteration}/{maxIterations}
                </span>
              )}
              <span className="text-sm text-muted-foreground">
                {totalTokens.toLocaleString()} tokens used
              </span>
            </div>
          </div>
          <div className="flex items-center gap-1">
            {phaseOrder.map((phase, index) => {
              const config = agentConfig[phase] || { icon: Bot, color: 'text-gray-500', bgColor: 'bg-gray-500/10', label: phase };
              const Icon = config.icon;
              const isCompleted = completedPhases.has(phase);
              const isCurrent = currentPhase === phase;
              const hasExecution = executions.some(e => e.agent_type === phase);
              const hasFailed = executions.some(e => e.agent_type === phase && e.success === false);

              return (
                <div key={phase} className="flex items-center flex-1">
                  <div className={cn(
                    "flex items-center justify-center w-10 h-10 rounded-full transition-all",
                    isCompleted && !hasFailed && "bg-green-500 text-white",
                    hasFailed && "bg-red-500 text-white",
                    isCurrent && !isCompleted && !hasFailed && "bg-blue-500 text-white animate-pulse",
                    !isCompleted && !isCurrent && hasExecution && "bg-gray-200 dark:bg-gray-700",
                    !hasExecution && "bg-gray-100 dark:bg-gray-800 text-gray-400"
                  )}>
                    {isCompleted && !hasFailed ? (
                      <CheckCircle2 className="h-5 w-5" />
                    ) : hasFailed ? (
                      <XCircle className="h-5 w-5" />
                    ) : isCurrent ? (
                      <Loader2 className="h-5 w-5 animate-spin" />
                    ) : (
                      <Icon className="h-5 w-5" />
                    )}
                  </div>
                  {index < phaseOrder.length - 1 && (
                    <div className={cn(
                      "flex-1 h-1 mx-1 rounded transition-colors",
                      isCompleted ? "bg-green-500" : "bg-gray-200 dark:bg-gray-700"
                    )} />
                  )}
                </div>
              );
            })}
          </div>
          <div className="flex justify-between mt-2">
            {phaseOrder.map((phase) => {
              const config = agentConfig[phase];
              return (
                <span key={phase} className="text-xs text-muted-foreground text-center flex-1">
                  {config?.label || phase}
                </span>
              );
            })}
          </div>
        </CardContent>
      </Card>

      {/* Tabs for different views */}
      <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
        <TabsList className="grid w-full grid-cols-4">
          <TabsTrigger value="execution" className="flex items-center gap-2">
            <Activity className="h-4 w-4" />
            Agent Execution
          </TabsTrigger>
          <TabsTrigger value="requirements" className="flex items-center gap-2">
            <FileText className="h-4 w-4" />
            Requirements & Traceability
          </TabsTrigger>
          <TabsTrigger value="developer-briefs" className="flex items-center gap-2">
            <Rocket className="h-4 w-4" />
            Developer Briefs
          </TabsTrigger>
          <TabsTrigger value="review-briefs" className="flex items-center gap-2">
            <Eye className="h-4 w-4" />
            Review Briefs
          </TabsTrigger>
        </TabsList>

        <TabsContent value="execution" className="mt-4">
          {/* Agent Execution Timeline */}
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Agent Execution Timeline</CardTitle>
            </CardHeader>
            <CardContent>
              <ScrollArea className="h-[400px] pr-4">
                <div className="space-y-4">
              <AnimatePresence>
                {executions.map((execution, index) => {
                  const config = agentConfig[execution.agent_type] || { 
                    icon: Bot, 
                    color: 'text-gray-500', 
                    bgColor: 'bg-gray-500/10',
                    label: execution.agent_name 
                  };
                  const Icon = config.icon;
                  const isActive = !execution.completed_at;
                  const isExpanded = expandedAgent === execution.id;
                  const isSuccess = execution.success === true;
                  const isFailed = execution.success === false;

                  return (
                    <motion.div
                      key={execution.id}
                      initial={{ opacity: 0, x: -20 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ delay: index * 0.05 }}
                      className="relative"
                    >
                      {/* Connection line */}
                      {index < executions.length - 1 && (
                        <div className="absolute left-5 top-12 w-0.5 h-[calc(100%-24px)] bg-gray-200 dark:bg-gray-700" />
                      )}

                      <div 
                        className={cn(
                          "flex items-start gap-4 p-4 rounded-lg border transition-all cursor-pointer hover:bg-muted/50",
                          isActive && "border-blue-500 bg-blue-500/5",
                          isSuccess && "border-green-500/30",
                          isFailed && "border-red-500/30 bg-red-500/5"
                        )}
                        onClick={() => setExpandedAgent(isExpanded ? null : execution.id)}
                      >
                        {/* Agent Icon */}
                        <div className={cn(
                          "flex items-center justify-center w-10 h-10 rounded-full shrink-0",
                          config.bgColor,
                          isActive && "animate-pulse"
                        )}>
                          {isActive ? (
                            <Loader2 className={cn("h-5 w-5 animate-spin", config.color)} />
                          ) : isSuccess ? (
                            <CheckCircle2 className="h-5 w-5 text-green-500" />
                          ) : isFailed ? (
                            <XCircle className="h-5 w-5 text-red-500" />
                          ) : (
                            <Icon className={cn("h-5 w-5", config.color)} />
                          )}
                        </div>

                        {/* Content */}
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center justify-between">
                            <div className="flex items-center gap-2">
                              <span className="font-medium">{execution.agent_name}</span>
                              {isActive && (
                                <Badge variant="default" className="animate-pulse">
                                  Running
                                </Badge>
                              )}
                              {isSuccess && (
                                <Badge variant="outline" className="text-green-600 border-green-600">
                                  Completed
                                </Badge>
                              )}
                              {isFailed && (
                                <Badge variant="destructive">
                                  Failed
                                </Badge>
                              )}
                            </div>
                            <div className="flex items-center gap-2 text-sm text-muted-foreground">
                              <span>{formatTime(execution.started_at)}</span>
                              {execution.completed_at && (
                                <>
                                  <ArrowRight className="h-3 w-3" />
                                  <span>{formatDuration(execution.started_at, execution.completed_at)}</span>
                                </>
                              )}
                              {isExpanded ? (
                                <ChevronDown className="h-4 w-4" />
                              ) : (
                                <ChevronRight className="h-4 w-4" />
                              )}
                            </div>
                          </div>

                          {/* Tokens */}
                          {(execution.tokens_used || 0) > 0 && (
                            <div className="text-sm text-muted-foreground mt-1">
                              {execution.tokens_used?.toLocaleString()} tokens
                              {execution.iterations && ` • ${execution.iterations} iterations`}
                            </div>
                          )}

                          {/* Expanded Content */}
                          <AnimatePresence>
                            {isExpanded && (
                              <motion.div
                                initial={{ height: 0, opacity: 0 }}
                                animate={{ height: 'auto', opacity: 1 }}
                                exit={{ height: 0, opacity: 0 }}
                                className="overflow-hidden"
                              >
                                <div className="mt-4 space-y-3">
                                  {/* Output Data */}
                                  {execution.output_data && Object.keys(execution.output_data).length > 0 && (
                                    <div>
                                      <span className="text-xs font-medium text-muted-foreground uppercase">Output</span>
                                      <pre className="mt-1 p-3 bg-muted rounded-md text-xs overflow-x-auto">
                                        {JSON.stringify(execution.output_data, null, 2)}
                                      </pre>
                                    </div>
                                  )}

                                  {/* Error Message */}
                                  {execution.error_message && (
                                    <div>
                                      <span className="text-xs font-medium text-red-500 uppercase">Error</span>
                                      <pre className="mt-1 p-3 bg-red-500/10 rounded-md text-xs text-red-500 overflow-x-auto whitespace-pre-wrap">
                                        {execution.error_message}
                                      </pre>
                                    </div>
                                  )}
                                </div>
                              </motion.div>
                            )}
                          </AnimatePresence>
                        </div>
                      </div>

                      {/* Handover Arrow */}
                      {index < executions.length - 1 && !isActive && (
                        <div className="flex items-center justify-center py-2">
                          <div className="flex items-center gap-2 text-xs text-muted-foreground">
                            <ArrowRight className="h-3 w-3" />
                            <span>Handover to next agent</span>
                          </div>
                        </div>
                      )}
                    </motion.div>
                  );
                })}
              </AnimatePresence>

              {executions.length === 0 && (
                <div className="flex flex-col items-center justify-center py-12 text-muted-foreground">
                  <Bot className="h-12 w-12 mb-4 opacity-50" />
                  <p>No agent executions yet</p>
                  <p className="text-sm">Start the workflow to see agent activity</p>
                </div>
              )}
            </div>
          </ScrollArea>
        </CardContent>
      </Card>
        </TabsContent>

        <TabsContent value="requirements" className="mt-4" forceMount hidden={activeTab !== 'requirements'}>
          <RequirementsView workflowId={workflowId} />
        </TabsContent>

        <TabsContent value="developer-briefs" className="mt-4" forceMount hidden={activeTab !== 'developer-briefs'}>
          <DeveloperBriefsView workflowId={workflowId} />
        </TabsContent>

        <TabsContent value="review-briefs" className="mt-4" forceMount hidden={activeTab !== 'review-briefs'}>
          <ReviewBriefsView workflowId={workflowId} />
        </TabsContent>
      </Tabs>
    </div>
  );
}
