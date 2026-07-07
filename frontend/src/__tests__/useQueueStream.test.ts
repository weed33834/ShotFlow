// useQueueStream 单例化测试 — 多组件共享一条 SSE 连接
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { setAuthToken } from "@/api/client";
import { useQueueStream } from "@/hooks/useQueueStream";

// Mock EventSource：记录所有实例，提供测试辅助方法
class MockEventSource {
  static instances: MockEventSource[] = [];
  url: string;
  onopen: (() => void) | null = null;
  onerror: (() => void) | null = null;
  private listeners: Record<string, Array<(e: { data: string }) => void>> = {};
  constructor(url: string) {
    this.url = url;
    MockEventSource.instances.push(this);
  }
  addEventListener(type: string, fn: (e: { data: string }) => void) {
    (this.listeners[type] ||= []).push(fn);
  }
  close() {
    MockEventSource.instances = MockEventSource.instances.filter((s) => s !== this);
  }
  // 测试辅助
  emitOpen() {
    this.onopen?.();
  }
  emitStats(data: unknown) {
    this.listeners["stats"]?.forEach((fn) => fn({ data: JSON.stringify(data) }));
  }
}

describe("useQueueStream 单例化", () => {
  beforeEach(() => {
    MockEventSource.instances = [];
    vi.stubGlobal("EventSource", MockEventSource);
    setAuthToken("fake-token");
  });
  afterEach(() => {
    vi.unstubAllGlobals();
    setAuthToken(null);
  });

  it("多个 hook 实例只创建一条 EventSource", () => {
    const { unmount: u1 } = renderHook(() => useQueueStream(true));
    const { unmount: u2 } = renderHook(() => useQueueStream(true));
    expect(MockEventSource.instances.length).toBe(1);
    u1();
    u2();
  });

  it("所有 hook 卸载后 EventSource 关闭", () => {
    const { unmount } = renderHook(() => useQueueStream(true));
    expect(MockEventSource.instances.length).toBe(1);
    unmount();
    expect(MockEventSource.instances.length).toBe(0);
  });

  it("stats 推送后所有 hook 实例都收到最新数据", () => {
    const r1 = renderHook(() => useQueueStream(true));
    const r2 = renderHook(() => useQueueStream(true));
    const es = MockEventSource.instances[0];
    act(() => {
      es.emitOpen();
      es.emitStats({ pending: 5, running: 2, completed: 1, failed: 0, cancelled: 0, total: 8 });
    });
    expect(r1.result.current.stats?.pending).toBe(5);
    expect(r2.result.current.stats?.pending).toBe(5);
    expect(r1.result.current.connected).toBe(true);
    expect(r2.result.current.connected).toBe(true);
    r1.unmount();
    r2.unmount();
  });
});
