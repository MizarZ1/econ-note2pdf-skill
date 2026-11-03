# 内容契约 v1

这是运行时字段的权威说明。UTF-8 JSON 保存结构，LaTeX 正文放在项目内独立 `.tex` 文件中。宿主可修改 title、mode、presentation、domains、units、symbols、单元和正文；sources/assets 的处理元数据由脚本维护。禁止把字符串路径写成项目外绝对路径或 `../`。

## project.json

必填：`version: 1`、`title`、`mode`（faithful/study/both）、`domains`（macro/micro/econometrics/math 的列表）、`inputs`、`sources`、`assets`、`units`（按阅读顺序的 ID 列表）、`symbols`。

可选 `preamble` 指向项目内 `.tex` 文件，用于课程公共宏和额外包，不含 documentclass 或 document 环境。跨单元使用的自定义宏必须放在此处，避免依赖前一单元的正文定义；正常编译与隔离诊断共用它。

可选 `presentation` 保存开始任务时的配置，例如：

```json
{
  "presentation": {
    "purpose": "revision",
    "source_style": "accent"
  }
}
```

- `purpose`：revision（复习理解）或 reference（查阅参考）。只指导 study 的内容组织；不是新的 mode，不允许改变 faithful 的编辑权限。缺省为 revision。
- `source_style`：plain（统一排版）、accent（原文深蓝强调）或 box（原文浅色块）。缺省为 plain，兼容已有工程。
- 初始化可使用 `--purpose revision|reference`、`--source-style plain|accent|box`；宿主也可编辑 project.json 中对应字段，不在正文写技术配置。变更后重新 assemble、compile、render 并复核。
- 原文强调只作用于 `origin: source` 块。explanation 和 correction 保持普通正文样式；样式不是来源证明，仍需 refs 和实际对照核查。
- box 对普通来源块使用可跨页色块；含 figure、table 浮动环境或 longtable 长表的块改用强调色，以保留其排版行为。不要为了套入色块删除图表内容或缩小到不可读。

- input：`id`、`name`、`path`（原始副本）、`sha256`。原始副本不覆盖。
- source：`id`、`input_id`、`page`（从 1 起）、`revision`（未准备时 null）、`image`、`image_sha256`（准备后）、`preview`、`size`、`tiles`、`transform`。未准备时后三类可为空。文件顺序即输入建议顺序；`order_confirmed` 由宿主核对后设 true。
- tile：`path`、`box`（在当前全图中的归一化区域）。
- transform：`dpi`、`rotate`（顺时针角度）、`quad`（旋转后图片的 TL,TR,BR,BL 四角，归一化）、`enhance`、`tile_size`、`overlap`；EXIF 方向在这些变换前应用。
- asset：`path`、`source_id`、`revision`、`box`、`sha256`。手绘矢量素材可直接写在块的 LaTeX 中；额外图片也必须登记来源，不能偷偷指向外部文件。
- symbol：`tex`、`meaning`、`scope`，均为非空字符串。列表可为空，非空时在讲义中生成记号表。

source ID 如 `s0001`，unit ID 如 `u001`。所有 ID 使用字母开头的 ASCII 字母、数字、下划线和连字符，避免 TeX label 和文件路径冲突。

## units/<id>.json

```json
{
  "id": "u001",
  "title": "跨期消费选择",
  "source_ids": ["s0001"],
  "coverage": [
    {"id":"c001","source_id":"s0001","revision":"REV","box":[0,0,1,1],"kind":"derivation","disposition":"included","block_ids":["b001"],"reason":""}
  ],
  "blocks": [
    {"id":"b001","kind":"derivation","origin":"source","refs":[{"source_id":"s0001","revision":"REV","box":[0,0,1,1]}],"body":{"faithful":"content/b001.tex","study":"content/b001-study.tex"}}
  ],
  "issues": []
}
```

`REV` 由 prepare 输出取得，不使用此示例字面值。实际覆盖清单按可见内容区域登记，不能仅为通过校验给整页贴一个不真实的记录。

### 内容块

- `kind`：text、equation、derivation、definition、proposition、proof、example、figure、table、summary、heading。
- `origin`：source（原始内容）、explanation（整理补充）、correction（用户或有依据的更正）。source/correction 必须有非空 refs；补充可引用支持它的来源。
- `refs`：每项为 source_id、revision、box。source 必须在该 unit 的 source_ids 内，revision 必须为当前值。
- `body.faithful`：忠实版片段；`body.study`：复习版片段。复习版未提供 study 时可复用 faithful；忠实版不回退使用 study。explanation 必须提供 study，只进入复习版。correction 必须同时提供两个版本，并有学术事项说明修正。
- 块 ID 在整份项目唯一。片段是正文，可含 align、tikzpicture、表格和环境，不能含 documentclass、begin/end document。避免跨块未闭合环境；跨图推导可放进同一块或多个完整环境并引用前式。
- `blocks` 按阅读顺序排列，可交错出现 source 与 explanation。一个块只承担一种来源身份；含原式和补充解释的段落应按身份拆成连续块，避免整段被误标成原文。各块保留完整的 LaTeX 环境。
- 使用 `\label{eq:...}` / `\ref{eq:...}` 关联推导；编译器生成编号，不能在正文猜最终页码。
- 图片必须用字面路径 `\includegraphics{assets/name.png}`，可带可选尺寸参数；不使用宏拼接路径。只有当前版本字面引用的已登记素材进入交付包。图片用相对路径 `assets/name.png`。图片在编译工程中以相同路径出现。

### 覆盖清单

每条包含 id、source_id、revision、box、kind、disposition、block_ids、reason。disposition 为 included、duplicate、excluded、unreadable。

- included 必须关联至少一个原文/修正块，且来源一致。
- duplicate 必须关联实际保留该内容的块，可跨单元；reason 说明重复证据。相似但新增条件不能当重复。
- excluded 必须写 reason，例如非课程内容；不能以“难识别”排除课程推导。
- unreadable 必须写 reason，并关联对应占位块及该块的学术事项。关键内容缺失标 critical；结果始终有 gap。
- 各 source 均需覆盖登记。结构完整仍需宿主看全图判断未登记笔迹。

### 学术事项

issue 必填 `id`、`severity`（note/critical）、`status`（open/resolved）、`block_ids`、`summary`、`detail`。summary/detail 是普通文本，脚本负责 TeX 转义。

- 普通疑点使用 note，默认汇入附录；可选 `appendix: false` 隐藏已解决且不影响读者的事项。
- critical + open 必须有对应块，在正文该块处提示，附录给出细节；标为 partial，不能以 appendix:false 隐藏。
- resolved 的更正记录可留在附录，detail 说明原式、更正依据或用户确认，不能只写“已修复”。
- 技术错误不写入 issues，记录到 logs/state。ID 在同一单元内唯一。

## state.json 与复核

由工具维护：`version:1`、`reviews`（unit ID → digest/note/时间）、`builds`（mode → fingerprint/assembled/compiled/partial/PDF 哈希/渲染/布局复核）、`events`（操作历史）。不要手改状态来跳过检查。

指纹按当前实际输入计算，旧值意味着 stale。来源/片段/素材/模板改变会使相关复核或构建失效。恢复时先 status，修正内容文件，再 validate、assemble、compile、render，实际阅读后 review。

## 诊断与退出

`errors` 表示结构损坏、路径无效、来源过期等，组装必须停止；`gaps` 表示来源未准备、正文未填、覆盖未完成或关键学术事项未决，允许显式部分组装；`warnings` 提供非阻塞诊断。命令返回 0/2/3 分别表示成功/失败/缺失或部分结果；status 的 0 仅代表查询完成。

## 分享工程

交付 source-map 只包含当前模式的块标识、来源区域和必要变换，不含原文件名、其他模式正文路径和内部 issue 详情。附录中展示的事项仍属于 PDF 内容。项目工作目录保留完整记录，不应整体公开上传。

片段及课程宏不允许 input/include、文件读写、csname、catcode、底层 def/let、special 等操作；公共宏使用 newcommand 等普通 LaTeX 定义。此检查会拒绝注释中的禁用命令，不是完整 TeX 安全解析器。自定义包仅使用已安装的普通包名，不使用路径。
