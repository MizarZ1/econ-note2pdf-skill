# 宿主安装与运行

核对日期：2026-11-17。所有入口共用同一 skill；图片理解与复核使用宿主模型，Python 不调用模型 API。各入口的实际验证范围见文末。

## 共用安装包与运行目录

完整 ZIP 只有一个 `advanced-econ-note2pdf/` 根目录，其中包含 `SKILL.md`、`scripts/`、`references/`、`assets/` 和依赖说明。安装整个目录，不单独复制 SKILL.md。Windows 或不支持符号链接的环境使用完整目录。

本地新安装：把 ZIP 解压到所选的 skills 根，使最终路径为 `<skills-root>/advanced-econ-note2pdf/SKILL.md`。同名目录已存在时先备份自定义改动，再整体替换，避免新旧文件混用；卸载只移除该技能目录，保留运行工程。网页／桌面上传使用原 ZIP，不先解包重压。

执行者从实际加载的 SKILL.md 定位资源；命令中给含空格的路径加引号。输入文件、安装目录和可写运行工程是三个不同位置。网页执行环境应使用已上传文件的实际路径，不能引用使用者电脑上的路径。工程内继续使用相对路径。

开始处理材料前运行：

```sh
python3 "<skill>/scripts/econ_note.py" doctor
```

`required_missing` 检查 Python 包；完整 PDF 任务还须检查 `capabilities.images`、`pdf_intake`（PDF 输入时）、`pdf_compile` 和 `pdf_preview`。doctor 返回 0 不代表 TeX 工具、中文字体或宿主视觉均可用。依赖清单在包内 `requirements.txt`；编译还需 XeLaTeX、latexmk、ctex/Fandol 等模板包，渲染需 Poppler。用一次最小中文编译与渲染确认实际环境。

宿主须能查看全图与高清局部、读写 JSON/TeX、运行命令并取得退出码。没有图像输入能力时不能声称完成转录；保留已完成产物并说明缺失能力，不静默切换 OCR 或外部模型服务。长命令保持进度反馈，退出码 3 代表部分／未复核结果。

## Claude Code

| 范围 | 完整目录位置 |
| --- | --- |
| 个人级 | `~/.claude/skills/advanced-econ-note2pdf/` |
| 项目级 | `<project>/.claude/skills/advanced-econ-note2pdf/` |

本仓库的 `.claude/skills/advanced-econ-note2pdf` 是指向核心目录的链接。独立安装用完整目录即可。新会话通过 `/skills` 检查发现，再用 `/advanced-econ-note2pdf` 或直接提出整理任务。若未发现，检查目录层级、元数据及同名遮蔽；个人级同名 skill 优先于项目级。资源路径以实际加载版本为准。

通过 claude.ai 账户登录并满足同步条件时，Claude Code 可下载同步账户中已启用的技能；API key 或代理会话不应假定可同步。这不表示本地目录会自动上传到账户。不要同时维护来源不明的同名副本，安装后核对加载位置。精确同步条件以当前版本为准。[官方目录与同步说明](https://code.claude.com/docs/en/skills)

## Claude 网页／桌面端 Skills 上传

这里指 Claude 聊天中的账户技能。按当前界面执行：

1. 在设置中启用文件创建／代码执行能力（可能显示为 `Code execution and file creation` 或 `Create and edit files`），并确认账户或组织允许自定义 Skills。
2. 打开 `Customize > Skills`；新版界面可能改为 `Plugins`，进入其中的 Skills 列表。
3. 选择创建／上传 skill，上传完整 ZIP 并启用。现有包采用同名根目录，name 与 description 符合已核对的上传长度要求。
4. 新建对话，上传材料并明确使用 `advanced-econ-note2pdf`。先检查依赖，再运行小型中文 PDF 流程并打开输出。桌面端需在其实际使用界面验证，不能用终端结果代替。

[上传帮助](https://support.claude.com/en/articles/12512180-using-skills-in-claude) · [自定义包要求](https://support.claude.com/en/articles/12512198-how-to-create-custom-skills) · [Plugins 入口调整](https://support.claude.com/en/articles/17740565-manage-plugins-skills-and-connectors-from-one-plugins-page)

网页文件执行发生在宿主计算环境；网络和依赖安装取决于账户设置，不能假设本机的 TeX 或字体可用，也不能将 API 环境限制直接套用到网页端。官方未保证本工具全部 TeX 依赖预装，须实际检查。缺依赖时按宿主允许的方式准备环境；无法解决时明确受影响的 PDF 交付步骤，不把上传成功写成端到端通过。[文件执行说明](https://support.claude.com/en/articles/12111783-create-and-edit-files-with-claude)

更新时在账户技能界面替换／重新上传完整包并重新检查启用状态；停用或卸载在该界面完成。账户安装与本地安装分别管理，不以一侧移除推断另一侧状态。

## DeepSeek Harness

已核对 0.2.1-rc.5 的实际 filesystem provider 与 skill registry。首选安装位置：

| 范围 | 位置 |
| --- | --- |
| 项目级 | `<project-root>/.dsh/skills/advanced-econ-note2pdf/` |
| 个人级 | `<dshHome>/skills/advanced-econ-note2pdf/`，默认 `~/.dsh/skills/advanced-econ-note2pdf/` |
| 共用项目入口 | `<project-root>/.agents/skills/advanced-econ-note2pdf/`；本仓库现有入口已被识别 |

项目根取最近包含 `.git` 的祖先，无则取当前工作目录。发现优先级为项目 `.dsh`、项目 `.agents`、`customSkillDirs`、用户 dshHome、用户 agentsHome、bundled；同名条目取优先项。dshHome 为显式配置优先，其次 `DSH_HOME`，最后 `~/.dsh`；agentsHome 同理使用 `DSH_AGENTS_HOME` 和 `~/.agents`。自定义目录通过当前 provider 的 `customSkillDirs` 配置；`includeDefaultRoots:false` 会关闭默认项目／用户根，需检查实际启用的根。

新会话直接要求“加载 advanced-econ-note2pdf skill 并整理这些材料”，检查技能目录或加载结果中的实际来源。没有发现时先核对项目根、目录层级、同名遮蔽与 provider 配置；不要猜测未提供的 CLI 子命令。安装和更新沿用完整目录方式，无需为本仓库重复建立 `.dsh` 链接。[官方 Skills 参考](https://deepseek-harness.github.io/deepseek-harness/en/reference/subsystems/skills)

filesystem provider 能发现技能，不等于所选模型能理解图片。`read_image` 要求当前模型 route 声明 image 输入；首次运行必须核对实际模型和图像工具是否可用，并试读材料。安装说明不替使用者修改模型或 API 配置。

## Codex 与通用入口

本仓库 `.agents/skills/advanced-econ-note2pdf` 指向同一核心，Codex 可自动选择或用 `$advanced-econ-note2pdf` 显式调用。个人安装方法见仓库 README。其他宿主须提供上述视觉、文件与命令能力，可让其读取实际安装目录的 SKILL.md 执行；未核对的发现机制不写成已支持。

## 中文 PDF 预览与重编译

编译会为受支持 Adobe CID 字体内嵌缺失的 ToUnicode 映射，避免预览器依赖外部 CMap。检查最终日志的 Missing character，并实际查看中文页。外部阅读器正常不代表宿主预览通过。

优先打开最终 PDF。若宿主自行重编译 TeX，记录实际主文件和编译器，按工程 DELIVERY.md 执行随包的 `python3 pdf_compat.py main.pdf`。LaTeX 主文件为 main.tex；不要只根据本地 Poppler 或其他渲染器结果声称宿主 UI 问题已解决。

## 本轮验证边界

| 层次 | 2026-11-17 已核对结果 |
| --- | --- |
| 共用包与独立运行 | 单根完整 ZIP；临时 skills 目录、含空格路径、无关 cwd 下的 CLI／模板／中文编译渲染及未复核导出通过 |
| Claude Code | 2.1.322 隔离项目 catalog 发现、Skill 调用和实际 SKILL.md／脚本读取通过；沿用现有默认模型，完整转录待验证 |
| Claude 网页／桌面 | 上传结构已检查；网页停在登录前安全验证，未完成上传或宿主内编译；桌面未验证 |
| DeepSeek Harness | 0.2.1-rc.5 实际 provider／registry 已发现仓库入口及隔离项目、用户、自定义目录，并载入正文与资源；模型图像理解及端到端待验证 |
| Codex 与真实材料 | 既有入口与工程检查保留；本轮合成检查不代表真实板书识别或完整课程验收 |
