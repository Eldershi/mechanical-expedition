# 第三方来源与许可

机械动力：奥术工艺 / Create: Arcane Crafts · 核对日期：2026-10-20。

本项目为独立附属模组，不代表 Mojang、Microsoft 或各依赖模组的开发团队。维护者为 Eldershi；项目反馈入口为 [GitHub Issues](https://github.com/Eldershi/create-arcane-crafts/issues)。

NOT AN OFFICIAL MINECRAFT PRODUCT. NOT APPROVED BY OR ASSOCIATED WITH MOJANG OR MICROSOFT.

## Minecraft

Minecraft Java Edition 1.20.1 为运行依赖，权利归 Mojang / Microsoft。参考 [Minecraft EULA](https://www.minecraft.net/en-us/eula) 和 [Usage Guidelines](https://www.minecraft.net/en-us/usage-guidelines)。仓库和发布 JAR 不包含游戏程序、游戏资源副本或修改后的完整客户端／服务器。

原版 Blaze、容器、模板、水动画等由已安装游戏在运行时提供；模型转换只分发本项目的拟合、材质和动画规则。原型曾参考的 1.21.1 Breeze 眉形已改为独立程序笔画，不读取或分发该版本的资源。

## 依赖模组

| 上游与作者 | 核对版本 | 许可与接入 |
| --- | --- | --- |
| Create — The Create Team / The Creators of Create | 6.0.8 | [代码 MIT、assets ARR](https://github.com/Creators-of-Create/Create/blob/mc1.20.1-6.0.8/LICENSE.md)。依赖/API；原生模型和材质运行时读取；改造动画代码保留 MIT 版权和全文 |
| Create Enchantment Industry — DragonsPlusMinecraft 及贡献者 | 2.5.4b | [LGPL-3.0-or-later](https://github.com/DragonsPlusMinecraft/CreateEnchantmentIndustry/blob/ee0c8f521255f51b94d893a2410329d28f1de525/LICENSE.txt)。砂轮继承与原生加工委托，打印 provider 接入；两项派生源码按 LGPL 发布 |
| Iron’s Spells ’n Spellbooks — iron431 / Redspace 及贡献者 | 1.20.1-3.16.3 | [ARR，允许自己编写依赖式 addon](https://github.com/iron431/irons-spells-n-spellbooks/blob/v1.20.1-3.16.3/LICENSE.md)。公开接口、注册表、原生粒子、隔离菜单、运行时书本模型与材质引用 |
| Sophisticated Backpacks — P3pp3rF1y 及贡献者 | 1.20.1-3.26.9.2194 | [官方 1.20.x 许可，ARR](https://github.com/P3pp3rF1y/SophisticatedBackpacks/blob/1.20.x/LICENSE.md)。背包补给使用依赖接口，升级框由已安装依赖运行时提供 |
| Sophisticated Core — P3pp3rF1y 及贡献者 | 1.20.1-1.5.6.2383 | [官方 1.20.x 许可，ARR](https://github.com/P3pp3rF1y/SophisticatedCore/blob/1.20.x/LICENSE.md)。运行依赖 |
| MinecraftForge 及贡献者 | 1.20.1-47.4.10 | [LGPL 2.1 与附加说明](https://github.com/MinecraftForge/MinecraftForge/blob/1.20.x/LICENSE.txt)。标准 Mod/API 依赖；原生流体材质运行时引用 |

完整文本、获取方式和版本限定见 `LICENSES/SOURCES.md`、`LICENSES/sources.json`。Sophisticated 与 Forge 收录的是官方维护分支许可，不冒称精确发布标签的快照。依赖仍是独立可替换 JAR，本项目不内嵌或重新分发它们。

## 实际代码适配

- `client/AscensionChamberRenderer.java`：相位、位移和追踪逻辑参考并改造 Create 6.0.8 的 `BlazeBurnerRenderer.renderShared` 与 `BlazeBurnerBlockEntity.tickAnimation`。Copyright (c) The Create Team / The Creators of Create。保留完整 MIT 文本；本项目加入奥术状态、书本和加工表现。
- `grinding/ArcaneGrindstoneDrainEntity.java`：容量检查和槽号 3000 协议适配 CEI `ProcessingInventory`；原生私有加工委托上游。整个此文件以 LGPL-3.0-or-later 发布。
- `grinding/ArcaneGrindstoneItem.java`：放置方向和替换行为适配 CEI `MechanicalGrindStoneItem`。整个此文件以 LGPL-3.0-or-later 发布。
- `compat/NativeAnvilBridge.java` 与对应 Mixin：调用安装的 Iron 原菜单，并只复制本次输入/输出 ItemStack；不分发原菜单实现。返还模板隔离与结果后置校验属于本项目适配。
- `client/AnimatedSpellBookMeshes.java`、`BookMeshGeometry.java`：读取安装的 Iron JSON 和原版 BookModel 公共接口，以本项目自己的转换算法生成关节；没有内嵌上游几何/UV压缩数据。
- `client/assets/`：运行时读取依赖材质和模型，应用有限调色、裁切、程序笔画及自有拟合规则；原生音效仅通过资源 ID 引用，没有复制音频。

## 资源分发范围

仓库和 JAR 只保留 8 张自有纹理：`block/casing`、三种 `block/core_*` 与四张 `entity/chamber/arcane_runes_*`（包括可选材质通道）。所有此前复制或改色的上游 PNG、动画元数据、OBJ 和派生模型数据均从公开资源中移除，改为运行时来源引用和内存转换。

变换规格、原始图像的摘要和比对结果不包含完整源图布局、像素索引表或压缩素材载荷。相关材料的原权利仍属上游；这种分发组织方式不授予任何人转发原模组或原素材的权限，也不声称获得了上游的额外授权。

## 构建工具

Gradle 8.8 Wrapper 来自 Forge 47.4.10 官方 MDK，适用 Apache-2.0 及 Wrapper 内附声明；完整文本和来源在 `gradle/wrapper/LICENSE`、`NOTICE`。ForgeGradle、MixinGradle 和 Mixin 注解处理器由构建工具获取，不内嵌入 Mod。

本项目自有部分保留原型的 All Rights Reserved 条款，文件标记及上述 MIT/LGPL 第三方许可例外优先，见 `LICENSE.md`。署名不替代许可。
