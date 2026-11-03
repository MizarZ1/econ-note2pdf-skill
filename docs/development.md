# 开发与自检

最低 Python 3.9。skill 的 `requirements.txt` 只声明 Pillow、pypdf；PDF 渲染另需本地 Poppler（`pdftoppm`），PDF 编译使用 XeLaTeX/latexmk。HEIC 可使用 `pillow-heif` 或 macOS `sips`；脚本不自动安装依赖。TeX 需包含 ctex/Fandol、AMS、TikZ/PGFPlots、booktabs、longtable、tabularx、caption、hyperref、bookmark、fancyhdr、tcolorbox 与 adobemapping 等包。

```sh
python3 advanced-econ-note2pdf/scripts/econ_note.py doctor
python3 -m compileall -q advanced-econ-note2pdf/scripts
python3 tools/dev_check.py
python3 tools/dev_check.py --with-latex
python3 tools/pdf_compat_check.py
python3 tools/presentation_check.py
python3 tools/check_repo.py
python3 tools/package_skill.py
```

`dev_check.py` 生成矩形与短文本的合成图片/PDF，检查文件导入、页面展开、分块、来源版本、裁切冲突与复核失效。它不调用模型、不含真实用户材料，不用于评价笔迹识别或讲义阅读质量。默认临时目录自动清理；`--keep .local/p3-check` 可保留产物定位问题。

## 已实现命令

```sh
python3 advanced-econ-note2pdf/scripts/econ_note.py init --project work/course --inputs /path/to/photo.jpg /path/to/notes.pdf --title '高级经济学' --mode both --domains macro
python3 advanced-econ-note2pdf/scripts/econ_note.py prepare --project work/course
python3 advanced-econ-note2pdf/scripts/econ_note.py crop --project work/course --source s0001 --box 0.1 0.2 0.8 0.9 --name phase-diagram
python3 advanced-econ-note2pdf/scripts/econ_note.py validate --project work/course
python3 advanced-econ-note2pdf/scripts/econ_note.py status --project work/course
```

初始化只生成待填写的逻辑单元；宿主查看 prepared 全图/分块后，根据 [内容契约](../advanced-econ-note2pdf/references/content-model.md) 写入 units 与 content。只有实际对照材料后才调用 `review --kind content --unit u001 --note '检查对象和结果'`。

多张照片组成一个单元时，可用 `unit` 新建单元，然后修改 `project.json.units` 的阅读顺序，移除已被替代的空单元 ID；磁盘上的旧文件保留。校验仍要求所有来源有覆盖记录，不能通过移除单元掩盖遗漏。

所有项目写操作使用锁；进程异常退出后先确认 `.econ-note.lock` 中 PID 已不再运行，再删除失效锁。每次更新 project.json 会在 history 保存旧版本；旧图像 revision 不覆盖。内容正文由宿主编辑，脚本不会重写。

## LaTeX 与交付

完成结构和内容填写后执行 `assemble --mode study`、`compile --mode study`、`render --mode study`，每条均带 `--project work/course`。查看渲染页后用 `review --kind layout --mode study --note '实际检查内容'`，完成各单元 content review 后执行 `package --mode study`。both 模式另对 faithful 执行同一流程。

正文片段只写 body。课程共用宏用 project.json 可选 `preamble` 指向项目内 `.tex`；正常编译和单元诊断均加载此文件，公共宏不要定义在另一个单元正文中。生成后的 build 文件不直接修改；修改原片段并重新 assemble，系统会保留旧工程。

编译失败可看返回的 `attempt.log` 与文件/行号；最多作 3 次有依据修复。仍失败时 `compile --isolate-failures` 对单元诊断并保留失败源码，成功的部分 PDF 返回 3；公共模板故障不能靠排除整份内容解决。未解析引用或缺字警告使产物标为 partial，普通版式警告需在页面复核时判断。

普通学术事项汇入 appendix，critical/open 在相邻正文作短提示。compile 日志只留 logs。`package --allow-unreviewed` 可提前导出，但返回 3 并在 delivery.json 标注 unreviewed；默认 package 要求当前内容与页面均已复核。ZIP 包含独立 LaTeX、素材、PDF 与来源记录，不包含完整原件、预览或工具日志。

合成 LaTeX 自检包含中文、跨期公式、定理证明、PGFPlots、来源图片、回归表、矩阵、跨章节引用和普通附录事项；额外检查旧 PDF 不误判、过期构建拒绝、失败单元隔离及修复恢复。该输入是工程夹具，不是课堂转录或验收样本。

## 开发记录

- P1：文档相对链接、JSON 示例解析与 diff 检查通过。
- P2：skill frontmatter/命名检查及参考链接检查通过。
- P3：compileall、doctor 与 dev_check.py 通过；本机 Pillow 11.3.0、pypdf 6.10.2、Poppler 可用。合成输入覆盖图片 + 2 页 PDF、幂等准备、裁切冲突、复核失效、过期来源和路径边界。真实材料测试、模型效果测试与用户验收仍未开展。
- P4：`dev_check.py --with-latex` 通过，检查了编译/渲染/ZIP、未复核打包限制、故意错误的隔离与恢复。修正了将首遍引用警告误当最终警告的问题；3 页合成讲义渲染已人工查看，未见截断与重叠。该结果不代表真实板书识别质量。

## 宿主发现与分发

`.agents/skills/advanced-econ-note2pdf` 和 `.claude/skills/advanced-econ-note2pdf` 是指向根目录 skill 的相对链接，只有一份维护源。`check_repo.py` 检查两条链接、技能元数据、文档引用和 Python 语法。

2026-10-31，本机 Codex CLI 0.166.0-alpha.5.1 的 app-server `skills/list` 实际返回此 skill，`scope=repo`、`enabled=true`。核对方式：从本机 `generate-json-schema` 确认 initialize 和 skills/list 参数，再以 stdio 只查询技能列表；没有创建模型任务。Claude Code 2.1.285 可用，项目入口配置与官方文档一致，尚未运行模型转录。DSH 未识别具体产品，专用加载保持待验证。

`package_skill.py` 只打包 skill 必需的脚本、参考文件、模板、元数据与依赖声明，固定 ZIP 条目时间以便复现，输出校验摘要。不会包含原始材料、工作目录、编译缓存、测试夹具或凭据。安装包解压后可直接从其中调用 CLI，无需此仓库 tools/ 或 docs/。

GitHub Actions 的 Engineering checks 只运行无模型、无真实样本的结构检查和合成材料流程；需要 Poppler，不安装 TeX。完整 LaTeX 与渲染自检在本机运行。CI 运行状态以对应 PR 的检查记录为准。

P5 开发检查已完成：安装包解压后的 CLI 可独立运行，重复打包摘要相同；损坏 PDF 返回结构化错误且不留下半成项目；faithful 不含 explanation，普通事项只进入附录，critical/open 强制部分输出且无法通过隐藏附录绕过正文提示。PR #6 的 Engineering checks 已运行成功，合并以最终提交的检查结果为准。

## 发布前回归（2026-11-02）

`python3 tools/publication_check.py` 需要 TeX，检查未引用裁切不导出、忠实版不带复习版内部详情/原文件名、latexmk RC 不执行、常见外部 input 在组装前拒绝以及 LICENSE 随包。`python3 tools/dev_check.py --with-latex` 继续覆盖中文/公式/图表/引用、失败隔离与恢复；当前两项均已通过。

Skills CLI 本地目录安装已在一次性项目内验证，未覆盖个人 skill 目录；README 的远程安装形式使用相同 CLI，私有仓库仍需要访问权限。真实案例只检查经授权的一张照片中完整 Hamilton 条件板面，输出2页；已实看全部页面，Fandol 字体嵌入、中文文本提取正常、当前编译警告为空。照片、转录、讲义、日志和本机路径不入库。

编译限制是在已知威胁上的加固而非完整 TeX 解析器或沙箱。不要将通过黑名单检查等同于可信内容。现有独立工程仍用 XeLaTeX/latexmk，手工重编译时也应禁用 RC，并只编译可信源码。

## 连续讲义与中文预览回归（2026-11-03）

`pdf_compat_check.py` 编译合成中文 PDF，验证缺失 ToUnicode 修复、中文提取、已有映射保留、元数据/书签保留、重复执行不改写文件以及未知 CID 集合拒绝猜测。`presentation_check.py` 检查用途配置、旧项目默认值、非法值拒绝、配置变更使旧构建失效，以及来源强调和跨页色块中的内容保留；还检查实际 PDF 中图、表、长表及其题注为来源蓝色，补充解释为黑色。两项需要 XeLaTeX，均已通过；不接入模型。

最终 PDF 在编译后嵌入缺失的受支持标准 Unicode 映射，独立 ZIP 带 `pdf_compat.py` 和使用说明。手工重新编译后执行 `python3 pdf_compat.py main.pdf`。已在无外部 CMaps 的 PDF.js 中复现原 PDF 中文消失，修复后中文可见；Codex 内建编译器已对显式 main.tex 编译成功。此证据不等同于 Codex UI 已目视验收。

授权数理经济学案例扩展为三块完整板面的两页连续讲义：优化对象与约束、Hamilton 定义、一阶变分、协态及边界条件；来源内容与补充推导交错排列，并分别记录。已核对关键公式及条件，查看全部渲染页；当前 PDF 无编译警告。仅覆盖选定板面，不代表全部照片、四学科或跨宿主验收；所有真实材料及交付物保留在忽略目录。
