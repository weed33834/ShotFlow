// 一句话出片 — 自然语言 → 出片（完整参数配置表单 + 快捷模板 + 批量生成 + 视频预览）
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
  InputNumber,
  Modal,
  Popconfirm,
  Radio,
  Row,
  Segmented,
  Select,
  Space,
  Spin,
  Switch,
  Tag,
  Tooltip,
  Typography,
  Upload,
} from "antd";
import {
  CaretRightOutlined,
  CopyOutlined,
  DownloadOutlined,
  InboxOutlined,
  PictureOutlined,
  RocketOutlined,
  SoundOutlined,
  FontSizeOutlined,
  ThunderboltOutlined,
  VideoCameraOutlined,
  BulbOutlined,
  AppstoreOutlined,
  ShareAltOutlined,
  ArrowUpOutlined,
} from "@ant-design/icons";
import type { UploadFile } from "antd";
import {
  generateApi,
  getQualityLevels,
  getSceneTemplates,
  getStylePresets,
  toolsApi,
} from "@/api";
import type {
  BatchGenerateResponse,
  GenerateRequest,
  GenerateResponse,
  OutputType,
  QualityLevel,
  SceneTemplate,
  StylePreset,
  ToolResult,
} from "@/types";

const { TextArea } = Input;

// ===== 产出类型 =====
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
  { value: "clone_cosyvoice", label: "语音克隆（CosyVoice）" },
];

// ===== 快捷模板：预设示例 prompt，一键填充 =====
interface QuickTemplate {
  key: string;
  title: string;
  prompt: string;
  style: string;
  scene: string;
  quality: string;
  icon: string;
}

const QUICK_TEMPLATES: QuickTemplate[] = [
  {
    key: "food_cinematic",
    title: "美食大片",
    prompt: "一道法式焦糖布丁在暖色灯光下缓缓旋转，焦糖光泽晶莹，蒸汽升腾，微距特写展示细腻质感，30秒美食广告",
    style: "cinematic",
    scene: "food",
    quality: "4k",
    icon: "🍮",
  },
  {
    key: "city_cyberpunk",
    title: "赛博都市",
    prompt: "未来都市夜景航拍，霓虹灯牌林立，飞行汽车穿梭于摩天大楼间，雨后街道倒映着紫色和蓝色的霓虹光芒，赛博朋克风格",
    style: "cyberpunk",
    scene: "city",
    quality: "4k",
    icon: "🌃",
  },
  {
    key: "nature_ghibli",
    title: "宫崎骏风光",
    prompt: "一片翠绿的草地延伸到天际，白云缓缓飘过，远处有古老的石桥和小溪，阳光穿过树叶洒下斑驳光影，吉卜力动画风格",
    style: "ghibli",
    scene: "nature",
    quality: "hd",
    icon: "🌿",
  },
  {
    key: "product_realistic",
    title: "产品广告",
    prompt: "一瓶高级香水在纯白背景下旋转展示，瓶身水晶质感，金色瓶盖反射柔和灯光，水滴滑落，30秒高端产品广告",
    style: "realistic",
    scene: "product",
    quality: "4k",
    icon: " perfume",
  },
  {
    key: "scifi_epic",
    title: "科幻史诗",
    prompt: "深海外星生物发着生物荧光在黑暗的海沟中游动，远处一座巨大的水下城市发出神秘光芒，探测器缓缓靠近，史诗科幻氛围",
    style: "scifi",
    scene: "story",
    quality: "8k",
    icon: "🚀",
  },
  {
    key: "travel_vlog",
    title: "旅行Vlog",
    prompt: "从飞机舷窗俯瞰雪山日出，镜头切换到古镇石板路的晨雾，最后是海边悬崖上的灯塔，黄金时刻光线，旅行vlog风格",
    style: "documentary",
    scene: "travel",
    quality: "hd",
    icon: "✈️",
  },
  {
    key: "anime_action",
    title: "动漫动作",
    prompt: "少年站在樱花树下握紧拳头，风吹起头发和花瓣，眼神坚定望向远方，突然加速冲向前方，动漫风格高速动作场面",
    style: "anime",
    scene: "action",
    quality: "hd",
    icon: "🌸",
  },
  {
    key: "ink_wash",
    title: "水墨意境",
    prompt: "远山如黛，一叶扁舟漂于江上，渔翁独钓，晨雾缭绕山水间，几只白鹭飞过，中国传统水墨画风格，写意意境",
    style: "ink_wash",
    scene: "nature",
    quality: "hd",
    icon: " mountains",
  },
];

// ===== 电影级画质增强：兜底选项 =====

const STYLE_FALLBACK: StylePreset[] = [
  { key: "cinematic", name: "电影感", image_suffix: "", video_suffix: "", negative_prompt: "" },
  { key: "cyberpunk", name: "赛博朋克", image_suffix: "", video_suffix: "", negative_prompt: "" },
  { key: "anime", name: "动漫", image_suffix: "", video_suffix: "", negative_prompt: "" },
  { key: "ink_wash", name: "水墨画", image_suffix: "", video_suffix: "", negative_prompt: "" },
  { key: "ghibli", name: "吉卜力", image_suffix: "", video_suffix: "", negative_prompt: "" },
  { key: "oil_painting", name: "油画", image_suffix: "", video_suffix: "", negative_prompt: "" },
  { key: "realistic", name: "写实", image_suffix: "", video_suffix: "", negative_prompt: "" },
  { key: "watercolor", name: "水彩", image_suffix: "", video_suffix: "", negative_prompt: "" },
  { key: "documentary", name: "纪实摄影", image_suffix: "", video_suffix: "", negative_prompt: "" },
  { key: "wes_anderson", name: "韦斯·安德森", image_suffix: "", video_suffix: "", negative_prompt: "" },
  { key: "scifi", name: "科幻", image_suffix: "", video_suffix: "", negative_prompt: "" },
  { key: "fantasy", name: "奇幻", image_suffix: "", video_suffix: "", negative_prompt: "" },
  { key: "noir", name: "黑色电影", image_suffix: "", video_suffix: "", negative_prompt: "" },
];

const SCENE_FALLBACK: SceneTemplate[] = [
  { key: "product", name: "产品展示", shot_rhythm: "慢节奏，每镜 3-5 秒", shot_sequence: "特写→旋转展示→全景→使用场景", lighting: "影棚柔光 + 边缘光", transition: "fade" },
  { key: "food", name: "美食制作", shot_rhythm: "中节奏，每镜 2-4 秒", shot_sequence: "食材微距→制作过程→摆盘特写→成品全景", lighting: "暖色自然光，侧逆光", transition: "wipeleft" },
  { key: "travel", name: "旅行vlog", shot_rhythm: "快节奏，每镜 2-3 秒", shot_sequence: "航拍定场→街道跟拍→景点特写→人物互动", lighting: "黄金时刻自然光", transition: "fade" },
  { key: "knowledge", name: "知识科普", shot_rhythm: "中节奏，每镜 4-6 秒", shot_sequence: "中景讲解→图示特写→实例演示→总结全景", lighting: "柔光均匀照明", transition: "fade" },
  { key: "story", name: "人物故事", shot_rhythm: "慢节奏，每镜 4-8 秒", shot_sequence: "环境定场→人物中景→表情特写→动作全景", lighting: "明暗对比/边缘光", transition: "fade" },
  { key: "city", name: "城市探索", shot_rhythm: "快节奏，每镜 2-4 秒", shot_sequence: "天际线航拍→FPV穿梭→街道手持→建筑仰拍", lighting: "霓虹/夜景，蓝紫色暮光", transition: "slideup" },
  { key: "nature", name: "自然风光", shot_rhythm: "慢节奏，每镜 5-10 秒", shot_sequence: "航拍大远景→延时摄影→微距细节→日出日落", lighting: "黄金时刻/体积光", transition: "fade" },
  { key: "action", name: "动作场景", shot_rhythm: "快节奏，每镜 1-3 秒", shot_sequence: "快切多角度→慢动作特写→一镜到底→航拍追拍", lighting: "高对比硬光", transition: "fade" },
  { key: "interview", name: "访谈对话", shot_rhythm: "慢节奏，每镜 5-10 秒", shot_sequence: "过肩镜头→面部特写→反应镜头→环境交代", lighting: "柔光影棚光，三点布光", transition: "fade" },
  { key: "tutorial", name: "教程演示", shot_rhythm: "中节奏，每镜 3-5 秒", shot_sequence: "全景操作→手部特写→屏幕录制→成品展示", lighting: "均匀明亮，无阴影干扰", transition: "fade" },
];

const QUALITY_FALLBACK: QualityLevel[] = [
  { key: "standard", label: "标准", desc: "1080p 高清画质" },
  { key: "hd", label: "高清", desc: "1080p+ 高清画质 + 浅景深" },
  { key: "4k", label: "4K", desc: "HDR 超高细节 + 电影级调色 + ACES" },
  { key: "8k", label: "8K", desc: "HDR 极清 + Dolby Vision + 光追" },
];

const TRANSITION_OPTIONS = [
  { value: "fade", label: "淡入淡出（fade）" },
  { value: "wipeleft", label: "左擦除（wipeleft）" },
  { value: "wiperight", label: "右擦除（wiperight）" },
  { value: "slideup", label: "上滑（slideup）" },
  { value: "slidedown", label: "下滑（slidedown）" },
  { value: "circleopen", label: "圆形展开（circleopen）" },
  { value: "circleclose", label: "圆形收拢（circleclose）" },
  { value: "distance", label: "推拉（distance）" },
  { value: "zoomin", label: "放大（zoomin）" },
];

const PUBLISH_PLATFORMS = [
  { value: "douyin", label: "抖音" },
  { value: "bilibili", label: "哔哩哔哩" },
  { value: "xiaohongshu", label: "小红书" },
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
  const [uploadFileList, setUploadFileList] = useState<UploadFile[]>([]);

  // 电影级画质增强状态
  const [stylePreset, setStylePreset] = useState<string>("");
  const [sceneTemplate, setSceneTemplate] = useState<string>("");
  const [qualityLevel, setQualityLevel] = useState<string>("standard");
  const [transition, setTransition] = useState<string>("fade");

  // 批量生成
  const [batchCount, setBatchCount] = useState<number>(3);
  const [batchOpen, setBatchOpen] = useState(false);
  const [batchResult, setBatchResult] = useState<BatchGenerateResponse | null>(null);

  // 发布弹窗
  const [publishOpen, setPublishOpen] = useState(false);
  const [publishAssetId, setPublishAssetId] = useState<number | null>(null);
  const [publishForm] = Form.useForm();

  const uploadedAssetIds = uploadFileList
    .filter((f) => f.status === "done" && f.response)
    .map((f) => Number((f.response as ToolResult).asset_id))
    .filter((id) => !Number.isNaN(id));

  // 查询系统配置状态
  const configQ = useQuery({
    queryKey: ["tools-providers"],
    queryFn: toolsApi.providers,
    staleTime: 30000,
  });

  // 电影级提示词：从 API 加载（失败用本地兜底）
  const stylesQ = useQuery({
    queryKey: ["prompts-styles"],
    queryFn: getStylePresets,
    staleTime: 300000,
  });
  const scenesQ = useQuery({
    queryKey: ["prompts-scenes"],
    queryFn: getSceneTemplates,
    staleTime: 300000,
  });
  const qualityQ = useQuery({
    queryKey: ["prompts-quality-levels"],
    queryFn: getQualityLevels,
    staleTime: 300000,
  });

  const styleOptions: StylePreset[] = [
    { key: "", name: "自动", image_suffix: "", video_suffix: "", negative_prompt: "" },
    ...(stylesQ.data?.styles ?? STYLE_FALLBACK),
  ];
  const sceneList: SceneTemplate[] = scenesQ.data?.scenes ?? SCENE_FALLBACK;
  const qualityOptions: QualityLevel[] = qualityQ.data?.levels ?? QUALITY_FALLBACK;
  const selectedScene = sceneList.find((s) => s.key === sceneTemplate);

  // 本地素材上传
  const uploadMut = useMutation({
    mutationFn: toolsApi.upload,
    onError: (e: Error) => {
      message.error(
        (e as Error & { friendlyMessage?: string }).friendlyMessage || e.message
      );
    },
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

  // 批量生成
  const batchMut = useMutation({
    mutationFn: generateApi.batch,
    onSuccess: (res: BatchGenerateResponse) => {
      setBatchResult(res);
      const successCount = res.results.filter((r) => r.spec_id !== null).length;
      message.success(`批量生成完成：${successCount}/${res.count} 个成功`);
      qc.invalidateQueries({ queryKey: ["tools-assets"] });
    },
    onError: (e: Error) => {
      message.error(
        (e as Error & { friendlyMessage?: string }).friendlyMessage || e.message
      );
    },
  });

  // 视频增强
  const enhanceMut = useMutation({
    mutationFn: ({ assetId, scale, fps }: { assetId: number; scale: number; fps: number }) =>
      toolsApi.enhance(assetId, scale, fps),
    onSuccess: (res) => {
      message.success(`视频增强完成：${res.status}`);
      qc.invalidateQueries({ queryKey: ["tools-assets"] });
    },
    onError: (e: Error) => {
      message.error(
        (e as Error & { friendlyMessage?: string }).friendlyMessage || e.message
      );
    },
  });

  // 发布
  const publishMut = useMutation({
    mutationFn: (payload: { asset_id: number; platform: string; title?: string; description?: string; tags?: string[] }) =>
      toolsApi.publish(payload),
    onSuccess: (res) => {
      if (res.success) {
        message.success(`发布成功！平台：${res.platform}，ID：${res.publish_id}`);
      } else {
        message.error(`发布失败：${res.error}`);
      }
      setPublishOpen(false);
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
    enabled: genMut.isSuccess || batchMut.isSuccess,
    retry: false,
  });

  const buildPayload = (): GenerateRequest => {
    const values = form.getFieldsValue();
    return {
      nl_prompt: (values.nl_prompt || "").trim(),
      output_type: outputType,
      video_aspect: values.video_aspect || "",
      voice_name: values.voice_name || "",
      subtitle_enabled: values.subtitle_enabled ?? true,
      bgm_enabled: values.bgm_enabled ?? true,
      local_asset_ids: uploadedAssetIds.length > 0 ? uploadedAssetIds : undefined,
      style_preset: stylePreset || "",
      scene_template: sceneTemplate || "",
      quality_level: qualityLevel || "standard",
      transition: transition || "fade",
    };
  };

  const handleGenerate = () => {
    const payload = buildPayload();
    if (!payload.nl_prompt) {
      message.warning("请先输入一句话描述");
      return;
    }
    genMut.mutate(payload);
  };

  const handleBatchGenerate = () => {
    const payload = buildPayload();
    if (!payload.nl_prompt) {
      message.warning("请先输入一句话描述");
      return;
    }
    setBatchResult(null);
    batchMut.mutate({ ...payload, count: batchCount });
  };

  // 一键应用快捷模板
  const applyTemplate = (tpl: QuickTemplate) => {
    form.setFieldValue("nl_prompt", tpl.prompt);
    setStylePreset(tpl.style);
    setSceneTemplate(tpl.scene);
    setQualityLevel(tpl.quality);
    setOutputType("video");
    message.success(`已加载模板：${tpl.title}`);
  };

  // 复制提示词到剪贴板
  const handleCopyPrompt = () => {
    const text = form.getFieldValue("nl_prompt") || "";
    if (text) {
      navigator.clipboard.writeText(text);
      message.success("已复制到剪贴板");
    }
  };

  // 下载资产
  const handleDownload = (url: string, filename: string) => {
    const a = document.createElement("a");
    a.href = url;
    a.download = filename || "download";
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
  };

  // 打开发布弹窗
  const openPublish = (assetId: number) => {
    setPublishAssetId(assetId);
    setPublishOpen(true);
  };

  // 提交发布
  const handlePublish = () => {
    publishForm.validateFields().then((values) => {
      if (publishAssetId === null) return;
      publishMut.mutate({
        asset_id: publishAssetId,
        platform: values.platform || "douyin",
        title: values.title || "",
        description: values.description || "",
        tags: values.tags || [],
      });
    });
  };

  const simMode = configQ.data?.simulate_mode ?? false;
  const llmOk = configQ.data?.llm_configured ?? false;
  const ffmpegOk = configQ.data?.ffmpeg_available ?? false;
  const llmProvider = configQ.data?.llm_provider ?? "openai";
  const llmModel = configQ.data?.llm_model ?? "gpt-4o-mini";

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
          <Tag color={llmOk ? "blue" : "default"}>
            Provider: {llmProvider}
          </Tag>
          <Tag color={llmOk ? "geekblue" : "default"}>
            Model: {llmModel}
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

      {/* 快捷模板画廊 */}
      <Card
        size="small"
        style={{ marginBottom: 16 }}
        title={
          <Space>
            <BulbOutlined style={{ color: "#faad14" }} />
            快捷模板
          </Space>
        }
        extra={
          <Typography.Text type="secondary" style={{ fontSize: 12 }}>
            点击一键填充提示词和风格参数
          </Typography.Text>
        }
      >
        <Row gutter={[8, 8]}>
          {QUICK_TEMPLATES.map((tpl) => (
            <Col key={tpl.key} xs={12} sm={8} md={6} lg={3}>
              <div
                onClick={() => applyTemplate(tpl)}
                style={{
                  border: "1.5px solid #e4e7eb",
                  borderRadius: 8,
                  padding: "10px 12px",
                  cursor: "pointer",
                  background: "#fafafa",
                  height: "100%",
                  transition: "all 0.2s",
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.borderColor = "#1668dc";
                  e.currentTarget.style.background = "#f0f5ff";
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.borderColor = "#e4e7eb";
                  e.currentTarget.style.background = "#fafafa";
                }}
              >
                <div style={{ fontSize: 24, marginBottom: 4 }}>{tpl.icon}</div>
                <Typography.Text strong style={{ fontSize: 13 }}>
                  {tpl.title}
                </Typography.Text>
                <div style={{ marginTop: 2 }}>
                  <Space size={4} wrap>
                    <Tag style={{ fontSize: 10, padding: "0 4px" }}>{tpl.quality.toUpperCase()}</Tag>
                  </Space>
                </div>
              </div>
            </Col>
          ))}
        </Row>
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
            label={
              <Space>
                <span>描述你想要的画面</span>
                <Tooltip title="复制提示词">
                  <Button size="small" type="text" icon={<CopyOutlined />} onClick={handleCopyPrompt} />
                </Tooltip>
              </Space>
            }
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

          <Space wrap>
            <Button
              type="primary"
              size="large"
              loading={genMut.isPending}
              onClick={handleGenerate}
              icon={<CaretRightOutlined />}
            >
              开始生成
            </Button>
            <Button
              size="large"
              loading={batchMut.isPending}
              onClick={() => setBatchOpen(true)}
              icon={<AppstoreOutlined />}
            >
              批量生成
            </Button>
            <Typography.Text type="warning" style={{ fontSize: 12 }}>
              {COPYRIGHT_HINT}
            </Typography.Text>
          </Space>
        </Form>
      </Card>

      {/* 电影级画质增强 */}
      <Card
        size="small"
        style={{ marginBottom: 16 }}
        title={
          <Space>
            <ThunderboltOutlined style={{ color: "#1677ff" }} />
            电影级画质增强
          </Space>
        }
      >
        {/* 风格预设 */}
        <div style={{ marginBottom: 20 }}>
          <Space style={{ marginBottom: 8 }}>
            <Typography.Text strong>风格预设</Typography.Text>
            <Typography.Text type="secondary" style={{ fontSize: 12 }}>
              选择视觉风格，自动注入专业镜头语言提示词
            </Typography.Text>
          </Space>
          {stylesQ.isLoading ? (
            <div style={{ textAlign: "center", padding: 16 }}>
              <Spin size="small" />
            </div>
          ) : (
            <Row gutter={[8, 8]}>
              {styleOptions.map((s) => {
                const selected = stylePreset === s.key;
                return (
                  <Col key={s.key || "auto"} xs={12} sm={8} md={6} lg={4}>
                    <Tooltip
                      title={
                        s.key === ""
                          ? "由 LLM 根据描述自动选择最合适的风格"
                          : s.negative_prompt
                            ? `避免：${s.negative_prompt}`
                            : s.image_suffix || s.name
                      }
                    >
                      <div
                        onClick={() => setStylePreset(s.key)}
                        style={{
                          border: `1.5px solid ${selected ? "#1677ff" : "#e4e7eb"}`,
                          borderRadius: 8,
                          padding: "8px 10px",
                          cursor: "pointer",
                          background: selected ? "#e6f4ff" : "#fafafa",
                          height: "100%",
                          transition: "all 0.2s",
                          boxShadow: selected ? "0 0 0 1px #1677ff" : "none",
                        }}
                      >
                        <Typography.Text
                          strong
                          style={{ color: selected ? "#1677ff" : undefined, fontSize: 13 }}
                        >
                          {s.name}
                        </Typography.Text>
                        <div style={{ marginTop: 2 }}>
                          <Typography.Text type="secondary" style={{ fontSize: 11 }}>
                            {s.key === "" ? "由 LLM 决定" : s.key}
                          </Typography.Text>
                        </div>
                      </div>
                    </Tooltip>
                  </Col>
                );
              })}
            </Row>
          )}
        </div>

        {/* 场景模板 + 转场效果 */}
        <Row gutter={16} style={{ marginBottom: 20 }}>
          <Col xs={24} md={12}>
            <Space style={{ marginBottom: 8 }}>
              <Typography.Text strong>场景模板</Typography.Text>
              <Typography.Text type="secondary" style={{ fontSize: 12 }}>
                预设镜头节奏与景别组合
              </Typography.Text>
            </Space>
            <Select
              style={{ width: "100%" }}
              value={sceneTemplate}
              onChange={setSceneTemplate}
              options={[
                { value: "", label: "自动（由 LLM 决定）" },
                ...sceneList.map((s) => ({ value: s.key, label: s.name })),
              ]}
            />
            {selectedScene && (
              <div style={{ marginTop: 6 }}>
                <Typography.Text type="secondary" style={{ fontSize: 12 }}>
                  节奏：{selectedScene.shot_rhythm} · 景别：{selectedScene.shot_sequence}
                </Typography.Text>
              </div>
            )}
          </Col>
          <Col xs={24} md={12}>
            <Space style={{ marginBottom: 8 }}>
              <Typography.Text strong>转场效果</Typography.Text>
              <Typography.Text type="secondary" style={{ fontSize: 12 }}>
                镜头之间的过渡方式
              </Typography.Text>
            </Space>
            <Select
              style={{ width: "100%" }}
              value={transition}
              onChange={setTransition}
              options={TRANSITION_OPTIONS}
            />
          </Col>
        </Row>

        {/* 质量等级 */}
        <div>
          <Space style={{ marginBottom: 8 }}>
            <Typography.Text strong>质量等级</Typography.Text>
            <Typography.Text type="secondary" style={{ fontSize: 12 }}>
              控制输出分辨率与画面细节
            </Typography.Text>
          </Space>
          <Radio.Group
            value={qualityLevel}
            onChange={(e) => setQualityLevel(e.target.value)}
            style={{ width: "100%" }}
          >
            <Row gutter={[8, 8]}>
              {qualityOptions.map((q) => (
                <Col key={q.key} xs={24} sm={12} md={6}>
                  <Radio value={q.key} style={{ alignItems: "flex-start" }}>
                    <div style={{ display: "inline-block" }}>
                      <Typography.Text strong>{q.label}</Typography.Text>
                      <div>
                        <Typography.Text type="secondary" style={{ fontSize: 11 }}>
                          {q.desc}
                        </Typography.Text>
                      </div>
                    </div>
                  </Radio>
                </Col>
              ))}
            </Row>
          </Radio.Group>
        </div>
      </Card>

      {/* 本地素材导入 */}
      <Card
        size="small"
        style={{ marginBottom: 16 }}
        title={
          <Space>
            <InboxOutlined />
            本地素材导入
          </Space>
        }
        extra={
          uploadedAssetIds.length > 0 ? (
            <Space>
              <Tag color="green">已上传 {uploadedAssetIds.length} 个</Tag>
              <Typography.Link
                onClick={() => {
                  setUploadFileList([]);
                }}
              >
                清空
              </Typography.Link>
            </Space>
          ) : null
        }
      >
        <Upload.Dragger
          multiple
          fileList={uploadFileList}
          accept="image/*,video/*,audio/*,.flv,.mkv,.m4v,.m4a,.ogg,.flac,.bmp,.webp"
          customRequest={({ file, onSuccess, onError }) => {
            uploadMut.mutate(file as File, {
              onSuccess: (res) => {
                onSuccess?.(res, file);
                message.success(`上传成功：${(file as File).name}（asset_id=${res.asset_id}）`);
                qc.invalidateQueries({ queryKey: ["tools-assets"] });
              },
              onError: (err) => {
                onError?.(err);
              },
            });
          }}
          onChange={({ fileList }) => {
            setUploadFileList(fileList);
          }}
          onRemove={(file) => {
            setUploadFileList((prev) => prev.filter((f) => f.uid !== file.uid));
            message.info(`已从列表移除：${file.name}`);
            return true;
          }}
        >
          <p className="ant-upload-drag-icon">
            <InboxOutlined />
          </p>
          <p className="ant-upload-text">点击或拖拽文件到此区域上传</p>
          <p className="ant-upload-hint">
            支持图片 / 视频 / 音频，单个文件不超过 100MB，可多选
          </p>
        </Upload.Dragger>
        {uploadedAssetIds.length > 0 && (
          <div style={{ marginTop: 12 }}>
            <Typography.Text type="secondary" style={{ fontSize: 12 }}>
              将随生成请求一起传给编排器参与拼接：
            </Typography.Text>
            <Space wrap style={{ marginTop: 4 }}>
              {uploadedAssetIds.map((id) => (
                <Tag key={id} color="blue">
                  asset_id: {id}
                </Tag>
              ))}
            </Space>
          </div>
        )}
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

      {/* 生成资产展示 — 带视频预览、下载、增强、发布 */}
      {(genMut.isSuccess || batchMut.isSuccess) && (
        <Card
          size="small"
          title={
            <Space>
              <VideoCameraOutlined />
              生成的资产
            </Space>
          }
        >
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
                const aid = Number(a.asset_id);
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
                              height: 200,
                              objectFit: "contain",
                              borderRadius: "6px 6px 0 0",
                              background: "#000",
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
                      actions={[
                        <Tooltip key="download" title="下载">
                          <DownloadOutlined onClick={() => handleDownload(a.url, `${a.provider}_${a.asset_id}`)} />
                        </Tooltip>,
                        ...(isVid ? [
                          <Tooltip key="enhance" title="AI 超分 + 补帧">
                            <Popconfirm
                              title="AI 视频增强"
                              description="将使用 Real-ESRGAN 超分辨率 + RIFE 帧插值，可能需要较长时间。继续？"
                              onConfirm={() => enhanceMut.mutate({ assetId: aid, scale: 2, fps: 60 })}
                              okText="开始增强"
                              cancelText="取消"
                            >
                              <ArrowUpOutlined />
                            </Popconfirm>
                          </Tooltip>,
                        ] : []),
                        ...(isVid ? [
                          <Tooltip key="publish" title="发布到社交平台">
                            <ShareAltOutlined onClick={() => openPublish(aid)} />
                          </Tooltip>,
                        ] : []),
                      ]}
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
                            {enhanceMut.isPending && enhanceMut.variables?.assetId === aid && " · 增强中..."}
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

      {/* 批量生成弹窗 */}
      <Modal
        title={
          <Space>
            <AppstoreOutlined />
            批量生成
          </Space>
        }
        open={batchOpen}
        onCancel={() => { setBatchOpen(false); setBatchResult(null); }}
        footer={[
          <Button key="cancel" onClick={() => { setBatchOpen(false); setBatchResult(null); }}>关闭</Button>,
          <Button
            key="submit"
            type="primary"
            loading={batchMut.isPending}
            onClick={handleBatchGenerate}
            icon={<RocketOutlined />}
          >
            开始批量生成
          </Button>,
        ]}
      >
        <Typography.Paragraph type="secondary">
          同一提示词生成多个变体，每个变体使用不同的 LLM 随机性，适合"一个主题出多个版本选最优"。
        </Typography.Paragraph>
        <Form layout="vertical">
          <Form.Item label="生成数量">
            <InputNumber
              min={1}
              max={10}
              value={batchCount}
              onChange={(v) => setBatchCount(v || 3)}
              style={{ width: "100%" }}
            />
          </Form.Item>
        </Form>

        {/* 批量结果 */}
        {batchResult && (
          <div style={{ marginTop: 16 }}>
            <Alert
              type={batchResult.results.every((r) => r.spec_id !== null) ? "success" : "warning"}
              showIcon
              message={`${batchResult.message}（成功 ${batchResult.results.filter((r) => r.spec_id !== null).length}/${batchResult.count}）`}
            />
            <div style={{ marginTop: 8 }}>
              {batchResult.results.map((r, i) => (
                <div key={i} style={{ padding: "4px 0" }}>
                  <Space>
                    <Tag color={r.spec_id !== null ? "green" : "red"}>
                      变体 {i + 1}
                    </Tag>
                    {r.spec_id !== null ? (
                      <span>spec_id: <b>{r.spec_id}</b></span>
                    ) : (
                      <Typography.Text type="danger">失败：{r.error}</Typography.Text>
                    )}
                  </Space>
                </div>
              ))}
            </div>
          </div>
        )}
      </Modal>

      {/* 发布弹窗 */}
      <Modal
        title={
          <Space>
            <ShareAltOutlined />
            发布到社交平台
          </Space>
        }
        open={publishOpen}
        onCancel={() => setPublishOpen(false)}
        onOk={handlePublish}
        confirmLoading={publishMut.isPending}
        okText="发布"
      >
        <Form form={publishForm} layout="vertical" initialValues={{ platform: "douyin" }}>
          <Form.Item name="platform" label="发布平台" rules={[{ required: true }]}>
            <Select options={PUBLISH_PLATFORMS} />
          </Form.Item>
          <Form.Item name="title" label="标题">
            <Input placeholder="输入视频标题" />
          </Form.Item>
          <Form.Item name="description" label="描述">
            <Input.TextArea rows={3} placeholder="输入视频描述" />
          </Form.Item>
          <Form.Item name="tags" label="标签">
            <Select mode="tags" placeholder="输入标签后回车" />
          </Form.Item>
        </Form>
        <Typography.Text type="warning" style={{ fontSize: 12 }}>
          需在 .env 中配置对应平台的 access_token / cookie 后才能真实发布。
        </Typography.Text>
      </Modal>
    </div>
  );
}
