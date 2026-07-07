# ComfyUI 工作流目录

> 本目录存放 AIGC 视频生产所需的核心 ComfyUI 工作流。  
> 以 ShotFlow /《奇点回响》为示例，实际项目请按需修改提示词、参考图与模型路径。

---

## 文件说明

| 文件 | 类型 | 用途 |
|------|------|------|
| `Flux_Character_Consistency.json` | 界面版 | Flux.1 Kontext + IPAdapter 角色一致性出图 |
| `Wan22_Dual_Expert_Video.json` | 界面版 | Wan2.2 I2V 14B 双专家视频生成 |
| `api/Flux_Character_Consistency_api.json` | API 版 | 角色一致性工作流，供脚本批量调用 |
| `api/Wan22_Dual_Expert_Video_api.json` | API 版 | 视频生成工作流，供脚本批量调用 |
| `comfyui_node_connections.md` | 文档 | 节点连接与参数说明 |
| `node_dependencies.md` | 文档 | 所需自定义节点与模型清单 |

---

## 打包发布

完成最终调试后，使用打包脚本生成可分发的工作流 ZIP：

```bash
bash 08_Automation/package_workflows.sh 1.0
```

输出位置：`05_Output/Final/workflows/ShotFlow_Workflows_v1.0.zip`

---

## 使用建议

1. **角色一致性**：先运行 Flux 工作流生成多角度参考图，确认盲测通过后再进入视频生成。
2. **视频生成**：标准镜头用 Wan2.2 High Noise Expert；特写/修复镜头用 Low Noise Expert。
3. **API 批量**：使用 `08_Automation/batch_keyframe_gen.py` 与 `08_Automation/storyboard_to_video.py` 调用 API 版工作流。

---

> 本文件为模板，实际项目请按真实工作流文件调整。
