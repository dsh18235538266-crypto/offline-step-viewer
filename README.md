# offline-step-viewer

> 通用 STEP 离线 3D 查看器 · 单文件 HTML · 双击即用 · 无需安装任何 CAD 软件

想看一个 STEP 模型，但电脑上没装 SolidWorks / AutoCAD / FreeCAD？**下载本仓库里的一个 HTML 文件就够了。**

## 使用方法（3 步）

1. **下载** [`offline-step-viewer.html`](offline-step-viewer.html)（约 12MB）
   - 点击文件名 → 右上角 **Download** 按钮保存；或 `git clone` 本仓库
2. **双击**文件，用任意现代浏览器打开（Chrome / Edge / Firefox）
3. **拖入** `.step` / `.stp` 文件（或点击"打开文件"按钮），即可旋转、缩放、平移浏览 3D 模型

就这么简单——零安装、零配置、零联网。

## 特性

- 📂 **单文件交付**：几何内核（OCCT-WASM）+ 渲染引擎（Three.js）全部内嵌在这一个 HTML 里
- 🔒 **完全离线**：模型数据不出本机，适合涉密或内部图纸的快速检查
- 🖱️ **标准查看操作**：鼠标左键旋转、滚轮缩放、右键平移
- 🌐 **无浏览器插件**：纯 WebGL 渲染，不需要装任何扩展

## 适用场景

- 客户/供应商发来 STEP 图纸，**先快速过目再决定**要不要导入 CAD 深入处理
- 检查从 [GrabCAD](https://grabcad.com) / [Printables](https://www.printables.com) / MakerWorld 等渠道下载的 3D 打印模型
- 临时电脑、车间电脑等**没有 CAD 授权**的机器上看图
- 机械臂二开选型：核对外形尺寸、安装孔位、接口形式

## 常见问题

**Q: 为什么文件有 12MB？**
A: OpenCASCADE 几何内核的 WebAssembly 版本以 base64 形式内嵌在文件里——这正是它能"零安装解析 STEP"的原因。

**Q: 会把我的模型上传到服务器吗？**
A: 不会。解析和渲染全部在浏览器本地完成，断网也能用。

**Q: 能编辑/修改模型吗？**
A: 不能，这是一个纯查看器。如需修改请使用 CAD 软件（FreeCAD 开源免费）。

## 技术原理（给感兴趣的工程师）

```
.step 文件 ──► occt-import-js (OCCT-WASM) ──► 网格化 (mesh) ──► Three.js WebGL 渲染
                浏览器内本地解析                  内存中转换           GPU 实时渲染
```

- **几何内核**：OpenCASCADE 的 WASM 编译版（occt-import-js），在浏览器里解析 STEP 实体数据
- **渲染**：Three.js，把解析出的网格交给 WebGL 实时绘制

## License

MIT
