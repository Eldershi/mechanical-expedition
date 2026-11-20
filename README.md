# 机械动力：远征

机械动力：远征客户端源码与安装包。游戏环境为 Minecraft 1.20.1、Forge 47.4.10、Java 17。

## 版本状态

| 版本 | 开发计划 |
| --- | --- |
| **1.20.1 · Forge** 已停止开发 | [归档的 ATM 之星毕业路线](docs/roadmap.md) |
| **1.21.1 · NeoForge** 当前开发线（测试中） | [开发计划与地月远征](https://github.com/Eldershi/mechanical-expedition/blob/migration/1.21.1-neoforge/docs/roadmap.md) |

体验 1.21.1 测试线请下载 [1.21.1-test.4](https://github.com/Eldershi/mechanical-expedition/releases/tag/v1.21.1-test.4)，导入为独立实例并选择 Java 21。

## 安装 1.20.1 客户端

1. 从 [发行页面](https://github.com/Eldershi/mechanical-expedition/releases) 下载 `mechanical-expedition-0.2.0-dev.2.mrpack`。
2. 使用支持 Modrinth 整合包的启动器导入该文件，并新建独立实例；启动器会下载清单中的模组及 Create MC GUI 官方文件，Paxi 会自动启用界面材质。
3. 为实例选择 Java 17，确认游戏版本是 Minecraft 1.20.1、加载器是 Forge 47.4.10，然后启动游戏。
4. 使用自己的 Minecraft 账号登录，并自行添加服务器。安装包不含账号信息、存档和服务器列表。

如果导入或启动失败，保留启动器报错和最新游戏日志供排查；分享前请先移除账号令牌及其他个人信息。旧版 `0.1.0-dev.1` 不包含当前游戏内容。此安装包用于全新安装，不应通过旧版更新器覆盖现有实例。

| 内容 | 位置 |
| --- | --- |
| 当前客户端的任务、配方、配置、资源和自研／定制补丁包 | `current/client/` |
| 当前专用服务端覆盖配置、脚本和登记补丁 | `current/server/` |
| 现用模组的文件名、哈希、下载定位和本地补丁路径 | `current/mods.lock.json` |
| 游戏与工具的自研代码、生成器、模型、贴图和标题源文件 | `development/` |
| 当前文件校验清单 | `current/files.sha256`、`development/files.sha256` |
| 已发布的 `0.1.0-dev.1` 发行源码和更新清单 | `pack/`、`files.tsv`、`mods.tsv`、`modrinth.index.json` |

当前游戏源码包含原配方并行、材料统一与原生加工、松烟墨、任务书、铁魔法 HNN 模型与资源包、装备兼容、女仆与仓储兼容，以及服务端生成、传送和随机刻补丁。实际模组依赖以 `current/mods.lock.json` 为准。

重复的番茄、稻米、洋葱及有对应素材的种子、稻穗优先使用农夫乐事外观，包含种植后的各生长阶段。物品与配方保持各自现有规则；外观覆盖的范围和构建方法见 [Crop appearance](development/tools/crop-appearance/README.md)。

当前兼容组合保留 JEI 15.59.0.212、JEI++ 1.0.7 和 ExtendedAE Plus 1.6.3，以兼容已安装的配方查看器扩展；Fluid Logistics 保留 1.3.1，以维持烈焰冷却器、霜冻蛋糕及配套冷加工配方。其他模组的精确版本与文件哈希以锁文件为准。

怪奇宝典收录 42 本教程与探索提示书，首次进入时发放，也可用一本书和一个书架合成。已有宝典放入玩家背包后会自动补齐缺失条目，保留自定义书籍、名称及当前选中的书；页面解锁仍由原模组控制。Malum 的秘传百科全书保留原生获取条件，取得后可手动加入宝典。怪奇宝典的物品外观使用模组自带的模型与贴图，汉化资源保留文字，不覆盖该物品外观。

中文补全覆盖当前模组的物品说明、功能提示、设置和各模组手册。武器中的硬编码提示仅在简体中文下替换，并保留颜色、动态数值与按键。安装更新后需要完整重启客户端。社区译文来自 [CFPA 团队及贡献者](https://github.com/CFPAOrg/Minecraft-Mod-Language-Package)，按其 CC BY-NC-SA 4.0 许可保留署名；原模组内容仍遵循各自许可。

5×5 动力合成使用 [Create: Factory Controller](integrations/mods/createfactorycontroller.json) `1.2.1-forge-1.20.1`（Beta），客户端与服务端安装相同版本。先在工厂控制器中放置材料与成品仪表、连接材料关系，打开成品仪表的“使用动力合成”，将网格大小设为与动力合成器方阵一致，并允许生产订单；随后在仓管中选择该产品的生产图样下单。默认最多支持 10×10 方阵，动力合成器之间需要用扳手连通；批量合成必须经过理包机。详细操作见[官方手册](https://nbcss.github.io/create-factory-controller/manual/en/factory-gauge.html#crafting)。

工厂控制器的单次合成材料必须能装入 9 个堆叠槽位。鎏盾胸甲等需要 10 种材料的配方仍使用原有手动动力合成方式；配方与材料保持原样。

仓储发报机使用 [Create: Stock Keeper Bookmarks](integrations/mods/stockkeeperbookmarks.json) 1.0.0 Forge 1.20.1 版，仅客户端安装，安装后需完整重启客户端。输入目的地地址后点击“+”保存书签；点击书签会直接向该地址发送已选物品，右键删除，拖动调整顺序。每台终端分别保存书签，打开界面时默认清空地址。个人书签保存在客户端本地，不随整合包发布。

[Sophisticated Building](integrations/mods/sophisticatedbuilding.json) 使用 5.1.2 Forge 1.20.1 版，客户端与服务端须安装同一版本。手持建筑方块，按住左 Alt 打开轮盘，选择墙面、地板或立方体；墙面和地板点击两次，立方体先选底面再确定高度。支持实心、空心和边框选项，生存模式按实际放置数量消耗材料；Ctrl+Z 撤销，Ctrl+Y 重做。选择 Disable 返回普通放置与挖掘。

生命值使用 [Overflowing Bars 8.0.1](integrations/mods/overflowingbars.json) 的紧凑分层显示，超过一排时在旁边显示 ×2、×3 等层数；护甲与韧性也支持叠层。Mantle 的生命值绘制已关闭，AsteorBar 保持关闭，避免重复接管 HUD。该模组仅需安装在客户端，显示沿用已加载的 GUI 资源。

[Create MC GUI 2.10.0](integrations/resourcepacks/create-mcgui.json) 由启动器直接从作者的 [CurseForge 文件](https://www.curseforge.com/minecraft/texture-packs/create-mcgui/files/9458951) 下载，并由 Paxi 自动启用。依照[作者许可](https://github.com/9qtzq6zstf-dev/create-mcGUI/blob/main/LICENSE)，整合包只保存下载引用，不捆绑或转存该材质包。

AuraTip 与 OElib 的事件接口适配、Steam Ages 与 Steam Letters 的机器注册兼容，以及 BCLib 和女仆世界生成保护的构建源码均保存在 `development/`。

地牢进行时 [Dungeon Now Loading](integrations/mods/dungeonnowloading.json) 使用 2.2 Forge 1.20.1 版，客户端与服务端安装同一版本。模组提供迷宫、二元神庙与可重复挑战的 Boss；现有存档需要在尚未生成的区块中寻找新增地牢。

[Modern Trials Integration](integrations/mods/mti.json) 使用 1.2.0 Forge 1.20.1 版，客户端与服务端安装同一版本。包含试炼大厅、试炼刷怪笼、宝库、重锤，以及铜格栅等铜与凝灰岩方块；已有存档需在尚未生成的区块寻找大厅。使用上游默认配置，保留新版袭击触发、命名牌与鞍合成、五根线制作拴绳及对应村民交易变化。第三方模组通过官方 CurseForge 下载引用安装，仓库不保存其 JAR。

交错电网 [Create: Power Grid](integrations/mods/powergrid.json) 使用 0.6.2 Forge 1.20.1 版，客户端与服务端均需安装；要求 Create `[6.0.7,6.1.0)`、Architectury `[9.2.14,)`。

敌对神经网络外观资源由独立项目 [create-style-hnn](https://github.com/Eldershi/create-style-hnn) 维护；下载与版本信息见[资源引用](integrations/resourcepacks/create-style-hnn.json)。

戴森球 [Dyson Cube Project](integrations/mods/dysoncubeproject.json) 使用 `1.20.1+1.0.5.1` Forge 版，客户端与服务端必须安装同一版本的模组；客户端启用 v1.1.0 机械动力风格外观，配套渲染兼容模组仅安装在客户端。

戴森球客户端外观通过 Paxi 单份加载，资源包、启动脚本与原生渲染兼容 JAR 使用匹配版本；安装或更新后需完整重启客户端。模型、贴图与构建输入由独立仓库 [create-style-dyson](https://github.com/Eldershi/create-style-dyson) 维护，三个客户端文件的版本、校验值与下载定位见 [集成引用](integrations/resourcepacks/create-style-dyson.json)。快照工具验证启用集成的文件校验值并省略其内容；停用集成的声明文件必须不在活动客户端路径中，残留文件或 Paxi 引用会阻止生成快照。

网络音乐机 [Net Music](integrations/mods/netmusic.json) 使用 `1.5.2-forge+mc1.20.1`，客户端和服务端安装同一版本。提供网络唱片机、唱片刻录机、电脑和大喇叭；联网音乐需要每位听众能够访问对应音源，本地音频路径仅供本机播放。安装后需完整重启客户端和服务端。

节气 [Ecliptic Seasons](integrations/mods/eclipticseasons.json) 使用 Forge 1.20.1 的 `0.15.5` 版（上游标记为 Beta），客户端与服务端均需安装。季节模拟设为环境模式，保留四季、节气、植被颜色与季节天气；关闭作物季节、湿度和骨粉限制，以及季节繁殖、蜜蜂、钓鱼和中暑规则。公共配置位于 `config/eclipticseasons-common.toml`，多人游戏以服务端配置为准。

下界作物遵循各自原生土壤与放置规则，不附加维度限制。破坏方块不要求 `init` 阶段，任务书不包含对应的阶段领取任务。烈焰蛋糕进食不附加魔改伤害。

模组锁文件共有 408 项：391 项有哈希匹配的下载来源，17 项为随源码保存的补丁包。

`current/client/` 是受管游戏文件的源码快照，第三方模组通过锁文件定位。它不包含账号、存档、玩家数据、服务器列表、地图、备份、运行缓存或一次性测试探针。`current/server/` 是专用服务端覆盖层，需要与公共游戏内容和对应服务端依赖一起使用。

仙灵与地精的自然生成已关闭。破灭魔王剑、崇高誓约之剑、誓约与禁忌之刃及其投射物施加的影焰继承施加者的七咒之戒伤害规则；影焰持续伤害不额外击退目标，正常近战击退保持原有规则。

理包机使用 [God Damn Repackager 0.5.1 Forge Alpha](https://www.curseforge.com/minecraft/mc-mods/god-damn-repackager)，同一机械动力保险库上的多台理包机可以并行处理订单；理包机需要红石供能。该模组仍为 Alpha，安装前应备份存档。

专用服务端使用原版运动碰撞解析，以兼容模组的碰撞钩子；Radium 的其他优化保持启用。

专用服务端通过 `config/fml.toml` 的 `maxThreads = 1` 串行执行 Forge 早期模组加载，规避 Quark 与 Supplementaries 构造期间对 Zeta 事件注册表的并发写入；启动可能更慢，正常游戏线程不受该设置限制。

专服覆盖层包含 Player Motion Guard 1.1.0：保留异常运动查询保护，并在本地保存有容量上限的逐 tick 玩家状态、行为事件、独立卡顿现场与 Spark 采样。JFR 暂时关闭，导出期间发生的进程中断原因仍待核实。部署配置每秒请求强制刷盘；只有回执已确认的数据作为跨进程强制终止的保留边界，待写数据仍可能丢失。该补丁不代表已定位异常速度的上游来源；客户端无需额外安装。配置、状态命令、查询与验证工具见 [Player Motion Guard](development/tools/player-motion-guard/README.md)。

当前安装包由 `python3 tools/package_current.py` 构建；构建时会校验客户端文件、模组锁和独立戴森球资源包。旧版更新器仍使用 `pack/` 中的旧发行清单。旧版包可用 `python3 tools/package_repository.py` 重建，更新器验证为 `python3 tools/test_updater.py`。

生成新的当前文件快照：

```sh
python3 tools/snapshot_current.py --project "/path/to/远征工作区" --instance "/path/to/活动客户端" --output "/path/to/新暂存目录"
```

快照工具写入新目录，核验文件与模组哈希，并保留锁文件中与现用哈希一致的下载来源。审阅后将生成内容同步到 `current/`，同时维护相应 `development/` 源码，完成验证、提交、推送和远端核验。

专服覆盖默认读取仓库中已核验的 `current/server/`；需要接入经确认的新覆盖目录时，用 `--server-source` 明确指定。

`development/` 保持工作区的源码相对布局。部分维护器依赖完整工作区、固定资源输入、原版模组 JAR 和 Forge／Minecraft／ASM／Mixin 运行库；构建前需要适配输入路径并补齐依赖。正式游戏内容以 `current/` 为准。

上游为 [Re_Construction / Team Nebula 的革新构件](https://github.com/Eternal-Snowstorm/Create-Mechanism-and-Innovation)。许可与发行来源见 [LICENSE](LICENSE)、[License.md](License.md)、[UPSTREAM.md](UPSTREAM.md) 和 `source-manifest.json`；源资产内的第三方许可随文件保留。
