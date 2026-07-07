// client 拦截器测试 — 401 去重、friendlyMessage 附加
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { AxiosError } from "axios";
import { http, setOnUnauthorized } from "@/api/client";

// 构造一个 401 AxiosError，模拟后端返回 token 失效
function make401(detail = "token 失效"): AxiosError {
  // 用 plain 对象模拟 AxiosError 结构，避免构造完整 AxiosResponse
  return {
    name: "AxiosError",
    message: "Unauthorized",
    code: "401",
    config: {},
    response: {
      status: 401,
      statusText: "Unauthorized",
      headers: {},
      config: {},
      data: { detail },
    },
  } as unknown as AxiosError;
}

describe("client 401 去重", () => {
  let originalAdapter: unknown;
  beforeEach(() => {
    originalAdapter = http.defaults.adapter;
    // 自定义 adapter：所有请求都 reject 一个 401 错误
    http.defaults.adapter = async () => {
      throw make401();
    };
  });
  afterEach(() => {
    http.defaults.adapter = originalAdapter as never;
    setOnUnauthorized(null);
  });

  it("并发多个 401 只触发一次 on401", async () => {
    const on401 = vi.fn();
    setOnUnauthorized(on401);
    await Promise.allSettled([
      http.get("/a").catch(() => {}),
      http.get("/b").catch(() => {}),
      http.get("/c").catch(() => {}),
    ]);
    expect(on401).toHaveBeenCalledTimes(1);
  });

  it("重新注册 onUnauthorized 后去重标志重置，新 401 可再次触发", async () => {
    const first = vi.fn();
    setOnUnauthorized(first);
    await Promise.allSettled([http.get("/a").catch(() => {}), http.get("/b").catch(() => {})]);
    expect(first).toHaveBeenCalledTimes(1);

    // 重新注册（模拟重新登录后 AuthContext 重挂载场景）
    const second = vi.fn();
    setOnUnauthorized(second);
    await Promise.allSettled([http.get("/c").catch(() => {})]);
    expect(second).toHaveBeenCalledTimes(1);
  });
});
