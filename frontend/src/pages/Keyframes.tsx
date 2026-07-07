// 关键帧管理 — 按镜头过滤 + 提交关键帧生成任务
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { App, Button, Card, Form, Input, InputNumber, Modal, Select, Space, Table, Tag } from "antd";
import { useState } from "react";
import { keyframesApi, queueApi, shotsApi } from "@/api";
import type { Keyframe } from "@/types";

export default function Keyframes() {
  const { message } = App.useApp();
  const qc = useQueryClient();
  const [shotId, setShotId] = useState<number | undefined>();
  const [open, setOpen] = useState(false);
  const [form] = Form.useForm();

  const { data: shots } = useQuery({ queryKey: ["shots"], queryFn: () => shotsApi.list() });
  const { data, isLoading } = useQuery({
    queryKey: ["keyframes", shotId],
    queryFn: () => keyframesApi.list(shotId ? { shot_id: shotId } : undefined),
  });

  const createMut = useMutation({
    mutationFn: keyframesApi.create,
    onSuccess: () => {
      message.success("关键帧已创建");
      qc.invalidateQueries({ queryKey: ["keyframes"] });
      setOpen(false);
      form.resetFields();
    },
    onError: (e: Error) => message.error((e as Error & { friendlyMessage?: string }).friendlyMessage || e.message),
  });

  const submitGenMut = useMutation({
    mutationFn: (kf: Keyframe) =>
      queueApi.submit({
        task_type: "keyframe",
        prompt: kf.prompt,
        shot_id: kf.shot_id,
        extra: { seed: kf.seed, label: kf.label },
      }),
    onSuccess: () => {
      message.success("已提交关键帧生成任务");
      qc.invalidateQueries({ queryKey: ["queue"] });
    },
    onError: (e: Error) => message.error((e as Error & { friendlyMessage?: string }).friendlyMessage || e.message),
  });

  return (
    <div>
      <Card
        title="关键帧管理"
        extra={
          <Space>
            <Select
              allowClear
              placeholder="按镜头过滤"
              style={{ width: 180 }}
              value={shotId}
              onChange={setShotId}
              options={(shots ?? []).map((s) => ({ value: s.id, label: s.shot_code }))}
            />
            <Button type="primary" onClick={() => setOpen(true)}>
              新建关键帧
            </Button>
          </Space>
        }
      >
        <Table<Keyframe>
          rowKey="id"
          loading={isLoading}
          dataSource={data ?? []}
          pagination={{ pageSize: 20, showSizeChanger: true }}
          scroll={{ x: 900 }}
          columns={[
            { title: "标签", dataIndex: "label", key: "label", width: 120 },
            { title: "提示词", dataIndex: "prompt", key: "prompt", ellipsis: true },
            { title: "Seed", dataIndex: "seed", key: "seed", width: 100 },
            {
              title: "含艾娃",
              dataIndex: "has_ava",
              key: "has_ava",
              width: 80,
              render: (v: boolean) => (v ? <Tag color="purple">是</Tag> : "否"),
            },
            {
              title: "状态",
              dataIndex: "status",
              key: "status",
              width: 90,
              render: (v: string) => <Tag color={v === "completed" ? "success" : v === "failed" ? "error" : "default"}>{v}</Tag>,
            },
            {
              title: "审核",
              dataIndex: "review_status",
              key: "review_status",
              width: 90,
              render: (v: string) => <Tag>{v}</Tag>,
            },
            {
              title: "操作",
              key: "action",
              width: 120,
              render: (_, record) => (
                <Button
                  size="small"
                  type="link"
                  loading={submitGenMut.isPending && submitGenMut.variables?.id === record.id}
                  onClick={() => submitGenMut.mutate(record)}
                >
                  提交生成
                </Button>
              ),
            },
          ]}
        />
      </Card>

      <Modal
        title="新建关键帧"
        open={open}
        onCancel={() => setOpen(false)}
        onOk={() =>
          form.validateFields().then((v) =>
            createMut.mutate({ ...v, shot_id: v.shot_id })
          )
        }
        confirmLoading={createMut.isPending}
      >
        <Form form={form} layout="vertical" initialValues={{ seed: 0, has_ava: true }}>
          <Form.Item name="shot_id" label="所属镜头" rules={[{ required: true }]}>
            <Select
              options={(shots ?? []).map((s) => ({ value: s.id, label: s.shot_code }))}
            />
          </Form.Item>
          <Form.Item name="label" label="标签" rules={[{ required: true }]}>
            <Input placeholder="如 S01_01" />
          </Form.Item>
          <Form.Item name="prompt" label="提示词">
            <Input.TextArea rows={3} />
          </Form.Item>
          <Form.Item name="seed" label="Seed">
            <InputNumber min={0} />
          </Form.Item>
          <Form.Item name="has_ava" label="含艾娃">
            <Select
              options={[
                { value: true, label: "是" },
                { value: false, label: "否" },
              ]}
            />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
