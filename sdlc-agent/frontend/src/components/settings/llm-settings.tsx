'use client';

import { useEffect, useState } from 'react';
import { Check, Loader2, Cpu, Zap, TestTube } from 'lucide-react';
import { api, LLMConfig, LLMModelOption } from '@/lib/api';
import { cn } from '@/lib/utils';

interface LLMSettingsProps {
  className?: string;
}

export function LLMSettings({ className }: LLMSettingsProps) {
  const [config, setConfig] = useState<LLMConfig | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<{ success: boolean; message: string } | null>(null);
  const [selectedModel, setSelectedModel] = useState<string>('');
  const [temperature, setTemperature] = useState<number>(0.1);
  const [maxTokens, setMaxTokens] = useState<number>(4096);

  useEffect(() => {
    loadConfig();
  }, []);

  const loadConfig = async () => {
    try {
      setLoading(true);
      const data = await api.settings.getLlmConfig();
      setConfig(data);
      setSelectedModel(data.current_model);
      setTemperature(data.temperature);
      setMaxTokens(data.max_tokens);
    } catch (error) {
      console.error('Failed to load LLM config:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    try {
      setSaving(true);
      setTestResult(null);
      const updated = await api.settings.updateLlmConfig({
        model: selectedModel,
        temperature,
        max_tokens: maxTokens,
      });
      setConfig(updated);
      setTestResult({ success: true, message: 'Settings saved successfully!' });
    } catch (error) {
      console.error('Failed to save LLM config:', error);
      setTestResult({ success: false, message: 'Failed to save settings' });
    } finally {
      setSaving(false);
    }
  };

  const handleTest = async () => {
    try {
      setTesting(true);
      setTestResult(null);
      const result = await api.settings.testLlm();
      setTestResult({
        success: result.success,
        message: `Model responded: "${result.response}" (${result.tokens_used} tokens)`,
      });
    } catch (error) {
      console.error('LLM test failed:', error);
      setTestResult({ success: false, message: 'Test failed - check your configuration' });
    } finally {
      setTesting(false);
    }
  };

  const groupedModels = config?.available_models.reduce((acc, model) => {
    if (!acc[model.provider]) {
      acc[model.provider] = [];
    }
    acc[model.provider].push(model);
    return acc;
  }, {} as Record<string, LLMModelOption[]>) || {};

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
          <Cpu className="h-5 w-5 text-primary" />
          <h3 className="font-semibold">LLM Configuration</h3>
        </div>
        <p className="text-sm text-muted-foreground mt-1">
          Select the AI model for agent operations
        </p>
      </div>

      <div className="p-4 space-y-6">
        {/* Model Selection */}
        <div className="space-y-3">
          <label className="text-sm font-medium">Model</label>
          <div className="space-y-4">
            {Object.entries(groupedModels).map(([provider, models]) => (
              <div key={provider} className="space-y-2">
                <div className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
                  {provider === 'openai' ? 'OpenAI' : 'Anthropic'}
                </div>
                <div className="grid gap-2">
                  {models.map((model) => (
                    <button
                      key={model.id}
                      onClick={() => setSelectedModel(model.id)}
                      className={cn(
                        "flex items-center justify-between p-3 rounded-lg border text-left transition-colors",
                        selectedModel === model.id
                          ? "border-primary bg-primary/5"
                          : "border-border hover:border-primary/50 hover:bg-muted/50"
                      )}
                    >
                      <div className="flex items-center gap-3">
                        <div className={cn(
                          "w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold",
                          model.provider === 'anthropic' 
                            ? "bg-orange-100 text-orange-700 dark:bg-orange-900 dark:text-orange-300"
                            : "bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300"
                        )}>
                          {model.provider === 'anthropic' ? 'C' : 'G'}
                        </div>
                        <div>
                          <div className="font-medium">{model.name}</div>
                          {model.description && (
                            <div className="text-xs text-muted-foreground">{model.description}</div>
                          )}
                        </div>
                      </div>
                      {selectedModel === model.id && (
                        <Check className="h-5 w-5 text-primary" />
                      )}
                    </button>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Temperature */}
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <label className="text-sm font-medium">Temperature</label>
            <span className="text-sm text-muted-foreground">{temperature.toFixed(2)}</span>
          </div>
          <input
            type="range"
            min="0"
            max="2"
            step="0.1"
            value={temperature}
            onChange={(e) => setTemperature(parseFloat(e.target.value))}
            className="w-full h-2 bg-muted rounded-lg appearance-none cursor-pointer accent-primary"
          />
          <div className="flex justify-between text-xs text-muted-foreground">
            <span>Precise</span>
            <span>Creative</span>
          </div>
        </div>

        {/* Max Tokens */}
        <div className="space-y-2">
          <label className="text-sm font-medium">Max Tokens</label>
          <input
            type="number"
            min="100"
            max="128000"
            value={maxTokens}
            onChange={(e) => setMaxTokens(parseInt(e.target.value) || 4096)}
            className="w-full px-3 py-2 rounded-md border bg-background text-sm"
          />
          <p className="text-xs text-muted-foreground">
            Maximum number of tokens in the response (100 - 128,000)
          </p>
        </div>

        {/* Test Result */}
        {testResult && (
          <div className={cn(
            "p-3 rounded-lg text-sm",
            testResult.success 
              ? "bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300"
              : "bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300"
          )}>
            {testResult.message}
          </div>
        )}

        {/* Actions */}
        <div className="flex gap-3 pt-2">
          <button
            onClick={handleSave}
            disabled={saving || !selectedModel}
            className={cn(
              "flex-1 flex items-center justify-center gap-2 px-4 py-2 rounded-md text-sm font-medium transition-colors",
              "bg-primary text-primary-foreground hover:bg-primary/90",
              "disabled:opacity-50 disabled:cursor-not-allowed"
            )}
          >
            {saving ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Zap className="h-4 w-4" />
            )}
            Save Changes
          </button>
          <button
            onClick={handleTest}
            disabled={testing}
            className={cn(
              "flex items-center justify-center gap-2 px-4 py-2 rounded-md text-sm font-medium transition-colors",
              "border hover:bg-muted",
              "disabled:opacity-50 disabled:cursor-not-allowed"
            )}
          >
            {testing ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <TestTube className="h-4 w-4" />
            )}
            Test
          </button>
        </div>

        {/* Current Config Info */}
        <div className="pt-4 border-t">
          <div className="text-xs text-muted-foreground">
            <div>Current: <span className="font-mono">{config?.current_model}</span></div>
            <div>Provider: {config?.current_provider}</div>
          </div>
        </div>
      </div>
    </div>
  );
}
