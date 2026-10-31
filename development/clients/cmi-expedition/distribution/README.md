# 发行构建工作区

`prepare_repository.py` 将审计通过的发行构建同步到发布检出目录。它保留当前源码目录与集成引用，并只暂存明确列出的项目文件。

输入为 `config.json` 指定版本下的 `dist/<version>/repository/` 和同级审计结果。运行前提交或另存发布检出目录中的已有修改。

现有发行源码可用 `tools/package_repository.py` 重建，更新器验证为 `tools/test_updater.py`。新发行使用独立版本号、对应标签及来源许可文件。
