// 总览看板 — 健康检查 + 队列统计 + 项目概览
import { useQuery } from "@tanstack/react-query";
import { Alert, Card, Col, Empty, Row, Spin, Statistic, Table, Typography } from "antd";
import dayjs from "dayjs";
import { healthApi, projectsApi, queueApi } from "@/api";
import { ProjectStatusTag } from "@/components/StatusTag";
import { useQueueStream } from "@/hooks/useQueueStream";

function healthLabel(v?: string) {
  if (!v) return "检测中";
  return v === "ok" ? "正常" : "异常";
}

export default function Dashboard() {
  const healthQ = useQuery({ queryKey: ["health"], queryFn: healthApi.check });
  const statsQ = useQuery({ queryKey: ["queue-stats"], queryFn: queueApi.stats });
  const projectsQ = useQuery({ queryKey: ["projects"], queryFn: () => projectsApi.list() });
  const live = useQueueStream(true);

  const health = healthQ.data;
  const s = live.stats || statsQ.data;

  return (
    <div>
      <Typography.Title level={4}>总览看板</Typography.Title>

      <Row gutter={[16, 16]}>
        <Col xs={24} sm={12} md={6}>
          <Card>
            <Statistic title="待执行任务" value={s?.pending ?? 0} valueStyle={{ color: "#1668dc" }} />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card>
            <Statistic title="执行中" value={s?.running ?? 0} valueStyle={{ color: "#1677ff" }} />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card>
            <Statistic title="已完成" value={s?.completed ?? 0} valueStyle={{ color: "#52c41a" }} />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card>
            <Statistic title="已失败" value={s?.failed ?? 0} valueStyle={{ color: "#ff4d4f" }} />
          </Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
        <Col xs={24} md={12}>
          <Card title="服务健康" size="small">
            {healthQ.isLoading ? (
              <Spin size="small" />
            ) : healthQ.isError ? (
              <Alert type="error" showIcon message="健康检查失败，后端可能未启动" />
            ) : (
              <>
                <p>应用：{health?.app ?? "—"}</p>
                <p>版本：{health?.version ?? "—"}</p>
                <p>
                  数据库：
                  <b style={{ color: health?.db === "ok" ? "#52c41a" : "#ff4d4f" }} title={health?.db}>
                    {healthLabel(health?.db)}
                  </b>
                </p>
                <p>
                  Redis：
                  <b style={{ color: health?.redis === "ok" ? "#52c41a" : "#ff4d4f" }} title={health?.redis}>
                    {healthLabel(health?.redis)}
                  </b>
                </p>
                <p>检测时间：{health ? dayjs(health.timestamp).format("YYYY-MM-DD HH:mm:ss") : "—"}</p>
              </>
            )}
          </Card>
        </Col>
        <Col xs={24} md={12}>
          <Card title="项目概览" size="small">
            <Table
              size="small"
              rowKey="id"
              pagination={false}
              loading={projectsQ.isLoading}
              locale={{ emptyText: <Empty description="暂无项目" /> }}
              dataSource={projectsQ.data ?? []}
              columns={[
                { title: "项目", dataIndex: "title", key: "title" },
                {
                  title: "状态",
                  dataIndex: "status",
                  key: "status",
                  render: (v: string) => <ProjectStatusTag status={v} />,
                },
                {
                  title: "更新时间",
                  dataIndex: "updated_at",
                  key: "updated_at",
                  render: (v: string) => dayjs(v).format("MM-DD HH:mm"),
                },
              ]}
            />
          </Card>
        </Col>
      </Row>
    </div>
  );
}
