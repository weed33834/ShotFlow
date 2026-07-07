// 工作流管理
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { App, Button, Card, Form, Input, Modal, Popconfirm, Table } from "antd";
import { useState } from "react";
import dayjs from "dayjs";
import { workflowsApi } from "@/api";
import type { Workflow } from "@/types";

export default function Workflows() {
  const { message } = App.useApp();
  const qc = useQueryClient();
  const [open, setOpen] = useState(false);
  const [form] = Form.useForm();

  const { data, isLoading } = useQuery({
    queryKey: ["workflows"],
    queryFn: () => workflowsApi.list(),
  });

  const createMut = useMutation({
    mutationFn: workflowsApi.create,
    onSuccess: () => {
      message.success("工作流已创建");
      qc.invalidateQueries({ queryKey: ["workflows"] });
      setOpen(false);
      form.resetFields();
    },
    onError: (e: Error) => message.error((e as Error & { friendlyMessage?: string }).friendlyMessage || e.message),
  });

  const delMut = useMutation({
    mutationFn: workflowsApi.remove,
    onSuccess: () => {
      message.success("已删除");
      qc.invalidateQueries({ queryKey: ["workflows"] });
    },
    onError: (e: Error) => message.error((e as Error & { friendlyMessage?: string }).friendlyMessage || e.message),
  });

  return (
    <Card
      title="ComfyUI 工作流管理"
      extra={
        <Button type="primary" onClick={() => setOpen(true)}>
          新建工作流
        </Button>
      }
    >
      <Table<Workflow>
        rowKey="id"
        loading={isLoading}
        dataSource={data ?? []}
        pagination={{ pageSize: 20, showSizeChanger: true }}
        columns={[
          { title: "名称", dataIndex: "name", key: "name" },
          { title: "文件路径", dataIndex: "file_path", key: "file_path", ellipsis: true },
          { title: "描述", dataIndex: "description", key: "description", ellipsis: true },
          {
            title: "更新时间",
            dataIndex: "updated_at",
            key: "updated_at",
            render: (v: string) => dayjs(v).format("MM-DD HH:mm"),
          },
          {
            title: "操作",
            key: "action",
            width: 80,
            render: (_, record) => (
              <Popconfirm title="确认删除该工作流？" onConfirm={() => delMut.mutate(record.id)}>
                <Button danger size="small" loading={delMut.isPending && delMut.variables === record.id}>删除</Button>
              </Popconfirm>
            ),
          },
        ]}
      />

      <Modal
        title="新建工作流"
        open={open}
        onCancel={() => setOpen(false)}
        onOk={() => form.validateFields().then((v) => createMut.mutate(v))}
        confirmLoading={createMut.isPending}
      >
        <Form form={form} layout="vertical">
          <Form.Item name="name" label="名称" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="file_path" label="文件路径">
            <Input placeholder="如 03_Workflows/api/Flux_Character_Consistency_api.json" />
          </Form.Item>
          <Form.Item name="description" label="描述">
            <Input.TextArea rows={2} />
          </Form.Item>
        </Form>
      </Modal>
    </Card>
  );
}
