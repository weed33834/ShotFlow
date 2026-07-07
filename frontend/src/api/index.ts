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
  Keyframe,
  KeyframeCreate,
  Project,
  ProjectCreate,
  ProjectUpdate,
  QaReport,
  QaReportCreate,
  QueueStats,
  RenderTask,
  RenderTaskCreate,
  RenderTaskStatus,
  Shot,
  ShotCreate,
  ShotUpdate,
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
