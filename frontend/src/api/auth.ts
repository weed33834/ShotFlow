// Auth API — 登录、注册、当前用户
import { http } from "./client";
import type { UserOut } from "@/types";

export interface TokenResponse {
  access_token: string;
  token_type: string;
  user: UserOut;
}

export const authApi = {
  login: (username: string, password: string) =>
    http
      .post<TokenResponse>("/auth/login", { username, password })
      .then((r) => r.data),
  // token 由 axios 请求拦截器统一注入，这里无需显式传
  me: () => http.get<UserOut>("/auth/me").then((r) => r.data),
  register: (payload: {
    username: string;
    email: string;
    password: string;
    full_name?: string;
    role?: string;
  }) => http.post<UserOut>("/auth", payload).then((r) => r.data),
};
