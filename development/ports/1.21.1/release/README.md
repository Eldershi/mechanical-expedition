# 1.21.1 测试构建

Minecraft 1.21.1、NeoForge 21.1.267、Java 21。构建进入 `migration/1.21.1-neoforge` 或对应的 `v1.21.1-test.N`。

1. 使用已验证的客户端和专用服输入，运行 [测试实例安装器](../world-server/space/install.py)。安装器使用 Pillow 从客户端模组构建焦黑与焦褐系列的材质包，并安装两端的配方覆盖。
2. 运行 `python3 development/ports/1.21.1/release/package_test.py validate` 检查分支和发布清单。
3. 运行 `python3 development/ports/1.21.1/release/package_test.py package --client <client> --server <server> --output <dir>`，生成客户端 MRPACK、服务端覆盖层 ZIP 和 SHA256SUMS。

客户端使用新建启动器实例导入，初始画面设置由 `client-options.txt` 提供。服务端覆盖层安装在已准备好的 NeoForge 专用服目录。包体依赖已锁定的本地输入，具有官方且哈希一致的客户端文件由启动器下载。Create MC GUI 通过作者官方文件引用下载。文件锁涵盖项目默认配置，世界、账号及验收副本的个人设置保存在本地。版本升级时从停止的验收副本执行 `lock` 子命令更新锁和索引，`--catalog <json>` 可传入含官方地址和 SHA-1 的下载目录。
