// Axios 实例 — 统一基础地址、token 注入、401 处理、错误兜底
import axios, { AxiosError } from "axios";

export const apiBase = import.meta.env.VITE_API_BASE_URL || "/api/v1";

export const http = axios.create({
  baseURL: apiBase,
  timeout: 30000,
  headers: { "Content-Type": "application/json" },
});

// token 持有器（由 AuthContext 设置，避免循环依赖）
let _token: string | null = null;
export function setAuthToken(token: string | null) {
  _token = token;
}
export function getAuthToken() {
  return _token;
}

// 请求拦截：自动注入 Authorization
http.interceptors.request.use((config) => {
  if (_token) {
    config.headers.Authorization = `Bearer ${_token}`;
  }
  return config;
});

// 把 axios 错误翻译成用户能看懂的中文提示
function friendlyMessage(error: unknown): string {
  if (!axios.isAxiosError(error)) return (error as Error)?.message || "请求失败";
  const status = error.response?.status;
  if (status && status >= 400 && status < 500 && error.response?.data?.detail) {
    return error.response.data.detail;
  }
  if (status === 404) return "资源不存在";
  if (status && status >= 500) return "服务异常，请联系管理员";
  if (error.code === "ECONNABORTED") return "请求超时，请稍后重试";
  if (!error.response) return "网络连接失败，请检查后端服务是否启动";
  return error.message || "请求失败";
}

// 401 处理回调（由 AuthContext 注册，避免直接操作 DOM）
// _firing401 标志：同一批并发 401 只触发一次回调，避免多次 logout 闪烁
let _on401: (() => void) | null = null;
let _firing401 = false;
export function setOnUnauthorized(handler: (() => void) | null) {
  _on401 = handler;
  // 重新注册时重置去重标志，让新会话的 401 仍能触发
  _firing401 = false;
}

// 响应拦截：统一错误 + 401 回调（去重）
http.interceptors.response.use(
  (resp) => resp,
  (error: AxiosError) => {
    if (error.response?.status === 401 && _on401 && !_firing401) {
      _firing401 = true;
      _on401();
      // 下一个事件循环重置标志，让重新登录后的 401 可再次触发
      setTimeout(() => {
        _firing401 = false;
      }, 0);
    }
    // 保留原始 AxiosError，附加 friendlyMessage
    (error as Error & { friendlyMessage?: string }).friendlyMessage = friendlyMessage(error);
    return Promise.reject(error);
  },
);

// 通用 CRUD 工厂
export function crud<T, C = Partial<T>>(resource: string) {
  return {
    list: (params?: Record<string, unknown>) =>
      http.get<T[]>(resource, { params }).then((r) => r.data),
    get: (id: number) => http.get<T>(`${resource}/${id}`).then((r) => r.data),
    create: (payload: C) => http.post<T>(resource, payload).then((r) => r.data),
    remove: (id: number) =>
      http.delete<{ message: string }>(`${resource}/${id}`).then((r) => r.data),
  };
}
