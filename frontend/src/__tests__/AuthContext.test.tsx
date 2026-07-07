// AuthContext 测试 — login() 持久化 token、logout() 清理 token
import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { AuthProvider, useAuth } from "@/contexts/AuthContext";
import { authApi } from "@/api/auth";
import type { ReactNode } from "react";

vi.mock("@/api/auth", () => ({
  authApi: {
    login: vi.fn(),
    me: vi.fn().mockResolvedValue({
      id: 1,
      username: "admin",
      email: "a@t.com",
      full_name: "Admin",
      role: "admin",
      is_active: true,
      is_superuser: true,
      created_at: "",
      updated_at: "",
    }),
    register: vi.fn(),
  },
}));

const wrapper = ({ children }: { children: ReactNode }) => <AuthProvider>{children}</AuthProvider>;

beforeEach(() => {
  sessionStorage.clear();
  vi.clearAllMocks();
});

describe("AuthContext", () => {
  it("login() 调用 authApi.login 并持久化 token", async () => {
    const fakeUser = {
      id: 1,
      username: "admin",
      email: "a@t.com",
      full_name: "Admin",
      role: "admin",
      is_active: true,
      is_superuser: true,
      created_at: "",
      updated_at: "",
    };
    (authApi.login as ReturnType<typeof vi.fn>).mockResolvedValue({
      access_token: "fake-token",
      token_type: "bearer",
      user: fakeUser,
    });

    const { result } = renderHook(() => useAuth(), { wrapper });

    await act(async () => {
      await result.current.login("admin", "pwd");
    });

    expect(authApi.login).toHaveBeenCalledWith("admin", "pwd");
    expect(result.current.token).toBe("fake-token");
    expect(result.current.user).toEqual(fakeUser);
    expect(result.current.isAuthenticated).toBe(true);
    expect(sessionStorage.getItem("shotflow_token")).toBe("fake-token");
  });

  it("logout() 清掉 token 与 user", async () => {
    const fakeUser = {
      id: 1,
      username: "admin",
      email: "a@t.com",
      full_name: "Admin",
      role: "admin",
      is_active: true,
      is_superuser: true,
      created_at: "",
      updated_at: "",
    };
    (authApi.login as ReturnType<typeof vi.fn>).mockResolvedValue({
      access_token: "fake-token",
      token_type: "bearer",
      user: fakeUser,
    });

    const { result } = renderHook(() => useAuth(), { wrapper });

    await act(async () => {
      await result.current.login("admin", "pwd");
    });
    expect(result.current.isAuthenticated).toBe(true);

    act(() => {
      result.current.logout();
    });

    expect(result.current.token).toBeNull();
    expect(result.current.user).toBeNull();
    expect(result.current.isAuthenticated).toBe(false);
    expect(sessionStorage.getItem("shotflow_token")).toBeNull();
  });

  it("无 token 时 initializing 立即为 false", () => {
    const { result } = renderHook(() => useAuth(), { wrapper });
    expect(result.current.initializing).toBe(false);
    expect(result.current.isAuthenticated).toBe(false);
  });
});
