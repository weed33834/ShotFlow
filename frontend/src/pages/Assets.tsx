// 资产画廊 — 按类型扫描磁盘文件 + 数据库资产记录
import { useQuery } from "@tanstack/react-query";
import {
  Alert,
  Card,
  Col,
  Empty,
  Row,
  Statistic,
  Table,
  Tabs,
  Typography,
} from "antd";
import { useState } from "react";
import { http } from "@/api/client";

type AssetType = "image" | "video" | "audio" | "doc";

interface ScanFile {
  path: string;
  filename: string;
  size: number;
  dir: string;
}

interface ScanResult {
  asset_type: string;
  count: number;
  files: ScanFile[];
}

const TYPE_LABELS: Record<AssetType, string> = {
  image: "图片",
  video: "视频",
  audio: "音频",
  doc: "文档",
};

function fmtSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

export default function Assets() {
  const [tab, setTab] = useState<AssetType>("image");

  const { data: scan, isLoading, error } = useQuery<ScanResult>({
    queryKey: ["scan", tab],
    queryFn: () =>
      http.get<ScanResult>(`/assets/scan/${tab}`).then((r) => r.data),
  });

  return (
    <div>
      <Typography.Title level={4}>资产画廊</Typography.Title>
      <Tabs
        activeKey={tab}
        onChange={(k) => setTab(k as AssetType)}
        items={(Object.keys(TYPE_LABELS) as AssetType[]).map((t) => ({
          key: t,
          label: TYPE_LABELS[t],
        }))}
      />

      {error && (
        <Alert
          type="error"
          showIcon
          style={{ marginBottom: 16 }}
          message="资产扫描失败"
          description={
            (error as Error & { friendlyMessage?: string }).friendlyMessage || error.message
          }
        />
      )}

      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col span={6}>
          <Card size="small">
            <Statistic title={`${TYPE_LABELS[tab]}文件数`} value={scan?.count ?? 0} />
          </Card>
        </Col>
        <Col span={6}>
          <Card size="small">
            <Statistic
              title="总大小"
              value={
                scan?.files
                  ? fmtSize(scan.files.reduce((s, f) => s + f.size, 0))
                  : "—"
              }
            />
          </Card>
        </Col>
      </Row>

      <Card title={`${TYPE_LABELS[tab]} 文件清单`} size="small">
        <Table<ScanFile>
          rowKey="path"
          loading={isLoading}
          dataSource={scan?.files ?? []}
          pagination={{ pageSize: 20 }}
          locale={{ emptyText: <Empty description="无文件" /> }}
          columns={[
            { title: "文件名", dataIndex: "filename", key: "filename" },
            { title: "目录", dataIndex: "dir", key: "dir" },
            {
              title: "大小",
              dataIndex: "size",
              key: "size",
              width: 100,
              render: (v: number) => fmtSize(v),
            },
            { title: "路径", dataIndex: "path", key: "path", ellipsis: true },
          ]}
        />
      </Card>
    </div>
  );
}
