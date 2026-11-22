# 远征多方块蓝图

适用于 Minecraft 1.21.1、NeoForge 和 Create 6.0.10。蓝图目录和结构文件由随包的模组资源生成，可直接用机械动力蓝图桌打开。

## 在游戏里使用

1. 将压缩包里的 `schematics` 文件夹合并进游戏实例目录。
2. 在蓝图桌放入空白蓝图，选择以 `Expedition_` 开头的文件。旁边的《蓝图目录》列出中英文文件对应、外尺寸和施工后的操作。
3. 拿着写好的蓝图到空地定位、旋转并预览。可以照着预览手搭，也可以把定位后的蓝图放入蓝图加农炮。蓝图炮从相邻箱子取材料，可用书或写字板打印材料清单。
4. 方块按蓝图摆好后，按设备本身的要求成型、配置和接线。沉浸工程用工程师手册找到锤击点。工业涡轮的叶片装在转子上。空间存储塔柱和端口需手动接入 ME 网络。

设备的可调尺寸以所属模组的规则为准。蓝图提供可复用的固定布局。戴森球射线接收站和电磁轨道弹射器由所持控制器放置时创建，预留空地后直接放置控制器。引用未装模组的搭建器模板需要相应模组才能成型。

## 生成蓝图包

安装 Python 3.10 或以上及 `nbtlib==2.0.4`。使用远征 1.21.1 NeoForge 模组目录运行以下命令。

```sh
python build.py --mods /path/to/instance/mods --output expedition-create-blueprints.zip
```

可追加 `--install /path/to/client-instance` 写入客户端的蓝图目录。如果那里有被修改过的同名文件，请先备份。运行时由 Create 原生蓝图桌处理这些文件。

沉浸工程的布局取自本版本的原生多方块结构资源，通用机械的六个机器布局取自 Multi Builder Tool 模板。冶炼和熔铸布局来自当前移植版的手册。AE 系列的矩阵和空间存储布局来自各自的 GuideME 手册。雷达布局使用仓库中对应的成型测试结构。

生成器保留施工需要的方块、方向和接口，移除方块实体保存的库存、能量以及其他世界状态。预览中的空位在施工时应保持空置。

合金炉提供 `Expedition_CMI_alloy_furnace_andesite.nbt` 和
`Expedition_CMI_alloy_furnace_brass.nbt`，各 88 格。蓝图以控制器朝西为基准，搭齐后自动识别。

液压机蓝图为 `Expedition_CMI_hydropress.nbt`。北面为操作台，西侧固料进、东侧固料出，南面接配方流体，东后侧接电。

工业高炉、大型电解池与自动贸易终端分别使用 `Expedition_CMI_shaft_furnace.nbt`、
`Expedition_CMI_electrolytic_cell.nbt` 和 `Expedition_CMI_trading_station.nbt`。三台设备的操作台朝北。
工业高炉需要两座已点燃的液体烈焰人燃烧室。自动贸易终端的两个蜂港各需 3×3×4 格净空，
物流蜂和地址在安装后通过 Create: Mobile Packages 配置。
各端口见[工业多方块](../world-server/brass-industry/README.md#工业设施外观)。
