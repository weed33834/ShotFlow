# Pull Request 模板

## 变更说明

<!-- 简要描述本次 PR 做了什么，以及为什么 -->

## 变更类型

- [ ] 新功能（feat）
- [ ] Bug 修复（fix）
- [ ] 重构（refactor）
- [ ] 文档（docs）
- [ ] 测试（test）
- [ ] CI/构建（chore）
- [ ] 依赖更新（deps）

## 测试

- [ ] 后端测试通过（`cd backend && python -m pytest tests/ -q`）
- [ ] 前端类型检查通过（`cd frontend && npx tsc --noEmit`）
- [ ] 手动验证功能正常

## 检查清单

- [ ] 代码风格一致（中文注释说明"为什么"）
- [ ] 无硬编码密钥/Token
- [ ] SIMULATE_MODE 下全链路可跑通
- [ ] .env.example 已更新（如新增配置项）
