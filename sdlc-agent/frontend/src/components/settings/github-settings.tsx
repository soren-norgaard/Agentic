'use client';

import { useState, useEffect, useCallback } from 'react';
import { motion } from 'framer-motion';
import {
  Github,
  CheckCircle2,
  XCircle,
  RefreshCw,
  Tag,
  Link2,
  AlertCircle,
  Loader2,
  ExternalLink,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { api, GitHubConfig, GitHubRepository } from '@/lib/api';

interface GitHubSettingsProps {
  className?: string;
}

export function GitHubSettings({ className }: GitHubSettingsProps) {
  const [config, setConfig] = useState<GitHubConfig | null>(null);
  const [repository, setRepository] = useState<GitHubRepository | null>(null);
  const [loading, setLoading] = useState(true);
  const [settingUpLabels, setSettingUpLabels] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [labelResult, setLabelResult] = useState<string | null>(null);

  const fetchConfig = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const configData = await api.github.getConfig();
      setConfig(configData);
      
      if (configData.configured) {
        try {
          const repoData = await api.github.getRepository();
          setRepository(repoData);
        } catch (repoError) {
          console.warn('Could not fetch repository info:', repoError);
        }
      }
    } catch (err) {
      console.error('Error fetching GitHub config:', err);
      setError('Failed to fetch GitHub configuration');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchConfig();
  }, [fetchConfig]);

  const handleSetupLabels = async () => {
    setSettingUpLabels(true);
    setLabelResult(null);
    try {
      const result = await api.github.setupLabels();
      setLabelResult(result.message);
    } catch (err: unknown) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to setup labels';
      setLabelResult(`Error: ${errorMessage}`);
    } finally {
      setSettingUpLabels(false);
    }
  };

  if (loading) {
    return (
      <Card className={cn('bg-[#1a1a2e] border-purple-500/20', className)}>
        <CardContent className="flex items-center justify-center py-8">
          <Loader2 className="h-6 w-6 animate-spin text-purple-400" />
          <span className="ml-2 text-gray-400">Loading GitHub configuration...</span>
        </CardContent>
      </Card>
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className={className}
    >
      <Card className="bg-[#1a1a2e] border-purple-500/20">
        <CardHeader>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg bg-purple-500/10">
                <Github className="h-6 w-6 text-purple-400" />
              </div>
              <div>
                <CardTitle className="text-white">GitHub Integration</CardTitle>
                <CardDescription className="text-gray-400">
                  Connect your project to GitHub for issue tracking and PRs
                </CardDescription>
              </div>
            </div>
            <Badge
              className={cn(
                'px-3 py-1',
                config?.configured
                  ? 'bg-green-500/20 text-green-400 border-green-500/30'
                  : 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30'
              )}
            >
              {config?.configured ? (
                <>
                  <CheckCircle2 className="h-3 w-3 mr-1" />
                  Connected
                </>
              ) : (
                <>
                  <AlertCircle className="h-3 w-3 mr-1" />
                  Not Configured
                </>
              )}
            </Badge>
          </div>
        </CardHeader>

        <CardContent className="space-y-6">
          {error && (
            <div className="p-4 rounded-lg bg-red-500/10 border border-red-500/20">
              <div className="flex items-center gap-2 text-red-400">
                <XCircle className="h-4 w-4" />
                <span>{error}</span>
              </div>
            </div>
          )}

          {!config?.configured ? (
            <div className="space-y-4">
              <div className="p-4 rounded-lg bg-yellow-500/10 border border-yellow-500/20">
                <h4 className="text-yellow-400 font-medium mb-2">Configuration Required</h4>
                <p className="text-gray-400 text-sm mb-4">
                  Set the following environment variables on the backend to enable GitHub integration:
                </p>
                <div className="bg-[#0d0d1a] rounded-lg p-3 font-mono text-sm">
                  <div className="text-gray-300">GITHUB_TOKEN=ghp_your_token_here</div>
                  <div className="text-gray-300">GITHUB_OWNER=your-username</div>
                  <div className="text-gray-300">GITHUB_REPO=your-repository</div>
                </div>
              </div>
              <Button
                onClick={fetchConfig}
                variant="outline"
                className="border-purple-500/30 text-purple-400 hover:bg-purple-500/10"
              >
                <RefreshCw className="h-4 w-4 mr-2" />
                Retry Connection
              </Button>
            </div>
          ) : (
            <>
              {/* Repository Info */}
              <div className="space-y-4">
                <h4 className="text-white font-medium flex items-center gap-2">
                  <Link2 className="h-4 w-4 text-purple-400" />
                  Connected Repository
                </h4>
                <div className="grid grid-cols-2 gap-4">
                  <div className="p-4 rounded-lg bg-[#0d0d1a] border border-purple-500/10">
                    <div className="text-gray-400 text-sm mb-1">Repository</div>
                    <div className="text-white font-medium">
                      {config.owner}/{config.repo}
                    </div>
                  </div>
                  <div className="p-4 rounded-lg bg-[#0d0d1a] border border-purple-500/10">
                    <div className="text-gray-400 text-sm mb-1">Auto Sync</div>
                    <div className="text-white font-medium">
                      {config.auto_sync_enabled ? 'Enabled' : 'Disabled'}
                    </div>
                  </div>
                </div>
                
                {repository && (
                  <div className="grid grid-cols-2 gap-4">
                    <div className="p-4 rounded-lg bg-[#0d0d1a] border border-purple-500/10">
                      <div className="text-gray-400 text-sm mb-1">Default Branch</div>
                      <div className="text-white font-medium">{repository.default_branch}</div>
                    </div>
                    <div className="p-4 rounded-lg bg-[#0d0d1a] border border-purple-500/10">
                      <div className="text-gray-400 text-sm mb-1">Open Issues</div>
                      <div className="text-white font-medium">{repository.open_issues_count}</div>
                    </div>
                  </div>
                )}

                {repository && (
                  <a
                    href={repository.html_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center text-purple-400 hover:text-purple-300 text-sm"
                  >
                    <ExternalLink className="h-4 w-4 mr-1" />
                    View on GitHub
                  </a>
                )}
              </div>

              {/* Labels Setup */}
              <div className="space-y-4 pt-4 border-t border-purple-500/10">
                <h4 className="text-white font-medium flex items-center gap-2">
                  <Tag className="h-4 w-4 text-purple-400" />
                  SDLC Labels
                </h4>
                <p className="text-gray-400 text-sm">
                  Create standard SDLC labels (epic, story, task, etc.) in your GitHub repository for issue categorization.
                </p>
                
                <div className="flex flex-wrap gap-2 mb-4">
                  {['epic', 'story', 'task', 'bug', 'spike', 'needs-design', 'ready-for-dev', 'in-review', 'blocked'].map((label) => (
                    <Badge
                      key={label}
                      variant="outline"
                      className="text-gray-300 border-gray-600"
                    >
                      {label}
                    </Badge>
                  ))}
                </div>

                {labelResult && (
                  <div
                    className={cn(
                      'p-3 rounded-lg text-sm',
                      labelResult.startsWith('Error')
                        ? 'bg-red-500/10 text-red-400 border border-red-500/20'
                        : 'bg-green-500/10 text-green-400 border border-green-500/20'
                    )}
                  >
                    {labelResult}
                  </div>
                )}

                <Button
                  onClick={handleSetupLabels}
                  disabled={settingUpLabels}
                  className="bg-purple-600 hover:bg-purple-700 text-white"
                >
                  {settingUpLabels ? (
                    <>
                      <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                      Setting up labels...
                    </>
                  ) : (
                    <>
                      <Tag className="h-4 w-4 mr-2" />
                      Setup SDLC Labels
                    </>
                  )}
                </Button>
              </div>
            </>
          )}
        </CardContent>
      </Card>
    </motion.div>
  );
}
