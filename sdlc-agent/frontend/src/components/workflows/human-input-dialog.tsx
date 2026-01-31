'use client';

import { useState, useEffect, useRef } from 'react';
import { motion } from 'framer-motion';
import {
  MessageSquare,
  Send,
  Loader2,
  AlertCircle,
  CheckCircle2,
  HelpCircle,
  ListChecks,
  FileQuestion,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { api, HumanInput } from '@/lib/api';

interface HumanInputDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  input: HumanInput | null;
  workflowName?: string;
  onSubmit?: () => void;
}

interface ParsedOption {
  label: string;
  description: string;
}

function parseOptions(optionsInput?: string | unknown[]): ParsedOption[] {
  if (!optionsInput) return [];
  
  try {
    // Handle case where options is already an array
    let optionsArray: unknown[];
    if (Array.isArray(optionsInput)) {
      optionsArray = optionsInput;
    } else if (typeof optionsInput === 'string') {
      // Try to parse JSON string
      const parsed = JSON.parse(optionsInput);
      if (Array.isArray(parsed)) {
        optionsArray = parsed;
      } else {
        return [];
      }
    } else {
      return [];
    }
    
    return optionsArray.map((opt) => {
      if (typeof opt === 'string') {
        return { label: opt, description: '' };
      } else if (opt && typeof opt === 'object') {
        const objOpt = opt as Record<string, unknown>;
        // Handle various object structures: {label, description}, {item, options}, etc.
        const label = (objOpt.label as string) || (objOpt.item as string) || (objOpt.text as string) || (objOpt.value as string) || JSON.stringify(opt);
        const description = (objOpt.description as string) || '';
        return { label, description };
      }
      return { label: String(opt), description: '' };
    });
  } catch {
    return [];
  }
}

const requestTypeConfig: Record<string, { icon: typeof MessageSquare; color: string; label: string }> = {
  clarification: { icon: HelpCircle, color: 'text-blue-500', label: 'Clarification Needed' },
  approval: { icon: CheckCircle2, color: 'text-green-500', label: 'Approval Required' },
  choice: { icon: ListChecks, color: 'text-purple-500', label: 'Selection Required' },
  text: { icon: MessageSquare, color: 'text-cyan-500', label: 'Input Required' },
  review: { icon: FileQuestion, color: 'text-yellow-500', label: 'Review Required' },
  escalation: { icon: AlertCircle, color: 'text-red-500', label: 'Escalation' },
};

export function HumanInputDialog({
  open,
  onOpenChange,
  input,
  workflowName,
  onSubmit,
}: HumanInputDialogProps) {
  const [response, setResponse] = useState('');
  const [selectedOptionIndices, setSelectedOptionIndices] = useState<Set<number>>(new Set());
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);
  const lastInputIdRef = useRef<string | null>(null);

  // Reset state only when dialog opens with a NEW input (different id)
  useEffect(() => {
    if (open && input?.id && input.id !== lastInputIdRef.current) {
      lastInputIdRef.current = input.id;
      setResponse('');
      setSelectedOptionIndices(new Set());
      setError(null);
      setSuccess(false);
      setSubmitting(false);
    }
    if (!open) {
      lastInputIdRef.current = null;
    }
  }, [open, input?.id]);

  const config = input ? (requestTypeConfig[input.request_type] || requestTypeConfig.text) : requestTypeConfig.text;
  const Icon = config.icon;
  const options = parseOptions(input?.context?.options);

  // Update response text when selections change
  useEffect(() => {
    if (selectedOptionIndices.size > 0) {
      const selectedLabels = Array.from(selectedOptionIndices)
        .sort((a, b) => a - b)
        .map(idx => options[idx]?.label)
        .filter(Boolean);
      setResponse(selectedLabels.join('; '));
    }
  }, [selectedOptionIndices, options]);

  // Early return AFTER all hooks
  if (!input) return null;

  const handleSubmit = async () => {
    if (!response.trim()) {
      setError('Please provide a response');
      return;
    }

    setSubmitting(true);
    setError(null);

    try {
      await api.workflows.submitInput(input.workflow_id, input.id, response);
      setSuccess(true);
      setTimeout(() => {
        onOpenChange(false);
        setResponse('');
        setSelectedOptionIndices(new Set());
        setSuccess(false);
        onSubmit?.();
      }, 1500);
    } catch (err) {
      console.error('Failed to submit input:', err);
      setError('Failed to submit response. Please try again.');
    } finally {
      setSubmitting(false);
    }
  };

  const handleToggleOption = (option: ParsedOption, index: number) => {
    setSelectedOptionIndices(prev => {
      const newSet = new Set(prev);
      if (newSet.has(index)) {
        newSet.delete(index);
      } else {
        newSet.add(index);
      }
      return newSet;
    });
  };

  const handleResponseChange = (value: string) => {
    setResponse(value);
    setError(null);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[90vh] flex flex-col">
        <DialogHeader className="shrink-0">
          <div className="flex items-center gap-3">
            <div className={cn('p-2 rounded-full bg-muted', config.color)}>
              <Icon className="h-5 w-5" />
            </div>
            <div>
              <DialogTitle className="text-xl">{config.label}</DialogTitle>
              {workflowName && (
                <DialogDescription className="mt-1">
                  Workflow: <span className="font-medium text-foreground">{workflowName}</span>
                </DialogDescription>
              )}
            </div>
          </div>
        </DialogHeader>

        <div className="flex-1 overflow-y-auto pr-2 min-h-0">
          <div className="space-y-6 py-4">
            {/* Phase badge */}
            {input.context?.phase && (
              <Badge variant="outline" className="text-xs">
                Phase: {input.context.phase}
              </Badge>
            )}

            {/* Original context info */}
            {input.context?.original_context && (
              <Card className="bg-muted/50">
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm font-medium text-muted-foreground">
                    Context
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-sm">{input.context.original_context}</p>
                </CardContent>
              </Card>
            )}

            {/* The prompt/question */}
            <div className="space-y-2">
              <h4 className="font-medium text-sm text-muted-foreground uppercase tracking-wide">
                Question
              </h4>
              <div className="prose prose-sm dark:prose-invert max-w-none">
                <div className="whitespace-pre-wrap text-sm leading-relaxed">
                  {input.prompt}
                </div>
              </div>
            </div>

            {/* Options (if available) */}
            {options.length > 0 && (
              <div className="space-y-3">
                <h4 className="font-medium text-sm text-muted-foreground uppercase tracking-wide">
                  Quick Options
                </h4>
                <p className="text-xs text-muted-foreground mb-2">
                  Select one or more options. Your selections will be combined in the response.
                </p>
                <div className="grid gap-2">
                  {options.map((option, index) => {
                    const isSelected = selectedOptionIndices.has(index);
                    return (
                      <button
                        key={index}
                        type="button"
                        onClick={() => handleToggleOption(option, index)}
                        className={cn(
                          'flex items-start gap-3 p-3 rounded-lg border text-left transition-all',
                          'hover:bg-accent hover:border-primary/50',
                          isSelected && 'border-primary bg-primary/5'
                        )}
                      >
                        <div
                          className={cn(
                            'w-5 h-5 rounded-md border-2 flex items-center justify-center shrink-0 mt-0.5',
                            isSelected
                              ? 'border-primary bg-primary'
                              : 'border-muted-foreground/30'
                          )}
                        >
                          {isSelected && (
                            <CheckCircle2 className="h-3 w-3 text-primary-foreground" />
                          )}
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className="font-medium text-sm">{option.label}</div>
                          {option.description && (
                            <div className="text-xs text-muted-foreground mt-0.5">
                              {option.description}
                            </div>
                          )}
                        </div>
                      </button>
                    );
                  })}
                </div>
              </div>
            )}

            {/* Response textarea */}
            <div className="space-y-2">
              <h4 className="font-medium text-sm text-muted-foreground uppercase tracking-wide">
                Your Response
              </h4>
              <Textarea
                value={response}
                onChange={(e) => handleResponseChange(e.target.value)}
                placeholder="Type your detailed response here, or select an option above..."
                className="min-h-[150px]"
                disabled={submitting || success}
              />
              <p className="text-xs text-muted-foreground">
                Provide detailed information to help the AI agents understand your requirements.
              </p>
            </div>

            {/* Error message */}
            {error && (
              <motion.div
                initial={{ opacity: 0, y: -10 }}
                animate={{ opacity: 1, y: 0 }}
                className="flex items-center gap-2 text-destructive text-sm"
              >
                <AlertCircle className="h-4 w-4" />
                {error}
              </motion.div>
            )}

            {/* Success message */}
            {success && (
              <motion.div
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                className="flex items-center gap-2 text-green-500 text-sm"
              >
                <CheckCircle2 className="h-4 w-4" />
                Response submitted! Workflow will continue processing...
              </motion.div>
            )}
          </div>
        </div>

        <DialogFooter className="gap-2 sm:gap-0 shrink-0 pt-4 border-t">
          <Button
            variant="outline"
            onClick={() => onOpenChange(false)}
            disabled={submitting}
          >
            Cancel
          </Button>
          <Button
            onClick={handleSubmit}
            disabled={submitting || success || !response.trim()}
            className="gap-2"
          >
            {submitting ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />
                Submitting...
              </>
            ) : success ? (
              <>
                <CheckCircle2 className="h-4 w-4" />
                Submitted!
              </>
            ) : (
              <>
                <Send className="h-4 w-4" />
                Submit Response
              </>
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
