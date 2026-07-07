// 用户案例展示区 — 管理列表 + 新建/编辑/删除
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { App, Button, Card, Form, Input, InputNumber, Modal, Popconfirm, Select, Space, Table, Tag } from "antd";
import { useState } from "react";
import dayjs from "dayjs";
import { caseStudiesApi } from "@/api";
import type { CaseStudy, CaseStudyCreate, CaseStudyStatus, CaseStudyUpdate } from "@/types";

const STATUS_OPTIONS: { value: CaseStudyStatus; label: string }[] = [
  { value: "draft", label: "草稿" },
  { value: "published", label: "已发布" },
  { value: "archived", label: "已归档" },
];

const STATUS_COLOR: Record<CaseStudyStatus, string> = {
  draft: "default",
  published: "green",
  archived: "gray",
};

type FormValues = CaseStudyCreate;

export default function CaseStudies() {
  const { message } = App.useApp();
  const qc = useQueryClient();
  const { data, isLoading } = useQuery({
    queryKey: ["case-studies", "admin"],
    queryFn: () => caseStudiesApi.adminList(),
  });
  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState<CaseStudy | null>(null);
  const [form] = Form.useForm<FormValues>();

  const openCreate = () => {
    setEditing(null);
    form.resetFields();
    setOpen(true);
  };

  const openEdit = (record: CaseStudy) => {
    setEditing(record);
    form.setFieldsValue({
      title: record.title,
      slug: record.slug,
      summary: record.summary,
      author: record.author,
      status: record.status,
      tags: record.tags,
      cover_image: record.cover_image,
      content_md: record.content_md,
      project_id: record.project_id ?? undefined,
    });
    setOpen(true);
  };

  const createMut = useMutation({
    mutationFn: (payload: CaseStudyCreate) => caseStudiesApi.create(payload),
    onSuccess: () => {
      message.success("案例已创建");
      qc.invalidateQueries({ queryKey: ["case-studies"] });
      setOpen(false);
    },
    onError: (e: Error) => message.error((e as Error & { friendlyMessage?: string }).friendlyMessage || e.message),
  });

  const updateMut = useMutation({
    mutationFn: ({ id, payload }: { id: number; payload: CaseStudyUpdate }) =>
      caseStudiesApi.update(id, payload),
    onSuccess: () => {
      message.success("已保存");
      qc.invalidateQueries({ queryKey: ["case-studies"] });
      setOpen(false);
    },
    onError: (e: Error) => message.error((e as Error & { friendlyMessage?: string }).friendlyMessage || e.message),
  });

  const delMut = useMutation({
    mutationFn: (id: number) => caseStudiesApi.remove(id),
    onSuccess: () => {
      message.success("已删除");
      qc.invalidateQueries({ queryKey: ["case-studies"] });
    },
    onError: (e: Error) => message.error((e as Error & { friendlyMessage?: string }).friendlyMessage || e.message),
  });

  const submit = () =>
    form.validateFields().then((v) => {
      // project_id 留空时传 null 给后端
      const payload: CaseStudyCreate = {
        ...v,
        project_id: v.project_id ?? null,
      };
      if (editing) updateMut.mutate({ id: editing.id, payload });
      else createMut.mutate(payload);
    });

  return (
    <div>
      <Card
        title="用户案例"
        extra={
          <Button type="primary" onClick={openCreate}>
            新建案例
          </Button>
        }
      >
        <Table<CaseStudy>
          rowKey="id"
          loading={isLoading}
          dataSource={data ?? []}
          pagination={{ pageSize: 20, showSizeChanger: true }}
          columns={[
            { title: "标题", dataIndex: "title", key: "title" },
            { title: "Slug", dataIndex: "slug", key: "slug" },
            {
              title: "状态",
              dataIndex: "status",
              key: "status",
              width: 100,
              render: (v: CaseStudyStatus) => (
                <Tag color={STATUS_COLOR[v]}>{v}</Tag>
              ),
            },
            { title: "作者", dataIndex: "author", key: "author", width: 120 },
            {
              title: "标签",
              dataIndex: "tags",
              key: "tags",
              render: (tags: string[]) =>
                (tags ?? []).map((t) => <Tag key={t}>{t}</Tag>),
            },
            {
              title: "创建时间",
              dataIndex: "created_at",
              key: "created_at",
              width: 160,
              render: (v: string) => dayjs(v).format("YYYY-MM-DD HH:mm"),
            },
            {
              title: "操作",
              key: "action",
              width: 140,
              render: (_, record) => (
                <Space>
                  <Button size="small" onClick={() => openEdit(record)}>
                    编辑
                  </Button>
                  <Popconfirm
                    title="确认删除该案例？"
                    onConfirm={() => delMut.mutate(record.id)}
                  >
                    <Button danger size="small" loading={delMut.isPending && delMut.variables === record.id}>
                      删除
                    </Button>
                  </Popconfirm>
                </Space>
              ),
            },
          ]}
        />
      </Card>

      <Modal
        title={editing ? "编辑案例" : "新建案例"}
        open={open}
        onCancel={() => setOpen(false)}
        onOk={submit}
        confirmLoading={createMut.isPending || updateMut.isPending}
        width={640}
      >
        <Form
          form={form}
          layout="vertical"
          initialValues={{ status: "draft", tags: [] }}
        >
          <Form.Item name="title" label="标题" rules={[{ required: true }]}>
            <Input placeholder="如：AIGC 短片《奇点回响》" />
          </Form.Item>
          <Form.Item name="slug" label="Slug" rules={[{ required: true }]}>
            <Input placeholder="全小写 + 连字符，如 shotflow-shortfilm" />
          </Form.Item>
          <Form.Item name="summary" label="摘要">
            <Input placeholder="一句话摘要，列表展示用" />
          </Form.Item>
          <Form.Item name="author" label="作者">
            <Input />
          </Form.Item>
          <Form.Item name="status" label="状态">
            <Select options={STATUS_OPTIONS} />
          </Form.Item>
          <Form.Item name="tags" label="标签">
            <Select mode="tags" placeholder="输入回车添加标签" />
          </Form.Item>
          <Form.Item name="cover_image" label="封面图路径">
            <Input placeholder="/covers/example.png" />
          </Form.Item>
          <Form.Item name="content_md" label="正文（Markdown）">
            <Input.TextArea rows={5} />
          </Form.Item>
          <Form.Item name="project_id" label="关联项目 ID">
            <InputNumber min={0} style={{ width: "100%" }} placeholder="可选" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
