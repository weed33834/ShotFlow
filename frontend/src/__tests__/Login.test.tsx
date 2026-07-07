// Login 页测试 — 渲染标题、表单提交调用 login()
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { App as AntdApp, ConfigProvider } from "antd";
import zhCN from "antd/locale/zh_CN";
import Login from "@/pages/Login";
import { AuthContext, type AuthState } from "@/contexts/AuthContext";

beforeEach(() => {
  sessionStorage.clear();
});

function renderLogin(loginFn: ReturnType<typeof vi.fn>) {
  const authValue: AuthState = {
    token: null,
    user: null,
    isAuthenticated: false,
    initializing: false,
    login: loginFn as unknown as AuthState["login"],
    logout: vi.fn(),
  };
  return render(
    <ConfigProvider locale={zhCN}>
      <AntdApp>
        <AuthContext.Provider value={authValue}>
          <MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
            <Login />
          </MemoryRouter>
        </AuthContext.Provider>
      </AntdApp>
    </ConfigProvider>
  );
}

describe("Login 页", () => {
  it("渲染 ShotFlow 标题与表单字段", () => {
    renderLogin(vi.fn());
    expect(screen.getByText("ShotFlow")).toBeInTheDocument();
    // antd Form label 关联的 input 用 placeholder 更稳定
    expect(screen.getByPlaceholderText("请输入用户名")).toBeInTheDocument();
    expect(screen.getByPlaceholderText("请输入密码")).toBeInTheDocument();
    // antd Button 文本被 span 包裹，用 button role 定位
    expect(screen.getByRole("button")).toBeInTheDocument();
  });

  it("填入用户名密码并提交时调用 login()", async () => {
    const loginFn = vi.fn().mockResolvedValue(undefined);
    renderLogin(loginFn);

    fireEvent.change(screen.getByPlaceholderText("请输入用户名"), { target: { value: "admin" } });
    fireEvent.change(screen.getByPlaceholderText("请输入密码"), { target: { value: "pwd" } });
    fireEvent.click(screen.getByRole("button"));

    await waitFor(() => {
      expect(loginFn).toHaveBeenCalledWith("admin", "pwd");
    });
  });

  it("login() 失败时不抛错（错误由 antd message 提示）", async () => {
    const loginFn = vi.fn().mockRejectedValue(new Error("密码错误"));
    renderLogin(loginFn);

    fireEvent.change(screen.getByPlaceholderText("请输入用户名"), { target: { value: "admin" } });
    fireEvent.change(screen.getByPlaceholderText("请输入密码"), { target: { value: "wrong" } });
    fireEvent.click(screen.getByRole("button"));

    await waitFor(() => {
      expect(loginFn).toHaveBeenCalledWith("admin", "wrong");
    });
    // 页面仍在登录页
    expect(screen.getByText("ShotFlow")).toBeInTheDocument();
  });
});
