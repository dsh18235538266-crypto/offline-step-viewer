# step-modeler-mcp

> 对话式 STEP 模型创建与编辑 · MCP 插件 · 实时 3D 预览

通过 Codex / Claude / Cursor 等 MCP 客户端对话建模，模型在浏览器中实时渲染。

## 特性

- 🛠️ **14 个建模工具**：基本体、布尔运算、安装孔/法兰/轴承座等机械臂二开场景模板
- 🔄 **实时预览**：通过 WebSocket 推送，浏览器自动刷新模型
- 🔒 **本地运行**：STEP 解析与渲染全部在浏览器本地完成，模型不上传
- 🤖 **机械臂二开定制**：内置夹爪基座模板、标准公制安装孔、法兰等

## 快速开始

### 1. 安装

```bash
# 需要 Python ≥ 3.10
pip install step-modeler-mcp
```

或者直接用 `uvx`（无需安装，自动拉取）：

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

编辑 Claude 配置文件（macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`）：

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

启动 MCP server 后，在浏览器中打开 viewer：

```bash
# 方式 1：从安装目录打开
python -m step_modeler.viewer

# 方式 2：直接打开 HTML 文件
# 用浏览器打开 viewer/index.html
```

浏览器会自动连接 WebSocket（`ws://127.0.0.1:8765`），显示"WS: 已连接"。

### 4. 开始对话建模

在 Codex 中输入：

```
帮我创建一个 60×40×10 的安装板，四角打 M6 安装孔
```

Agent 会调用 `create_box` → `create_mounting_hole` × 4 → `push_to_viewer`，浏览器实时显示结果。

## 工具列表

### 基本体

| 工具 | 说明 |
|---|---|
| `create_box(length, width, height, pos?)` | 创建长方体 |
| `create_cylinder(radius, height, pos?, axis?)` | 创建圆柱 |

### 布尔运算

| 工具 | 说明 |
|---|---|
| `boolean_subtract(tool_shape_cmd, tool_pos)` | 从当前模型减去一个基本体（打孔/挖槽） |
| `boolean_union(other_shape_cmd, other_pos)` | 与当前模型合并（加凸台/法兰） |

工具描述格式：
- `cylinder:r=4,h=20` → 半径 4、高 20 的圆柱
- `box:l=10,w=10,h=10` → 10×10×10 的长方体

### 导出与预览

| 工具 | 说明 |
|---|---|
| `export_step(path?)` | 导出当前模型为 STEP 文件 |
| `push_to_viewer(source?)` | 推送当前模型到浏览器实时预览 |

### 场景模板（机械臂二开定制）

| 工具 | 说明 |
|---|---|
| `create_mounting_hole(m_size, pos?, depth?, through?)` | 标准公制安装孔（M3–M20） |
| `create_flange(width?, thickness?, hole_pattern?, hole_size?, center_bore?)` | 法兰盘（4 角孔模板） |
| `create_bore(diameter, depth?, pos?, through?)` | 任意直径孔（轴承座/过线孔） |
| `create_gripper_base(jaw_length?, jaw_width?, jaw_height?, gap?, base_thickness?)` | 两爪夹爪基座 |

### 工具函数

| 工具 | 说明 |
|---|---|
| `get_model_info()` | 查询当前模型包围盒、体积、零件数 |
| `reset_model()` | 清空内存模型 |
| `undo()` / `redo()` | 撤销/重做 |

## 对话示例

### 示例 1：创建安装板

```
用户：创建一个 80×60×8 的铝合金安装板，四角打 M8 安装孔，中心开 Ø25 过线孔

Agent:
  → create_box(80, 60, 8)
  → create_mounting_hole("M8", [35, 25, 0])
  → create_mounting_hole("M8", [-35, 25, 0])
  → create_mounting_hole("M8", [35, -25, 0])
  → create_mounting_hole("M8", [-35, -25, 0])
  → create_bore(25, through=true)
  → push_to_viewer("安装板 + 4×M8 + Ø25 过线孔")
```

### 示例 2：生成夹爪基座

```
用户：生成一个双爪夹爪基座，爪长 50、爪宽 15、爪高 25、间隙 10

Agent:
  → create_gripper_base(jaw_length=50, jaw_width=15, jaw_height=25, gap=10)
  → push_to_viewer("双爪夹爪基座")
```

### 示例 3：在已有模型上打孔

```
用户：在当前模型 (30, 0, 0) 位置打一个 M10 的安装孔

Agent:
  → create_mounting_hole("M10", [30, 0, 0])
  → push_to_viewer("M10 安装孔")
```

## 技术栈

- **建模引擎**：[build123d](https://github.com/gumyr/build123d) — 基于 OpenCASCADE 的声明式 Python CAD 库
- **MCP 协议**：[mcp](https://pypi.org/project/mcp/) — Model Context Protocol Python SDK
- **Viewer**：[Three.js](https://threejs.org/) + [occt-import-js](https://github.com/kovacsv/occt-import-js) — 浏览器端 STEP 解析与 WebGL 渲染
- **实时通信**：[websockets](https://websockets.readthedocs.io/) — Python WebSocket 服务器

## 开发

```bash
# 克隆仓库
git clone https://github.com/yourname/step-modeler-mcp.git
cd step-modeler-mcp

# 创建虚拟环境
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# .venv\Scripts\activate    # Windows

# 安装依赖（可编辑模式）
pip install -e .

# 运行
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
│   └── viewer_ws.py     # WebSocket 服务
├── viewer/
│   └── index.html       # 实时预览 HTML
├── pyproject.toml
├── README.md
└── LICENSE
```

## 路线图

- [ ] 装配树支持（多零件层级显示）
- [ ] 测量工具（点对点距离、孔距）
- [ ] 爆炸视图
- [ ] 参数化模板系统
- [ ] GLB 导出
- [ ] 草图绘制（2D 轮廓拉伸）

## 许可证

MIT
