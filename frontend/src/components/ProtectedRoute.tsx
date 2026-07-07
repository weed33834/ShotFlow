// 路由守卫 — 未登录跳转登录页
import { Navigate, useLocation } from "react-router-dom";
import { Spin } from "antd";
import { useAuth } from "@/contexts/AuthContext";
import type { ReactNode } from "react";

export default function ProtectedRoute({ children }: { children: ReactNode }) {
  const { isAuthenticated, initializing } = useAuth();
  const location = useLocation();

  // 正在用存量 token 恢复会话，先显示 loading，避免恢复瞬间被误判未登录跳转
  if (initializing) {
    return (
      <div style={{ minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center" }}>
        <Spin size="large" tip="正在恢复会话…" />
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }
  return <>{children}</>;
}
