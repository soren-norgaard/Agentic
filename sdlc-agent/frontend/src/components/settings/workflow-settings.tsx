'use client';

import { useEffect, useState } from 'react';
import { Check, Loader2, Settings2 } from 'lucide-react';
import { api, WorkflowConfig } from '@/lib/api';
import { cn } from '@/lib/utils';

interface WorkflowSettingsProps {
  className?: string;
}

export function WorkflowSettings({ className }: WorkflowSettingsProps) {
  const [config, setConfig] = useState<WorkflowConfig | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saveResult, setSaveResult] = useState<{ success: boolean; message: string } | null>(null);
  const [maxIterations, setMaxIterations] = useState<number>(100);

  useEffect(() => {
    loadConfig();
  }, []);

  const loadConfig = async () => {
    try {
      setLoading(true);
      const data = await api.settings.getWorkflowConfig();
      setConfig(data);
      setMaxIterations(data.max_iterations);
    } catch (error) {
      console.error('Failed to load workflow config:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    try {
      setSaving(true);
      setSaveResult(null);
      const updated = await api.settings.updateWorkflowConfig({
        max_iterations: maxIterations,
      });
      setConfig(updated);
      setSaveResult({ success: true, message: 'Settings saved successfully!' });
    } catch (error) {
      console.error('Failed to save workflow config:', error);
      setSaveResult({ success: false, message: 'Failed to save settings' });
    } finally {
      setSaving(false);
    }
  };

  const hasChanges = config && maxIterations !== config.max_iterations;

  if (loading) {
    return (
      <div className={cn("rounded-lg border bg-card p-6", className)}>
        <div className="flex items-center justify-center py-8">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        </div>
      </div>
    );
  }

  return (
    <div className={cn("rounded-lg border bg-card", className)}>
      <div className="border-b p-4">
        <div className="flex items-center gap-2">
          <Settings2 className="h-5 w-5 text-primary" />
          <h3 className="font-semibold">Workflow Settings</h3>
        </div>
        <p className="text-sm text-muted-foreground mt-1">
          Configure workflow execution parameters
        </p>
      </div>

      <div className="p-4 space-y-6">
        {/* Max Iterations */}
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <label className="text-sm font-medium">Max Iterations</label>
            <span className="text-sm text-muted-foreground">{maxIterations}</span>
          </div>
          <input
            type="range"
            min="10"
            max="500"
            step="10"
            value={maxIterations}
            onChange={(e) => setMaxIterations(parseInt(e.target.value))}
            className="w-full h-2 bg-muted rounded-lg appearance-none cursor-pointer accent-primary"
          />
          <div className="flex justify-between text-xs text-muted-foreground">
            <span>10 (Quick)</span>
            <span>500 (Thorough)</span>
          </div>
          <p className="text-xs text-muted-foreground mt-2">
            Maximum number of agent iterations per workflow run. Higher values allow more thorough processing but may take longer.
          </p>
        </div>

        {/* Save Result Message */}
        {saveResult && (
          <div
            className={cn(
              "flex items-center gap-2 p-3 rounded-lg text-sm",
              saveResult.success
                ? "bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400"
                : "bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400"
            )}
          >
            {saveResult.success && <Check className="h-4 w-4" />}
            {saveResult.message}
          </div>
        )}

        {/* Save Button */}
        <div className="flex justify-end">
          <button
            onClick={handleSave}
            disabled={saving || !hasChanges}
            className={cn(
              "flex items-center gap-2 px-4 py-2 rounded-lg font-medium transition-colors",
              hasChanges
                ? "bg-primary text-primary-foreground hover:bg-primary/90"
                : "bg-muted text-muted-foreground cursor-not-allowed"
            )}
          >
            {saving && <Loader2 className="h-4 w-4 animate-spin" />}
            Save Changes
          </button>
        </div>
      </div>
    </div>
  );
}
