# 远征 1.21.1-test.18

适用于 Minecraft 1.21.1、NeoForge 21.1.267 和 Java 21。

- 主菜单两侧的安山合金按钮顶边、小蓝按钮底边对齐中间按钮。间距统一为 4 个 GUI 像素，窄窗口自动换行。四个主要按钮的黑色描边占 1 个 GUI 像素。主菜单隐藏左下版本文字，原生版权文字贴右对齐。主菜单背景音乐关闭。Realms、Mods、Quark 和机械动力设置的文字或图标对齐到各自的按钮正面。
- 「饰品」打开统一的 Curios 样式面板。通用饰品、天境及其他饰品共用一张网格，每个槽位只显示一次。蝴蝶结在同一网格切换外观，右侧保留护甲和随身合成。配方仍可从 JEI 查看，原版配方书遵循 NERB 的现有设置。
- 七咒之戒的末影箱和磁戒开关分开排列。通用容器采用 Quark 的整理和转移按钮，普通点击转移全部，按住 Shift 转移匹配物品。
- 生存物品栏、饰品面板和精妙背包默认显示 TrashSlot 销毁槽。饰品页的销毁槽贴在右下角。
- 从测试版 1.21.1-test.12 更新专用服时，停止服务器并应用本页的服务端增量包，移除旧的饰品适配模组，再启动。客户端和服务端使用相同的新菜单协议。
- 仓储管理员的下单选项移到独立一行，生产订单按钮避开地址收藏列。
- 降低第一人称火焰遮罩的位置和不透明度，保留燃烧提示。

- 客户端和专用服均加入 [Create Rancher 1.0.6](https://www.curseforge.com/minecraft/mc-mods/create-rancher)，作者为 Halex，许可为 MIT。集奶地板可以把牛奶送入机械动力流体管路。[乳品车间布局及操作](development/ports/1.21.1/world-server/dairy-workshop/)。

- 客户端和专用服均加入 [Create CIR Addition 3.5.0](https://github.com/CIR-Server/Create-CIR-Addition/releases/tag/v3.5.0)，作者为 CIR Server 和 Real_Infinistar，许可为 CC BY-SA 4.0。启用 Create 机器优化，关闭自动清理、量子环限制和 Boss 保护，并沿用整合包的宝石切割规则。

- 客户端包含 Mielon’s The Sift 2.0.6、远征 Sift 兼容模组和 Lightman’s Currency 2.3.0.6。多人游戏请在启动器中导入本版 MRPACK。

- 客户端切换到 Sodium 的 12 区块近景，加入 Gnetum 和叶片剔除，使用快速树叶和天气渲染。默认关闭光影、云和实体阴影。
- 盔甲展示在附近没有展示架时跳过逐帧扫描。Xaero 世界地图默认在后台持续更新。
- Xaero 小地图默认放在右上角，始终北朝上。左上角显示当前 FPS。
- Paxi 启用地形、装备、模组外观和汉化材质。Create: mcGUI、Create Style HNN 等材质包由启动器从作者发布地址下载。
- Stay True 和 Fresh Waystones 使用作者的 1.21 对应版本。Pinnacle 使用 1.21.1 版，宝石动画、附魔台声音及奶桶模型由独立资源包适配。
- 附魔台的台身、物品模型和悬浮书使用 Minecraft 原版外观。

- 卫星收发站、货运发射台、太空电梯、轨道空投炮和月面异界门使用《黄铜协奏曲》的控制器配方与装配布局。结构外观使用机械动力原版材质。
- 五类控制器和航线记录可沿用。已有端点按新布局重搭后可以继续运行。
- 机素防护沿用 Giselle 的随身氧气。机巧新生气密甲使用气罐组的专用自然空气格。
- 航天任务书接入地月补给、月球地牢调查和首次异界航行。

- 加入 12 座工业多方块。控制器配方和布局参照《黄铜协奏曲》，模型使用机械动力原版纹理。运行采用远征测试工序。
- 差速器通过三步 Create 序列组装，每轮产出两个，可制作工业高炉和大型差分机控制器。

[安装、构建及校验](development/ports/1.21.1/release/) · [设施与护甲操作](development/ports/1.21.1/world-server/space/) · [工业设施操作](development/ports/1.21.1/world-server/brass-industry/)
