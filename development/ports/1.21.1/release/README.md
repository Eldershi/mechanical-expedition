# 1.21.1 测试构建

Minecraft 1.21.1、NeoForge 21.1.267、Java 21。构建进入 `migration/1.21.1-neoforge` 或对应的 `v1.21.1-test.N`。

1. 使用已验证的客户端和专用服输入，运行 [测试实例安装器](../world-server/space/install.py)。安装器下载并校验独立发布的 [Create Style Foundry](https://github.com/Eldershi/create-style-foundry) 客户端材质包，并安装两端的配方覆盖。
2. 运行 `python3 development/ports/1.21.1/release/package_test.py validate` 检查分支和发布清单。
3. 运行 `python3 development/ports/1.21.1/release/package_test.py package --client <client> --server <server> --output <dir>`，生成客户端 MRPACK、服务端覆盖层 ZIP 和 SHA256SUMS。

客户端使用新建启动器实例导入，初始画面设置由 `client-options.txt` 提供。服务端覆盖层安装在已准备好的 NeoForge 专用服目录。客户端第三方模组和 Create MC GUI 由启动器从锁定的作者下载地址安装，远征自研模组随包提供。文件锁涵盖项目默认配置，世界、账号及验收副本的个人设置保存在本地。版本升级时从停止的验收副本执行 `lock` 子命令更新锁和索引。工具按文件名与 SHA-1 复用现有下载地址，`--catalog <json>` 可补充新的官方来源。

### 同步本地客户端

每次更新开发分支后，在本地发布工作树执行 `git pull --ff-only`，核对 `HEAD` 与远端跟踪提交一致。提交包含游戏内容时，关闭本机测试客户端并运行同一检出中的更新工具。

```sh
python3 development/ports/1.21.1/release/update_local_client.py --profile "<实例目录>" --from-ref "<当前已安装的提交或标签>"
python3 development/ports/1.21.1/release/update_local_client.py --profile "<实例目录>" --from-ref "<当前已安装的提交或标签>" --apply
```

首次运行提供 `--from-ref`。后续更新从实例中的安装记录读取上次同步的提交。预检会验证发布锁、准备文件，并列出将更新或移除的路径。应用后逐项校验哈希并记录已安装的提交。工具保留存档、`options.txt` 和个人资源包顺序中的额外条目。遇到有意保留的本机设置时，可重复使用 `--preserve <相对路径>`。发生冲突时先核对差异再更新。安装后启动客户端，检查本次改动涉及的功能。

客户端和专用服共用[生产覆盖层](production_overlay.py)中的工业配方、矿床、机器配方界面和同名物品兼容规则。部署专用服时使用与客户端一致的构建。锁中退役的旧模组由本地客户端更新工具移除，服务端覆盖层部署时也要清除对应旧版本。

客户端和专用服均关闭 Quark 的「替换脚手架」功能，脚手架沿用普通方块放置规则。
