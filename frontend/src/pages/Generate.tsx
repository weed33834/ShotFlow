// 一句话出片 — 自然语言 → 出片（完整参数配置表单）
import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Alert,
  App,
  Button,
  Card,
  Col,
  Collapse,
  Empty,
  Form,
  Input,
  Row,
  Segmented,
  Select,
  Space,
  Spin,
  Switch,
  Tag,
  Typography,
} from "antd";
import {
  CaretRightOutlined,
  PictureOutlined,
  VideoCameraOutlined,
  SoundOutlined,
  FontSizeOutlined,
} from "@ant-design/icons";
import { generateApi, toolsApi } from "@/api";
import type { GenerateRequest, GenerateResponse, OutputType, ToolResult } from "@/types";

const { TextArea } = Input;

const OUTPUT_OPTIONS: { value: OutputType; label: string; icon: React.ReactNode }[] = [
  { value: "video", label: "视频", icon: <VideoCameraOutlined /> },
  { value: "image_set", label: "图集", icon: <PictureOutlined /> },
  { value: "micro_movie", label: "微电影", icon: <VideoCameraOutlined /> },
  { value: "comic", label: "漫画", icon: <PictureOutlined /> },
  { value: "vn", label: "视觉小说", icon: <PictureOutlined /> },
];

const ASPECT_OPTIONS = [
  { value: "", label: "自动" },
  { value: "16:9", label: "16:9 横屏" },
  { value: "9:16", label: "9:16 竖屏" },
  { value: "1:1", label: "1:1 正方" },
];

const VOICE_OPTIONS = [
  { value: "", label: "自动选择" },
  { value: "child_cn", label: "童声（中文）" },
  { value: "female_cn", label: "女声（中文）" },
  { value: "male_cn", label: "男声（中文）" },
  { value: "female_en", label: "女声（英文）" },
  { value: "male_en", label: "男声（英文）" },
  { value: "female_ja", label: "女声（日文）" },
  { value: "male_ja", label: "男声（日文）" },
  { value: "female_ko", label: "女声（韩文）" },
];

const COPYRIGHT_HINT = "本平台仅提供生成工具，所用素材/角色/音乐的版权由使用者自行负责";

// 根据 url 或 meta 粗略判断是否为图片
function isImageAsset(a: ToolResult): boolean {
  const fromMeta = (a.meta?.type as string | undefined) ?? "";
  if (fromMeta.startsWith("image")) return true;
  const u = a.url.toLowerCase();
  return /\.(png|jpe?g|gif|webp|bmp|svg)(\?|#|$)/i.test(u);
}

// 判断是否为视频
function isVideoAsset(a: ToolResult): boolean {
  const fromMeta = (a.meta?.type as string | undefined) ?? "";
  if (fromMeta.startsWith("video")) return true;
  const u = a.url.toLowerCase();
  return /\.(mp4|mov|avi|mkv|webm)(\?|#|$)/i.test(u);
}

// 判断是否为音频
function isAudioAsset(a: ToolResult): boolean {
  const fromMeta = (a.meta?.type as string | undefined) ?? "";
  if (fromMeta.startsWith("audio")) return true;
  const u = a.url.toLowerCase();
  return /\.(mp3|wav|flac|ogg|aac|m4a)(\?|#|$)/i.test(u);
}

export default function Generate() {
  const { message } = App.useApp();
  const qc = useQueryClient();
  const [form] = Form.useForm();
  const [outputType, setOutputType] = useState<OutputType>("video");

  // 查询系统配置状态
  const configQ = useQuery({
    queryKey: ["tools-providers"],
    queryFn: toolsApi.providers,
    staleTime: 30000,
  });

  const genMut = useMutation({
    mutationFn: generateApi.generate,
    onSuccess: (res: GenerateResponse) => {
      message.success(`已生成，spec_id=${res.spec_id}，状态：${res.status}`);
      qc.invalidateQueries({ queryKey: ["tools-assets"] });
    },
    onError: (e: Error) => {
      message.error(
        (e as Error & { friendlyMessage?: string }).friendlyMessage || e.message
      );
    },
  });

  const assetsQ = useQuery({
    queryKey: ["tools-assets"],
    queryFn: toolsApi.assets,
    enabled: genMut.isSuccess,
    retry: false,
  });

  const handleGenerate = () => {
    const values = form.getFieldsValue();
    const nl = (values.nl_prompt || "").trim();
    if (!nl) {
      message.warning("请先输入一句话描述");
      return;
    }
    const payload: GenerateRequest = {
      nl_prompt: nl,
      output_type: outputType,
      video_aspect: values.video_aspect || "",
      voice_name: values.voice_name || "",
      subtitle_enabled: values.subtitle_enabled ?? true,
      bgm_enabled: values.bgm_enabled ?? true,
    };
    genMut.mutate(payload);
  };

  const simMode = configQ.data?.simulate_mode ?? false;
  const llmOk = configQ.data?.llm_configured ?? false;
  const ffmpegOk = configQ.data?.ffmpeg_available ?? false;

  return (
    <div>
      <Typography.Title level={4}>一句话出片</Typography.Title>

      {/* 系统状态指示 */}
      <Card size="small" style={{ marginBottom: 16 }}>
        <Space size="large" wrap>
          <Tag color={simMode ? "orange" : "green"}>
            {simMode ? "模拟模式" : "真实模式"}
          </Tag>
          <Tag color={llmOk ? "green" : "red"}>
            LLM: {llmOk ? "已配置" : "未配置"}
          </Tag>
          <Tag color={ffmpegOk ? "green" : "red"}>
            FFmpeg: {ffmpegOk ? "可用" : "不可用"}
          </Tag>
          {configQ.data?.providers && (
            <Typography.Text type="secondary" style={{ fontSize: 12 }}>
              已注册 {configQ.data.providers.length} 个 Provider
            </Typography.Text>
          )}
        </Space>
      </Card>

      {/* 产出类型选择 */}
      <Card size="small" style={{ marginBottom: 16 }}>
        <Segmented
          value={outputType}
          onChange={(v) => setOutputType(v as OutputType)}
          options={OUTPUT_OPTIONS.map((o) => ({
            value: o.value,
            label: (
              <Space size={4}>
                {o.icon}
                {o.label}
              </Space>
            ),
          }))}
          block
        />
      </Card>

      {/* 主表单 */}
      <Card size="small" style={{ marginBottom: 16 }}>
        <Form form={form} layout="vertical" initialValues={{
          subtitle_enabled: true,
          bgm_enabled: true,
          video_aspect: "",
          voice_name: "",
        }}>
          <Form.Item
            name="nl_prompt"
            label="描述你想要的画面"
            rules={[{ required: true, message: "请输入描述" }]}
          >
            <TextArea
              rows={4}
              placeholder="例如：一只小猫在花园里追蝴蝶，阳光明媚，卡通风格，15秒短视频"
              maxLength={2000}
              showCount
            />
          </Form.Item>

          {/* 高级参数折叠面板 */}
          <Collapse
            ghost
            items={[{
              key: "advanced",
              label: (
                <Space>
                  <CaretRightOutlined />
                  高级参数
                </Space>
              ),
              children: (
                <Row gutter={16}>
                  <Col span={8}>
                    <Form.Item name="video_aspect" label="画面比例">
                      <Select options={ASPECT_OPTIONS} />
                    </Form.Item>
                  </Col>
                  <Col span={8}>
                    <Form.Item name="voice_name" label={
                      <Space size={4}>
                        <SoundOutlined />
                        配音声音
                      </Space>
                    }>
                      <Select options={VOICE_OPTIONS} />
                    </Form.Item>
                  </Col>
                  <Col span={4}>
                    <Form.Item name="subtitle_enabled" label={
                      <Space size={4}>
                        <FontSizeOutlined />
                        字幕
                      </Space>
                    } valuePropName="checked">
                      <Switch />
                    </Form.Item>
                  </Col>
                  <Col span={4}>
                    <Form.Item name="bgm_enabled" label="背景音乐" valuePropName="checked">
                      <Switch />
                    </Form.Item>
                  </Col>
                </Row>
              ),
            }]}
          />

          <Space>
            <Button
              type="primary"
              size="large"
              loading={genMut.isPending}
              onClick={handleGenerate}
              icon={<CaretRightOutlined />}
            >
              开始生成
            </Button>
            <Typography.Text type="warning" style={{ fontSize: 12 }}>
              {COPYRIGHT_HINT}
            </Typography.Text>
          </Space>
        </Form>
      </Card>

      {/* 生成结果 */}
      {genMut.isSuccess && (
        <Card size="small" style={{ marginBottom: 16 }}>
          <Alert
            type="success"
            showIcon
            message="生成成功"
            description={
              <div>
                <Space>
                  <span>spec_id：<b>{genMut.data.spec_id}</b></span>
                  <Tag color={genMut.data.status === "generated" ? "green" : "blue"}>
                    {genMut.data.status}
                  </Tag>
                </Space>
                {genMut.data.message && <div style={{ marginTop: 4 }}>{genMut.data.message}</div>}
              </div>
            }
          />
        </Card>
      )}

      {/* 生成资产展示 */}
      {genMut.isSuccess && (
        <Card size="small" title="生成的资产">
          {assetsQ.isLoading ? (
            <div style={{ textAlign: "center", padding: 40 }}>
              <Spin tip="加载资产..." />
            </div>
          ) : assetsQ.isError ? (
            <Alert
              type="error"
              showIcon
              message="资产拉取失败"
              description={
                (assetsQ.error as Error & { friendlyMessage?: string }).friendlyMessage ||
                assetsQ.error.message
              }
            />
          ) : (assetsQ.data ?? []).length === 0 ? (
            <Empty description="暂无资产" />
          ) : (
            <Row gutter={[12, 12]}>
              {assetsQ.data!.map((a) => {
                const isImg = isImageAsset(a);
                const isVid = isVideoAsset(a);
                const isAud = isAudioAsset(a);
                return (
                  <Col key={a.asset_id} xs={24} sm={12} md={8} lg={6}>
                    <Card
                      size="small"
                      hoverable
                      cover={
                        isImg ? (
                          <img
                            src={a.url}
                            alt={String(a.asset_id)}
                            style={{
                              width: "100%",
                              height: 160,
                              objectFit: "cover",
                              borderRadius: "6px 6px 0 0",
                            }}
                            onError={(e) => {
                              (e.target as HTMLImageElement).style.display = "none";
                            }}
                          />
                        ) : isVid ? (
                          <video
                            src={a.url}
                            controls
                            style={{
                              width: "100%",
                              height: 160,
                              objectFit: "cover",
                              borderRadius: "6px 6px 0 0",
                            }}
                          />
                        ) : isAud ? (
                          <div style={{ padding: 16, textAlign: "center" }}>
                            <audio src={a.url} controls style={{ width: "100%" }} />
                          </div>
                        ) : (
                          <div style={{ padding: 16 }}>
                            <a href={a.url} target="_blank" rel="noreferrer">
                              {a.url.length > 50 ? a.url.slice(0, 50) + "..." : a.url}
                            </a>
                          </div>
                        )
                      }
                    >
                      <Card.Meta
                        title={
                          <Space>
                            <Tag color="geekblue">{a.provider}</Tag>
                            {isImg && <Tag color="blue">图片</Tag>}
                            {isVid && <Tag color="purple">视频</Tag>}
                            {isAud && <Tag color="orange">音频</Tag>}
                          </Space>
                        }
                        description={
                          <Typography.Text type="secondary" style={{ fontSize: 12 }}>
                            ID: {a.asset_id}
                          </Typography.Text>
                        }
                      />
                    </Card>
                  </Col>
                );
              })}
            </Row>
          )}
        </Card>
      )}
    </div>
  );
}
