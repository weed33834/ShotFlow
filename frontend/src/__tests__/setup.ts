// 测试环境 setup — 为 jsdom 补足 antd / react-router 需要的全局对象
import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import { afterEach } from "vitest";

// 每个测试后自动清理 DOM，避免上一个用例残留的元素干扰下一个
afterEach(() => {
  cleanup();
});

// antd ResponsiveObserver 依赖 window.matchMedia，jsdom 不提供
if (!window.matchMedia) {
  Object.defineProperty(window, "matchMedia", {
    writable: true,
    value: (query: string) => ({
      matches: false,
      media: query,
      onchange: null,
      addListener: () => {},
      removeListener: () => {},
      addEventListener: () => {},
      removeEventListener: () => {},
      dispatchEvent: () => false,
    }),
  });
}

// antd message / Spin 等组件依赖 ResizeObserver
if (!global.ResizeObserver) {
  global.ResizeObserver = class {
    observe() {}
    unobserve() {}
    disconnect() {}
  };
}
