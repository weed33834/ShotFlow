// 质检报告
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { App, Button, Card, Form, Input, Modal, Select, Table } from "antd";
import { useState } from "react";
import dayjs from "dayjs";
import { qaApi, shotsApi } from "@/api";
import { SeverityTag } from "@/components/StatusTag";
import type { QaReport } from "@/types";

const SEVERITY_OPTS = [
  { value: "info", label: "提示" },
  { value: "warning", label: "警告" },
  { value: "critical", label: "严重" },
];
const FIX_STATUS_OPTS = [
  { value: "open", label: "待处理" },
  { value: "in_progress", label: "处理中" },
  { value: "resolved", label: "已解决" },
  { value: "wontfix", label: "不修复" },
];

export default function QA() {
  const { message } = App.useApp();
  const qc = useQueryClient();
  const [open, setOpen] = useState(false);
  const [form] = Form.useForm();

  const { data: shots } = useQuery({ queryKey: ["shots"], queryFn: () => shotsApi.list() });
  const { data, isLoading } = useQuery({
    queryKey: ["qa"],
    queryFn: () => qaApi.list(),
  });

  const createMut = useMutation({
    mutationFn: qaApi.create,
    onSuccess: () => {
      message.success("质检报告已创建");
      qc.invalidateQueries({ queryKey: ["qa"] });
      setOpen(false);
      form.resetFields();
    },
    onError: (e: Error) => message.error((e as Error & { friendlyMessage?: string }).friendlyMessage || e.message),
  });

  return (
    <Card
      title="质检报告"
      extra={
        <Button type="primary" onClick={() => setOpen(true)}>
          新建报告
        </Button>
      }
    >
      <Table<QaReport>
        rowKey="id"
        loading={isLoading}
        dataSource={data ?? []}
        pagination={{ pageSize: 20, showSizeChanger: true }}
        columns={[
          {
            title: "严重度",
            dataIndex: "severity",
            key: "severity",
            width: 80,
            render: (v: string) => <SeverityTag severity={v} />,
          },
          { title: "缺陷数", key: "defects", width: 80, render: (_, r) => (Array.isArray(r.defects) ? r.defects.length : 0) },
          { title: "修复状态", dataIndex: "fix_status", key: "fix_status", width: 100 },
          { title: "修复说明", dataIndex: "fix_note", key: "fix_note", ellipsis: true },
          { title: "报告", dataIndex: "report_md", key: "report_md", ellipsis: true },
          {
            title: "更新时间",
            dataIndex: "updated_at",
            key: "updated_at",
            width: 120,
            render: (v: string) => dayjs(v).format("MM-DD HH:mm"),
          },
        ]}
      />

      <Modal
        title="新建质检报告"
        open={open}
        onCancel={() => setOpen(false)}
        onOk={() => form.validateFields().then((v) => createMut.mutate(v))}
        confirmLoading={createMut.isPending}
      >
        <Form form={form} layout="vertical" initialValues={{ severity: "warning", fix_status: "open" }}>
          <Form.Item name="shot_id" label="关联镜头">
            <Select
              allowClear
              options={(shots ?? []).map((s) => ({ value: s.id, label: s.shot_code }))}
            />
          </Form.Item>
          <Form.Item name="severity" label="严重度" rules={[{ required: true }]}>
            <Select options={SEVERITY_OPTS} />
          </Form.Item>
          <Form.Item name="fix_status" label="修复状态">
            <Select options={FIX_STATUS_OPTS} />
          </Form.Item>
          <Form.Item name="fix_note" label="修复说明">
            <Input.TextArea rows={2} />
          </Form.Item>
          <Form.Item name="report_md" label="报告内容">
            <Input.TextArea rows={3} />
          </Form.Item>
        </Form>
      </Modal>
    </Card>
  );
}
