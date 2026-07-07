// SSE hook — 订阅队列状态推送，自动重连
// 模块级单例：多个组件共享一条 EventSource，避免 MainLayout + Dashboard/Queue 同页开多条连接
// stats 浅比较：内容相同不更新引用，避免每 2 秒无谓重渲染与队列重取
import { useEffect, useReducer } from "react";
import { apiBase, getAuthToken } from "@/api/client";
import type { QueueStats } from "@/types";

const SSE_PATH = `${apiBase}/queue/stream/events`;
// 连续失败上限：超过后停止重连，避免 token 失效时无限重连浪费资源
const MAX_RETRIES = 10;

// ===== 模块级单例 store =====
let _source: EventSource | null = null;
let _stats: QueueStats | null = null;
let _connected = false;
let _refCount = 0;
let _retryCount = 0;
let _reconnectTimer: number | undefined;
const _listeners = new Set<() => void>();

function _notify() {
  _listeners.forEach((fn) => fn());
}

function _ensureSource() {
  if (_source) return;
  // EventSource 不能自定义请求头，token 只能走 query
  const token = getAuthToken();
  if (!token) return; // 未登录不连 SSE
  const es = new EventSource(`${SSE_PATH}?token=${encodeURIComponent(token)}`);
  _source = es;

  es.onopen = () => {
    _retryCount = 0;
    _connected = true;
    _notify();
  };
  es.addEventListener("stats", (e: MessageEvent) => {
    try {
      const next: QueueStats = JSON.parse(e.data);
      // 浅比较：内容相同则不更新引用，避免无谓重渲染与队列重取
      if (JSON.stringify(next) === JSON.stringify(_stats)) return;
      _stats = next;
      _notify();
    } catch {
      /* 忽略解析失败 */
    }
  });
  es.onerror = () => {
    _connected = false;
    _notify();
    es.close();
    _source = null;
    // 超过最大重试次数则停止（token 失效或后端长期不可用）
    if (_retryCount >= MAX_RETRIES) return;
    // 指数退避重连，最长 30s
    const delay = Math.min(1000 * 2 ** _retryCount, 30000);
    _retryCount += 1;
    _reconnectTimer = window.setTimeout(() => {
      if (_refCount > 0) _ensureSource();
    }, delay);
  };
}

function _acquire() {
  _refCount += 1;
  _retryCount = 0;
  _ensureSource();
}

function _release() {
  _refCount = Math.max(0, _refCount - 1);
  if (_refCount === 0) {
    if (_reconnectTimer !== undefined) {
      window.clearTimeout(_reconnectTimer);
      _reconnectTimer = undefined;
    }
    _source?.close();
    _source = null;
    _connected = false;
    _stats = null;
    _retryCount = 0;
    _notify();
  }
}

export function useQueueStream(enabled = true) {
  const [, force] = useReducer((x: number) => x + 1, 0);
  useEffect(() => {
    if (!enabled) return;
    const listener = () => force();
    _listeners.add(listener);
    _acquire();
    return () => {
      _listeners.delete(listener);
      _release();
    };
  }, [enabled]);

  return { stats: _stats, connected: _connected };
}
