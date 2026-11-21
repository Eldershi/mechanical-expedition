# 1.21.1 多方块设施美术清单

范围以 `v1.21.1-test.3` 为准，涵盖地月设施与工业设施的专用视觉资源。在目标客户端核对条目对应的界面和游戏内表现后勾选。模型和纹理可以在同组内共用，每个注册 ID 都要核对。

| 待核对范围 | 数量 |
| --- | ---: |
| 多方块控制器 | 17 |
| 专用建材、地面航标和碳电极 | 39 |
| 独立物品图标 | 36 |
| 流体外观 | 2 |
| 流体桶图标 | 2 |

## 工业设施外观

合金炉、液压机、工业高炉、大型电解池和自动贸易终端使用专用控制器模型、工作动画、机器 GUI 和 JEI 配方样式。物品和 FE 接口在五座机器的控制器上，流体接口以实际配置为准。可共用的锅炉、覆板、支撑、护栏和灯具随方块 ID 使用同一套外观。

[接口和资源构建说明](../development/ports/1.21.1/world-server/brass-industry/README.md#工业设施外观)

## 控制器和运行表现

每座控制器都要检查放置模型、物品栏图标、JEI 控制器合成图、Multiblocked2 立体结构预览以及设备配方页的图标。每条列出对应的运行表现验收点。压头动作和其他尚待适配的机制在对应玩法接入后验收。

### 地月设施

- [ ] **轨道卫星收发站** `expedition_space:satellite_relay`。天线扫描、登记成功、收到月球地牢坐标。
- [ ] **货运火箭发射台** `expedition_space:freight_launchpad`。接收发货请求、发射、货物到达。
- [ ] **太空电梯** `expedition_space:space_elevator`。乘坐或运货、升降、到站。
- [ ] **轨道空投炮** `expedition_space:orbital_drop_cannon`。发射、落点受阻等待、投送成功。
- [ ] **异界门** `expedition_space:other_gate`。满足开门条件、门体启动、通过、复位。

### 工业设施

- [ ] **巨型粉碎机** `expedition_industry:huge_crusher`。进料、粉碎和多路出料。
- [ ] **合金炉** `expedition_industry:alloy_furnace`。液体燃烧室热态、熔炼、出液。
- [ ] **液压机** `expedition_industry:hydropress`。装料、压头动作和复位、成品排出。
- [ ] **爆破压缩机** `expedition_industry:blasting_compressor`。TNT 装填、机内压制、成品排出。
- [ ] **工业高炉** `expedition_industry:shaft_furnace`。高炉热态、半成品出料、钢水排出。
- [ ] **大气冷凝机** `expedition_industry:condenser`。冷凝剂供给、开始冷凝、收集流体。
- [ ] **大型电解池** `expedition_industry:electrolytic_cell`。供电、电解气泡和多路流体输出。
- [ ] **无限取液池** `expedition_industry:infinity_fetching_pool`。种液输入、运转、流体输出。
- [ ] **电流体谐振塔** `expedition_industry:electro_hydro_resonant_tower`。充能、电极工作、电流体或物品产出。
- [ ] **电子管计算机控制器** `expedition_industry:electron_tube_computer`。运行指示、数据产出、写盘。
- [ ] **大型差分机** `expedition_industry:large_difference_engine`。差分齿轮运动、压缩数据、写盘。
- [ ] **自动贸易终端** `expedition_industry:trading_station`。接收订单、卖出结算、买入交货。

## 专用方块和方块物品

同一个斜梁和支架要检查朝向与翻转，转动件要检查三个轴向，栏杆要检查连接，台阶和楼梯要检查各自的摆放状态。灯要核对发光面，隔热窗要核对透明层。

### 航天建材、航标和电极

- [ ] 地面收货航标 `expedition_space:surface_beacon`
- [ ] 铆接航天框架 `expedition_space:riveted_frame`
- [ ] 航天结构板 `expedition_space:structural_panel`
- [ ] 舱外隔热窗 `expedition_space:insulated_window`
- [ ] 碳电极 `expedition_space:carbon_electrode`

### 锅炉和工业覆板

- [ ] 黄铜锅炉 `design_decor:brass_boiler`
- [ ] 大型黄铜锅炉 `design_decor:brass_boiler_large`
- [ ] 黄铜锅炉结构件 `design_decor:brass_boiler_structure`
- [ ] 铸铁锅炉 `design_decor:cast_iron_boiler`
- [ ] 大型铸铁锅炉 `design_decor:cast_iron_boiler_large`
- [ ] 铸铁锅炉结构件 `design_decor:cast_iron_boiler_structure`
- [ ] 铜锅炉 `design_decor:copper_boiler`
- [ ] 工业铁锅炉 `design_decor:industrial_iron_boiler`
- [ ] 大型工业铁锅炉 `design_decor:industrial_iron_boiler_large`
- [ ] 工业铁锅炉结构件 `design_decor:industrial_iron_boiler_structure`
- [ ] 金锅炉 `design_decor:gold_boiler`
- [ ] 大型金锅炉 `design_decor:gold_boiler_large`
- [ ] 金锅炉结构件 `design_decor:gold_boiler_structure`
- [ ] 工业覆板 `design_decor:industrial_plating_block`
- [ ] 工业金块 `design_decor:industrial_gold_block`

### 梁、支架、栏杆和灯

- [ ] 金属支架 `design_decor:metal_support`
- [ ] 斜置金属支架 `design_decor:diagonal_metal_support`
- [ ] 斜置金属梁 `design_decor:diagonal_girder`
- [ ] 装饰格栅 `design_decor:ornate_grate`
- [ ] 铁栏杆 `design_decor:iron_railing`
- [ ] 黄铜栏杆 `design_decor:brass_railing`
- [ ] 铜栏杆 `design_decor:copper_railing`
- [ ] 安山探照灯 `design_decor:andesite_floodlight`
- [ ] 黄铜灯 `design_decor:brass_lamp`
- [ ] 铜灯 `design_decor:copper_lamp`

### 传动件和集装箱

- [ ] 工业齿轮 `design_decor:industrial_gear`
- [ ] 大型工业齿轮 `design_decor:industrial_gear_large`
- [ ] 赭金粉碎轮 `design_decor:ochrum_crushing_wheel`
- [ ] 粉碎轮装配件 `design_decor:crushing_wheel_controller`
- [ ] 红色集装箱 `design_decor:red_container`
- [ ] 绿色集装箱 `design_decor:green_container`

### 黄铜砖、台阶和楼梯

- [ ] 黄铜砖 `create_things_and_misc:brass_bricks`
- [ ] 黄铜砖台阶 `create_things_and_misc:brass_brick_slab`
- [ ] 黄铜砖楼梯 `create_things_and_misc:brass_brick_stairs`

## 独立物品图标

同系物品要能在 JEI 和背包里一眼区分，例如锡、铝和黄铜硬盘，各色电路板，各级插件，货运载具和运载火箭，以及成品差速器和未完成件。

### 航天作业与护甲升级

- [ ] 卫星 `expedition_space:satellite`
- [ ] 运载火箭 `expedition_space:carrier_rocket`
- [ ] 货运控制器 `expedition_space:freight_remote`
- [ ] 可复用货运载具 `expedition_space:freight_module`
- [ ] 月球异常凭据 `expedition_space:lunar_signature`
- [ ] 气密生命维持模块 `expedition_space:life_support_module`
- [ ] 气密耐热内衬 `expedition_space:thermal_lining`

### 数据、运算与电路

- [ ] 锡硬盘 `expedition_space:tin_hard_disk`
- [ ] 铝硬盘 `expedition_space:aluminum_hard_disk`
- [ ] 黄铜硬盘 `expedition_space:brass_hard_disk`
- [ ] 电子管计算机 `expedition_space:electron_tube_computer`
- [ ] 黄绿色电路板 `expedition_space:lime_circuit_board`
- [ ] 品红色电路板 `expedition_space:magenta_circuit_board`
- [ ] 二阶矩阵 `expedition_space:matrix_2`
- [ ] 电路板 `expedition_industry:circuit_board`
- [ ] 千字节数据 `expedition_industry:data_kib`
- [ ] 兆字节数据 `expedition_industry:data_mib`

### 航天构件和异界门用料

- [ ] 轻质复合板 `expedition_space:light_composite_plate`
- [ ] 效能插件Ⅰ `expedition_space:efficiency_module`
- [ ] 产能插件Ⅱ `expedition_space:productivity_module_2`
- [ ] 电流体电容 `expedition_space:electro_hydro_capacitor`
- [ ] 谐振原虫 `expedition_space:mycetozoan`
- [ ] 未知原型 `expedition_space:unknown_prototype`
- [ ] 流体构件 `expedition_space:fluid_mechanism`
- [ ] 高速装罐机 `createandesiteabound:filling_machine`

### 传动、工业耗材与产物

- [ ] 差速器 `expedition_industry:differential`
- [ ] 未完成的差速器 `expedition_industry:incomplete_differential`
- [ ] 电气齿轮组 `expedition_industry:electric_gear`
- [ ] 行星齿轮组 `expedition_industry:planetary_gear`
- [ ] 聚合物锭 `expedition_industry:polymer_ingot`
- [ ] 节能插件Ⅱ `expedition_industry:efficiency_module_2`
- [ ] 半成品钢 `expedition_industry:semi_finished_steel`
- [ ] 铝渣 `expedition_industry:aluminum_slag`
- [ ] 石墨粉 `expedition_industry:graphite_dust`
- [ ] 冷凝剂 `expedition_industry:coolant`
- [ ] 贸易代币 `expedition_industry:trade_credit`

## 流体和桶

- [ ] 液态空气 `expedition_industry:liquid_air`。核对静态与流动态纹理、透明度、罐体及 JEI 显示。
- [ ] 液态空气桶 `expedition_industry:liquid_air_bucket`。核对物品栏与 JEI 图标。
- [ ] 电流体 `expedition_industry:electro_hydro_fluid`。核对静态与流动态纹理、透明度、罐体及 JEI 显示。
- [ ] 电流体桶 `expedition_industry:electro_hydro_fluid_bucket`。核对物品栏与 JEI 图标。


## 游戏内验收

- [ ] JEI 搜索结果、3×3 合成图、加工配方页及催化剂图标都引用新资源。差速器的原生序列组装页要能区分底件、三步的投入物、未完成件和成品。
- [ ] Multiblocked2 在各层、各朝向显示正确模型。整机预览同时核对机械动力的齿轮、传动轴和流体设备，Functional Storage 的抽屉，以及 Ad Astra 的航天原件等共享部件的视觉衔接。
- [ ] FTB 地月任务的控制器、供氧模块和月球异常凭据图标正常。设备菜单中的物品槽、储液槽、功率条和进度条在界面里清晰可读。
- [ ] 在游戏内核对待机、运行、完成、堵料或断电的可见反馈。跨维度发射、到货、乘坐、投送与异界门特效按服务端事件同步。联机时检查操作者和旁观玩家看到的状态。
- [ ] 测试角色手持和掉落显示，以及玩家使用默认界面比例时的清晰度。实景和 JEI 以相同构建核对。

## 配置入口

- [地月控制器与配套资源](../development/ports/1.21.1/world-server/space/overlay/kubejs)
- [工业控制器与配套资源](../development/ports/1.21.1/world-server/brass-industry/overlay/kubejs)
- [地月逐格结构定义](../development/ports/1.21.1/world-server/space/structures.json)
- [工业逐格结构定义](../development/ports/1.21.1/world-server/brass-industry/structures.json)
