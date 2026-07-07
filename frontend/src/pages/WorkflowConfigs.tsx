// 工作流配置 — YAML 参数化表单 + Provider 评分
import { useEffect, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import {
  App,
  Button,
  Card,
  Col,
  Descriptions,
  Empty,
  Form,
  Input,
  InputNumber,
  Progress,
  Row,
  Select,
  Space,
  Table,
  Typography,
} from "antd";
import { http } from "@/api/client";

interface WorkflowParam {
  key: string;
  label: string;
  type: string;
  required: boolean;
  default: number | string;
  min?: number;
  max?: number;
  node_class?: string;
  node_input?: string;
}

interface WorkflowConfig {
  name: string;
  task_type: string;
  file_path: string;
  description: string;
  parameters: WorkflowParam[];
  defaults: Record<string, unknown>;
}

interface ProviderProfile {
  quality: number;
  speed: number;
  cost: number;
  capability: number;
  requires_gpu: boolean;
}

interface RecommendResult {
  recommended: string;
  reason: string;
  scores: Record<string, number>;
  profiles: Record<string, ProviderProfile>;
}

export default function WorkflowConfigs() {
  const { message } = App.useApp();

  const { data: configs, isLoading } = useQuery({
    queryKey: ["wf-configs"],
    queryFn: () => http.get<WorkflowConfig[]>("/workflows-cfg/configs").then((r) => r.data),
  });

  // Provider 评分参数可切换，覆盖标准/复杂、有/无 GPU 场景
  const [complexity, setComplexity] = useState<string>("complex");
  const [hasGpu, setHasGpu] = useState<boolean>(true);

  const { data: recommend } = useQuery<RecommendResult>({
    queryKey: ["provider-recommend", complexity, hasGpu],
    queryFn: () =>
      http
        .get<RecommendResult>("/workflows-cfg/provider/recommend", {
          params: { complexity, has_gpu: hasGpu },
        })
        .then((r) => r.data),
  });

  const [selectedName, setSelectedName] = useState<string | undefined>();
  const [form] = Form.useForm();

  const selected = configs?.find((c) => c.name === selectedName) || configs?.[0];

  const { data: detail } = useQuery({
    queryKey: ["wf-config", selected?.name],
    queryFn: () =>
      http.get<WorkflowConfig>(`/workflows-cfg/configs/${selected?.name}`).then((r) => r.data),
    enabled: !!selected?.name,
  });

  // 切换工作流时同步表单初始值（antd Form initialValues 仅首次挂载生效）
  useEffect(() => {
    form.resetFields();
    form.setFieldsValue(detail?.defaults);
  }, [detail, form]);

  const injectMut = useMutation({
    mutationFn: (params: Record<string, unknown>) =>
      http
        .post(`/workflows-cfg/configs/${selected!.name}/inject`, { name: selected!.name, params })
        .then((r) => r.data),
    onSuccess: () => message.success("参数已注入并校验通过，工作流 JSON 可提交 ComfyUI"),
    onError: (e: Error) => message.error((e as Error & { friendlyMessage?: string }).friendlyMessage || e.message),
  });

  return (
    <div>
      <Typography.Title level={4}>工作流配置</Typography.Title>
      <Row gutter={[16, 16]}>
        <Col xs={24} md={10}>
          <Card title="工作流列表" size="small" loading={isLoading}>
            <Table
              size="small"
              rowKey="name"
              pagination={false}
              dataSource={configs ?? []}
              onRow={(r) => ({ onClick: () => setSelectedName(r.name) })}
              rowSelection={{
                type: "radio",
                selectedRowKeys: selectedName ? [selectedName] : [],
                onChange: (keys) => setSelectedName(keys[0] as string),
              }}
              columns={[
                { title: "名称", dataIndex: "name", key: "name" },
                { title: "类型", dataIndex: "task_type", key: "task_type" },
              ]}
            />
          </Card>
        </Col>
        <Col xs={24} md={14}>
          <Card title="参数表单" size="small">
            {detail ? (
              <>
                <Descriptions size="small" column={1} style={{ marginBottom: 12 }}>
                  <Descriptions.Item label="描述">{detail.description}</Descriptions.Item>
                  <Descriptions.Item label="文件">{detail.file_path}</Descriptions.Item>
                </Descriptions>
                <Form
                  form={form}
                  layout="vertical"
                  initialValues={detail.defaults}
                  onFinish={(v) => injectMut.mutate(v)}
                >
                  {detail.parameters.map((p) => (
                    <Form.Item
                      key={p.key}
                      name={p.key}
                      label={`${p.label} (${p.key})`}
                      rules={p.required ? [{ required: true }] : []}
                    >
                      {p.type === "text" ? (
                        <Input.TextArea rows={2} />
                      ) : (
                        <InputNumber
                          min={p.min}
                          max={p.max}
                          style={{ width: "100%" }}
                        />
                      )}
                    </Form.Item>
                  ))}
                  <Button type="primary" htmlType="submit" loading={injectMut.isPending}>
                    校验并注入参数
                  </Button>
                </Form>
              </>
            ) : (
              <Empty description="请从左侧选择工作流" />
            )}
          </Card>
        </Col>
      </Row>

      <Card
        title="Provider 评分"
        size="small"
        style={{ marginTop: 16 }}
        extra={
          <Space>
            <Select
              size="small"
              style={{ width: 110 }}
              value={complexity}
              onChange={setComplexity}
              options={[
                { value: "standard", label: "标准镜头" },
                { value: "complex", label: "复杂镜头" },
              ]}
            />
            <Select
              size="small"
              style={{ width: 110 }}
              value={hasGpu ? "gpu" : "nogpu"}
              onChange={(v) => setHasGpu(v === "gpu")}
              options={[
                { value: "gpu", label: "有 GPU" },
                { value: "nogpu", label: "无 GPU" },
              ]}
            />
          </Space>
        }
      >
        {recommend ? (
          <>
            <Descriptions size="small" column={1} style={{ marginBottom: 12 }}>
              <Descriptions.Item label="推荐 Provider">
                <b style={{ color: "#1668dc" }}>{recommend.recommended}</b>
              </Descriptions.Item>
              <Descriptions.Item label="原因">{recommend.reason}</Descriptions.Item>
            </Descriptions>
            <Row gutter={16}>
              {Object.entries(recommend.profiles).map(([name, p]) => (
                <Col xs={24} sm={12} key={name}>
                  <Card type="inner" title={name} size="small">
                    <p>质量：<Progress percent={p.quality * 10} size="small" /></p>
                    <p>速度：<Progress percent={p.speed * 10} size="small" /></p>
                    <p>成本（越高越便宜）：<Progress percent={p.cost * 10} size="small" /></p>
                    <p>复杂镜头能力：<Progress percent={p.capability * 10} size="small" /></p>
                    <p>综合得分：<b>{recommend.scores[name]}</b></p>
                  </Card>
                </Col>
              ))}
            </Row>
          </>
        ) : (
          <Empty description="加载中…" />
        )}
      </Card>
    </div>
  );
}
