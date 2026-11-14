---
navigation:
  parent: introduction/index.md
  title: ME 线缆放置工具
  position: 3
  icon: meplacementtool:me_cable_placement_tool
categories:
  - meplacementtool tools
item_ids:
  - meplacementtool:me_cable_placement_tool
---

# ME 线缆放置工具

<ItemImage id="meplacementtool:me_cable_placement_tool" scale="4" />

ME 线缆放置工具专为快速布线设计，支持多种线缆类型和颜色，并提供多种放置模式。

## 功能特性

- **多种线缆类型**：支持玻璃、包层、智能、致密包层、致密线缆
- **多种放置模式**：
  - **直线模式**：快速铺设直线线缆
  - **平面填充**：在矩形区域内铺设线缆网络
  - **平面分支**：创建树状分支结构的线缆网络
- **网络集成**：通过 <ItemLink id="ae2:wireless_access_point" /> 连接到你的 ME 网络
- **撤销支持**：支持撤销最近的放置操作

## 操作指南

- **右键**：选择坐标
- **左键**：取消坐标选定
- **按 G 键**：打开配置界面
- **手持工具 Ctrl + 左键**：撤销上一次放置操作
- **将工具放入 ME 无线接入点**：链接到 ME 网络

### 未插入光谱的钥匙

![未插入光谱的钥匙](../../assets/me_cable_placement_tool_gui_no_key.png)

- **手动染色**：如果副手持有染料，放置线缆时会消耗染料进行自动染色

### 插入光谱的钥匙后

![插入光谱的钥匙后](../../assets/me_cable_placement_tool_gui_with_key.png)

- **颜色选择**：可以在配置界面自由选择所有 16 种颜色
- **自动染色**：放置出来的线缆会自动变为选定的颜色，无需消耗染料
- **按 A 键**：收藏当前选中的颜色（可在按键绑定中修改）

## 合成配方

<RecipeFor id="meplacementtool:me_cable_placement_tool" />
