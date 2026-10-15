# 机械动力：远征 · 更新源

这是远征魔改版的独立客户端更新仓库。基于 [Re_Construction / Team Nebula 的革新构件](https://github.com/Eternal-Snowstorm/Create-Mechanism-and-Innovation)。固定基线、来源和许可见 `UPSTREAM.md`、`source-manifest.json`、`LICENSE`、`License.md`。

## 内容

- `pack/`：发行版管理的配置、脚本、任务、资源与更新器源码。
- `files.tsv`：每个受管内容文件的SHA-256与相对路径。
- `mods.tsv`：精确模组版本、SHA-256和作者公开下载地址。仓库不存放整套模组JAR。
- `release.env`：独立版本号、渠道和固定Minecraft／Forge版本。

玩家使用导入包中的 `updater/update.bat`（Windows）或 `updater/update.command`（macOS）。Git for Windows为Windows入口提供Git、Bash和curl；macOS使用本地Git与系统工具。详见 `pack/README.md`。

## 发布习惯

每次发布在远征开发工作区运行 `distribution/build_release.py`，它会依据当前已验证实例重建清单与导入包。检查构建报告，运行 `distribution/test_updater.py`，再提交生成的更新仓库，打上独立版本标签并发布对应 `.mrpack` 与源码ZIP。

仅从本仓库重建导入包（Python 3，无第三方依赖）：`python3 tools/package_repository.py`。文件与模组清单必须一致；重建会核验SHA-256。更新器测试：`python3 tools/test_updater.py`。

GitHub Actions支持推送与版本号一致的 `v*` 标签，或在Actions页面手动运行“Build client release”。任务先测试更新器，再生成导入包、源码ZIP与SHA-256清单，最后建立开发版Release。已发布的同名版本不会被自动覆盖。

新版本必须先在独立测试实例运行。更新源仅应用同一Minecraft与Forge版本内的变更；迁移游戏或加载器版本时生成新的安装包。

`.mrpack`使用官方格式并包含ForgeCDN等公开下载地址，面向支持这些来源的启动器导入；它不是直接上传Modrinth网站的发行包。

源码保留原有许可和署名。所有本修改版分发均免费，不包含开发者存档、账号信息、QQ导出、日志、服务器地址或机器专用路径。
