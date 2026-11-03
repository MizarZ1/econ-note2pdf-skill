# 宿主加载与能力约定

核对日期：2026-10-31。通用 skill 不调用模型 API；识别、询问和复核由当前宿主模型执行。脚本只依赖本地 Python、图像/PDF 工具和 TeX。

## 通用能力

宿主需读取 SKILL.md 及按需参考文件、查看本地图片、编辑 UTF-8 JSON/TeX、运行命令、读取退出码与日志、向用户提问。PDF 用脚本渲染成图片后交给宿主视觉能力，不依赖宿主内置 PDF 提取接口。运行长命令时保持进度反馈。

将 `<skill>` 解析为实际 skill 根目录，`<project>` 为独立的可写运行目录。使用带引号的绝对路径调用脚本，工程内保存相对路径。命令返回 3 代表部分或未复核结果，不能仅因 stdout 包含 PDF 路径就宣称完成。

若无视觉能力，报告缺失能力并保留已完成工程；不能把 OCR 或模型服务作为静默替代。若 LaTeX/Poppler 缺失，给出 doctor 诊断，先保留可编辑产物，不宣称 PDF 已生成。

任务开始时的配置询问使用当前宿主可用的交互能力；没有专门询问工具时，用一条简短消息询问使用者。已有选择直接沿用，并保存到项目配置。不要为了询问用途或样式引入新的模型服务或固定审批步骤。

## Codex

仓库入口为 `.agents/skills/advanced-econ-note2pdf`，相对符号链接指向共用 skill。Codex 官方文档确认仓库扫描 `.agents/skills`，支持链接目录；显式调用 `$advanced-econ-note2pdf`。元数据使用 skill 内的 `agents/openai.yaml`，正常保留自动选择行为。[官方加载说明](https://learn.chatgpt.com/docs/build-skills)

本仓库入口只影响此项目；独立安装时将 ZIP 解出的完整 skill 文件夹放入当前宿主支持的个人或项目 skill 目录。使用新会话或刷新技能列表确认发现情况，不修改用户的模型/API 配置。

交付 PDF 的外部阅读器显示正常，不代表 Codex 内置预览也已验证。遇到中文仅在 Codex 中异常时，区分打开已编译 PDF 与打开 TeX 工程后由宿主重新编译：分别记录实际文件、编译日志与渲染结果，检查字体替换和字形问题。不要仅因本地 Poppler 渲染成功就声称宿主预览问题已解决；可在保留可搜索 PDF 的同时提供实际渲染页供阅读，宿主兼容状态按实际检查报告。

## Claude Code

仓库入口为 `.claude/skills/advanced-econ-note2pdf`，指向相同目录。官方文档确认本地项目 skill 与链接目录可被加载；显式调用 `/advanced-econ-note2pdf`。所有指令和资源继续来自同一核心，无需复制一套 Claude 专用流程。[官方加载说明](https://code.claude.com/docs/en/skills)

这里适配的是本地 Claude Code 项目入口，不宣称自动同步到 claude.ai、Cowork 或云端会话。不能把本机目录在云端不可见误判为 skill 本身可远程运行。

## DSH 与其他宿主

DSH 的具体产品与 skill 加载协议尚未确认。提供通用入口：让宿主读取安装目录的 SKILL.md，按上述能力执行同一 CLI。如果宿主不支持标准 skill 发现，显式指定该文件即可，不编造 DSH 配置字段或安装路径。

DSH 专用自动发现和端到端运行标为待验证，不阻塞通用包交付。

## 当前验证边界

| 项目 | 状态 |
| --- | --- |
| 核心资源与相对路径 | 本地检查；打包后离开源码目录可调用 CLI |
| Python/Poppler/XeLaTeX 链路 | 本机合成内容自检通过 |
| Codex | 本机 app-server skills/list 实际发现，scope=repo、enabled=true；文件、命令与图像查看能力已使用；真实转录效果未验收 |
| Claude Code | 已核对官方加载约定并配置入口；未进行模型端到端转录测试 |
| DSH | 通用入口已提供；专用加载待核实 |
| 真实材料和阅读验收 | 开发完成后另行安排 |

Windows 未开启符号链接支持时，使用 ZIP 中的完整目录替代仓库链接。核心脚本不依赖 macOS，HEIC 的 sips 路径只是可选分支；没有验证过的平台不可写成已通过。

## 中文 PDF 兼容性

编译后会为缺失映射的受支持 Adobe CID 字体内嵌 ToUnicode（依赖 TeX 的 adobemapping/kpsewhich）。已用 PDF.js 在不加载外部 CMaps 的条件下复现旧 PDF 中文缺失，并验证内嵌映射后正常。此项属于渲染器兼容测试，不代表每个宿主 UI 已目视验收。

LaTeX 工程的 documentclass 直接放在 main.tex，支持宿主主文件发现。Codex 内建编译器可能与终端编译器不同；内建编译成功不代表已经执行本工具的 PDF 后处理。优先打开 output 中最终 PDF；手动重编译后运行随包的 `python3 pdf_compat.py main.pdf`。
