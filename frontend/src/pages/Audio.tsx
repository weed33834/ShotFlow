// 对白配音管理
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { App, Button, Card, Form, Input, InputNumber, Modal, Select, Table, Tag } from "antd";
import { useState } from "react";
import { audioApi, shotsApi } from "@/api";
import type { Dialogue } from "@/types";

const ROLE_OPTS = [
  { value: "ava", label: "艾娃" },
  { value: "core", label: "核心" },
  { value: "narrator", label: "旁白" },
];

export default function AudioPage() {
  const { message } = App.useApp();
  const qc = useQueryClient();
  const [open, setOpen] = useState(false);
  const [form] = Form.useForm();

  const { data: shots } = useQuery({ queryKey: ["shots"], queryFn: () => shotsApi.list() });
  const { data, isLoading } = useQuery({
    queryKey: ["dialogues"],
    queryFn: () => audioApi.list(),
  });

  const createMut = useMutation({
    mutationFn: audioApi.create,
    onSuccess: () => {
      message.success("对白已创建");
      qc.invalidateQueries({ queryKey: ["dialogues"] });
      setOpen(false);
      form.resetFields();
    },
    onError: (e: Error) => message.error((e as Error & { friendlyMessage?: string }).friendlyMessage || e.message),
  });

  return (
    <Card
      title="对白配音"
      extra={
        <Button type="primary" onClick={() => setOpen(true)}>
          新建对白
        </Button>
      }
    >
      <Table<Dialogue>
        rowKey="id"
        loading={isLoading}
        dataSource={data ?? []}
        pagination={{ pageSize: 20, showSizeChanger: true }}
        columns={[
          {
            title: "角色",
            dataIndex: "role",
            key: "role",
            width: 90,
            render: (v: string) => <Tag color="purple">{v}</Tag>,
          },
          { title: "对白", dataIndex: "text", key: "text", ellipsis: true },
          { title: "情绪", dataIndex: "emotion", key: "emotion", width: 90 },
          { title: "时间码(s)", dataIndex: "start_time", key: "start_time", width: 90 },
          {
            title: "配音状态",
            dataIndex: "status",
            key: "status",
            width: 100,
            render: (v: string) => <Tag color={v === "completed" ? "success" : "default"}>{v}</Tag>,
          },
          { title: "音频路径", dataIndex: "audio_path", key: "audio_path", ellipsis: true },
        ]}
      />

      <Modal
        title="新建对白"
        open={open}
        onCancel={() => setOpen(false)}
        onOk={() => form.validateFields().then((v) => createMut.mutate(v))}
        confirmLoading={createMut.isPending}
      >
        <Form form={form} layout="vertical" initialValues={{ role: "ava", start_time: 0 }}>
          <Form.Item name="shot_id" label="所属镜头">
            <Select
              allowClear
              options={(shots ?? []).map((s) => ({ value: s.id, label: s.shot_code }))}
            />
          </Form.Item>
          <Form.Item name="role" label="角色" rules={[{ required: true }]}>
            <Select options={ROLE_OPTS} />
          </Form.Item>
          <Form.Item name="text" label="对白" rules={[{ required: true }]}>
            <Input.TextArea rows={2} />
          </Form.Item>
          <Form.Item name="emotion" label="情绪">
            <Input placeholder="如 坚定/低沉" />
          </Form.Item>
          <Form.Item name="start_time" label="时间码(秒)">
            <InputNumber min={0} step={0.1} />
          </Form.Item>
        </Form>
      </Modal>
    </Card>
  );
}
