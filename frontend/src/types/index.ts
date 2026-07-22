// 与后端 backend/app/schemas 对齐的 TypeScript 类型定义
// 单一事实来源：后端 schema 变更时同步更新此处

export interface Project {
  id: number;
  title: string;
  subtitle: string;
  status: string;
  description: string;
  config: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface ProjectCreate {
  title: string;
  subtitle?: string;
  status?: string;
  description?: string;
  config?: Record<string, unknown>;
}

export type ProjectUpdate = Partial<ProjectCreate>;

export interface Shot {
  id: number;
  project_id: number;
  shot_code: string;
  scene: string;
  duration: number;
  shot_type: string;
  complexity: string;
  gen_method: string;
  camera: string;
  description: string;
  order: number;
  created_at: string;
  updated_at: string;
}

export interface ShotCreate {
  project_id: number;
  shot_code: string;
  scene?: string;
  duration?: number;
  shot_type?: string;
  complexity?: string;
  gen_method?: string;
  camera?: string;
  description?: string;
  order?: number;
}

export type ShotUpdate = Partial<Omit<ShotCreate, "project_id">>;

export interface Keyframe {
  id: number;
  shot_id: number;
  label: string;
  prompt: string;
  negative_prompt: string;
  seed: number;
  has_ava: boolean;
  status: string;
  output_path: string;
  review_status: string;
  review_note: string;
  created_at: string;
  updated_at: string;
}

export interface KeyframeCreate {
  shot_id: number;
  label: string;
  prompt?: string;
  negative_prompt?: string;
  seed?: number;
  has_ava?: boolean;
}

export interface VideoClip {
  id: number;
  shot_id: number;
  provider: string;
  is_complex: boolean;
  params: Record<string, unknown>;
  status: string;
  output_path: string;
  duration: number;
  error: string;
  created_at: string;
  updated_at: string;
}

export interface VideoClipCreate {
  shot_id: number;
  provider?: string;
  is_complex?: boolean;
  params?: Record<string, unknown>;
}

export interface Dialogue {
  id: number;
  shot_id: number | null;
  role: string;
  text: string;
  emotion: string;
  start_time: number;
  status: string;
  audio_path: string;
  created_at: string;
  updated_at: string;
}

export interface DialogueCreate {
  shot_id?: number | null;
  role?: string;
  text?: string;
  emotion?: string;
  start_time?: number;
}

export type TaskType = "keyframe" | "video_i2v" | "video_t2v" | "kling" | "tts" | "music";
export type TaskStatus = "pending" | "running" | "completed" | "failed" | "cancelled";

export interface RenderTask {
  id: number;
  project_id: number | null;
  shot_id: number | null;
  task_type: TaskType;
  prompt: string;
  priority: number;
  status: TaskStatus;
  retry_count: number;
  max_retry: number;
  celery_task_id: string;
  extra: Record<string, unknown>;
  error: string;
  checkpoint: string;
  progress: number;
  worker_id: string;
  error_class: string;
  started_at: string | null;
  completed_at: string | null;
  failed_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface RenderTaskCreate {
  task_type: TaskType;
  prompt?: string;
  priority?: number;
  max_retry?: number;
  project_id?: number | null;
  shot_id?: number | null;
  extra?: Record<string, unknown>;
}

export interface RenderTaskStatus {
  id: number;
  task_type: TaskType;
  status: TaskStatus;
  retry_count: number;
  progress: number;
  error: string;
  celery_task_id: string;
}

export interface QueueStats {
  pending: number;
  running: number;
  completed: number;
  failed: number;
  cancelled: number;
  total: number;
}

export interface Workflow {
  id: number;
  name: string;
  file_path: string;
  description: string;
  parameters: Record<string, unknown>;
  node_dependencies: unknown[];
  created_at: string;
  updated_at: string;
}

export interface WorkflowCreate {
  name: string;
  file_path?: string;
  description?: string;
  parameters?: Record<string, unknown>;
  node_dependencies?: unknown[];
}

export interface QaReport {
  id: number;
  shot_id: number | null;
  defects: unknown[];
  severity: string;
  fix_status: string;
  fix_note: string;
  report_md: string;
  created_at: string;
  updated_at: string;
}

export interface QaReportCreate {
  shot_id?: number | null;
  defects?: unknown[];
  severity?: string;
  fix_status?: string;
  fix_note?: string;
  report_md?: string;
}

export interface DailyBrief {
  id: number;
  project_id: number | null;
  brief_date: string;
  author: string;
  content: string;
  created_at: string;
  updated_at: string;
}

export interface DailyBriefCreate {
  project_id?: number | null;
  brief_date: string;
  author?: string;
  content?: string;
}

export interface MessageResponse {
  message: string;
  ok: boolean;
}

export interface HealthResponse {
  status: string;
  app: string;
  version: string;
  db: string;
  redis: string;
  timestamp: string;
}

export interface UserOut {
  id: number;
  username: string;
  email: string;
  full_name: string;
  role: string;
  is_active: boolean;
  is_superuser: boolean;
  created_at: string;
  updated_at: string;
}

export type CaseStudyStatus = "draft" | "published" | "archived";

export interface CaseStudy {
  id: number;
  title: string;
  slug: string;
  summary: string;
  content_md: string;
  cover_image: string;
  author: string;
  status: CaseStudyStatus;
  tags: string[];
  meta: Record<string, unknown>;
  project_id: number | null;
  created_at: string;
  updated_at: string;
}

export interface CaseStudyCreate {
  title: string;
  slug: string;
  summary?: string;
  content_md?: string;
  cover_image?: string;
  author?: string;
  status?: CaseStudyStatus;
  tags?: string[];
  meta?: Record<string, unknown>;
  project_id?: number | null;
}

export type CaseStudyUpdate = Partial<CaseStudyCreate>;

// 一句话出片 — 自然语言生成接口类型
export type OutputType = "video" | "image_set" | "micro_movie" | "comic" | "vn";

export interface GenerateRequest {
  nl_prompt: string;
  output_type: OutputType;
  video_aspect?: string;
  voice_name?: string;
  subtitle_enabled?: boolean;
  bgm_enabled?: boolean;
  // 上传的本地素材 asset_id 列表，S5 组装时追加到生成资产之后参与拼接
  local_asset_ids?: number[];
}

export interface GenerateResponse {
  spec_id: number;
  status: "simulated" | "generated";
  message: string;
}

// 工具资产结果
export interface ToolResult {
  asset_id: string;
  url: string;
  provider: string;
  meta: Record<string, unknown>;
}

// Provider 配置状态
export interface ProvidersConfig {
  providers: string[];
  simulate_mode: boolean;
  llm_configured: boolean;
  llm_provider: string;
  llm_model: string;
  ffmpeg_available: boolean;
}
