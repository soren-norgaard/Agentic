'use client';

import { useState, useEffect, useCallback, useRef } from 'react';
import {
  FileCode,
  Loader2,
  ChevronDown,
  ChevronRight,
  ExternalLink,
  Rocket,
  CheckCircle2,
  Copy,
  Check,
  GitBranch,
  Target,
  Clock,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { ScrollArea } from '@/components/ui/scroll-area';
import { api, Artifact } from '@/lib/api';

interface DeveloperBriefsViewProps {
  workflowId: string;
}

export function DeveloperBriefsView({ workflowId }: DeveloperBriefsViewProps) {
  const [briefs, setBriefs] = useState<Artifact[]>([]);
  const [loading, setLoading] = useState(true);
  const [expandedBriefs, setExpandedBriefs] = useState<Set<string>>(new Set());
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const hasAutoExpanded = useRef(false);
  const hasFetched = useRef(false);

  useEffect(() => {
    // Only fetch once per workflowId
    if (hasFetched.current) return;
    hasFetched.current = true;
    
    const fetchBriefs = async () => {
      try {
        const response = await api.workflows.getDeveloperBriefs(workflowId);
        setBriefs(response.items);
        // Auto-expand the first brief
        if (response.items.length > 0 && !hasAutoExpanded.current) {
          setExpandedBriefs(new Set([response.items[0].id]));
          hasAutoExpanded.current = true;
        }
      } catch (error) {
        console.error('Failed to fetch developer briefs:', error);
      } finally {
        setLoading(false);
      }
    };
    
    fetchBriefs();
  }, [workflowId]);

  const toggleBrief = (briefId: string) => {
    setExpandedBriefs(prev => {
      const next = new Set(prev);
      if (next.has(briefId)) {
        next.delete(briefId);
      } else {
        next.add(briefId);
      }
      return next;
    });
  };

  const copyToClipboard = async (content: string, briefId: string) => {
    try {
      await navigator.clipboard.writeText(content);
      setCopiedId(briefId);
      setTimeout(() => setCopiedId(null), 2000);
    } catch (error) {
      console.error('Failed to copy:', error);
    }
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: 'numeric',
      minute: '2-digit',
    });
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (briefs.length === 0) {
    return (
      <Card>
        <CardContent className="flex flex-col items-center justify-center py-12 text-muted-foreground">
          <FileCode className="h-12 w-12 mb-4 opacity-50" />
          <p className="font-medium">No developer briefs yet</p>
          <p className="text-sm mt-1">
            Developer briefs will appear when stories are prepared for development
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-lg font-semibold flex items-center gap-2">
            <Rocket className="h-5 w-5 text-green-500" />
            Developer Briefs
          </h3>
          <p className="text-sm text-muted-foreground mt-1">
            {briefs.length} brief{briefs.length !== 1 ? 's' : ''} prepared for development
          </p>
        </div>
      </div>

      {/* Briefs List */}
      <div className="space-y-3">
        {briefs.map((brief) => {
          const isExpanded = expandedBriefs.has(brief.id);
          const extraData = brief.extra_data as {
            story_id?: string;
            story_title?: string;
            requirement_ids?: string[];
          };

          return (
            <Card key={brief.id} className={cn(isExpanded && 'ring-1 ring-green-500/50')}>
              <CardHeader
                className="py-3 px-4 cursor-pointer hover:bg-muted/50 transition-colors"
                onClick={() => toggleBrief(brief.id)}
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    {isExpanded ? (
                      <ChevronDown className="h-4 w-4 text-muted-foreground" />
                    ) : (
                      <ChevronRight className="h-4 w-4 text-muted-foreground" />
                    )}
                    <div>
                      <CardTitle className="text-base flex items-center gap-2">
                        <GitBranch className="h-4 w-4 text-green-500" />
                        {extraData?.story_title || brief.name}
                      </CardTitle>
                      <CardDescription className="flex items-center gap-3 mt-1">
                        <span className="flex items-center gap-1">
                          <Clock className="h-3 w-3" />
                          {formatDate(brief.created_at)}
                        </span>
                        {extraData?.story_id && (
                          <Badge variant="outline" className="text-xs">
                            {extraData.story_id}
                          </Badge>
                        )}
                      </CardDescription>
                    </div>
                  </div>

                  <div className="flex items-center gap-2">
                    {extraData?.requirement_ids && extraData.requirement_ids.length > 0 && (
                      <div className="flex items-center gap-1">
                        <Target className="h-3 w-3 text-blue-500" />
                        <span className="text-xs text-muted-foreground">
                          {extraData.requirement_ids.length} req{extraData.requirement_ids.length !== 1 ? 's' : ''}
                        </span>
                      </div>
                    )}
                    <Badge variant="secondary" className="bg-green-500/10 text-green-600">
                      <CheckCircle2 className="h-3 w-3 mr-1" />
                      Ready
                    </Badge>
                  </div>
                </div>
              </CardHeader>

              {isExpanded && brief.content && (
                <CardContent className="pt-0 pb-4">
                  <div className="border rounded-lg overflow-hidden">
                    {/* Brief toolbar */}
                    <div className="flex items-center justify-between px-3 py-2 bg-muted/50 border-b">
                      <span className="text-xs font-medium text-muted-foreground">
                        Developer Brief (Markdown)
                      </span>
                      <Button
                        variant="ghost"
                        size="sm"
                        className="h-7 px-2"
                        onClick={(e) => {
                          e.stopPropagation();
                          copyToClipboard(brief.content || '', brief.id);
                        }}
                      >
                        {copiedId === brief.id ? (
                          <>
                            <Check className="h-3 w-3 mr-1 text-green-500" />
                            Copied
                          </>
                        ) : (
                          <>
                            <Copy className="h-3 w-3 mr-1" />
                            Copy
                          </>
                        )}
                      </Button>
                    </div>

                    {/* Brief content */}
                    <ScrollArea className="h-[400px]">
                      <div className="p-4">
                        <pre className="whitespace-pre-wrap text-sm font-mono leading-relaxed">
                          {brief.content}
                        </pre>
                      </div>
                    </ScrollArea>
                  </div>
                </CardContent>
              )}
            </Card>
          );
        })}
      </div>
    </div>
  );
}
