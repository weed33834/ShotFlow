// 公共状态标签组件 — 统一任务状态、项目状态、质检严重度的颜色映射
import { Tag } from "antd";
import type { TaskStatus } from "@/types";

const TASK_STATUS_COLOR: Record<TaskStatus, string> = {
  pending: "default",
  running: "processing",
  completed: "success",
  failed: "error",
  cancelled: "warning",
};

export function TaskStatusTag({ status }: { status: TaskStatus }) {
  const label: Record<TaskStatus, string> = {
    pending: "待执行",
    running: "执行中",
    completed: "已完成",
    failed: "已失败",
    cancelled: "已取消",
  };
  return <Tag color={TASK_STATUS_COLOR[status]}>{label[status]}</Tag>;
}

const PROJECT_STATUS_COLOR: Record<string, string> = {
  planning: "default",
  pre_production: "blue",
  production: "processing",
  post_production: "gold",
  release: "success",
  archived: "default",
};

const PROJECT_STATUS_LABEL: Record<string, string> = {
  planning: "策划中",
  pre_production: "预制作",
  production: "生产中",
  post_production: "后期",
  release: "已发布",
  archived: "已归档",
};

export function ProjectStatusTag({ status }: { status: string }) {
  return (
    <Tag color={PROJECT_STATUS_COLOR[status] || "default"}>
      {PROJECT_STATUS_LABEL[status] || status}
    </Tag>
  );
}

const TASK_TYPE_LABEL: Record<string, string> = {
  keyframe: "关键帧",
  video_i2v: "图生视频",
  video_t2v: "文生视频",
  kling: "可灵",
  tts: "配音",
  music: "配乐",
};

export function TaskTypeTag({ type }: { type: string }) {
  return <Tag color="geekblue">{TASK_TYPE_LABEL[type] || type}</Tag>;
}

const SEVERITY_COLOR: Record<string, string> = {
  info: "blue",
  warning: "orange",
  critical: "red",
};

export function SeverityTag({ severity }: { severity: string }) {
  return <Tag color={SEVERITY_COLOR[severity] || "default"}>{severity}</Tag>;
}
