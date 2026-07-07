# 安全策略

[English](./SECURITY.md) | 中文（当前）

感谢你帮助保持 ShotFlow 的安全。我们非常重视任何安全漏洞的报告。

---

## 报告漏洞

如果你发现安全漏洞，**请不要公开开 Issue**。请通过以下方式私下报告：

- 在 GitHub 仓库创建 **Security Advisory**（私有报告）：
  `https://github.com/MS33834/ShotFlow/security/advisories/new`

  这条渠道是私密的，只有仓库维护者可见。请在标题前加 `[SECURITY]`。

请在报告中包含：

- 漏洞描述与影响范围
- 复现步骤（最小可复现示例最佳）
- 受影响的版本 / commit
- 你建议的修复方向（可选）

我们会在 **3 个工作日内**确认收到报告，并在评估后尽快给出修复计划与时间表。

---

## 支持的版本

ShotFlow 仍在积极开发中，仅对 `main` 分支的最新提交提供安全修复。

| 版本 | 支持状态 |
|------|----------|
| `main` (最新) | 支持 |
| 历史发布版 | 不支持 |

---

## 安全使用建议

本仓库涉及多个外部 API 与本地推理服务，部署时请注意：

1. **密钥管理**：所有 API 密钥（可灵、ElevenLabs、Suno、ComfyUI）通过 `.env` 注入，`.env` 已被 `.gitignore` 忽略，**切勿提交**。
2. **JWT 密钥**：生产部署必须用 `openssl rand -hex 32` 生成 `SECRET_KEY`，后端在 `SECRET_KEY` 仍为默认值时会拒绝启动。
3. **ComfyUI 暴露**：ComfyUI 默认无鉴权，不要将其直接暴露到公网；建议仅监听 `127.0.0.1` 或置于反代 + 鉴权之后。
4. **双仓库令牌**：同步 GitHub / GitCode 用的 Token 请通过系统凭据管理器或 `git -c credential.helper` 临时注入，**绝不写入 `.git/config`、脚本或任何文件**。

---

## 已知安全相关设计

- 认证：JWT（`python-jose` 3.4.0+，修复 CVE-2024-33663/33664/33665）
- 密码哈希：`bcrypt`（避免 passlib 1.7.x 与 bcrypt 4.x 兼容问题）
- RBAC：队列操作按角色（admin / director / algo_engineer / video_operator / ops / pm）鉴权（见 `backend/app/api/deps.py`）
