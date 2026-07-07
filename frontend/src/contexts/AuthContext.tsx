// Auth context — token 与当前用户管理
// 持久化策略：token 存 sessionStorage（标签页内持久，关浏览器即清，比 localStorage 更克制）
// 刷新页面时从 sessionStorage 恢复 token 并调 /auth/me 拉回用户，避免反复登录
/* eslint-disable react-refresh/only-export-components -- 标准 Context 模式：Provider + Context 对象 + hook 同文件，拆分会增加导入负担 */
import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { authApi, type TokenResponse } from "@/api/auth";
import { setAuthToken, setOnUnauthorized } from "@/api/client";
import { queryClient } from "@/lib/queryClient";
import type { UserOut } from "@/types";

const TOKEN_KEY = "shotflow_token";

export interface AuthState {
  token: string | null;
  user: UserOut | null;
  isAuthenticated: boolean;
  initializing: boolean;
  login: (username: string, password: string) => Promise<void>;
  logout: () => void;
}

export const AuthContext = createContext<AuthState | undefined>(undefined);

function readStoredToken(): string | null {
  try {
    return sessionStorage.getItem(TOKEN_KEY);
  } catch {
    return null;
  }
}

function writeStoredToken(token: string | null) {
  try {
    if (token) sessionStorage.setItem(TOKEN_KEY, token);
    else sessionStorage.removeItem(TOKEN_KEY);
  } catch {
    /* sessionStorage 不可用时忽略 */
  }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const storedToken = readStoredToken();
  const [token, setToken] = useState<string | null>(storedToken);
  const [user, setUser] = useState<UserOut | null>(null);
  const [initializing, setInitializing] = useState(!!storedToken);

  const logout = useCallback(() => {
    writeStoredToken(null);
    setAuthToken(null);
    setToken(null);
    setUser(null);
    queryClient.clear();
  }, []);

  // 注册 401 回调：token 失效时通过 React 状态清理，不直接操作 DOM
  useEffect(() => {
    setOnUnauthorized(() => {
      logout();
    });
    return () => setOnUnauthorized(null);
  }, [logout]);

  const login = useCallback(async (username: string, password: string) => {
    const resp: TokenResponse = await authApi.login(username, password);
    writeStoredToken(resp.access_token);
    setAuthToken(resp.access_token); // 同步设置，避免 SSE 等 effect 时序问题
    setToken(resp.access_token);
    setUser(resp.user);
    setInitializing(false);
  }, []);

  // 同步 token 到 axios 拦截器（覆盖刷新页面等场景）
  useEffect(() => {
    setAuthToken(token);
  }, [token]);

  // 挂载时若有存量 token，调 /auth/me 恢复用户；仅 401（token 失效）才登出，
  // 网络 5xx 等临时错误保留 token，避免后端短暂不可用就把所有用户踢下线
  useEffect(() => {
    if (!token) {
      setInitializing(false);
      return;
    }
    if (user) {
      setInitializing(false);
      return; // login 已设置 user，跳过冗余 me() 调用
    }
    let cancelled = false;
    authApi
      .me()
      .then((u) => {
        if (!cancelled) {
          setUser(u);
          setInitializing(false);
        }
      })
      .catch((err) => {
        if (cancelled) return;
        // 401/403 表示 token 失效，需登出；其余错误（网络/5xx）保留 token
        const status = err?.response?.status;
        if (status === 401 || status === 403) {
          logout();
        }
        setInitializing(false);
      });
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token]);

  const value = useMemo<AuthState>(
    () => ({
      token,
      user,
      isAuthenticated: !!token,
      initializing,
      login,
      logout,
    }),
    [token, user, initializing, login, logout]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth 必须在 AuthProvider 内使用");
  return ctx;
}
