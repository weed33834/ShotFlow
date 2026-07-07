// 镜头管理 — 按项目过滤 + 新建/编辑/删除
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { App, Button, Card, Form, Input, InputNumber, Modal, Popconfirm, Select, Space, Table } from "antd";
import { useState } from "react";
import { projectsApi, shotsApi } from "@/api";
import type { Shot, ShotCreate, ShotUpdate } from "@/types";

const SHOT_TYPE_OPTS = [
  { value: "extreme_closeup", label: "极特写" },
  { value: "closeup", label: "特写" },
  { value: "medium", label: "中景" },
  { value: "wide", label: "全景" },
  { value: "extreme_wide", label: "大全景" },
];
const COMPLEXITY_OPTS = [
  { value: "standard", label: "标准" },
  { value: "complex", label: "复杂" },
];
const GEN_METHOD_OPTS = [
  { value: "wan_i2v", label: "Wan2.2 I2V" },
  { value: "wan_t2v", label: "Wan2.2 T2V" },
  { value: "kling", label: "可灵" },
];

export default function Shots() {
  const { message } = App.useApp();
  const qc = useQueryClient();
  const [projectId, setProjectId] = useState<number | undefined>();
  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState<Shot | null>(null);
  const [form] = Form.useForm<ShotCreate>();

  const { data: projects } = useQuery({
    queryKey: ["projects"],
    queryFn: () => projectsApi.list(),
  });
  const { data, isLoading } = useQuery({
    queryKey: ["shots", projectId],
    queryFn: () => shotsApi.list(projectId ? { project_id: projectId } : undefined),
  });

  const openCreate = () => {
    setEditing(null);
    form.resetFields();
    setOpen(true);
  };

  const openEdit = (record: Shot) => {
    setEditing(record);
    form.setFieldsValue(record);
    setOpen(true);
  };

  const createMut = useMutation({
    mutationFn: (payload: ShotCreate) => shotsApi.create(payload),
    onSuccess: () => {
      message.success("镜头已创建");
      qc.invalidateQueries({ queryKey: ["shots"] });
      setOpen(false);
    },
    onError: (e: Error) => message.error((e as Error & { friendlyMessage?: string }).friendlyMessage || e.message),
  });

  const updateMut = useMutation({
    mutationFn: ({ id, payload }: { id: number; payload: ShotUpdate }) =>
      shotsApi.update(id, payload),
    onSuccess: () => {
      message.success("已保存");
      qc.invalidateQueries({ queryKey: ["shots"] });
      setOpen(false);
    },
    onError: (e: Error) => message.error((e as Error & { friendlyMessage?: string }).friendlyMessage || e.message),
  });

  const delMut = useMutation({
    mutationFn: (id: number) => shotsApi.remove(id),
    onSuccess: () => {
      message.success("已删除");
      qc.invalidateQueries({ queryKey: ["shots"] });
    },
    onError: (e: Error) => message.error((e as Error & { friendlyMessage?: string }).friendlyMessage || e.message),
  });

  const submit = () =>
    form.validateFields().then((v) => {
      if (editing) updateMut.mutate({ id: editing.id, payload: v });
      else createMut.mutate(v);
    });

  return (
    <div>
      <Card
        title="镜头管理"
        extra={
          <>
            <Select
              allowClear
              placeholder="按项目过滤"
              style={{ width: 200, marginRight: 8 }}
              value={projectId}
              onChange={setProjectId}
              options={(projects ?? []).map((p) => ({ value: p.id, label: p.title }))}
            />
            <Button type="primary" onClick={openCreate}>
              新建镜头
            </Button>
          </>
        }
      >
        <Table<Shot>
          rowKey="id"
          loading={isLoading}
          dataSource={data ?? []}
          pagination={{ pageSize: 20, showSizeChanger: true }}
          scroll={{ x: 1000 }}
          columns={[
            { title: "镜头号", dataIndex: "shot_code", key: "shot_code", width: 100 },
            { title: "场景", dataIndex: "scene", key: "scene" },
            { title: "时长(s)", dataIndex: "duration", key: "duration", width: 80 },
            { title: "景别", dataIndex: "shot_type", key: "shot_type", width: 100 },
            { title: "复杂度", dataIndex: "complexity", key: "complexity", width: 80 },
            { title: "生成方式", dataIndex: "gen_method", key: "gen_method", width: 110 },
            { title: "运镜", dataIndex: "camera", key: "camera" },
            { title: "描述", dataIndex: "description", key: "description", ellipsis: true },
            {
              title: "操作",
              key: "action",
              width: 130,
              fixed: "right",
              render: (_, record) => (
                <Space>
                  <Button size="small" onClick={() => openEdit(record)}>
                    编辑
                  </Button>
                  <Popconfirm title="确认删除该镜头？" onConfirm={() => delMut.mutate(record.id)}>
                    <Button danger size="small" loading={delMut.isPending && delMut.variables === record.id}>删除</Button>
                  </Popconfirm>
                </Space>
              ),
            },
          ]}
        />
      </Card>

      <Modal
        title={editing ? "编辑镜头" : "新建镜头"}
        open={open}
        onCancel={() => setOpen(false)}
        onOk={submit}
        confirmLoading={createMut.isPending || updateMut.isPending}
      >
        <Form form={form} layout="vertical" initialValues={{ duration: 5, shot_type: "medium", complexity: "standard", gen_method: "wan_i2v", order: 0 }}>
          <Form.Item name="project_id" label="所属项目" rules={[{ required: true }]}>
            <Select
              options={(projects ?? []).map((p) => ({ value: p.id, label: p.title }))}
            />
          </Form.Item>
          <Form.Item name="shot_code" label="镜头号" rules={[{ required: true }]}>
            <Input placeholder="如 S01_01" />
          </Form.Item>
          <Form.Item name="scene" label="场景">
            <Input />
          </Form.Item>
          <Form.Item name="duration" label="时长(秒)">
            <InputNumber min={1} max={60} />
          </Form.Item>
          <Form.Item name="shot_type" label="景别">
            <Select options={SHOT_TYPE_OPTS} />
          </Form.Item>
          <Form.Item name="complexity" label="复杂度">
            <Select options={COMPLEXITY_OPTS} />
          </Form.Item>
          <Form.Item name="gen_method" label="生成方式">
            <Select options={GEN_METHOD_OPTS} />
          </Form.Item>
          <Form.Item name="camera" label="运镜">
            <Input />
          </Form.Item>
          <Form.Item name="description" label="描述">
            <Input.TextArea rows={2} />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
