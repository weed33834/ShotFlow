#!/usr/bin/env bash
# -*- coding: utf-8 -*-
# ShotFlow — ComfyUI 工作流打包脚本
# 用法: bash 08_Automation/package_workflows.sh [版本号]
#
# 功能:
#   1. 收集 03_Workflows/ 下的 JSON 工作流与节点依赖说明
#   2. 生成打包清单 README
#   3. 输出 ZIP 到 05_Output/Final/workflows/ShotFlow_Workflows_v{版本}.zip

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
WORKFLOWS_DIR="$PROJECT_ROOT/03_Workflows"
OUTPUT_DIR="$PROJECT_ROOT/05_Output/Final/workflows"
VERSION="${1:-0.2.0}"
ZIP_NAME="ShotFlow_Workflows_v${VERSION}.zip"
TMP_DIR="$(mktemp -d)"

mkdir -p "$OUTPUT_DIR"

echo "========================================="
echo "  ComfyUI 工作流打包"
echo "  版本: v$VERSION"
echo "========================================="
echo ""

# 1. 复制工作流文件
echo "[1/4] 复制工作流文件..."
mkdir -p "$TMP_DIR/workflows"
cp -r "$WORKFLOWS_DIR"/*.json "$TMP_DIR/workflows/" 2>/dev/null || true
cp -r "$WORKFLOWS_DIR/api" "$TMP_DIR/workflows/" 2>/dev/null || true

# 2. 复制节点依赖说明
echo "[2/4] 复制节点依赖说明..."
cp "$WORKFLOWS_DIR/node_dependencies.md" "$TMP_DIR/workflows/" 2>/dev/null || true
cp "$WORKFLOWS_DIR/comfyui_node_connections.md" "$TMP_DIR/workflows/" 2>/dev/null || true
cp "$WORKFLOWS_DIR/README.md" "$TMP_DIR/workflows/" 2>/dev/null || true

# 3. 生成打包清单
echo "[3/4] 生成打包清单..."
cat > "$TMP_DIR/workflows/README_Packaged_Workflows.md" << EOF
# ShotFlow — ComfyUI 工作流打包清单

> 版本：v$VERSION  
> 打包日期：$(date +%Y-%m-%d)  
> 本打包文件为模板示例，实际项目请替换为你的工作流 JSON。

---

## 包含内容

| 文件 | 说明 |
|------|------|
| Flux_Character_Consistency.json | Flux.1 Kontext + IPAdapter 角色一致性工作流（界面版） |
| Wan22_Dual_Expert_Video.json | Wan2.2 I2V 双专家视频生成工作流（界面版） |
| api/Flux_Character_Consistency_api.json | 角色一致性工作流（API 格式） |
| api/Wan22_Dual_Expert_Video_api.json | 视频生成工作流（API 格式） |
| comfyui_node_connections.md | 节点连接与参数说明 |
| node_dependencies.md | 所需自定义节点与模型列表 |

---

## 快速使用

1. 在 ComfyUI 中点击 **Load** 加载界面版 JSON。
2. 或在 API 环境中使用 \`api/\` 下的 JSON 调用 ComfyUI API。
3. 根据你的项目替换提示词、参考图与模型路径。

---

## 依赖环境

- ComfyUI 最新版
- Python 3.10+
- CUDA 12.x
- 见 \`node_dependencies.md\` 获取完整节点列表

---

> 打包脚本：\`08_Automation/package_workflows.sh\`
EOF

# 4. 打包 ZIP
echo "[4/4] 打包 ZIP..."
cd "$TMP_DIR"
zip -r "$OUTPUT_DIR/$ZIP_NAME" workflows/
cd - > /dev/null

# 清理临时目录
rm -rf "$TMP_DIR"

echo ""
echo "========================================="
echo "  打包完成"
echo "  输出: $OUTPUT_DIR/$ZIP_NAME"
echo "========================================="
