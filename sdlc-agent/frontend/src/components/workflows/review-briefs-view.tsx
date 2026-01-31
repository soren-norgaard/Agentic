'use client';

import { useState, useEffect, useRef } from 'react';
import {
  Loader2,
  ChevronDown,
  ChevronRight,
  ExternalLink,
  CheckSquare,
  Copy,
  Check,
  GitPullRequest,
  Target,
  Clock,
  Eye,
  Shield,
  TestTube,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { ScrollArea } from '@/components/ui/scroll-area';
import { api, Artifact } from '@/lib/api';

interface ReviewBriefsViewProps {
  workflowId: string;
}

export function ReviewBriefsView({ workflowId }: ReviewBriefsViewProps) {
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
        const response = await api.workflows.getReviewBriefs(workflowId);
        setBriefs(response.items);
        // Auto-expand the first brief
        if (response.items.length > 0 && !hasAutoExpanded.current) {
          setExpandedBriefs(new Set([response.items[0].id]));
          hasAutoExpanded.current = true;
        }
      } catch (error) {
        console.error('Failed to fetch review briefs:', error);
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
          <Eye className="h-12 w-12 mb-4 opacity-50" />
          <p className="font-medium">No review briefs yet</p>
          <p className="text-sm mt-1">
            Review briefs will appear when PRs are prepared for code review
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
            <Eye className="h-5 w-5 text-purple-500" />
            Review Briefs
          </h3>
          <p className="text-sm text-muted-foreground mt-1">
            {briefs.length} brief{briefs.length !== 1 ? 's' : ''} prepared for code review
          </p>
        </div>
      </div>

      {/* Briefs List */}
      <div className="space-y-3">
        {briefs.map((brief) => {
          const isExpanded = expandedBriefs.has(brief.id);
          const extraData = brief.extra_data as {
            pr_number?: number;
            pr_title?: string;
            story_id?: string;
          };

          return (
            <Card key={brief.id} className={cn(isExpanded && 'ring-1 ring-purple-500/50')}>
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
                        <GitPullRequest className="h-4 w-4 text-purple-500" />
                        {extraData?.pr_title || brief.name}
                      </CardTitle>
                      <CardDescription className="flex items-center gap-3 mt-1">
                        <span className="flex items-center gap-1">
                          <Clock className="h-3 w-3" />
                          {formatDate(brief.created_at)}
                        </span>
                        {extraData?.pr_number && (
                          <Badge variant="outline" className="text-xs">
                            PR #{extraData.pr_number}
                          </Badge>
                        )}
                        {extraData?.story_id && (
                          <Badge variant="outline" className="text-xs">
                            {extraData.story_id}
                          </Badge>
                        )}
                      </CardDescription>
                    </div>
                  </div>

                  <div className="flex items-center gap-2">
                    <div className="flex items-center gap-3 text-xs text-muted-foreground">
                      <span className="flex items-center gap-1">
                        <CheckSquare className="h-3 w-3 text-green-500" />
                        Functional
                      </span>
                      <span className="flex items-center gap-1">
                        <Shield className="h-3 w-3 text-amber-500" />
                        Security
                      </span>
                      <span className="flex items-center gap-1">
                        <TestTube className="h-3 w-3 text-blue-500" />
                        Testing
                      </span>
                    </div>
                    <Badge variant="secondary" className="bg-purple-500/10 text-purple-600">
                      <Eye className="h-3 w-3 mr-1" />
                      Ready for Review
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
                        Review Brief (Markdown)
                      </span>
                      <div className="flex items-center gap-2">
                        {extraData?.pr_number && (
                          <Button
                            variant="ghost"
                            size="sm"
                            className="h-7 px-2"
                            onClick={(e) => {
                              e.stopPropagation();
                              // TODO: Construct GitHub URL from project settings
                              window.open(`https://github.com/owner/repo/pull/${extraData.pr_number}`, '_blank');
                            }}
                          >
                            <ExternalLink className="h-3 w-3 mr-1" />
                            View PR
                          </Button>
                        )}
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
