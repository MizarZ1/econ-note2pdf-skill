# 宿主执行流程

任务配置按 [入口](../SKILL.md) 获取，字段与默认值见 [内容契约](content-model.md)；正文编写前读 [编辑规则](editorial.md)。

## 材料与上下文

先查看每张全图的课题、布局和覆盖区域，再看高清局部；低分辨率预览不能作为密集公式的唯一证据，PDF 自带文本只用于定位。显式输入顺序优先，目录自然排序只是候选。结合标题、时间下标、推导接续和擦写痕迹判断；两个合理顺序会改变推导时询问用户，其余部分继续。

按内容区域比较重叠照片：完全重复可合并；新条件、修正符号、后续箭头和被擦掉的中间步骤单独保留。图片相似或首行公式相同不足以去重。

## 转录与单元

单元是可独立理解的问题、命题或推导，可跨多图，一图也可有多个单元。逐区域登记文字、公式、图表和有意义边注，在 coverage 中说明纳入、重复、排除或无法识别及对应内容；整页有一条记录不等于完整覆盖。

先核对忠实内容与符号含义，再派生 study。保存上下文简记：目标、已用条件、待接续等式、变量、图中对象和未完证明。符号表按作用域区分同形符号（如 λ 的乘子／特征值），沿用教师记号，必要规范化须全节一致并记录；教师手写习惯只用于当前课程。少量符号在首次使用处解释，不必生成记号表。

模糊处先定位原区域、放大或轻度增强，再结合已确认定义核查。学科知识只提出候选，不能把候选当成已确认内容。按编辑规则记录补充、更正和歧义，并在 study 写作前建立知识依赖与阅读顺序。跨图推导用完整的 LaTeX 环境及公式引用衔接，不让环境跨文件悬空。

## 工具与运行顺序

以下 `<skill>`、`<project>`、输入路径均替换为实际绝对路径；mode、用途、样式和学科按本次配置替换。依赖或宿主能力问题查 [宿主说明](hosts.md)。

```sh
python3 "<skill>/scripts/econ_note.py" doctor
python3 "<skill>/scripts/econ_note.py" init --project "<project>" --inputs "<photo-or-pdf>" --title '课程讲义' --mode study --purpose revision --source-style plain --domains macro
python3 "<skill>/scripts/econ_note.py" prepare --project "<project>"
```

doctor 的返回码不代表完整 PDF 能力，须核对输出中的图像、编译、预览能力，PDF 输入还需 pdf_intake。prepare 后实际查看返回的全图、预览和 tiles，按契约填写 units/ 与 content/，不能直接跳到组装。

后续命令均在 `python3 "<skill>/scripts/econ_note.py"` 后接下表参数：

| 顺序 | 命令与关键参数 |
| --- | --- |
| 结构与覆盖检查 | `validate --project "<project>"`，同时对照原图核查覆盖 |
| 内容复核登记 | `review --project "<project>" --kind content --unit u001 --note '核对范围与结果'`，逐单元实际复核后登记 |
| 组装、编译、渲染 | 分别执行 `assemble`、`compile`、`render`，均带 `--project "<project>" --mode study` |
| 页面复核登记 | `review --project "<project>" --kind layout --mode study --note '检查页码与结果'`，查看全部最终页后登记 |
| 交付 | `package --project "<project>" --mode study` |

both 共享来源与内容核对，分别组装、编译、渲染、页面复核和打包 faithful、study。课程共用宏写入 project.json 的 preamble 文件，不改安装目录模板；具体参数查 `--help`。

## 修复与恢复

恢复先 `status --project "<project>"`，只处理未完成或 stale 单元，保留用户修正。用途、样式、内容等变更后重新 validate、assemble、compile、render 并实际复核；不得沿用过期状态。

修复项目内源片段或课程模板后重新组装，不只改生成文件。读取错误块、前后文和原图，先排查环境闭合、非法字符、宏缺失和尺寸，再处理复杂图形；确认条件、公式行数和图表信息未减少。同一故障最多 3 次有依据修复，仍失败则保存内容，以 `compile --isolate-failures` 逐单元诊断；公共模板问题修公共模板，不能排除所有章节。

确需部分输出时用 `assemble --allow-partial`；提前交付未复核结果用 `package --allow-unreviewed`。均带上述工程与模式参数，缺失位置和未复核状态须保留，技术错误留日志。退出码 3 是部分／未复核结果，不是正常完成。

编译禁用 latexmk 自动 RC，限制 TeX 读写并检查文件操作及动态指令；这些措施不是操作系统沙箱。不编译不可信的现成 TeX 工程，不为恶意指令放宽限制。中文使用 Fandol；检查 Unicode 映射诊断、最终日志 Missing character 并实看中文页。独立工程重编译后按 DELIVERY.md 执行 pdf_compat.py；宿主预览差异见宿主说明。

## 两次复核

**内容：** 原图逐区域对照 coverage，检查上下标、量词、条件、符号、等式／近似、图表标签和边注。再通读正文：问题和条件是否清楚、新符号是否已解释、推导与跨节引用是否连贯、结论何时适用，source 强调是否混入补充。完成后登记每个 unit 的 content review。

**页面：** 查看最新 PDF 的每页渲染，检查中文、标题分页、长公式和矩阵截断、图形标签拥挤、表注丢失、未解析引用、字号和图文位置。检查色块跨页完整性与少量记号造成的空白页，完成后登记各 mode 的 layout review。

两种复核都由宿主实际执行；内容或 PDF 改变后旧复核失效，不能以脚本通过或自动登记替代查看。
