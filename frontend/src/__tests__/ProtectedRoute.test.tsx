// ProtectedRoute 测试 — 未登录时跳转 /login，已登录时透传 children
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import ProtectedRoute from "@/components/ProtectedRoute";
import { AuthContext, type AuthState } from "@/contexts/AuthContext";

function renderWithAuth(authValue: AuthState, initialPath = "/dashboard") {
  return render(
    <AuthContext.Provider value={authValue}>
      <MemoryRouter
        initialEntries={[initialPath]}
        future={{ v7_startTransition: true, v7_relativeSplatPath: true }}
      >
        <Routes>
          <Route path="/login" element={<div>登录页</div>} />
          <Route
            path="/dashboard"
            element={
              <ProtectedRoute>
                <div>受保护页面</div>
              </ProtectedRoute>
            }
          />
        </Routes>
      </MemoryRouter>
    </AuthContext.Provider>
  );
}

const baseAuth: AuthState = {
  token: null,
  user: null,
  isAuthenticated: false,
  initializing: false,
  login: vi.fn(),
  logout: vi.fn(),
};

beforeEach(() => {
  sessionStorage.clear();
});

describe("ProtectedRoute", () => {
  it("未登录时重定向到 /login", () => {
    renderWithAuth(baseAuth);
    expect(screen.getByText("登录页")).toBeInTheDocument();
    expect(screen.queryByText("受保护页面")).not.toBeInTheDocument();
  });

  it("正在恢复会话时显示 loading", () => {
    renderWithAuth({ ...baseAuth, initializing: true });
    // antd Spin 渲染为 role=status，不会渲染受保护内容
    expect(screen.queryByText("受保护页面")).not.toBeInTheDocument();
  });

  it("已登录时透传 children", () => {
    renderWithAuth({ ...baseAuth, isAuthenticated: true, token: "t" });
    expect(screen.getByText("受保护页面")).toBeInTheDocument();
  });
});
