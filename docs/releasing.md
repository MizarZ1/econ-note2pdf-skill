# 发布方式

公开分发库为 [MizarZ1/econ-note2pdf-skill](https://github.com/MizarZ1/econ-note2pdf-skill)，从经过检查的源码快照建立。私有开发库独立保留；公开库不带其 Git 历史。后续从已审查并合并的开发提交生成快照，再通过公开库的分支与 PR 更新。

使用 `git archive HEAD` 在临时目录生成当前文件快照，检查内容后才上传。不要复制开发库的 `.git`、私人材料、`.local`、工作目录或本地日志；不强推或重写已有共享历史。发布提交使用公开 GitHub 身份，不在提交信息中包含本机路径或私人材料。

分发快照保留根 LICENSE、skill/LICENSE、README、安装说明和有效资源。维护者填写 GitHub Description 与 Topics（economics、latex、agent-skills），启用私密漏洞报告。公开库的 issue 与 PR 用于用户反馈；私有工作目录中的材料不随修订同步。

发布前运行结构检查、完整工程链路、`publication_check.py`、`pdf_compat_check.py`、`presentation_check.py`，检查 `git diff --check`。执行 `python3 tools/package_skill.py --output dist/advanced-econ-note2pdf-v0.1.0-preview.zip`，检查 ZIP 文件列表、LICENSE 与 SHA-256。建立 `v0.1.0-preview` 标签和预览 Release，附安装包与校验文件；先验证远程安装到临时目录，再公开 Release。创建公开仓库或发布 Release 需实际用户授权，外部 fork 不继承开发计划中的维护者授权。

源照片、生成讲义不随公开 Release 发布，除非另外取得具体授权。
