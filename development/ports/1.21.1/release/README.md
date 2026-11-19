# 1.21.1 测试构建

Minecraft 1.21.1、NeoForge 21.1.267、Java 21。构建进入 `migration/1.21.1-neoforge` 或对应的 `v1.21.1-test.N`。

1. 使用已验证的客户端和专用服输入，安装当前源码的地月适配。运行 [地月设施安装器](../world-server/space/install.py)。
2. 运行 `python3 development/ports/1.21.1/release/package_test.py validate` 检查分支和发布清单。
3. 运行 `python3 development/ports/1.21.1/release/package_test.py package --client <client> --server <server> --output <dir>`，生成客户端 MRPACK、服务端覆盖层 ZIP 和 SHA256SUMS。

客户端使用新建启动器实例导入。服务端覆盖层安装在已准备好的 NeoForge 专用服目录。包体依赖已锁定的本地输入，具有官方且哈希一致的客户端文件由启动器下载。Create MC GUI 通过作者官方文件引用下载。文件锁不包含世界、账号和客户端个人设置。版本升级时从停止的验收副本执行 `lock` 子命令更新锁和索引，`--catalog <json>` 可传入含官方地址和 SHA-1 的下载目录。
