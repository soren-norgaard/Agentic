'use client';

import { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  FileText,
  MessageSquare,
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  Loader2,
  ClipboardList,
  Target,
  Users,
  Layers,
  BookOpen,
  HelpCircle,
  Rocket,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Separator } from '@/components/ui/separator';
import { api, Artifact, RequirementsTraceability } from '@/lib/api';
import { useToast } from '@/hooks/use-toast';

interface RequirementsViewProps {
  workflowId: string;
}

export function RequirementsView({ workflowId }: RequirementsViewProps) {
  const [artifact, setArtifact] = useState<Artifact | null>(null);
  const [traceability, setTraceability] = useState<RequirementsTraceability | null>(null);
  const [loading, setLoading] = useState(true);
  const [expandedSections, setExpandedSections] = useState<Set<string>>(
    new Set(['original', 'human_inputs', 'epics'])
  );
  const [preparingStoryId, setPreparingStoryId] = useState<string | null>(null);
  const [preparedStories, setPreparedStories] = useState<Set<string>>(new Set());
  const { toast } = useToast();
  const hasFetched = useRef(false);

  useEffect(() => {
    // Only fetch once per workflowId
    if (hasFetched.current) return;
    hasFetched.current = true;
    
    const fetchArtifacts = async () => {
      try {
        const response = await api.workflows.getArtifacts(workflowId, 'requirements');
        if (response.items.length > 0) {
          const reqArtifact = response.items[0];
          setArtifact(reqArtifact);
          
          // Parse the content
          if (reqArtifact.content) {
            try {
              const parsed = JSON.parse(reqArtifact.content);
              setTraceability(parsed);
            } catch (e) {
              console.error('Failed to parse traceability content:', e);
            }
          }
        }
      } catch (error) {
        console.error('Failed to fetch artifacts:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchArtifacts();
  }, [workflowId]);

  const toggleSection = (section: string) => {
    setExpandedSections(prev => {
      const next = new Set(prev);
      if (next.has(section)) {
        next.delete(section);
      } else {
        next.add(section);
      }
      return next;
    });
  };

  // Helper to get requirement by ID
  const getRequirementById = (reqId: string): { id: string; title: string; type: string } | null => {
    if (!traceability) return null;
    
    // Check functional requirements
    const funcReq = traceability.requirements.functional.find(
      r => r.id === reqId || `REQ-${r.id}` === reqId
    );
    if (funcReq) return { id: funcReq.id, title: funcReq.title, type: 'functional' };
    
    // Check non-functional requirements
    const nonFuncReq = traceability.requirements.non_functional.find(
      r => r.id === reqId || `REQ-${r.id}` === reqId
    );
    if (nonFuncReq) return { id: nonFuncReq.id, title: nonFuncReq.title, type: 'non_functional' };
    
    return null;
  };

  // Component to display requirement links
  const RequirementLinks = ({ requirementIds }: { requirementIds: string[] }) => {
    if (!requirementIds || requirementIds.length === 0) return null;
    
    return (
      <div className="mt-3 pt-3 border-t border-dashed">
        <p className="text-xs font-medium text-muted-foreground mb-2 flex items-center gap-1">
          <Target className="h-3 w-3" />
          Traces to Requirements:
        </p>
        <div className="flex flex-wrap gap-1.5">
          {requirementIds.map((reqId, i) => {
            const req = getRequirementById(reqId);
            return (
              <Badge 
                key={i} 
                variant="outline" 
                className={cn(
                  "text-xs cursor-help",
                  req?.type === 'functional' ? "border-blue-500/50 text-blue-600" : "border-purple-500/50 text-purple-600"
                )}
                title={req?.title || reqId}
              >
                REQ-{req?.id || reqId}
              </Badge>
            );
          })}
        </div>
      </div>
    );
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (!artifact || !traceability) {
    return (
      <Card>
        <CardContent className="flex flex-col items-center justify-center py-12 text-muted-foreground">
          <FileText className="h-12 w-12 mb-4 opacity-50" />
          <p className="font-medium">No requirements traceability yet</p>
          <p className="text-sm mt-1">
            Requirements traceability will appear after the requirements phase completes
          </p>
        </CardContent>
      </Card>
    );
  }

  const { summary } = traceability;

  return (
    <div className="space-y-4">
      {/* Summary Stats */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
        <Card>
          <CardContent className="pt-4 pb-3 px-4">
            <div className="flex items-center gap-2">
              <Target className="h-4 w-4 text-blue-500" />
              <span className="text-2xl font-bold">{summary.total_functional_requirements}</span>
            </div>
            <p className="text-xs text-muted-foreground mt-1">Functional Reqs</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4 pb-3 px-4">
            <div className="flex items-center gap-2">
              <ClipboardList className="h-4 w-4 text-purple-500" />
              <span className="text-2xl font-bold">{summary.total_non_functional_requirements}</span>
            </div>
            <p className="text-xs text-muted-foreground mt-1">Non-Functional</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4 pb-3 px-4">
            <div className="flex items-center gap-2">
              <Layers className="h-4 w-4 text-green-500" />
              <span className="text-2xl font-bold">{summary.total_epics}</span>
            </div>
            <p className="text-xs text-muted-foreground mt-1">Epics</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4 pb-3 px-4">
            <div className="flex items-center gap-2">
              <BookOpen className="h-4 w-4 text-orange-500" />
              <span className="text-2xl font-bold">{summary.total_stories}</span>
            </div>
            <p className="text-xs text-muted-foreground mt-1">User Stories</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4 pb-3 px-4">
            <div className="flex items-center gap-2">
              <MessageSquare className="h-4 w-4 text-cyan-500" />
              <span className="text-2xl font-bold">{summary.total_human_inputs}</span>
            </div>
            <p className="text-xs text-muted-foreground mt-1">Human Inputs</p>
          </CardContent>
        </Card>
      </div>

      <ScrollArea className="h-[500px] pr-4">
        <div className="space-y-4">
          {/* Original Requirements Section */}
          <CollapsibleSection
            title="Original Requirements"
            icon={<FileText className="h-4 w-4" />}
            isExpanded={expandedSections.has('original')}
            onToggle={() => toggleSection('original')}
          >
            <div className="p-4 bg-muted/50 rounded-lg">
              <p className="whitespace-pre-wrap text-sm">{traceability.original_requirements || 'No original requirements provided'}</p>
            </div>
          </CollapsibleSection>

          {/* Human Inputs Section */}
          {traceability.human_inputs.length > 0 && (
            <CollapsibleSection
              title="Human Input History"
              icon={<MessageSquare className="h-4 w-4" />}
              badge={traceability.human_inputs.length}
              isExpanded={expandedSections.has('human_inputs')}
              onToggle={() => toggleSection('human_inputs')}
            >
              <div className="space-y-3">
                {traceability.human_inputs.map((input, index) => (
                  <motion.div
                    key={index}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: index * 0.05 }}
                    className="p-4 border rounded-lg bg-card"
                  >
                    <div className="flex items-start gap-3">
                      <div className="flex items-center justify-center w-8 h-8 rounded-full bg-cyan-500/10 shrink-0">
                        <HelpCircle className="h-4 w-4 text-cyan-500" />
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-2">
                          <Badge variant="outline" className="text-xs capitalize">
                            {input.type}
                          </Badge>
                          {input.timestamp && (
                            <span className="text-xs text-muted-foreground">
                              {new Date(input.timestamp).toLocaleString()}
                            </span>
                          )}
                        </div>
                        
                        {/* Question */}
                        <div className="mb-3">
                          <p className="text-sm font-medium text-muted-foreground">Question:</p>
                          <p className="text-sm mt-1">{input.question || input.prompt}</p>
                        </div>

                        {/* Options if any */}
                        {input.options && (Array.isArray(input.options) ? input.options.length > 0 : true) && (
                          <div className="mb-3">
                            <p className="text-sm font-medium text-muted-foreground">Options:</p>
                            <div className="flex flex-wrap gap-2 mt-1">
                              {(() => {
                                // Handle options being a string (JSON) or array
                                let optionsArray: unknown[] = [];
                                if (typeof input.options === 'string') {
                                  try {
                                    optionsArray = JSON.parse(input.options);
                                  } catch {
                                    optionsArray = [input.options];
                                  }
                                } else if (Array.isArray(input.options)) {
                                  optionsArray = input.options;
                                }
                                
                                return optionsArray.map((opt, i) => {
                                  let displayText: string;
                                  if (typeof opt === 'string') {
                                    displayText = opt;
                                  } else if (opt && typeof opt === 'object') {
                                    const objOpt = opt as Record<string, unknown>;
                                    displayText = (objOpt.label as string) || (objOpt.item as string) || (objOpt.text as string) || JSON.stringify(opt);
                                  } else {
                                    displayText = String(opt);
                                  }
                                  return (
                                    <Badge key={i} variant="secondary" className="text-xs">
                                      {displayText}
                                    </Badge>
                                  );
                                });
                              })()}
                            </div>
                          </div>
                        )}

                        {/* Response */}
                        {input.response && (
                          <div className="mt-2 p-3 bg-green-500/10 rounded-lg border border-green-500/20">
                            <div className="flex items-center gap-2 mb-1">
                              <CheckCircle2 className="h-3 w-3 text-green-500" />
                              <p className="text-xs font-medium text-green-600">Response:</p>
                            </div>
                            <p className="text-sm">
                              {typeof input.response === 'string' 
                                ? input.response 
                                : (input.response as Record<string, unknown>).text as string || JSON.stringify(input.response)}
                            </p>
                          </div>
                        )}
                      </div>
                    </div>
                  </motion.div>
                ))}
              </div>
            </CollapsibleSection>
          )}

          {/* Requirements Section */}
          {(traceability.requirements.functional.length > 0 || traceability.requirements.non_functional.length > 0) && (
            <CollapsibleSection
              title="Extracted Requirements"
              icon={<Target className="h-4 w-4" />}
              badge={traceability.requirements.functional.length + traceability.requirements.non_functional.length}
              isExpanded={expandedSections.has('requirements')}
              onToggle={() => toggleSection('requirements')}
            >
              <div className="space-y-4">
                {traceability.requirements.functional.length > 0 && (
                  <div>
                    <h4 className="text-sm font-medium mb-2 flex items-center gap-2">
                      <span className="w-2 h-2 rounded-full bg-blue-500" />
                      Functional Requirements
                    </h4>
                    <div className="space-y-2">
                      {traceability.requirements.functional.map((req: any, index: number) => (
                        <div key={index} className="p-3 border rounded-lg bg-card">
                          <div className="flex items-center gap-2 mb-1">
                            <Badge variant="outline" className="text-xs">
                              {req.id || `FR-${index + 1}`}
                            </Badge>
                            {req.priority && (
                              <Badge variant="secondary" className="text-xs capitalize">
                                {req.priority}
                              </Badge>
                            )}
                          </div>
                          <p className="text-sm font-medium">{req.title}</p>
                          {req.description && (
                            <p className="text-sm text-muted-foreground mt-1">{req.description}</p>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {traceability.requirements.non_functional.length > 0 && (
                  <div>
                    <h4 className="text-sm font-medium mb-2 flex items-center gap-2">
                      <span className="w-2 h-2 rounded-full bg-purple-500" />
                      Non-Functional Requirements
                    </h4>
                    <div className="space-y-2">
                      {traceability.requirements.non_functional.map((req: any, index: number) => (
                        <div key={index} className="p-3 border rounded-lg bg-card">
                          <div className="flex items-center gap-2 mb-1">
                            <Badge variant="outline" className="text-xs">
                              {req.id || `NFR-${index + 1}`}
                            </Badge>
                            {req.type && (
                              <Badge variant="secondary" className="text-xs capitalize">
                                {req.type}
                              </Badge>
                            )}
                          </div>
                          <p className="text-sm font-medium">{req.title}</p>
                          {req.description && (
                            <p className="text-sm text-muted-foreground mt-1">{req.description}</p>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </CollapsibleSection>
          )}

          {/* Epics Section */}
          {traceability.epics.length > 0 && (
            <CollapsibleSection
              title="Generated Epics"
              icon={<Layers className="h-4 w-4" />}
              badge={traceability.epics.length}
              isExpanded={expandedSections.has('epics')}
              onToggle={() => toggleSection('epics')}
            >
              <div className="space-y-3">
                {traceability.epics.map((epic, index) => (
                  <motion.div
                    key={epic.id}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: index * 0.05 }}
                    className="p-4 border rounded-lg bg-card"
                  >
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-2">
                          <Badge className="bg-green-500/10 text-green-600 border-green-500/20">
                            EPIC-{epic.id}
                          </Badge>
                          <Badge variant="secondary" className="text-xs">
                            {epic.story_count} stories
                          </Badge>
                        </div>
                        <h4 className="font-medium">{epic.title}</h4>
                        {epic.description && (
                          <p className="text-sm text-muted-foreground mt-1">{epic.description}</p>
                        )}
                        {epic.business_value && (
                          <p className="text-sm text-blue-600 mt-2">
                            <span className="font-medium">Business Value:</span> {epic.business_value}
                          </p>
                        )}
                        <RequirementLinks requirementIds={epic.requirement_ids || []} />
                      </div>
                    </div>
                  </motion.div>
                ))}
              </div>
            </CollapsibleSection>
          )}

          {/* User Stories Section */}
          {traceability.user_stories.length > 0 && (
            <CollapsibleSection
              title="User Stories"
              icon={<BookOpen className="h-4 w-4" />}
              badge={traceability.user_stories.length}
              isExpanded={expandedSections.has('stories')}
              onToggle={() => toggleSection('stories')}
            >
              <div className="space-y-3">
                {traceability.user_stories.map((story, index) => (
                  <motion.div
                    key={story.id}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: index * 0.05 }}
                    className="p-4 border rounded-lg bg-card"
                  >
                    <div className="flex items-center gap-2 mb-2">
                      <Badge className="bg-orange-500/10 text-orange-600 border-orange-500/20">
                        STORY-{story.id}
                      </Badge>
                      {story.epic_id && (
                        <Badge variant="outline" className="text-xs">
                          EPIC-{story.epic_id}
                        </Badge>
                      )}
                    </div>
                    <h4 className="font-medium">{story.title}</h4>
                    {story.user_story && (
                      <p className="text-sm italic text-muted-foreground mt-2 p-2 bg-muted/50 rounded">
                        {story.user_story}
                      </p>
                    )}
                    {story.acceptance_criteria && story.acceptance_criteria.length > 0 && (
                      <div className="mt-3">
                        <p className="text-xs font-medium text-muted-foreground uppercase mb-2">
                          Acceptance Criteria
                        </p>
                        <ul className="space-y-1">
                          {story.acceptance_criteria.map((ac: any, i: number) => (
                            <li key={i} className="flex items-start gap-2 text-sm">
                              <CheckCircle2 className="h-4 w-4 text-green-500 shrink-0 mt-0.5" />
                              <span>{typeof ac === 'string' ? ac : ac.criteria || ac.description || JSON.stringify(ac)}</span>
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}
                    <RequirementLinks requirementIds={story.requirement_ids || []} />

                    {/* Prepare for Development Button */}
                    <div className="mt-4 pt-3 border-t">
                      <Button
                        variant={preparedStories.has(story.id) ? 'secondary' : 'default'}
                        size="sm"
                        disabled={preparingStoryId === story.id || preparedStories.has(story.id)}
                        onClick={async (e) => {
                          e.stopPropagation();
                          setPreparingStoryId(story.id);
                          try {
                            // Extract acceptance criteria as strings
                            const acList = story.acceptance_criteria?.map((ac: any) => 
                              typeof ac === 'string' ? ac : ac.criteria || ac.description || JSON.stringify(ac)
                            ) || [];

                            const result = await api.workflows.prepareDevelopment(workflowId, {
                              story_id: `STORY-${story.id}`,
                              story_title: story.title,
                              story_description: story.user_story || '',
                              acceptance_criteria: acList,
                              requirement_ids: story.requirement_ids || [],
                            });

                            if (result.success) {
                              setPreparedStories(prev => new Set(Array.from(prev).concat([story.id])));
                              toast({
                                title: 'Developer Brief Created',
                                description: `Brief for "${story.title}" is ready. Check the Developer Briefs tab.`,
                              });
                            }
                          } catch (error) {
                            console.error('Failed to prepare development:', error);
                            toast({
                              title: 'Failed to prepare',
                              description: 'Could not create developer brief. Please try again.',
                              variant: 'destructive',
                            });
                          } finally {
                            setPreparingStoryId(null);
                          }
                        }}
                        className="w-full"
                      >
                        {preparingStoryId === story.id ? (
                          <>
                            <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                            Preparing...
                          </>
                        ) : preparedStories.has(story.id) ? (
                          <>
                            <CheckCircle2 className="h-4 w-4 mr-2" />
                            Brief Created
                          </>
                        ) : (
                          <>
                            <Rocket className="h-4 w-4 mr-2" />
                            Prepare for Development
                          </>
                        )}
                      </Button>
                    </div>
                  </motion.div>
                ))}
              </div>
            </CollapsibleSection>
          )}
        </div>
      </ScrollArea>
    </div>
  );
}

// Collapsible Section Component
interface CollapsibleSectionProps {
  title: string;
  icon: React.ReactNode;
  badge?: number;
  isExpanded: boolean;
  onToggle: () => void;
  children: React.ReactNode;
}

function CollapsibleSection({ title, icon, badge, isExpanded, onToggle, children }: CollapsibleSectionProps) {
  return (
    <Card>
      <CardHeader
        className="cursor-pointer hover:bg-muted/50 transition-colors py-3"
        onClick={onToggle}
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="text-muted-foreground">{icon}</span>
            <CardTitle className="text-base">{title}</CardTitle>
            {badge !== undefined && (
              <Badge variant="secondary" className="text-xs">
                {badge}
              </Badge>
            )}
          </div>
          {isExpanded ? (
            <ChevronDown className="h-4 w-4 text-muted-foreground" />
          ) : (
            <ChevronRight className="h-4 w-4 text-muted-foreground" />
          )}
        </div>
      </CardHeader>
      <AnimatePresence>
        {isExpanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
          >
            <CardContent className="pt-0">{children}</CardContent>
          </motion.div>
        )}
      </AnimatePresence>
    </Card>
  );
}
