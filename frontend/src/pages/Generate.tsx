// 一句话出片 — 自然语言 → 出片（最小网页 UI）
import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Alert,
  App,
  Button,
  Card,
  Col,
  Empty,
  Row,
  Select,
  Input,
  Space,
  Spin,
  Tag,
  Typography,
} from "antd";
import { generateApi, toolsApi } from "@/api";
import type { GenerateResponse, OutputType, ToolResult } from "@/types";

const OUTPUT_OPTIONS: { value: OutputType; label: string }[] = [
  { value: "video", label: "视频 video" },
  { value: "image_set", label: "图集 image_set" },
  { value: "micro_movie", label: "微电影 micro_movie" },
  { value: "comic", label: "漫画 comic" },
  { value: "vn", label: "视觉小说 vn" },
];

const COPYRIGHT_HINT =
  "⚠️ 本平台仅提供生成工具，所用素材/角色/音乐的版权由使用者自行负责";

// 根据 url 或 meta 粗略判断是否为图片，图片用 <img>，其余显示链接 + provider 标签
function isImageAsset(a: ToolResult): boolean {
  const fromMeta = (a.meta?.type as string | undefined) ?? "";
  if (fromMeta.startsWith("image")) return true;
  const u = a.url.toLowerCase();
  return /\.(png|jpe?g|gif|webp|bmp|svg)(\?|#|$)/i.test(u);
}

export default function Generate() {
  const { message } = App.useApp();
  const qc = useQueryClient();
  const [prompt, setPrompt] = useState("");
  const [outputType, setOutputType] = useState<OutputType>("video");

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
    const nl = prompt.trim();
    if (!nl) {
      message.warning("请先输入一句话描述");
      return;
    }
    genMut.mutate({ nl_prompt: nl, output_type: outputType });
  };

  return (
    <div>
      <Typography.Title level={4}>一句话出片</Typography.Title>

      <Card size="small" style={{ marginBottom: 16 }}>
        <Space direction="vertical" style={{ width: "100%" }} size="middle">
          <Typography.Text strong>用一句话描述你想生成的画面</Typography.Text>
          <Input.TextArea
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            rows={4}
            placeholder="魔改奶龙奶娃捧腹大笑15秒"
            maxLength={2000}
            showCount
          />

          <Space wrap>
            <Select<OutputType>
              value={outputType}
              onChange={setOutputType}
              options={OUTPUT_OPTIONS}
              style={{ width: 220 }}
            />
            <Button
              type="primary"
              loading={genMut.isPending}
              onClick={handleGenerate}
            >
              生成
            </Button>
          </Space>

          {/* 版权提示：固定小字，始终可见 */}
          <Typography.Text type="warning" style={{ fontSize: 12 }}>
            {COPYRIGHT_HINT}
          </Typography.Text>

          {genMut.isSuccess && (
            <Alert
              type="success"
              showIcon
              message="生成成功"
              description={
                <div>
                  <div>
                    spec_id：<b>{genMut.data.spec_id}</b>
                  </div>
                  <div>
                    status：<Tag color={genMut.data.status === "generated" ? "green" : "blue"}>
                      {genMut.data.status}
                    </Tag>
                  </div>
                  {genMut.data.message && <div>{genMut.data.message}</div>}
                </div>
              }
            />
          )}
        </Space>
      </Card>

      {genMut.isSuccess && (
        <Card size="small" title="最近生成的资产">
          {assetsQ.isLoading ? (
            <Spin />
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
              {assetsQ.data!.map((a) => (
                <Col key={a.asset_id} xs={24} sm={12} md={8} lg={6}>
                  <Card size="small" hoverable>
                    {isImageAsset(a) ? (
                      <img
                        src={a.url}
                        alt={a.asset_id}
                        style={{ width: "100%", borderRadius: 6, objectFit: "cover" }}
                      />
                    ) : (
                      <div>
                        <a href={a.url} target="_blank" rel="noreferrer">
                          {a.url}
                        </a>
                      </div>
                    )}
                    <div style={{ marginTop: 8 }}>
                      <Tag color="geekblue">{a.provider}</Tag>
                      <Typography.Text type="secondary" style={{ fontSize: 12 }}>
                        {a.asset_id}
                      </Typography.Text>
                    </div>
                  </Card>
                </Col>
              ))}
            </Row>
          )}
        </Card>
      )}
    </div>
  );
}
