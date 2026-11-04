# AGENTS.md — Dummy-Robot 复刻项目

本文件供在该仓库工作的 AI/自动化代理使用。回答或修改项目内容前，必须先按下面顺序获取上下文，不要仅凭聊天片段重新猜测项目状态。

## 一、必读顺序

1. 先读 [项目最新进展](notes/项目最新进展.md)：确认当前板卡状态、阻塞项和下一步。
2. 再读本文件的“问题 → 文件索引”，只打开与当前任务有关的文件。
3. 涉及历史原因、某天做过什么时，读 [每日工作概览](notes/每日工作概览.md)。
4. 涉及硬件测量、故障证据或具体测点时，读 [七块板测试记录](notes/七块板测试记录.md)。
5. 仍无法定位资料时，读 [PROJECT_INDEX.md](PROJECT_INDEX.md) 的第四节“问题 → 文件速查表”和第五节“已知坑与易误判点”，不要默认通读整份大索引。
6. [CLAUDE.md](CLAUDE.md) 是原有项目入口和关键提醒；其中“项目现状”可能晚于或早于实际进展，发生冲突时以“项目最新进展”和具体测试记录中的新证据为准。

路径简写：文档中的 <V2> 指 source/1.Dummy V2任同学整理。路径含空格和中文，命令行中必须完整引用。

## 二、当前最高优先级

- REF：先修 3.3 V 启动与 VCAP 异常。U3、C20 已换，旧 L2 暂时回装；保持复位时 C10 为 3.3 V，但 C34/C35 为 1.71 V，U12 发热。禁止长时间上电、提高限流或直接升到 24 V。
- 42-3：U5（SN65HVD232DR）和 U3（STM32F103CBT6）在 24 V 误接事故中损坏，等待一起更换。
- 42-1、42-2：硬件可用，但需要重烧含 CAN 死锁修复的新固件。
- 35-1、35-2、35-3：当前均已通过上电和烧录，可作为后续对照板。

完整状态和操作顺序见 [项目最新进展](notes/项目最新进展.md)。

## 三、硬件排障工作方式

1. 用户已确认的接线、档位和重复测量不要反复追问；直接沿原理图和已知读数推进下一步。
2. 优先使用供电分段、断电阻值、二极管档、低压限流注入和对照板电压定位。只有证据已经把故障隔离到器件或支路时，才建议拆焊。
3. 每一步都要明确：
   - 表笔/电源正负接哪里；
   - 使用什么档位或电压、限流；
   - 正常范围；
   - 不同结果分别意味着什么；
   - 下一步去哪测。
4. 蜂鸣不等于短路。必须结合网络、芯片内部结构、阻值/二极管值和上电电压判断。
5. 不能把限流导致的输入掉压当成器件正常工作电压。记录电压时同时记录电源是 CV 还是 CC。
6. 对 REF 继续排障前，先读 [七块板测试记录](notes/七块板测试记录.md) 的“四·二”和“四·三”，不要从头重复 USB、U11、U3、C20、NRST 或 VCAP 已做过的测试。
7. 任何 24 V 测试都应在低压缓升和关键电源轨通过后进行；电机相线只允许断电插拔。

## 四、三个最容易答错的项目事实

1. 减速比、关节限位、方向位和部分连杆长度有两套互相冲突的值：6.Docs/DH参数 图片与 dummy_robot.cpp 源码不一致。回答时必须说明来源和冲突，不能只报一套。
2. 只有 REF 主控使用 FreeRTOS；Motor-42 和 Motor-35 是裸机主循环加定时器中断。减速比也不在电机固件中，而在主控 dummy_robot.cpp。
3. 执行阶段以 [Dummy_V2复刻路线图](notes/Dummy_V2复刻路线图.md) 为框架，但其 2026-09-29 的“你现在在哪”已经过期；实时状态以 [项目最新进展](notes/项目最新进展.md) 为准。

## 五、问题 → 文件索引

### 当前状态、历史与计划

| 问题 | 文件 |
|---|---|
| 现在做到哪、有哪些阻塞、下一步是什么 | [notes/项目最新进展.md](notes/项目最新进展.md) |
| 每天做过什么、判断如何演变 | [notes/每日工作概览.md](notes/每日工作概览.md) |
| 长期阶段、学习路线、预算与安全底线 | [notes/Dummy_V2复刻路线图.md](notes/Dummy_V2复刻路线图.md) |
| 全仓库资料定位、已知坑 | [PROJECT_INDEX.md](PROJECT_INDEX.md) |
| 原有 Claude 项目说明 | [CLAUDE.md](CLAUDE.md) |

### PCB 焊接、测试与维修

| 问题 | 文件 |
|---|---|
| 七块板逐板状态、测量值、维修、烧录、REF 故障 | [notes/七块板测试记录.md](notes/七块板测试记录.md) |
| 统一的万用表和上电步骤 | [notes/七块板万用表与上电测试指南.md](notes/七块板万用表与上电测试指南.md) |
| Motor-42 / Motor-35 焊接顺序和风险 | [notes/电机驱动板焊接指南.md](notes/电机驱动板焊接指南.md) |
| Motor-42 原理图、接口和学习笔记 | [notes/motor42驱动板.md](notes/motor42驱动板.md) |
| REF 原理图、接口、电源和焊接笔记 | [notes/ref主控板.md](notes/ref主控板.md) |
| LedRing 焊接 | [notes/LedRing焊接指南.md](notes/LedRing焊接指南.md) |
| 实际采购器件的交互式查找 | [notes/我的采购BOM_交互版.html](notes/我的采购BOM_交互版.html) |

### BOM、采购与库存

| 问题 | 文件 |
|---|---|
| 当前实际采购、订单、数量和账面余量 | [实际采购iBOM_Dummy整机.xlsx](source/1.Dummy%20V2任同学整理/5.Bom/实际采购iBOM_Dummy整机.xlsx) |
| 任同学整机 BOM | [dummy V2版本_bom.xlsx](source/1.Dummy%20V2任同学整理/5.Bom/dummy%20V2版本_bom.xlsx) |
| Ryan 复刻 BOM | [Dummy_V2_BOM_Ryan_v1.1.xlsx](source/1.Dummy%20V2任同学整理/5.Bom/Dummy_V2_BOM_Ryan_v1.1.xlsx) |
| 上游整板 BOM | [dummy_boards_bom.xlsx](source/dummy/hardware/dummy_boards_bom.xlsx) |

采购表中的余量不等于现场库存。回答“是否还有备件”时，先看采购表和 BOM 确认型号/理论数量，再明确提示以用户现场实物为准。

### 固件与构建

| 问题 | 路径 |
|---|---|
| REF 主控固件 | source/1.Dummy V2任同学整理/2.Firmware/dummy-ref-core-fw/ |
| Motor-42 固件 | source/1.Dummy V2任同学整理/2.Firmware/dummy-42motor-fw/ |
| Motor-35 固件 | source/1.Dummy V2任同学整理/2.Firmware/dummy-35motor-fw/ |
| 已验证构建产物 | source/1.Dummy V2任同学整理/2.Firmware/build/ |
| 主控整机参数与减速比 | <V2>/2.Firmware/dummy-ref-core-fw/Robot/instances/dummy_robot.cpp |
| 电机 CAN 协议 | <V2>/2.Firmware/dummy-42motor-fw/UserApp/protocols/interface_can.cpp |
| REF 启动流程 | <V2>/2.Firmware/dummy-ref-core-fw/UserApp/main.cpp |

固件关键现状：

- Motor-42 / Motor-35 的 CAN 失败死锁已修复，但 AutoBusOff 仍关闭。
- REF 为了在未接电机板时继续启动，源码已临时注释 dummy.Init()；接整机前必须恢复或实现带超时的根治方案。
- REF CCMRAM 已占满 64 KB；修改任务栈或静态对象前先看 map。

### 原理图、PCB 与制造文件

| 问题 | 路径 |
|---|---|
| Altium 原理图和 PCB | <V2>/1.Hardware/*/PCB源文件/ |
| 可用 Gerber | source/dummy/hardware/*/*-gerber.zip |
| 板卡手册与整板 BOM | source/dummy/hardware/dummy_boards_manual.pdf、dummy_boards_bom.xlsx |
| PCB 实物参考图 | <V2>/6.Docs/PCB/ |
| 引脚定义 | <V2>/6.Docs/Pins definations.pdf |
| 线束连接图 | <V2>/6.Docs/Cable_connection.pdf |

Motor-42 在 <V2> 内的同名 Gerber 包缺钻孔文件，投板必须优先使用 source/dummy/hardware/motor42/motor42-gerber.zip。

### 机械、3D 打印与 CNC

| 问题 | 文件/路径 |
|---|---|
| 当前定稿打印/CNC 数量和缺失件尺寸 | [notes/3D打印与CNC清单.md](notes/3D打印与CNC清单.md) |
| 当前选定机械版本 | <V2>/4.Model/Dummy V2 版本 视频款/ |
| 3D 打印 STL | 视频款/3D打印STL文件/ |
| CNC STEP | 视频款/CNC加工STEP文件/ |
| 整机装配体 | 视频款/Dummy-B v2装配体.step |
| 二维工程图 | 视频款/Dummy-B 2D工程图/ |

视频款和木子版结构件几何不同，不能混装。J1 与基座如果使用改版，必须成对更换。

### 学习资料

| 问题 | 文件 |
|---|---|
| 江协 STM32 课程 | [嵌入式学习/STM32课程字幕_P04-P49_合并版.md](嵌入式学习/STM32课程字幕_P04-P49_合并版.md) |
| 尚硅谷 FreeRTOS | [嵌入式学习/尚硅谷FreeRTOS教程字幕/FreeRTOS入门教程_校对版.md](嵌入式学习/尚硅谷FreeRTOS教程字幕/FreeRTOS入门教程_校对版.md) |
| 尚硅谷 PCB 课程 | [嵌入式学习/尚硅谷PCB设计教程字幕/PCB设计教程_校对版.md](嵌入式学习/尚硅谷PCB设计教程字幕/PCB设计教程_校对版.md) |
| 任同学焊接视频整理 | [notes/任同学视频字幕/README.md](notes/任同学视频字幕/README.md) |
| 视频焊接要点 | [notes/任同学视频字幕/焊接要点清单.md](notes/任同学视频字幕/焊接要点清单.md) |

字幕是自动识别文本，器件名和专业术语必须结合原理图/BOM校正后再引用。

## 六、文档维护规则

发生实质进展时按以下边界同步：

1. 当前有效状态、板卡矩阵、阻塞项或下一步改变：更新 notes/项目最新进展.md。
2. 当天完成项、排障过程、判断变化：在 notes/每日工作概览.md 追加当天条目。
3. 板级测量、测点、返修证据：更新 notes/七块板测试记录.md。
4. 长期阶段或路线改变：更新 notes/Dummy_V2复刻路线图.md。
5. 新增重要文件或旧路径失效：更新本文件的索引；需要全仓库级别检索时再更新 PROJECT_INDEX.md。

不要把同一段详细排障过程复制到多个文件：测试记录保留证据，项目最新进展只保留结论，每日概览保留时间线。

## 七、版本控制与文件安全

- 工作区可能已有用户未提交的修改；修改前先检查状态，不覆盖或清理无关文件。
- 不删除 tmp、History、构建产物或用户文件，除非用户明确要求并确认范围。
- 对原理图、BOM、固件做结论时优先引用项目内原始文件，不以旧聊天回答代替文件证据。
- 修改后至少检查新文档链接、Markdown 基本格式和 Git diff；未获授权时不要自动提交或推送。
