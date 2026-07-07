// 项目管理 — 列表 + 新建/编辑/删除
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { App, Button, Card, Form, Input, Modal, Popconfirm, Select, Space, Table } from "antd";
import { useState } from "react";
import dayjs from "dayjs";
import { projectsApi } from "@/api";
import { ProjectStatusTag } from "@/components/StatusTag";
import type { Project, ProjectCreate, ProjectUpdate } from "@/types";

const STATUS_OPTIONS = [
  { value: "planning", label: "策划中" },
  { value: "pre_production", label: "预制作" },
  { value: "production", label: "生产中" },
  { value: "post_production", label: "后期" },
  { value: "release", label: "已发布" },
  { value: "archived", label: "已归档" },
];

export default function Projects() {
  const { message } = App.useApp();
  const qc = useQueryClient();
  const { data, isLoading } = useQuery({
    queryKey: ["projects"],
    queryFn: () => projectsApi.list(),
  });
  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState<Project | null>(null);
  const [form] = Form.useForm<ProjectCreate>();

  const openCreate = () => {
    setEditing(null);
    form.resetFields();
    setOpen(true);
  };

  const openEdit = (record: Project) => {
    setEditing(record);
    form.setFieldsValue({
      title: record.title,
      subtitle: record.subtitle,
      status: record.status,
      description: record.description,
    });
    setOpen(true);
  };

  const createMut = useMutation({
    mutationFn: (payload: ProjectCreate) => projectsApi.create(payload),
    onSuccess: () => {
      message.success("项目已创建");
      qc.invalidateQueries({ queryKey: ["projects"] });
      setOpen(false);
    },
    onError: (e: Error) => message.error((e as Error & { friendlyMessage?: string }).friendlyMessage || e.message),
  });

  const updateMut = useMutation({
    mutationFn: ({ id, payload }: { id: number; payload: ProjectUpdate }) =>
      projectsApi.update(id, payload),
    onSuccess: () => {
      message.success("已保存");
      qc.invalidateQueries({ queryKey: ["projects"] });
      setOpen(false);
    },
    onError: (e: Error) => message.error((e as Error & { friendlyMessage?: string }).friendlyMessage || e.message),
  });

  const delMut = useMutation({
    mutationFn: (id: number) => projectsApi.remove(id),
    onSuccess: () => {
      message.success("已删除");
      qc.invalidateQueries({ queryKey: ["projects"] });
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
        title="项目管理"
        extra={
          <Button type="primary" onClick={openCreate}>
            新建项目
          </Button>
        }
      >
        <Table<Project>
          rowKey="id"
          loading={isLoading}
          dataSource={data ?? []}
          pagination={{ pageSize: 20, showSizeChanger: true }}
          columns={[
            { title: "ID", dataIndex: "id", key: "id", width: 60 },
            { title: "标题", dataIndex: "title", key: "title" },
            { title: "副标题", dataIndex: "subtitle", key: "subtitle" },
            {
              title: "状态",
              dataIndex: "status",
              key: "status",
              render: (v: string) => <ProjectStatusTag status={v} />,
            },
            { title: "描述", dataIndex: "description", key: "description", ellipsis: true },
            {
              title: "更新时间",
              dataIndex: "updated_at",
              key: "updated_at",
              render: (v: string) => dayjs(v).format("YYYY-MM-DD HH:mm"),
            },
            {
              title: "操作",
              key: "action",
              width: 130,
              render: (_, record) => (
                <Space>
                  <Button size="small" onClick={() => openEdit(record)}>
                    编辑
                  </Button>
                  <Popconfirm title="确认删除该项目？" onConfirm={() => delMut.mutate(record.id)}>
                    <Button danger size="small" loading={delMut.isPending && delMut.variables === record.id}>删除</Button>
                  </Popconfirm>
                </Space>
              ),
            },
          ]}
        />
      </Card>

      <Modal
        title={editing ? "编辑项目" : "新建项目"}
        open={open}
        onCancel={() => setOpen(false)}
        onOk={submit}
        confirmLoading={createMut.isPending || updateMut.isPending}
      >
        <Form form={form} layout="vertical" initialValues={{ status: "planning" }}>
          <Form.Item name="title" label="标题" rules={[{ required: true }]}>
            <Input placeholder="如：奇点回响" />
          </Form.Item>
          <Form.Item name="subtitle" label="副标题">
            <Input />
          </Form.Item>
          <Form.Item name="status" label="状态">
            <Select options={STATUS_OPTIONS} />
          </Form.Item>
          <Form.Item name="description" label="描述">
            <Input.TextArea rows={3} />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
