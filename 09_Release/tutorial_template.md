# 技术社区教程模板

> 项目：ShotFlow /《奇点回响》（示例）  
> 作者：项目技术团队  
> 发布平台：知乎 / 微信公众号 / 博客 / B站专栏（任选）  
> 本模板为示例框架，实际项目请按真实技术栈与经验填充。

---

## 标题（示例）

《如何用 AIGC 工业化流程做出电影感科幻短片：从角色一致性到 4K 母版输出》

---

## 一、项目背景

- 为什么要做这个项目？
- 当前 AIGC 视频生产的痛点（角色不一致、闪烁、崩坏）
- 本项目希望验证/解决什么问题？

---

## 二、技术栈概览

| 层级 | 工具/模型 | 用途 |
|------|-----------|------|
| 剧本与角色 | DeepSeek / Claude | 剧本、角色圣经 |
| 角色一致性 | Flux.1 Kontext + IPAdapter | 角色参考图 |
| 视频生成 | Wan2.2 I2V 14B | 标准镜头 |
| 复杂镜头 | 可灵 2.5 Turbo | 首尾帧约束 |
| 剪辑/调色 | DaVinci Resolve | 精剪与调色 |
| 音频 | ElevenLabs + Suno/Udio | 配音与配乐 |
| 画质增强 | Topaz Video AI | 4K 超分 |

---

## 三、关键流程拆解

### 3.1 角色一致性

- 如何构建角色圣经？
- IPAdapter 权重与参考图数量
- 盲测方法与评分标准

### 3.2 分镜到视频

- 分镜表如何设计？
- 关键帧生成与提示词管理
- Wan2.2 High/Low Noise 双专家选择策略

### 3.3 复杂镜头处理

- 什么情况下调用可灵 API？
- 首尾帧约束与 denoise 调优

### 3.4 后期合成

- 粗剪 → 锁定剪辑 → 调色 → 混音的流程
- Topaz 超分参数
- 瑕疵修复经验

---

## 四、失败案例与解决方案

- 案例 1：角色服装颜色偏移 → 如何修复
- 案例 2：手部崩坏 → 如何避免
- 案例 3：视频闪烁 → 参数调整

（详见 [`06_Research/failure_cases.md`](../06_Research/failure_cases.md)）

---

## 五、资源下载

- GitHub 仓库：https://github.com/MS33834/ShotFlow
- GitCode 仓库：https://gitcode.com/badhope/ShotFlow
- ComfyUI 工作流打包：`05_Output/Final/workflows/ShotFlow_Workflows_v1.0.zip`
- SOP 手册：`04_SOP/sop_shotflow.md`

---

## 六、总结与展望

- 本次验证的核心结论
- 哪些流程已可复用？
- 下一步优化方向

---

> 本文件为模板，实际项目请按真实经验与数据改写。
