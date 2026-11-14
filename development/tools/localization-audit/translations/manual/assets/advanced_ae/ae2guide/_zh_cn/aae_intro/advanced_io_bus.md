---
navigation:
  parent: aae_intro/aae_intro-index.md
  title: ME高级IO总线
  icon: advanced_ae:advanced_io_bus_part
categories:
  - advanced items
item_ids:
  - advanced_ae:advanced_io_bus_part
---

# ME高级IO总线

<GameScene zoom="8" background="transparent">
  <ImportStructure src="../structure/cable_advanced_io_bus.snbt"></ImportStructure>
</GameScene>

ME高级IO总线是与外部物品栏交互的强大工具，由<ItemLink id="advanced_ae:import_export_bus_part"/>与<ItemLink id="advanced_ae:stock_export_bus_part"/>融合而成，继承了两者的功能。此外，其基础速度是<ItemLink id="ae2:export_bus"/>的 8 倍。虽然需要一段时间才能达到全速，但完全升级后的速度极快。

## 输出

ME高级IO总线按照过滤设置输出物品，达到指定数量后便停止。界面左侧还可以设置是否维持物品库存数量。

## 输入

ME高级IO总线也会输入未被设为输出的物品。输入和输出操作分别计数，因此不会因持续执行某一种操作而阻塞另一种。启用数量维持后，总线会优先输入超过设定数量的物品；若仍有剩余操作次数，则继续输入未被过滤的物品。

<RecipeFor id="advanced_ae:advanced_io_bus_part"/>