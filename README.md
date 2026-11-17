# Econ Note2PDF

把经济学板书照片和手写笔记 PDF，整理成适合复习与查阅的中文讲义，同时获得 PDF 和可编辑的 LaTeX 源码。

在支持视觉、文件和命令工具的 agent 中，提供材料和整理要求，让 agent 阅读材料、串联推导、整理图表并编译讲义。下方提供 Codex、Claude 和 DeepSeek Harness 的安装入口；各入口的运行依赖与验证范围见 [宿主说明](advanced-econ-note2pdf/references/hosts.md)。适用于宏观、微观、计量和经济数理课程。

- **沿着知识线索阅读**：围绕问题、条件、推导和结论组织内容，把跨照片的推导衔接起来。
- **保留经济学细节**：关注公式上下标、时点、约束、边界条件，以及相图、回归表和图表注释。
- **用 LaTeX 整理板书**：转录可辨认的文字、公式和表格，重绘能可靠还原的图。其余必要的局部截图随原因放在附录。
- **区分原文与讲解**：原文和原式可用浅彩色框或深蓝强调，补充解释在相邻正文中展开。
- **方便继续修改**：交付可编辑源码、必要图表素材及来源记录，便于核对、补充和重新生成 PDF。

[下载版本](https://github.com/MizarZ1/econ-note2pdf-skill/releases) · [使用说明](#开始使用) · [反馈问题](https://github.com/MizarZ1/econ-note2pdf-skill/issues)

## 安装到 Codex

直接在 Codex 对话中输入：

```text
$skill-installer install https://github.com/MizarZ1/econ-note2pdf-skill/tree/v0.1.1-preview/advanced-econ-note2pdf
```

也可以使用 Node.js/npm，在终端执行：

```sh
npx skills add MizarZ1/econ-note2pdf-skill --skill advanced-econ-note2pdf --agent codex --global
```

上述带版本号的链接安装已发布的 `v0.1.1-preview`。如需 `main` 分支的最新改动，将链接中的 `v0.1.1-preview` 换为 `main`；版本变化见 [CHANGELOG](CHANGELOG.md)。

安装后可在自己的项目中使用，无需克隆仓库。若 Codex 中未出现该 skill，重启后再试。其他宿主的加载方式见 [宿主说明](advanced-econ-note2pdf/references/hosts.md)。

## 安装到 Claude Code

从 [Releases](https://github.com/MizarZ1/econ-note2pdf-skill/releases) 下载完整 skill ZIP，将其中的 `advanced-econ-note2pdf` 文件夹放入以下任一位置：

- 所有项目使用：`~/.claude/skills/advanced-econ-note2pdf/`。
- 仅当前项目使用：`<项目>/.claude/skills/advanced-econ-note2pdf/`。

最终应直接找到该目录下的 `SKILL.md`，不要多套一层同名目录。新会话用 `/skills` 查看，再通过 `/advanced-econ-note2pdf` 调用。克隆本仓库开发时，已有项目入口可复用。个人级同名技能优先，安装后核对实际加载来源。[官方说明](https://code.claude.com/docs/en/skills)

如需将 `main` 分支的最新改动制成完整安装／上传包，在终端执行：

```sh
git clone --branch main https://github.com/MizarZ1/econ-note2pdf-skill.git
cd econ-note2pdf-skill
python3 tools/package_skill.py --output dist/advanced-econ-note2pdf-main.zip
```

生成的 ZIP 与下面的网页／桌面上传、DSH 目录安装共用；GitHub 自动提供的整个仓库源码 ZIP 不是 skill 上传包。

## 上传到 Claude 网页／桌面端

使用同一完整 ZIP。在 Claude 设置中启用文件创建／代码执行，在 `Customize > Skills`（新版可能为 `Plugins` 中的 Skills）选择上传并启用。新建对话、上传板书或 PDF，再明确要求使用 `advanced-econ-note2pdf`；网页端使用已上传文件，不能读取你电脑上的材料路径。[官方上传帮助](https://support.claude.com/en/articles/12512180-using-skills-in-claude)

上传后先让 Claude 运行 `doctor` 并检查 TeX／Poppler 和中文字体，确认能编译、渲染中文 PDF。安装包结构已检查；网页／桌面端的实际上传和完整 PDF 流程尚未验证，不能假设全部依赖已预装。

## 安装到 DeepSeek Harness

将 ZIP 中的完整文件夹放入项目的 `.dsh/skills/`，或个人的 `~/.dsh/skills/`。如果配置了 `DSH_HOME`，个人位置改为 `$DSH_HOME/skills/`。本仓库的 `.agents/skills/` 入口也已通过本机 0.2.1-rc.5 的实际发现检查，无需重复复制。

新会话直接要求“加载 advanced-econ-note2pdf skill 并整理这些材料”。实际模型还须支持图片输入；完整模型转录尚未验证。自定义根、覆盖顺序和排错见 [宿主说明](advanced-econ-note2pdf/references/hosts.md)。

以上目录安装更新时，先保留自定义改动，再整体替换技能目录；卸载只移除该目录，保留课程工程。Claude 账户技能在其管理界面更新或停用。各入口共用同一包，不必维护多套内容规则。

## 开始使用

把材料放在本地文件夹中，在 Codex 中提供路径和你的要求：

```text
$advanced-econ-note2pdf 将 /path/to/板书 整理成中文复习讲义。
请串联公式与推导，原文使用浅彩色框，并交付 PDF 和 LaTeX 源码。
```

也可以把目标改为便于查阅的参考资料，或要求保留原始内容顺序。开始整理时，agent 会确认尚未明确的用途、整理方式和原文样式；已经说明的要求会直接沿用。

### 选择整理方式

| 方式 | 适合的需求 | 内容组织 |
| --- | --- | --- |
| 复习讲义 | 理解课程、梳理推导或查阅公式 | 按知识关系分节，加入必要的连接说明与补充推导 |
| 忠实转录 | 对照原材料、保留课堂记录 | 保留原有内容与顺序，侧重清晰排版 |
| 两者都要 | 同时需要原始记录和整理讲义 | 共用来源记录，分别生成两个版本 |

### 你会得到什么

- **阅读用 PDF**：中文正文、数学公式、图表和章节引用；普通整理说明集中在附录。
- **可编辑 LaTeX 工程**：源码、实际使用的图表素材，以及重编译说明。
- **来源记录**：将内容关联到对应材料，方便回看和核对。

需要调整解释、公式或排版时，可以让 agent 在同一工程中继续修改、重新编译并检查页面。

## 运行环境

需要能够查看图片并运行命令的 agent，以及其实际执行环境中的以下工具（本机或宿主计算环境）：

| 工具 | 用途 |
| --- | --- |
| Python 3.9+、Pillow、pypdf | 处理照片、PDF 页面与项目文件 |
| XeLaTeX、latexmk 和完整中文 TeX 发行版 | 编译中文、公式和图表；模板使用 ctex/Fandol、TikZ/PGFPlots 等包 |
| Poppler | 渲染 PDF 页面，检查排版效果 |

首次使用时，让 agent 先运行 skill 的 `doctor`，同时检查返回的 PDF 编译和预览能力，再按缺失项准备环境。返回码为零仅表示必需 Python 包可用，不能代替中文编译与渲染检查。安装 skill 和准备这些工具是两个步骤；具体依赖与手动命令见 [环境与开发说明](docs/development.md)。

识别和整理使用当前 agent 的模型，无需另配模型 API。图片是否上传云端及相关费用取决于所用宿主的设置。

## 使用建议

尽量提供清晰、按授课顺序排列的材料，并保留公式周围的题设、图表标签和边界条件。对影响结论的模糊内容，agent 会询问你或在对应位置提示，便于核对。

分享讲义或源码前，留意正文和裁切图中是否包含个人信息。数据处理与编译安全说明见 [安全说明](SECURITY.md)。

通过 Skills CLI 安装后，可用 `npx skills update` 更新，或用 `npx skills remove advanced-econ-note2pdf --agent codex --global` 卸载。也可以从 Releases 下载完整 skill ZIP，备份自定义改动后替换原目录。

## 反馈与参与

遇到问题或有改进建议，欢迎 [提交 issue](https://github.com/MizarZ1/econ-note2pdf-skill/issues)，说明使用的宿主、系统、处理的材料类型和预期效果。复现材料请使用合成内容或已获授权并脱敏的片段。

[贡献指南](CONTRIBUTING.md) · [开发与验证](docs/development.md) · [版本记录](CHANGELOG.md) · [MIT 许可证](LICENSE)
