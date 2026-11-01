# 机械动力：远征

私有开发源码仓库。游戏环境为 Minecraft 1.20.1、Forge 47.4.10、Java 17。

| 内容 | 位置 |
| --- | --- |
| 当前客户端的任务、配方、配置、资源和自研／定制补丁包 | `current/client/` |
| 当前专用服务端覆盖配置、脚本和登记补丁 | `current/server/` |
| 现用模组的文件名、哈希、下载定位和本地补丁路径 | `current/mods.lock.json` |
| 游戏与工具的自研代码、生成器、模型、贴图和标题源文件 | `development/` |
| 当前文件校验清单 | `current/files.sha256`、`development/files.sha256` |
| 已发布的 `0.1.0-dev.1` 发行源码和更新清单 | `pack/`、`files.tsv`、`mods.tsv`、`modrinth.index.json` |

当前游戏源码包含原配方并行、材料统一与原生加工、松烟墨、任务书、铁魔法 HNN 模型与资源包、装备兼容、女仆与仓储兼容，以及服务端生成、传送和随机刻补丁。实际模组依赖以 `current/mods.lock.json` 为准。

交错电网 [Create: Power Grid](integrations/mods/powergrid.json) 使用 0.6.2 Forge 1.20.1 版，客户端与服务端均需安装；要求 Create `[6.0.7,6.1.0)`、Architectury `[9.2.14,)`。

敌对神经网络外观资源由独立项目 [create-style-hnn](https://github.com/Eldershi/create-style-hnn) 维护；下载与版本信息见[资源引用](integrations/resourcepacks/create-style-hnn.json)。

戴森球 [Dyson Cube Project](integrations/mods/dysoncubeproject.json) 使用 `1.20.1+1.0.5.1` Forge 版，客户端与服务端必须安装同一版本的模组；模组继续在双端保留，客户端外观资源包与渲染脚本已停用。

戴森球客户端外观集成当前为停用状态，Paxi 不加载对应资源包，客户端不运行配套渲染脚本。独立仓库 [create-style-dyson](https://github.com/Eldershi/create-style-dyson) 保留模型、贴图与构建输入；版本、文件校验值与发布下载定位继续保存在 [集成引用](integrations/resourcepacks/create-style-dyson.json)。快照工具验证启用集成的文件校验值并省略其内容；停用集成的声明文件必须不在活动客户端路径中，残留文件或 Paxi 引用会阻止生成快照。

模组锁文件共有 396 项：377 项有哈希匹配的下载来源，14 项保存了本地补丁包，5 项仅有精确哈希，尚缺可核实的下载定位。

`current/client/` 是受管游戏文件的源码快照，第三方模组通过锁文件定位。它不包含账号、存档、玩家数据、服务器列表、地图、备份、运行缓存或一次性测试探针。`current/server/` 是专用服务端覆盖层，需要与公共游戏内容和对应服务端依赖一起使用。

专用服务端使用原版运动碰撞解析，以兼容模组的碰撞钩子；Radium 的其他优化保持启用。

现有更新器与 Release 仍使用 `pack/` 中的发行清单。`current/` 尚未生成新的安装包或 Release；不能用现有版本号向玩家宣称已分发这些源码。重建现有发行包可运行 `python3 tools/package_repository.py`，更新器验证为 `python3 tools/test_updater.py`。

生成新的当前文件快照：

```sh
python3 tools/snapshot_current.py --project "/path/to/远征工作区" --instance "/path/to/活动客户端" --output "/path/to/新暂存目录"
```

快照工具写入新目录，核验文件与模组哈希，并保留锁文件中与现用哈希一致的下载来源。审阅后将生成内容同步到 `current/`，同时维护相应 `development/` 源码，完成验证、提交、推送和远端核验。

专服覆盖默认读取仓库中已核验的 `current/server/`；需要接入经确认的新覆盖目录时，用 `--server-source` 明确指定。

`development/` 保持工作区的源码相对布局。部分维护器依赖完整工作区、固定资源输入、原版模组 JAR 和 Forge／Minecraft／ASM／Mixin 运行库；构建前需要适配输入路径并补齐依赖。正式游戏内容以 `current/` 为准。

上游为 [Re_Construction / Team Nebula 的革新构件](https://github.com/Eternal-Snowstorm/Create-Mechanism-and-Innovation)。许可与发行来源见 [LICENSE](LICENSE)、[License.md](License.md)、[UPSTREAM.md](UPSTREAM.md) 和 `source-manifest.json`；源资产内的第三方许可随文件保留。
