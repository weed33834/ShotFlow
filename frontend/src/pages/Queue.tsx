// 渲染队列 — SSE 实时状态 + 提交/重试/取消
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  App,
  Badge,
  Button,
  Card,
  Col,
  Form,
  Input,
  InputNumber,
  Modal,
  Progress,
  Row,
  Select,
  Space,
  Statistic,
  Table,
  Tag,
} from "antd";
import { useEffect, useState } from "react";
import dayjs from "dayjs";
import { queueApi } from "@/api";
import { TaskStatusTag, TaskTypeTag } from "@/components/StatusTag";
import { useQueueStream } from "@/hooks/useQueueStream";
import type { RenderTask, RenderTaskCreate, TaskStatus, TaskType } from "@/types";

const TASK_TYPE_OPTS: { value: TaskType; label: string }[] = [
  { value: "keyframe", label: "关键帧" },
  { value: "video_i2v", label: "图生视频" },
  { value: "video_t2v", label: "文生视频" },
  { value: "kling", label: "可灵" },
  { value: "tts", label: "配音" },
  { value: "music", label: "配乐" },
];

const STATUS_FILTER_OPTS: { value: TaskStatus | "all"; label: string }[] = [
  { value: "all", label: "全部" },
  { value: "pending", label: "待执行" },
  { value: "running", label: "执行中" },
  { value: "completed", label: "已完成" },
  { value: "failed", label: "已失败" },
  { value: "cancelled", label: "已取消" },
];

export default function Queue() {
  const { message } = App.useApp();
  const qc = useQueryClient();
  const [open, setOpen] = useState(false);
  const [form] = Form.useForm<RenderTaskCreate>();
  const [statusFilter, setStatusFilter] = useState<TaskStatus | "all">("all");
  // 优先级行内编辑：当前编辑行 id 与暂存值
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editingValue, setEditingValue] = useState<number>(0);
  const live = useQueueStream(true);

  const { data, isLoading } = useQuery({
    queryKey: ["queue", statusFilter],
    queryFn: () =>
      queueApi.list(statusFilter === "all" ? undefined : { status: statusFilter }),
    // SSE 推送时手动刷新；同时保留 10s 兜底轮询
    refetchInterval: 10_000,
  });

  // SSE 有新数据时刷新列表
  useEffect(() => {
    if (live.stats) qc.invalidateQueries({ queryKey: ["queue"] });
  }, [live.stats, qc]);

  const submitMut = useMutation({
    mutationFn: (payload: RenderTaskCreate) => queueApi.submit(payload),
    onSuccess: () => {
      message.success("任务已提交");
      qc.invalidateQueries({ queryKey: ["queue"] });
      setOpen(false);
      form.resetFields();
    },
    onError: (e: Error) => message.error((e as Error & { friendlyMessage?: string }).friendlyMessage || e.message),
  });

  const retryMut = useMutation({
    mutationFn: queueApi.retry,
    onSuccess: () => {
      message.success("已重试");
      qc.invalidateQueries({ queryKey: ["queue"] });
    },
    onError: (e: Error) => message.error((e as Error & { friendlyMessage?: string }).friendlyMessage || e.message),
  });

  const cancelMut = useMutation({
    mutationFn: queueApi.cancel,
    onSuccess: () => {
      message.success("已取消");
      qc.invalidateQueries({ queryKey: ["queue"] });
    },
    onError: (e: Error) => message.error((e as Error & { friendlyMessage?: string }).friendlyMessage || e.message),
  });

  // 更新优先级
  const priorityMut = useMutation({
    mutationFn: ({ id, priority }: { id: number; priority: number }) =>
      queueApi.update(id, { priority }),
    onSuccess: () => {
      message.success("优先级已更新");
      qc.invalidateQueries({ queryKey: ["queue"] });
    },
    onError: (e: Error) => message.error((e as Error & { friendlyMessage?: string }).friendlyMessage || e.message),
  });

  // 提交优先级编辑：失焦或回车时触发（显式接收 id/value，避免依赖被竞态改写的 editingValue）
  const commitPriority = (id: number, value: number) => {
    setEditingId(null);
    priorityMut.mutate({ id, priority: value });
  };

  const s = live.stats;

  return (
    <div>
      <Card
        title={
          <Space>
            渲染队列
            <Badge status={live.connected ? "success" : "error"} text={live.connected ? "实时已连接" : "实时断开"} />
          </Space>
        }
        extra={
          <Button type="primary" onClick={() => setOpen(true)}>
            提交任务
          </Button>
        }
      >
        <Row gutter={16} style={{ marginBottom: 16 }}>
          <Col span={4}>
            <Statistic title="待执行" value={s?.pending ?? 0} />
          </Col>
          <Col span={4}>
            <Statistic title="执行中" value={s?.running ?? 0} valueStyle={{ color: "#1677ff" }} />
          </Col>
          <Col span={4}>
            <Statistic title="已完成" value={s?.completed ?? 0} valueStyle={{ color: "#52c41a" }} />
          </Col>
          <Col span={4}>
            <Statistic title="已失败" value={s?.failed ?? 0} valueStyle={{ color: "#ff4d4f" }} />
          </Col>
          <Col span={4}>
            <Statistic title="已取消" value={s?.cancelled ?? 0} valueStyle={{ color: "#faad14" }} />
          </Col>
          <Col span={4}>
            <Statistic title="总计" value={s?.total ?? 0} />
          </Col>
        </Row>

        <Row justify="end" style={{ marginBottom: 16 }}>
          <Col>
            <Space>
              <span>状态筛选</span>
              <Select
                style={{ width: 160 }}
                value={statusFilter}
                onChange={(val: TaskStatus | "all") => setStatusFilter(val)}
                options={STATUS_FILTER_OPTS}
              />
            </Space>
          </Col>
        </Row>

        <Table<RenderTask>
          rowKey="id"
          loading={isLoading}
          dataSource={data ?? []}
          pagination={{ pageSize: 20, showSizeChanger: true }}
          scroll={{ x: 1100 }}
          columns={[
            { title: "ID", dataIndex: "id", key: "id", width: 60 },
            {
              title: "类型",
              dataIndex: "task_type",
              key: "task_type",
              width: 100,
              render: (v: string) => <TaskTypeTag type={v} />,
            },
            { title: "提示词", dataIndex: "prompt", key: "prompt", ellipsis: true },
            {
              title: "优先级",
              dataIndex: "priority",
              key: "priority",
              width: 90,
              render: (v: number, record) => {
                // 已完成/已取消不允许编辑
                const editable = record.status !== "completed" && record.status !== "cancelled";
                if (editingId === record.id) {
                  return (
                    <InputNumber
                      size="small"
                      min={0}
                      max={100}
                      value={editingValue}
                      onChange={(val) => setEditingValue(val ?? 0)}
                      onBlur={() => commitPriority(record.id, editingValue)}
                      onPressEnter={() => commitPriority(record.id, editingValue)}
                    />
                  );
                }
                return (
                  <span
                    style={{ cursor: editable ? "pointer" : "default", color: editable ? "#1677ff" : undefined }}
                    onClick={() => {
                      if (!editable) return;
                      setEditingId(record.id);
                      setEditingValue(v);
                    }}
                  >
                    {v}
                  </span>
                );
              },
            },
            {
              title: "状态",
              dataIndex: "status",
              key: "status",
              width: 90,
              render: (v: string) => <TaskStatusTag status={v as TaskStatus} />,
            },
            {
              title: "进度",
              dataIndex: "progress",
              key: "progress",
              width: 140,
              render: (v: number, record) => {
                // completed 显示 100% 绿色；running 显示蓝色实际进度；其余灰色 0%
                if (record.status === "completed") {
                  return <Progress percent={100} size="small" status="success" />;
                }
                if (record.status === "running") {
                  return <Progress percent={v ?? 0} size="small" />;
                }
                return <Progress percent={0} size="small" strokeColor="#d9d9d9" />;
              },
            },
            { title: "重试", key: "retry", width: 70, render: (_, r) => `${r.retry_count}/${r.max_retry}` },
            {
              title: "创建时间",
              dataIndex: "created_at",
              key: "created_at",
              width: 140,
              render: (v: string) => dayjs(v).format("MM-DD HH:mm:ss"),
            },
            {
              title: "错误",
              dataIndex: "error",
              key: "error",
              ellipsis: true,
              render: (v: string) => (v ? <Tag color="red">{v}</Tag> : "—"),
            },
            {
              title: "操作",
              key: "action",
              width: 140,
              render: (_, record) => (
                <Space>
                  <Button
                    size="small"
                    disabled={record.status === "running" || record.status === "pending"}
                    onClick={() => retryMut.mutate(record.id)}
                  >
                    重试
                  </Button>
                  <Button
                    size="small"
                    danger
                    disabled={record.status === "completed" || record.status === "cancelled"}
                    onClick={() => cancelMut.mutate(record.id)}
                  >
                    取消
                  </Button>
                </Space>
              ),
            },
          ]}
        />
      </Card>

      <Modal
        title="提交渲染任务"
        open={open}
        onCancel={() => setOpen(false)}
        onOk={() => form.validateFields().then((v) => submitMut.mutate(v))}
        confirmLoading={submitMut.isPending}
      >
        <Form form={form} layout="vertical" initialValues={{ task_type: "keyframe", priority: 0, max_retry: 3 }}>
          <Form.Item name="task_type" label="任务类型" rules={[{ required: true }]}>
            <Select options={TASK_TYPE_OPTS} />
          </Form.Item>
          <Form.Item name="prompt" label="提示词">
            <Input.TextArea rows={3} />
          </Form.Item>
          <Form.Item name="priority" label="优先级（越大越先）">
            <InputNumber min={0} max={100} />
          </Form.Item>
          <Form.Item name="max_retry" label="最大重试">
            <InputNumber min={0} max={10} />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
