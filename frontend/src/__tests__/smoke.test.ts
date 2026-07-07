import { describe, it, expect } from "vitest";

describe("smoke test", () => {
  it("vitest is wired up correctly", () => {
    expect(1 + 1).toBe(2);
  });

  it("jsdom DOM environment is available", () => {
    const div = document.createElement("div");
    div.textContent = "hello";
    expect(div.textContent).toBe("hello");
  });
});
