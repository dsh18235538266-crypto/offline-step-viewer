# step-modeler-mcp

> 对话式治具与适配板生成器 · MCP 插件 · 实时 3D 预览

通过 Codex / Claude / Cursor 等 MCP 客户端**从零生成**机械臂二开场景的简单零件——安装板、法兰、夹爪基座、支架底座——浏览器实时渲染预览。

## 定位说明（重要，先读这段）

本项目定位是 **parametric part generator（参数化零件生成器）**，**不是** CAD 编辑器。

- ✅ **能做的事**：从零"生成"结构简单的零件——安装板、法兰、夹爪基座、带孔底座等，参数由对话指定，结果导出 STEP
- ❌ **不能做的事**：导入一个已有 STEP 模型并"修改"它（加孔/改尺寸）。原因：STEP 格式不保留特征历史，无法做参数化编辑；同时本地几何内核（OpenCASCADE）不具备商业 CAD 的特征树能力
- ❌ **不适合做的事**：复杂装配体、带倒角/圆角/抽壳的复杂特征、曲面建模

如果你需要"对话修改已有模型"，请使用 **Onshape + jarvis-onshape-mcp**（[github.com/ReshefElisha/jarvis-onshape-mcp](https://github.com/ReshefElisha/jarvis-onshape-mcp)）——它驱动云参数化 CAD，支持真正的特征编辑，社区验证成熟（★168）。

## 特性

- 🛠️ **14 个建模工具**：基本体、布尔运算、治具场景模板（安装孔/法兰/轴承座/夹爪基座）
- 🔄 **实时预览**：服务端三角化后 WebSocket 推送 mesh，浏览器自动刷新
- 📂 **离线 STEP 查看器**：`viewer/offline-step-viewer.html` 单文件 HTML，双击即用，无需安装任何环境
- 🔒 **本地运行**：模型不上传任何服务器
- 🤖 **面向机械臂二开**：内置公制安装孔（M3–M20）、双爪基座等常用零件模板

## 快速开始

### 1. 安装

```bash
# 需要 Python ≥ 3.10
pip install step-modeler-mcp
```

或直接用 `uvx`：

```bash
uvx step-modeler-mcp
```

### 2. 配置 MCP 客户端

#### Codex

编辑 `~/.codex/mcp.json`：

```json
{
  "mcpServers": {
    "step-modeler": {
      "command": "uvx",
      "args": ["step-modeler-mcp"],
      "env": {
        "VIEWER_PORT": "8765"
      }
    }
  }
}
```

#### Claude Desktop

编辑 Claude 配置文件（macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`，Windows: `%APPDATA%\Claude\claude_desktop_config.json`）：

```json
{
  "mcpServers": {
    "step-modeler": {
      "command": "uvx",
      "args": ["step-modeler-mcp"],
      "env": {
        "VIEWER_PORT": "8765"
      }
    }
  }
}
```

### 3. 启动 Viewer

`viewer/` 目录下有两个查看器，按需选用：

| 文件 | 用途 | 依赖 |
|---|---|---|
| `viewer/index.html` | 实时预览 MCP 生成的模型（WebSocket 接收 mesh 推送） | 需先启动 MCP server |
| `viewer/offline-step-viewer.html` | 打开**任意已有 STEP 文件**查看（OCCT-WASM 浏览器端解析） | 无，双击即用 |

**实时预览**：启动 MCP server 后（它会自动开 WebSocket 服务），浏览器打开 `viewer/index.html`，显示"WS: 已连接"即就绪。

**离线查看**：直接双击 `viewer/offline-step-viewer.html`，拖入或打开任意 `.step` / `.stp` 文件即可浏览，完全离线运行，适合快速检查从 GrabCAD / Printables 等渠道下载的 STEP 模型。

### 4. 开始对话

在 Codex 中输入：

```
帮我做一个 60×40×10 的安装板，四角打 M6 安装孔
```

Agent 会调用 `create_box` → `create_mounting_hole` × 4 → `push_to_viewer`，浏览器实时显示结果。

## 工具列表

### 基本体

| 工具 | 说明 |
|---|---|
| `create_box(length, width, height, pos?)` | 长方体（mm） |
| `create_cylinder(radius, height, pos?, axis?)` | 圆柱（mm） |

### 布尔运算

| 工具 | 说明 |
|---|---|
| `boolean_subtract(tool_shape_cmd, tool_pos)` | 从当前模型减去基本体（打孔/挖槽） |
| `boolean_union(other_shape_cmd, other_pos)` | 与当前模型合并（加凸台） |

描述格式：`cylinder:r=4,h=20` 或 `box:l=10,w=10,h=10`

### 导出与预览

| 工具 | 说明 |
|---|---|
| `export_step(path?)` | 导出当前模型为 STEP |
| `push_to_viewer(source?)` | 推送当前模型到浏览器实时预览 |

### 场景模板（治具向）

| 工具 | 说明 |
|---|---|
| `create_mounting_hole(m_size, pos?, depth?, through?)` | 公制安装孔（M3–M20 通孔/盲孔） |
| `create_flange(width?, thickness?, hole_pattern?, hole_size?, center_bore?)` | 法兰/转接板 |
| `create_bore(diameter, depth?, pos?, through?)` | 任意直径孔（过线孔/轴承座） |
| `create_gripper_base(jaw_length?, jaw_width?, jaw_height?, gap?, base_thickness?)` | 双爪夹爪基座 |

### 工具函数

| 工具 | 说明 |
|---|---|
| `get_model_info()` | 包围盒 / 体积 / 零件数 |
| `reset_model()` | 清空当前模型 |
| `undo()` / `redo()` | 撤销/重做 |

## 对话示例

### 示例 1：安装板

```
用户：创建一个 80×60×8 的安装板，四角打 M8 安装孔，中心开 Ø25 过线孔

Agent:
  → create_box(80, 60, 8)
  → create_mounting_hole("M8", [35, 25, 0])
  → create_mounting_hole("M8", [-35, 25, 0])
  → create_mounting_hole("M8", [35, -25, 0])
  → create_mounting_hole("M8", [-35, -25, 0])
  → create_bore(25, through=true)
  → push_to_viewer("安装板 + 4×M8 + Ø25 过线孔")
```

### 示例 2：夹爪基座

```
用户：做一个双爪夹爪基座，爪长 50、爪宽 15、爪高 25、间隙 10

Agent:
  → create_gripper_base(jaw_length=50, jaw_width=15, jaw_height=25, gap=10)
  → push_to_viewer("双爪夹爪基座")
```

### 示例 3：法兰转接

```
用户：生成一个 60×8 厚的方形法兰，四角 M6，中心 Ø30 轴承孔

Agent:
  → create_flange(width=60, thickness=8, hole_size="M6", center_bore=30)
  → push_to_viewer("60mm 法兰")
```

## 技术栈

- **建模引擎**：[build123d](https://github.com/gumyr/build123d) — OpenCASCADE 之上的声明式 Python CAD
- **MCP 协议**：[mcp](https://pypi.org/project/mcp/)（v2.x, MCPServer）
- **实时通信**：[websockets](https://websockets.readthedocs.io/)
- **Viewer**：[Three.js](https://threejs.org/) — WebGL 渲染，服务端三角化推送

## 开发

```bash
git clone https://github.com/yourname/step-modeler-mcp.git
cd step-modeler-mcp
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e .
step-modeler-mcp
```

### 项目结构

```
step-modeler-mcp/
├── src/step_modeler/
│   ├── __init__.py
│   ├── server.py        # MCP server 入口 + 工具注册
│   ├── tools.py         # 原子工具实现
│   ├── templates.py     # 场景模板实现
│   ├── state.py         # 模型状态管理 + 历史栈
│   └── viewer_ws.py     # WebSocket 服务（mesh 推送）
├── viewer/
│   ├── index.html               # 实时预览 HTML（WebSocket）
│   └── offline-step-viewer.html # 独立离线 STEP 查看器（单文件，双击即用）
├── tests/
│   └── test_e2e.py      # 端到端测试
├── pyproject.toml
├── README.md
└── LICENSE
```

## 路线图

- [ ] 更多治具模板（电机安装座、相机支架、导轨转接板）
- [ ] 模板参数校验与错误提示（hints）
- [ ] GLB/STL 导出
- [ ] 多零件合并输出（Compound 装配级导出）

## 许可证

MIT
