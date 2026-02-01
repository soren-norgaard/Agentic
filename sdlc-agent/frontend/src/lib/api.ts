const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

interface RequestOptions extends RequestInit {
  params?: Record<string, string>;
}

class ApiError extends Error {
  constructor(
    public status: number,
    public statusText: string,
    public data?: unknown
  ) {
    super(`API Error: ${status} ${statusText}`);
    this.name = 'ApiError';
  }
}

async function request<T>(endpoint: string, options: RequestOptions = {}): Promise<T> {
  const { params, ...fetchOptions } = options;
  
  let url = `${API_BASE_URL}${endpoint}`;
  
  if (params) {
    const searchParams = new URLSearchParams(params);
    url += `?${searchParams.toString()}`;
  }

  const response = await fetch(url, {
    ...fetchOptions,
    headers: {
      'Content-Type': 'application/json',
      ...fetchOptions.headers,
    },
  });

  if (!response.ok) {
    const data = await response.json().catch(() => null);
    throw new ApiError(response.status, response.statusText, data);
  }

  return response.json();
}

// Types
export interface Project {
  id: string;
  name: string;
  description: string;
  status: 'draft' | 'active' | 'paused' | 'completed' | 'archived';
  repository_url?: string;
  settings: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface Workflow {
  id: string;
  project_id: string;
  name: string;
  status: 'pending' | 'running' | 'paused' | 'awaiting_input' | 'completed' | 'failed' | 'cancelled';
  phase: string;
  state: Record<string, unknown>;
  current_state?: {
    iteration_count?: number;
    phase?: string;
    [key: string]: unknown;
  };
  checkpoint_id?: string;
  started_at?: string;
  completed_at?: string;
  created_at: string;
  updated_at: string;
}

export interface Task {
  id: string;
  workflow_id: string;
  parent_task_id?: string;
  type: 'epic' | 'story' | 'bug' | 'spike' | 'task' | 'subtask';
  title: string;
  description?: string;
  acceptance_criteria?: string[];
  status: 'backlog' | 'ready' | 'in_progress' | 'in_review' | 'testing' | 'done' | 'blocked';
  priority: 'low' | 'medium' | 'high' | 'critical';
  assigned_agent?: string;
  estimation_points?: number;
  created_at: string;
  updated_at: string;
}

export interface AgentExecution {
  id: string;
  workflow_id: string;
  task_id?: string;
  agent_type: string;
  agent_name: string;
  status: 'started' | 'running' | 'completed' | 'failed' | 'cancelled';
  success?: boolean;
  input_state?: Record<string, unknown>;
  input_data?: Record<string, unknown>;
  output_state?: Record<string, unknown>;
  output_data?: Record<string, unknown>;
  error_message?: string;
  tokens_used?: number;
  iterations?: number;
  cost_usd?: number;
  started_at: string;
  completed_at?: string;
}

export interface HumanInput {
  id: string;
  workflow_id: string;
  task_id?: string;
  agent_type?: string;
  request_type: 'clarification' | 'approval' | 'choice' | 'text' | 'review' | 'escalation';
  input_type?: string;
  prompt: string;
  options?: string[];
  context?: {
    phase?: string;
    options?: string;
    original_context?: string;
    [key: string]: unknown;
  };
  response?: string | null;
  is_resolved: boolean;
  requested_at: string;
  responded_at?: string | null;
  timeout_at?: string;
  created_at?: string;
}

export interface Artifact {
  id: string;
  workflow_id?: string;
  task_id?: string;
  name: string;
  artifact_type: string;
  file_path?: string;
  content?: string;
  extra_data: Record<string, unknown>;
  version: number;
  created_at: string;
  updated_at: string;
}

// Requirements traceability content structure
export interface RequirementsTraceability {
  original_requirements: string;
  human_inputs: Array<{
    type: string;
    question?: string;
    prompt?: string;
    context: string;
    options: string[];
    response: Record<string, unknown>;
    timestamp?: string;
  }>;
  requirements: {
    functional: Array<{
      id: string;
      type: string;
      title: string;
      description: string;
      priority: string;
    }>;
    non_functional: Array<{
      id: string;
      type: string;
      title: string;
      description: string;
      priority: string;
    }>;
  };
  epics: Array<{
    id: string;
    db_id?: string;
    title: string;
    description: string;
    business_value?: string;
    requirement_ids: string[];  // Links to requirements
    story_count: number;
  }>;
  user_stories: Array<{
    id: string;
    db_id?: string;
    epic_id?: string;
    title: string;
    user_story: string;
    acceptance_criteria: Array<Record<string, unknown>>;
    requirement_ids: string[];  // Links to requirements
  }>;
  summary: {
    total_functional_requirements: number;
    total_non_functional_requirements: number;
    total_epics: number;
    total_stories: number;
    total_human_inputs: number;
  };
}

// Developer Brief types
export interface DeveloperBriefArtifact {
  id: string;
  workflow_id: string;
  name: string;
  artifact_type: 'developer_brief';
  content: string;  // Markdown content
  extra_data: {
    story_id: string;
    story_title: string;
    requirement_ids: string[];
  };
  created_at: string;
  updated_at: string;
}

export interface DevelopmentPrepRequest {
  story_id: string;
  story_title: string;
  story_description?: string;
  acceptance_criteria?: string[];
  requirement_ids?: string[];
  github_issue_number?: number;
}

export interface DevelopmentPrepResponse {
  success: boolean;
  brief_artifact_id?: string;
  brief_content?: string;
  github_comment_posted: boolean;
  message: string;
}

export interface ReviewPrepRequest {
  pr_number: number;
  pr_title: string;
  story_id?: string;
  story_title?: string;
  acceptance_criteria?: string[];
  files_changed?: Array<{ path: string; filename?: string }>;
}

export interface ReviewPrepResponse {
  success: boolean;
  brief_artifact_id?: string;
  brief_content?: string;
  github_comment_posted: boolean;
  message: string;
}

export interface WorkflowContinueRequest {
  target_phase: string;
  config?: Record<string, unknown>;
}

// GitHub Types
export interface GitHubConfig {
  configured: boolean;
  owner?: string;
  repo?: string;
  auto_sync_enabled: boolean;
}

export interface GitHubRepository {
  id: number;
  name: string;
  full_name: string;
  description: string;
  html_url: string;
  default_branch: string;
  open_issues_count: number;
  has_issues: boolean;
  private: boolean;
}

export interface GitHubIssueItem {
  number: number;
  title: string;
  state: string;
  labels: string[];
  assignee?: string;
  created_at: string;
  updated_at: string;
  html_url: string;
}

export interface SyncTaskResponse {
  success: boolean;
  github_issue_number: number;
  github_issue_url: string;
  task_id: string;
}

export interface SyncAllResponse {
  success: boolean;
  synced_count: number;
  failed_count: number;
  results: Array<{
    task_id: string;
    success: boolean;
    github_issue_number?: number;
    error?: string;
  }>;
}

export interface GitHubProject {
  id: string;
  number: number;
  title: string;
  url: string;
}

export interface SyncToProjectResponse {
  synced_count: number;
  failed_count: number;
  project_url: string;
  details: Array<{
    task_id: string;
    title: string;
    issue_number: number;
    project_item_id?: string;
    status?: string;
    failed?: boolean;
    error?: string;
  }>;
}

export interface PullFromGitHubResponse {
  synced_count: number;
  skipped_count: number;
  not_found_count: number;
  details: Array<{
    issue_number: number;
    issue_title: string;
    task_id?: string;
    action: string;
    old_status?: string;
    new_status?: string;
    github_status?: string;
    reason?: string;
    current_status?: string;
    message?: string;
  }>;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  skip: number;
  limit: number;
}

export interface HealthResponse {
  status: string;
  version: string;
  timestamp: string;
  checks?: Record<string, { status: string; latency_ms?: number }>;
}

// API Client
export const api = {
  // Health
  health: {
    check: () => request<HealthResponse>('/health'),
    ready: () => request<HealthResponse>('/health/ready'),
    live: () => request<HealthResponse>('/health/live'),
  },

  // Projects
  projects: {
    list: (skip = 0, limit = 20) =>
      request<PaginatedResponse<Project>>('/api/v1/projects', {
        params: { skip: String(skip), limit: String(limit) },
      }),
    
    get: (id: string) => request<Project>(`/api/v1/projects/${id}`),
    
    create: (data: { name: string; description: string; repository_url?: string; settings?: Record<string, unknown> }) =>
      request<Project>('/api/v1/projects', {
        method: 'POST',
        body: JSON.stringify(data),
      }),
    
    update: (id: string, data: Partial<Project>) =>
      request<Project>(`/api/v1/projects/${id}`, {
        method: 'PATCH',
        body: JSON.stringify(data),
      }),
    
    delete: (id: string) =>
      request<void>(`/api/v1/projects/${id}`, { method: 'DELETE' }),
  },

  // Workflows
  workflows: {
    list: (skip = 0, limit = 20, projectId?: string) =>
      request<PaginatedResponse<Workflow>>('/api/v1/workflows', {
        params: {
          skip: String(skip),
          limit: String(limit),
          ...(projectId && { project_id: projectId }),
        },
      }),
    
    get: (id: string) => request<Workflow>(`/api/v1/workflows/${id}`),
    
    create: (data: { project_id: string; name: string; description?: string; initial_state?: Record<string, unknown> }) =>
      request<Workflow>('/api/v1/workflows', {
        method: 'POST',
        body: JSON.stringify(data),
      }),
    
    start: (id: string) =>
      request<Workflow>(`/api/v1/workflows/${id}/start`, { method: 'POST' }),
    
    pause: (id: string) =>
      request<Workflow>(`/api/v1/workflows/${id}/pause`, { method: 'POST' }),
    
    resume: (id: string) =>
      request<Workflow>(`/api/v1/workflows/${id}/resume`, { method: 'POST' }),
    
    cancel: (id: string) =>
      request<Workflow>(`/api/v1/workflows/${id}/cancel`, { method: 'POST' }),
    
    submitHumanInput: (workflowId: string, inputId: string, response: string) =>
      request<Workflow>(`/api/v1/workflows/${workflowId}/human-input/${inputId}`, {
        method: 'POST',
        body: JSON.stringify({ response }),
      }),
    
    getTasks: (workflowId: string) =>
      request<Task[]>(`/api/v1/workflows/${workflowId}/tasks`),
    
    getExecutions: (workflowId: string) =>
      request<AgentExecution[]>(`/api/v1/workflows/${workflowId}/executions`),
    
    getArtifacts: (workflowId: string, artifactType?: string) =>
      request<{ items: Artifact[]; total: number }>(`/api/v1/workflows/${workflowId}/artifacts`, {
        params: artifactType ? { artifact_type: artifactType } : undefined,
      }),
    
    getArtifact: (workflowId: string, artifactId: string) =>
      request<Artifact>(`/api/v1/workflows/${workflowId}/artifacts/${artifactId}`),
    
    getPendingInputs: (workflowId: string) =>
      request<HumanInput[]>(`/api/v1/workflows/${workflowId}/pending-inputs`),
    
    getInputs: (workflowId: string) =>
      request<PaginatedResponse<HumanInput>>(`/api/v1/workflows/${workflowId}/inputs`),
    
    submitInput: (workflowId: string, inputId: string, response: string) =>
      request<Workflow>(`/api/v1/workflows/${workflowId}/input`, {
        method: 'POST',
        body: JSON.stringify({ 
          input_id: inputId,
          response: { text: response }
        }),
      }),

    action: (id: string, action: 'start' | 'pause' | 'resume' | 'cancel' | 'retry') =>
      request<Workflow>(`/api/v1/workflows/${id}/actions`, {
        method: 'POST',
        body: JSON.stringify({ action }),
      }),

    delete: (id: string) =>
      request<void>(`/api/v1/workflows/${id}`, { method: 'DELETE' }),

    // Continue workflow to next phase
    continue: (id: string, targetPhase: string, config?: Record<string, unknown>) =>
      request<Workflow>(`/api/v1/workflows/${id}/continue`, {
        method: 'POST',
        body: JSON.stringify({ target_phase: targetPhase, config: config || {} }),
      }),

    // Prepare development for a story
    prepareDevelopment: (workflowId: string, data: DevelopmentPrepRequest) =>
      request<DevelopmentPrepResponse>(`/api/v1/workflows/${workflowId}/prepare-development`, {
        method: 'POST',
        body: JSON.stringify(data),
      }),

    // Get developer briefs
    getDeveloperBriefs: (workflowId: string) =>
      request<{ items: Artifact[]; total: number }>(`/api/v1/workflows/${workflowId}/developer-briefs`),

    // Prepare review brief for a PR
    prepareReview: (workflowId: string, data: ReviewPrepRequest) =>
      request<ReviewPrepResponse>(`/api/v1/workflows/${workflowId}/prepare-review`, {
        method: 'POST',
        body: JSON.stringify(data),
      }),

    // Get review briefs
    getReviewBriefs: (workflowId: string) =>
      request<{ items: Artifact[]; total: number }>(`/api/v1/workflows/${workflowId}/review-briefs`),
  },

  // Tasks (Epics, Stories, Tasks)
  tasks: {
    list: (params?: {
      project_id?: string;
      parent_id?: string;
      task_type?: 'epic' | 'story' | 'task' | 'bug' | 'spike';
      status?: string;
      priority?: string;
      page?: number;
      page_size?: number;
    }) => {
      const queryParams: Record<string, string> = {};
      if (params?.project_id) queryParams.project_id = params.project_id;
      if (params?.parent_id) queryParams.parent_id = params.parent_id;
      if (params?.task_type) queryParams.task_type = params.task_type;
      if (params?.status) queryParams.status = params.status;
      if (params?.priority) queryParams.priority = params.priority;
      queryParams.page = String(params?.page || 1);
      queryParams.page_size = String(params?.page_size || 50);
      
      return request<TaskListResponse>('/api/v1/tasks', { params: queryParams });
    },
    
    get: (id: string) => request<TaskItem>(`/api/v1/tasks/${id}`),
    
    getHierarchy: (projectId: string) =>
      request<TaskItem[]>(`/api/v1/tasks/hierarchy/${projectId}`),
    
    getStats: (projectId: string) =>
      request<TaskStats>(`/api/v1/tasks/stats/${projectId}`),
    
    create: (data: {
      project_id: string;
      parent_id?: string;
      title: string;
      description?: string;
      task_type?: 'epic' | 'story' | 'task' | 'bug' | 'spike';
      status?: string;
      priority?: string;
      story_points?: number;
      acceptance_criteria?: Array<Record<string, string>>;
      labels?: string[];
    }) =>
      request<TaskItem>('/api/v1/tasks', {
        method: 'POST',
        body: JSON.stringify(data),
      }),
    
    update: (id: string, data: Partial<TaskItem>) =>
      request<TaskItem>(`/api/v1/tasks/${id}`, {
        method: 'PATCH',
        body: JSON.stringify(data),
      }),
    
    move: (id: string, newStatus: string) =>
      request<TaskItem>(`/api/v1/tasks/${id}/move`, {
        method: 'POST',
        params: { new_status: newStatus },
      }),
    
    breakdown: (id: string, additionalContext?: string) =>
      request<{ workflow_id: string; message: string }>(`/api/v1/tasks/${id}/breakdown`, {
        method: 'POST',
        body: JSON.stringify({ additional_context: additionalContext }),
      }),
    
    delete: (id: string) =>
      request<void>(`/api/v1/tasks/${id}`, { method: 'DELETE' }),

    getArtifacts: (taskId: string, artifactType?: string) => {
      const params: Record<string, string> = {};
      if (artifactType) params.artifact_type = artifactType;
      return request<Artifact[]>(`/api/v1/tasks/${taskId}/artifacts`, { params });
    },

    generateBrief: (taskId: string, additionalContext?: string) =>
      request<{ workflow_id: string; message: string }>(`/api/v1/tasks/${taskId}/generate-brief`, {
        method: 'POST',
        body: JSON.stringify({ additional_context: additionalContext }),
      }),
  },

  // GitHub Integration
  github: {
    getConfig: () => request<GitHubConfig>('/api/v1/github/config'),
    
    getRepository: () => request<GitHubRepository>('/api/v1/github/repository'),
    
    setupLabels: () =>
      request<{ success: boolean; labels_created: number; message: string }>(
        '/api/v1/github/setup-labels',
        { method: 'POST' }
      ),
    
    syncTask: (taskId: string) =>
      request<SyncTaskResponse>('/api/v1/github/sync-task', {
        method: 'POST',
        body: JSON.stringify({ task_id: taskId }),
      }),
    
    syncProject: (projectId: string, taskTypes?: string[], includeSynced?: boolean) => {
      const params: Record<string, string> = {};
      if (taskTypes) params.task_types = taskTypes.join(',');
      if (includeSynced) params.include_synced = 'true';
      return request<SyncAllResponse>(`/api/v1/github/sync-project/${projectId}`, {
        method: 'POST',
        params,
      });
    },
    
    listIssues: (state: string = 'open', labels?: string) => {
      const params: Record<string, string> = { state };
      if (labels) params.labels = labels;
      return request<GitHubIssueItem[]>('/api/v1/github/issues', { params });
    },
    
    importIssue: (issueNumber: number, projectId: string, taskType: string = 'task') =>
      request<{ success: boolean; task_id: string; title: string }>(
        '/api/v1/github/import-issue',
        {
          method: 'POST',
          body: JSON.stringify({
            issue_number: issueNumber,
            project_id: projectId,
            task_type: taskType,
          }),
        }
      ),
    
    // GitHub Projects
    listProjects: () => request<GitHubProject[]>('/api/v1/github/projects'),
    
    createProject: (title: string) =>
      request<GitHubProject>(`/api/v1/github/projects?title=${encodeURIComponent(title)}`, {
        method: 'POST',
      }),
    
    syncToProject: (projectId: string, projectNumber: number, statusMapping?: Record<string, string>) =>
      request<SyncToProjectResponse>(`/api/v1/github/sync-to-project/${projectId}`, {
        method: 'POST',
        body: JSON.stringify({
          project_number: projectNumber,
          status_mapping: statusMapping || {
            backlog: 'Backlog',
            todo: 'Todo',
            in_progress: 'In Progress',
            in_review: 'In Review',
            done: 'Done',
            blocked: 'Backlog',
          },
        }),
      }),
    
    // Configure project columns
    configureProjectColumns: (projectNumber: number) =>
      request<{ success: boolean; message: string }>(`/api/v1/github/projects/${projectNumber}/fields/options`, {
        method: 'PUT',
        body: JSON.stringify({
          field_name: 'Status',
          options: [
            { name: 'Backlog', color: 'GRAY', description: 'Not yet started' },
            { name: 'Todo', color: 'BLUE', description: 'Ready to work on' },
            { name: 'In Progress', color: 'YELLOW', description: 'Currently being worked on' },
            { name: 'In Review', color: 'PURPLE', description: 'Awaiting review' },
            { name: 'Done', color: 'GREEN', description: 'Completed' },
          ],
        }),
      }),
    
    // Pull from GitHub (bidirectional sync)
    pullFromGitHub: (projectId: string, projectNumber: number) =>
      request<PullFromGitHubResponse>(`/api/v1/github/pull-from-github/${projectId}`, {
        method: 'POST',
        body: JSON.stringify({
          project_number: projectNumber,
        }),
      }),
  },

  // Stats
  stats: {
    dashboard: () => request<DashboardStats>('/api/v1/stats/dashboard'),
  },

  // Settings
  settings: {
    getLlmConfig: () => request<LLMConfig>('/api/v1/settings/llm'),
    
    updateLlmConfig: (config: { model: string; temperature?: number; max_tokens?: number }) =>
      request<LLMConfig>('/api/v1/settings/llm', {
        method: 'PUT',
        body: JSON.stringify(config),
      }),
    
    testLlm: () =>
      request<LLMTestResult>('/api/v1/settings/llm/test', { method: 'POST' }),
    
    getWorkflowConfig: () => request<WorkflowConfig>('/api/v1/settings/workflow'),
    
    updateWorkflowConfig: (config: { max_iterations: number }) =>
      request<WorkflowConfig>('/api/v1/settings/workflow', {
        method: 'PUT',
        body: JSON.stringify(config),
      }),
  },

  // Pull Requests (Code Review Dashboard)
  prs: {
    list: (state: 'open' | 'closed' | 'all' = 'open') =>
      request<PRListResponse>('/api/v1/prs', { params: { state } }),
    
    get: (prNumber: number) =>
      request<PRSummary>(`/api/v1/prs/${prNumber}`),
    
    triggerReview: (prNumber: number, options?: { 
      submit_review?: boolean; 
      include_suggestions?: boolean;
    }) =>
      request<ReviewResponse>(`/api/v1/prs/${prNumber}/review`, {
        method: 'POST',
        body: JSON.stringify(options || { submit_review: true, include_suggestions: true }),
      }),
    
    runQualityCheck: (prNumber: number, options?: {
      check_tests?: boolean;
      check_lint?: boolean;
      check_types?: boolean;
      check_security?: boolean;
      post_comment?: boolean;
    }) =>
      request<QualityCheckResponse>(`/api/v1/prs/${prNumber}/quality`, {
        method: 'POST',
        body: JSON.stringify(options || { 
          check_tests: true, 
          check_lint: true, 
          check_types: true, 
          check_security: true,
          post_comment: true 
        }),
      }),
    
    getDashboard: () =>
      request<DashboardSummary>('/api/v1/prs/dashboard/summary'),
  },
};

// LLM Settings Types
export interface LLMModelOption {
  id: string;
  name: string;
  provider: string;
  description?: string;
}

export interface LLMConfig {
  current_provider: string;
  current_model: string;
  available_models: LLMModelOption[];
  temperature: number;
  max_tokens: number;
}

export interface LLMTestResult {
  success: boolean;
  model: string;
  response: string;
  tokens_used: number;
}

export interface WorkflowConfig {
  max_iterations: number;
}

// Stats Types
export interface MetricItem {
  label: string;
  value: string;
  change: number;
  change_label: string;
}

export interface DashboardStats {
  active_workflows: MetricItem;
  tasks_completed: MetricItem;
  avg_cycle_time: MetricItem;
  tokens_used: MetricItem;
}

// Task Types (for Backlog/Kanban)
export interface TaskItem {
  id: string;
  project_id: string;
  parent_id?: string;
  title: string;
  description?: string;
  task_type: 'epic' | 'story' | 'task' | 'bug' | 'spike';
  status: 'backlog' | 'todo' | 'in_progress' | 'in_review' | 'done' | 'blocked';
  priority: 'critical' | 'high' | 'medium' | 'low';
  story_points?: number;
  estimated_hours?: number;
  actual_hours?: number;
  acceptance_criteria: Array<{ Given?: string; When?: string; Then?: string; [key: string]: string | undefined }>;
  technical_notes?: string;
  labels: string[];
  external_id?: string;
  children_count?: number;
  children?: TaskItem[];
  created_at: string;
  updated_at: string;
}

export interface TaskStats {
  total: number;
  by_status: Record<string, number>;
  by_type: Record<string, number>;
  by_priority: Record<string, number>;
  total_story_points: number;
  completed_story_points: number;
}

export interface TaskListResponse {
  items: TaskItem[];
  total: number;
  page: number;
  page_size: number;
}

// PR Types (for Code Review Dashboard)
export interface PRSummary {
  number: number;
  title: string;
  author: string;
  branch: string;
  base: string;
  created_at: string;
  updated_at: string;
  review_status: 'pending' | 'in_progress' | 'reviewed' | 'approved' | 'changes_requested';
  quality_status: 'unknown' | 'passing' | 'warning' | 'failing';
  ci_status: 'unknown' | 'pending' | 'running' | 'success' | 'failure';
  files_changed: number;
  additions: number;
  deletions: number;
  test_coverage?: number;
  html_url: string;
  review_artifact_id?: string;
}

export interface PRListResponse {
  total: number;
  open_count: number;
  prs: PRSummary[];
}

export interface ReviewResponse {
  success: boolean;
  pr_number: number;
  files_analyzed: number;
  findings_count: number;
  review_brief?: string;
  review_submitted: boolean;
  artifact_id?: string;
  message: string;
}

export interface TestCoverageResult {
  files_changed: number;
  files_with_tests: number;
  coverage_percentage: number;
  missing_tests: string[];
  test_files_found: string[];
}

export interface QualityCheckResponse {
  success: boolean;
  pr_number: number;
  quality_status: 'unknown' | 'passing' | 'warning' | 'failing';
  test_coverage?: TestCoverageResult;
  lint_issues: number;
  type_errors: number;
  security_issues: number;
  summary_markdown: string;
  artifact_id?: string;
  posted_to_github: boolean;
}

export interface DashboardSummary {
  total_open_prs: number;
  pending_reviews: number;
  quality_passing: number;
  quality_failing: number;
  ci_passing: number;
  ci_failing: number;
  prs_needing_review: PRSummary[];
  prs_with_issues: PRSummary[];
  recent_reviews: Array<{
    pr_number: number;
    pr_title: string;
    created_at: string;
    findings_count: number;
  }>;
}
