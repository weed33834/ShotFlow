// 主布局 — ProLayout 侧边栏 + 路由出口 + 用户菜单
import { ProLayout } from "@ant-design/pro-components";
import {
  AppstoreOutlined,
  DashboardOutlined,
  FileImageOutlined,
  LogoutOutlined,
  PictureOutlined,
  PlayCircleOutlined,
  SettingOutlined,
  SoundOutlined,
  ThunderboltOutlined,
  ToolOutlined,
  TrophyOutlined,
  VideoCameraOutlined,
} from "@ant-design/icons";
import { Dropdown, Badge } from "antd";
import { useEffect } from "react";
import { Link, Outlet, useLocation, useNavigate } from "react-router-dom";
import { useQueueStream } from "@/hooks/useQueueStream";
import { useAuth } from "@/contexts/AuthContext";
import { queryClient } from "@/lib/queryClient";

const menuRoutes = {
  path: "/",
  routes: [
    { path: "/dashboard", name: "总览看板", icon: <DashboardOutlined /> },
    { path: "/projects", name: "项目", icon: <AppstoreOutlined /> },
    { path: "/shots", name: "镜头", icon: <VideoCameraOutlined /> },
    { path: "/keyframes", name: "关键帧", icon: <FileImageOutlined /> },
    { path: "/queue", name: "渲染队列", icon: <ThunderboltOutlined /> },
    { path: "/workflows", name: "工作流", icon: <ToolOutlined /> },
    { path: "/workflow-configs", name: "工作流配置", icon: <SettingOutlined /> },
    { path: "/assets", name: "资产", icon: <PictureOutlined /> },
    { path: "/audio", name: "对白配音", icon: <SoundOutlined /> },
    { path: "/qa", name: "质检", icon: <PlayCircleOutlined /> },
    { path: "/case-studies", name: "用户案例", icon: <TrophyOutlined /> },
  ],
};

export default function MainLayout() {
  const location = useLocation();
  const navigate = useNavigate();
  const { user, logout, token } = useAuth();
  const { stats, connected } = useQueueStream(true);
  const pending = stats?.pending ?? 0;

  // 登出（token 变 null）时清理 queryClient 缓存，避免泄漏前一个用户的数据
  useEffect(() => {
    if (!token) queryClient.clear();
  }, [token]);

  const userMenu = {
    items: [
      {
        key: "logout",
        label: "退出登录",
        icon: <LogoutOutlined />,
        onClick: () => {
          logout();
          navigate("/login", { replace: true });
        },
      },
    ],
  };

  return (
    <ProLayout
      title="ShotFlow"
      logo={false}
      layout="mix"
      fixedHeader
      fixSiderbar
      route={menuRoutes}
      location={{ pathname: location.pathname }}
      menuItemRender={(item, dom) =>
        item.path ? <Link to={item.path}>{dom}</Link> : dom
      }
      avatarProps={{
        title: user?.full_name || user?.username || "ShotFlow",
        size: "small",
        render: (_props, dom) => (
          <Dropdown menu={userMenu}>{dom}</Dropdown>
        ),
      }}
      footerRender={() => (
        <div style={{ textAlign: "center", color: "#888", fontSize: 12 }}>
          ShotFlow · AIGC 视频工业化流水线 · SSE{" "}
          <Badge status={connected ? "success" : "error"} text={connected ? "已连接" : "断开"} />
        </div>
      )}
    >
      {pending > 0 && (
        <div
          style={{
            position: "fixed",
            top: 12,
            right: 24,
            zIndex: 100,
            background: "rgba(24,144,255,0.1)",
            padding: "4px 12px",
            borderRadius: 12,
            fontSize: 13,
          }}
        >
          待执行任务：<b>{pending}</b>
        </div>
      )}
      <Outlet />
    </ProLayout>
  );
}
