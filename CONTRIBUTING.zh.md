# 贡献指南

[English](./CONTRIBUTING.md) | 中文（当前）

感谢你对 ShotFlow 感兴趣。这个项目的目标是沉淀一套**可复用、可协作**的 AIGC 视频工业化流程。任何形式的贡献都有价值。

---

## 你可以做什么

- 报告 Bug 或流程中的坑
- 补充新的 ComfyUI 工作流或改进现有工作流
- 优化提示词，提升角色一致性或视频稳定性
- 改进自动化脚本，提升效率或容错
- 补充后期、音频、调色经验
- 完善文档，让新手更容易上手
- 翻译文档为其他语言

---

## 提交 Issue

在提交 Issue 前，请先搜索是否已有类似问题。如果确定是新问题，请尽量包含：

- 问题描述
- 复现步骤
- 期望结果 vs 实际结果
- 运行环境（GPU、OS、Python 版本、ComfyUI 版本）
- 相关日志或截图

---

## 提交 Pull Request

1. Fork 本仓库
2. 基于 `main` 分支创建新分支：`git checkout -b feature/your-feature-name`
3. 修改内容，保持现有目录结构和命名风格
4. 确保新增脚本可通过 `preflight_check.py` 的基础检查
5. 提交并推送到你的 Fork
6. 提交 Pull Request，说明改动原因和影响范围

---

## 代码与文档风格

- Python 脚本使用 4 空格缩进，遵循 PEP 8
- Shell 脚本使用 `set -euo pipefail` 开头
- 文档使用 Markdown，标题层级清晰
- 新增文件请在 README 的目录结构中补充说明
- 不要提交真实 API 密钥、模型文件、大体积输出文件

---

## 讨论与建议

如果你有一个较大的改动想法，建议先开 Issue 讨论，避免大规模返工。

---

## 每次提交前必查远程仓库状态（强制规范）

> 这是本仓库的强制工作流。**每次**做完一个阶段、准备提交同步前，所有开发者都必须执行下列检查，确认仓库处于健康状态，否则不得推送。

### 检查清单（逐项确认）

1. **Pull Request**：检查 GitHub / GitCode 是否有未处理的 PR 需要合并或评审。
   - GitHub: `https://github.com/MS33834/ShotFlow/pulls`
   - GitCode: `https://gitcode.com/badhope/ShotFlow/pulls`
2. **Issue**：检查是否有未处理的 Issue（bug 报告、功能请求），判断是否影响本次提交。
3. **分支**：检查是否有遗留的功能分支需要清理或合并。
   ```bash
   git fetch --all --prune
   git branch -a   # 应仅保留 main（除非有明确在用的功能分支）
   ```
4. **CI 状态**：确认最近一次提交的 CI 全绿（GitHub Actions）。
   ```bash
   # GitHub CLI 方式
   gh run list --repo MS33834/ShotFlow --limit 3
   # 或网页查看 https://github.com/MS33834/ShotFlow/actions
   ```
   若有红叉，**先修 CI 再推送**，不要在有红叉的基础上叠加新提交。
5. **双仓库一致性**：GitHub 与 GitCode 的 `main` SHA 必须一致。
   ```bash
   git fetch origin gitcode
   LOCAL=$(git rev-parse main)
   GH=$(git rev-parse origin/main)
   GC=$(git rev-parse gitcode/main)
   [ "$LOCAL" = "$GH" ] && [ "$LOCAL" = "$GC" ] && echo "一致" || echo "不一致，需先同步"
   ```
6. **本地测试**：推送前本地测试必须全绿。
   ```bash
   cd backend && DATABASE_URL="sqlite:///test.db" python3 -m pytest tests/ -q
   ```
7. **敏感信息扫描**：确认未暂存 `.env`、`*.db`、`*.key`、`*.pem`、密钥等。
   ```bash
   git diff --cached --name-only | grep -iE '\.env$|\.db$|\.key$|\.pem$|secret|credential' && echo "!!敏感文件!!" || echo "安全"
   ```

### 推送命令模板

```bash
# 提交（用 -c 临时传身份，不写入 config）
git -c user.name="your-name" -c user.email="your@email" commit -m "feat: ..."

# 同步推送双仓库（密钥通过 credential.helper 临时注入，不入仓）
git push origin main
git push gitcode main

# 推送后再次验证三方一致
git ls-remote origin refs/heads/main
git ls-remote gitcode refs/heads/main
```

> **安全提醒**：永远不要把 GitHub Token / GitCode Token 写入 `.git/config`、脚本或任何文件。推送时通过 `git -c credential.helper=...` 临时注入，或在本地用系统凭据管理器。

---

## 开源项目体检（每月或每次发版前执行）

> 这是本项目的"体检流程"。建议按月执行，**每次打 release tag 或宣布里程碑完结前必须执行**。共七项，全部绿灯才能签字。

### 检查清单

1. **开源配套文件齐全**：仓库根目录与 `.github/` 下必须存在下列文件。
   ```bash
   ls LICENSE CONTRIBUTING.md CONTRIBUTING.zh.md CODE_OF_CONDUCT.md \
      CODE_OF_CONDUCT.zh.md SECURITY.md SECURITY.zh.md CHANGELOG.md \
      CITATION.cff TROUBLESHOOTING.md
   ls .github/CODEOWNERS .github/FUNDING.yml .github/dependabot.yml \
      .github/PULL_REQUEST_TEMPLATE.md
   ls .github/ISSUE_TEMPLATE/bug_report.md .github/ISSUE_TEMPLATE/feature_request.md \
      .github/ISSUE_TEMPLATE/config.yml
   ```
   任一缺失，先从最近一次绿灯的提交恢复，再继续。

2. **分支卫生**：`main` 是唯一的长期分支。遗留的功能分支 / dependabot 分支必须合并或删除。
   ```bash
   git fetch --all --prune
   git branch -r            # 预期：origin/main、gitcode/main（仅在用的功能分支除外）
   ```

3. **PR / Issue 队列**：无堆积的未处理 PR 或 Issue，7 天内必须 triage。
   ```bash
   gh pr list --repo MS33834/ShotFlow --state open
   gh issue list --repo MS33834/ShotFlow --state open
   # 也可直接看 GitHub / GitCode 网页
   ```
   - Dependabot PR：补丁/小版本合并；大版本升级已在 `.github/dependabot.yml` 中忽略，如仍出现请关闭并附说明。
   - 30 天未活动的 Issue：关闭或加 `wontfix` / `needs-info` 标签。

4. **CI 全绿**：`main` 分支最近一次提交必须所有 job 通过。
   ```bash
   gh run list --repo MS33834/ShotFlow --branch main --limit 3
   # 全部显示 success；若有 failure，先修复再开展新工作
   ```

5. **双仓库镜像一致**：GitHub、GitCode、本地三方 `main` SHA 必须相同。
   ```bash
   LOCAL=$(git rev-parse main)
   GH=$(git ls-remote origin refs/heads/main | awk '{print $1}')
   GC=$(git ls-remote gitcode refs/heads/main | awk '{print $1}')
   [ "$LOCAL" = "$GH" ] && [ "$LOCAL" = "$GC" ] && echo "三方一致" || echo "漂移，需先同步"
   ```

6. **本地 CI 全套复跑**：发版前必须在本地复现 CI 流水线。
   ```bash
   # 后端
   cd backend && DATABASE_URL="sqlite://" SECRET_KEY="ci-secret-not-for-production-use-32chars-min" \
     REDIS_URL="redis://localhost:6379/0" SIMULATE_MODE="true" pytest tests/ -q
   ruff check . && black --check . && isort --check-only .

   # 自动化脚本 / 文档
   cd .. && ruff check 08_Automation tests && black --check 08_Automation tests && isort --check-only 08_Automation tests
   python 08_Automation/project_health_check.py
   python 08_Automation/check_doc_links.py

   # 前端
   cd frontend && npm run lint && npx tsc --noEmit && npm run test && npm run build
   ```
   预期：后端 179 测试通过，前端 16 测试通过，4179 模块 build 成功，510 文档链接全绿。

7. **敏感文件与密钥扫描**：仓库中无密钥、凭据、大体积二进制。
   ```bash
   git ls-files | grep -iE '\.env$|\.db$|\.key$|\.pem$|secret|credential|token' && echo "!!需复核!!" || echo "干净"
   # 同时确认 .gitignore 覆盖 .env、*.db、node_modules/、__pycache__/、dist/
   ```

### 签字

七项全部绿灯后，在 `CHANGELOG.md` 追加一行：

```
- YYYY-MM-DD：开源项目体检通过 — 分支/PR/CI/镜像/测试全部绿灯。
```

任一项红叉，**立即停止**。先修复再开展新功能开发，绝不在红叉体检上打 release tag。

---
