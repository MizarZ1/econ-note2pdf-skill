# 参与开发

提交 issue 时说明宿主、系统、依赖版本、复现步骤及预期行为；用合成或已获授权并脱敏的最小材料，不上传完整私人课堂照片、个人笔记或日志中的凭据。

改动通过分支与 PR 提交。先运行 `python3 tools/check_repo.py`、`python3 tools/dev_check.py`；编译或导出变更另运行 `python3 tools/dev_check.py --with-latex` 和 `python3 tools/publication_check.py`。后两项需要 XeLaTeX、latexmk、Poppler。

贡献采用项目 MIT 许可。编译成功、内容复核和真实材料验收分别报告；外部贡献者不继承维护者的自动合并授权。
