// 各资源 API — 基于 crud 工厂与手写特殊端点
import { crud, http } from "./client";
import type {
  CaseStudy,
  CaseStudyCreate,
  CaseStudyUpdate,
  DailyBrief,
  DailyBriefCreate,
  Dialogue,
  DialogueCreate,
  GenerateRequest,
  GenerateResponse,
  Keyframe,
  KeyframeCreate,
  Project,
  ProjectCreate,
  ProjectUpdate,
  ProvidersConfig,
  QaReport,
  QaReportCreate,
  QueueStats,
  RenderTask,
  RenderTaskCreate,
  RenderTaskStatus,
  Shot,
  ShotCreate,
  ShotUpdate,
  ToolResult,
  VideoClip,
  VideoClipCreate,
  Workflow,
  WorkflowCreate,
} from "@/types";

export const projectsApi = {
  ...crud<Project, ProjectCreate>("/projects"),
  update: (id: number, payload: ProjectUpdate) =>
    http.patch<Project>(`/projects/${id}`, payload).then((r) => r.data),
};

export const shotsApi = {
  ...crud<Shot, ShotCreate>("/shots"),
  update: (id: number, payload: ShotUpdate) =>
    http.patch<Shot>(`/shots/${id}`, payload).then((r) => r.data),
};

export const keyframesApi = crud<Keyframe, KeyframeCreate>("/keyframes");
export const videosApi = crud<VideoClip, VideoClipCreate>("/videos");
export const audioApi = crud<Dialogue, DialogueCreate>("/audio");
export const workflowsApi = crud<Workflow, WorkflowCreate>("/workflows");
export const qaApi = crud<QaReport, QaReportCreate>("/qa");
export const dailyApi = crud<DailyBrief, DailyBriefCreate>("/daily-briefs");

export const queueApi = {
  list: (params?: Record<string, unknown>) =>
    http.get<RenderTask[]>("/queue", { params }).then((r) => r.data),
  submit: (payload: RenderTaskCreate) =>
    http.post<RenderTask>("/queue", payload).then((r) => r.data),
  status: (id: number) =>
    http.get<RenderTaskStatus>(`/queue/${id}`).then((r) => r.data),
  retry: (id: number) =>
    http.post<RenderTask>(`/queue/${id}/retry`).then((r) => r.data),
  cancel: (id: number) =>
    http.post<RenderTask>(`/queue/${id}/cancel`).then((r) => r.data),
  update: (id: number, payload: { priority?: number }) =>
    http.patch<RenderTask>(`/queue/${id}`, payload).then((r) => r.data),
  stats: () => http.get<QueueStats>("/queue/stats").then((r) => r.data),
};

export const healthApi = {
  check: () =>
    http
      .get<{
        status: string;
        app: string;
        version: string;
        db: string;
        redis: string;
        timestamp: string;
      }>("/health")
      .then((r) => r.data),
};

export const caseStudiesApi = {
  list: () => http.get<CaseStudy[]>("/case-studies").then((r) => r.data),
  getBySlug: (slug: string) =>
    http.get<CaseStudy>(`/case-studies/${slug}`).then((r) => r.data),
  adminList: () =>
    http.get<CaseStudy[]>("/case-studies/admin/list").then((r) => r.data),
  create: (payload: CaseStudyCreate) =>
    http.post<CaseStudy>("/case-studies", payload).then((r) => r.data),
  update: (id: number, payload: CaseStudyUpdate) =>
    http.patch<CaseStudy>(`/case-studies/${id}`, payload).then((r) => r.data),
  remove: (id: number) =>
    http.delete<{ message: string }>(`/case-studies/${id}`).then((r) => r.data),
};

// 一句话出片 — 自然语言生成 + 工具资产
export const generateApi = {
  generate: (payload: GenerateRequest) =>
    http.post<GenerateResponse>("/generate", payload).then((r) => r.data),
  // 批量生成：同一 prompt 生成 count 个变体
  batch: (payload: GenerateRequest & { count: number }) =>
    http.post<GenerateResponse & { results: { spec_id: number | null; error: string | null }[] }>(
      "/generate/batch",
      payload,
    ).then((r) => r.data),
};

export const toolsApi = {
  assets: () =>
    http.get<ToolResult[]>("/tools/assets").then((r) => r.data),
  providers: () =>
    http.get<ProvidersConfig>("/tools/providers").then((r) => r.data),
  // 上传本地素材文件（图片/视频/音频），返回入库后的 Asset 信息
  upload: (file: File) => {
    const formData = new FormData();
    formData.append("file", file);
    return http
      .post<ToolResult>("/tools/upload", formData, {
        headers: { "Content-Type": "multipart/form-data" },
      })
      .then((r) => r.data);
  },
  // ASR 语音转文字
  transcribe: (assetId: number, language = "zh") =>
    http.post<{ text: string; segments: { start: number; end: number; text: string }[]; srt: string }>(
      "/tools/transcribe",
      null,
      { params: { asset_id: assetId, language } },
    ).then((r) => r.data),
  // editing_steps JSON 编辑引擎
  editingSteps: () =>
    http.get<{ steps: { name: string; type: string; parameters: Record<string, unknown> }[] }>(
      "/tools/editing-steps",
    ).then((r) => r.data),
  edit: (assetId: number, steps: { name: string; params?: Record<string, unknown> }[]) =>
    http.post<{ asset_id: number; output_path: string; status: string }>(
      "/tools/edit",
      steps,
      { params: { asset_id: assetId } },
    ).then((r) => r.data),
  // 自动发布
  publishConfig: () =>
    http.get<{ platforms: string[]; douyin_configured: boolean; bilibili_configured: boolean }>(
      "/tools/publish/config",
    ).then((r) => r.data),
  publish: (payload: {
    asset_id: number;
    platform: string;
    title?: string;
    description?: string;
    tags?: string[];
  }) =>
    http.post<{
      success: boolean;
      platform: string;
      video_url: string;
      publish_id: string;
      error: string;
    }>("/tools/publish", payload).then((r) => r.data),
};
