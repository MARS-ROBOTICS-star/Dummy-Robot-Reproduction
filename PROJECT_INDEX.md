# Dummy-Robot 项目索引 (PROJECT_INDEX.md)

> **本文件的用途**:给 Claude Code 会话做文件检索用的导航地图。回答本项目的任何技术问题前,先查本文件定位目标文件,再去读该文件,避免全仓库 find/grep 摸索。
>
> 仓库根目录:`/home/lbz/Dummy-Robot/`
> 本文件内所有路径均为**相对于仓库根**的相对路径。
> **简写**:`<V2>` = `source/1.Dummy V2任同学整理`(项目本体目录,路径含空格与中文,shell 中务必加引号)。
> 生成日期:2026-10-08 | 索引文件总数:4436(不含 `.git`)
> **2026-10-08 已执行一次清理**,回收约 2.8 GB(详见「五、已知坑」F 节)。
> **2026-10-12 新增** `source/dummy/` —— Gitee 上游仓库 `switchpi/dummy` 的本地克隆(**仅 auk 分支**,3290 文件 / 180 MB)。与 `<V2>/` 的全面比对结论、目录索引见**第十二章**;新增的 4 条坑见「五、已知坑」G 节。
>
> **2026-10-12 版本定稿**:**PCB 一律用 auk 的 Gerber(= V1.01),结构件一律用「Dummy V2 版本 视频款」**。判定证据、取用表、文件黑名单见**第十三章**。
>
> **怎么用这份文件**:本文件约 250 KB,**不要全文通读**。先看「四、问题 → 文件 速查表」和「五、已知坑」,定位到章节后再跳读该章节;或直接 `grep` 关键词。每个章节末尾都有自己的「典型问题 → 去哪个文件」映射表。
>
> **可信度说明**:本索引由 6 个子代理实际打开文件、读代码、看图、解压 BOM、跑 diff 得出,不是从文件名推断。但**索引不等于实物**——凡涉及参数数值的结论,都标注了来源文件;参数图与源码存在大面积冲突(见「五、已知坑」第 1 条),任何数值在上板前都需实测确认。

## 目录

- 一、项目是什么
- 二、系统架构速览
- 三、顶层目录地图
- **四、问题 → 文件 速查表**(先看这里)
- **五、已知坑与易误判点**(务必先看)
- 六、项目文档资料(含规划纲领文档,优先阅读)
- 七、主控板固件 dummy-ref-core-fw
- 八、关节电机固件(42 / 35)
- 九、硬件 / 3D模型 / BOM
- 十、上位机软件与 ESP32 固件
- 十一、学习资料与调研产出(非 Dummy 本体)
- 十二、上游克隆 `source/dummy/`(Gitee auk 分支)
- **十三、版本判定与打板选型(已定稿)**(打板/打印前必看)

---

## 一、项目是什么

Dummy 是稚晖君(peng-zhihui)开源的桌面级 **6 自由度机械臂**。本仓库是"任同学整理"的 **Dummy V2** 版本资料包,硬件在原版基础上由**木子晓文**改版(见 `source/1.Dummy V2任同学整理/1.Hardware/README.md`)。

上游参考:https://github.com/peng-zhihui/Dummy-Robot

**V2 相对原版的硬件改动**(摘自 `1.Hardware/README.md`):
1. 简化设计,更适合量产
2. 所有 1.0mm 连接器改为 1.5mm 插针(修原版连接器易脱落)
3. 删除 base 板,集成到主板
4. 增加 switching LDO,供电电流最大 2A(修原版 MCU LDO 电流过小、温度过高)
5. LED Ring、蜂鸣器控制从 ESP32 移到 STM32 MCU
6. 更合理的布局、降低量产成本

本仓库不只是上游资料的镜像,还包含**用户自己的复刻规划文档、一次自动化复刻审计、以及嵌入式学习资料**。

---

## 二、系统架构速览

机械臂由**三类板子**构成,通过 **CAN 总线**互联:

| 板子 | MCU | 软件形态 | 角色 |
|---|---|---|---|
| **主控板** ref-controller | STM32F405RGT6 | **FreeRTOS** + CMSIS-RTOS v2 | 运动学解算、指令解析、OLED/IMU/RGB、对外 USB/UART 通信 |
| **42 关节电机板** ×N | STM32F103CBT6 | **纯裸机**(无 RTOS) | 闭环步进控制、编码器标定、CAN 从机 |
| **35 关节电机板** ×N | STM32F103CBT6 | **纯裸机**(无 RTOS) | 同上,小规格关节 |
| ESP32 模块 | ESP32 | (见软件章节) | 网络/IoT,V2 已把灯环蜂鸣器控制移走 |

> **关键认知**:只有主控板用 FreeRTOS。电机固件是裸机 + 定时器中断跑控制环。回答"RTOS 怎么用"类问题时不要去翻电机固件。

**主控板 FreeRTOS 任务布局**(`.../dummy-ref-core-fw/UserApp/main.cpp` + `Core/Src/freertos.c`):

| 任务 | 优先级 | 栈 | 作用 |
|---|---|---|---|
| `ControlLoopFixUpdateTask` | **Realtime** | 2000 | 200Hz 定频控制环,下发关节指令 |
| `usbIrqTask` | AboveNormal | 500 | USB 中断延迟处理 —— ⚠️ **实际为死任务,信号量从未被 give** |
| `ControlLoopUpdateTask` | Normal | 2000 | 从命令队列取指令并解析 |
| `OledTask` | Normal | 2000 | IMU 读取 + OLED 刷新 |
| `RGBTask` | Normal | 2000 | 灯效 |
| `defaultTask` | Normal | 2000 | 初始化后调用 C++ `Main()` 然后自删除 |

同步机制:
- **任务通知**:TIM7 中断 `vTaskNotifyGiveFromISR` → 控制环任务 `ulTaskNotifyTake(pdTRUE, portMAX_DELAY)`。这是实时性核心。
- **7 个信号量**:`sem_usb_irq` / `sem_uart4_dma` / `sem_uart5_dma` / `sem_usb_rx` / `sem_usb_tx` / `sem_can1_tx` / `sem_can2_tx`
  - ⚠️ 其中 **`sem_usb_irq` 全工程没有任何 `osSemaphoreRelease`**,`OTG_FS_IRQHandler` 直接调 `HAL_PCD_IRQHandler`。因此 `usbIrqTask` 永久阻塞,**是死任务**(详见第七章)。
- **1 个消息队列**:`osMessageQueueNew(16, 64, nullptr)` 命令 FIFO(`Robot/instances/dummy_robot.h`)
- 堆:`configTOTAL_HEAP_SIZE = 65536`(CCRAM)。源码注释称"已用 60K/64K",但 **`freertos_inc.h` 的注释值与代码实值不符**(注释 commTask 48000/oled 4000/ctrlLoopFix 4000,实际 45000/2000/2000),该余量结论需按实值重算。
- 中断门限:`configLIBRARY_MAX_SYSCALL_INTERRUPT_PRIORITY = 5`(数值更小=更高优先级的中断不可调用 FreeRTOS API)

---

## 三、顶层目录地图

| 目录 | 内容 | 文件数 |
|---|---|---|
| `source/1.Dummy V2任同学整理/` | **项目本体**(硬件/固件/软件/模型/BOM/文档) | 4159 |
| `source/dummy/` | **上游 Gitee 克隆**(auk 分支),`<V2>/` 的上游出处,见第十二章 | 3290 |
| `嵌入式学习/` | 尚硅谷 STM32 / FreeRTOS / PCB 三门课的字幕 | 191 |
| `workspace/` | B站视频调研工作区(video-understanding 技能产出) | 173 |
| `notes/` | `Dummy_V2复刻路线图.md` | 1 |
| `build/` | **空目录** | 0 |
| `logs/` | **空目录** | 0 |

`<V2>/` 顶层还直接放着 **5 份复刻方案文档 + 原作者使用指南**(约 1 MB),是项目的规划纲领,详见第六章开头。

`<V2>/` 内部:

| 子目录 | 内容 | 文件数 |
|---|---|---|
| `1.Hardware/` | 四块板的 PCB 工程与 Gerber | 57 |
| `2.Firmware/` | 三套 STM32 固件 + ESP32 + 源码注释版 | 3701 |
| `3.Software/` | 上位机:simple-cli / CLI-Tool / DummyStudio | 160 |
| `4.Model/` | 三套 3D 模型(原版/社区改版/视频款) | 157 |
| `5.Bom/` | `dummy V2版本_bom.xlsx` | 1 |
| `6.Docs/` | 参数图、引脚定义、接线图、复刻审计 | 73(其中审计目录占 53) |

---

## 四、问题 → 文件 速查表

`<V2>` = `source/1.Dummy V2任同学整理`。各章节末尾另有更细的映射表。

### 复刻计划 / 学习路径

| 问题 | 去哪 |
|---|---|
| 我现在该做什么?下一步? | **`notes/Dummy_V2复刻路线图.md`** —— 唯一有效的执行文件,明文声明旧方案仅作技术参考 |
| 完整的实验阶段划分(E0~E13) | `<V2>/Dummy_V2项目驱动复刻方案_PBL版.md` |
| 为什么要这么安排 / 技术依据 | `<V2>/Dummy_V2详细复刻方案_审计修订版.md`(G0~G7 Gate + D01~D20 + 34 条验收用例) |
| 项目科普、给外行讲 | `<V2>/Dummy_V2项目全景科普讲义.md` |
| 原作者怎么用这台机械臂 | `<V2>/dummy使用指南v1.3.pdf` |
| 有哪些阻塞项、风险 | `<V2>/6.Docs/复刻审计_2026-09-06/审计结论与证据.md`(A01~A14) |

### 参数与数值

| 问题 | 去哪 |
|---|---|
| 六轴减速比、关节限位、方向位 | **两套冲突值**:`<V2>/6.Docs/DH参数/dummy V2 版本 DH参数.png`(图) vs `<V2>/2.Firmware/dummy-ref-core-fw/Robot/instances/dummy_robot.cpp:20-33`(源码)。见「五、已知坑」第 1 条 |
| 逆解几何常量(L_BS/L_AM/...) | `dummy_robot.cpp` 顶部 + `Robot/algorithms/kinematic/6dof_kinematic.cpp` |
| 减速器扭矩/惯量/型号 | `<V2>/6.Docs/减速器参数/mini8_parameters.JPG`、`mini11_parameters.JPG`(MINIF08/MINIF11,各含 30 和 50 两档) |
| 电机 PID(DCE)参数 | ⚠️ **不在 `6.Docs/电机PID/`**(那是 PID 概念截图)。在 `<V2>/2.Firmware/dummy-42motor-fw/Ctrl/Motor/motor.cpp` 与 `UserApp/main.cpp`(DCE 200/80/300/250;35 板 kp=195)。**EEPROM 存值优先于代码默认值** |
| 运行限流 / 校准电流 | 1000 mA / 2000 mA(互相独立),来源审计 A05 |
| 控制环频率、细分 | 电机板 20 kHz、51200 细分步(`motor.cpp`);主控控制环 200 Hz(`UserApp/main.cpp` TIM7) |
| 晶振频率 | **电机板 12 MHz,REF 板 8 MHz**(实物照片 `6.Docs/PCB/m42.jpg`、`controller_bot.jpg` 丝印佐证) |
| 整机成本、物料清单 | `<V2>/5.Bom/dummy V2版本_bom.xlsx`(6 sheet;元器件 285 + 板费 110 元) |
| 板上到底有哪些芯片 | `<V2>/1.Hardware/*/Motor-42.html` 等交互式 BOM(LZString 压缩,需解压,见第九章脚本) |

### 接线与通信

| 问题 | 去哪 |
|---|---|
| P1/P2/P3 接口引脚定义 | `<V2>/6.Docs/Pins definations.pdf` + 第六章。P1/P2 = `+24V,+24V,GND,GND,CAN_L,CAN_H`;P3 = `UART_RX,TX,GND,SWDIO,SWCLK,GND` |
| 线束怎么接 | `<V2>/6.Docs/Cable_connection.pdf`。**仅 REF→J1 用同向线且需交换中间两根 CAN 线**,J1~J6 全用反向线 |
| CAN 节点号怎么设 | 拨码 J1~J6 = `0001`~`0110`。**第 4 位是终端电阻不是节点 ID** |
| 主控↔电机 CAN 协议帧格式 | `<V2>/2.Firmware/dummy-42motor-fw/UserApp/protocols/interface_can.cpp`(26 个命令码全列于第八章);主控侧 `dummy-ref-core-fw/Robot/actuators/ctrl_step/ctrl_step.cpp` + `UserApp/protocols/can_protocol.cpp`。`StdId = (nodeID<<7)｜cmd`,1 Mbps |
| 上位机 ASCII 命令格式 | `dummy-ref-core-fw/UserApp/protocols/ascii_protocol.cpp`。`>`=MoveJ `@`=MoveL `&`=关节 `!`=系统 `#`=调参 |
| CLI-Tool 怎么调用 | **`dummy0.robot.move_j(...)`**(对象树多一层 `robot`)。树定义在 `UserApp/protocols/cmd_protocol.cpp:MakeObjTree()` |
| USB VID:PID | `1209:0D32`(`dummy-ref-core-fw/USB_DEVICE/App/usbd_desc.c`) |

### 固件代码

| 问题 | 去哪 |
|---|---|
| 六轴逆解怎么实现 | `dummy-ref-core-fw/Robot/algorithms/kinematic/6dof_kinematic.cpp` |
| 整机状态机、指令模式 | `Robot/instances/dummy_robot.cpp/.h`(4 种 commandMode) |
| FreeRTOS 任务/信号量/队列 | `dummy-ref-core-fw/Core/Src/freertos.c` + `UserApp/main.cpp` + `UserApp/freertos_inc.h` |
| 闭环控制算法 | `dummy-42motor-fw/Ctrl/Motor/motor.cpp` |
| 梯形/S 曲线轨迹规划 | `dummy-42motor-fw/Ctrl/Motor/motion_planner.cpp` |
| 编码器标定流程 | `dummy-42motor-fw/Ctrl/Sensor/Encoder/encoder_calibrator_base.cpp`(标定区 0x08017C00 + 32K) |
| MT6816 磁编码器读取 | `Ctrl/Sensor/Encoder/mt6816_base.cpp` + `Port/mt6816_stm32.cpp` |
| TB67H450 驱动与电流输出 | `Ctrl/Driver/tb67h450_base.cpp` + `Port/tb67h450_stm32.cpp`(**实际 10 位分辨率**) |
| 带中文注释的源码解读 | `<V2>/2.Firmware/Dummy 源码注释/`(⚠️ 6 份里 5 份其实来自**主控**;3 份语法已损坏只能当文档读) |

### 硬件与机械

| 问题 | 去哪 |
|---|---|
| PCB 源文件(原理图/PCB) | `<V2>/1.Hardware/*/PCB源文件/*.PcbDoc` + `*.SchDoc`。**全部是 Altium,不是嘉立创EDA**。motor42/35/ref-controller **缺 `.PrjPCB`**,需手动建工程 |
| Gerber 制造文件 | `<V2>/1.Hardware/*/\*Gaber.zip`。⚠️ **Motor-42 缺 NC Drill,不能直接投板**(审计 A01) |
| 该用哪套 3D 模型 | **`<V2>/4.Model/Dummy V2 版本 视频款/`**(BOM 就是按它选型的) |
| 3D 打印件 / CNC 件 | `视频款/3D打印STL文件/` 与 `视频款/CNC加工STEP文件/`;木子版靠文件名含 `metal` 判断 |
| PCB 实物长什么样 | `<V2>/6.Docs/PCB/`(m42 / m35 / controller_top / controller_bot) |

### 学习资料

| 问题 | 去哪 |
|---|---|
| FreeRTOS 某知识点在第几讲 | `嵌入式学习/尚硅谷FreeRTOS教程字幕/FreeRTOS入门教程_校对版.md`(55 讲,文件名自带标题) |
| PCB 设计某知识点在第几讲 | `嵌入式学习/尚硅谷PCB设计教程字幕/PCB设计教程_校对版.md`(131 讲,**标题全是 NA,只能靠第十一章的讲次分组表定位**) |
| STM32 某外设在第几讲 | `嵌入式学习/尚硅谷STM32字幕/`(基础篇 194 讲 + 高级篇 135 讲) |
| 江协 STM32 课程(路线图指定) | `嵌入式学习/STM32课程字幕_P04-P49_合并版.md`(**是另一门课**,不属尚硅谷那套) |

### 上游克隆 / 版本溯源(`source/dummy/`)

| 问题 | 去哪 |
|---|---|
| 我的固件 baseline 是上游哪一版 | **auk 分支 `ba5c088`(2023-12-10)**。42/35 电机固件自那次提交起上游再未改动。溯源证据见第十二章第 1 节 |
| `<V2>/` 和上游到底差什么 | 第十二章第 1 节(全局内容哈希比对)+ 第 3/4 节(双向独有清单) |
| URDF / MoveIt 配置、仿真模型 | `source/dummy/ros2/`(**`<V2>/` 完全没有**),索引见第十二章第 5 节。⚠️ URDF 限位是占位值,见「五、已知坑」G 节第 1 条 |
| 关节质量 / 惯量张量 | `source/dummy/ros2/dummy_ws/src/dummy-ros2_description/urdf/dummy-ros2.xacro`(7 个 link 都有 `<mass>` + `<inertia>`)—— **全仓库唯一的动力学参数来源** |
| 减速器厂家去哪买 | `source/dummy/harmonic_reducer/README.md`(淘宝店铺链接) |
| 同步带怎么算长度/型号 | `source/dummy/bom/README.md`(misumi + gaigibelt 两个计算工具链接) |
| 接线图 / 引脚定义 PDF | 两处同一文件:`<V2>/6.Docs/Cable_connection.pdf`、`Pins definations.pdf` = `source/dummy/bbs_backup_files/bbs_backup.zip` 内的同名文件(内容哈希一致) |
| 板子 Gerber / 装配手册 | `source/dummy/hardware/`(3 个 gerber zip + `dummy_boards_manual.pdf` + `dummy_boards_bom.xlsx`,**`<V2>/` 没有手册和整板 BOM**) |
| 上游完整 PCB 工程在哪下 | 不在仓库里。`source/dummy/hardware/ref-controller/README.md` 指向论坛 `https://dummy.mbbs.cc/#/thread/detail/67` |
| **打板该用哪个文件** | **第十三章第 3 节取用表**。一句话:三块板全用 `source/dummy/hardware/*/\*-gerber.zip` |
| **3D 打印该用哪套结构件** | **第十三章第 5 节**。一句话:`<V2>/4.Model/Dummy V2 版本 视频款/` |
| 哪些硬件文件绝对不要用 | 第十三章第 4 节「文件黑名单」 |
| 怎么确认某个版图是不是 V1.01 | 第十三章第 2 节,看丝印 `Texts6` 流 + 过孔坐标指纹 |

---

## 五、已知坑与易误判点

> 这一节是本索引最该先读的部分。以下每条都在复刻或答题时**真实导致过错误判断**,按"会不会让你做错事"排序。

### A. 参数与资料层面

**1. ⚠️ 减速比等核心参数存在两套互相冲突的值,且两套都未经实物验收**

| 项 | `6.Docs/DH参数` 图 | 当前 REF 源码 |
|---|---|---|
| 减速比 | 50/50/50/50/50/**5** | 30/30/30/**24**/30/**50** |
| inverse 方向位 | false/true/true/true/true/true | true/false/true/false/true/true |
| 连杆长度 | 126.5/35/146/117/52/75.5 mm | 109/35/146/115/52/72 mm |

**J6 减速比差 10 倍,方向位 6 轴全不同。** 审计明确裁定两套都不是实物验收值。回答任何涉及减速比/限位/长度的问题,必须说明来源并提示此冲突,不要只报一个数。

**2. `6.Docs/电机PID/PID.png` 里没有任何项目参数** —— 目录名叫"电机PID",内容却是一张 ChatGPT 讲 PID 概念的截图。真实 DCE 参数在 `motor.cpp`,且**EEPROM 存值优先于代码默认值**,所以读代码也只能得到默认值。

**3. `DH参数.png` 不是 DH 参数表** —— 它是 `dummy_robot.cpp:20-33` 的 IDE 截图,只有 6 个求解器几何常量和关节配置,**没有标准 DH 的 α/θ 列**。不要据此声称"项目提供了 DH 参数表"。

**4. 读 `deepseek_*.md` 前必须先看审计第 3 节的误判裁定表** —— 那 5 份是子代理原始输出,主审复核后裁定了**14 处误判**。典型:子代理说电机板 HSE 是 8 MHz,实际 12 MHz(实物晶振丝印 `12.000` 独立佐证)。直接引用 `deepseek_*.md` 会传播错误结论。

**5. 审计快照已过期** —— `file_inventory.csv` 是 2026-09-06 的,不含此后新增的 `notes/`、`workspace/`、`嵌入式学习/`。重跑 `audit_inventory.py --verify` 报差异属正常。**注意:该脚本不带 `--verify` 会覆盖审计历史快照,不要随意运行。**

**6. 字幕全是 AI 自动轨,术语误识别严重** —— 实测 "STM32"→"sm 32"、"I2C"→"IPHONEC"、"51单片机"→"五一单片机"、"博世"→"博士"。引用字幕内容前必须校正术语。

### B. 架构认知层面

**7. 只有主控板用 FreeRTOS** —— 42/35 电机固件是**纯裸机** + 定时器中断(控制环在 `Ctrl/Motor/motor.cpp`,由 TIM 中断驱动)。被问"RTOS 怎么用"时不要去翻电机固件。

**8. 减速比不在电机固件里** —— 在主控 `<V2>/2.Firmware/dummy-ref-core-fw/Robot/instances/dummy_robot.cpp:21-28` 的 `CtrlStepMotor(hcan, id, inverse, reduction, min, max)` 构造参数里。去电机固件找减速比会白费功夫。

**9. 42 与 35 固件实质是同一套代码** —— `diff -rq` 只有 5 个文件不同,**唯一功能性差异是 `dce_kp`:42=200,35=195**。不要假设两者有结构性区别。

**10. `Dummy 源码注释/` 里 6 份文件有 5 份来自主控,不是电机固件** —— 它放在 `2.Firmware/` 下极易误判。且其中 3 份(`main.cpp`、`6dof_kinematic.cpp`、`motor.cpp`)已被粘贴过程破坏语法(有裸的 ```` ```cpp ````、`Copy code` 栅栏、缺收尾 `};`、多余括号),**无法编译,只能当文档读**。好消息:去注释后逐行比对,有效代码与当前主线一字不差。

**11. ESP32 模块是没被集成的旁支** —— `esp32-iot/firmware/` 其实是 mongoose 上游仓库快照,`examples/` 下 **3241 个文件全是上游示例,与 Dummy 无关**。真正属于 Dummy 的只有 uart-bridge 的 4 个文件。全仓库主控固件和上位机代码对它**零引用**,三个上位机工具没有一个走它的 TCP/WS/MQTT。

**12. `chatgpt_gui.py` 不是 LLM 控制 GUI** —— 文件名完全误导。实际是 PyQt5 的 MPU6050 加速度曲线窗口,而且它发的 `#GETMPU` 命令**在主控固件里不存在**,是已失效的实验代码。

**13. `芯片说明/MT6050陀螺仪.pdf` 文件名有错** —— 实为 **MPU-6050**(IMU)。注意与编码器芯片 **MT6816** 区分,两者容易混淆。

### C. 会烧板子 / 卡死硬件的代码缺陷

**14. 🔴 电机板 `CAN_Send` 失败直接进 `Error_Handler()`** —— 位置 `<V2>/2.Firmware/dummy-42motor-fw/Core/Src/can.c:181-187`,`Error_Handler` 实现在同固件 `Core/Src/main.c:171-179`(`__disable_irq()` + `while(1){}`)。总线繁忙、主控掉线、未接终端电阻时,**一次发送失败就让关节板永久卡死,必须断电重启**。配合 `AutoRetransmission = DISABLE` 风险更高。这是全项目最该先改的一处。

**15. 🔴 电机板链接脚本把整片 128K Flash 都给代码** —— `<V2>/2.Firmware/dummy-42motor-fw/STM32F103CBTx_FLASH.ld`,没为 0x08017C00 的 32K 编码器标定区保留。当前 Debug 构建约 73 KB,余约 22 KB,**代码膨胀后会静默覆盖标定数据**(审计 A06 同指此项)。

**16. 超前角补偿系数从未针对 MT6816 重标** —— `Motor::Controller::CompensateAdvancedAngle()` 自带注释 *"The code is for DPS series sensors, need to measured and renew for TLE5012/MT6816."* 这是已知遗留,影响高速性能。

**17. 电流分辨率实际是 10 位(~3.2 mA/LSB),不是 12 位** —— `tb67h450_base.cpp` 按 12 位 DAC 计算,但 Port 层 `>>2` 后写 TIM2 CCR。

**18. 主控 TIM2 被双重占用** —— `MX_TIM2_Init()` 配成编码器模式(PA15/PB3),而 `rgb.hpp` 用 `HAL_TIM_PWM_Start_DMA(&htim2, CH4)` 发 WS2812。PB10/PB11 也同时被 I2C2 和 soft_i2c 占用。

**19. `Middlewares/` 不是纯净上游** —— `usbd_cdc.h` 被加入第二组端点 `ODRIVE_IN_EP 0x83 / ODRIVE_OUT_EP 0x03`,`usbd_cdc.c` 被插入 `osSemaphoreRelease(sem_usb_tx)`。**升级 ST 库会破坏 USB 双端点功能**。

**20. `!STOP` 不是真急停** —— 审计 A07,且存在 0/0 路径。CAN 节点号 0~15 直接索引 7 元素数组(7~15 越界,A08)。命令解析与 64 字节队列存在越界(A11)。

### D. 死代码 / 失效功能(别在这上面浪费时间)

| 项 | 说明 |
|---|---|
| `usbIrqTask` | **死任务**,`sem_usb_irq` 全工程无任何 `osSemaphoreRelease` |
| `Robot/actuators/mintasca/`(约 5500 行) | **从未被实例化**,只被 `common_inc.h` 包含 |
| `Bsp/imu/mpu6050_1.hpp`(1062 行) | 是 `MPU6050.hpp` 的**逐字节完全副本**,无人 include |
| UART5 接收路径 | 复制粘贴 bug:对 UART5 数据调了 `uart4_stream_input.process_bytes()`;`OnUart5AsciiCmd()` 是空函数 |
| `rgb.Run(RGB::ALLOff)` | 空操作,switch 无该分支;`PureColor(ALLOff)` 里写的是 `r=0,g=10,b=0` |
| `AdcGetVoltage()` | 实现被改坏,真公式已注释,只返回 VREFINT 推算值 |
| `CAN1_RX0_IRQHandler` | 提前 `return`,`HAL_CAN_IRQHandler(&hcan1)` 成死代码 |
| 电机板 `TIM3_IRQHandler` / `EXTI9_5_IRQHandler` | 直接 `return`,STEP/DIR 功能预留未启用 |
| CAN `0x11` Set Node-ID | **永久失效**,每次上电被拨码值无条件覆盖 |
| `enableTempWatch` | `Main()` 里无条件置 false,EEPROM 值无效;`0x25` 查温度恒为 0,须先发 `0x7d` |
| `run_shell.py generate-code` | 引用未注册的 `args.template`/`args.output`,子命令不可用 |
| `ref_tool/shell.py` 的发现回调 | 死代码(生效的是 `fibre/shell.py` 那份),帮助文本还残留 `odrv0.` 字样 |

### E. 环境与工具链

**21. 35 电机固件在当前工具链下很可能编不过** —— 42 侧 4 个文件已于 2026-09-06 本地修补(`stdint-gcc.h` → `<stdint.h>`),35 保持上游原样未修。

**22. 四块板都是 Altium,且三块缺工程文件** —— motor42/motor35/ref-controller 都**没有 `.PrjPCB`**(只有 LedRing 有),Altium 里需手动建工程再 Add Existing。注意:`嵌入式学习/` 里的 PCB 课程教的是**立创EDA**,与本项目硬件不是一套工具。

**23. `.html` 是 InteractiveHtmlBom,器件型号 grep 不到** —— 数据在 `LZString.decompressFromBase64()` 里,必须解压(第九章有可复用脚本)。HTML title 写 "Interactive BOM for KiCAD" 只是该工具默认标题,工程实际是 Altium 导出。

**24. 多个 PDF 文本提取失败,必须看图** —— `Cable_connection.pdf` 只提取出 66 字节、`Pins definations.pdf` 82 字节、`LP2992.pdf` 8 字节,`4.Model` 的 19 个工程图多数 1~520 字节。**对这些文件 grep 无效,须用 Read 看图**。

**25. `木子晓汶版本3D模型/stps/` 是空目录** —— STEP 文件在上游另一个分支,根本没进本仓库。

**26. `视频款/3D打印STL文件/外壳A.stl` 与 `外壳B.stl` md5 完全相同**(`946699c9502030c081eec7f7f4ce8548`)—— 同一件两命名或漏传,打印前必须核对。

**27. "焊盘更改版" 改了什么无任何说明** —— 两个 `.rar` 里只有一个 `.PcbDoc`,无原理图无 Gerber,时间戳(2024-07-17)反而比 `PCB源文件/`(2024-03)新。要用得自己重新出光绘。

**28. 主控板原理图两套命名** —— 目录里是 `REF-Controller.SchDoc`,`REF_V1.01.zip` 里是 `Main.SchDoc`,哪个对应当前 `REF-Base.PcbDoc` 不明。

**29. DummyStudio 串口插件是 FREE 版,单次运行累计传输上限 1 MB** —— 高频下发关节角会撞上限,重启应用才能复位。

**30. `en.stsw-link004 (1).zip` 对 Linux 无用** —— 只含 Windows `setup.exe`(ST-LINK Utility v4.6.0, 2020)。本机是 Ubuntu。

**31. UART4 通道不支持 `#SET_DCE_K*` 和 `#REBOOT`** —— 所以**不能通过 ESP32 远程调 PID**。

**32. `esp32-iot/.../wifi.c:96` 会把明文 WiFi 密码打进串口日志** —— 连接失败时触发。SSID/密码由用户现场输入存 SPIFFS,源码无预置值。

### F. 清理记录(2026-10-08 已执行,回收约 2.8 GB)

**已删除**:

| 路径 | 回收 | 说明 |
|---|---|---|
| `workspace/stm32-roadmap-video-evidence/videos/**/source.mp4`(31 个) | ~2.6 GB | B 站原视频,可按 BVID 重新下载 |
| 同上目录的 `source.jpg` 封面(31 个) | ~11 MB | |
| `workspace/stm32-roadmap-video-evidence/gemini/chunks/` | ~145 MB | 切片缓存,Gemini 分析已失败无结果可保 |
| `<V2>/1.Hardware/motor42/PCB源文件/History/`(21 项) | ~48 MB | Altium 自动版本备份 |

**有意保留**(删 mp4 已达成腾空间目的,这些是文字依据,成本仅 3.2 MB):

- `videos/**/source.ai-zh.srt`(24 个,904 KB)—— 那次调研的 Gemini 分析**从未完成**(API 返 HTTP 402 额度耗尽),**所有结论实际是基于这些字幕得出的**,删了就无法核对报告引用
- `videos/**/source.info.json`(31 个)、`source.description`(31 个)—— B 站元数据,重跑时需要
- `deliverables/`(6 个文本,80 KB)—— 调研结论本体
- `urls.txt` / `downloaded.txt` / `.video-understanding-workspace.json` —— 重跑依据

**未清理、仍可按需处理**:

| 路径 | 体积 | 备注 |
|---|---|---|
| `<V2>/1.Hardware/motor35/PCB源文件/History/` | 4.3 MB | Altium 备份 2 份 |
| `<V2>/1.Hardware/ref-controller/PCB源文件/History/` | 5.9 MB | Altium 备份 |
| 零碎垃圾:`desktop.ini` ×2、`.DS_Store` ×6、SolidWorks `~$*` 锁文件 ×5、`__MACOSX/._*` ×1 | 极小 | 共 14 个,无价值 |

### G. 上游克隆 `source/dummy/` 相关(2026-10-12 新增)

**1. ⚠️ `ros2/` 里的 URDF 关节限位是占位值,不是真限位** —— `dummy-ros2.xacro` 六个关节的 `<limit>` **全部**是 `lower=-3.14 upper=3.14 effort=150 velocity=3.15`,`joint_limits.yaml` 里也只有速度限制、**position 限制整节缺失**。而主控源码 `dummy_robot.cpp:22-28` 的真实限位是 `-170~170 / -73~90 / 35~180 / -180~180 / -120~120 / -720~720`,六轴全都对不上。**不要把 URDF 当成「第三套参数」去调和那两套冲突值** —— 它是 SolidWorks 导出器的默认填充。

**2. 但 URDF 的连杆原点是有效的第三方交叉验证** —— 把 `<origin xyz>` 与 `dummy_robot.cpp:32` 的 `DOF6Kinematic(0.109, 0.035, 0.146, 0.115, 0.052, 0.072)` 对照:

| 参数 | 源码值(m) | URDF 原点(m) | 结论 |
|---|---|---|---|
| L2 | 0.035 | 0.035(J2 y) | **完全一致** |
| L3 | 0.146 | 0.146(J3 z) | **完全一致** |
| L5 | 0.052 | 0.052(J4 z) | **完全一致** |
| L1 | 0.109 | 0.100684(J1 z) | 差 8.3 mm |
| L4 | 0.115 | 0.127(J5 y) | 差 12 mm |
| L6 | 0.072 | 0.077(J6 y) | 差 5 mm |

三个完全吻合、三个差 5~12 mm。注意 URDF 原点含 x/y 偏置(如 J1 的 `x=-0.019225`),与一维连杆长度不是同一量纲,差值不能直接当误差。但这说明 **`6.Docs/DH参数` 图那套 126.5/35/146/117/52/75.5 与 URDF 更不吻合**(L1 差 25 mm),源码那套相对可信。仍需实测,见 A 节第 1 条。

**3. ⚠️ `<V2>/2.Firmware/esp32-iot/` 的 332 个符号链接已损坏,上游克隆里是完好的** —— `<V2>/` 那份里,本该是符号链接的文件变成了**内容为字面路径的 19~30 字节文本文件**(例:`firmware/examples/arduino/w5500-http/mongoose.c` 内容就是 `../../../mongoose.c` 这 19 个字符)。这是资料包在不支持符号链接的环境下打包/解压造成的。`source/dummy/esp32-iot/` 里同样这 332 个路径是**真正的符号链接**(git 模式位 `120000`),数量完全对得上。
**要编译 mongoose 相关的 ESP32 例程,必须用 `source/dummy/esp32-iot/`,用 `<V2>/` 那份会报找不到实现。** 这也是 `<V2>` 文件数(4137)比上游(3290)多出来的最大一块。

**4. `<V2>/1.Hardware/` 的 motor42/35 版图是「焊盘更改版」,不是上游 V1.01 原版** —— 三方比对(auk 松散 SchDoc / `bbs_backup.zip` 内 V1.01 包 / `<V2>/PCB源文件`)结果:

- `<V2>/PCB源文件/*.SchDoc` 与 `source/dummy/hardware/motor*/*.SchDoc` **逐字节相同**,是较新的一版
- `bbs_backup.zip` 内 `Motor-42_v1.01.zip` / `Motor-35-V1.01.zip` 是**较旧的归档**:motor42 的 `Drive.SchDoc`、`Port.SchDoc`、`Motor-42.PcbDoc` 与新版不同,motor35 的 `Port.SchDoc`、`Motor-35.PcbDoc` 不同
- 所以 **`<V2>/` 在原理图上不落后于上游**,两者同版;打板时按 `<V2>/` 或 `source/dummy/hardware/` 都可以,**不要用 zip 包里的 V1.01**

**5. `source/dummy/3d-model/stps/README.md` 指向一个已被删除的分支** —— 它写 "Refer to Fan-feature branch",但本机**只保留了 auk 分支**(2026-10-12 清理,`fetch` refspec 也已限定为只拉 auk)。该目录下除 README 外没有任何 step 文件。要取 step 模型得先恢复 refspec 再 fetch,命令见第十二章开头。

**7. ⚠️⚠️ `<V2>/1.Hardware/motor42/motor42 Gaber.zip` 没有钻孔文件,不能送厂** —— 该包 `.TXT`/`.DRR`/`.LDP` **全部缺失**(auk 同名包三者都有)。铜层、阻焊、板框都在,唯独没有 NC Drill,上传打样平台会报缺层或被按默认规则猜孔。**42 板必须用 `source/dummy/hardware/motor42/motor42-gerber.zip`**。详见第十三章。

**8. ⚠️ 两套结构件几何完全不同,混装必然装不上** —— `<V2>/4.Model/木子晓汶版本3D模型/`(= auk 的 `3d-model/`)与 `<V2>/4.Model/Dummy V2 版本 视频款/` 的 J1/J2J3/J4/J6/基座尺寸全不一致,J5 的拆分方式也不同(单件 vs 三件)。螺丝孔位与皮带长度均不通用。**本项目已定稿用视频款**,见第十三章第 5 节。

**6. `source/dummy/3d-model/README.md` 透露 J6 减速方案可能要改** —— 原文:"J6末端对精度要求不高,正在考虑用个成本更低的28行星减速器"。这与 A 节第 1 条的 **J6 减速比 50 vs 5 之争**直接相关 —— 说明 J6 传动方案本身在上游就没定稿,两套冲突值可能对应不同方案。采购 J6 减速器前务必确认。

---

## 六、项目文档资料

> 本节覆盖：`source/1.Dummy V2任同学整理/` 顶层的规划纲领文档与官方使用指南、`6.Docs/` 全部 74 个文件（图片/PDF/芯片手册/审计产出）、以及 `notes/Dummy_V2复刻路线图.md`。
> 所有路径相对仓库根 `/home/lbz/Dummy-Robot/`。路径含空格和中文，shell 中必须加引号。

---

### 项目规划纲领文档（优先阅读）

这是整个项目**最重要的一组文档**。共 4 份 md 方案 + 1 份官方 PDF 指南 + 1 份 README，加上仓库外的 `notes/Dummy_V2复刻路线图.md`。

#### 当前有效版本（先看这一条）

**`notes/Dummy_V2复刻路线图.md`（2026-09-29）是当前唯一的执行依据。** 它在正文开头明确写道：

> 旧方案（初稿、审计修订版、PBL 版、科普讲义）保留作技术参考，**执行以本文件为准**。

因此：

| 问题类型 | 该读哪一份 |
|---|---|
| **我现在该做什么 / 学习路径 / 阶段划分 / 预算** | `notes/Dummy_V2复刻路线图.md`（阶段 0～9） |
| **某个风险/缺陷的技术证据和源码行号** | `<V2>/6.Docs/复刻审计_2026-09-06/审计结论与证据.md`（A01～A14） |
| **工程化 SOP、验收用例、Gate 放行标准** | `<V2>/Dummy_V2详细复刻方案_审计修订版.md`（G0～G7、34 条验收用例） |
| **实验级操作细节（E0～E13 每个实验怎么做）** | `<V2>/Dummy_V2项目驱动复刻方案_PBL版.md` |
| **名词扫盲 / 整条控制链怎么走 / 原理科普** | `<V2>/Dummy_V2项目全景科普讲义.md` |
| **原作者的官方接线、命令、拨码说明** | `<V2>/dummy使用指南v1.3.pdf` |
| **历史背景：第一版设想是什么** | `<V2>/Dummy_V2复刻与学习方案_初稿.md`（已被取代，仅供溯源） |

#### 四份方案的演进关系

```text
初稿 (9/6 11:19)                    ← 第一版设想：首月单电机 + 逐周计划
   │  经「复刻审计_2026-09-06」全项目审计（A01～A14 风险）
   ▼
审计修订版 R1 (9/6 11:19)           ← 明文「替代初稿的执行安排」；加 G0～G7 Gate、D01～D20 工作单元、FW01～FW12 固件修复
   │  用户反馈：安全前置太重，看不到可见成果
   ▼
PBL 版 PBL-1 (9/6 12:35)            ← 明文「不再按 D01～D20 执行」；改为 E0～E13 实验驱动，先看到效果再补知识
   │  用户实际卡在 E0 之后：看不懂原理图、不懂 HAL 参数、无硬件
   ▼
复刻路线图 (9/29, notes/)           ← 当前有效版本：补上「阶段 0 打地基 + 阶段 1 纸上读懂」，
                                       把江协 STM32 课程正式纳入路线，硬件能力（焊接/PCB）从可选变必做，
                                       安全要求压缩成一页，并给出每阶段预算
```

关键点：

- **审计是为了产出「审计修订版」**，这一点在审计目录内可直接确认：`审计结论与证据.md` 开头即写「详细实施方案见项目根目录 Dummy_V2详细复刻方案_审计修订版.md」，而修订版的第 2 节「相对初稿的关键修改」逐行引用 A01～A14 作为依据。
- **PBL 版也产出于同一个审计目录**：它配套 `复刻审计_2026-09-06/PBL路线复核补充.md`（P01～P17 定点源码复核）和 `verify_pbl_plan.py`（文档自检脚本）。所以 `复刻审计_2026-09-06/` 同时是「修订版」和「PBL 版」两份方案的证据底座。
- **路线图取代了这些方案的执行地位，但没有取代它们的技术内容**。路线图附录 B「已知问题清单（通俗版）」只是 A01～A14 的通俗化重述，附录 C 给出「本方案阶段 ↔ 旧 PBL 方案 E 编号」对照表。查技术细节仍要回到审计和两份方案。

#### 各文档的章节结构与核心内容

| 文件 | 作用 | 内容要点 |
|---|---|---|
| `notes/Dummy_V2复刻路线图.md`（775 行，9/29） | **当前执行依据** | 0 一页看懂 / 1 规划依据（用户画像 + 四条原则）/ 2 路线总图（三线并行）/ 3 阶段 0～9 详解 / 4 江协课程选学表 / 5 硬件能力线 / 6 采购与预算 / 7 安全底线 / 8 怎样用 AI 学 / 9 实验记录模板 / 附录 A 资料速查、B 已知问题 12 条、C 旧编号对照、D 推荐资料 |
| `source/1.Dummy V2任同学整理/Dummy_V2项目驱动复刻方案_PBL版.md`（814 行，81 KB，9/6 12:35） | 实验驱动路线 E0～E13 | 1 一页路线图 / 2 为什么不再按 D01～D20 / 3 MVP-1 单电机实验台（`motor42_lab` 改造规格）/ 4 首批最小采购 / 5 E0～E5 / 6 E6 CAN / 7 E7 真实关节 / 8 E8 REF 双轴 / 9 E9 机械冻结 / 10 E10～E12 六轴整机 / 11 E13 扩展 / 12 JIT 学习地图 / 13 分阶段安全（A～F 前置分类、风险时点矩阵、FW01～FW12 后移）/ 14 Need-It-Now 采购 Gate / 15 故障排查树 / 16 实验日志模板 / 17 原始证据索引。证据标记体系：**[证]** 仓库原文确认、**[设]** 设计选择、**[测]** 待实测 |
| `source/1.Dummy V2任同学整理/Dummy_V2详细复刻方案_审计修订版.md`（55 KB，9/6 11:19） | 工程化 SOP + Gate | 20 章。1 目标背景 / 2 相对初稿的关键修改（对照 A01～A14）/ 3 总路线与 G0～G7 放行门槛 / 4 安全设计（三层停止、最小状态机、禁止的试验方式）/ 5 开发基线 / 6 首月 20 个工作单元 / 7 Motor-42 硬件制造 / 8 固件修复清单 / 9 首板上电 SOP / 10 裸电机校准闭环 SOP / 11 CAN / 12 单关节 / 13 REF 双轴 / 14 V2 参数冻结（六轴参数冲突表）/ 15 六轴集成标定 / 16 采购预算 / 17 上位机 ESP32 / 18 验收用例 34 条 / 19 学习地图 / 20 三个工作包 |
| `source/1.Dummy V2任同学整理/Dummy_V2项目全景科普讲义.md`（41 KB，9/4） | 零基础科普 | 21 章，最适合回答「这是什么/为什么」。0 项目是什么 / 1 整机类比 / 2 为什么分七个 STM32、三个时间尺度 / 3 **从一个命令到真实运动的 12 步全链路**（PC→REF→IK→限位→关节角换算→CAN→电机板→51200 计数→规划器→20 kHz 闭环→双 TB67H450→MT6816 反馈）/ 4 机械与传动链 / 5 电子硬件 / 6 STM32 与嵌入式 / 7 电机控制（PID 与 DCE）/ 8 编码器与**三种校准** / 9 CAN/UART/USB/WiFi/Fibre / 10 REF 中的机器人学（DH、FK、IK）/ 11 **三套机械模型为什么不能混装**（稚晖君原版 / 木子晓汶版 / 视频 V2）/ 12 机械文件格式 / 13 PCB 文件格式 / 14 仓库目录导读 / 15 上电后各板在做什么 / 16 容易混淆的十组概念 / 17 资料并非无歧义产品资料 / 18 五条核心认知 / 19 看到 X 应该想到什么 / 20 自测题 / 21 后续教学顺序 |
| `source/1.Dummy V2任同学整理/Dummy_V2复刻与学习方案_初稿.md`（31 KB，9/6 11:19） | **已被取代**，仅供溯源 | 15 章。首月单个 42 电机闭环实验台 + 逐周计划（第 1～4 周）+ 五个阶段 + 预算 Gate + 「最近三个具体动作」。其假设已被审计逐条推翻（见修订版第 2 节） |
| `source/1.Dummy V2任同学整理/dummy使用指南v1.3.pdf`（851 KB，10 页，2024-01-22，作者 zRed） | **原作者官方手册** | 1 电路连接（同向/反向线、6pin P1 原理图）/ 2 皮带尺寸 110 116 148 182 / 3 ST-Link 调试接线（前三根）/ 4 USB 命令清单（`!STOP/!START/!HOME/!CALIBRATION/!RESET/!DISABLE`、`#GETJPOS/#GETLPOS/#SET_DCE_KP/KI/KD/#REBOOT/#CMDMODE`、`>`/`@`/`&`）/ 5 web 端上位机（ESP32 esputil 烧录 + `wifi WIFI_NET WIFI_PASS`）。另含 CAN ID 真值表与三块板的端口定义 |
| `source/1.Dummy V2任同学整理/README.md`（1.2 KB，2024-04-13） | 原始仓库说明 | 来源链：稚晖君原理 → 木子晓汶 PCB 二次开发 → 论坛 V2 模型。教学视频 B 站 BV18x421Q7Td；论坛 http://dummy.free.mbbs.cc；虚拟机网盘（提取码 1234）；串口助手 serial.keysking.com；烧录工具 vcon.io。六个目录各自的描述。**声明：仅供学习，禁止一切商用** |

---

### 6.Docs 文件索引

#### 顶层文件

| 文件 | 作用 | 内容要点 |
|---|---|---|
| `source/1.Dummy V2任同学整理/6.Docs/Pins definations.pdf` | **三块板的引脚定义**（3 页） | 见下文「引脚定义」小节 |
| `source/1.Dummy V2任同学整理/6.Docs/Cable_connection.pdf` | **整机接线拓扑图**（1 页，横版） | 见下文「接线图」小节 |
| `source/1.Dummy V2任同学整理/6.Docs/02dd3e9cb70d260ed7a63c2eaafac5c.jpg` | 微信群二维码 | 「群聊：稚晖君Dummy机械臂V2版本复刻交群」。**二维码已于 2024-04-20 失效**，无技术价值 |
| `source/1.Dummy V2任同学整理/6.Docs/微信截图_20240420204129.png` | 群内调试要点 6 条 | ①单个电机先拨码调通；②**拨码是 2 进制，从 1 开始：0001 0010 0011 0100 0101 0110 = 节点 1~6**；③刷机要通电；④ref 板直接上电刷机；⑤电机板接 ref 主板后再刷机，刷机线接电机板上，别搞错；⑥dummy studio 很好用，所见即所得 |
| `source/1.Dummy V2任同学整理/6.Docs/en.stsw-link004 (1).zip` | ST-Link 驱动/工具 | 仅 2 个条目：`STM32 ST-LINK Utility v4.6.0/setup.exe`（27.6 MB，2020-10-01）。**Windows 专用，Linux 上用 OpenOCD/stlink 替代**。不要解压到项目目录内 |

#### 子目录

| 文件 | 作用 | 内容要点（含实际参数值） |
|---|---|---|
| `6.Docs/DH参数/dummy V2 版本 DH参数.png` | **六轴关节配置与求解器几何常量**（IDE 源码截图） | `DummyRobot` 构造函数第 23–33 行截图。见下文「DH/几何参数」小节。**注意：这是代码截图，不是标准 DH 参数表** |
| `6.Docs/DH参数/fw2.jpg` | 几何常量在机械臂上的位置示意 | Fusion360 侧视图，红色标注六个长度的量取位置：`L_BASE`、`D_BASE`、`L_ARM`、`D_ELBOW`、`L_FOREARM`、`L_WRIST`。**配合上图使用才能知道每个数字量的是哪一段** |
| `6.Docs/减速器参数/mini11_parameters.JPG` | MINIF11 谐波减速器规格 | 见下文「减速器参数」小节 |
| `6.Docs/减速器参数/mini8_parameters.JPG` | MINIF08 谐波减速器规格 | 同上 |
| `6.Docs/电机PID/PID.png` | ⚠️ **不是 PID 参数表** | 一张 ChatGPT 回答的截图，内容是 PID 控制的通俗解释（比例/积分/微分项定义、`Output = Kp·Error + Ki·Integral + Kd·Derivative`）。**不含任何本项目的具体 Kp/Ki/Kd 数值**。实际 PID/DCE 参数要查固件源码与 `#SET_DCE_KP/KI/KD` 命令 |
| `6.Docs/芯片说明/STM32F405.pdf` | REF 主控数据手册 | 已提取文本 745 KB |
| `6.Docs/芯片说明/MT6050陀螺仪.pdf` | ⚠️ 文件名写 MT6050，实为 **MPU-6050** 六轴陀螺仪手册（REF 板上实物就是 InvenSense MPU-6050）。**不要与编码器芯片 MT6816 混淆** |
| `6.Docs/芯片说明/LP2992.pdf` | LDO 稳压器 | 文本提取失败（仅 8 字节），是扫描版/图片型 PDF |
| `6.Docs/芯片说明/ME3116.pdf` / `SY8090.pdf` | DC-DC 降压芯片 | 24 V → 低压电源树用 |
| `6.Docs/芯片说明/OLED 13H.pdf` | REF 板 OLED 模块手册 | |
| `6.Docs/PCB/top.jpg` | **Motor 板功能区标注图**（最适合入门） | 彩框标注四个区：**高电压电源**（220µF/35V ×2、SS54、双 H450=TB67H450、24V/B-/B+/A-/A+ 丝印）、**MCU**（STM32F103C8T6 LQFP48、**Y1 = YXC 12.000 MHz 晶振**、SWDIO/SWCLK 排针）、**MCU 电源**、**CAN BUS**（S1 拨码、`IN CAN OUT` 丝印、P1/P2 连接器） |
| `6.Docs/PCB/m42.jpg` | Motor-42 实板正面高清照 | STM32F103C8T6（丝印 `MYS 99 249`）、YXC **12.000 MHz** 晶振、U1/U2 = **2× H45C（TB67H450FNG）**、C11/C14 = **150µF/35V** 电解电容、**S1 = 4 位拨码（1 2 3 4）**、K1/K2 两个按键、LED1/LED2、P1 IN / P2 OUT（均标 24V、B-B+、A-A+）、P3 = 6pin 侧插（调试口） |
| `6.Docs/PCB/m35.jpg` | Motor-35 实板正面高清照 | 与 m42 **同一套方案**：STM32F103C8T6、12.000 MHz、2× H450、150µF/35V、4 位拨码 S1、K1/K2。板更小，P3 在左侧，P1 在上、P2 在右 |
| `6.Docs/PCB/controller_top.jpg` | REF 控制板正面 | L 形板。贴纸 `Designed by MUZI XIAOWEN`。**ESP32-PICO-D4**（U8 区，`06F4300B`）、**SiLabs CP2102**（USB 转串口）、OLED 模块、**USB Type-C**、电感 + 多路 DC-DC、P2 6pin 白色连接器、A1 板载天线区 |
| `6.Docs/PCB/controller_bot.jpg` | REF 控制板背面 | **STM32F405RGT6**（LQFP64，丝印 `GQ20W 9R 11 / CHN GQ 324`）、**InvenSense MPU-6050**（U10）、**YXC 8.000 MHz 晶振**（注意：REF 是 8 MHz，电机板是 12 MHz）、150µF/35V、P1 6pin（24V+CAN）、P3 4pin（LED ring）、**板号丝印 `02615G_Y173_231113`**（2023-11-13 批次） |
| `6.Docs/配色/红色.jpg` | 整机实物照（红色 CNC 阳极氧化版） | 六轴整机装在 3D 打印灰色基座上，关节为红色铝合金 CNC 件，走线用黑白编织网管，电机板外挂黑色散热外壳。**展示的是 CNC 加工工艺版本** |
| `6.Docs/配色/橙色.jpg` | 整机实物照（橙色 3D 打印版） | 同一机械结构但为橙色 PLA/白色 3D 打印件，电机板裸露可见（能看到 `150 35V` 电容和 `IN B-B+ A-A+ OUT` 丝印）、J2 大臂为白色打印件、底座白色+橙色。**展示的是全打印低成本版本**。两张图说明同一套模型可选 CNC 或 3D 打印两种工艺 |
| `6.Docs/其他/fw2.png` | 电机固件工程结构 + main.cpp 截图 | 左侧工程树 `Ctrl-Step-Driver-STM32F1-fw`：Ctrl/{Driver(tb67h450_base, sin_map), Motor(motion_planner, motor), Sensor/Encoder(mt6816_base, encoder_calibrator_base), Signal(button_base, led_base)}。右侧 main.cpp 88–112 行：`motor.AttachDriver(&tb67H450)`、`AttachEncoder(&mt6816)`、**`HAL_TIM_Base_Start_IT(&htim1) // 100Hz`**、**`HAL_TIM_Base_Start_IT(&htim4) // 20kHz`**、`button1 && button2 同时按下 → encoderCalibrator.isTriggered = true` |
| `6.Docs/其他/fw3.png` | UART 命令解析源码截图 | `interface_uart.cpp` 的 `case 'v'` / `case 'p'` 分支：`sscanf(_data, "v %f", &vel)` → 若模式不是 `MODE_COMMAND_VELOCITY` 则 `SetCtrlMode()` 切模式 → `SetVelocitySetPoint((int32_t)(vel * MOTOR_ONE_CIRCLE_SUBDIVIDE_STEPS))`。**这张图直接佐证审计 A04：UART 命令会切换控制模式，不是只读调试口** |

---

#### DH 参数 / 六轴几何参数

`6.Docs/DH参数/dummy V2 版本 DH参数.png` 实际是 `dummy_robot.cpp` 构造函数的 IDE 截图（第 20–33 行）。逐行抄录：

| 关节 | id | inverse | reduction（减速比） | angleLimitMin | angleLimitMax |
|---|---:|---|---:|---:|---:|
| ALL（广播） | 0 | false | 1 | -180° | 180° |
| J1 | 1 | false | **50** | -170° | 170° |
| J2 | 2 | true | **50** | -75° | 90° |
| J3 | 3 | true | **50** | 0° | 180° |
| J4 | 4 | true | **50** | -180° | 180° |
| J5 | 5 | true | **50** | -100° | 120° |
| J6 | 6 | true | **5** | -720° | 720° |
| hand（夹爪） | 7 | — | — | — | — |

求解器几何常量（`DOF6Kinematic` 构造参数，单位 m）：

```cpp
dof6Solver = new DOF6Kinematic(L_BS: 0.1265f, D_BS: 0.035f, L_AM: 0.146f,
                               L_FA: 0.117f,  D_EW: 0.052f, L_WT: 0.0755f);
```

| 符号 | 含义（见 `fw2.jpg` 标注） | 图中值 (mm) | 当前 REF 源码值 (mm) |
|---|---|---:|---:|
| L_BS | L_BASE 基座高度 | **126.5** | 109 |
| D_BS | D_BASE 基座偏置 | **35** | 35 |
| L_AM | L_ARM 大臂长 | **146** | 146 |
| L_FA | L_FOREARM 小臂长 | **117** | 115 |
| D_EW | D_ELBOW 肘偏置 | **52** | 52 |
| L_WT | L_WRIST 腕长 | **75.5** | 72 |

> ⚠️ **参数矛盾（审计 A02，P0 级）**：这张图与 `2.Firmware/dummy-ref-core-fw/Robot/instances/dummy_robot.cpp:23-32` 的**当前源码不一致**。
>
> | 项 | 当前源码 | 本图（视频 V2） |
> |---|---|---|
> | J1~J6 减速比 | 30/30/30/**24**/30/**50** | 50/50/50/50/50/**5** |
> | J1~J6 inverse | true/false/true/false/true/true | false/true/true/true/true/true |
> | J2 范围 | -73~90° | -75~90° |
> | J3 范围 | 35~180° | 0~180° |
> | J5 范围 | -120~120° | -100~120° |
>
> **J6 尤其危险：源码 50 vs 图中 5，差 10 倍。** 审计裁定：两套都不是实物验收值，必须按实际装配的减速器实测总传动比。另：这六个长度是**求解器几何常量**，不等于完整的标准 DH 参数表（无 α/θ 列）。

#### 减速器参数

两张图是同一系列谐波减速器（MINIF 系列）的规格页，**均同时列出 30 和 50 两档减速比**，不指示本项目应选哪一档（审计 A02）。

**MINIF11**（`6.Docs/减速器参数/mini11_parameters.JPG`）—— 用于 J1~J5 候选

| 减速比 | 重量 | 2000 r/min 额定转矩 | 起停容许峰值转矩 | 平均负载转矩容许最大值 | 瞬间容许最大转矩 | 容许最高输入转速 | 容许平均输入转速 | 转动惯量 (1/4GD²) |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 30 | 0.4 kg | 2.2 N·m | 4.5 N·m | 3.4 N·m | 8.5 N·m | 8500 r/min | 3500 r/min | 1.4×10⁻² kg·cm² |
| **50** | 0.4 kg | **3.5 N·m** | **8.3 N·m** | **5.5 N·m** | **17 N·m** | 8500 r/min | 3500 r/min | 1.2×10⁻² kg·cm² |

外形尺寸：法兰 42.5×42.5 mm，外圆 Ø50.0，总厚 34.0 mm（Ø40.5 本体 24.5 高）；安装孔 2-Ø4.5 均布贯穿 + 2-M4 均布贯穿 + 6-M3 均布深 8；输入轴孔 Ø5.0 H7，输出孔 Ø12.0 H7，定位止口 Ø35.0 (-0.01/-0.03)，Ø20.5 内孔。

**MINIF08**（`6.Docs/减速器参数/mini8_parameters.JPG`）—— 用于 J6 / 小关节候选

| 减速比 | 2000 r/min 额定转矩 | 起停容许峰值转矩 | 平均负载转矩容许最大值 | 瞬间容许最大转矩 | 容许最高输入转速 | 容许平均输入转速 | 转动惯量 |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 30 | 0.9 N·m | 1.8 N·m | 1.4 N·m | 3.3 N·m | 8500 r/min | 3500 r/min | 3.2×10⁻³ kg·cm² |
| **50** | **1.8 N·m** | **3.3 N·m** | **2.3 N·m** | **6.6 N·m** | 8500 r/min | 3500 r/min | 3.0×10⁻³ kg·cm² |

外形尺寸：法兰 32.0×32.0 mm，外圆 Ø37.50，总厚 21.0 mm（Ø30.5/Ø31.0/Ø32.0 阶梯）；安装孔 2-M3 6H 均布贯穿 + 2-Ø3.5 均布贯穿 + 3-Ø2.5 均布深 8；输入轴孔 Ø5.0 H7，输出 Ø9.0 H7 / Ø8.0，定位止口 Ø26.0 (-0.01/-0.03)，Ø13.0 内孔。

> ⚠️ `4.Model/` 中 STEP 零件名出现 `minif-11-50` 等字样，是**选型线索**，不是实物铭牌或总传动比验收记录（审计 A02）。

#### 电机 PID 参数

**项目资料中不存在 PID 数值表。** `6.Docs/电机PID/PID.png` 只是一张 ChatGPT 对 PID 概念的通俗解释截图（含公式 `Output = Kp·Error + Ki·Integral + Kd·Derivative`），零项目参数。

实际要查 PID / DCE 参数，去这些地方：

- 固件默认值：`2.Firmware/dummy-42motor-fw/UserApp/main.cpp`（启动时从 EEPROM 加载，**EEPROM 值优先于代码默认值**）
- 控制器实现：`2.Firmware/dummy-42motor-fw/Ctrl/Motor/motor.cpp`（DCE 控制器）
- 运行时修改：REF 的 `#SET_DCE_KP` / `#SET_DCE_KI` / `#SET_DCE_KD <node> <value>` 命令（`dummy使用指南v1.3.pdf` 第 8 页）
- 科普解释：`Dummy_V2项目全景科普讲义.md` 第 7.4 节「PID 和 DCE」

已知的电流相关默认值（来自审计 A05）：**运行限流 1000 mA、校准电流 2000 mA**，两者独立，改一个不会约束另一个。

#### 引脚定义（`6.Docs/Pins definations.pdf`，3 页）

**第 1 页 — REF 主控板**

- 调试排针（板上侧）：`UART-RX`、`UART-TX`、`GND` | `SWDIO`、`SWCLK`、`GND`（6 针）
- 另一侧 3 针：`GND`、`PWM`、`+5V`（LED Ring）
- 主连接器（6 针，底部）：**`+24V`、`+24V`、`GND`、`GND`、`CAN_L`、`CAN_H`**（两根并联供电线）

**第 2 页 — Motor-42 板**

- **P1 / P2**（板上两个 6 针卧式，`IN` / `OUT`）：`+24V`、`+24V`、`GND`、`GND`、`CAN_L`、`CAN_H` —— 功率 + CAN 菊花链，P1 与 P2 引脚定义相同
- **P3**（侧面 6 针）：`UART_RX`、`UART_TX`、`GND`、`SWDIO`、`SWCLK`、`GND` —— **调试/烧录口**
- **S1**：CAN 节点 ID 拨码 + 终端电阻

**第 3 页 — Motor-35 板**：与 Motor-42 **引脚定义完全相同**，仅物理布局不同（P1 在上、P2 在右侧、P3 在左侧）。

`dummy使用指南v1.3.pdf` 第 4 页给出 **CAN ID 真值表**：

| ID2 | ID1 | ID0 | CAN BUS ID |
|---:|---:|---:|---:|
| 0 | 0 | 0 | 0 |
| 0 | 0 | 1 | 1 |
| 0 | 1 | 0 | 2 |
| 0 | 1 | 1 | 3 |
| 1 | 0 | 0 | 4 |
| 1 | 0 | 1 | 5 |
| 1 | 1 | 0 | 6 |
| 1 | 1 | 1 | 7 |

即 J1~J6 对应拨码 `0001 0010 0011 0100 0101 0110`（与微信截图一致）。**实板 S1 是 4 位拨码，但软件只用低 3 位做节点 ID，第 4 位是 CAN 终端电阻（120 Ω）**。审计 A10 提醒：第 4 位的电气作用须查所选原理图确认。

> ⚠️ **P1/P2（功率+CAN）与 P3（UART/SWD）外观相似但功能完全不同，插错会损坏板子**（审计 A03）。使用指南第 2 页原话：「左下第三个 6pin 接口则是程序烧录接口，别接错了」。

#### 接线图（`6.Docs/Cable_connection.pdf`，1 页横版）

整机 CAN 菊花链拓扑，用蓝色箭头串起四块板：

```text
REF 板 P1 ──(同向线，需交换中间两根 CAN 线)──> Motor 板#1 P1(IN)
Motor#1 P2(OUT) ──(反向线)──> Motor#2 P1(IN) ──(反向线)──> Motor#3 ... 直到 J6
```

图上两处中文标注：

- 指向 REF→J1 那根线：**「只有第一条线是同向线」**
- 指向其余线：**「其余都是反向线」**

使用指南第 1 页补充说明：「Ref to j1 使用同向线，**需要交换中间两根 canbus 线**；剩下 j1 至 j6 的连接都使用反向线」，并给出 P1 的原理图片段：**pin1/pin2 = VCC_IN（两根一组）、pin3 = CAN1_H、pin4 = CAN1_L、pin5/pin6 = GND**（`Header 6H`）。6pin 接口左边 IN 侧 24V 丝印处为 24V，右边 OUT 侧实际 24V 在靠 IN 一侧。

供电：DC5.5 插座 → 正极串自锁开关 → REF 板（使用指南第 3 页手绘图）。

> ⚠️ **审计 A03（P0，阻塞上电）**：不能把「同向/反向」「中间两针」当成跨版本通用配线规则。必须以**同一板版本、同一观察方向**的原理图和实板为准，逐针万用表测出 24 V / GND / CAN_H / CAN_L 再制线；两根并联供电线要分别测通断。填表用 `复刻审计_2026-09-06/实施记录模板.md` 第 2 节「线束逐针核验单」。

---

### 复刻审计_2026-09-06/

一次由 5 个 OpenCode 子代理（均为 `opencode-go/deepseek-v4-pro`）+ 主审复核完成的全项目静态审计的产出目录。**审计范围是「全文件清点 + 复刻关键路径深审」，不代表 3970 个文件逐行验证，更不代表可以制造或安全运行。**

#### 核心结论（`审计结论与证据.md`，22 KB，裁定版本）

**覆盖边界**：审计前对 3,970 个文件生成 SHA-256 清单，总计 566,257,059 字节（≈566 MB）。分布：根目录 5 / `1.Hardware` 57 / `2.Firmware` 3565 / `3.Software` 160 / `4.Model` 157 / `5.Bom` 1 / `6.Docs` 25。

**已确认的阻塞项 A01～A14**：

| 编号 | 优先级 | 标题 | 一句话结论 |
|---|---|---|---|
| A01 | P0 | Motor-42 制造包不能直接放行 | `motor42 Gaber.zip` 31 个文件**无独立 NC Drill**，无 Excellon `M48` 头；`.RUL` 是 DRC 规则非钻孔文件。三类主板均无已审核标准 CPL。REF 包含根目录和 `REF_V1/` 两套输出不可混发 |
| A02 | P0 | 视频 V2 参数图与当前 REF 固件不是同一套参数 | 减速比、方向位、限位、六个几何长度全部冲突（见上文 DH 小节） |
| A03 | P0 | 线束版本与观察方向必须逐针核验 | P1/P2 是功率+CAN，P3 是 UART/SWD，外观相似功能不同 |
| A04 | P0 | 电机 UART 是会改变控制模式的运动入口 | `c/v/p` 命令单位分别为 A、转/秒、电机轴绝对转数（内部转 mA / 51200 计数每圈）；会切 `requestMode`，所以 `enableMotorOnBoot=false` **不构成独立运动授权门**。解析器忽略 `_len`，无空参/有限值/尾部垃圾检查，且在中断上下文被调用 |
| A05 | P0 | 编码器有效性与失联保护没闭合到安全状态 | `mt6816_base.cpp:25-56` 读到 parity 和 `noMagFlag` 但失败仍沿用旧角度；无通用命令存活超时停机；`main.cpp:50-56` **默认关闭堵转保护并强制关闭温度监视**；默认 1 A 控制限流与 2 A 校准电流独立 |
| A06 | P1 | Flash 存储地址存在但链接器未保护保留区 | 校准表 `0x08017C00` 长 32 KiB，参数区 `0x0801FC00` 长 1 KiB；程序从 `0x08000000` 起只有 **95 KiB** 可用，而 `.ld` 仍授权整个 128 KiB |
| A07 | P0 | `!STOP` 不是真正急停 | `EmergencyStop()` 只「移动到当前位置」+ `isEnabled=false` + 清队列，**不调用节点失能接口**；`MoveJ()` 目标等于当前位置时出现 `0/0` 路径，非法浮点可能进入 CAN |
| A08 | P0 | CAN 长度、节点与发送错误处理不足 | `can_protocol.cpp:22-32` 由标准 ID 得到 0~15 节点号直接索引 `motorJ[id]`，**数组只有 7 个元素，7~15 越界**；未验证 DLC/IDE/RTR；电机端 `CAN_Send()` 失败直接进关中断死循环的 `Error_Handler()` |
| A09 | P1 | REF 不支持「拔掉四轴就变两轴」 | 六轴发送循环与到达掩码 `0b1111110` 硬编码；`Homing/Resting` 等待缺席节点可能永不结束。IMU 缺失会阻止后续任务启动（但通信已先初始化） |
| A10 | P0 | 两种「校准」完全不同 | 电机编码器校准（本地按键 / CAN `0x02`，32 KiB 映射表）≠ REF `!CALIBRATION`（`CalibrateHomeOffset()`，会**使能所有节点、调整 J2/J3 电流、两次写零偏、自动收拢并重启**）。节点 ID 每次启动被三位拨码覆盖，CAN `0x11` 写入不持久 |
| A11 | P1 | REF 命令解析和队列边界需专项修复 | `sscanf` 返回数量未检查；`std::string::find` 是子串匹配不是完整命令匹配；命令队列固定 64 字节，`Push()` 直接传 `c_str()` 有越界读/截断风险 |
| A12 | P1/P0 | ESP32 有被展平成普通文本的链接文件及网络控制风险 | `main/net.c` 只有一行 `../../../uart-bridge/net.c` 但不是符号链接，CMake 仍当 C 源码编译。全项目扫到 **320 个相对路径文本占位文件**。桥接默认启 TCP/WebSocket，HTTP 配置接口无鉴权，示例 `config.json` 用公共 MQTT broker |
| A13 | P1 | 上位机只作为后期接口，不能误接到 Motor-42 UART | `simple-cli.py:7-20` 硬编码 macOS 端口，发送的是 **REF 的 `!START`**，不是 Motor-42 的 `c/v/p`。VID `0x1209` 与软件配置相符（子代理的「VID 不匹配」判断被推翻） |
| A14 | P1 | 机械材料与许可证不能凭文件名补齐 | 皮带：BOM「其它」列 **130×2 / 150×1**，旧使用指南列 **110/116/148/182**（版本冲突）；`GBN1302GT-60` 在 STEP 中对应文字是「同步带」，**不能解析成 60 齿同步轮**；BOM 42×40 与 STEP 42-34/42-40 并存。GPL 允许商业使用，不能认定「GPL 商用即违规」 |

**第 3 节「对子代理误判的裁定」**（14 条）—— 读 `deepseek_*.md` 前必须先看这张表，典型纠正：

- HSE 不是 8 MHz 而是 **12 MHz**（宿主预处理验证，且 `PCB/m42.jpg` 实物晶振丝印 `12.000` 佐证）
- STM32F1 的 HAL 用四次 halfword 实现 DOUBLEWORD，EEPROM 不会必然失败
- `node >= 1 & node <= 6` 不会「拒绝偶数节点」（C++17 静态断言复核）
- REF 方向位是 `true/false/true/false/true/true`，不是子代理说的 `false/true/false/true/false/true`
- `SetEnableTemp(false)` 是温度监视接口，不能当失能用
- `GBN1302GT-60` 不是 60 齿从动轮
- fibre 有 `.py` 源码，不是只有 `.pyc`

**第 4 节「本次验证结果与下一步」**：已完成全清单/哈希、4 个制造 ZIP 的 CRC 与钻孔候选检查、HSE 宏宿主预处理、C++ 布尔表达式静态断言、Python AST 检查、源文件路径占位扫描。**未完成**：ARM 构建、烧录、上电、EDA 电气审查、CAD 干涉与实例统计、商家询价、实物性能验收。当时 PATH 中没有 `cmake`、`arm-none-eabi-gcc`、`ninja`。

#### 5 份 deepseek_*.md（子代理原始报告，非裁定）

每份开头都带警告横幅：「原始子代理意见，保留用于审计追溯，不是执行依据」。

| 文件 | 覆盖面 | 主要结论 |
|---|---|---|
| `deepseek_ref.md`（16 KB，144 行） | `2.Firmware/dummy-ref-core-fw/`（STM32F405 主控） | P0-1 `!STOP` 不真正切断使能；P0-2 `!HOME`/`!CALIBRATION` 会自动运动且 `Homing()` 可能无视方向/限位撞机械限位。列出逐行读过的 20+ 个文件清单。**方向位、位与表达式、温度监视接口、IMU 初始化顺序四处有误判** |
| `deepseek_motor.md`（16 KB，145 行） | `dummy-42motor-fw` / `dummy-35motor-fw` | 电机板固件调用链、UART/CAN 入口、编码器、校准器、Flash 布局。**HSE 8 MHz / 控制环 13.33 kHz 的说法被推翻** |
| `deepseek_hardware.md`（15 KB，143 行） | `1.Hardware/` 电子制造 | 制造包完整性、Gerber/钻孔/CPL/钢网。**「所有板没有钢网资料、所有 RUL 是铣槽层」被判过度** |
| `deepseek_mechanical.md`（13 KB，143 行） | `4.Model/` + `5.Bom/` | P0-1 减速比冲突（装配体 50:1 vs 固件 J1~J5 30/24）；P0-2 42 电机长度未冻结（42-34 vs 42-40）；P0-3 Motor-42 无机器可读 CPL，BOM 非最终采购单。**60 齿同步轮与 3:1 传动比的推论错误** |
| `deepseek_software.md`（12 KB，126 行） | `3.Software/` + ESP32 集成 | Python 入口、协议、依赖、Unity 成品边界。**「fibre 只有 pyc」「simple-cli 可直接控单电机」「GPL 商用违规」三处错误** |

#### 数据文件

| 文件 | 大小 | 数据结构 | 用途 |
|---|---|---|---|
| `file_inventory.csv` | 735 KB，3970 行 + 表头 | `path, bytes, sha256, extension, coverage`（BOM 开头）。`coverage` 当前全为 `inventory_only` | 审计开始时的全文件 SHA-256 快照。**`inventory_only` 只表示清点过，不能解释为已审源码** |
| `inventory_summary.json` | 308 KB | `{scope, excluded, file_count:3970, bytes:566257059, sections:{目录→{files,bytes}}, empty_files:[9], duplicate_groups:[855 组], errors:[2]}` | 目录统计、9 个空文件、855 组重复文件、2 个提取错误（含 `esputil.zip` 不是有效 zip） |
| `evidence_checks.json` | 74 KB | `{tools, relative_path_source_stubs[320], host_preprocessor, cpp_boolean_range_check, gerber_packages[4], ref_constructor_rows[6], motor_42_vs_35_hash_differences[18], python_ast_errors[0], budget_interval_sums_CNY, delivery_checks}` | **「审计修订版」的机读证据**。`tools` 记录当时 cmake/arm-none-eabi-gcc/ninja 均为 null；`gerber_packages` 记录 4 个制造 ZIP 的文件数、CRC 错误、NC drill 候选；`delivery_checks` 记录 34 条测试用例、12 项固件任务、20 个工作单元、8 个 Gate、5 个已验证 pro 会话 |
| `pbl_document_checks.json` | 1.6 KB | `{documents[2], experiments[14], source_references:20, staged_firmware_tasks:12, prerequisite_classes:6, purchase_classes:6, original_artifacts_hash_checked:3965, changed_artifacts:[], arithmetic_checks:"passed"}` | **「PBL 版」的自检结果**。确认 PBL 版 814 行 39092 字符、33 条完整路径全部存在、E0~E13 共 14 个实验齐全、3965 个原始文件哈希未变 |
| `archive_members.json` | 29 KB | 数组，每项 `{path, members:[...]}` | ZIP/XLSX 成员清单（A01 的证据）。**不递归解析嵌套压缩包** |
| `agent_runs.json` | 20 KB | 数组 5 项，每项 `{scope, session, complete, exit, tools, last_tool, finish, text_chars, errors, models, read_paths}` | 5 个 OpenCode 子代理会话的运行记录，用于核对实际使用的模型是 `opencode-go/deepseek-v4-pro` |

#### 脚本

| 文件 | 行数 | 作用 |
|---|---|---|
| `audit_inventory.py` | 128 | 生成/校验全文件 SHA-256 清单。`--verify` 校验，**不带参数会重新生成快照（会覆盖本次审计历史，勿随意运行）**。需 Python 3.11+ 的 `hashlib.file_digest` |
| `verify_evidence.py` | 159 | 复核 `evidence_checks.json` 中的各项检查（Gerber 包、HSE 预处理、C++ 静态断言、Python AST、路径占位扫描） |
| `verify_pbl_plan.py` | 96 | **验证 PBL 版文档本身的完整性**：①代码围栏成对；②所有 md 链接目标存在；③所有反引号里形如 `N.目录/...` 的路径真实存在；④`### E{n}：` 标题恰好是 E0~E13 连续 14 个；⑤比对 3965 个原始文件哈希未变。输出 `pbl_document_checks.json`。**纯文档/静态完整性检查，不做 ARM 构建或硬件测试** |

可复核命令（从 `source/1.Dummy V2任同学整理/` 运行）：

```bash
python3 "6.Docs/复刻审计_2026-09-06/audit_inventory.py" --verify
python3 "6.Docs/复刻审计_2026-09-06/verify_evidence.py"
```

#### `extracted/`（33 个文件）

审计时机器提取的辅助文本，**原文件仍是依据；图片中的文字不一定出现在 PDF 提取文本里**。

- **19 个工程图文本**（`4.Model__...pdf.txt`）：V2 视频款的 `Dummy-B 2D工程图` 拆分版本 1~7 + Baseboard + J4/j5 法兰盘，以及 `改版工程图` 的基座改版/J1改版/J23/J4/J5A/J5B/J6/j5法兰盘。**多数极小（1~520 字节），说明这些图纸是矢量/图片型，文字提取基本失败**。最大的 `Dummy-B 2D工程图.pdf.txt` 仅 1594 字节
- **6 个芯片手册文本**：`STM32F405`（746 KB，最完整）、`MT6050陀螺仪`（168 KB）、`OLED 13H`（64 KB）、`ME3116`（22 KB）、`SY8090`（22 KB）、`LP2992`（**仅 8 字节，提取失败**）
- `6.Docs__Cable_connection.pdf.txt`（66 B）/ `6.Docs__Pins definations.pdf.txt`（82 B）：**几乎没有文字**，证明这两份 PDF 全是矢量图，必须用看图方式读
- `dummy使用指南v1.3.pdf.txt`（6.2 KB）：使用指南的完整文本，**适合 grep 检索命令名**
- `dummy V2版本_bom.json`（70 KB）：`5.Bom/dummy V2版本_bom.xlsx` 六个工作表的单元格提取
- `pins-1.png` / `pins-2.png` / `pins-3.png`：`Pins definations.pdf` 三页的位图渲染（主审用于补读）

#### 其他文件

| 文件 | 作用 |
|---|---|
| `实施记录模板.md`（5.8 KB，128 行） | 7 节现场填写表格：1 版本冻结单（18 个字段：源码哈希、编译器、ELF/HEX SHA-256、程序占用、板号、电机型号、磁铁规格、限流、EEPROM 值、CAN ID 来源、命令白名单…）/ 2 **线束逐针核验单**（A 端板号·观察方向·Pin·网络 ↔ B 端，含通断阻值和相邻针绝缘）/ 3 首板上电记录 / 4 六轴参数冻结表 / 5 制造与采购放行单 / 6 实验日志 / 7 阶段验收签署 |
| `PBL路线复核补充.md`（9.5 KB，65 行） | PBL 版的配套源码复核，**P01~P17 共 17 条定点证据**。核心结论：可以先做 TX-only 编码器观察 → 板上触发的有限次本地闭环 → 最后才做双向 UART 控制。关键事实：UART 为 **115200 8N1，PB6 TX / PB7 RX，RX DMA 是 `DMA_NORMAL` 不是循环 DMA**；编码器 `RESOLUTION = 16384`；校准器 **200 整步 × 每步 16 点，粗步进 2、细步进 1**，校准成功后自动 `HAL_NVIC_SystemReset`；`SetPositionSetPoint` 接受整数计数，**转数要 ×51200 取整**；`.ld` 仍是 128 KiB 而校准区起点 `0x08017C00` |

#### 时效性（审计日期 2026-09-06 vs 当前 2026-10-08）

- **已过去约 1 个月。** 审计的**源码事实部分**（A01~A14 的行号、数值、结构）仍然有效——`notes/Dummy_V2复刻路线图.md`（9/29）附录 B 原样继承了这 12~14 条问题，并写明「这些都是之前审计从源码和资料里确认过的问题」。
- **审计的执行建议部分已被降级。** 路线图明确把这些缺陷从「开工前必须修完的门槛」改为「到了对应阶段再处理，很多本身就是好的练习题」，并给出各自的处理阶段（见路线图附录 B 的「什么时候处理」列）。
- **已经发生变化的状态**：审计时 PATH 无 `cmake`/`arm-none-eabi-gcc`/`ninja`、无任何编译产物；**路线图记录 E0 已完成**——Motor-42 固件已能在 Linux 上编译出 `.elf/.hex/.bin`，产物在 `source/1.Dummy V2任同学整理/2.Firmware/build/motor42-baseline/`，且程序实际约 74 KB（未触及 95 KiB 上限）。
- **哈希快照已不可全信**：`file_inventory.csv` 是 9/6 的快照，不含审计目录本身，也不含 9 月之后新增的 `notes/`、`build/`、`workspace/`、`嵌入式学习/`。重跑 `audit_inventory.py --verify` 会报告这些差异，属正常。

---

### 可回答的典型问题 → 去哪个文件

1. **问：我现在该做什么？下一步学什么？** → `notes/Dummy_V2复刻路线图.md` 第 0 节「一页看懂」+ 第 3 节阶段详解。**这是唯一的执行依据，不要用三份旧方案的进度安排**
2. **问：复刻分几个阶段？预算多少？** → `notes/Dummy_V2复刻路线图.md` 第 2 节路线总图（阶段 0～9，各带成果/用时/花费）+ 第 6 节采购与预算
3. **问：六轴 DH 参数 / 减速比 / 限位是多少？** → `source/1.Dummy V2任同学整理/6.Docs/DH参数/dummy V2 版本 DH参数.png`（视频 V2 值）**必须同时看** `6.Docs/复刻审计_2026-09-06/审计结论与证据.md` A02（源码值与冲突裁定）和 `2.Firmware/dummy-ref-core-fw/Robot/instances/dummy_robot.cpp:23-32`
4. **问：L_BS / L_AM / L_FA 这些长度量的是机械臂哪一段？** → `6.Docs/DH参数/fw2.jpg`（Fusion360 标注图）
5. **问：谐波减速器选 30 还是 50？额定转矩多少？** → `6.Docs/减速器参数/mini11_parameters.JPG`（J1~J5）、`mini8_parameters.JPG`（J6/小关节）。**选型结论见审计 A02：两图都列 30/50，资料不指示应购哪一档**
6. **问：电机 PID 参数（Kp/Ki/Kd）是多少？** → **`6.Docs/电机PID/PID.png` 里没有**（只是 ChatGPT 概念截图）。查 `2.Firmware/dummy-42motor-fw/Ctrl/Motor/motor.cpp` 和 `UserApp/main.cpp`，运行时改用 `#SET_DCE_KP/KI/KD` 命令
7. **问：三块板的引脚怎么定义？哪个口能插烧录器？** → `6.Docs/Pins definations.pdf`（3 页，看图）。**P1/P2 = 24V+CAN，P3 = UART/SWD，不能插错**
8. **问：整机怎么接线？同向线反向线是什么？** → `6.Docs/Cable_connection.pdf` + `source/1.Dummy V2任同学整理/dummy使用指南v1.3.pdf` 第 1 节。**上电前必读审计 A03**
9. **问：CAN 节点 ID 怎么拨码？** → `dummy使用指南v1.3.pdf` 第 4 页真值表 + `6.Docs/微信截图_20240420204129.png`（J1~J6 = `0001`~`0110`）。**拨码每次开机覆盖 EEPROM，见审计 A10**
10. **问：REF 支持哪些串口命令？`!HOME` 和 `!CALIBRATION` 有什么区别？** → `dummy使用指南v1.3.pdf` 第 7~9 页命令清单；**区别的权威解释在审计 A10**（两种校准完全不同，`!CALIBRATION` 会让所有关节自己动）
11. **问：Motor-42 的 Gerber 能直接发厂吗？** → **不能。** `6.Docs/复刻审计_2026-09-06/审计结论与证据.md` A01（缺 NC Drill、无审核 CPL、多版本并存）
12. **问：为什么 `!STOP` 不能当急停用？** → 审计 A07 + 路线图附录 B 第 8 条。必须保留物理断电开关
13. **问：板子上那颗晶振是多少 MHz？** → 电机板 **12 MHz**（`6.Docs/PCB/m42.jpg`、`m35.jpg` 实物丝印 `YXC 12.000`，并经审计宿主预处理验证）；REF 板 **8 MHz**（`6.Docs/PCB/controller_bot.jpg`）。**子代理报告里的「8 MHz」说法对电机板是错的**
14. **问：Motor 板 / REF 板上都有哪些芯片？** → `6.Docs/PCB/top.jpg`（带功能区彩框标注，最易懂）、`m42.jpg`（STM32F103C8T6 + 2×TB67H450）、`controller_top.jpg`（ESP32-PICO-D4 + CP2102 + OLED）、`controller_bot.jpg`（STM32F405RGT6 + MPU-6050）
15. **问：机械臂做成什么样子？CNC 还是 3D 打印？** → `6.Docs/配色/红色.jpg`（红色 CNC 阳极氧化）、`6.Docs/配色/橙色.jpg`（橙白 3D 打印）
16. **问：这个项目整体是怎么运作的？从敲命令到电机转经过哪些环节？** → `source/1.Dummy V2任同学整理/Dummy_V2项目全景科普讲义.md` 第 3 节（12 步全链路）
17. **问：为什么 `4.Model/` 里有三套模型？能混装吗？** → 科普讲义第 11 章（稚晖君原版 / 木子晓汶版 / 视频 V2，**不能混装**）；版本冻结要求见审计修订版第 14.1 节
18. **问：皮带要买多长？** → **资料冲突**：BOM 写 130×2 / 150×1，使用指南写 110 116 148 182。见审计 A14，以实际装配版本为准
19. **问：ESP32 固件能直接编译吗？联网安全吗？** → **不能直接编译**，有 320 个被展平的链接文件；网络面无鉴权、示例配置连公共 MQTT。见审计 A12
20. **问：哪些 PDF 能 grep，哪些必须看图？** → 能 grep：`6.Docs/复刻审计_2026-09-06/extracted/` 下的 `STM32F405`/`MT6050`/`OLED 13H`/`ME3116`/`SY8090` 和 `dummy使用指南v1.3.pdf.txt`。必须看图：`Cable_connection.pdf`、`Pins definations.pdf`、`LP2992.pdf`、全部 `4.Model` 工程图
21. **问：某个审计结论的原始出处在哪？** → `审计结论与证据.md`（裁定版）→ 对应 `deepseek_*.md`（原始意见）。**顺序不能反：子代理报告有 14 处已纠正的误判，列在裁定文第 3 节**
22. **问：做实验要填什么记录？** → `6.Docs/复刻审计_2026-09-06/实施记录模板.md`（7 节正式表格）或 `notes/Dummy_V2复刻路线图.md` 第 9 节（简化版）

---

## 七、主控板固件 dummy-ref-core-fw

机械臂**主控板**（REF / Robot Embedded Framework 核心板）固件。MCU 为 **STM32F405RGT6**（1MB Flash / 128KB SRAM + 64KB CCMRAM，HSE + PLL M=4/N=168/P=2 → SYSCLK 168MHz，APB1=42MHz、APB2=84MHz，Flash latency 5）。架构是 CubeMX 生成的 HAL 工程 + FreeRTOS 10.3.1（CMSIS-RTOS v2 封装）+ 一层 C++ 业务层（`UserApp` / `Robot` / `Bsp`）+ ODrive 的 fibre 原生协议栈。

构建方式：CMake + arm-none-eabi-gcc，C++17 / C11，硬浮点 `fpv4-sp-d16`，`file(GLOB_RECURSE)` 全量扫源码。固件入口链路为
`startup_stm32f405xx.s` → `Reset_Handler` → `Core/Src/main.c: main()` → `osKernelStart()` → `defaultTask` → `Core/Src/freertos.c: StartDefaultTask()` → `MX_USB_DEVICE_Init()` → `UserApp/main.cpp: Main()`。

**全局对象（都在 `UserApp/main.cpp` 顶部定义，其他文件通过 `extern DummyRobot dummy;` 引用）**：
`oled(&hi2c0)`（软 I2C）、`mpu6050(&hi2c1)`、`timerCtrlLoop(&htim7, 200)`、`pwm(21000, 21000)`、`rgb(0)`、`dummy(&hcan1)`。

**任务与同步原语总表**（跨 `Core/Src/freertos.c`、`Bsp/communication/*`、`UserApp/main.cpp`）：

| 任务名 | 创建位置 | 优先级 | 栈 | 职责 |
|---|---|---|---|---|
| `defaultTask` | `Core/Src/freertos.c` | Normal | 2000 | 调 `MX_USB_DEVICE_Init()` 后进 `Main()`，`Main()` 返回即 `vTaskDelete` 自杀 |
| `usbIrqTask` | `Core/Src/freertos.c`（必须在 USB init 前建） | AboveNormal | 500 | `UsbDeferredInterruptTask`，等 `sem_usb_irq` 后跑 `HAL_PCD_IRQHandler` |
| `commTask` | `Bsp/communication/communication.cpp` | Normal | **45000** | `CommitProtocol()` 发布 fibre 对象树，再启动 UART/USB/CAN server，之后空转 |
| `UartServerTask` | `Bsp/communication/interface_uart.cpp` | Normal | 2000 | 1ms 轮询 UART4/5 的 DMA 环形缓冲 |
| `UsbServerTask` | `Bsp/communication/interface_usb.cpp` | Normal | 2000 | 等 `sem_usb_rx`，分发 CDC / native 两个端点 |
| `ControlLoopFixUpdateTask` | `UserApp/main.cpp` | **Realtime** | 2000 | 200Hz 定频控制环，靠 TIM7 的 `ulTaskNotifyTake` 唤醒 |
| `ControlLoopUpdateTask` | `UserApp/main.cpp` | Normal | 2000 | 阻塞在命令 FIFO 上解析运动指令 |
| `OledTask` | `UserApp/main.cpp` | Normal | 2000 | IMU 更新 + OLED 刷新（无 delay，全速跑） |
| `RGBTask` | `UserApp/main.cpp` | Normal | 2000 | WS2812 灯效，`osDelay(30)` |

信号量（7 个，全在 `Core/Src/freertos.c: MX_FREERTOS_Init()` 创建）：`sem_usb_irq(1,0)`、`sem_uart4_dma(1,1)`、`sem_uart5_dma(1,1)`、`sem_usb_rx(1,0)`、`sem_usb_tx(1,1)`、`sem_can1_tx(1,1)`、`sem_can2_tx(1,1)`；声明在 `UserApp/freertos_inc.h`。命令队列：`osMessageQueueNew(16, 64, nullptr)`，在 `DummyRobot::CommandHandler` 构造函数里建。

---

### UserApp/ — 应用层入口与协议回调

业务代码的最上层。`main.cpp` 定义所有全局外设/机器人对象并创建用户任务；`protocols/` 下三个文件是三类协议的"用户钩子"——BSP 层收到数据后回调这里，所以**加新指令就改这三个文件**。`common_inc.h` 是唯一的"万能头"，C 段和 C++ 段用 `extern "C"` 分开。

| 文件 | 作用 | 关键符号/要点 |
|---|---|---|
| `source/1.Dummy V2任同学整理/2.Firmware/dummy-ref-core-fw/UserApp/main.cpp` | C++ 侧真正的 main；全局对象定义 + 4 个用户任务 + TIM7 回调 | 全局 `SSD1306 oled(&hi2c0)`、`MPU6050 mpu6050(&hi2c1)`、`Timer timerCtrlLoop(&htim7,200)`、`PWM pwm(21000,21000)`、`RGB rgb(0)`、`DummyRobot dummy(&hcan1)`；`Main()`、`ThreadControlLoopFixUpdate()`、`ThreadControlLoopUpdate()`、`ThreadOledUpdate()`、`ThreadRGBUpdate()`、`OnTimer7Callback()`、`HAL_TIM_PWM_PulseFinishedCallback()`（TIM2 完成→`rgb.Interrupt(1)`）；`mpu6050.InitFilter(200,100,50)`；`pwm.SetDuty(PWM::CH_A1, 0.5)` 点亮开关 LED；启动日志 `"[sys] Heap remain: %d Bytes"` 打到 `*uart4StreamOutputPtr` |
| `.../UserApp/common_inc.h` | 全工程统一包含头 | `#define CONFIG_FW_VERSION 1.0`（会进 USB 产品字符串）；`void Main(void)`；`extern uint64_t serialNumber; extern char serialNumberStr[13];`；C++ 段包含 `communication.hpp`、`U8g2lib.hpp`、`MPU6050.hpp`、`rgb.hpp`、`timer.hpp`、`actuators/mintasca/sca.hpp`、`actuators/ctrl_step/ctrl_step.hpp`、`instances/dummy_robot.h` |
| `.../UserApp/freertos_inc.h` | 信号量/任务句柄的 extern 声明 + 栈占用备注 | `sem_usb_irq / sem_uart4_dma / sem_uart5_dma / sem_usb_rx / sem_usb_tx / sem_can1_tx / sem_can2_tx`；注释 `/*---- 60K (used) / 64K (for FreeRTOS on ccram) ----*/`；**注释里的栈大小（commTask 48000、oledTask 4000、controlLoopFixUpdate 4000）与代码实际值（45000 / 2000 / 2000）不一致**；还声明了代码里已不存在的 `usbServerTaskHandle` 以外的 `uartServerTaskHandle` 等 |
| `.../UserApp/protocols/ascii_protocol.cpp` | ASCII 行指令的用户实现（USB-CDC / UART4 / UART5 各一个回调） | `OnUsbAsciiCmd()`、`OnUart4AsciiCmd()`、`OnUart5AsciiCmd()`（**UART5 回调体为空**）；指令前缀分三类：`!` 系统控制（`!STOP`→`commandHandler.EmergencyStop()`、`!START`→`SetEnable(true)`、`!HOME`→`Homing()`、`!CALIBRATION`→`CalibrateHomeOffset()`、`!RESET`→`Resting()`、`!DISABLE`→`SetEnable(false)`）；`#` 查询/配置（`#GETJPOS`、`#GETLPOS`、`#SET_DCE_KP/KI/KD <node> <val>`、`#REBOOT <node>`、`#CMDMODE <mode>`）；`>`/`@`/`&` 运动指令→`dummy.commandHandler.Push(_cmd)` 并回复剩余 FIFO 空间 |
| `.../UserApp/protocols/can_protocol.cpp` | CAN1 收包的用户分发 | `OnCanMessage(CAN_context*, CAN_RxHeaderTypeDef*, uint8_t*)`；**ID 拆分：`id = StdId >> 7`（4bit 节点号），`cmd = StdId & 0x7F`（7bit 命令码）**；`case 0x23` → `motorJ[id]->UpdateAngleCallback(*(float*)data, data[4])`；`case 0x25` → `memcpy(&motorJ[id]->temperature, data, 4)`；每帧结束都调 `dummy.UpdateJointAnglesCallback()`；CAN2 分支留空；文件顶部有未使用的 static `txHeader` |
| `.../UserApp/protocols/cmd_protocol.cpp` | fibre 原生协议对象树定义 | `MakeObjTree()`、`COMMIT_PROTOCOL` 宏展开出 `CommitProtocol()`；暴露 `serial_number`(ro)、`get_temperature`、`get_voltage`、`robot`（= `dummy.MakeProtocolDefinitions()`）；`class HelperFunctions staticFunctions`；`#define TEST_ADC_CHANNEL_0 0`（传给 `AdcGetVoltage(0)`，不匹配任何 `ADC_CHx`） |

#### UserApp/main.cpp 详述

`Main()` 的初始化顺序有强依赖：先 `InitCommunication()`——它创建 `commTask` 并**阻塞等待 `endpointListValid`**，确保 fibre 对象树（内含 `motorJ[1..6]->MakeProtocolDefinitions()`）在任何通信之前已发布；因此 `dummy` 必须是全局对象、在 `Main()` 之前就构造完 `motorJ[]`/`hand`，否则 `MakeProtocolDefinitions()` 会对空指针解引用。随后 `dummy.Init()`（设命令模式与默认速度）、IMU 以 `do{ Init(); osDelay(100); } while(!testConnection())` 死等连接、`oled.Init()`、`pwm.Start()`，再依次创建 4 个用户任务，最后 `timerCtrlLoop.SetCallback(OnTimer7Callback); timerCtrlLoop.Start()` 才真正开始 200Hz 控制环。

控制环的数据流是"中断只做唤醒"：TIM7 溢出 → `HAL_TIM_IRQHandler` → `HAL_TIM_PeriodElapsedCallback`（`Core/Src/main.c`）→ 非 TIM6 分支 `OnTimerCallback(TIM7)` → `Bsp/utils/timer.cpp` 的函数指针表 → `OnTimer7Callback()` → `vTaskNotifyGiveFromISR(controlLoopFixUpdateHandle)` + `portYIELD_FROM_ISR`；任务侧 `ulTaskNotifyTake(pdTRUE, portMAX_DELAY)` 被唤醒。使能状态下按 `dummy.commandMode` 分支：三种点位/轨迹模式都走 `dummy.MoveJoints(dummy.targetJoints)` + `UpdateJointPose6D()`，调参模式走 `tuningHelper.Tick(10)`（注意传的是常量 10ms，与 200Hz=5ms 的实际周期不符）；未使能时只 `UpdateJointAngles()`（主动发 CAN 查询角度）+ 正解。`OledTask` 里 `cmdModeNames[4][4] = {"SEQ","INT","TRJ","TUN"}` 用 `dummy.commandMode - 1` 索引，并把 `jointsStateFlag` 的 bit1~bit6 渲染成 `*`/`_`。

#### Robot/instances/dummy_robot.cpp 与 .h 详述

`DummyRobot` 是整个固件的业务中枢，持有 7 个 `CtrlStepMotor*`（`motorJ[0]` 是广播 ID 0 的"全体"伪电机，`motorJ[1..6]` 对应 6 个关节）、一个 `DummyHand*`（节点 7，夹爪）、一个 `DOF6Kinematic*`。构造函数里写死了**每个关节的减速比与软限位**：J1 `(inverse=true, reduction=30, -170~170)`、J2 `(false,30,-73~90)`、J3 `(true,30,35~180)`、J4 `(false,24,-180~180)`、J5 `(true,30,-120~120)`、J6 `(true,50,-720~720)`，`motorJ[ALL]` 为 `(id=0,false,1,-180~180)`；运动学实例为 `new DOF6Kinematic(0.109f, 0.035f, 0.146f, 0.115f, 0.052f, 0.072f)`（单位米，依次 L_BASE/D_BASE/L_ARM/L_FOREARM/D_ELBOW/L_WRIST）。常量：`REST_POSE = {0,-73,180,0,0,0}`、`DEFAULT_JOINT_SPEED = 30`、`DEFAULT_JOINT_ACCELERATION_BASES = {150,100,200,200,200,200}`、低/高加速度 30/100、默认模式 `COMMAND_TARGET_POINT_INTERRUPTABLE`。

关节空间运动的核心是 `MoveJ()`：先逐轴查软限位，再算 `deltaJoints = target - current`，用 `AbsMaxOf6()` 找出转角最大的轴，以它为基准算总时间 `time = maxAngle * reduction / jointSpeed`，然后给每轴分配 `dynamicJointSpeeds = |delta * reduction / time * 0.1f|`（注释标 `0~10r/s`）——这就是各轴同步到达的"梯形同步"实现；真正下发在 `MoveJoints()`，对每轴调 `motorJ[j]->SetAngleWithVelocityLimit(target - initPose, dynamicJointSpeeds)`。`MoveL()` 则调 `dof6Solver->SolveIK()` 拿 8 组解，逐组查软限位，在合法解里挑"与当前关节角偏差最大值最小"的一组，再转调 `MoveJ()`。角度反馈是纯回调式的：`UpdateJointAngles()` 只是广播一帧 `0x23` 请求，真正的 `currentJoints` 由 CAN 中断里的 `UpdateJointAnglesCallback()` 填充（`currentJoints.a[i-1] = motorJ[i]->angle + initPose.a[i-1]`），同时按 `motorJ[i]->state == FINISH` 维护 `jointsStateFlag` 的位；`IsMoving()` 判据是 `jointsStateFlag != 0b1111110`。`CalibrateHomeOffset()` 是两段式手动标定（限流 0.5A → `ApplyPositionAsHome()` → 回 Resting 姿态 → 再 `ApplyPositionAsHome()` → 恢复 1A → `Reboot()`），每步之间 `osDelay(500)`。

内部类 `CommandHandler` 是 USB/UART 协议层与控制环之间的解耦层：ASCII 回调只负责 `Push()` 进 16×64 的消息队列，`ControlLoopUpdateTask` 侧 `Pop(osWaitForever)` + `ParseCommand()`。`ParseCommand()` 按 `commandMode` 分成两套语义：`SEQUENTIAL`/`CONTINUES_TRAJECTORY` 模式下解析完会 `MoveJoints()` 触发一次立即下发，然后 `while(IsMoving() && IsEnabled()) osDelay(5)` **阻塞等运动完成**再回 `"ok"`（流控靠这个实现）；`INTERRUPTABLE` 模式则立刻回 `"ok"`、不等待，新指令直接覆盖 `targetJoints`。指令格式 `>j1,...,j6[,speed]`（关节，`&` 同义）、`@x,y,z,a,b,c[,speed]`（笛卡尔）；`sscanf` 返回值 6 表示不带速度、7 表示带速度。回复同时打到 `*usbStreamOutputPtr` 和 `*uart4StreamOutputPtr`。`TuningHelper::Tick()` 做 `time += 2π·f·dt`、`delta = amp·sin(time)` 的正弦扫频，按 `tuningFlag` 的 bit0~bit5 选轴，`SetFreqAndAmp()` 限幅 f∈[0.1,5]、amp∈[1,50]。

---

### Robot/ — 机器人本体：执行器驱动、运动学、整机实例

三层结构：`actuators/` 是电机驱动（`ctrl_step` 是本项目自研步进闭环驱动器，经 CAN1 控制；`mintasca` 是 INNFOS SCA 伺服的第三方 SDK）、`algorithms/kinematic/` 是 6 自由度正逆解、`instances/` 是把它们组装成整机的 `DummyRobot`。

| 文件 | 作用 | 关键符号/要点 |
|---|---|---|
| `.../Robot/instances/dummy_robot.h` | `DummyRobot` / `DummyHand` / 内部类 `TuningHelper`、`CommandHandler` 声明；fibre 对象树 | `#define ALL 0`；`enum CommandMode{COMMAND_TARGET_POINT_SEQUENTIAL=1, ..._INTERRUPTABLE, COMMAND_CONTINUES_TRAJECTORY, COMMAND_MOTOR_TUNING}`；`REST_POSE={0,-73,180,0,0,0}`；`DEFAULT_JOINT_ACCELERATION_BASES={150,100,200,200,200,200}`；`currentJoints/targetJoints/initPose/currentPose6D/jointsStateFlag/commandMode/motorJ[7]/hand` 均为 public；`MakeProtocolDefinitions()` 暴露 `calibrate_home_offset/homing/resting/joint_1..6/joint_all/hand/reboot/set_enable/set_rgb_enable/set_rgb_mode/move_j/move_l/set_joint_speed/set_joint_acc/set_command_mode/tuning`；头部注释给出各关节推荐参数表（`current_limit 2`、`acceleration 30`、`dce_kp 1000`（J3 为 1500）、`dce_kv 80`、`dce_ki 200`、`dce_kd 250`（J2 为 200）） |
| `.../Robot/instances/dummy_robot.cpp` | 上述类的实现 | `AbsMaxOf6()`；构造函数里的减速比/软限位魔数（见上）；`DOF6Kinematic(0.109,0.035,0.146,0.115,0.052,0.072)`；`MoveJ/MoveL/MoveJoints/SetJointSpeed/SetJointAcceleration/CalibrateHomeOffset/Homing/Resting/UpdateJointPose6D`（正解后 ×1000 把 m 换成 mm）；`Reboot()` = 广播重启 + `osDelay(500)` + `HAL_NVIC_SystemReset()`；`DummyHand::SetAngle()` 限幅 0~30°、CAN `StdId = 7<<7 | 0x02`，`SetMaxCurrent()` 限幅 0~1A、`mode=0x01`；`CommandHandler::{Push,Pop,ParseCommand,GetSpace,ClearFifo,EmergencyStop}`；`TuningHelper::{SetTuningFlag,Tick,SetFreqAndAmp}` |
| `.../Robot/actuators/ctrl_step/ctrl_step.hpp` | 步进闭环电机的 CAN 驱动类声明 | `class CtrlStepMotor`；`enum State{RUNNING,FINISH,STOP}`；`const uint32_t CTRL_CIRCLE_COUNT = 200*256`（50 步进细分计数，代码里实际未用）；成员 `nodeID/angle/angleLimitMax/angleLimitMin/temperature/inverseDirection/reduction/state`；`MakeProtocolDefinitions()` 暴露 `angle`(ro) 与 `reboot/get_temperature/set_enable_temperature/erase_configs/set_enable/set_position_with_time/set_position/set_velocity/set_velocity_limit/set_current/set_current_limit/set_node_id/set_acceleration/apply_home_offset/do_calibration/set_enable_on_boot/set_dce_kp/kv/ki/kd/set_enable_stall_protect/update_angle` |
| `.../Robot/actuators/ctrl_step/ctrl_step.cpp` | 把每个 API 翻译成一帧 CAN | 见下方详述的完整命令码表 |
| `.../Robot/algorithms/kinematic/6dof_kinematic.h` | DH 参数与 6 自由度解算接口 | `class DOF6Kinematic`；`RAD_TO_DEG = 57.295777754771045f`；`struct ArmConfig_t{L_BASE,D_BASE,L_ARM,L_FOREARM,D_ELBOW,L_WRIST}`；`float DH_matrix[6][4] // home,d,a,alpha`；`struct Joint6D_t{float a[6]; operator-}`、`struct Pose6D_t{X,Y,Z,A,B,C,R[9],hasR}`、`struct IKSolves_t{Joint6D_t config[8]; char solFlag[8][3]}`；`SolveFK()`、`SolveIK()` |
| `.../Robot/algorithms/kinematic/6dof_kinematic.cpp` | 正逆解实现 | 见下方详述 |
| `.../Robot/actuators/mintasca/sca.hpp` / `sca.cpp` | INNFOS SCA 伺服的 C++ 封装（606 行）；**本固件中未实例化，属"编译但不使用"** | `class SCA`；静态 `data[2][8]`、`txHeader[2]`、`RxMsg`、`Can1SendMsg/Can2SendMsg`（直接 `HAL_CAN_AddTxMessage`，失败重试 `0xFFF` 次，不经 `sem_canX_tx`）、`OnCanReceiveMsg()`→`canDispatch()`；构造默认 `reductionRatio=36`；`Init(bool _enableActuator)`、`Homing()`（阻塞轮询 `Position_Real` 到 ±0.1）、`SetMode/SetPosition/SetVelocity/SetCurrent/...`；`MakeProtocolDefinitions()` 暴露 `enable/disable/homing/get_error_code/clear_error/is_online/is_enable/set_mode/get_mode/set_position/get_position/set_velocity/get_velocity/set_current/get_current`；源码注释为 GBK 乱码 |
| `.../Robot/actuators/mintasca/sca_api.h` / `sca_api.c` | INNFOS 官方 SCA_API V1.5.3（3857 行） | `#define SCA_NUM_USE 2`、`CanOvertime 0xFFFF`、`CanPowertime 0xFFFFFF`、`SendInterval 200`、`SCA_Delay(x) delayMicroseconds(x)`；模式常量 `SCA_Current_Mode 0x01 / SCA_Velocity_Mode 0x02 / SCA_Position_Mode 0x03 / SCA_Profile_Position_Mode 0x06 / SCA_Profile_Velocity_Mode 0x07 / SCA_Homing_Mode 0x08`；`Actr_Enable 0x01 / Actr_Disable 0x00`、`Block 0x01 / Unblock 0x00`；`lookupActuators/setupActuators/getInstance/enableActuator/setPositionFast/...` |
| `.../Robot/actuators/mintasca/sca_protocol.h` / `sca_protocol.c` | INNFOS CAN 协议寄存器表 V1.5.2（939 行实现） | 按"读/写 + 数据宽度类"分组的命令码：`R1_Heartbeat 0x00`、`R1_Mode 0x55`、`R1_PowerState 0x2B`、`R2_Voltage 0x45`、`R2_Error 0xFF`、`R3_Current 0x04`、`R3_Velocity 0x05`、`R3_Position 0x06`、`R4_CVP 0x94`、`R5_ShakeHands 0x02`、`W1_Mode 0x07`、`W1_PowerState 0x2A`、`W3_Position 0x0A`、`W3_HomingValue 0x87`、`W4_ClearError 0xFE`、`W4_Save 0x0D` 等；`CAN_Handler_t`、`SCA_Handler_t`、`CanRxMsg`、`canDispatch()` |

#### Robot/algorithms/kinematic/6dof_kinematic.cpp 详述

该文件是纯数学模块，不依赖 HAL/RTOS，只用 CMSIS-DSP（`arm_cos_f32`/`arm_sin_f32`，文件开头用 `inline float cosf/sinf` 覆盖标准库以走硬件加速表）。基础工具：`MatMultiply(m,l,n)` 通用行主序矩阵乘、`RotMatToEulerAngle()` / `EulerAngleToRotMat()` 做旋转矩阵 ↔ 欧拉角（ZYX 顺序，输出顺序为 `[C,B,A]`，含 `|R[6]|≥1-1e-4` 的万向锁奇异处理）。构造函数把 6 组 `{home, d, a, alpha}` 填进 `DH_matrix`——关键的 home 偏置是 `θ2` 的 `-π/2` 与 `θ3` 的 `+π/2`，alpha 序列为 `{-π/2, 0, π/2, -π/2, π/2, 0}`；同时预算 `l_se`（大臂长）、`l_ew_2 = L_FOREARM² + D_ELBOW²`（小臂含肘偏置的等效长度平方），`l_ew` 与 `atan_e` 延迟到首次 `SolveIK()` 才算（`if (0 == l_ew)` 懒初始化）。

`SolveFK()` 不构造 4×4 齐次矩阵，而是分别累乘 6 个 3×3 旋转矩阵得到 `R02..R06`，再把四段连杆向量 `L1_base/L2_arm/L3_elbow/L6_wrist` 分别旋到基坐标并相加得位置 `P06`，最后 `RotMatToEulerAngle(R06, &P06[3])`——输入关节角单位是度（内部除 `RAD_TO_DEG`），输出位置单位是**米**（`DummyRobot::UpdateJointPose6D()` 负责 ×1000 转 mm），姿态转回度并把 `R06` 整体拷进 `Pose6D_t::R`。

`SolveIK()` 是解析法的"球腕 + 平面三角"分解，输出固定 8 组解，索引编码为 `4*ind_arm + 2*ind_elbow + ind_wrist`，`solFlag[i][0..2]` 三列分别标记肩/肘/腕的解有效性（`1` 正常、`0` 超出可达、`-1` 奇异退化、此时用 `_lastJoint6D` 兜底）。流程：输入位置先 `/1000` 从 mm 转米；若 `hasR == false` 则由欧拉角重建 `R06`，否则直接用 `_inputPose6D.R`；减掉腕长向量得腕心 `P0_w`；`qs = atan2(y,x)` 与 `atan2(-y,-x)` 给出肩的两个分支（`sqrt(x²+y²) ≤ 1e-6` 即肩奇异）；旋到 1 系后用余弦定理 `acos_a/acos_e` 解肘的两个分支（含 `l_se+l_ew-l_sw` 与 `l_sw-|l_se-l_ew|` 两种边界的 `1e-6` 判定、`acos` 入参的 ±1 钳位）；再由 `R36` 解腕三角 `qw`（`|R36[8]| ≥ 1-1e-6` 为腕奇异）。最后统一把超出 ±π 的角度**加减一个 π**（注意是 `M_PI` 而非 `2*M_PI`）并乘 `RAD_TO_DEG` 输出度。

#### Robot/actuators/ctrl_step/ctrl_step.cpp 详述

这个文件本质是一张"函数 → CAN 帧"的翻译表，是**读 CAN 协议时最该先看的文件**。统一帧格式：标准帧、`DLC = 8`、`txHeader.StdId = nodeID << 7 | mode`（高 4 位节点、低 7 位命令码），payload 前 4 字节是 `float`/`int32` 的小端字节拷贝，`canBuf[4]` 在"配置类"命令里是**是否写入 EEPROM 的标志**、在 `SetPositionSetPoint` 里是"需要 ACK"标志。发送一律走 `CanSendMessage(get_can_ctx(hcan), canBuf, &txHeader)`，即先 `osSemaphoreAcquire(sem_can1_tx)` 再 `HAL_CAN_AddTxMessage`。

完整命令码表：`0x01 SetEnable`（同时把 `state` 置为 `FINISH`/`STOP`）、`0x02 DoCalibration`、`0x03 SetCurrentSetPoint`、`0x04 SetVelocitySetPoint`、`0x05 SetPositionSetPoint`（`canBuf[4]=1` 需 ACK）、`0x07 SetPositionWithVelocityLimit`（pos 在 0~3 字节、vel 在 4~7 字节，**此帧没有 EEPROM 标志位**）、`0x11 SetNodeID`、`0x12 SetCurrentLimit`、`0x13 SetVelocityLimit`、`0x14 SetAcceleration`（`canBuf[4]=0`，唯一不存 EEPROM 的配置项）、`0x15 ApplyPositionAsHome`、`0x16 SetEnableOnBoot`、`0x17/0x18/0x19/0x1A SetDceKp/Kv/Ki/Kd`、`0x1B SetEnableStallProtect`、`0x23 UpdateAngle`（请求角度，回包由 `can_protocol.cpp` 的 `case 0x23` 处理）、`0x25 GetTemp`（回包 `case 0x25`）、`0x7d SetEnableTemp`、`0x7e EraseConfigs`、`0x7f Reboot`。

角度与电机圈数的换算集中在两个地方：下发侧 `SetAngle()` / `SetAngleWithVelocityLimit()` 做 `_angle = inverseDirection ? -_angle : _angle; stepMotorCnt = _angle / 360.0f * reduction;`（即把关节角度折算成**电机输出圈数**）；回读侧 `UpdateAngleCallback(float _pos, bool _isFinished)` 做反变换 `tmp = _pos / reduction * 360`，再按 `inverseDirection` 取反写入 `angle`，并把 `state` 设为 `FINISH`/`RUNNING`——`DummyRobot::IsMoving()` 完全依赖这个 `state`，所以**丢一帧 `0x23` 回包就会让上层误判运动状态**。`GetTemp()` 的返回值是上一次回调缓存的 `temperature`，不是本次请求的结果（请求是异步的）。

---

### Bsp/ — 板级支持包

分 5 个子目录：`communication/`（USB-CDC 双端点 / UART4+5 DMA / CAN1+2 的服务线程与 fibre 适配）、`gpio/`（ADC、编码器、PWM、WS2812）、`imu/`（MPU6050 + biquad 滤波）、`memory/`（Flash 模拟 EEPROM）、`utils/`（硬件定时器包装、微秒延时、软件 I2C、CMSIS-DSP 头）。

#### Bsp/communication/

| 文件 | 作用 | 关键符号/要点 |
|---|---|---|
| `.../Bsp/communication/communication.hpp` | 通信层对外接口 + `COMMIT_PROTOCOL` 宏 | `InitCommunication()`、`CommitProtocol()`、`CommunicationTask()`、`UsbDeferredInterruptTask()`；`#define COMMIT_PROTOCOL` 用 `treeBuffer[sizeof(treeType)]` + placement new 构造对象树再 `fibre_publish()` |
| `.../Bsp/communication/communication.cpp` | commTask / usbIrqTask 的实现；`printf` 重定向 | 详述见下 |
| `.../Bsp/communication/ascii_processor.hpp` | ASCII 行协议的声明与 `Respond()` 模板 | `ASCII_protocol_parse_stream()`；`template<typename...TArgs> void Respond(StreamSink&, const char* fmt, ...)`——**内部 `char response[64]`，超长会被 snprintf 截断**，并自动追加 `"\r\n"` |
| `.../Bsp/communication/ascii_processor.cpp` | 字节流 → 行 → 按通道分发 | `#define MAX_LINE_LENGTH 256`；`ASCII_protocol_parse_stream()` 用 **static** `parse_buffer/read_active/parse_buffer_idx` 做状态机（`\r` 或 `\n` 结束一行，超长则丢弃直到下一行）——**三个通道共用这一组 static 变量，多通道并发会串包**；`ASCII_protocol_process_line()` 按 `response_channel.channelType` 分发到 `OnUsbAsciiCmd` / `OnUart4AsciiCmd` / `OnUart5AsciiCmd` |
| `.../Bsp/communication/interface_can.hpp` | `CAN_context` 结构与 CAN 服务接口 | `struct CAN_context{handle, node_id, serial_number, node_ids_in_use_0/1[4], last_heartbeat_mailbox, tx_msg_cnt, sem_send_heartbeat, 各类回调计数器, received_msg_cnt, received_ack, unexpected_errors, unhandled_messages}`；`get_can_ctx()`、`StartCanServer()`、`CanSendMessage()`、`OnCanMessage()` |
| `.../Bsp/communication/interface_can.cpp` | CAN1/CAN2 初始化、全部 HAL 回调、发送原语 | `CAN_context can1Ctx, can2Ctx`；`get_can_ctx()` 按 `Instance` 返回；`StartCanServer(CAN_TypeDef*)` 配置**全通过滤波器**（`FilterIdHigh/Low=0`、`FilterMaskIdHigh/Low=0`、`FilterBank 0`、`CAN_RX_FIFO0`、`CAN_FILTERSCALE_16BIT`）后 `HAL_CAN_Start` + `HAL_CAN_ActivateNotification`（几乎开满所有中断）；`HAL_CAN_TxMailbox0/1/2CompleteCallback` → `tx_complete_callback()` → 释放 `sem_can1_tx`/`sem_can2_tx`；`HAL_CAN_RxFifo0MsgPendingCallback()` 里 `HAL_CAN_GetRxMessage(CAN_RX_FIFO0, &headerRx, data)` 后直接调用户的 `OnCanMessage()`（**static 的 `headerRx`/`data` 被 CAN1/CAN2 共用**）；`HAL_CAN_ErrorCallback()` 手动处理三个邮箱的 ALST（重置 `TXRQ` 重发）与 TERR；`CanSendMessage()` = 取信号量 + `HAL_CAN_AddTxMessage` |
| `.../Bsp/communication/interface_uart.hpp` | UART 服务接口 | `extern StreamSink* uart4StreamOutputPtr; extern StreamSink* uart5StreamOutputPtr;`、`StartUartServer()` |
| `.../Bsp/communication/interface_uart.cpp` | UART4/5 的 DMA 循环收 + DMA 发 | `#define UART_TX_BUFFER_SIZE 64`、`UART_RX_BUFFER_SIZE 64`；`static uint8_t dma_rx_buffer[2][64]`、`dma_last_rcv_idx[2]`；`class UART4Sender/UART5Sender : public StreamSink`（`channelType = CHANNEL_TYPE_UART4/5`，发送取 `sem_uart4_dma`/`sem_uart5_dma` 后 `HAL_UART_Transmit_DMA`，超时 `PROTOCOL_SERVER_TIMEOUT_MS`=10ms）；fibre 侧链路 `uart4_packet_output → uart4_channel → uart4_stream_input`（`StreamBasedPacketSink`/`BidirectionalPacketBasedChannel`/`StreamToPacketSegmenter`）；`UartServerTask()` 用 `UART_RX_BUFFER_SIZE - huart.hdmarx->Instance->NDTR` 追 DMA 写指针，处理回绕两段，每轮 `osDelay(1)`；`HAL_UART_TxCpltCallback()` 释放对应 DMA 信号量；**UART5 的两段处理里误用了 `uart4_stream_input.process_bytes()`（应为 `uart5_stream_input`）** |
| `.../Bsp/communication/interface_usb.hpp` | USB 接口与统计 | `extern StreamSink* usbStreamOutputPtr;`、`typedef struct{rx_cnt, tx_cnt, tx_overrun_cnt} USBStats_t`、`extern USBStats_t usb_stats_`、`usb_rx_process_packet()`、`StartUsbServer()` |
| `.../Bsp/communication/interface_usb.cpp` | USB-CDC 双端点（ASCII + fibre native） | `class USBSender : public PacketSink`（取 `sem_usb_tx` 超时则 `tx_overrun_cnt++` 后强行覆盖 TX 缓冲，注释承认"不再无损"）；`usb_packet_output_cdc(CDC_OUT_EP)` 与 `usb_packet_output_native(ODRIVE_OUT_EP)`；`class TreatPacketSinkAsStreamSink`（`channelType = CHANNEL_TYPE_USB`）实例 `usb_stream_output` → `usbStreamOutputPtr`；`BidirectionalPacketBasedChannel usb_channel(usb_packet_output_native)`；`struct USBInterface{rx_buf,rx_len,data_pending,out_ep,in_ep,usb_sender}` 的两个实例 `CDC_interface`/`ODrive_interface`；`UsbServerTask()` 等 `sem_usb_rx` 后分别走 `ASCII_protocol_parse_stream()` 或 `usb_channel.process_packet()`，再 `USBD_CDC_ReceivePacket()` 放行下一包；`usb_rx_process_packet()` 由 `CDC_Receive_FS` 调用 |

#### Bsp/communication/communication.cpp 详述

这个文件只有 89 行，但决定了整个固件的通信启动时序。`InitCommunication()` 在 `Main()` 最开头被调用，它创建 `commTask`（栈 **45000** 字节——全工程最大，因为 fibre 对象树的 JSON 生成与 `MakeObjTree()` 的模板展开都在这个栈上跑），然后 `while (!endpointListValid) osDelay(1)` 自旋等待。`CommunicationTask()` 里的顺序是：`CommitProtocol()`（placement new 构造对象树 + `fibre_publish()`）→ 置 `endpointListValid = true` 放行 `Main()` → 依次 `StartUartServer()`、`StartUsbServer()`、`StartCanServer(CAN1)`、`StartCanServer(CAN2)` → 进入 `osDelay(1000)` 空循环。因此 `CAN` 在 `dummy.Init()` 之前已经可用，但**对象树是在 `dummy` 的构造函数之后、`dummy.Init()` 之前发布的**。

另一个关键点是 `_write()` 的重写：标准库 `printf` 最终落到这里，而它**同时**写 `usbStreamOutputPtr` 和 `uart4StreamOutputPtr` 两个通道——这就是 `ascii_processor.hpp` 注释里"别用 printf，用 `Respond()`"的原因。`UsbDeferredInterruptTask()` 的设计意图是把 USB 中断的重活搬到 AboveNormal 优先级的任务里（等 `sem_usb_irq` → `HAL_PCD_IRQHandler` → `HAL_NVIC_EnableIRQ(OTG_FS_IRQn)` 重新开中断），但当前 `Core/Src/stm32f4xx_it.c` 的 `OTG_FS_IRQHandler()` 是**直接调 `HAL_PCD_IRQHandler`**、从不释放 `sem_usb_irq`，所以这个任务实际永久阻塞（见"值得注意的点"）。

#### Bsp/gpio/

| 文件 | 作用 | 关键符号/要点 |
|---|---|---|
| `.../Bsp/gpio/analog.hpp` / `analog.cpp` | ADC 的薄封装，转调 `Core/Src/adc.c` | `class Analog`；`enum AdcChannel_t{CH1,CH2,CH3,CH4}` 映射到 `ADC_CH1..ADC_CH4`（= `ADC_CHANNEL_12..15`，引脚 PC2/PC3/PC4/PC5）；`GetChipTemperature()`、`GetVoltage()`、`GetRaw()`；**本固件未实例化 `Analog`，`cmd_protocol.cpp` 直接调 C 版 `AdcGetVoltage/AdcGetChipTemperature`** |
| `.../Bsp/gpio/encoder.hpp` / `encoder.cpp` | TIM 编码器模式的 64 位圈数计数封装 | `class Encoder`；默认 `cpr = 4096`；`struct Config_t{cpr, inverse}` 经 fibre 暴露为 `config.cpr`/`config.inverse`；`GetCount()` = `GetCntLoop(htim->Instance) * 65536 + CNT`；`GetAngle(bool _useRAD)`；`Start()` = `ClearCntLoop` + `CNT=0` + `HAL_TIM_Encoder_Start_IT(TIM_CHANNEL_ALL)`；**本固件未实例化**（TIM2/TIM3 虽按编码器模式初始化但没人调 `Start()`） |
| `.../Bsp/gpio/pwm.hpp` / `pwm.cpp` | TIM9/TIM12 各 2 路 PWM | `class PWM`；`enum PwmChannel_t{CH_ALL, CH_A1, CH_A2, CH_B1, CH_B2}`；构造函数**自己完整重做** `HAL_TIM_PWM_Init` + `ConfigChannel` + `HAL_TIM_MspPostInit`（不走 `MX_TIM9/12_Init`），频率限幅 10~84000Hz，`Period = 999`，TIM9 预分频 `168000/f - 1`（APB2 定时器 168MHz）、TIM12 `84000/f - 1`（APB1 84MHz）；`SetDuty()` 把 0~1 映射成 `CCR = 1000 * duty`；引脚 **PA2=TIM9_CH1、PA3=TIM9_CH2、PB14=TIM12_CH1、PB15=TIM12_CH2** |
| `.../Bsp/gpio/rgb.hpp` | WS2812 灯带驱动（271 行，几乎全是头文件内联实现） | `class RGB`；`#define MAX_LED 12`、`USE_BRIGHTNESS 0`、`PI 3.14159265358979f`；`enum Rgb_style_t{RAINBOW, FADE, BLINK, ALLRed, ALLGreen, ALLBlue, ALLOff}`；`LED_Data[12][4]`（索引 0 存序号，1/2/3 存 **G,R,B**）、`pwmData[24*12+50]`；`WS2812_Send()` 用 `HAL_TIM_PWM_Start_DMA(&htim2, TIM_CHANNEL_4, pwmData, indx)`，码型 **1→CCR 70、0→CCR 30（周期 105）**，尾部补 30 个 0 做 reset，然后 `while(!data_sentflag){}` **忙等** DMA 完成；`Run()`、`Interrupt(flag)`、`Set_LED()`、`RainBow()/Fade()/Blink()/PureColor()`；`Sequence()` 是空壳 |
| `.../Bsp/gpio/rgb.cpp` | 仅 42 行：构造函数（空）、`Run()` 的 switch、`Interrupt()` | `RGB::RGB(uint8_t m)` 注释 `//init here` 实为空实现；`Run()` 的 switch **没有 `ALLOff` 分支**（落到 `default: break`），所以 `ThreadRGBUpdate` 里的 `rgb.Run(RGB::ALLOff)` 什么也不做；`PureColor(ALLOff)` 里也写的是 `r=0,g=10,b=0`（不是全黑） |

#### Bsp/imu/

| 文件 | 作用 | 关键符号/要点 |
|---|---|---|
| `.../Bsp/imu/MPU6050.hpp` / `MPU6050.cpp` | jrowberg i2cdevlib 的 STM32 HAL 移植（1062 / 3791 行），加了本项目自己的 `Update()`/`InitFilter()` | `class MPU6050`；`struct ImuDataRaw_t{int16_t ax..gz} dataRaw`、`struct ImuData_t{float ax..gz} data`；`Init()` = `setClockSource(MPU6050_CLOCK_PLL_XGYRO)` + `setFullScaleGyroRange(MPU6050_GYRO_FS_250)` + `setFullScaleAccelRange(MPU6050_ACCEL_FS_2)` + `setDLPFMode(MPU6050_DLPF_BW_98)` + `setSleepEnabled(false)`；`testConnection()` 判 `getDeviceID() == 0x34`；`Update(bool _useFilter)` = `getMotion6()` + 除 `accRangeScale`/`gyroRangeScale` + 可选 `biquadFilterApply()`；`InitFilter(200, 100, 50)` 对 6 轴各建一个 LPF；还包含整套 DMP / offset / FIFO / 从机寄存器 API（本项目未用） |
| `.../Bsp/imu/mpu6050_1.hpp` | **与 `MPU6050.hpp` 逐字节完全相同的冗余副本**（1062 行），无人 include | — |
| `.../Bsp/imu/MPU6050_6Axis_MotionApps20.h` / `MPU6050_9Axis_MotionApps41.h` | InvenSense DMP 固件镜像与初始化序列（782 / 887 行），第三方、本项目未用 | `dmpInitialize()` 等 |
| `.../Bsp/imu/i2c_dev.hpp` / `i2c_dev.cpp` | i2cdevlib 的 HAL 后端 | `I2Cdev_init(I2C_HandleTypeDef*)`；`I2Cdev_readBit/readBitW/readBits/readBitsW/readByte/readWord/readBytes/readWords`、`I2Cdev_writeBit/.../writeWords`；`#define I2CDEV_DEFAULT_READ_TIMEOUT 1000`；头里还 `#define true 1 / false 0` |
| `.../Bsp/imu/helper_3dmath.h` | i2cdevlib 的四元数/向量数学工具类（215 行） | `class Quaternion`、`class VectorInt16`、`class VectorFloat`；本项目未用 |
| `.../Bsp/imu/filters/biquad_filter.h` / `biquad_filter.c` | Betaflight 风格双二阶 IIR 滤波 | `BiquadFilter_t`、`filterApplyFnPtr`；`biquadFilterInitLPF(filter, _filterCallFreq, _cutoffFreq)`、`biquadFilterInit(..., Q, filterType)`、`biquadFilterUpdate/UpdateLPF`、`biquadFilterApply()`（DF2T）、`biquadFilterApplyDF1()`、`filterGetNotchQ()`、`nullFilterApply()` |
| `.../Bsp/imu/filters/filter_math.h` / `filter_math.c` | Betaflight 的快速数学库（183 / 346 行） | `sin_approx/cos_approx/atan2_approx/acos_approx/exp_approx/log_approx/pow_approx`、`quickMedianFilter3/5/7/9[f]`、`stdev_t` + `devPush/devVariance/devStandardDeviation`、`applyDeadband/fapplyDeadband`、`scaleRange[f]`、`constrain/constrainf`、`fix12_t` 定点辅助 |

#### Bsp/memory/

| 文件 | 作用 | 关键符号/要点 |
|---|---|---|
| `.../Bsp/memory/eeprom_interface.h` | Arduino 风格 `EEPROMClass` 模板封装（FlashStorage_STM32 v1.1.0） | `class EEPROMClass`；`read/update/write/get<T>/put<T>/isValid/commit/length/setCommitASAP`；`length()` 返回 `E2END + 1`；只在 `!defined(DATA_EEPROM_BASE)` 分支生效；`common_inc.h` 包含了它但本固件**没有定义任何 `EEPROMClass` 实例** |
| `.../Bsp/memory/emulated_eeprom.h` / `emulated_eeprom.cpp` | ST 官方的 Flash 模拟 EEPROM（91 / 321 行） | `eeprom_read_byte/write_byte`、`eeprom_buffer_fill/flush`、`eeprom_buffered_read_byte/write_byte`；F4 走 `FLASH_DATA_SECTOR = FLASH_SECTOR_TOTAL - 1`（**最后一个扇区，F405RG 为 Sector 11，0x080E0000 起 128KB**），`FLASH_PAGE_SIZE` 默认 1KB、`E2END = FLASH_PAGE_SIZE - 1`；flush 会整扇区擦除 |

#### Bsp/utils/

| 文件 | 作用 | 关键符号/要点 |
|---|---|---|
| `.../Bsp/utils/timer.hpp` / `timer.cpp` | 把 5 个基本定时器包装成"设频率 + 挂回调" | `class Timer`；`typedef void (*TimerCallback_t)()`；`static TimerCallback_t timerCallbacks[5]` 索引顺序为 **TIM7, TIM10, TIM11, TIM13, TIM14**；构造函数校验 `Instance` 必须是这 5 个之一（否则 `Error_Handler()`），频率限 1~10000000Hz，`CalcRegister()` 以 `psc` 从 0.5 开始倍增直到 `arr ≤ 65535`，**基准固定写死 84MHz**，APB2 的 TIM10/TIM11 再把 `PSC` ×2；`Start()` = `HAL_TIM_Base_Start_IT`；`extern "C" void OnTimerCallback(TIM_TypeDef*)` 是 `Core/Src/main.c` 的 `HAL_TIM_PeriodElapsedCallback` 的下游，**不检查回调指针是否为空** |
| `.../Bsp/utils/time_utils.h` / `time_utils.c` | 微秒级时间戳与忙等延时 | `micros()`（`HAL_GetTick()*1000 + (LOAD+1 - VAL)` 换算，用 `LL_SYSTICK_IsActiveCounterFlag()` 处理 tick 翻转竞态）、`millis()` = `HAL_GetTick()`、`delayMicroseconds(us)` = `us *= 23; while(us--) __NOP();`（**纯经验魔数 23，按 168MHz 粗估**） |
| `.../Bsp/utils/software_i2c/soft_i2c.h` / `soft_i2c.c` | GPIO 模拟 I2C，给 OLED 用 | `#define MYI2C_SCL_PIN GPIO_PIN_10 / PORT GPIOB`、`MYI2C_SDA_PIN GPIO_PIN_11 / PORT GPIOB`（**与 I2C2 复用同一对引脚 PB10/PB11**）；`#define I2C_SOFT ((I2C_TypeDef*)0x00000000UL)`、`extern I2C_HandleTypeDef hi2c0`（`soft_i2c.c` 里定义，`Instance` 即 `I2C_SOFT`，是 u8g2 判断走软/硬 I2C 的依据）；`#define CPU_FREQUENCY_MHZ 0`（注释写 `//4`，导致 `delay_xus()` 退化）；`Soft_I2C_Init/Start/Stop/Send_Byte/Read_Byte/Ack/NAck/Wait_Ack`、`SOFT_I2C_Master_Transmit(daddr, buff, len)`、`delay_xus()` |
| `.../Bsp/utils/arm_math/arm_math.h`、`arm_common_tables.h`、`arm_const_structs.h` | CMSIS-DSP 头文件（7157 / 121 / 66 行），**第三方，一般无需阅读** | 配合 `CMakeLists.txt` 里 `link_libraries("arm_cortexM4lf_math.a")`；`6dof_kinematic.cpp` 只用 `arm_cos_f32`/`arm_sin_f32` |

---

### Core/ — CubeMX 生成的 MCU 配置与中断

CubeMX 生成的框架代码，但有若干处关键的 `USER CODE` 手改——**读中断、时钟、外设引脚必须看这里**。

| 文件 | 作用 | 关键符号/要点 |
|---|---|---|
| `.../Core/Src/main.c` | C 侧 `main()`：序列号生成、时钟、外设初始化、启动调度器 | `uint64_t serialNumber`（由 `UID_BASE` 的 uuid0+uuid2 与 uuid1>>16 拼成）、`char serialNumberStr[13]`（12 位十六进制，用作 USB 序列号）、`uint64_t myserial = 8`（未使用）；`__attribute__((section(".ccmram"))) uint8_t ucHeap[configTOTAL_HEAP_SIZE]`——**FreeRTOS 64KB 堆放在 CCMRAM，靠 `-DconfigAPPLICATION_ALLOCATED_HEAP` 生效**；`SystemClock_Config()`：HSE + PLL M=4/N=168/P=DIV2/Q=7，AHB=DIV1、APB1=DIV4、APB2=DIV2，`FLASH_LATENCY_5`；初始化顺序 GPIO→DMA→I2C1/2→CAN1/2→USART1→I2C3→SPI1/SPI3→UART4→ADC1→UART5→TIM2→TIM3（**注意不含 TIM7/9/10/11/12，这些由 `Timer`/`PWM` 类自己初始化**）；`HAL_TIM_PeriodElapsedCallback()`：TIM6 → `HAL_IncTick()`，其他 → `OnTimerCallback(htim->Instance)`；`Error_Handler()` = 关中断死循环 |
| `.../Core/Src/freertos.c` | 7 个信号量与 `defaultTask`/`usbIrqTask` 的创建 | `MX_FREERTOS_Init()`（信号量初值见本节开头的表）；`usbIrqTask` 必须在 `MX_USB_DEVICE_Init()` 之前创建（注释明确说明），`stack_size = 500`、`osPriorityAboveNormal`；`defaultTask` `stack_size = 2000`、Normal；`StartDefaultTask()` = `MX_USB_DEVICE_Init()` → `Main()` → `vTaskDelete(defaultTaskHandle)` |
| `.../Core/Inc/FreeRTOSConfig.h` | 内核裁剪配置 | `configTOTAL_HEAP_SIZE ((size_t)65536)`、`USE_FreeRTOS_HEAP_4`、`configTICK_RATE_HZ 1000`、`configMAX_PRIORITIES 56`、`configMINIMAL_STACK_SIZE 128`、`configENABLE_FPU 1`、`configUSE_PREEMPTION 1`、`configSUPPORT_STATIC_ALLOCATION 1` 且 `DYNAMIC_ALLOCATION 1`、`configUSE_TRACE_FACILITY 1`、`configMAX_TASK_NAME_LEN 16`、`configLIBRARY_MAX_SYSCALL_INTERRUPT_PRIORITY 5`（**所以所有用 FreeRTOS API 的中断优先级都设成了 5 或更低的数字优先级，即 ≥5**）、`configLIBRARY_LOWEST_INTERRUPT_PRIORITY 15`、`configASSERT(x)` = 关中断死循环、`vPortSVCHandler`/`xPortPendSVHandler` 映射、`USE_CUSTOM_SYSTICK_HANDLER_IMPLEMENTATION 0` |
| `.../Core/Src/stm32f4xx_it.c` | 全部中断向量实现（558 行） | **手改处**：`NMI_Handler` 改成死循环；`CAN1_RX0_IRQHandler` 被改写为"只检查 FMP0 并直接调 `HAL_CAN_RxFifo0MsgPendingCallback(&hcan1)` 然后 `return`"，**绕过了 `HAL_CAN_IRQHandler`（因此 CAN1 的错误/TX 中断在 RX0 线上不被处理）**；`OTG_FS_IRQHandler` 直接调 `HAL_PCD_IRQHandler(&hpcd_USB_OTG_FS)`，**没有 `osSemaphoreRelease(sem_usb_irq)`**；其余为标准转发：`DMA1_Stream0→hdma_uart5_rx`、`DMA1_Stream2→hdma_uart4_rx`、`DMA1_Stream4→hdma_uart4_tx`、`DMA1_Stream7→hdma_uart5_tx`、`DMA2_Stream0→hdma_adc1`、`TIM2/TIM3`（编码器）、`TIM1_UP_TIM10`、`TIM1_TRG_COM_TIM11`、`TIM8_UP_TIM13`、`TIM8_TRG_COM_TIM14`、`TIM6_DAC`（HAL 时基）、`TIM7`（控制环）、`CAN1/CAN2 TX/RX0/RX1/SCE`、`UART4/UART5`、`SPI3`、`ADC` |
| `.../Core/Src/tim.c` | TIM2/3/7/9/10/11/12/13/14 的初始化、MSP、编码器圈数计数 | `htim2..htim14` 全部句柄定义；`volatile int64_t encCntLoop[2]`；`MX_TIM2_Init()`/`MX_TIM3_Init()` 为**编码器模式** `TIM_ENCODERMODE_TI12`、`IC1/IC2Filter = 4`、`Period = 65535`（引脚 **TIM2: PA15/PB3（AF1）**、**TIM3: PC6/PC7（AF2）**）；`MX_TIM7_Init()` `Prescaler = 83, Period = 9999`（= 84MHz/84/10000 = 100Hz，但运行时被 `Timer` 类按 200Hz 覆写）；TIM9 `PSC=7/ARR=999`、TIM12 `PSC=3/ARR=999`、TIM10/11/13/14 `PSC=167或83, ARR=9999`；NVIC 优先级统一 `(5,0)`；`HAL_TIM_MspPostInit()` 配 PWM 引脚（PA2/PA3 AF3_TIM9、PB14/PB15 AF9_TIM12）；文件末尾 `HAL_TIM_IC_CaptureCallback()` 在溢出时按 `CR1 & 0x10`（计数方向）增减 `encCntLoop`，并提供 `GetCntLoop()`、`ClearCntLoop()`、`GetEncoderCount()`（后三者**在非 TIM2/TIM3 时没有 return，是 UB**） |
| `.../Core/Src/can.c` | CAN1/CAN2 初始化与 MSP | `hcan1`/`hcan2`；两路均 `Prescaler = 7`、`SJW_1TQ`、`BS1_3TQ`、`BS2_2TQ` → APB1 42MHz / 7 = 6MHz，6 TQ/bit → **1 Mbps**；`Mode = CAN_MODE_NORMAL`、`AutoBusOff = DISABLE`、`AutoWakeUp = ENABLE`、**`AutoRetransmission = DISABLE`**（发送失败不自动重发，靠 `HAL_CAN_ErrorCallback` 手动重置 TXRQ）；CAN1 `TransmitFifoPriority = ENABLE`、CAN2 `DISABLE`；引脚 **CAN1: PB8=RX / PB9=TX（AF9）**、**CAN2: PB12=RX / PB13=TX（AF9）**，均 `GPIO_PULLUP` + `VERY_HIGH`；`HAL_RCC_CAN1_CLK_ENABLED` 引用计数（CAN2 依赖 CAN1 时钟）；NVIC 全部 `(5,0)` |
| `.../Core/Inc/main.h` | CubeMX 的引脚别名 | `KEY_Pin PC13`、`LED_Pin PC8`、`OLED_I2C2_SCL_Pin PB10`、`OLED_I2C2_SDA_Pin PB11`、`IMU_I2C1_SCL_Pin PB6`、`IMU_I2C1_SDA_Pin PB7`；`Error_Handler()` 声明 |
| `.../Core/Src/adc.c` + `Core/Inc/adc.h` | ADC1 + DMA 循环采样与换算 | `uint16_t adc1ValBuf[ADC_CHANNEL_REF + 1]`；`#define ADC_CH1..CH4 = ADC_CHANNEL_12..15`（引脚 **PC2/PC3/PC4/PC5**）、`ADC_CHANNEL_TEMP 4`、`ADC_CHANNEL_REF 5`；6 个 Rank 依次为 CH12/13/14/15/TEMPSENSOR/VREFINT；`MX_ADC1_Init()` 末尾 `HAL_ADC_Start_DMA(&hadc1, adc1ValBuf, NbrOfConversion)`，DMA2_Stream0 Channel0；`AdcGetChipTemperature()` 用 `TEMPSENSOR_CAL1/CAL2` 出厂校准值线性插值；`AdcGetVoltage()` / `AdcGetRaw()` 的通道→索引 switch |
| `.../Core/Src/i2c.c` | I2C1/2/3 初始化 | 三路 `ClockSpeed = 400000`、`DUTYCYCLE_2`、7 位地址；引脚 **I2C1: PB6/PB7（IMU）**、**I2C2: PB10/PB11（OLED，实际由软 I2C 顶替）**、**I2C3: PA8=SCL / PC9=SDA**；均 `GPIO_MODE_AF_OD` + `PULLUP` |
| `.../Core/Src/usart.c` | UART4/UART5/USART1 + 各自 DMA | 三路均 115200；**UART4: PA0/PA1（AF8）**，`hdma_uart4_rx = DMA1_Stream2`（Circular）、`hdma_uart4_tx = DMA1_Stream4`；**UART5: PC12=TX / PD2=RX（AF8）**，`hdma_uart5_rx = DMA1_Stream0`、`tx = DMA1_Stream7`；**USART1: PA9/PA10（AF7）**，无 DMA、代码里没人用；UART4/5 NVIC 优先级 `(6,0)` |
| `.../Core/Src/spi.c` | SPI1/SPI3 初始化 | `BaudRatePrescaler_2`；**SPI1: PA5=SCK / PA7=MOSI / PB4=MISO（AF5）**、**SPI3: PC10/PC11 + PB5**；本固件未使用 |
| `.../Core/Src/dma.c` | DMA 时钟与 NVIC | `MX_DMA_Init()`；DMA1_Stream0/2/4/7、DMA2_Stream0，NVIC 均 `(6,0)` |
| `.../Core/Src/stm32f4xx_hal_timebase_tim.c` | 把 HAL 时基从 SysTick 换到 **TIM6** | `HAL_InitTick()` 配置 TIM6 1kHz 中断 → `HAL_IncTick()`；这样 SysTick 可以完全交给 FreeRTOS |
| `.../Core/Src/gpio.c`、`stm32f4xx_hal_msp.c`、`syscalls.c`、`system_stm32f4xx.c`，以及 `Core/Inc/` 下 `adc.h/can.h/dma.h/gpio.h/i2c.h/spi.h/tim.h/usart.h/stm32f4xx_it.h/stm32f4xx_hal_conf.h` | 其余 CubeMX 生成的外设初始化/MSP/库配置，**基本无手改，按需查阅** | `MX_GPIO_Init()` 只配 `KEY_Pin`（PC13 输入上拉）与 `LED_Pin`（PC8 推挽，初值 SET）；`stm32f4xx_hal_conf.h` 决定启用哪些 HAL 模块；`syscalls.c` 提供 newlib 桩（真正的 `_write` 在 `communication.cpp` 里覆盖） |

---

### USB_DEVICE/ — USB CDC 设备（双端点）

CubeMX 的 USB Device CDC 框架，被**魔改成双端点**：端点 1 跑人类可读的 ASCII 协议（标准 VCP），端点 3（沿用 ODrive 的命名 `ODRIVE_*`）跑 fibre 二进制原生协议。

| 文件 | 作用 | 关键符号/要点 |
|---|---|---|
| `.../USB_DEVICE/App/usbd_cdc_if.c` | CDC 接口层，双端点收发 | `#define USB_RX_DATA_SIZE 64 / USB_TX_DATA_SIZE 64`（在 `usbd_cdc_if.h`）；四个缓冲 `CDCRxBufferFS / REFRxBufferFS / CDCTxBufferFS / REFTxBufferFS`；`USBD_Interface_fops_FS = {CDC_Init_FS, CDC_DeInit_FS, CDC_Control_FS, CDC_Receive_FS}`；`CDC_Init_FS()` 给 `CDC_OUT_EP` 和 `ODRIVE_OUT_EP` **各设一组 Tx/Rx 缓冲**；`CDC_Receive_FS(Buf, Len, endpoint_pair)` 直接转调 `usb_rx_process_packet()`（定义在 `interface_usb.cpp`）；`CDC_Transmit_FS(Buf, Len, endpoint_pair)` 按端点选 `hcdc->CDC_Tx` 或 `hcdc->REF_Tx`，`State != 0` 即返回 `USBD_BUSY`，长度 > 64 返回 `USBD_FAIL`；端点常量定义在被改过的 `Middlewares/.../usbd_cdc.h`：`CDC_IN_EP 0x81 / CDC_OUT_EP 0x01 / ODRIVE_IN_EP 0x83 / ODRIVE_OUT_EP 0x03` |
| `.../USB_DEVICE/App/usbd_desc.c`、`usb_device.c`、`USB_DEVICE/Target/usbd_conf.c` 及对应 `.h` | 描述符、设备初始化、HAL↔USB 库胶水层，**大体为生成代码** | `USBD_VID 0x1209`、`USBD_PID_FS 0x0D32`、`USBD_MANUFACTURER_STRING "Robot Embedded Framework"`、`USBD_PRODUCT_STRING_FS` 由 `CONFIG_FW_VERSION` 拼成 `REF 1.0 CDC Interface`；序列号字符串**不是**写死的 `"000000000001"`，而是 `USBD_SerialStrDescriptor()` 返回 `serialNumberStr`（取自 MCU UID）；`MX_USB_DEVICE_Init()` 在 `StartDefaultTask` 里调用；`usbd_conf.c` 里 `HAL_PCD_MspInit` 配 PA11/PA12（USB_OTG_FS）与 `OTG_FS_IRQn` |

---

### 构建与工程配置

| 文件 | 作用 | 关键符号/要点 |
|---|---|---|
| `.../dummy-ref-core-fw/CMakeLists.txt` | 主构建脚本（与 `CMakeLists_template.txt` **内容完全一致**，首行注明"AUTO GENERATED FROM THE TEMPLATE! DO NOT CHANGE"） | `project(Core-STM32F4-fw C CXX ASM)`、C++17 / C11；`-mcpu=cortex-m4 -mthumb -mfloat-abi=hard -mfpu=fpv4-sp-d16`；`add_compile_definitions(ARM_MATH_CM4;ARM_MATH_MATRIX_CHECK;ARM_MATH_ROUNDING)`；`add_definitions(-DUSE_HAL_DRIVER -DSTM32F4 -DSTM32F4xx -DSTM32F405xx -DconfigAPPLICATION_ALLOCATED_HEAP)`（最后一项让 `ucHeap` 能放进 CCMRAM）；`COMMON_FLAGS` 含 `-u _printf_float -u _scanf_float`（**这是 `%f` 解析能工作的前提**，但该变量只定义未使用）；构建类型映射 Release→`-Ofast`、RelWithDebInfo→`-Ofast -g`、MinSizeRel→`-Os`、默认→`-Og -g`；`include_directories` 列出全部 BSP/3rdParty 路径；`file(GLOB_RECURSE SOURCES "startup/*.*" "Drivers/*.*" "Core/*.*" "UserApp/*.*" "3rdParty/*.*" "Middlewares/*.*" "USB_DEVICE/*.*" "Robot/*.*" "Bsp/*.*")`（**通配 `*.*`，新增文件无需改脚本，但也会把 `.h`/`.lua`/`.md` 一起塞进源列表**）；`link_libraries("arm_cortexM4lf_math.a")` + `link_directories("Drivers/CMSIS/Lib")`；链接选项 `-Wl,-gc-sections,--print-memory-usage,-Map=...`；POST_BUILD 用 objcopy 产出 `.hex` 和 `.bin` |
| `.../dummy-ref-core-fw/STM32F405RGTx_FLASH.ld` | 链接脚本 | `ENTRY(Reset_Handler)`、`_estack = 0x20020000`、`_Min_Heap_Size = 0x3C00`、`_Min_Stack_Size = 0x800`；`MEMORY{ RAM 0x20000000 128K; CCMRAM 0x10000000 64K; FLASH 0x8000000 1024K }`；段顺序 `.isr_vector → .text → .rodata → .ARM → .preinit/init/fini_array → .data(>RAM AT>FLASH) → .ccmram(>CCMRAM AT>FLASH，符号 _siccmram/_sccmram/_eccmram) → .bss → ._user_heap_stack`；**`.ccmram` 段是 `ucHeap` 的落脚处，`startup` 负责从 Flash 搬运初值** |
| `.../dummy-ref-core-fw/startup/startup_stm32f405xx.s` | ST 官方 F405 启动文件 | `g_pfnVectors` 向量表、`Reset_Handler`（拷 `.data`、清 `.bss`、`SystemInit`、`__libc_init_array`、`main`）、`Default_Handler`；`.fpu softvfp`（实际 FPU 由编译选项开启）；**注意它不含 `.ccmram` 的搬运代码——若 `ucHeap` 需要初值会有问题，但 heap 本身无需初始化** |
| `.../dummy-ref-core-fw/REF-STM32F4-fw.ioc` | CubeMX 工程文件（19751 字节） | `Mcu.Name = STM32F405RGTx`、`Mcu.Family = STM32F4`；`FREERTOS.configTOTAL_HEAP_SIZE = 65536`、`configENABLE_FPU = 1`、`configUSE_TRACE_FACILITY = 1`；`FREERTOS.Tasks01 = defaultTask,24,500,StartDefaultTask,Default,...`（**CubeMX 里 defaultTask 栈登记为 500，代码里实际是 2000**）；IP 列表含 FREERTOS、USB_DEVICE、ADC1、CAN1/2、I2C1/2/3、SPI1/3、TIM2/3/7/9~14、UART4/5、USART1；`Mcu.PinN` 列出所有被占用引脚 |
| `.../dummy-ref-core-fw/.mxproject` | CubeMX 的生成记录（20621 字节），**自动生成，一般无需阅读** | 记录 `PreviousLibFiles` / `PreviousUsedSW4STM32Files` / `PreviousGenFiles`；里面残留原作者的绝对路径 `I:/onWorking/_Private/Dummy-Robot-dev/2.Firmware/Core-STM32F4-fw/`，可见该固件原名为 **Core-STM32F4-fw** |
| `.../dummy-ref-core-fw/stlink.cfg` | OpenOCD 配置 | `source [find interface/stlink.cfg]`、`transport select hla_swd`、`source [find target/stm32f4x.cfg]`、`adapter speed 10000`；注释里留了切 cmsis-dap 与设 `FLASH_SIZE` 的开关 |
| `.../dummy-ref-core-fw/.cproject`、`.project` | 旧 SW4STM32 / Eclipse 工程文件，**与 CMake 构建无关，已废弃** | — |
| `.../dummy-ref-core-fw/.gitignore` | 仅一行 `cmake-build-*` | — |

### 第三方与自动生成目录（一句话概述，一般无需阅读）

- `.../dummy-ref-core-fw/Drivers/` — **第三方/自动生成，一般无需阅读**：ST 官方 STM32F4xx HAL 驱动 + CMSIS 内核/设备头 + 预编译的 `Drivers/CMSIS/Lib/arm_cortexM4lf_math.a`。
- `.../dummy-ref-core-fw/Middlewares/` — **第三方，一般无需阅读**（但**有两处本项目的改动**）：FreeRTOS 10.3.1 内核 + CMSIS_RTOS_V2 封装 + ST USB Device Library；`Class/CDC/Inc/usbd_cdc.h` 被加入了 `ODRIVE_IN_EP/ODRIVE_OUT_EP` 第二组端点，`Class/CDC/Src/usbd_cdc.c` 被插入了 `osSemaphoreRelease(sem_usb_tx)`（TX 完成释放信号量）。
- `.../dummy-ref-core-fw/3rdParty/fibre/` — **第三方，一般无需阅读**：ODrive 的 fibre RPC 协议栈（`protocol.hpp` 1300+ 行模板元编程 + `protocol.cpp`）；查协议细节时的有用常量：`PROTOCOL_SERVER_TIMEOUT_MS = 10`、`CANONICAL_CRC8_POLYNOMIAL 0x37 / INIT 0x42`、`CANONICAL_CRC16_POLYNOMIAL 0x3d65 / INIT 0x1337`、`enum{CHANNEL_TYPE_USB, CHANNEL_TYPE_UART4, CHANNEL_TYPE_UART5}`、`fibre_publish()`、`make_protocol_function/_object/_property/_ro_property/_member_list`。
- `.../dummy-ref-core-fw/3rdParty/u8g2/` — **第三方，一般无需阅读**：u8g2 单色屏图形库 + C++ 封装；本项目相关的两个点是 `cpp/U8g2lib.hpp` 里的 `class SSD1306 : public U8G2`（`u8g2_Setup_ssd1306_i2c_128x80_noname_f`，旋转 `U8G2_R3`，`Init()` 会在 `Instance == I2C_SOFT` 时调 `Soft_I2C_Init()`）和 `u8g2_stm32f4.c` 的 HAL 后端（`u8x8_byte_stm32_hw_i2c` / `u8x8_byte_stm32_hw_spi` / `u8x8_stm32_gpio_and_delay`，按 `I2C_SOFT` 分流到 `SOFT_I2C_Master_Transmit` 或 `HAL_I2C_Master_Transmit`）。
- `.../dummy-ref-core-fw/cmake-build-debug/`、`.../.idea/`、`.../usb-fs.tar.gz` — **构建产物 / IDE 配置 / 打包备份，无需阅读**。

---

### 本固件可回答的典型问题 → 去哪个文件

1. 问：六轴逆解算法怎么实现的？解有多少组、怎么选？ → 读 `source/1.Dummy V2任同学整理/2.Firmware/dummy-ref-core-fw/Robot/algorithms/kinematic/6dof_kinematic.cpp` 的 `DOF6Kinematic::SolveIK()`（8 组解 + `solFlag[8][3]`）；选解逻辑在 `Robot/instances/dummy_robot.cpp` 的 `DummyRobot::MoveL()`。
2. 问：正解（FK）怎么算的？DH 参数在哪里？ → 读 `6dof_kinematic.cpp` 的 `DOF6Kinematic::SolveFK()` 与构造函数里的 `tmp_DH_matrix`；臂长实参在 `dummy_robot.cpp` 构造函数 `new DOF6Kinematic(0.109f, 0.035f, 0.146f, 0.115f, 0.052f, 0.072f)`。
3. 问：200Hz 控制环是怎么触发的？为什么用任务通知而不是信号量？ → 读 `UserApp/main.cpp` 的 `OnTimer7Callback()` 与 `ThreadControlLoopFixUpdate()`，中断转发链看 `Core/Src/main.c: HAL_TIM_PeriodElapsedCallback()` → `Bsp/utils/timer.cpp: OnTimerCallback()`。
4. 问：给电机发 CAN 指令的命令码表是什么？某个功能对应哪个 mode？ → 读 `Robot/actuators/ctrl_step/ctrl_step.cpp`（`StdId = nodeID<<7 | mode`，0x01~0x7f 全表）；收包解析在 `UserApp/protocols/can_protocol.cpp: OnCanMessage()`。
5. 问：上位机发的 `>0,0,90,0,0,0,30` 这种指令是怎么一路走到电机的？ → 顺序读 `Bsp/communication/interface_usb.cpp: UsbServerTask()` → `Bsp/communication/ascii_processor.cpp: ASCII_protocol_parse_stream()` → `UserApp/protocols/ascii_protocol.cpp: OnUsbAsciiCmd()` → `Robot/instances/dummy_robot.cpp: CommandHandler::Push()/ParseCommand()` → `MoveJ()`/`MoveJoints()` → `ctrl_step.cpp: SetAngleWithVelocityLimit()`。
6. 问：三种/四种命令模式（SEQ/INT/TRJ/TUN）行为差异在哪？ → 读 `Robot/instances/dummy_robot.cpp` 的 `DummyRobot::SetCommandMode()`（设加速度与 `jointSpeedRatio`）和 `CommandHandler::ParseCommand()`（是否阻塞等待运动完成）；枚举定义在 `Robot/instances/dummy_robot.h`。
7. 问：各关节的减速比、软限位、方向取反在哪里配置？ → 读 `Robot/instances/dummy_robot.cpp` 的 `DummyRobot::DummyRobot()` 构造函数；推荐 PID 参数表在 `Robot/instances/dummy_robot.h` 文件头注释。
8. 问：多轴速度是怎么同步的 / `set_joint_speed` 的单位是什么？ → 读 `Robot/instances/dummy_robot.cpp` 的 `MoveJ()` 中 `dynamicJointSpeeds` 计算与 `SetJointSpeed()`（0~100 限幅后乘 `jointSpeedRatio`）。
9. 问：零点标定（home offset）的流程是什么？ → 读 `Robot/instances/dummy_robot.cpp: DummyRobot::CalibrateHomeOffset()`，底层命令是 `ctrl_step.cpp: ApplyPositionAsHome()`（mode `0x15`）。
10. 问：FreeRTOS 有几个任务、优先级和栈多大？堆放在哪？ → 任务创建看 `UserApp/main.cpp: Main()` + `Core/Src/freertos.c: MX_FREERTOS_Init()` + `Bsp/communication/communication.cpp`/`interface_usb.cpp`/`interface_uart.cpp` 里的 `*_attributes`；堆大小看 `Core/Inc/FreeRTOSConfig.h: configTOTAL_HEAP_SIZE`，存放位置看 `Core/Src/main.c` 的 `__attribute__((section(".ccmram"))) uint8_t ucHeap[]` 与 `STM32F405RGTx_FLASH.ld` 的 `.ccmram` 段。
11. 问：7 个信号量各自保护什么？谁 give 谁 take？ → 读 `Core/Src/freertos.c`（创建与初值）、`UserApp/freertos_inc.h`（声明）、`Bsp/communication/interface_can.cpp: tx_complete_callback()`、`interface_uart.cpp: HAL_UART_TxCpltCallback()`、`interface_usb.cpp: USBSender::process_packet()`。
12. 问：USB 为什么能同时跑文本指令和二进制协议？端点号是多少？ → 读 `Bsp/communication/interface_usb.cpp`（`CDC_interface` vs `ODrive_interface`）与 `USB_DEVICE/App/usbd_cdc_if.c: CDC_Init_FS()/CDC_Transmit_FS()`；端点常量在 `Middlewares/ST/STM32_USB_Device_Library/Class/CDC/Inc/usbd_cdc.h`。
13. 问：UART 是怎么无中断收包的？波特率、引脚是多少？ → 读 `Bsp/communication/interface_uart.cpp: UartServerTask()/StartUartServer()`（追 `hdmarx->Instance->NDTR`）；波特率与引脚在 `Core/Src/usart.c`（115200，UART4=PA0/PA1，UART5=PC12/PD2）。
14. 问：CAN 波特率怎么算出 1Mbps 的？滤波器怎么配的？ → 读 `Core/Src/can.c: MX_CAN1_Init()`（`Prescaler 7`/`BS1 3TQ`/`BS2 2TQ`，APB1=42MHz）与 `Bsp/communication/interface_can.cpp: StartCanServer()`（全通滤波器 + `HAL_CAN_ActivateNotification`）。
15. 问：OLED 显示的内容和刷新逻辑在哪？为什么走软件 I2C？ → 读 `UserApp/main.cpp: ThreadOledUpdate()`；驱动入口 `3rdParty/u8g2/cpp/U8g2lib.hpp` 的 `class SSD1306` 与 `3rdParty/u8g2/u8g2_stm32f4.c`；软 I2C 的 `hi2c0`/引脚定义在 `Bsp/utils/software_i2c/soft_i2c.h` 与 `soft_i2c.c`。
16. 问：IMU 数据是怎么读取和滤波的？量程设置是多少？ → 读 `Bsp/imu/MPU6050.cpp` 的 `MPU6050::Init()`（±2g / ±250°/s / DLPF 98Hz）、`Update()`、`InitFilter()`，以及 `Bsp/imu/filters/biquad_filter.c`；调用点在 `UserApp/main.cpp: ThreadOledUpdate()` 的 `mpu6050.Update(true)`。
17. 问：WS2812 灯带是怎么驱动的？灯效模式有哪些？ → 读 `Bsp/gpio/rgb.hpp` 的 `WS2812_Send()`（TIM2 CH4 PWM+DMA，码型 70/30）与 `RainBow()/Fade()/Blink()/PureColor()`，模式分发在 `Bsp/gpio/rgb.cpp: RGB::Run()`，任务在 `UserApp/main.cpp: ThreadRGBUpdate()`，DMA 完成回调在 `UserApp/main.cpp: HAL_TIM_PWM_PulseFinishedCallback()`。
18. 问：`reftool`/上位机看到的那些 RPC 节点（`robot.joint_1.set_position` 等）是在哪定义的？ → 读 `UserApp/protocols/cmd_protocol.cpp: MakeObjTree()`，再逐层看 `dummy_robot.h`、`ctrl_step.hpp`、`sca.hpp` 里的 `MakeProtocolDefinitions()`；发布机制在 `Bsp/communication/communication.hpp` 的 `COMMIT_PROTOCOL` 宏 + `3rdParty/fibre/cpp/include/fibre/protocol.hpp: fibre_publish()`。
19. 问：USB 序列号/VID/PID/产品名是什么？怎么生成的？ → 读 `USB_DEVICE/App/usbd_desc.c`（`USBD_VID 0x1209`、`USBD_PID_FS 0x0D32`）与 `Core/Src/main.c` 开头由 `UID_BASE` 生成 `serialNumber`/`serialNumberStr` 的代码。
20. 问：怎么编译烧录？优化等级和链接脚本怎么改？ → 读 `dummy-ref-core-fw/CMakeLists.txt`（注意首行"由模板生成，勿改"，要改应改 `CMakeLists_template.txt`）、`STM32F405RGTx_FLASH.ld`、`stlink.cfg`。
21. 问：`printf` 输出到哪里去了？为什么建议用 `Respond()`？ → 读 `Bsp/communication/communication.cpp` 末尾的 `_write()`（同时写 USB 和 UART4）与 `Bsp/communication/ascii_processor.hpp` 的 `Respond()` 模板。
22. 问：系统时基、`micros()`、`delayMicroseconds()` 分别用的什么硬件？ → 读 `Core/Src/stm32f4xx_hal_timebase_tim.c`（HAL tick 走 TIM6）、`Bsp/utils/time_utils.c`（`micros()` 读 SysTick、`delayMicroseconds()` 是 `us*23` 的 NOP 忙等）、`Core/Inc/FreeRTOSConfig.h`（`configTICK_RATE_HZ 1000`）。

---

### 值得注意的点（阅读/排查时优先怀疑）

- **`usbIrqTask` 实际永久阻塞**：`Core/Src/stm32f4xx_it.c: OTG_FS_IRQHandler()` 直接调 `HAL_PCD_IRQHandler`，全工程没有任何地方 `osSemaphoreRelease(sem_usb_irq)`，所以 `Bsp/communication/communication.cpp: UsbDeferredInterruptTask()` 的"延迟中断处理"从未被唤醒（该任务白占 500 字节栈）。
- **UART5 接收路径的复制粘贴 bug**：`Bsp/communication/interface_uart.cpp` 第 157 / 166 行对 UART5 的 DMA 数据调用了 `uart4_stream_input.process_bytes()`，应为 `uart5_stream_input`；结果 UART5 的 fibre 二进制流被灌进了 UART4 的分包器。此外 `OnUart5AsciiCmd()`（`ascii_protocol.cpp`）是空函数，UART5 的 ASCII 指令无任何响应。
- **`rgb.Run(RGB::ALLOff)` 是空操作**：`Bsp/gpio/rgb.cpp: RGB::Run()` 的 switch 缺 `ALLOff` 分支；而 `PureColor(ALLOff)` 里也写成 `r=0, g=10, b=0`（不是全灭）。
- **TIM2 被两套用途争用**：`Core/Src/tim.c: MX_TIM2_Init()` 把 TIM2 配成编码器模式（PA15/PB3），而 `Bsp/gpio/rgb.hpp: WS2812_Send()` 用 `HAL_TIM_PWM_Start_DMA(&htim2, TIM_CHANNEL_4, ...)` 发灯带数据——两者互斥；同理 PB10/PB11 既配了 I2C2 又被 `soft_i2c.h` 当作软 I2C 引脚。
- **`WS2812_Send()` 在 Normal 优先级任务里忙等**：`while (!data_sentflag){}`，若 DMA 完成回调没来就会死等；而 `data_sentflag` 是普通 `uint8_t`（非 `volatile`），`-Ofast` 下有被优化掉的风险。
- **`AdcGetVoltage()` 的实现被改坏了**：`Core/Src/adc.c` 里真正的换算公式被注释掉，函数算出 `index` 后完全不用它，只返回 VREFINT 推算出的参考电压，与通道无关。`UserApp/protocols/cmd_protocol.cpp` 传入的 `TEST_ADC_CHANNEL_0 = 0` 也不匹配任何 `ADC_CHx`（= 12~15）。
- **`ascii_processor.cpp` 的行缓冲是三通道共用的 `static`**：`parse_buffer` / `read_active` / `parse_buffer_idx` 没有按通道区分，USB 与 UART 同时有数据时会串包。
- **`interface_can.cpp` 的 `headerRx` / `data` 也是全局 static**：CAN1 与 CAN2 的接收中断共用，且 `OnCanMessage()` 在中断上下文里被调用（里面还跑了 `UpdateJointAnglesCallback()` 的 6 轴循环）。
- **`Core/Src/stm32f4xx_it.c: CAN1_RX0_IRQHandler()` 提前 `return`**，`HAL_CAN_IRQHandler(&hcan1)` 成为死代码——该中断线上的错误标志不会被 HAL 清理。
- **`UserApp/freertos_inc.h` 的注释与代码矛盾**：注释标 `commTask 48000 / oledTask 4000 / controlLoopFixUpdate 4000`，实际代码分别是 `45000 / 2000 / 2000`；`.ioc` 里 `defaultTask` 栈登记 500，代码里是 2000。注释称"60K used / 64K"需按实际栈值重新核算。
- **`Bsp/utils/timer.cpp: OnTimerCallback()` 不判空**：若某个 TIM 的中断已使能但没 `SetCallback()`，会跳到空指针（当前只有 TIM7 设了回调，而 `MX_TIM10/11/13/14_Init` 的 MSP 都 `HAL_NVIC_EnableIRQ` 了）。`CalcRegister()` 还把时钟基准写死成 84MHz，对 APB2 的 TIM10/11 只靠 `PSC * 2` 近似补偿。
- **`Core/Src/tim.c` 的 `GetCntLoop()` / `GetEncoderCount()` 缺 default return**，非 TIM2/TIM3 入参时返回值未定义。
- **`SCA`（mintasca）整个模块在本固件中未被实例化**：`common_inc.h` 包含了 `sca.hpp`，但没有任何 `SCA` 对象；它的 `Can1SendMsg/Can2SendMsg` 还绕过了 `sem_canX_tx` 直接 `HAL_CAN_AddTxMessage`，若启用会与 `CanSendMessage()` 的信号量保护冲突。`Bsp/gpio/encoder.hpp`（`Encoder`）、`Bsp/gpio/analog.hpp`（`Analog`）、`Bsp/memory/eeprom_interface.h`（`EEPROMClass`）同样是"编译但无实例"。
- **`Bsp/imu/mpu6050_1.hpp` 是 `MPU6050.hpp` 的逐字节重复副本**（1062 行），无人 include，纯冗余。
- **`DummyRobot::TuningHelper::Tick(10)`**（`UserApp/main.cpp`）传的是固定 10ms，但调用频率是 200Hz（5ms），导致调参正弦的实际频率是设定值的两倍。
- **`ascii_protocol.cpp` 里多处把 `&&` 写成按位 `&`**：`if (node >= 1 & node <= 6)`，当前语义上凑巧正确但是明显笔误；另外 `#SET_DCE_*` 的局部变量命名为 `kp` 却被 KI/KD 分支复用。
- **`soft_i2c.h` 的 `CPU_FREQUENCY_MHZ` 被设为 0**（注释里原值是 4），使 `delay_xus()` 的计算退化为不减；软 I2C 的时序实际靠 HAL GPIO 调用本身的开销撑着。
- **`Middlewares/` 不是纯净的上游代码**：`Class/CDC/Inc/usbd_cdc.h` 加了 `ODRIVE_*_EP`，`Class/CDC/Src/usbd_cdc.c` 插了 `osSemaphoreRelease(sem_usb_tx)`——升级 ST 库会直接破坏 USB 双端点功能。
- **`CMakeLists.txt` 的 `COMMON_FLAGS` 定义后未被使用**：`-u _printf_float -u _scanf_float` 并没有真正加进编译/链接选项（`%f` 目前能用是因为 `nano.specs` 之外的默认行为，属脆弱依赖）；`.mxproject` 里残留原作者绝对路径，显示本固件原名为 `Core-STM32F4-fw`。

---

## 八、关节电机固件(42 / 35)

关节电机固件是跑在每个关节的**闭环步进电机驱动板**上的程序,与主控(`dummy-ref-core-fw`,STM32F4 + FreeRTOS)通过 **CAN 总线**通信。两套固件(42 步进电机 / 35 步进电机)均为:

- MCU:**STM32F103CBT6**(128K Flash / 20K RAM,Cortex-M3,HSE 12MHz × PLL6 = **72MHz**)
- **纯裸机,无 FreeRTOS**。闭环控制靠 `TIM4` 20kHz 中断,外设/按键/LED 靠 `TIM1` 100Hz 中断,主循环 `for(;;)` 只做编码器标定收尾和 EEPROM 落盘
- 驱动芯片:**TB67H450**(双 H 桥 + V-ref 电流设定,0.1Ω 采样电阻 → 0~3300mV V-ref 对应 0~3300mA)
- 位置传感器:**MT6816** 14 位磁编码器(SPI1,软片选 PA15)
- 工程上游是开源项目 **XDrive_Step / Ctrl-Step**(unlir "知不知啊"),CMake 工程名 `Ctrl-Step-STM32-fw`

两套固件的目录结构与代码**几乎完全相同**(`diff -rq` 仅 5 个文件有差异,其中唯一的功能性差异是 `dce_kp`)。因此下文**以 42 为主**逐文件详述,差异单列一节。

仓库内路径前缀(下文表格中省略):
`source/1.Dummy V2任同学整理/2.Firmware/dummy-42motor-fw/`

---

### 顶层 / 构建配置

工程用 CLion 风格的 CMake + arm-none-eabi 工具链交叉编译,CubeMX 负责生成 `Core/`、`Drivers/`,业务代码在 `Ctrl/`、`Port/`、`UserApp/` 三层(算法层 / 平台移植层 / 应用层)。

| 文件 | 作用 | 关键符号/要点 |
|---|---|---|
| `CMakeLists.txt` | 实际使用的构建脚本 | `project(Ctrl-Step-STM32-fw C CXX ASM)`;C++17 / C11;`-mcpu=cortex-m3 -mthumb -mthumb-interwork`;宏 `-DUSE_HAL_DRIVER -D__MICROLIB -DSTM32F1 -DSTM32F1xx -DSTM32F103xB`;`file(GLOB_RECURSE)` 收集 `startup/ Drivers/ Core/ Ctrl/ UserApp/ Port/`;POST_BUILD 产出 `.hex` 和 `.bin`;Debug 默认 `-Og -g`,Release `-Ofast` |
| `CMakeLists_template.txt` | CLion/CubeMX 的模板源文件 | **与 `CMakeLists.txt` 逐字节相同**(`diff` 无输出)。首行注释 "AUTO GENERATED FROM THE TEMPLATE! DO NOT CHANGE!" 指的就是它 |
| `STM32F103CBTx_FLASH.ld` | 链接脚本 | `RAM : 0x20000000, 20K`;`FLASH : 0x08000000, 128K`;`_estack = 0x20005000`;`_Min_Heap_Size = 0x200`(512B)、`_Min_Stack_Size = 0x400`(1K)。**注意:脚本把整片 128K Flash 都给了代码,没有为 0x08017C00 起的 32K 编码器标定区 + 1K EEPROM 区做保留**,固件膨胀到 >95K 会覆盖标定数据(当前 Debug 构建 bin 仅 74KB,尚安全) |
| `stlink.cfg` | OpenOCD 下载脚本 | `source [find interface/stlink.cfg]`;`transport select hla_swd`;`source [find target/stm32f1x.cfg]`;`adapter speed 10000`(10MHz) |
| `Ctrl-Step-fw.xml` | SW4STM32/TrueSTUDIO 目标定义 | `<mcuId>STM32F103CBTx</mcuId>`、`<dbgIF>SWD</dbgIF>`、`<dbgDEV>ST-LinkV2-1</dbgDEV>` |
| `startup/startup_stm32f103xb.s` | CMSIS 启动文件(第三方/自动生成) | 365 行,标准 `Reset_Handler` → `SystemInit` → `__libc_init_array` → `main`,中断向量表 |
| `README.md` | 一句话提示 | "使用 STM32CubeMX 重新生成工程后,需要取消 `stm32f1xx_it.c` 的更改。"——因为 `stm32f1xx_it.c` 里手工塞了 `Tim1Callback100Hz()` / `Tim4Callback20kHz()` / UART IDLE 处理,CubeMX 重新生成会冲掉 |
| `.cproject` / `.project` / `.mxproject` / `.gitignore` / `.idea/` | IDE 与 CubeMX 元数据(第三方/自动生成),只有 42 有 | — |
| `Drivers/` | STM32F1xx HAL + CMSIS(第三方/自动生成,4.3MB) | 回答固件逻辑问题时不必进入 |

---

### `UserApp/` —— 应用层

应用层是整个固件的"胶水":`Main()` 负责上电配置加载与对象装配,两个定时器回调是实际的执行主体,`protocols/` 下两个文件分别实现 CAN(与主控通信的正式通道)和 UART(调试通道)命令解析。

| 文件 | 作用 | 关键符号/要点 |
|---|---|---|
| `UserApp/main.cpp` | 裸机入口 `Main()`、定时器回调、按键事件 | 全局对象 `boardConfig`/`motor`/`tb67H450`/`mt6816`/`encoderCalibrator`/`button1(1,1000)`/`button2(2,3000)`/`statusLed`;`Tim1Callback100Hz()`、`Tim4Callback20kHz()`;`OnButton1Event`/`OnButton2Event`;默认参数 currentLimit=1000mA、velocityLimit=30 r/s、velocityAcc=100 r/s²、calibrationCurrent=2000mA、DCE(200,80,300,250) |
| `UserApp/common_inc.h` | C/C++ 边界头 | `extern "C"` 段声明 `void Main(); void OnUartCmd(uint8_t*,uint16_t); void OnCanCmd(uint8_t _cmd, uint8_t* _data, uint32_t _len);` C++ 段 include `Motor/motor.h`、`mt6816_stm32.h`、`tb67h450_stm32.h`、`encoder_calibrator_stm32.h`、`button_stm32.h`、`led_stm32.h`、`adc.h` |
| `UserApp/configurations.h` | 掉电保存的板级配置结构 | `enum configStatus_t { CONFIG_RESTORE=0, CONFIG_OK, CONFIG_COMMIT }`;`struct Config_t`(typedef 名 **`BoardConfig_t`**)字段:`configStatus, canNodeId, encoderHomeOffset, defaultMode, currentLimit, velocityLimit, velocityAcc, calibrationCurrent, dce_kp, dce_kv, dce_ki, dce_kd, motor_temperature(float), enableMotorOnBoot, enableStallProtect, enableTempWatch`;`extern BoardConfig_t boardConfig` |
| `UserApp/protocols/interface_can.cpp` | **与主控的 CAN 协议实现** | `OnCanCmd()` 大 switch;`CAN_TxHeaderTypeDef txHeader{.IDE=CAN_ID_STD,.RTR=CAN_RTR_DATA,.DLC=8}`;应答 ID = `(canNodeId << 7) | cmd` |
| `UserApp/protocols/interface_uart.cpp` | 串口调试命令 | `OnUartCmd()`;只支持 3 条:`'c'`=电流(A)、`'v'`=速度(r/s)、`'p'`=位置(r);用 `strtok(_data, "c")` + `atof` 解析,如 `c0.5`、`p1.5`;其他字符打印 "Only support [c] [v] [p] commands!" |

#### `UserApp/main.cpp`(裸机主循环与中断分工)

**上电流程(`Main()`,被 `Core/Src/main.c` 在所有 `MX_*_Init()` 之后调用):**

1. `GetSerialNumber()` 读 MCU UID(读了但**只赋给局部变量 `serialNum`,未被使用**)。
2. **读 3 位拨码开关定 CAN 节点号**:`ID0=PA8`(拨码 4)、`ID1=PA9`(拨码 3)、`ID2=PA10`(拨码 2),均内部上拉、低有效,取反后拼成 `nodeID = !PA8 | (!PA9<<1) | (!PA10<<2)`,范围 0~7。
3. `EEPROM eeprom; eeprom.get(0, boardConfig);` 从模拟 EEPROM(Flash 最后一页)读配置。若 `configStatus != CONFIG_OK`,写入**出厂默认值**:
   - `currentLimit = 1*1000`(1000 mA)
   - `velocityLimit = 30 * MOTOR_ONE_CIRCLE_SUBDIVIDE_STEPS`(30 r/s)
   - `velocityAcc = 100 * MOTOR_ONE_CIRCLE_SUBDIVIDE_STEPS`(100 r/s²)
   - `calibrationCurrent = 2000`(mA)
   - `dce_kp=200, dce_kv=80, dce_ki=300, dce_kd=250`(**35 固件此处为 195**)
   - `defaultMode = MODE_COMMAND_POSITION`,`enableMotorOnBoot=false`,`enableStallProtect=false`,`enableTempWatch=false`
   - 注意:初始化列表里 **`.canNodeId` 被注释掉了**(`//.canNodeId = defaultNodeID`),因此聚合初始化把它置 0;紧接着第 58 行 `boardConfig.canNodeId = defaultNodeID;` **每次上电都用拨码值覆盖**,所以 CAN 命令 `0x11`(Set Node-ID)写进 EEPROM 的节点号实际**永久失效**,注释 "depends on 3 bits switch now" 说明这是有意改动。
   - 同样 `boardConfig.enableTempWatch = false;` 在第 56 行被无条件强制关闭,EEPROM 里存的值无效(只能靠 CAN `0x7d` 运行时打开)。
4. 把 `boardConfig` 的值灌进 `motor.config.motionParams` / `ctrlParams`,并显式调用 `motor.motionPlanner.velocityTracker.SetVelocityAcc()` 和 `positionTracker.SetVelocityAcc()`(因为 `MotionPlanner::AttachConfig` 在 `Motor` 构造时就跑过了,此时才拿到真实加速度)。
   - **注意**:`currentTracker` 和 `trajectoryTracker` 的加速度没有同步刷新,仍是 `Motor` 构造函数里的 `ratedCurrentAcc=2000 mA/s` 和 `ratedVelocityAcc=1000 r/s²`。
5. 装配:`motor.AttachDriver(&tb67H450)` / `AttachEncoder(&mt6816)`,然后 `motor.controller->Init()`、`motor.driver->Init()`、`motor.encoder->Init()`。
6. 注册按键回调,`HAL_Delay(100)` 后**启动两个定时器中断**:`HAL_TIM_Base_Start_IT(&htim1)`(100Hz)、`HAL_TIM_Base_Start_IT(&htim4)`(20kHz)。
7. 若**上电时两键同按** → `encoderCalibrator.isTriggered = true`,进入编码器标定。
8. `for(;;)`:只做两件事 —— `encoderCalibrator.TickMainLoop()`(标定数据计算 + 写 Flash,非标定状态立即 return);检查 `boardConfig.configStatus`,`CONFIG_COMMIT` 则 `eeprom.put(0, boardConfig)`,`CONFIG_RESTORE` 则落盘后 `HAL_NVIC_SystemReset()`。

**中断分工(NVIC 优先级,数字越小越高):**

| 中断 | 优先级 | 职责 |
|---|---|---|
| `TIM4_IRQn` → `Tim4Callback20kHz()` | 0 | **闭环控制环**。标定中跑 `encoderCalibrator.Tick20kHz()`,否则跑 `motor.Tick20kHz()`(读编码器 + 闭环 + 输出)。二者**互斥**,不会同时跑 |
| `TIM3_IRQn` | 0 | 代码里**直接 `return`**,未使用(TIM3 CH1=PA6 配为输入捕获+复位从模式,是预留的 STEP/DIR 脉冲输入) |
| `USB_HP_CAN1_TX` / `USB_LP_CAN1_RX0` / `CAN1_RX1` / `CAN1_SCE` | 3 | `HAL_CAN_IRQHandler(&hcan)`,最终进 `HAL_CAN_RxFifo0MsgPendingCallback` → `OnCanCmd()` |
| `TIM1_UP_IRQn` → `Tim1Callback100Hz()` | 5 | 按键扫描 `button1/2.Tick(10)`、状态灯 `statusLed.Tick(10, motor.controller->state)`、1 秒一次 `AdcGetChipTemperature()`(仅 `enableTempWatch` 为真时) |
| `USART1_IRQn` | (CubeMX 默认) | IDLE 帧检测 + DMA 收包 → `OnRecvEnd()`(= `OnUartCmd`) |
| `DMA1_Channel1/4/5` | — | ADC1 循环采样、USART1 TX/RX |
| `EXTI9_5_IRQn` | — | 代码里**直接 `return`**,且 `gpio.c` 里 NVIC 使能已注释掉;原本是 `SIGNAL_COUNT_DIR_Pin`(PA7)的 DIR 跳变中断 |

两个回调都是先手工 `__HAL_TIM_CLEAR_IT(&htimX, TIM_IT_UPDATE)`,再干活;`stm32f1xx_it.c` 里调完回调直接 `return`,**绕过 `HAL_TIM_IRQHandler`** 省开销——这正是 README 警告 CubeMX 重新生成会破坏的地方。

**潜在问题**:`Tim4Callback20kHz`(优先级 0)会抢占 CAN 中断(优先级 3);反过来 CAN 回调里 `OnCanCmd` 的 `0x05` 分支有一句 `printf("SET MOTOR[0x05] POSITION[]\r\n")`——在中断上下文里走 `retarget.c` 的阻塞式 `HAL_UART_Transmit`,会把 CAN 中断拖长到毫秒级。`OnButton1Event` / `OnButton2Event`(100Hz 中断内)也有 `printf("KEY1/KEY2\r\n")`。

**按键行为**(`button1` 长按阈值 1000ms,`button2` 为 3000ms):
- KEY1 短按:在 `MODE_STOP` 与 `boardConfig.defaultMode` 之间切换(即"使能/停止")
- KEY1 长按:触发编码器标定(`isTriggered=true` 并立即手工调一次 `Tick20kHz()` + `TickMainLoop()`)
- KEY2 短按:`motor.controller->ClearStallFlag()` 清堵转
- KEY2 长按:把当前模式的设定值归零(电流/速度/位置 → 0)

---

### `Ctrl/` —— 平台无关的控制算法层

`Ctrl/` 是纯 C++、不含任何 HAL 调用的抽象层:所有与芯片相关的操作都声明成纯虚/空虚函数,由 `Port/` 下的派生类实现。目录分 4 块:`Driver/`(功率级)、`Motor/`(闭环 + 轨迹规划)、`Sensor/Encoder/`(磁编码器 + 标定)、`Signal/`(按键 + LED)。

#### `Ctrl/Driver/`

| 文件 | 作用 | 关键符号/要点 |
|---|---|---|
| `Ctrl/Driver/driver_base.h` | 功率级抽象基类 | `class DriverBase`;纯虚 `Init()`、`SetFocCurrentVector(uint32_t _directionInCount, int32_t _current_mA)`、`Sleep()`、`Brake()`、`SetTwoCoilsCurrent(uint16_t,uint16_t)`;`struct FastSinToDac_t { uint16_t sinMapPtr; int16_t sinMapData; uint16_t dacValue12Bits; }`,成员 `phaseA`/`phaseB`。注释明确:电流矢量方向用"把 360° 圆分成 N 份的计数"表示,电流范围 0~3300mA |
| `Ctrl/Driver/tb67h450_base.h` | TB67H450 平台无关实现的声明 | `class TB67H450Base : public DriverBase`;**空实现**虚函数(非纯虚)`InitGpio()`、`InitPwm()`、`DacOutputVoltage(uint16_t,uint16_t)`、`SetInputA(bool,bool)`、`SetInputB(bool,bool)` 留给 Port 层 |
| `Ctrl/Driver/tb67h450_base.cpp` | 正弦查表 → 两相电流 + H 桥方向 | 见下方小节 |
| `Ctrl/Driver/sin_map.h` | 正弦查表(自动生成的常量表) | `#define sin_pi_m2_dpix 1024`、`#define sin_pi_m2_dpiybit 12`;`const int16_t sin_pi_m2[1025]`,一个完整电周期 1024 点,幅值 0~**4096**(Q12 定点)。被 `extern "C"` 包住但内容是 C++(`#include <cstdint>`) |

#### `Ctrl/Driver/tb67h450_base.cpp`(驱动芯片与 PWM 输出)

核心是 `SetFocCurrentVector(uint32_t _directionInCount, int32_t _current_mA)`,20kHz 控制环的最后一步:

1. **相位查表索引**:`phaseB.sinMapPtr = _directionInCount & 0x3FF`(取低 10 位 → 一个电周期 = **1024 个细分计数**);`phaseA.sinMapPtr = (phaseB.sinMapPtr + 256) & 0x3FF`,即 A 相**超前 B 相 90°**(256/1024)。
   - 配合 `SOFT_DIVIDE_NUM = 256`,一个电周期对应 4 个物理整步 —— 符合两相步进电机 "4 整步 = 1 电周期"。
2. **幅值 → 12 位 DAC**:`dac_reg = abs(_current_mA) * 5083 >> 12`。系数 5083/4096 ≈ **1.2410**,正是 `4095 / 3300mA`,把 mA 线性映射到 12 位满量程(3300mA 满程)。随后 `& 0x0FFF` 截断。
3. **两相幅值**:`phaseX.dacValue12Bits = (dac_reg * abs(phaseX.sinMapData)) >> sin_pi_m2_dpiybit`(>>12 还原 Q12)。
4. `SetTwoCoilsCurrent(phaseA.dacValue12Bits, phaseB.dacValue12Bits)` → 直接转调 `DacOutputVoltage()`。注释引用 **TB67H450 Datasheet p.10**:因采样电阻 0.1Ω,0~3300mV 的 V-ref 等价 0~3300mA 的电流设定点。
5. **H 桥方向**:按 `sinMapData` 的符号设 IN+/IN−:`>0 → SetInputX(true,false)`(正向)、`<0 → (false,true)`(反向)、`==0 → (true,true)`(**刹车/短接**,不是高阻)。
6. `Sleep()`:DAC 清 0 + `SetInputX(false,false)` → H 桥高阻(电机自由转动)。
   `Brake()`:DAC 清 0 + `SetInputX(true,true)` → 两相短接,反电动势制动。

**PWM 实际输出(在 `Port/tb67h450_stm32.cpp`)**:`DacOutputVoltage()` 把 12 位值 **`>> 2` 降为 10 位** 写进 `TIM2` CH4(A 相)/ CH3(B 相)的 CCR。TIM2 配置为 `Prescaler=0, Period=1023`,即 **72MHz / 1024 ≈ 70.3kHz 的 10 位 PWM**,外接 RC 当作伪 DAC 给 TB67H450 的 VREF。因此**实际电流分辨率是 10 位(约 3.2mA/LSB),不是 12 位**。

#### `Ctrl/Motor/`

| 文件 | 作用 | 关键符号/要点 |
|---|---|---|
| `Ctrl/Motor/motor.h` | 电机对象 + 内嵌控制器声明 | `class Motor`;常量 `MOTOR_ONE_CIRCLE_HARD_STEPS = 200`(1.8° 步进)、`SOFT_DIVIDE_NUM = 256`、`MOTOR_ONE_CIRCLE_SUBDIVIDE_STEPS = 200*256 = **51200**`;`enum Mode_t { MODE_STOP, MODE_COMMAND_POSITION, MODE_COMMAND_VELOCITY, MODE_COMMAND_CURRENT, MODE_COMMAND_Trajectory, MODE_PWM_POSITION, MODE_PWM_VELOCITY, MODE_PWM_CURRENT, MODE_STEP_DIR }`;`enum State_t { STATE_STOP, STATE_FINISH, STATE_RUNNING, STATE_OVERLOAD, STATE_STALL, STATE_NO_CALIB }`;`class Controller` 内含 `PID_t`(速度环,默认 kp=5,ki=30,kd=0)与 `DCE_t`(位置环,默认 kp=200,kv=80,ki=300,kd=250);构造函数里的默认 `ratedCurrent=1000mA`、`caliCurrent=2000mA`、`ratedCurrentAcc=2000mA/s`、`ratedVelocity=30r/s`、`ratedVelocityAcc=1000r/s²` |
| `Ctrl/Motor/motor.cpp` | 闭环控制实现 | 见下方小节 |
| `Ctrl/Motor/motion_planner.h` | 5 个独立"跟踪器"的声明 | `class MotionPlanner`;`CONTROL_FREQUENCY = 20000`(Hz)、`CONTROL_PERIOD = 50`(µs);`struct Config_t { encoderHomeOffset, caliCurrent, ratedCurrent, ratedVelocity, ratedVelocityAcc, ratedCurrentAcc }`;内嵌类 `CurrentTracker`、`VelocityTracker`、`PositionTracker`、`PositionInterpolator`、`TrajectoryTracker`(后者 `updateTimeout = 200` ms) |
| `Ctrl/Motor/motion_planner.cpp` | 梯形加减速规划 | 见下方小节 |

#### `Ctrl/Motor/motor.cpp`(闭环控制实现、控制环频率)

**控制环频率:20kHz**(`MotionPlanner::CONTROL_FREQUENCY = 20000`,周期 50µs,由 `TIM4` 中断驱动)。入口 `Motor::Tick20kHz()` 只有两步:`encoder->UpdateAngle()` 然后 `CloseLoopControlTick()`。

`CloseLoopControlTick()` 的 7 个阶段:

1. **首次调用对齐**(`static bool isFirstCalled`):把 `rectifiedAngle` 相对 `encoderHomeOffset` 做 ±半圈归一化,一次性写入 `realLapPosition/realPosition` 及其 Last,然后 `return`(第一拍不输出)。
2. **位置累加(多圈)**:`deltaLapPosition = realLapPosition - realLapPositionLast`,若跨过 ±51200/2 则 ∓51200 环绕修正,累加到 `realPosition`(单位:细分步,51200/圈)。
3. **状态估计**:
   - 速度:一阶 IIR + 定点余数累加,`estVelocityIntegral += (Δpos * 20000 + (estVelocity<<5 - estVelocity)); estVelocity = estVelocityIntegral >> 5;` 等效时间常数 32 拍(1.6ms)的低通。单位:细分步/秒。
   - 超前角补偿:`estLeadPosition = CompensateAdvancedAngle(estVelocity)`;`estPosition = realPosition + estLeadPosition`。
   - `estError = softPosition - estPosition`(只记录,未用于控制)。
4. **控制律分派**(按 `modeRunning`):
   - `isStalled || softDisable || !encoder->IsCalibrated()` → 清积分、清输出、`driver->Sleep()`(高阻)
   - `softBrake` → 清积分、`driver->Brake()`
   - `MODE_COMMAND_CURRENT` / `MODE_PWM_CURRENT` → `CalcCurrentToOutput(softCurrent)`
   - `MODE_COMMAND_VELOCITY` / `MODE_PWM_VELOCITY` → `CalcPidToOutput(softVelocity)`
   - `MODE_COMMAND_POSITION` / `MODE_PWM_POSITION` / `MODE_COMMAND_Trajectory` / `MODE_STEP_DIR` → `CalcDceToOutput(softPosition, softVelocity)`
   - `MODE_STOP` → `driver->Sleep()`
5. **模式切换**:`modeRunning != requestMode` 时切换并置 `softNewCurve = true`;下一拍根据新模式调对应 tracker 的 `NewTask(当前估计值)`,并 `ClearIntegral()` + `ClearStallFlag()`,保证无冲击切换。
6. **限幅 + 规划**:`goalVelocity`/`goalCurrent` 先钳到 `ratedVelocity`/`ratedCurrent`,再交给对应 tracker 的 `CalcSoftGoal()` 得到平滑的 `softPosition/softVelocity/softCurrent`。
7. **状态机**:
   - **堵转检测**(需 `stallProtectSwitch`):电流模式下只要 `current != 0`,其他模式下 `current == ratedCurrent`(满额),且 `|estVelocity| < 51200/5`(即 **< 0.2 r/s**)时累计 `stalledTime += 50µs`,**累计到 1 秒**(`1000*1000` µs)置 `isStalled = true`。注释明确:**堵转标志只能手动清除**(KEY2 短按 / CAN `0x7e` 前的 `ClearStallFlag`),条件消失只清计时器不清标志。
   - **过载检测**:非电流模式下 `current == ratedCurrent` 持续 1 秒 → `overloadFlag = true`;条件消失**自动清零**。
   - `state` 优先级:`STATE_NO_CALIB > STATE_STOP > STATE_STALL > STATE_OVERLOAD >` 按模式判 `STATE_FINISH`/`STATE_RUNNING`。位置模式下需 `softPosition == goalPosition && softVelocity == 0` 才算 FINISH。

**三个控制律(全定点整数运算,无浮点)**:

- `CalcCurrentToOutput(int32_t current)`:开环电流模式。`focPosition = estPosition ± SOFT_DIVIDE_NUM`(**±256 计数 = 电角度 ±90°**,正电流超前、负电流滞后),然后 `driver->SetFocCurrentVector(focPosition, focCurrent)`。这是"永远保持最大力矩角"的方案。
- `CalcPidToOutput(int32_t _speed)`:**速度环 PID**,输出是电流(mA)。
  - `vError = _speed - estVelocity`,钳位 ±1048576(±1024*1024)
  - `outputKp = kp * vError`
  - 积分:`integralRound += ki * vError; integralRemainder = integralRound >> 10; outputKi += integralRemainder;`,`outputKi` 钳到 `±(ratedCurrent << 10)`
  - `outputKd = kd * (vError - vErrorLast)`
  - `output = (Kp+Ki+Kd) >> 10`,钳到 `±ratedCurrent`,再喂给 `CalcCurrentToOutput`
- `CalcDceToOutput(int32_t _location, int32_t _speed)`:**位置环 DCE**(Deviation Counter Error,带速度前馈的 PD+I),输出也是电流。
  - `pError = _location - estPosition`,**钳位 ±3200**(注释:限到 1/16 圈 = 51200/16)
  - `vError = (_speed - estVelocity) >> 7`,**钳位 ±4000**
  - `outputKp = kp * pError`
  - 积分项**同时吃位置误差和速度误差**:`integralRound += (ki * pError + kv * vError); integralRemainder = integralRound >> 7; outputKi += integralRemainder;`,钳到 `±(ratedCurrent << 10)`
  - `outputKd = kd * vError`(**微分项用的是速度误差,不是误差的差分**)
  - `output = (Kp+Ki+Kd) >> 10`,钳到 `±ratedCurrent`

**其他 API**:
- `SetPositionSetPoint(_pos)`:`goalPosition = _pos + encoderHomeOffset`
- `SetPositionSetPointWithTime(_pos, _time)`:解二次方程算出能在 `_time` 秒内走完 `deltaPos` 的梯形速度上限 `vMax`,写进 `ratedVelocity`;若 `deltaPos > ratedVelocityAcc*t²/4`(时间不够)则退回 `boardConfig.velocityLimit` 并返回 `false`。**唯一用到 `sqrtf` 的地方**
- `GetPosition(bool _isLap=false)`:返回**圈数**(float),`(realPosition - encoderHomeOffset) / 51200`;`_isLap=true` 返回单圈位置
- `GetVelocity()`:`estVelocity / 51200`(r/s);`GetFocCurrent()`:`focCurrent / 1000`(A)
- `ApplyPosAsHomeOffset()`:`encoderHomeOffset = realPosition % 51200`
- `CompensateAdvancedAngle(int32_t _vel)`:**static,纯分段线性查表**的相位超前补偿。分 4 段(|v| < 100000 / < 1300000 / < 2200000 / 更大),斜率 262、105、52(配 `>>20`),最大补偿 **±430** 细分步。**代码注释明确写着 "The code is for DPS series sensors, need to measured and renew for TLE5012/MT6816."——即这组标定值是别的传感器的,对 MT6816 未重新标定过**,是个已知的遗留问题。

#### `Ctrl/Motor/motion_planner.cpp`(梯形/S 曲线规划)

**结论:实现的是梯形(T 型)速度曲线,没有 S 曲线(jerk 限制)。** 五个独立 tracker,全部是**定点积分 + 余数保留**,统一手法:

```
integral += acc;  value += integral / CONTROL_FREQUENCY;  integral %= CONTROL_FREQUENCY;
```

即每 50µs 把加速度积一次,商加到状态量,余数留到下一拍 —— 零浮点、零累积误差。

| Tracker | 用于模式 | 规划逻辑 |
|---|---|---|
| `CurrentTracker` | `MODE_*_CURRENT` | 一阶斜坡限幅。`currentAcc` 来自 `ratedCurrentAcc`(2000 mA/s)。跨零时**先把电流拉到 0 再往反向加**(两段式),避免突变。输出 `goCurrent` |
| `VelocityTracker` | `MODE_*_VELOCITY` | 同构的速度斜坡,`velocityAcc` 来自 `ratedVelocityAcc`,跨零同样两段式。输出 `goVelocity` |
| `PositionTracker` | `MODE_*_POSITION` | **核心的梯形位置规划**。见下 |
| `PositionInterpolator` | `MODE_STEP_DIR` | 不做规划,只做**速度估计/插值**:对外部给的 `_goalPosition` 差分,用 `>>6`(64 拍 ≈ 3.2ms)的 IIR 估速度,`goPosition = recordPosition`(直接跟),`goVelocity = estVelocity` 供 DCE 的速度前馈用 |
| `TrajectoryTracker` | `MODE_COMMAND_Trajectory` | **动态加速度**轨迹跟踪:每收到新 (pos, vel) 目标就解 `a = (v₁+v₀)(v₁-v₀) / (2·Δp)`(即 v²=v₀²+2aΔp),之后按该 `a` 匀加速积分。若 **200ms**(`updateTimeout`)内没有新目标 → `overtimeFlag` 置位,按 `velocityDownAcc` 减速到 0(失联保护)。`Init(200)` 里把 `velocityDownAcc` 设为 `ratedVelocityAcc`,被注掉的那行原本是 `/10` |

**`PositionTracker::CalcSoftGoal(_goalPosition)` 的梯形逻辑**:

- `SetVelocityAcc(v)` 同时设 `velocityUpAcc = velocityDownAcc = v`(**加减速对称**),并预计算 `quickVelocityDownAcc = 0.5f / velocityDownAcc`(float,唯一的浮点量,用来快速算刹车距离)。
- `Init()` 里 `speedLockingBrake = ratedVelocityAcc / 1000`(注释说这是最佳值),低于此速度时直接归零锁定,避免末端抖振。
- `deltaPosition == 0`(已到位):速度在 `±speedLockingBrake` 内直接清零锁死,否则按 `velocityDownAcc` 刹停。
- `deltaPosition != 0`:
  - 同向运动时算**刹车距离** `need_down_location = trackVelocity² * quickVelocityDownAcc`(即 v²/(2a));
    - 剩余距离 > 刹车距离 → 继续加速(到 `ratedVelocity` 封顶,**匀速段**)
    - 否则 → 按 `velocityDownAcc` **减速段**
  - **反向运动**(目标在后、速度在前)→ 无条件减速到 0 再掉头
  - 超速(`|trackVelocity| > ratedVelocity`)→ 先减速
- 最后 `CalcPositionIntegral(trackVelocity)` 把速度积成 `trackPosition`,输出 `go_location` / `go_velocity`。

命名风格上 `PositionTracker` 用蛇形(`go_location`、`real_location`),其余 tracker 用驼峰(`goPosition`),是上游代码的历史痕迹;`TrajectoryTracker` 里还有拼写错误 `velovityNowRemainder`。

#### `Ctrl/Sensor/Encoder/`

| 文件 | 作用 | 关键符号/要点 |
|---|---|---|
| `Ctrl/Sensor/Encoder/encoder_base.h` | 编码器抽象基类 | `class EncoderBase`;`struct AngleData_t { uint16_t rawAngle; uint16_t rectifiedAngle; bool rectifyValid; }`;`const int32_t RESOLUTION = 1 << 14 = **16384**`(14 位);注释说明每个状态存一个 uint16 → **标定表共 32KB Flash**;纯虚 `Init()`、`UpdateAngle()`、`IsCalibrated()` |
| `Ctrl/Sensor/Encoder/mt6816_base.h` | MT6816 平台无关实现声明 | `class MT6816Base : public EncoderBase`;构造参数 `uint16_t* _quickCaliDataPtr`(标定表在 Flash 的首地址);`struct SpiRawData_t { rawData, rawAngle, noMagFlag, checksumFlag }`;纯虚 `SpiInit()`、`SpiTransmitAndRead16Bits(uint16_t)`(**35 固件此处是空实现 `{}` 而非 `= 0`**) |
| `Ctrl/Sensor/Encoder/mt6816_base.cpp` | SPI 读角 + 奇偶校验 + 查表校正 | `Init()` 遍历全部 16384 个表项,只要有一项是 `0xFFFF`(未擦写)就判 `rectifyValid = false`;`UpdateAngle()` 发两帧 `(0x80|0x03)<<8` 和 `(0x80|0x04)<<8` 读寄存器 0x03/0x04,拼成 16 位 `rawData`,做**奇校验**(16 位中 1 的个数为偶才有效),**最多重试 3 次**;`rawAngle = rawData >> 2`(高 14 位),`noMagFlag = rawData & 0x02`(**读了但从未被使用**);最后 `rectifiedAngle = quickCaliDataPtr[rawAngle]` 查表 |
| `Ctrl/Sensor/Encoder/encoder_calibrator_base.h` | 标定器声明 | `class EncoderCalibratorBase`;`MOTOR_ONE_CIRCLE_HARD_STEPS = 200`、`SAMPLE_COUNTS_PER_STEP = 16`、`AUTO_CALIB_SPEED = 2`、`FINE_TUNE_CALIB_SPEED = 1`;`enum Error_t { CALI_NO_ERROR, CALI_ERROR_AVERAGE_DIR, CALI_ERROR_AVERAGE_CONTINUTY, CALI_ERROR_PHASE_STEP, CALI_ERROR_ANALYSIS_QUANTITY }`;`enum State_t { CALI_DISABLE, CALI_FORWARD_PREPARE, CALI_FORWARD_MEASURE, CALI_BACKWARD_RETURN, CALI_BACKWARD_GAP_DISMISS, CALI_BACKWARD_MEASURE, CALI_CALCULATING }`;RAM 占用 `sampleDataAverageForward[201]` + `Backward[201]`(约 804 字节);纯虚 `BeginWriteFlash/EndWriteFlash/ClearFlash/WriteFlash16bitsAppend` |
| `Ctrl/Sensor/Encoder/encoder_calibrator_base.cpp` | 标定流程 | 见下方小节 |

#### `Ctrl/Sensor/Encoder/encoder_calibrator_base.cpp`(标定流程)

标定目的:建立一张 **16384 项的查找表**(`rawAngle` → `rectifiedAngle`),把 MT6816 的原始角度映射到"线性的 51200 细分步"坐标,同时消除磁编码器非线性和电机齿距误差。表存在 Flash `0x08017C00` 起的 32KB。

**触发方式**:上电两键同按、KEY1 长按、或 CAN 命令 `0x02`,都只是置 `isTriggered = true`。

**阶段一:采样(在 20kHz 中断 `Tick20kHz()` 里跑,状态机)**

| 状态 | 行为 |
|---|---|
| `CALI_DISABLE` | 见 `isTriggered` → 以 `caliCurrent`(默认 2000mA)通电,`goPosition = 51200`(从第二圈开始,避免负数),转 `CALI_FORWARD_PREPARE` |
| `CALI_FORWARD_PREPARE` | 以 `AUTO_CALIB_SPEED = 2` 计数/拍**正转整整一圈**(51200→102400)。目的:让电机先跑一圈消除启动位置的不确定性,并进入稳定的满力矩跟随 |
| `CALI_FORWARD_MEASURE` | 回到 `goPosition = 51200`,以 `FINE_TUNE_CALIB_SPEED = 1` 计数/拍**慢速正转一圈**。每当 `goPosition % 256 == 0`(即每个物理整步)就连采 **16 个** `rawAngle`,用 `CycleDataAverage()` 做**环形平均**(处理 0/16383 跨零),存入 `sampleDataAverageForward[0..200]` |
| `CALI_BACKWARD_RETURN` | 继续正转 `256*20 = 20` 个整步(越冲) |
| `CALI_BACKWARD_GAP_DISMISS` | 反转这 20 个整步 —— **专门用于消除齿隙/回程间隙(backlash)**,让反向测量从同一个点开始 |
| `CALI_BACKWARD_MEASURE` | 慢速**反转一圈**,同样每整步采 16 点存 `sampleDataAverageBackward[]` |
| `CALI_CALCULATING` | `SetFocCurrentVector(0, 0)` 断力矩,等主循环处理 |

正反双向测量再取平均,是为了**对消齿隙和摩擦滞后带来的系统误差**。

**阶段二:校验与写表(在主循环 `TickMainLoop()` 里跑,因为要长时间擦写 Flash)**

1. 非 `CALI_CALCULATING` 立即 return;否则 `driver->Sleep()`。
2. `CalibrationDataCheck()` 四类校验:
   - 正反向逐点 `CycleAverage()` 求平均,结果**原地写回 `sampleDataAverageForward[]`**
   - 首尾差为 0 → `CALI_ERROR_AVERAGE_DIR`;否则由符号确定 `goDirection`(编码器计数方向 vs 电机转向)
   - 逐点差分必须落在 `[calibSampleResolution/2, calibSampleResolution*3/2]` 区间(`calibSampleResolution = 16384/200 ≈ 81`),越界 → `CALI_ERROR_AVERAGE_CONTINUTY`(**丢步、磁铁偏心、负载过大的典型报错**)
   - 方向必须单调一致,否则 `CALI_ERROR_AVERAGE_DIR`
   - 整圈中编码器"回绕点"(符号翻转处)必须**恰好出现 1 次**,否则 `CALI_ERROR_PHASE_STEP`;该点记作 `(rcdX, rcdY)` 作为写表起点
3. `ClearFlash()` → `BeginWriteFlash()` → 按 `goDirection` 分两套三重循环,对每个整步区间做**线性插值**:`dataU16 = CycleMod(SOFT_DIVIDE_NUM * stepX + SOFT_DIVIDE_NUM * stepY / dataI32, 51200)`,逐个 `WriteFlash16bitsAppend()` → `EndWriteFlash()`。
4. `resultNum != RESOLUTION`(即写入条数 ≠ 16384)→ `CALI_ERROR_ANALYSIS_QUANTITY`。
5. 成功:`encoder->angleData.rectifyValid = true`;失败:`rectifyValid = false` 且 `ClearFlash()`(宁可留空也不留错表)。
6. 无论成败都 `motor.controller->isStalled = true`(强制停机),`state = CALI_DISABLE`、`isTriggered = false`;**成功时 `HAL_NVIC_SystemReset()` 重启**,让 `MT6816Base::Init()` 重新校验新表。

**辅助的环形算术(全部 static)**:`CycleMod(a,b) = (a+b)%b`;`CycleSubtract(a,b,cyc)`(差值跨半周期则 ∓cyc);`CycleAverage(a,b,cyc)`(跨零时平均值 ±cyc/2);`CycleDataAverage(data,len,cyc)`(以 `data[0]` 为基准做环形平均)。

**遗留调试代码**:`TestFlash()`(往标定区灌 16384 个 `0x6666`,被 `OnButton1Event` 里注释掉的一行调用)和 `FlashRun()`(返回 `stopFlash ? 0 : 1`,`stopFlash` 永远是 0,其唯一调用点在 `main.cpp` 里也被注释掉了)—— 都是死代码。

#### `Ctrl/Signal/`

| 文件 | 作用 | 关键符号/要点 |
|---|---|---|
| `Ctrl/Signal/button_base.h` | 按键抽象 | `class ButtonBase`;`enum Event { UP, DOWN, LONG_PRESS, CLICK }`;`longPressTime` 默认 2000ms(实际 `main.cpp` 传 1000 / 3000);纯虚 `ReadButtonPinIO(uint8_t)` |
| `Ctrl/Signal/button_base.cpp` | 边沿检测 + 长短按判定 | `Tick(uint32_t _timeElapseMillis)`;**在 UP 边沿**同时发 `UP` 再发 `LONG_PRESS` 或 `CLICK`;无软件消抖(靠 100Hz 采样周期天然滤抖);`SetOnEventListener()` 注册时先读一次引脚初始化 `lastPinIO`,避免上电误触发 |
| `Ctrl/Signal/led_base.h` | 双 LED 状态指示抽象 | `class LedBase`;`Tick(uint32_t, Motor::State_t)`、`Status(uint8_t id, bool on)`;纯虚 `SetLedState(uint8_t,bool)` |
| `Ctrl/Signal/led_base.cpp` | 状态 → 灯码映射 | **LED0 = 使能/心跳灯**:`STATE_RUNNING` 时跑 100/100/100/700ms 的双闪心跳;`STATE_FINISH` 常亮;其余熄灭。**LED1 = 错误闪码**:`targetBlinkNum` = `STATE_NO_CALIB` → **1 闪**、`STATE_STALL` → **2 闪**、`STATE_OVERLOAD` → **3 闪**、正常 → 0;闪码节奏 100ms 亮/100ms 灭,组间隔 1000ms。**排查上板故障时直接看这个灯码** |

---

### `Port/` —— STM32 平台移植层

`Port/` 把 `Ctrl/` 的抽象接口落到 STM32 HAL 上,是"硬件相关的所有东西"的集中地。每个类都是对应 base 类的薄派生(典型只有 10~50 行)。`Port/Platform/` 下另有三块与算法无关的基础设施:Flash 分区管理(`Memory/`)、UID 读取(`Utils/`)、printf 重定向(`retarget.*`)。

| 文件 | 作用 | 关键符号/要点 |
|---|---|---|
| `Port/tb67h450_stm32.h` / `.cpp` | TB67H450 的 STM32 实现 | `class TB67H450 : public TB67H450Base`;`InitGpio()` 配 **PA2=BM, PA3=BP, PA4=AM, PA5=AP** 为推挽输出;`InitPwm()` → `MX_TIM2_Init()`;`DacOutputVoltage()` → `__HAL_TIM_SET_COMPARE(&htim2, TIM_CHANNEL_4, A>>2)` / `TIM_CHANNEL_3, B>>2`(**12 位截成 10 位**);`SetInputA/B()` 直写 `GPIOA->BSRR`/`BRR`(绕过 HAL,20kHz 下省时间)。注意 `SetInputA` 里**硬编码** `GPIO_PIN_5`/`GPIO_PIN_4`,没用 `HW_ELEC_AP_Pin` 宏 |
| `Port/mt6816_stm32.h` / `.cpp` | MT6816 的 STM32 实现 | `class MT6816 : public MT6816Base`;构造函数硬编码标定表地址 **`(uint16_t*)(0x08017C00)`**,头文件注释解释:128K Flash 的最后 33K(32K 标定 + 1K 用户)留给存储;`SpiInit()` → `MX_SPI1_Init()`;`SpiTransmitAndRead16Bits()` 手动拉低 `GPIOA->BRR = GPIO_PIN_15` 片选,`HAL_SPI_TransmitReceive(&hspi1, ..., 1, HAL_MAX_DELAY)`,再拉高。**这是阻塞调用,在 20kHz 中断里每拍调 2~6 次** |
| `Port/led_stm32.h` / `.cpp` | LED 实现 | `class Led : public LedBase`;`SetLedState(0)` → `LED1_Pin`(**PC13**)、`(1)` → `LED2_Pin`(**PC14**);**低电平点亮**(`_state ? GPIO_PIN_RESET : GPIO_PIN_SET`) |
| `Port/button_stm32.h` / `.cpp` | 按键实现 | `class Button : public ButtonBase`;`ReadButtonPinIO(1)` → **PB12**(BUTTON1)、`(2)` → **PB2**(BUTTON2),内部上拉;`IsPressed()` 返回 `!ReadButtonPinIO(id)`(**低电平为按下**) |
| `Port/encoder_calibrator_stm32.h` / `.cpp` | 标定数据落 Flash | `class EncoderCalibrator : public EncoderCalibratorBase`;四个方法全部转调 `Stockpile_Flash_Data_{Empty,Begin,End,Write_Data16}(&stockpile_quick_cali)` |
| `Port/Platform/Memory/stockpile_config.h` | **Flash 分区表(最重要的地址定义)** | `STOCKPILE_APP_FIRMWARE_ADDR = 0x08000000`,SIZE `0x0000BC00`(47K);`STOCKPILE_APP_CALI_ADDR = **0x08017C00**`,SIZE `0x00008000`(**32K**,注释:可容纳 16K×2 字节,即最大支持 14 位编码器);`STOCKPILE_APP_DATA_ADDR = 0x0801FC00`,SIZE `0x400`(1K);另有 DAPLink BL 分区和 RAM 分区 `STOCKPILE_RAM_APP_START=0x20000000/0x4F00`、`STOCKPILE_RAM_SHARED_START=0x20004F00/0x100`。文件头保留了上游 **XDrive_Step / unlir(知不知啊)GPLv3** 版权声明和 STM32F1 容量对照表 |
| `Port/Platform/Memory/stockpile_f103cb.c` / `.h` | Flash 分区读写 | `Stockpile_Page_Size = 0x400U`,用 `#error` 与 HAL 的 `FLASH_PAGE_SIZE` 比对;`struct Stockpile_FLASH_Typedef { begin_add, area_size, page_num, asce_write_add }`;三个全局实例 `stockpile_app_firmware` / **`stockpile_quick_cali`** / `stockpile_data`;API `Stockpile_Flash_Data_Empty`(整区页擦除)、`_Begin`(解锁 + 复位写指针)、`_End`(加锁)、`_Set_Write_Add`、`_Write_Data16/32/64`(顺序追加) |
| `Port/Platform/Memory/eeprom_interface.h` | Arduino 风格 EEPROM 类 | `class EEPROM`,来自 **FlashStorage_STM32 v1.1.0**;模板 `get<T>(int offset, T&)` / `put<T>(int idx, const T&)` 逐字节读写缓冲;`_commitASAP` 默认 true → 每次 `put` 立刻 `eeprom_buffer_flush()` 真写 Flash(**注释提醒会损耗寿命**);`length()` 返回 `E2END+1`。F103 无硬件 EEPROM,故走 `emulated_eeprom.h` 分支 |
| `Port/Platform/Memory/emulated_eeprom.h` / `.cpp` | Flash 模拟 EEPROM(第三方,ST/Arduino-STM32 移植) | `E2END = FLASH_PAGE_SIZE - 1`(**1024 字节,单页**);`eeprom_buffer_fill/flush`、`eeprom_buffered_read_byte/write_byte`;实际落在 **Flash 最后一页 = 0x0801FC00**,与 `STOCKPILE_APP_DATA_ADDR` 一致。`boardConfig` 从 offset 0 开始存(`sizeof(BoardConfig_t)` 约 56 字节) |
| `Port/Platform/Utils/st_hardware.h` / `.c` | 读芯片 UID | `uint64_t GetSerialNumber()`:读 `UID_BASE + 0/4/8` 三个 32 位,`uuid_mixed_part = uuid0 + uuid2`,返回 `(uuid_mixed_part << 16) | (uuid1 >> 16)`。注释说这是为了与 ST 内置 USB bootloader 的序列号算法一致。**`Main()` 里调了但结果未使用** |
| `Port/Platform/retarget.h` / `.c` | newlib printf 重定向到串口 | `RetargetInit(UART_HandleTypeDef*)`(在 `usart.c` 的 `MX_USART1_UART_Init` 里被调,传 `&huart1`);实现 `_write`(走阻塞 `HAL_UART_Transmit`)、`_read`、`_isatty`、`_close`、`_lseek`、`_fstat`。**所有 `printf` 最终都是阻塞发送,在中断里调用会显著拖长中断** |

---

### `Core/` —— CubeMX 生成的外设配置(含手工改动)

`Core/Inc` 与 `Core/Src` 由 CubeMX 生成,但在 USER CODE 区塞了关键的手工代码。下表只详述有手工内容或承载重要配置的文件。

| 文件 | 作用 | 关键符号/要点 |
|---|---|---|
| `Core/Src/main.c` | HAL 入口 `main()` 与时钟树 | `HAL_Init()` → `SystemClock_Config()` → `MX_GPIO_Init, MX_DMA_Init, MX_ADC1_Init, MX_USART1_UART_Init, MX_CAN_Init, MX_SPI1_Init, MX_TIM2_Init, MX_TIM3_Init, MX_TIM4_Init, MX_TIM1_Init` → **`Main()`**(C++ 应用入口,永不返回)→ 空 `while(1)`。时钟:`HSE_ON`(**12MHz**,见 `stm32f1xx_hal_conf.h`)、`PLLSOURCE_HSE`、`PLLMUL = RCC_PLL_MUL6` → **SYSCLK = 72MHz**;`AHB=DIV1`(72M)、`APB1=DIV2`(**36M**)、`APB2=DIV1`(72M)、`FLASH_LATENCY_2`;ADC 时钟 `RCC_ADCPCLK2_DIV6`(12MHz)。`Error_Handler()` = `__disable_irq()` + 死循环 |
| `Core/Src/stm32f1xx_it.c` | **中断向量实现(重手工改动,README 专门警告)** | `extern "C"` 声明 `Tim1Callback100Hz/Tim3CaptureCallback/Tim4Callback20kHz/GpioPin7InterruptCallback`;`TIM1_UP_IRQHandler` 调 `Tim1Callback100Hz(); return;`(**不进 `HAL_TIM_IRQHandler`**);`TIM4_IRQHandler` 调 `Tim4Callback20kHz(); return;`;`TIM3_IRQHandler` 和 `EXTI9_5_IRQHandler` 都是直接 `return`(**功能禁用**);`USART1_IRQHandler` 手工实现 **IDLE 空闲帧收包**:检测 `UART_FLAG_IDLE` → `HAL_UART_DMAStop` → 用 `__HAL_DMA_GET_COUNTER` 算出 `rxLen = BUFFER_SIZE - temp` → `OnRecvEnd(rx_buffer, rxLen)` → `memset` 清零 → 重启 `HAL_UART_Receive_DMA`;`HardFault/MemManage/BusFault/UsageFault/NMI_Handler` 全是死循环(**无故障信息输出**) |
| `Core/Src/tim.c` | 四个定时器配置 | `htim1`:PSC=**71**、ARR=**9999** → 72M/72/10000 = **100Hz**(基本定时,NVIC prio **5**)。`htim2`:PSC=**0**、ARR=**1023**、PWM1 模式、CH3+CH4 → **70.3kHz 10 位 PWM**,`MX_TIM2_Init` 末尾直接 `HAL_TIM_PWM_Start(CH3/CH4)`;MspPostInit 配 **PB10=TIM2_CH3(B 相 PWM)、PB11=TIM2_CH4(A 相 PWM)** 并调 `__HAL_AFIO_REMAP_TIM2_PARTIAL_2()`。`htim3`:PSC=71、ARR=65535、**输入捕获 CH1 = PA6**、`TIM_SLAVEMODE_RESET` + `TIM_TS_TI1FP1`(预留的 STEP 脉冲测周,NVIC prio 0,但 ISR 被 return 掉)。`htim4`:PSC=**71**、ARR=**49** → 72M/72/50 = **20kHz**(**闭环控制环时基**,NVIC prio **0**) |
| `Core/Src/can.c` | CAN 外设 + 收发回调 | `hcan.Init.Prescaler = 4`、`SJW_1TQ`、`BS1 = 5TQ`、`BS2 = 3TQ` → 36MHz/(4×(1+5+3)) = **1 Mbps**;`Mode = CAN_MODE_NORMAL`、`AutoBusOff = DISABLE`、`AutoWakeUp = ENABLE`、**`AutoRetransmission = DISABLE`**(发失败不重传);过滤器 FilterBank 0 全 0 掩码 = **接收所有帧**,FIFO0;`HAL_CAN_Start` + `HAL_CAN_ActivateNotification(几乎全部中断)`;引脚 **PB8=CAN_RX、PB9=CAN_TX** + `__HAL_AFIO_REMAP_CAN1_2()`;NVIC prio **3**。`CAN_Send(pHeader, data)` 包装 `HAL_CAN_AddTxMessage`,**失败直接 `Error_Handler()` 死机**。`HAL_CAN_RxFifo0MsgPendingCallback`:`id = StdId >> 7`、`cmd = StdId & 0x7F`,**`id == 0`(广播)或 `id == canNodeId` 时**调 `OnCanCmd(cmd, RxData, RxHeader.DLC)` |
| `Core/Src/spi.c` | MT6816 的 SPI1 | `SPI_MODE_MASTER`、`DATASIZE_**16BIT**`、`CLKPolarity = **HIGH**` + `CLKPhase = **2EDGE**`(**SPI Mode 3**)、`NSS_SOFT`、`BAUDRATEPRESCALER_8` → 72M/8 = **9 MHz**、`FIRSTBIT_MSB`;引脚 **PB3=SCK、PB4=MISO、PB5=MOSI**(片选 PA15 在 `gpio.c` 里单独配) |
| `Core/Src/adc.c` | 电压/温度采样 + NTC 换算 | `ScanConvMode = ENABLE`、`ContinuousConvMode = ENABLE`、`NbrOfConversion = 2`、`SamplingTime = 239.5 CYCLES`;通道 **ADC_CHANNEL_0 = PA0 = `POWER_U_Pin`(母线电压)**、**ADC_CHANNEL_1 = PA1 = `DRV_TEMP_Pin`(NTC)**;DMA1_Channel1 **循环**搬到 `uint16_t whole_adc_data[2][12]`(**只用了前 2 个元素,数组开得过大**);`HAL_ADCEx_Calibration_Start` 后 `HAL_ADC_Start_DMA(..., 2)`。`float AdcGetChipTemperature()` 用 **Beta 方程**换算 NTC:`BALANCE_RESISTOR = 3300.0`、`MAX_ADC = 4095.0`、`BETA = 3455.0`、`ROOM_TEMP = 298.15K`、`RESISTOR_ROOM_TEMP = 10000.0`;`rThermistor = 3300*(4095/adc - 1)`,`tKelvin = (BETA*298.15)/(BETA + 298.15*ln(R/10000))`,返回 `tKelvin - 273.15`。**函数名叫 "ChipTemperature" 但读的是外部 NTC(驱动级温度),不是 MCU 内部温度传感器 —— 命名误导**;母线电压 `whole_adc_data[0][0]` **采了但从未被使用** |
| `Core/Src/usart.c` | 调试串口 | `huart1.Init.BaudRate = **115200**`;`__HAL_UART_ENABLE_IT(&huart1, UART_IT_IDLE)`;`RetargetInit(&huart1)`(接 printf);**`Uart_SetRxCpltCallBack(OnUartCmd)`** —— 把 `UserApp/protocols/interface_uart.cpp` 的解析函数挂到 `OnRecvEnd` 函数指针;`HAL_UART_Receive_DMA(&huart1, rx_buffer, 128)` 开 DMA 收;DMA1_Channel5=RX、Channel4=TX,均 `DMA_NORMAL` |
| `Core/Inc/usart.h` | 串口缓冲定义 | `#define BUFFER_SIZE 128`;`extern volatile uint8_t rxLen`(**注意是 uint8_t,而 `BUFFER_SIZE` 是 128,刚好不溢出**);`extern uint8_t rx_buffer[128]`;`extern void (*OnRecvEnd)(uint8_t*, uint16_t)`;`void Uart_SetRxCpltCallBack(void(*)(uint8_t*,uint16_t))` |
| `Core/Src/gpio.c` | 全部 GPIO 初始化 | LED1/LED2(PC13/PC14)推挽输出初始 RESET;四个 H 桥相位脚(PA2~PA5)推挽输出;**`SIGNAL_COUNT_DIR_Pin`(PA7)配为 `GPIO_MODE_IT_RISING_FALLING`,但 `HAL_NVIC_EnableIRQ(EXTI9_5_IRQn)` 被注释掉**;`SIGNAL_COUNT_EN_Pin`(PB0)输入;`SIGNAL_ALERT_Pin`(PB1)推挽输出;BUTTON1/2(PB12/PB2)输入**上拉**;`SPI1_CS_Pin`(PA15)推挽输出初始 SET;**ID0/ID1/ID2(PA8/PA9/PA10)输入上拉**(手工添加的拨码开关) |
| `Core/Inc/main.h` | **全部引脚宏(查引脚看这里)** | `ID0=PA8, ID1=PA9, ID2=PA10`;`LED1=PC13, LED2=PC14`;`POWER_U=PA0, DRV_TEMP=PA1`;`HW_ELEC_BM=PA2, HW_ELEC_BP=PA3, HW_ELEC_AM=PA4, HW_ELEC_AP=PA5`;`SIGNAL_COUNT_DIR=PA7`;`SIGNAL_COUNT_EN=PB0, SIGNAL_ALERT=PB1`;`BUTTON2=PB2`;`HW_ELEC_BPWM=PB10, HW_ELEC_APWM=PB11`;`BUTTON1=PB12`;`SPI1_CS=PA15` |
| `Core/Inc/stm32f1xx_hal_conf.h` | HAL 模块裁剪与晶振值 | **`HSE_VALUE = 12000000U`**(算时钟必看);各 `HAL_xxx_MODULE_ENABLED` 开关 |
| `Core/Src/dma.c`、`stm32f1xx_hal_msp.c`、`syscalls.c`、`system_stm32f1xx.c`;`Core/Inc/{adc,can,dma,gpio,spi,stm32f1xx_it,tim}.h` | CubeMX 生成的样板(自动生成),无手工逻辑 | `dma.c` 只开 `__HAL_RCC_DMA1_CLK_ENABLE()` 和 DMA NVIC;`adc.h` 额外导出 `float AdcGetChipTemperature()` 与 `extern uint16_t whole_adc_data[2][12]`;`can.h` 额外导出 `CAN_Send()` 与 `extern uint8_t RxData[8]`(**`interface_can.cpp` 直接读这个全局数组**) |

---

### `UserApp/protocols/interface_can.cpp`(与主控的 CAN 协议)

这是**关节板与主控之间唯一的正式通信协议**,主控侧的对应实现是 `source/1.Dummy V2任同学整理/2.Firmware/dummy-ref-core-fw/Robot/actuators/ctrl_step/ctrl_step.cpp`(类 `CtrlStepMotor`),两边的命令码已逐条交叉核对一致。

**物理层与帧格式**

| 项 | 值 |
|---|---|
| 波特率 | **1 Mbps**(APB1 36MHz / Prescaler 4 / (1+5+3)TQ) |
| 帧类型 | **标准帧**(11 位 ID),`CAN_RTR_DATA`,`DLC = 8`(固定 8 字节) |
| ID 编码 | **`StdId = (nodeID << 7) | cmd`** —— 高 4 位节点号,低 7 位命令码 |
| 节点号来源 | 板上 **3 位拨码开关**(PA8/PA9/PA10,低有效),范围 **0~7**,每次上电覆盖 EEPROM 值 |
| 过滤 | 硬件过滤器全通;软件在 `HAL_CAN_RxFifo0MsgPendingCallback` 里判 `id == 0 || id == canNodeId`,**`nodeID = 0` 为广播地址** |
| 应答 ID | `(canNodeId << 7) | cmd`(与请求同码,主控靠 ID 的节点号区分来源) |
| 数据字节序 | **小端,直接内存重解释**(`*(float*)RxData`、`*(uint32_t*)RxData`),无字节序转换 |
| 存盘标志 | 带 Memory 的命令(`0x1x`)用 **`_data[4] != 0`** 表示"同时写入 EEPROM"(置 `configStatus = CONFIG_COMMIT`,主循环落盘) |
| 回读标志 | `0x05`/`0x06` 用 **`_data[4] != 0`** 表示"需要位置 + 完成状态 ACK" |

**0x00~0x0F:不落 EEPROM 的实时命令**

| 码 | 名称 | 请求数据 | 行为 / 应答 |
|---|---|---|---|
| `0x01` | Enable Motor | `[0:4] uint32` 1=使能 | `requestMode = (val==1) ? MODE_COMMAND_VELOCITY : MODE_STOP`。**注意:使能后进的是速度模式,不是 `boardConfig.defaultMode`** |
| `0x02` | Do Calibration | — | `encoderCalibrator.isTriggered = true`,启动编码器标定(约数十秒,结束后自动重启) |
| `0x03` | Set Current SetPoint | `[0:4] float` 安培 | 自动切 `MODE_COMMAND_CURRENT`;`SetCurrentSetPoint(val * 1000)`(转 mA) |
| `0x04` | Set Velocity SetPoint | `[0:4] float` r/s | 自动切 `MODE_COMMAND_VELOCITY`(切换时先把 `ratedVelocity` 恢复成 `boardConfig.velocityLimit`);`SetVelocitySetPoint(val * 51200)` |
| `0x05` | Set Position SetPoint | `[0:4] float` 圈;`[4] uint8` 需要 ACK | 自动切 `MODE_COMMAND_POSITION`;`SetPositionSetPoint(val * 51200)`。`_data[4]` 非 0 → 回 `0x23` 帧。**此分支含一句 `printf("SET MOTOR[0x05] POSITION[]\r\n")`,在 CAN 中断里阻塞发串口,是已知的性能隐患** |
| `0x06` | Set Position with Time | `[0:4] float` 圈;`[4:8] float` 秒 | `SetPositionSetPointWithTime(pos*51200, time)`,内部反解梯形曲线的速度上限。**`[4]` 同时被当作 ACK 标志用,与 time 的第 1 个字节重叠 —— 设计冲突**(见下方风险) |
| `0x07` | Set Position with Velocity-Limit | `[0:4] float` 圈;`[4:8] float` r/s | 先把 `ratedVelocity` 设成 `vel*51200`,再 `SetPositionSetPoint`。**总是**回一帧 `0x23`(位置 + 完成标志) |

**0x10~0x1F:参数配置(`_data[4]` 决定是否落 EEPROM)**

| 码 | 名称 | 请求数据 | 写入字段 |
|---|---|---|---|
| `0x11` | Set Node-ID | `[0:4] uint32` | `boardConfig.canNodeId`。**上电时会被拨码开关覆盖,实际无效** |
| `0x12` | Set Current-Limit | `[0:4] float` 安培 | `ratedCurrent` + `boardConfig.currentLimit`(×1000 转 mA) |
| `0x13` | Set Velocity-Limit | `[0:4] float` r/s | `ratedVelocity` + `boardConfig.velocityLimit`(×51200) |
| `0x14` | Set Acceleration | `[0:4] float` r/s² | `ratedVelocityAcc` + `velocityTracker/positionTracker.SetVelocityAcc()` + `boardConfig.velocityAcc` |
| `0x15` | Apply Home-Position | — | `ApplyPosAsHomeOffset()`,`boardConfig.encoderHomeOffset = encoderHomeOffset % 51200`;**无条件** `CONFIG_COMMIT` |
| `0x16` | Set Auto-Enable on Boot | `[0:4] uint32` 1=开 | `boardConfig.enableMotorOnBoot` |
| `0x17` | Set DCE Kp | `[0:4] int32` | `ctrlParams.dce.kp` + `boardConfig.dce_kp` |
| `0x18` | Set DCE Kv | `[0:4] int32` | `dce.kv` + `boardConfig.dce_kv` |
| `0x19` | Set DCE Ki | `[0:4] int32` | `dce.ki` + `boardConfig.dce_ki` |
| `0x1A` | Set DCE Kd | `[0:4] int32` | `dce.kd` + `boardConfig.dce_kd` |
| `0x1B` | Set Enable Stall-Protect | `[0:4] uint32` 1=开 | `ctrlParams.stallProtectSwitch` + `boardConfig.enableStallProtect` |

**0x20~0x2F:查询命令(请求可空,设备主动回同码帧)**

| 码 | 名称 | 应答帧格式(ID = `nodeId<<7 \| cmd`,DLC=8) |
|---|---|---|
| `0x21` | Get Current | `[0:4] float` 安培(`GetFocCurrent()`);`[4] uint8` = `state == STATE_FINISH` |
| `0x22` | Get Velocity | `[0:4] float` r/s(`GetVelocity()`);`[4] uint8` = FINISH 标志 |
| `0x23` | Get Position | `[0:4] float` 圈(`GetPosition()`);`[4] uint8` = FINISH 标志。**也是 `0x05`/`0x06`/`0x07` 的 ACK 帧格式** |
| `0x24` | Get Offset | `[0:4] **int32**` = `encoderHomeOffset`(细分步,不是 float!);`[4]` 未填 |
| `0x25` | Get Temperature | `[0:4] float` ℃(`boardConfig.motor_temperature`);`[4:8]` 显式清 0。**需先用 `0x7d` 打开温度采集,否则恒为 0** |

**0x70~0x7F:系统命令**

| 码 | 名称 | 行为 |
|---|---|---|
| `0x7d` | Enable Temperature Watch | `boardConfig.enableTempWatch = true`(仅运行时生效,`Main()` 启动时强制置 false) |
| `0x7e` | Erase Configs | `configStatus = CONFIG_RESTORE` → 主循环落盘后 `HAL_NVIC_SystemReset()`,重启后因 `configStatus != CONFIG_OK` 恢复出厂默认 |
| `0x7f` | Reboot | 立即 `HAL_NVIC_SystemReset()` |

**协议层风险点(回答"为什么丢指令/抖动"类问题时用得上)**

1. **`0x06` 的 `[4]` 字节语义冲突**:`[4:8]` 是 `time` 的 4 字节 float,而 `if (_data[4])` 又把它的最低字节当 ACK 开关 —— 对大多数非 0 的 time 值 ACK 会被意外触发。
2. **应答复用请求缓冲**:所有应答都把结果写回**传进来的 `_data`(即全局 `RxData[8]`)**再发送,下一帧到来会覆盖;同时 `_data` 的 `[5..7]` 字节保留的是请求里的脏数据(只有 `0x25` 显式清 0)。
3. **`0x03/0x04/0x05` 读的是全局 `RxData` 而不是形参 `_data`** —— 当前两者是同一块内存,但一旦改成多缓冲就会出 bug。
4. **`AutoRetransmission = DISABLE` + `CAN_Send` 失败即 `Error_Handler()` 死循环**:总线繁忙或无 ACK(例如主控没上电/终端电阻缺失)时,一次发送失败就会让关节板**永久卡死在 `__disable_irq()` 的空循环里**,表现为"电机突然失控/掉线",必须断电重启。
5. 命令码 `0x00`、`0x08~0x10`、`0x1C~0x20`、`0x26~0x7C` 均落到 `default: break`,静默忽略。

---

### 42 与 35 固件的差异

`diff -rq` 实测:两棵源码树里**只有 5 个文件内容不同**(另有若干 IDE 元数据只在 42 侧存在)。`Ctrl/Motor/`、`Ctrl/Driver/`、`Core/Src/*`、`Port/*`、`STM32F103CBTx_FLASH.ld`、`CMakeLists.txt`、`stlink.cfg`、`startup/` **全部逐字节相同**。

| 文件 | 42 | 35 | 性质 |
|---|---|---|---|
| `UserApp/main.cpp` | `.dce_kp = 200` | `.dce_kp = **195**` | **唯一的功能性差异**:35 电机的位置环比例增益略低(约 -2.5%)。其余 `dce_kv=80 / ki=300 / kd=250`、电流限制 1000mA、标定电流 2000mA、速度限 30 r/s、加速度 100 r/s² **完全相同** |
| `UserApp/main.cpp` | 文件末尾**无换行符** | 末尾有换行符 | 纯格式 |
| `UserApp/common_inc.h` | `#include <stdint.h>` | `#include "stdint-gcc.h"` | 编译期兼容性改动(见下) |
| `UserApp/configurations.h` | `#include <stdint.h>` | `#include "stdint-gcc.h"` | 同上 |
| `Port/Platform/Utils/st_hardware.h` | `#include <stdint.h>` | `#include <stdint-gcc.h>` | 同上 |
| `Ctrl/Sensor/Encoder/mt6816_base.h` | `virtual void SpiInit() = 0;`<br>`virtual uint16_t SpiTransmitAndRead16Bits(uint16_t) = 0;` | 两者都是**空实现 `{}`** | 42 改成了**纯虚函数**(更严格,漏实现会编译报错);35 的 `uint16_t ... {}` 是**无返回值的非 void 函数,是 UB,现代 GCC 会报 `-Wreturn-type` 警告**。42 的写法更正确 |
| 只在 42 侧存在 | `.cproject`、`.project`、`.mxproject`、`.gitignore`、`.idea/` | — | IDE/CubeMX 元数据 |

**关于 `stdint-gcc.h` → `stdint.h`**:文件时间戳显示 42 侧这 4 个文件是 **2026-09-06 本地修改**的(35 侧仍是原始的 2023-12-26)。`stdint-gcc.h` 是 ARM-GCC 自带的私有头,在新版 arm-none-eabi 工具链里引入方式变了,改成标准 `<stdint.h>` 才能编过。**结论:42 固件被本地修补过以便在当前工具链构建(`<V2>/2.Firmware/build/motor42-baseline/` 就是它的产物);35 固件保持上游原样,用新工具链很可能编不过。**

**意外发现(与直觉相反)**:
- **42 和 35 的减速比、编码器标定值、引脚映射、CAN ID 分配、电流/电压参数、细分数、控制环频率全部相同** —— 两份固件实质上是同一份代码,只差一个 `dce_kp`。减速比并不在电机固件里,而是在**主控**侧:`dummy-ref-core-fw/Robot/actuators/ctrl_step/ctrl_step.cpp` 的 `CtrlStepMotor` 构造参数 `reduction`。所以问"42 和 35 的减速比"要去主控固件找,本固件里没有。
- 两份 `README.md` 内容也**完全相同**(都是"重新生成后要取消 `stm32f1xx_it.c` 的更改")。
- `Ctrl-Step-fw.xml` 两份都写 `STM32F103CBTx`,未区分型号。

---

### `<V2>/2.Firmware/build/motor42-baseline/` 目录

42 固件的一次**已完成的本地基线构建**产物(CMake + Make,非 git 跟踪内容)。

| 文件 | 作用 | 关键要点 |
|---|---|---|
| `<V2>/2.Firmware/build/motor42-baseline/CMakeCache.txt` | CMake 配置缓存 | **`CMAKE_BUILD_TYPE:STRING=Debug`**(即 `-Og -g`,**不是 Release**);`CMAKE_HOME_DIRECTORY = .../dummy-42motor-fw` —— 确认源是 42 而非 35 |
| `<V2>/2.Firmware/build/motor42-baseline/Ctrl-Step-STM32-fw.bin` | 裸二进制 | **74,436 字节(约 73KB)**。Flash 128K,标定区从 0x08017C00(偏移 95K)开始 → **当前还有约 22KB 余量**,未与标定区冲突 |
| `<V2>/2.Firmware/build/motor42-baseline/Ctrl-Step-STM32-fw.hex` | Intel HEX,烧写用 | 209KB |
| `<V2>/2.Firmware/build/motor42-baseline/Ctrl-Step-STM32-fw.elf` | 带调试符号的 ELF | 1.26MB,配合 OpenOCD/gdb 调试用 |
| `<V2>/2.Firmware/build/motor42-baseline/Ctrl-Step-STM32-fw.map` | 链接映射 | 590KB。`Memory region` 段确认 `RAM 0x20000000 len 0x5000`(20K)、`FLASH 0x08000000 len 0x20000`(128K)。查某个符号占多少 Flash/RAM 来这里 |
| `<V2>/2.Firmware/build/motor42-baseline/Makefile`、`cmake_install.cmake`、`CMakeFiles/` | 生成的构建系统 | `CMakeFiles/CMakeError.log` / `CMakeOutput.log` 记录工具链探测过程 |

重新构建:在 `dummy-42motor-fw/` 下 `cmake -B <builddir> -DCMAKE_BUILD_TYPE=Debug && cmake --build <builddir>`;烧写:`openocd -f stlink.cfg -c "program Ctrl-Step-STM32-fw.hex verify reset exit"`。

---

### `Dummy 源码注释/` 目录

6 个带**中文注释的源码副本**,是给人阅读用的参考资料,**不参与任何构建**(不在任何 `CMakeLists.txt` 的 `GLOB` 路径里)。

**对应的原文件**(已用"去注释后逐行比对"确认):

| 注释版文件 | 原文件(仓库相对路径) | 注释版行数 / 原文行数 | 代码是否同步 |
|---|---|---|---|
| `6dof_kinematic.h` | `source/1.Dummy V2任同学整理/2.Firmware/dummy-ref-core-fw/Robot/algorithms/kinematic/6dof_kinematic.h` | 134 / 83 | **完全一致**(去注释后 0 行差异) |
| `6dof_kinematic.cpp` | `.../dummy-ref-core-fw/Robot/algorithms/kinematic/6dof_kinematic.cpp` | 643 / 509 | 代码一致,但**有语法破坏**(见下) |
| `ctrl_step.cpp` | `.../dummy-ref-core-fw/Robot/actuators/ctrl_step/ctrl_step.cpp` | 340 / 338 | **完全一致** |
| `dummy_robot.h` | `.../dummy-ref-core-fw/Robot/instances/dummy_robot.h` | 315 / 213 | **完全一致** |
| `dummy_robot.cpp` | `.../dummy-ref-core-fw/Robot/instances/dummy_robot.cpp` | 640 / 567 | **完全一致** |
| `main.cpp` | `.../dummy-ref-core-fw/UserApp/main.cpp` | 327 / 216 | 代码一致,但**有语法破坏**(见下) |
| `motor.cpp` | `.../dummy-42motor-fw/Ctrl/Motor/motor.cpp` | 770 / 639 | 代码一致,但**有语法破坏**(见下) |

**重要:只有 `motor.cpp` 来自电机固件,其余 5 个都来自主控固件 `dummy-ref-core-fw`。** 这个目录放在 `2.Firmware/` 下容易误以为是电机固件的注释版,实际 6 份里 5 份讲的是主控的运动学、机器人实例和 CAN 客户端。

**与主线代码的同步性**:**全部同步,无版本差异**。用 `gcc -fpreprocessed -dD -E -P` 去掉注释和空白后比对,6 个文件的有效代码与当前主线**一字不差**,时间戳(2024-02-15~17)也与当时的代码一致。可以放心把注释版当作当前代码的解读来读。

**注释质量**:注释是 **LLM(明显是 ChatGPT)批量生成**后人工粘贴进源码的,特征明显:
- 行内注释多为英文原注释的直译 + 补充,例如 `// 1.Encoder data Update  1. 更新编码器数据`;
- 函数前有段落式的中文说明,解释得**基本准确且相当详细**(`motor.cpp` 把 20kHz 闭环的七个阶段、DCE 定点运算逐句讲了);
- `6dof_kinematic.cpp` 里有价值的增量:手画了一份 **DH 参数表(θi/di/ai/αi)** 并逐行解释每个连杆参数的几何含义 —— 这是原文没有的,读运动学时值得看;
- 文件编码 UTF-8,除 `motor.cpp` 外均为 **CRLF** 行尾。

**三个文件被注释过程破坏了语法,无法编译(重要)**:
1. `main.cpp` 第 152~156 行附近,ChatGPT 回答里的 markdown 代码栅栏被**原样粘进去**:出现了裸的 `cpp` 和 `Copy code` 两行(**没有 `//` 前缀**),后面还跟着一整份**未注释的 `ThreadOledUpdate()` 重复定义**。
2. `6dof_kinematic.cpp` 第 144 行起,`tmp_DH_matrix[6][4]` 的初始化列表**缺少收尾的 `};`**,紧跟着是裸的 ASCII 表格行(`|---------------------------------|`、`| 0  L_BASE  D_BASE  -π/2 |` …),同样没有注释符。
3. `motor.cpp` 第 375 行在堵转检测的 `if (` 之后多插了一个**不配对的 `(`**(`if (// Current Mode 电流模式` 后面独立一行 `(`),括号不平衡。

→ **结论:这 6 个文件只能当文档读,不能当代码编译或拷回工程使用。** 若需要可编译的带注释版本,得先修掉上述三处。

---

### 本固件可回答的典型问题 → 去哪个文件

(路径均相对仓库根 `/home/lbz/Dummy-Robot/`,公共前缀 `source/1.Dummy V2任同学整理/2.Firmware/`)

| 问题 | 去哪个文件 |
|---|---|
| 主控发什么 CAN 帧控制关节?命令码有哪些?ID 怎么编? | `dummy-42motor-fw/UserApp/protocols/interface_can.cpp`(设备侧全部命令码)+ `dummy-42motor-fw/Core/Src/can.c`(波特率 1Mbps、`id = StdId>>7`、`cmd = StdId&0x7F`)+ 主控侧 `dummy-ref-core-fw/Robot/actuators/ctrl_step/ctrl_step.cpp` |
| 闭环控制环跑多快?由什么驱动? | `dummy-42motor-fw/Ctrl/Motor/motion_planner.h`(`CONTROL_FREQUENCY = 20000`)+ `Core/Src/tim.c`(TIM4 PSC=71/ARR=49)+ `UserApp/main.cpp`(`Tim4Callback20kHz`) |
| 位置环/速度环的控制律和 PID 参数在哪?怎么调? | `dummy-42motor-fw/Ctrl/Motor/motor.cpp` 的 `CalcDceToOutput`(位置环 DCE)/ `CalcPidToOutput`(速度环 PID);默认值在 `Ctrl/Motor/motor.h` 构造函数和 `UserApp/main.cpp`(dce 200/80/300/250,pid 5/30/0);运行时改用 CAN `0x17~0x1A` |
| 电流限制、标定电流、最大速度、最大加速度的默认值 | `dummy-42motor-fw/UserApp/main.cpp` 的 `BoardConfig_t` 默认初始化块(1000mA / 2000mA / 30 r/s / 100 r/s²);兜底默认在 `Ctrl/Motor/motor.h` 构造函数 |
| 细分数是多少?一圈多少个计数?电角度怎么算? | `dummy-42motor-fw/Ctrl/Motor/motor.h`(`200 × 256 = 51200` 细分步/圈)+ `Ctrl/Driver/tb67h450_base.cpp`(低 10 位 = 1024 计数/电周期,A 相超前 256) |
| mA 怎么变成 TB67H450 的 VREF?PWM 频率和分辨率? | `dummy-42motor-fw/Ctrl/Driver/tb67h450_base.cpp`(`×5083>>12`,0~3300mA 满程)+ `Port/tb67h450_stm32.cpp`(`>>2` 写 TIM2 CCR)+ `Core/Src/tim.c`(TIM2:70.3kHz / 10 位) |
| 编码器是什么型号?多少位?怎么读?校验方式? | `dummy-42motor-fw/Ctrl/Sensor/Encoder/mt6816_base.cpp`(MT6816,寄存器 0x03/0x04,奇校验,重试 3 次)+ `encoder_base.h`(`RESOLUTION = 16384`,14 位)+ `Port/mt6816_stm32.cpp`(SPI1 9MHz Mode3,CS=PA15) |
| 编码器标定怎么做?按什么键?标定失败的报错含义? | `dummy-42motor-fw/Ctrl/Sensor/Encoder/encoder_calibrator_base.cpp`(7 状态机 + `Error_t` 五种错误)+ `encoder_calibrator_base.h`(采样常量)+ `UserApp/main.cpp`(两键同按 / KEY1 长按触发) |
| 标定数据 / 板级配置存在 Flash 哪里?占多大? | `dummy-42motor-fw/Port/Platform/Memory/stockpile_config.h`(标定区 `0x08017C00` + 32K;数据区 `0x0801FC00` + 1K)+ `Port/mt6816_stm32.h`(硬编码指针)+ `Port/Platform/Memory/eeprom_interface.h`(EEPROM 类) |
| 某个引脚接什么?LED/按键/拨码开关/H 桥在哪个脚? | `dummy-42motor-fw/Core/Inc/main.h`(全部引脚宏)+ `Core/Src/gpio.c`(模式/上拉)+ `Port/led_stm32.cpp`、`Port/button_stm32.cpp` |
| CAN 节点 ID 怎么确定?为什么改了 ID 不生效? | `dummy-42motor-fw/UserApp/main.cpp` 第 22~28、58 行(3 位拨码 PA8/PA9/PA10,每次上电覆盖 EEPROM)+ `UserApp/protocols/interface_can.cpp` 的 `0x11` |
| LED 闪几下代表什么故障? | `dummy-42motor-fw/Ctrl/Signal/led_base.cpp`(LED1:1 闪=未标定、2 闪=堵转、3 闪=过载;LED0:心跳=运行、常亮=到位) |
| 堵转/过载保护的判定条件和恢复方式? | `dummy-42motor-fw/Ctrl/Motor/motor.cpp` 的 "State Check" 段(满额电流 + 速度 < 0.2 r/s 持续 1 秒;堵转只能手动清,过载自动清)+ `ClearStallFlag()` |
| 梯形加减速怎么实现的?有 S 曲线吗? | `dummy-42motor-fw/Ctrl/Motor/motion_planner.cpp`(梯形,无 S 曲线;`PositionTracker::CalcSoftGoal` 的刹车距离判据) |
| 温度是怎么测的?为什么读回来是 0? | `dummy-42motor-fw/Core/Src/adc.c`(`AdcGetChipTemperature()`,NTC Beta 方程,PA1)+ `UserApp/main.cpp`(100Hz 回调里 1s 采一次,受 `enableTempWatch` 控制,启动时被强制置 false,需 CAN `0x7d` 打开) |
| 串口调试命令有哪些?波特率?printf 输出到哪? | `dummy-42motor-fw/UserApp/protocols/interface_uart.cpp`(`c`/`v`/`p` 三条)+ `Core/Src/usart.c`(115200,IDLE+DMA 收包)+ `Port/Platform/retarget.c`(`_write` → `HAL_UART_Transmit`) |
| 怎么编译/烧写?用什么工具链?Flash 还剩多少? | `dummy-42motor-fw/CMakeLists.txt`、`STM32F103CBTx_FLASH.ld`、`stlink.cfg`;基线产物与余量看 `<V2>/2.Firmware/build/motor42-baseline/`(Debug 构建 73KB / 128K) |
| 42 和 35 固件到底差在哪? | 只差 `UserApp/main.cpp` 的 `dce_kp`(200 vs 195)+ 3 处 `stdint-gcc.h` 头文件 + `Ctrl/Sensor/Encoder/mt6816_base.h` 的纯虚声明。详见本文「42 与 35 固件的差异」一节 |
| 减速比在哪里配置? | **不在电机固件里**,在主控 `dummy-ref-core-fw/Robot/actuators/ctrl_step/ctrl_step.cpp` 的 `CtrlStepMotor` 构造参数 `reduction` |
| 想看带中文注释的运动学 / CAN 客户端 / 闭环代码 | `Dummy 源码注释/`(6dof_kinematic、dummy_robot、ctrl_step、main 来自主控;motor.cpp 来自 42 电机固件)。注意其中 `main.cpp`、`6dof_kinematic.cpp`、`motor.cpp` 语法已被破坏,只能读不能编译 |

---

## 九、硬件 / 3D模型 / BOM

> ⚠️ **要动手打板或 3D 打印,先看第十三章,不要在本章选版本。** 本章是全部硬件/模型文件的清单与说明;**哪个版本该用、哪些不能用,已在「十三、版本判定与打板选型」定稿**(PCB 用 auk 的 Gerber = V1.01;结构件用「Dummy V2 版本 视频款」)。本章列出的 `PCB源文件`、焊盘更改版、`<V2>` 的 motor42 Gerber 等均**不在**选用之列。

所有路径相对仓库根 `/home/lbz/Dummy-Robot/`。公共前缀 `source/1.Dummy V2任同学整理/`（下文简写为 `<V2>/`）。
**注意**：路径含空格和中文，shell 操作必须加引号。

---

### 1. 硬件 `<V2>/1.Hardware/`（57 个文件，4 块板）

#### 1.1 关键结论（先看这个）

- **4 块板全部是 Altium Designer 工程**，不是嘉立创 EDA、不是 KiCad。证据：`.PcbDoc` / `.SchDoc` / `.PrjPCB`，Gerber 为 Altium 风格扩展名（`.GTL/.GBL/.GTO/.GTS/.GPT/.GM13/.APR_LIB/.EXTREP/.DRR`）。没有任何 `.ejsonprj`/`.eprj`/`.kicad_pcb`。
- **只有 LedRing 有 `.PrjPCB` 工程文件**；motor35 / motor42 / ref-controller **缺工程文件**，只能单独打开 `.PcbDoc` 和各 `.SchDoc`（Altium 里需手动建工程再 Add Existing）。
- 三个 `*.html` 是 **InteractiveHtmlBom 生成的交互式 BOM**（HTML 内 `<title>Interactive BOM for KiCAD</title>` 只是该工具默认标题，数据由 Altium 工程导出）。板型数据在 `var pcbdata = JSON.parse(LZString.decompressFromBase64("..."))`，需 LZ-String 解压才能文本检索（`pip install lzstring`）。
- 板子对应关系：`motor42` → 42 步进电机关节驱动板（J1/J2/J3）；`motor35` → 35 步进电机关节驱动板（J4/J5/J6）；`ref-controller` → REF 示教器/主控板（STM32F405 + ESP32）；`LedRing` → 基座灯环小板。
- **「焊盘更改版」`.rar` 里只有一个 `.PcbDoc`**，没有原理图、没有 Gerber，是在原 PCB 上改焊盘（时间戳 2024-07-17，比 `PCB源文件/` 里的 2024-03 新）。仓库内 **没有任何文字说明改了什么焊盘**，只能在 Altium 里和原版 diff。motor35 的 rar 内文件名错位为 `Motor-3（焊盘更改版）5.PcbDoc`。

#### 1.2 文件表

| 文件/目录 | 作用 | 要点 |
|---|---|---|
| `<V2>/1.Hardware/README.md` | 木子晓汶版相对稚晖君原版的 7 条改进 | 连接器 1.0mm→1.5mm 插针防脱、删除 base 板并集成进主板、加 switching LDO（2A，解决原版 MCU LDO 发热）、LED ring + buzzer 控制从 ESP32 移到 STM32、降量产成本。原理图版权属稚晖君，PCB 由木子晓汶设计 |
| `<V2>/1.Hardware/motor42/PCB源文件/Motor-42.PcbDoc` | 42 驱动板 PCB（Altium，4.1MB） | 板上主要器件：STM32F103CBT6(U3)、TB67H450FNG ×2(U1/U2)、MT6816 磁编码器(U8)、SN65HVD232D CAN(U5)、ME3116 DC-DC(U6)、LP2992-3V3(U7)；元件总数 79，31 个 BOM 分组 |
| `<V2>/1.Hardware/motor42/PCB源文件/*.SchDoc` | 42 板原理图，按模块分页 | `MCU` / `Drive` / `Power` / `Interface` / `Port` 共 5 页。**无顶层 `.PrjPCB`，也无 Main.SchDoc 顶层图纸** |
| ~~`<V2>/1.Hardware/motor42/PCB源文件/History/`~~ | Altium 自动版本备份 | **已于 2026-10-08 删除**(21 项 / 48 MB)。当前 `PCB源文件/` 下只剩有效文件:`Motor-42.PcbDoc` + 5 页原理图(MCU/Drive/Power/Interface/Port) |
| `<V2>/1.Hardware/motor42/motor42 Gaber.zip` | **42 板 Gerber + 钻孔**（2024-03-24，31 文件） | Altium Gerber：`.GTL/.GBL/.G1/.G2`（4 层板）+ `.GTO/.GTS/.GTP/.GBO/.GBS/.GBP` + 钻孔 `.GG1`、报告 `.REP/.EXTREP`。注意包内还夹了一份 `README.md`。打嘉立创直接传这个 zip |
| `<V2>/1.Hardware/motor42/Motor-42.html` | 42 板交互式 BOM（172KB） | metadata: title=`Motor-42`, date=`2023-11-29 11:56`。浏览器打开可点元件高亮位置，贴片时对照用 |
| `<V2>/1.Hardware/motor42/Motor-42（焊盘更改版）.rar` | 42 板焊盘修改版 PCB | 内含单一 `Motor-42.PcbDoc`（4.13MB，2024-07-17）。比 `PCB源文件/` 新，**但没配套 Gerber，要自己重新出光绘** |
| `<V2>/1.Hardware/motor35/PCB源文件/Motor-35.PcbDoc` | 35 驱动板 PCB（Altium，4.07MB） | 器件型号与 42 板**完全相同**（同一套设计，仅板型/布局不同）；元件总数 72 |
| `<V2>/1.Hardware/motor35/PCB源文件/*.SchDoc` | 35 板原理图 5 页 | 同样 `MCU/Drive/Power/Interface/Port`，无 `.PrjPCB` |
| `<V2>/1.Hardware/motor35/PCB源文件/History/` | Altium 备份 2 份(4.3 MB,**未删除**) | `Motor-35.~(1)` / `~(3)` |
| `<V2>/1.Hardware/motor35/motor35 Gaber.zip` | **35 板 Gerber**（2024-03-24，34 文件） | 4 层（`.G1/.G2`），含 `.DRR` 钻孔报告 |
| `<V2>/1.Hardware/motor35/Motor-35.html` | 35 板交互式 BOM | title=`Motor-35`, date=`2023-12-19 22:24` |
| `<V2>/1.Hardware/motor35/Motor-35（焊盘更改版）.rar` | 35 板焊盘修改版 | 内含 `Motor-3（焊盘更改版）5.PcbDoc`（**文件名中文括号插在 "Motor-3" 和 "5" 之间，疑为重命名失误**），4.07MB，2024-07-17 |
| `<V2>/1.Hardware/ref-controller/PCB源文件/REF-Base.PcbDoc` | 主控/示教器板 PCB（Altium，5.2MB，最大的板） | 器件：STM32F405RGT6(U12)、ESP32（BOM 中写 `ESP32_SIP`/QFN-48，采购项为 ESP32-PICO-D4）、CP2102 USB 串口(U1)、MPU6050(U10)、NRF24L01 模块(U7)、SN65HVD232D(U11)、SY8089 2A + ME3116 电源、MLT-7525 蜂鸣器、Type-C(J1)；元件总数 98，52 个 BOM 分组。6 层/多层（Gerber 有 `.GP1/.GP2` 内电层） |
| `<V2>/1.Hardware/ref-controller/PCB源文件/REF-Controller.SchDoc` | 主控板原理图（单页） | **目录里没有 `Main.SchDoc`**；`REF_V1.01.zip` 里才有 `Main.SchDoc` → 原理图存在两套命名，需确认哪个对应当前 PcbDoc |
| `<V2>/1.Hardware/ref-controller/REF_V1.01.zip` | 主控板 V1.01 源文件备份（3.1MB） | 只有 2 个文件：`Main.SchDoc`(2023-12-15) + `REF-Base.PcbDoc`(2023-12-19)。**这是源文件备份，不是 Gerber** |
| `<V2>/1.Hardware/ref-controller/ref-controller-gerber.zip` | **主控板 Gerber**（2024-03-24） | 含完整光绘 + 内电层 `.GP1/.GP2`，并额外带一个 `REF_V1/` 子目录（2023-11-13 的 DRC 报告 `Design Rule Check - REF-Base.drc/.html` + `.apr`） |
| `<V2>/1.Hardware/ref-controller/REF-Base.html` 与 `PCB源文件/PnPout/REF-Base.html` | 主控板交互式 BOM，**两份内容相同**（各 180KB） | metadata: title=`REF-Base`, date=`2023-11-29 10:08`。`PnPout/` 是 Altium 贴片输出目录 |
| `<V2>/1.Hardware/LedRing/LedRing.PrjPCB` + `.PrjPCBStructure` | **唯一完整的 Altium 工程文件** | 打开这个即可加载灯环工程 |
| `<V2>/1.Hardware/LedRing/LedRing.PcbDoc` / `Main.SchDoc` | 灯环 PCB + 原理图 | 板很小（Gerber 总计仅 140KB），双层板（无 `.G1/.G2`） |
| `<V2>/1.Hardware/LedRing/led gaber.zip` | **灯环 Gerber**（2024-02-20，33 文件） | 目录结构为 `Project Outputs for LedRing/`（Altium 默认输出路径，说明确实有工程文件） |
| `<V2>/1.Hardware/motor42/desktop.ini`、`ref-controller/desktop.ini` | Windows 残留文件 | 无内容价值 |

#### 1.3 查 BOM/板上器件的脚本模板

`*.html` 里的器件清单被 LZ-String 压缩，grep 不到型号。解压方法：

```python
import re, json, lzstring
s = open(path, encoding='utf-8-sig').read()
m = re.search(r'var pcbdata = JSON\.parse\(LZString\.decompressFromBase64\("(.*?)"\)\)', s, re.S)
d = json.loads(lzstring.LZString().decompressFromBase64(m.group(1)))
# d["metadata"] -> title/date;  d["bom"]["both"/"F"/"B"] -> [数量, 型号, 封装, [[位号, idx], ...], 额外字段]
```

---

### 2. 3D 模型 `<V2>/4.Model/`（157 个文件）

文件类型分布：41 `.stl`、39 `.step/.STEP`、26 `.SLDPRT`、19 `.pdf`、9 `.SLDDRW`、9 `.dxf`、4 `.zip`、4 `.3mf`、3 `.md`、2 `.rar`、1 `.png`。

#### 2.1 三套模型的关系与选择

| 版本目录 | 来源 | 主要格式 | 定位 |
|---|---|---|---|
| `稚晖君原版模型/`（4 文件） | 原作者 peng-zhihui，2022-10-21 | `.step` | **祖版/参考**。与本仓库的 V2 电控和 BOM 不匹配，不要直接下单 |
| `木子晓汶版本3D模型/`（94 文件） | 社区改版（PCB 作者同一人） | `.stl` 为主 + SolidWorks 源文件 `Out_stp1/` | 中间版本。README 明确"自行承担风险"，且含未完的想法（J6 考虑换更便宜的 28 行星减速器） |
| `Dummy V2 版本 视频款/`（59 文件） | 论坛 V2 版本 / B 站复刻教学视频对应款 | 3D打印 `.stl`+`.3mf`、CNC `.step`、2D 工程图 `.pdf` | **推荐用于实际复刻**。根 `README.md` 写明 `5.Bom/` "仅为视频链接中 V2 模型的硬件选型"，即 **BOM 只与视频款对应**；`6.Docs/复刻审计_2026-09-06/deepseek_mechanical.md` 与 `Dummy_V2复刻与学习方案_初稿.md` 也把机械基线锁定在视频款 |

**版本混乱风险（已被审计文档记录）**：三套并存但只有视频款有配套 BOM；视频款内部还有 `改版/`，与 `CNC加工STEP文件/` 的同名零件（基座、J1）**替换关系未确定，不可同时下单**。

#### 2.2 推荐款：`Dummy V2 版本 视频款/`

| 文件/目录 | 作用 | 要点 |
|---|---|---|
| `Dummy-B v2装配体.step` | **视频款主装配体**（23MB） | 整机装配基线，查装配关系/干涉先看这个 |
| `CNC加工STEP文件/`（9 个 `.step`） | **CNC 金属件**：`基座` `J1` `J23` `J4` `J4法兰盘` `J5A` `J5B` `J5法兰盘` `J6` | 发 CNC 打样用。`J23` = J2 与 J3 共用的大臂连杆；法兰盘为关节输出端连接件 |
| `3D打印STL文件/` J 系列 STL | **3D打印结构件**：`J1` `J2J3` `J4` `J4法兰盘` `J5A` `J5B` `J5法兰盘` `J6` | 与 CNC 件一一对应的塑料版（低成本替代） |
| `3D打印STL文件/基座.stl` `基座.3mf` `基座底板.stl` `基座底板.3mf` | 基座本体 + 底板 | `.3mf` 为含打印参数的切片工程（基座、基座底板、35PCB外壳A/B 各有一份） |
| `3D打印STL文件/35PCB外壳A/B`、`42PCB外壳A/B` | 关节驱动板外壳（35 板 / 42 板各 2 片对合） | 与 `1.Hardware/` 的 motor35/motor42 板对应 |
| `3D打印STL文件/外壳A.stl` `外壳B.stl` `外壳C.stl` | 臂身外壳 | **`外壳A.stl` 与 `外壳B.stl` md5 完全相同**（`946699c9…`），疑为同一件两命名或漏传，打印前须确认 |
| `3D打印STL文件/控制器外壳.stl` `控制器内衬.stl` `控制器屏幕底板.stl` | REF 示教器（手持控制器）外壳三件 | 配 `1.Hardware/ref-controller` 板 + OLED |
| `3D打印STL文件/dummy 亚克力 PCB盖板 图纸.zip` | 亚克力 PCB 盖板激光切割图 | 包内 4 文件：`35.step`/`35.pdf`、`42.step`/`42.pdf`。**不要解压到项目目录** |
| `Dummy-B 2D工程图/Dummy-B 2D工程图.pdf` | 整套 2D 工程图（合并版） | 找尺寸/公差查这里 |
| `Dummy-B 2D工程图/工程图拆分版本/` | 同一套图拆成 10 个 PDF | `1.pdf`–`7.pdf` + `Baseboard.pdf` + `J4法兰盘.pdf` + `j5法兰盘.pdf`（文件名不带零件名，需逐个翻） |
| `Dummy-B 2D工程图/工程图拆分版本.rar` | 上目录的压缩副本（内容 8 文件，与已解压目录重复） | 冗余，可忽略 |
| `改版/Dummy-B.STEP` | **改版整机装配体**（34MB，比主装配体更大） | 与 `Dummy-B v2装配体.step` 并存，差异未说明 |
| `改版/基座改版.step` `改版/J1改版.step` | 改版的基座、J1 | 与 `CNC加工STEP文件/基座.step`、`J1.step` 疑为替代关系，**二选一** |
| `改版/改版工程图/`（8 PDF） | 改版工程图：`基座改版` `J1改版` `J23` `J4` `J5A` `J5B` `j5法兰盘` `J6` | `改版/改版工程图.rar` 是同内容的压缩副本，冗余 |

#### 2.3 `木子晓汶版本3D模型/`（社区改版，94 文件）

命名约定（见其 `README.md`）：**文件名含 `metal` 的是 CNC 件**，其余为 3D 打印件。

| 文件/目录 | 作用 | 要点 |
|---|---|---|
| `README.md` | 命名约定 + 免责声明 | "含 metal = CNC 件"；J6 末端精度要求低，作者在考虑更便宜的 28 行星减速器 |
| 根目录 7 个 STL：`base` `joint1` `joint23` `joint4` `joint5` `joint6` `controller_enclosure` | 旧一轮打印件（基座、J1、J2+J3、J4、J5、J6、控制器外壳） | 与 `latest/` 重复，属旧版 |
| `latest/`（7 STL + README） | **该版本最新打印件**：`base` `j1` `j2j3` `j4` `j5` `j6` `controller_enclosure` | README: "For 3d printed dummy"。用这版，不要用根目录那 7 个 |
| `m42/`（2 STL） | 42 电机支架：`motor42-bracket-bot`（打印）、`motor42-bracket-top-metal`（**CNC**） | |
| `m35/`（2 STL） | 35 电机支架：`motor35-bracket-bot`（打印）、`motor35-bracket-top-metal`（**CNC**） | |
| `mini8-bracket-metal.stl` `mini11-bracket-metal.stl` | 谐波/行星减速器支架（CNC） | 对应 BOM "其它" 表里的 mini8 ×1、mini11 ×4 减速器 |
| `ref-controller/contorller-oled-bracket.stl` | 示教器 OLED 支架（**目录名 `contorller` 拼写错误**） | |
| `stps/` | **空目录**，只有一个 `README.md` | README 写 "step 3d models / Thanks to PULI @pu_li_ce / Refer to Fan-feature branch" → **STEP 文件没有随仓库提交，在另一个分支**。这是一个实际缺失 |
| `Out_stp1/` | SolidWorks 原始工程 + 各类导出，是该版本的"源" | 下面细分 |
| `Out_stp1/src/`（26 `.SLDPRT`） | **SolidWorks 零件源文件**。零件：`base`/`base1`/`base2`、`Joint1`、`Joint2 & Joint3`、`Joint4`、`Joint5`、`Joint6`、`min-11-bra-connection`、`mini8-cover1105`、`motor35-br-top`、`motor42-br-top`、`tape` | 多个零件有 v1/v2/v3 并存（如 `3DJoint4_Dummy v164 v1/v2/v3`）；另有 5 个 `~$` 开头的 SolidWorks **锁文件/临时文件**（`~$3DJoint4…` 等），无用，应忽略 |
| `Out_stp1/CNC/`（13 `.STEP`） | **CNC 加工用 STEP**：`base`/`base1`/`base2`、`Joint1`、`Joint2 & Joint3`、`Joint4`、`Joint5`、`Joint6`、`min-11-bra-connection`、`mini8-cover1105`、`motor35-br-top`、`motor42-br-top`、`tape` | 这是该版本下单 CNC 的目录 |
| `Out_stp1/3D/`（4 `.STEP`） | 3D 打印用导出：`Joint2 & Joint3`（两份，一份带 `_1`）、`Joint4 v2`、`Joint5 v2` | 不完整，只有 4 件 |
| `Out_stp1/Drawing/`（9 `.SLDDRW`） | SolidWorks **2D 工程图源**：base、base1、Joint1、Joint2&Joint3、Joint4、Joint5、Joint6、min-11-bra-connection、mini8-cover1105 | 需 SolidWorks 打开；没有导出 PDF |
| `Out_stp1/dxf/`（9 `.DXF`） | 上述 9 张工程图的 DXF 导出 | 可用 CAD/在线工具查看，**无 SolidWorks 时看这个** |
| `Out_stp1/BACK/` | 备份/杂项 | `Joint5_Dummy v164 v1.STEP`；`metal_step/` 内有 `min-11-bra-connection.step`、`motor35-br-top.step`、`motor42-br-top.step`、`mini8-cover1105/`（含 `mini8-cover1105.step` + `MINI8-2D-DRAW.png` 二维图）；另有 `metal_step.zip`、`mini8-cover1105.zip` 压缩副本和 macOS 残留 `__MACOSX/._mini8-cover1105.zip` |

#### 2.4 `稚晖君原版模型/`（4 文件，2022-10-21）

| 文件 | 作用 | 要点 |
|---|---|---|
| `Dummy v164.step` | **原版整机装配体**（33.7MB） | "v164" 这个版本号被后续版本文件名继承（`*_Dummy v164 v1.SLDPRT`） |
| `Case v17.step` | 原版外壳/控制器壳（8.1MB） | |
| `Motor42-上盖.step` / `Motor42-下盖.step` | 原版 42 电机支架上下盖 | 对应木子版的 `motor42-bracket-top/bot` |

---

### 3. BOM `<V2>/5.Bom/dummy V2版本_bom.xlsx`

读法：`~/miniconda3/bin/python3`（已装 `openpyxl` 3.1.5）。**6 个 sheet**，前三个是按板子的 Altium 导出 BOM，后三个是采购清单。

| Sheet | 行×列 | 结构 | 要点 |
|---|---|---|---|
| `REF` | 72×9 | `Comment \| Quantity \| Designator \| Footprint \| Layer \| 淘宝价格 \| 立创价格 \| 备注` | 主控板，**57 条物料行**（Top/Bottom 分段各列一次），之后 15 行是中文说明与淘宝链接。注：列顺序与另两个 sheet 不同（Quantity 在第 2 列） |
| `Motor-42` | 35×9 | `Comment \| Description \| Designator \| Footprint \| Quantity \| Layer \| 淘宝价格 \| LC价格 \| 备注` | 42 驱动板，**32 条物料行** + 2 空行。唯一带 `Description` 字段的表 |
| `Motor-35` | 35×9 | `Comment \| Quantity \| Description \| Designator \| Footprint \| Layer \| 淘宝价格 \| LC价格 \| 备注` | 35 驱动板，**34 条物料行**。器件型号与 Motor-42 一致，只有数量/位号不同 |
| `部分淘宝购买版123元` | 51×12 | 立创商城购物车导出：`购买类型 \| 商品编号 \| 物料编码 \| 商品分类 \| 名称 \| 商品型号 \| 品牌 \| 封装规格 \| 单个毛重 \| 购买数量 \| 商品单价 \| 金额` | **50 条**。贵的主芯片（MCU/ESP32/CP2102/MT6816/TB67H450/CAN）**不在内**，走淘宝买，故总价低 |
| `一键购买版443元` | 58×12 | 同上列结构 | **57 条**，= 123 元版 + 主芯片。`商品编号` 是立创 `C` 号，可直接一键导入购物车 |
| `其它` | 18×7 | `内容 \| 型号 \| 数量 \| 链接 \| （空） \| 选项2 \| 说明` | **17 条机械/电机/线材**，淘宝链接。BOM 中唯一的非电子件清单 |

关键物料示例（型号 + 立创 C 号 / 数量）：

- **电机**：42 步进 `l=40` ×3（J1/J2/J3）；35 步进 `l=28` ×2；J6 用 35 步进 `l=20` ×1 带行星减速（`其它` sheet）
- **减速器**：mini11 ×4、mini8 ×1（同一淘宝链接选不同规格）
- **轴承**：5×13×4 ×4、5×10×4 ×1；配 **圆柱销 5×35 ×4**
- **编码器**：`MT6816CT-ACD` 麦歌恩零延迟磁角位置传感器，SOP-8，`C879560`，×6（6 个关节各 1），￥18.39/个 → 110.34 元，是单项最贵物料
- **主控芯片**：`STM32F405RGT6` LQFP-64 `C15742` ×1（REF 主控）；`STM32F103CBT6` LQFP-48 `C8304` ×6（每块关节驱动板 1 片，订货型）
- **无线/通信**：`ESP32-PICO-D4` `C193707` ×1、`CP2102-GMR` `C6568` ×1、`SN65HVD232DR` CAN `C30530` ×7、`NRF24L01` 模块（淘宝 ￥5.8）、`MPU6050` `QFN-24`（淘宝 ￥4.7）
- **电机驱动**：`TB67H450FNG,EL` 东芝 SOIC-8 `C545417` ×6
- **电源**：24V 6A 适配器 ×1、`ME3116AM6G`、`SY8089AAAC`、`LP2992 3V3`
- **传动/线材**：同步轮 20 齿内孔 5mm 外径 18 ×6、同步皮带（实测 130×2、150×1）、ZH1.5mm 6P 排线 50cm ×1 + 30cm ×6
- **显示**：0.78 寸 OLED 裸屏 128×80 SPI/SH1107
- 成本说明（`REF` sheet 底部）：元器件合计 285 元 + 电路板制作 110 元；淘宝部分 162 元、立创商城部分 123 元

**注意**：BOM 中 `REF` sheet 把 ESP32 标为 `ESP32_SIP`/QFN-48，采购 sheet 则为 `ESP32-PICO-D4`；两个晶振（8MHz 与 12MHz）都在采购清单里。BOM **只对应视频款机械版本**（根 `README.md` 明确声明），且不保证淘宝链接质量。

---

### 可回答的典型问题 → 去哪个文件

| 问题 | 去哪 |
|---|---|
| 42 电机板的 Gerber 在哪？ | `<V2>/1.Hardware/motor42/motor42 Gaber.zip`（Altium 光绘，直接传嘉立创。⚠️ 但 **Motor-42 缺 NC Drill，不能直接投板**，见审计 A01） |
| 板子是嘉立创 EDA 还是 Altium？用什么软件打开？ | 全部 **Altium**。只有 `<V2>/1.Hardware/LedRing/LedRing.PrjPCB` 有工程文件；其余三块板只能单独打开 `PCB源文件/*.PcbDoc` + `*.SchDoc` |
| 主控板原理图在哪？为什么有两个名字？ | `<V2>/1.Hardware/ref-controller/PCB源文件/REF-Controller.SchDoc`；另有 `REF_V1.01.zip` 内的 `Main.SchDoc`（两套命名，需确认对应关系） |
| `Motor-42.html` 是什么，怎么看里面的元件型号？ | InteractiveHtmlBom 交互式 BOM，浏览器直接打开；型号被 LZ-String 压缩，用 §1.3 的脚本解压 `var pcbdata` |
| "焊盘更改版" 改了什么？ | 无文字说明。`<V2>/1.Hardware/motor4{2,5}/Motor-4*（焊盘更改版）.rar` 内只有 `.PcbDoc`（2024-07-17），需在 Altium 中与 `PCB源文件/` 版本（2024-03）对比 |
| 关节驱动板用的 MCU / 驱动 / 编码器是什么？ | STM32F103CBT6 + TB67H450FNG×2 + MT6816 + SN65HVD232D（35/42 板完全相同）。见 BOM `Motor-35`/`Motor-42` sheet |
| 主控板用的是哪颗 MCU？ | STM32F405RGT6（U12）+ ESP32（U2）+ CP2102 + MPU6050 + NRF24L01。见 BOM `REF` sheet |
| 复刻该用哪套 3D 模型？ | `<V2>/4.Model/Dummy V2 版本 视频款/`（BOM 和教学视频都对应这一款） |
| 整机装配体 STEP 在哪？ | `<V2>/4.Model/Dummy V2 版本 视频款/Dummy-B v2装配体.step`（23MB）；改版为同目录 `改版/Dummy-B.STEP`（34MB） |
| 哪些零件要 CNC、哪些 3D 打印？ | 视频款：`CNC加工STEP文件/`(9 件) vs `3D打印STL文件/`。木子版：**文件名含 `metal` 的是 CNC**（`m42/m35/*-top-metal.stl`、`mini8/mini11-bracket-metal.stl`、`Out_stp1/CNC/`） |
| J2、J3 的零件为什么找不到？ | J2 和 J3 共用一个件，文件名是 `J23` / `joint23` / `j2j3` / `Joint2 & Joint3` |
| 2D 工程图（尺寸/公差）在哪？ | `<V2>/4.Model/Dummy V2 版本 视频款/Dummy-B 2D工程图/Dummy-B 2D工程图.pdf`（或 `工程图拆分版本/` 10 个 PDF）；改版见 `改版/改版工程图/` |
| 木子版的 STEP 文件在哪？ | `<V2>/4.Model/木子晓汶版本3D模型/Out_stp1/CNC/` 和 `Out_stp1/BACK/metal_step/`。`stps/` **是空的**，其 README 说文件在另一个 `Fan-feature` 分支 |
| SolidWorks 源零件在哪？ | `<V2>/4.Model/木子晓汶版本3D模型/Out_stp1/src/`（26 个 `.SLDPRT`，忽略 `~$` 锁文件）；工程图源 `Out_stp1/Drawing/`，无 SolidWorks 时看 `Out_stp1/dxf/` |
| 电机/减速器/轴承/皮带买什么型号？ | `<V2>/5.Bom/dummy V2版本_bom.xlsx` 的 **`其它` sheet**（17 条，含淘宝链接） |
| 元器件一键下单清单？ | 同文件 `一键购买版443元` sheet（57 条，带立创 `C` 商品编号）；省钱版见 `部分淘宝购买版123元`（主芯片走淘宝） |
| 木子版相对稚晖君原版改了什么？ | `<V2>/1.Hardware/README.md`（7 条改进：连接器 1.5mm、删 base 板、switching LDO 2A、灯环/蜂鸣器改由 STM32 控制等） |
| 示教器（手持控制器）外壳模型？ | 视频款 `3D打印STL文件/控制器外壳.stl` + `控制器内衬.stl` + `控制器屏幕底板.stl`；木子版 `latest/controller_enclosure.stl` + `ref-controller/contorller-oled-bracket.stl` |
| PCB 亚克力盖板图纸？ | `<V2>/4.Model/Dummy V2 版本 视频款/3D打印STL文件/dummy 亚克力 PCB盖板 图纸.zip`（内含 35/42 的 step + pdf） |

---

## 十、上位机软件与 ESP32 固件

本节覆盖仓库中三套上位机工具（`3.Software/`）和一个 ESP32 网络桥固件（`2.Firmware/esp32-iot/`）。
所有路径相对仓库根 `/home/lbz/Dummy-Robot/`。注意路径含空格与中文，shell 中必须加引号。

**一句话定位**：

| 工具 | 性质 | 连接方式 | 协议 |
|---|---|---|---|
| `simple-cli/` | 极简 Python 调参 CLI + 一个串口绘图 GUI | pyserial 打开 USB CDC 虚拟串口，115200 | 行式 ASCII（`!` / `#` 命令） |
| `CLI-Tool/` | ODrive `fibre` 框架改造的交互式 Python shell | pyusb/libusb 直接抓 USB bulk 端点（VID:PID = `1209:0D31/0D32/0D33`），也支持 `serial:`/`tcp:`/`udp:` | fibre 二进制 RPC（endpoint 0 下发 JSON 对象树） |
| `DummyStudio/` | Unity 3D 可视化示教/拖拽 IK 程序，**只有编译产物** | SerialPort Utility Pro 插件按 `VendorID=1209` 枚举串口，115200 | 行式 ASCII（同主控固件） |
| `esp32-iot/` | mongoose 上游仓库 + 一个改过的 ESP32 UART↔网络桥 | ESP32 WiFi STA；对外 HTTP:80 / TCP:4001 / WS:4002 / MQTT；对内 UART1 GPIO26(TX)/GPIO27(RX) @115200 | 透传字节流，自动补 `\n` → 接主控 UART4 的 ASCII 协议 |

---

### simple-cli

路径：`source/1.Dummy V2任同学整理/3.Software/simple-cli/`

| 文件 | 作用 | 关键符号/要点 |
|---|---|---|
| `simple-cli.py` | 电机 PID 调参用的交互式命令行（137 行） | `class DummyCLI(cmd.Cmd)`；`sername` 硬编码串口；波特率 115200 |
| `chatgpt_gui.py` | **文件名误导**：实际是 PyQt5 + QtChart 的 MPU6050 加速度实时曲线窗口（76 行），与 LLM/ChatGPT 完全无关 | `class MainWindow(QMainWindow)`、`#GETMPU` |
| `README.md` | 10 行使用说明（改串口名 → `start` → `kp`/`ki`/`kd` → `reboot` → 按电机按键重新校准 → `stop`） | — |

#### `simple-cli.py` 详解

- **是什么**：`cmd.Cmd` 做的 6 行级交互 shell，提示符 `Dummy-> `。唯一用途是在线调六个关节步进电机的 DCE 位置环 PID，并重启某个节点让新参数生效。
- **接口**：`pyserial`，`serial.Serial(sername, 115200, timeout=1)`。`sername` 在**第 7 行硬编码**为 macOS 的 USB CDC 设备名 `/dev/tty.usbmodem204C397F32321`——也就是主控 STM32 的 USB 虚拟串口（不是 fibre 的 bulk 通道），换机器必须手改。
- **命令实现**（都是 `write(字符串.encode())`，以 `\n` 结尾）：

| CLI 命令 | 实现函数 | 实际写出的字节 | 响应判据 |
|---|---|---|---|
| `start` | `start()` (L10) | `!START\n` | 轮询直到读到 `Started ok` |
| `stop` | `stop()` (L39) | `!DISABLE\n` | 轮询直到读到 `ok` |
| `kp <node> <v>` | `dce_kp()` (L50) | `#SET_DCE_KP <node> <v>\n` | 不读回 |
| `ki <node> <v>` | `dce_ki()` (L57) | `#SET_DCE_KI <node> <v>\n` | 不读回 |
| `kd <node> <v>` | `dce_kd()` (L64) | `#SET_DCE_KD <node> <v>\n` | 不读回 |
| `reboot <node>` | `node_reboot()` (L71) | `#REBOOT <node>\n` | 不读回 |
| `quit` / `help` | — | — | — |

- `checkSerial()` (L22) 在每条 `#` 命令前检查端口是否已打开/掉线，未 `start` 过就提示 "Please run start command first!"。
- **注意一个隐蔽行为**：`checkSerial()` 内部会 `ser.read()` 吞掉一个字节，所以这个工具不适合做严格的请求-响应解析。
- node 取值 1..6（主控侧校验 `node >= 1 && node <= 6`，对应 `dummy.motorJ[node]`）。

#### `chatgpt_gui.py` 详解

- **任务描述里假设它是「用 LLM 控制机械臂的实验性 GUI」，实际并不是。** 通读全文 76 行，没有任何 HTTP 客户端、没有 `openai`/`requests`/`http.client` 导入、没有任何 prompt 文本、没有模型名、没有自然语言到指令的转换逻辑。文件名很可能是从别的实验里复制后忘了改。
- **实际功能**：PyQt5 主窗，标题 `"MPU6050 Data"`，内嵌一个 `QChart`，三条 `QLineSeries`（Accelerometer X/Y/Z），Y 轴固定 `[-2, 2]`（单位看起来是 g），X 轴滚动显示最近 120 s。
- **数据来源**：`QTimer` 每 500 ms 触发 `update_chart()`，向串口写 `#GETMPU\n`，读一行；若以 `ok` 开头则取 `line[3:]` 按空格分成 3 个 float 追加到曲线。超过 120 点时裁剪到最后 20 点。
- **串口**：第 41 行 `serial.Serial('/dev/tty.usbmodem204C397F32321', 115200)`，同样硬编码。
- **凭据检查结论：本文件（及整个 `simple-cli/`、`CLI-Tool/`）未发现任何硬编码 API key、token 或密码。** 全目录内唯一的"硬编码常量"是串口设备路径，不属于凭据。
- **重要落差**：`#GETMPU` 在主控固件里**不存在**。`grep -rn GETMPU` 全仓库只命中本文件；`dummy-ref-core-fw/UserApp/protocols/ascii_protocol.cpp` 的 `#` 分支只实现了 `GETJPOS / GETLPOS / SET_DCE_K* / REBOOT / CMDMODE`，其余 `#` 命令统一回 `"ok"`（无数据）。所以这个 GUI 跑起来只会收到裸 `ok`，拆不出 3 个浮点 → **是未完成/已失效的实验代码**（或者针对某个未入库的固件分支）。

---

### CLI-Tool

路径：`source/1.Dummy V2任同学整理/3.Software/CLI-Tool/`

这是把 ODrive 的 `odrivetool` 整体改名移植过来的工具链：`fibre`（通信框架，基本原封不动）+ `ref_tool`（原 `odrive_tool`，改名为 REF = Robot-Embedded-Framework）。

#### 入口与杂项

| 文件 | 作用 | 关键符号/要点 |
|---|---|---|
| `run_shell.py` | 唯一入口（163 行），`argparse` 子命令分发 | 子命令：`shell`（默认）、`liveplotter`，另有未注册但代码在的 `drv-status`/`rate-test`/`udev-setup`/`generate-code`/`backup-config`/`restore-config`；全局参数 `-p/--path`（默认 `usb`）、`-s/--serial-number`、`-v`、`--version` |
| `run.bat` | Windows 启动器：用 Windows Terminal 拉一个 `cmd` 配置，再 `ipython run_shell.py -- %*` | 用 `TAG` 环境变量防重入 |
| `zadig-2.5.exe` | 第三方 USB 驱动替换工具：在 Windows 上把主控的 fibre bulk 接口驱动换成 WinUSB，否则 pyusb/libusb 打不开设备 | 仅 Windows 需要 |
| `_addition/ref_demo.py` | 11 行最小示例：`import ref_tool; my_drive = ref_tool.find_any()`，并注释了 `find_any("serial:/dev/ttyUSB0")` 的写法。`_addition/` 里只有这一个文件 | — |
| `.gitignore` | Python 打包产物忽略规则（从 ODrive 带过来的） | — |
| `.idea/` | PyCharm 工程配置（`cmd_tool.iml`、`deployment.xml`、`ros.xml` 等），无代码价值 | — |
| `fibre/__pycache__/`、`ref_tool/__pycache__/` | CPython 3.7 字节码缓存 → 这套工具当年是在 **Python 3.7** 下跑的 | — |

`run_shell.py` 典型用法：

```bash
# Windows
run.bat                         # == ipython run_shell.py -- shell
# Linux/mac
python3 run_shell.py shell                     # USB 自动发现
python3 run_shell.py -p serial:/dev/ttyUSB0 shell
python3 run_shell.py -p usb,serial:/dev/ttyUSB0 shell
python3 run_shell.py liveplotter               # 实时曲线（代码里画的是 ODrive 的 axis0/axis1 编码器，对 Dummy 需改）
```

#### `ref_tool/`（项目自己的工具代码，逐文件）

| 文件 | 作用 | 关键符号/要点 |
|---|---|---|
| `ref_tool/__init__.py` | 包初始化，把 `fibre.find_any/find_all` 提升为 `ref_tool.find_any/find_all` | **有坑**：L4-6 把 `<repo>/Firmware/fibre/python` 插进 `sys.path`，该目录在本仓库不存在；实际用的是 `CLI-Tool/fibre/`（靠 cwd 命中）。`import fibre` 包在 `try/except: pass` 里，失败会静默 |
| `ref_tool/shell.py` | 启动交互 shell，设定 Dummy 品牌 | `launch_shell()` → `fibre.launch_shell(..., branding_short="dummy", branding_long="Dummy-Robot")`；`print_banner()` 打印 "Please connect your Dummy-Robot."；向 shell 注入 `start_liveplotter`。文件内另有一份 `did_discover_device`/`did_lose_device`（L32/L56）**是死代码**，真正生效的是 `fibre/shell.py` 里那份 |
| `ref_tool/utils.py` | 杂项工具（181 行） | `start_liveplotter(get_var_callback)`（matplotlib 实时曲线，`data_rate=10`/`plot_rate=10`/`num_samples=1000`）、`print_drv_regs()`、`show_oscilloscope()`、`rate_test()`（测 RPC 吞吐）、`usb_burn_in_test()`、`yes_no_prompt()`、`OperationAbortedException`、`_VT100Colors`；Windows 下 `import win32console/colorama` |
| `ref_tool/configuration.py` | 配置备份/恢复（82 行） | `get_dict()`/`set_dict()` 递归遍历 fibre 对象树的 `config` 子对象 → dict；`backup_config(device, filename, logger)`、`restore_config(...)`、`get_temp_config_filename(device)`（按 serial_number 命名的临时 json） |
| `ref_tool/code_generator.py` | 从设备 endpoint JSON 生成 C/C++ 侧代码（69 行） | `get_flat_endpoint_list(json, prefix, id_offset)`、`generate_code(odrv, template_file, output_file)`。注意 `run_shell.py` 的 `generate-code` 分支引用了 `args.template`/`args.output`，但没有对应 `add_argument` → **该子命令实际不可用** |
| `ref_tool/version.py` | 版本号与 udev 规则（94 行） | `version_str_to_tuple()`、`get_version_from_git()`、`get_version_str()`、`setup_udev_rules(logger)`（Linux 上装 udev 规则以免 sudo） |

#### `fibre/`（ODrive 的 RPC/发现协议库，不逐个精读）

角色：提供"**把 MCU 里的 C++ 对象树直接当成 Python 对象访问**"的 RPC 层。设备在 endpoint 0 返回一段描述对象树的 JSON，库据此动态构造 Python 代理对象，于是属性读写和函数调用会被翻译成二进制包。

| 文件 | 作用 | 关键符号 |
|---|---|---|
| `fibre/__init__.py` | 导出 `find_any`/`find_all`/`launch_shell`/`Logger`/`Event`/`ChannelBrokenException` 等 | — |
| `fibre/discovery.py` | 多传输并行发现（129 行）。`path` 形如 `usb` / `serial:/dev/ttyUSB0` / `tcp:...` / `udp:...`，逗号可并列 | `channel_types` 字典、`find_all()`、`find_any()`；`did_discover_channel()` 读 endpoint 0 的 JSON、算 CRC16、构造 `RemoteObject` |
| `fibre/protocol.py` | 帧格式、CRC、通道状态机（365 行） | `calc_crc8`/`calc_crc16`、`StreamToPacketSegmenter`、`PacketFromStreamConverter`、`Channel`、`ChannelBrokenException`、`ChannelDamagedException` |
| `fibre/remote_object.py` | JSON 对象树 → Python 代理（264 行） | `RemoteObject`、`RemoteProperty`、`RemoteFunction`、`StructCodec`、`EndpointRefCodec` |
| `fibre/usbbulk_transport.py` | **主传输**：pyusb/libusb 直接读写 bulk 端点（215 行） | `WELL_KNOWN_VID_PID_PAIRS = [(0x1209,0x0D31),(0x1209,0x0D32),(0x1209,0x0D33)]`；优选 `bInterfaceClass==0x00 && SubClass==0x01` 的自定义接口，退而选 CDC(`0x0a`)；Linux 下会 `detach_kernel_driver` |
| `fibre/serial_transport.py` | 串口传输 | `SerialStreamTransport`、`find_dev_serial_ports()`、`find_pyserial_ports()` |
| `fibre/tcp_transport.py` / `udp_transport.py` | TCP/UDP 传输 | `TCPTransport` / `UDPTransport` |
| `fibre/shell.py` | 真正的 shell 实现（116 行）：优先 IPython `InteractiveShellEmbed`，否则 `code.InteractiveConsole`；按 `branding_short` 命名设备变量；装 excepthook 隐藏 `ChannelBrokenException` | `launch_shell()`、`did_discover_device()`（`interactive_name = branding_short + str(index)`） |
| `fibre/utils.py` | 日志/事件/序列号格式化（237 行） | `Logger`、`Event`、`wait_any()`、`get_serial_number_str()` |

#### 连接方式与暴露的 Python 接口（最关键）

- **连接**：默认 `--path usb` → `fibre/usbbulk_transport.py`，用 **pyusb（libusb 后端）直接占用 USB bulk 端点**，不走操作系统串口驱动。所以 Windows 上必须先用 `zadig-2.5.exe` 把该接口驱动换成 **WinUSB**；Linux 上要么 root，要么 `run_shell.py udev-setup` 装 udev 规则。VID:PID 对得上主控固件 `dummy-ref-core-fw/USB_DEVICE/App/usbd_desc.c`（`USBD_VID 0x1209` / `USBD_PID_FS 0x0D32`）。
- **shell 里的变量名**：`branding_short="dummy"`，所以连上后第一台设备叫 **`dummy0`**（控制台提示 `Connected to Dummy-Robot <12位序列号> as dummy0`）。注意 `ref_tool/shell.py` 的帮助文本还残留着 ODrive 的 `odrv0.` / `ref0.` 字样，**是过时文案，别照抄**。
- **能不能直接 `dummy.move_j(...)`？** 能，但对象树多一层 `robot`。对象树定义在主控固件 `dummy-ref-core-fw/UserApp/protocols/cmd_protocol.cpp`（`MakeObjTree()`）和 `dummy-ref-core-fw/Robot/instances/dummy_robot.h`（`MakeProtocolDefinitions()`）：

```python
dummy0.serial_number            # ro property
dummy0.get_temperature()        # 芯片温度
dummy0.get_voltage()
dummy0.robot.move_j(j1,j2,j3,j4,j5,j6)
dummy0.robot.move_l(x,y,z,a,b,c)
dummy0.robot.homing(); dummy0.robot.resting()
dummy0.robot.calibrate_home_offset()
dummy0.robot.set_enable(True)
dummy0.robot.set_joint_speed(s); dummy0.robot.set_joint_acc(a)
dummy0.robot.set_command_mode(m)
dummy0.robot.set_rgb_enable(b); dummy0.robot.set_rgb_mode(m)
dummy0.robot.reboot()
dummy0.robot.joint_1 .. joint_6, joint_all   # 见 Robot/actuators/ctrl_step/ctrl_step.hpp
  → .angle, .set_position(pos), .set_velocity(vel), .set_current(c),
    .set_dce_kp/.set_dce_kv/.set_dce_kd, .do_calibration(),
    .apply_home_offset(), .set_node_id(id), .reboot(), .erase_configs() ...
dummy0.robot.hand.set_angle(a) / .set_enable(b) / .set_current_limit(c)
dummy0.robot.tuning.set_tuning_freq_amp(...) / .set_tuning_flag(...)
```

- 即 **fibre 通道与 ASCII 通道是两套并行的接口**：`CLI-Tool` 走 fibre 二进制 RPC，`simple-cli`/`DummyStudio` 走同一个 USB 设备上的 ASCII 行协议（`Bsp/communication/ascii_processor.cpp` 负责分流）。

---

### DummyStudio

路径：`source/1.Dummy V2任同学整理/3.Software/DummyStudio/`

> **⚠️ 仅有编译产物，无源码，无法修改。** 这是一个 Unity（Mono 后端、Windows x86_64）独立播放器构建，总计约 90 MB，构建时间戳 2022-10-21。要改功能只能找原始 Unity 工程（本仓库没有）或反编译 `Assembly-CSharp.dll`。

| 文件/目录 | 作用 | 关键符号/要点 |
|---|---|---|
| `DummyStudio.exe` | Unity 播放器可执行文件，650 KB，无业务逻辑 | — |
| `UnityPlayer.dll` | Unity 引擎运行时，27 MB | — |
| `MonoBleedingEdge/` | Mono 运行时（`EmbedRuntime/` + `etc/mono/` 配置）。Unity 自带，**不逐个列**。 | — |
| `DummyStudio_Data/` | Unity 数据目录：`globalgamemanagers*`、`level0`（唯一一个场景）、`resources.assets(.resS)`、`sharedassets0.assets(.resS)`（35 MB，模型/贴图主体）。Unity 自带结构，**不逐个列 78 个 dll**。 | — |
| `DummyStudio_Data/app.info` | 两行：`pengzhihui` / `DummyStudio` → 公司名/产品名，作者是 Dummy 项目原作者稚晖君 | — |
| `DummyStudio_Data/boot.config` | Unity 启动开关（`gfx-enable-gfx-jobs=1`、`vr-enabled=0`、`hdr-display-enabled=0`、`gc-max-time-slice=3`），**不含任何业务信息** | — |
| `DummyStudio_Data/Managed/Assembly-CSharp.dll` | **全部业务逻辑在这里**（634 KB）。要进一步了解功能必须用 ILSpy/dnSpy 反编译 | 见下 |
| `DummyStudio_Data/Plugins/x86_64/spap.dll` | SerialPort Utility Pro 的原生串口插件（SPAP = SerialPort Appendix/Plugin） | — |
| `DummyStudio_Data/StreamingAssets/serial_config.txt` | **唯一的外部可编辑配置**，纯文本两行：`VendorID=1209` / `BaudRate=115200` | 程序启动时按 VID 自动枚举并挑选串口，不需要用户选 COM 号 |
| `DummyStudio_Data/Resources/` | `unity_builtin_extra`、`unity default resources`，Unity 内置资源 | — |

#### 功能推断（基于 `Assembly-CSharp.dll` 的符号/字符串）

`strings -n 4`（ASCII 元数据名）与 `strings -el`（UTF-16 用户字符串）两路提取后可见：

- **Dummy 业务类**：`DummyRobotBridge`、`dummyRobot`、`DummyTargetTrack`、`OnRobotJointsChanged`、`OnSerialMessage`、`GetSerialDebugString`、`joints`、`jointBodys`、`IMU_port`。
- **第三方资产 1：Runtime Transform Gizmos**（命名空间痕迹 `RT*`，shader 名 `RTUnityApp/GizmoSolidHandle`、`RTUnityApp/XZGrid_Plane`、`RTUnityApp/TorusCull` 等；类 `ObjectMoveGizmo`、`GizmoScalerHandle`、`RTFocusCamera`、`SceneGizmo`；UI 文本 `Move gizmo`/`Rotation gizmo`/`Scale gizmo`/`Universal gizmo`/`Enable snapping`/`Enable vertex snapping`/`Transform Pivot:`/`Transform Space:`）→ 运行时可在 3D 场景里**拖动平移/旋转手柄**。
- **第三方资产 2：SerialPort Utility Pro**（字符串 `SerialPort Utility Pro is FREE VERSION.`、`SerialPortUtility Pro became transmission restriction (1MB) for FREE Version.`、`VendorID:`、`VID:`/`, PID:`、`Port Opened!`、`OPEN_ERROR`、`LICENSE_ERROR`、`Closing port, because it was already open!`、`ExternalConfig Apply! {0} = {1}`）。
- 场景里有示例可抓物体：`RedCube`/`BlueCube`/`GreenCube`/`YellowCube`/`Sphere`/`Cylinder`（含 `(1)` 副本）。

**结论**：DummyStudio 是一个**单场景 3D 可视化示教/遥操作程序** —— 在虚拟场景里用 gizmo 拖动目标（`DummyTargetTrack` 让机械臂末端跟随目标），实时把关节角推给真机（`DummyRobotBridge` + `OnRobotJointsChanged`），并显示串口调试字符串（`GetSerialDebugString`）。**没有**发现轨迹录制/回放相关的符号（无 `Record`/`Playback`/`Trajectory`/`Waypoint`/`Keyframe` 类名），也没有文件保存逻辑 → 更像**实时拖拽跟随**而非离线轨迹编程。

#### 与固件的通信方式（已确认的部分）

- **物理层确定**：USB CDC 虚拟串口，`VendorID=1209`、`BaudRate=115200`（`StreamingAssets/serial_config.txt`，明文可改）。与主控 `usbd_desc.c` 的 `0x1209:0x0D32` 一致，与 `simple-cli` 的 115200 一致。注意它靠 VID 枚举，**不走 fibre 的 bulk 接口**（SerialPort Utility Pro 只能开 COM 口）。
- **应用层只能推断**：`Assembly-CSharp.dll` 的 UTF-16 字符串里**没有任何 `>`/`@`/`&`/`!START`/`#GETJPOS` 这类协议字面量**，也没有 `{0},{1},...` 形式的格式串（提取到的格式串只有 `{0}={1}`、`{0}.{1}`、`[{0}{1}] {2}`、`{0:X2}`、`C:{0}, R:{1}, L:{2}`、`ADDRESS:{0}, FUNCTION:{1}, DATA:{2}` 等，均属两个第三方资产自身的调试/Modbus 文本）。命令很可能是用 `StringBuilder`/逐个 `+` 拼出来的，字面量被拆碎了。
- 可确定的只是：存在 `OnSerialMessage` 回调（收）+ `DummyRobotBridge`（发），且 `OnRobotJointsChanged` 以关节角为单位。**结合主控固件只实现了 `>j1,j2,...,j6[,speed]`（MoveJ）和 `@x,y,z,a,b,c[,speed]`（MoveL）两种连续运动命令，DummyStudio 几乎必然是在发 `>` 开头的关节命令。**要确证必须反编译 `Assembly-CSharp.dll`，或抓一次真机串口。
- **已知限制**：所用的 SerialPort Utility Pro 是 **FREE 版**，单次运行累计传输上限 1 MB，超了要重启程序（字符串原文 `* This limit is resettable by rebooting application.`）。长时间高频下发关节角会撞到这个上限 —— 这是个很实用的排障知识点。

---

### esp32-iot

路径：`source/1.Dummy V2任同学整理/2.Firmware/esp32-iot/`

> **目录性质判定：这个目录 ≈ 一份完整的 mongoose 上游仓库快照 + 一处 Dummy 自己的改动。** `firmware/` 下的 `mongoose.c`/`mongoose.h`（合并后的单文件库）、`src/`（~80 个文件，mongoose 的未合并源码）、`test/`、`LICENSE`、`README.md`（标题就是 "Mongoose - Embedded Web Server / Embedded Networking Library"，Cesanta 版权）全部是上游原件。

| 文件/目录 | 作用 | 关键要点 |
|---|---|---|
| `README.md`（顶层，7 行） | **Dummy 自己写的**构建备忘：`make build`，然后 `esputil mkhex 0x8000 partition-table.bin 0x1000 bootloader.bin 0x100000 mongoose-esp32-example.bin > bridge.hex`，再 `esputil -fspi 6,17,8,11,16 -p /dev/cu.usbserial-0001 flash bridge.hex`。末尾给出参考链接 `https://mongoose.ws/documentation/tutorials/uart-bridge/` | **这一行链接就是整个模块的身份证**：它是 mongoose 的 uart-bridge 教程 |
| `tool/esputil.zip` | **0 字节空文件**（占位，内容未入库） | — |
| `firmware/hex/dummy-iot.hex` | **0 字节空文件**（占位） | 真正的固件在 `firmware/examples/esp32/uart-bridge/dummy-iot.hex`（2.5 MB，真实内容） |
| `firmware/mongoose.c` / `mongoose.h` | mongoose 合并版单文件库（上游） | — |
| `firmware/src/` | mongoose 未合并源码：`net.c`、`http.c`、`ws.c`、`mqtt.c`、`sntp.c`、`dns.c`、`json.c/h`、`rpc.c`、`tls_*.c`、`ota_*.c`、`fs_*.c`、`arch_*.h`、`device_stm32*.c`、`net_builtin.c`、`drivers/` 等。**`Makefile` 的 `mongoose.c:` 目标就是把 `src/*.c` 拼成 `mongoose.c`。** | **全部是上游代码，不含任何 Dummy 逻辑**（`grep -ri "dummy-robot\|DummyStudio" src/` 零命中；命中的 "dummy" 只是 mongoose 自己的 `device_dummy.c`/`tls_dummy.c`/`ota_dummy.c` 空实现） |
| `firmware/test/`、`firmware/Makefile`、`firmware/.vscode/`、`firmware/LICENSE`、`firmware/README.md` | mongoose 上游的测试、构建、编辑器配置、GPLv2/商业双许可说明 | — |
| `firmware/examples/`（**3241 个文件**，占本目录绝大部分体积） | mongoose 上游自带的示例工程集：`stm32/`（nucleo-f429zi/f746zg/h723zg/h743zi… 裸机与 CubeIDE 工程）、`nxp/`、`ti/`、`infineon/`、`microchip/`、`rp2040/`、`arduino/`、`zephyr/`、`esp8266/` 以及一大堆纯 PC 示例（`http-server`、`mqtt-*`、`device-dashboard`、`video-stream`…）。**与 Dummy 完全无关，不要逐个展开。** | 例外见下两行 |
| `firmware/examples/uart-bridge/` | 通用（PC/裸机）版 UART↔网络桥。`net.c` 是**核心业务逻辑且被 Dummy 改过**（见下）；`web_root/`（`index.html` + `main.js` + `preact.min.js` + `style.css`）是网页控制台；`packed_fs.c` 是 web_root 打包进 flash 的产物；`config.json` 是默认配置 | 改动点：`s_state` 默认 `.tx=26, .rx=27, .baud=115200`；MQTT 默认 topic `dummy/tx`/`dummy/rx`；`uart_write()` 里**若缓冲区末尾没有 `\n` 就补一个** |
| `firmware/examples/esp32/uart-bridge/` | **真正属于 Dummy 的 ESP32 工程**（ESP-IDF，`idf.py` 构建，Docker `espressif/idf`） | 见下表 |
| `firmware/examples/esp32/device-dashboard/` | mongoose 上游的另一个 ESP32 示例，**未被使用** | — |

#### `firmware/examples/esp32/uart-bridge/` 逐文件

| 文件 | 作用 | 关键要点 |
|---|---|---|
| `main/main.h` | 公共头 | `FS_ROOT "/spiffs"`、`WIFI_FILE "/spiffs/wifi.json"`、`UART_NO 1`；声明 `uart_bridge_fn`/`uart_read`/`wifi_init`/`cli`/`cli_init` |
| `main/main.c` | `app_main()`：挂载 SPIFFS → 读 `/spiffs/wifi.json` 里的 `$.ssid`/`$.pass` 连 WiFi（失败就死循环重试）→ 没有配置则进串口 CLI 等配置 → 连上后 `mg_http_listen("http://0.0.0.0:80", uart_bridge_fn)` + `mg_mgr_poll` 事件循环。`config_read/write` 读写 `/spiffs/config.json` | **顶部注释 `//gpio27 RX` `//gpio26 TX` 是 Dummy 的硬件接线记录** |
| `main/uart.c` | ESP-IDF UART 驱动封装 | `uart_open(no,rx,tx,cts,rts,baud)`（8N1，无流控）、`uart_init(tx,rx,baud)` 用 `UART_NO=1`、`uart_read()`、`uart_write()`。**`uart_write()` 里若数据中无 `\n` 则额外写一个 `\n`** → 专门为主控的「行式 ASCII 协议」做的适配 |
| `main/wifi.c` | 从 ESP-IDF wifi station 示例改来；STA 模式，WPA2-PSK，失败重试 3 次 | `wifi_init(ssid, pass)`。**注意：L96 连接失败时会把明文密码打进日志**（`MG_ERROR(("Failed to connect to SSID:%s, password:%s", ssid, pass))`）—— 是信息泄露隐患，但**不是硬编码凭据**，SSID/密码由用户在 CLI 里现场输入并存到 SPIFFS |
| `main/cli.c` | 串口 CLI（首次配网用） | `cli(uint8_t)` 逐字节累积到 `\n` 后 `sscanf("%9s %49s %249[^\r\n]")` 解析；命令：`wifi <SSID> <PASS>`（连通后写 `wifi.json`）、`ls`、`cat <f>`、`rm <f>`、`ll <level>`（设日志等级）、`reboot` |
| `main/net.c`/`mongoose.c`/`mongoose.h`/`packed_fs.c` | **都是只含一行相对路径的"软链接文本"**（如 `net.c` 内容就是字符串 `../../../uart-bridge/net.c`），ESP-IDF 构建时按路径取上一级的真文件 | 所以**读 `esp32/uart-bridge/main/net.c` 读不到代码，要去 `examples/uart-bridge/net.c`** |
| `CMakeLists.txt` / `main/CMakeLists.txt` | ESP-IDF 工程定义，工程名 `mongoose-esp32-example`；编译宏 `MG_ENABLE_LINES=1`、`MG_ENABLE_PACKED_FS=1`、`UART_API_IMPLEMENTED=1`（后者让 `net.c` 用 `uart.c` 的真实现而非 stdin/stdout 的 dummy 实现） | — |
| `Makefile` | Docker 包装：`docker run espressif/idf idf.py build/flash`；`bridge.hex` 目标用 `esputil mkhex` 拼三段镜像；`flash2` 用 `esputil -b 921600 -fp 0x220` 烧写并 monitor | — |
| `sdkconfig` / `sdkconfig.defaults` / `partitions.csv` | IDF 配置与分区表 | — |
| `dummy-iot.hex` / `bridge.hex` | **两个 2 571 116 字节、内容相同的预编译固件镜像**（2023-12-26）。`dummy-iot.hex` 就是 `bridge.hex` 改名 | 这是「Dummy IoT 模块」的成品固件 |
| `esputil` | 预编译的 ESP32 烧写工具二进制（24 KB） | 对应顶层 README 里的 `esputil` 命令 |
| `make` | **0 字节空文件**（误 commit） | — |
| `README.md` | mongoose 上游的 uart-bridge 烧写说明（指向 mongoose.ws 下载），**没改** | — |

#### 这个 ESP32 模块到底起什么作用

`firmware/examples/uart-bridge/net.c` 是全部逻辑（244 行，Cesanta 版权 + Dummy 改默认值）：

- ESP32 连上 WiFi 后同时提供 **4 条通道**，全部与同一个 UART 双向透传：
  - **HTTP:80** —— 网页控制面板（`web_root/`，preact 写的 dashboard，截图在 `examples/uart-bridge/screenshots/dashboard.png`）。API：`GET /api/hi`（探活）、`GET /api/config/get`、`POST /api/config/set`（改 tcp/ws/mqtt 的 url 与 enable、rx/tx 引脚、baud，落盘 `/spiffs/config.json`）。
  - **TCP:4001**（`DEFAULT_TCP "tcp://0.0.0.0:4001"`，默认 enable）—— 裸 TCP 透传，最适合上位机脚本直连。
  - **WebSocket:4002**（`DEFAULT_WEBSOCKET "ws://0.0.0.0:4002"`，默认 enable）—— 网页控制台用。
  - **MQTT**（`DEFAULT_MQTT "mqtt://broker.hivemq.com:1883?tx=dummy/tx&rx=dummy/rx"`，**代码里默认 disable**，但 `examples/uart-bridge/config.json` 里写成 `"enable":true`）—— 订阅 `dummy/rx` 收命令、发布 `dummy/tx` 回数据，经公共 broker 走公网。
- `timer_fn()` 每 20 ms 轮询 UART，把读到的字节扇出给所有已连接的 WS/TCP/MQTT 客户端。
- **结论：它是一个「WiFi 远程控制 + 网页控制面板」二合一的透明串口桥，自己不认识任何机械臂命令**。它把网络侧收到的文本原样喂给 UART（并保证以 `\n` 结尾），所以**网络侧说的就是主控的 ASCII 行协议**：从手机浏览器往 WS 里敲 `>0,0,0,0,0,0,30` 就等于往主控串口敲同一行。

#### 是否真的被用上了

证据两面：

**支持"做成了"**：
- 有 2.5 MB 的预编译固件 `dummy-iot.hex`（2023-12-26），命名明确是 Dummy 的 IoT 固件，且有配套 `esputil` 和顶层 README 的烧写命令 —— 说明至少烧过、跑过。
- Dummy 的改动是**有针对性的**，不是随手改：引脚默认值 TX=26/RX=27 与 `main.c` 注释一致；波特率 115200 与主控 `dummy-ref-core-fw/Core/Src/usart.c` 里 `huart4.Init.BaudRate = 115200` 一致；MQTT topic 改成 `dummy/tx`/`dummy/rx`；`uart_write()` 补 `\n` 正是为了配合主控 `OnUart4AsciiCmd` 的行解析。接口对得上 → 它接的是主控的 **UART4**（即 `ascii_protocol.cpp` 的第二条 ASCII 通道）。

**支持"是个半成品/边缘实验"**：
- 整个目录没有自己的工程说明，顶层 README 只有 7 行构建备忘，**没有任何接线图、使用说明、IP/端口文档**。
- `tool/esputil.zip`、`firmware/hex/dummy-iot.hex`、`esp32/uart-bridge/make` 三个文件都是 **0 字节占位**，说明入库很草率。
- web_root 的 dashboard 是 **mongoose 原版 UI，一点没为 Dummy 定制**（没有关节滑块、没有 MoveJ 按钮，只是个通用串口终端 + 配置页）。
- 其他上位机工具（`simple-cli`、`CLI-Tool`、`DummyStudio`）**全都只走 USB，没有一个支持 TCP/WS/MQTT 连这个桥**（`CLI-Tool` 的 fibre 虽然有 `tcp:`/`udp:` 传输，但 fibre 是二进制 RPC，与这个桥透传的 ASCII 协议不是一套，接不上）。
- 整个仓库其他地方 **零引用**：`grep -ri "esp32\|dummy-iot\|4001\|4002"` 在主控固件和上位机代码里都没有命中。
- 代码路径藏在 `firmware/examples/esp32/uart-bridge/` 里（而不是提成一个独立工程），且把整个 3241 文件的 mongoose 示例库一起 commit 了进来。

**综合判断：功能上是跑通了的（有成品 hex、改动与主控接口精确对齐），但它是一个独立的、文档缺失的旁支实验，没有被集成进 Dummy 的任何上位机工作流。** 要用只能手动烧 hex、串口 CLI 配网、然后自己写 socket 脚本或用原版网页终端打 ASCII 命令。

---

### 上位机 ↔ 固件 的通信协议对照

主控固件侧实现：`source/1.Dummy V2任同学整理/2.Firmware/dummy-ref-core-fw/UserApp/protocols/ascii_protocol.cpp`
运动命令的二次解析：`source/1.Dummy V2任同学整理/2.Firmware/dummy-ref-core-fw/Robot/instances/dummy_robot.cpp` → `DummyRobot::CommandHandler::ParseCommand()`（L426 起）

**传输层**：USB CDC 虚拟串口 115200 8N1（`OnUsbAsciiCmd`）；或 UART4 115200（`OnUart4AsciiCmd`，ESP32 桥接的就是这条）。**每条命令一行，以 `\n` 结尾**，首字符决定分类。

#### 首字符分类

| 前缀 | 含义 | 处理路径 |
|---|---|---|
| `!` | 立即执行的系统命令（用 `s.find()` 子串匹配，不做严格解析） | `ascii_protocol.cpp` 直接调 `dummy.*` |
| `#` | 查询 / 参数设置（同样 `s.find()` 子串匹配） | 同上 |
| `>` `@` `&` | 运动命令，**先入队** `commandHandler.Push()`，回复剩余队列空位（一个数字），再由 `ParseCommand()` 消费 | `dummy_robot.cpp` |

#### 完整命令表（含上位机侧出处）

| 命令字符串（含 `\n`） | 语义 | 固件响应 | 哪个上位机发 |
|---|---|---|---|
| `!START` | 使能机械臂 `SetEnable(true)` | `Started ok` | `simple-cli.py:15`（`start` 命令，轮询到 `Started ok` 为止） |
| `!STOP` | 急停 `EmergencyStop()` | `Stopped ok` | 无（仅固件支持） |
| `!HOME` | 回零 `Homing()` | `Started ok` | 无 |
| `!RESET` | 回休息位 `Resting()` | `Started ok` | 无 |
| `!CALIBRATION` | 标定 home offset | `calibration ok` | 无 |
| `!DISABLE` | 下使能 `SetEnable(false)` | `Disabled ok` | `simple-cli.py:42`（`stop` 命令，轮询到含 `ok`） |
| `#GETJPOS` | 读 6 个关节角 | `ok %.2f ×6`（`currentJoints`） | 无（`DummyStudio` 可能在用，未确证） |
| `#GETLPOS` | 读末端 6D 位姿 | `ok %.2f ×6`（`currentPose6D` X,Y,Z,A,B,C） | 无（同上） |
| `#SET_DCE_KP <node> <kp>` | 设节点位置环 Kp，node∈[1,6] | `ok SET MOTOR [n] DCE_KP [v]` / `error ... is wrong` | `simple-cli.py:53`（`kp <node> <v>`） |
| `#SET_DCE_KI <node> <ki>` | 设 Ki | `ok SET MOTOR [n] DCE_KI [v]` | `simple-cli.py:60`（`ki`） |
| `#SET_DCE_KD <node> <kd>` | 设 Kd | `ok SET MOTOR [n] DCE_KD [v]` | `simple-cli.py:67`（`kd`） |
| `#REBOOT <node>` | 重启节点让参数生效 | `ok REBOOT MOTOR [n]` | `simple-cli.py:74`（`reboot <node>`） |
| `#CMDMODE <mode>` | 切运动命令模式 | `ok Set command mode to [m]` | 无 |
| **任何其他 `#...`** | **落到 else 分支** | 裸 `ok`（无数据） | ⚠️ `chatgpt_gui.py:48` 的 `#GETMPU` 就落在这里 → 该 GUI 永远拿不到数据 |
| `>j1,j2,j3,j4,j5,j6` | MoveJ（关节空间），逗号分隔 6 个 float，**无空格** | 入队时回队列空位数；执行完回 `ok` | 推测是 `DummyStudio` 的主力命令（未确证） |
| `>j1,...,j6,speed` | MoveJ 并先 `SetJointSpeed(speed)`（7 参数形式） | 同上 | 同上 |
| `&j1,...,j6[,speed]` | 与 `>` **解析完全相同**的 MoveJ（第二个入口，用于区分来源/优先级） | 同上 | — |
| `@x,y,z,a,b,c[,speed]` | MoveL（笛卡尔空间），x/y/z 位置 + a/b/c 姿态 | 同上 | — |

**解析细节（容易踩坑）**：
- `>`/`&`/`@` 用 `sscanf(">%f,%f,%f,%f,%f,%f,%f", ...)`，靠返回值区分 6 参数还是 7 参数；**分隔符必须是逗号，前缀后不能有空格**。
- `COMMAND_TARGET_POINT_SEQUENTIAL` / `COMMAND_CONTINUES_TRAJECTORY` 模式下，`>`/`&` 会**阻塞等待运动完成**（`while (IsMoving() && IsEnabled()) osDelay(5)`）后才回 `ok`；`COMMAND_TARGET_POINT_INTERRUPTABLE` 模式下立刻回 `ok`（可被下一条打断）。**写上位机时这个差异决定要不要等 `ok`。**
- `!` 和 `#` 走 `std::string::find()` **子串**匹配，所以 `!DOSTART` 也会被当成 `!START`；前缀后可以有任意前后缀垃圾字符。
- UART4 通道（`OnUart4AsciiCmd`，ESP32 桥接的那条）**只实现了 `!*`、`#GETJPOS`、`#GETLPOS`、`#CMDMODE` 和 `>`/`@`/`&`**，**不支持 `#SET_DCE_K*` 和 `#REBOOT`** —— 也就是说**不能通过 ESP32 远程调 PID**。另外该分支的条件是 `if (_cmd[0] == '!' || !dummy.IsEnabled())`，未使能时所有命令都会掉进 `!` 分支。
- `Respond()` 的输出不带统一帧尾，上位机按行读即可。

#### 另一套并行接口：fibre 二进制 RPC

与上面的 ASCII 协议**互不相干**，供 `CLI-Tool` 使用。定义在 `dummy-ref-core-fw/UserApp/protocols/cmd_protocol.cpp`（`MakeObjTree()`）与 `Robot/instances/dummy_robot.h`、`Robot/actuators/ctrl_step/ctrl_step.hpp`。调用形如 `dummy0.robot.move_j(0,0,0,0,0,0)`，走 USB bulk 端点（同一物理设备的另一个 USB 接口）。分流逻辑在 `Bsp/communication/ascii_processor.cpp` / `communication.cpp` / `interface_usb.cpp`。

---

### 可回答的典型问题 → 去哪个文件

| 问题 | 去哪里 |
|---|---|
| 上位机到底怎么下发一条 MoveJ？格式长什么样？ | 先看本节的协议对照表；固件侧 `2.Firmware/dummy-ref-core-fw/Robot/instances/dummy_robot.cpp` L426+ `ParseCommand()`；分类在 `2.Firmware/dummy-ref-core-fw/UserApp/protocols/ascii_protocol.cpp` L104+ |
| ASCII 命令一共有哪些？`!`/`#`/`>`/`@`/`&` 分别干什么？ | `2.Firmware/dummy-ref-core-fw/UserApp/protocols/ascii_protocol.cpp`（USB 通道 L1-112，UART4 通道 L114+） |
| 怎么在线调关节电机的 PID？用哪个工具、哪条命令？ | `3.Software/simple-cli/simple-cli.py`（`kp/ki/kd/reboot`）+ `3.Software/simple-cli/README.md`；注意 UART4 不支持这些命令 |
| 为什么 `#GETMPU` 没反应 / `chatgpt_gui.py` 是干什么的？ | `3.Software/simple-cli/chatgpt_gui.py`（实为 MPU6050 绘图 GUI）；对照 `ascii_protocol.cpp` 的 `#` 分支——`GETMPU` 未实现，落到 else 回裸 `ok` |
| 有没有用 LLM/ChatGPT 控制机械臂的代码？ | **没有。** 唯一看起来像的 `3.Software/simple-cli/chatgpt_gui.py` 与 LLM 无关，全仓库无任何 LLM API 调用 |
| 怎么进那个能 `dummy0.robot.move_j(...)` 的 Python 交互 shell？ | 入口 `3.Software/CLI-Tool/run_shell.py`（或 Windows 的 `run.bat`）；shell 实现 `3.Software/CLI-Tool/ref_tool/shell.py` + `3.Software/CLI-Tool/fibre/shell.py`；最小示例 `3.Software/CLI-Tool/_addition/ref_demo.py` |
| shell 里能访问哪些属性和函数（对象树）？ | 固件端定义：`2.Firmware/dummy-ref-core-fw/UserApp/protocols/cmd_protocol.cpp`（根，含 `robot`）、`Robot/instances/dummy_robot.h`（`move_j`/`move_l`/`hand`/`joint_N`）、`Robot/actuators/ctrl_step/ctrl_step.hpp`（单电机的 `angle`/`set_position`/`set_dce_*` 等） |
| CLI-Tool 是怎么连设备的？为什么 Windows 要跑 zadig？ | `3.Software/CLI-Tool/fibre/usbbulk_transport.py`（pyusb/libusb + `WELL_KNOWN_VID_PID_PAIRS`）、`fibre/discovery.py`（`--path` 的 `usb`/`serial`/`tcp`/`udp` 分发）；`zadig-2.5.exe` 用来把接口驱动换成 WinUSB；Linux 免 sudo 用 `ref_tool/version.py:setup_udev_rules()` |
| 设备的 USB VID/PID 是多少？ | `2.Firmware/dummy-ref-core-fw/USB_DEVICE/App/usbd_desc.c`（`0x1209` / `0x0D32`）；上位机侧 `3.Software/CLI-Tool/fibre/usbbulk_transport.py` L15-19、`3.Software/DummyStudio/DummyStudio_Data/StreamingAssets/serial_config.txt` |
| 怎么备份/恢复机械臂配置？怎么画实时曲线？ | `3.Software/CLI-Tool/ref_tool/configuration.py`（`backup_config`/`restore_config`）、`3.Software/CLI-Tool/ref_tool/utils.py`（`start_liveplotter`、`rate_test`、`print_drv_regs`）；入口参数在 `run_shell.py` |
| DummyStudio 能不能改？源码在哪？ | **不能改，无源码。** 只有 `3.Software/DummyStudio/` 下的 Unity 编译产物；业务逻辑全在 `DummyStudio_Data/Managed/Assembly-CSharp.dll`，需 ILSpy/dnSpy 反编译 |
| DummyStudio 怎么改串口/波特率？连不上怎么办？ | `3.Software/DummyStudio/DummyStudio_Data/StreamingAssets/serial_config.txt`（`VendorID=1209` / `BaudRate=115200`，明文可改，按 VID 自动枚举） |
| DummyStudio 用久了就不动了 / 传输变慢？ | 它用的 SerialPort Utility Pro 是 FREE 版，单次运行累计传输上限 1 MB，需重启程序；证据在 `Assembly-CSharp.dll` 的字符串里 |
| DummyStudio 到底是示教、还是轨迹录制？ | 推断是**实时拖拽 gizmo 让末端跟随**的可视化遥操作（符号 `DummyRobotBridge`/`DummyTargetTrack`/`OnRobotJointsChanged` + Runtime Transform Gizmos 资产），**未发现任何轨迹录制/回放符号**；作者信息在 `DummyStudio_Data/app.info` |
| ESP32 模块是干什么的？提供哪些端口？ | 逻辑全在 `2.Firmware/esp32-iot/firmware/examples/uart-bridge/net.c`（HTTP:80 / TCP:4001 / WS:4002 / MQTT `dummy/tx`,`dummy/rx`）；网页 UI 在同目录 `web_root/` |
| ESP32 怎么配网 / 怎么烧固件？ | 配网：`2.Firmware/esp32-iot/firmware/examples/esp32/uart-bridge/main/cli.c`（串口敲 `wifi <SSID> <PASS>`）；烧写：`2.Firmware/esp32-iot/README.md` + 同目录 `Makefile`，固件 `dummy-iot.hex`/`bridge.hex`，工具 `esputil` |
| ESP32 接在主控哪几个脚上？波特率多少？ | `2.Firmware/esp32-iot/firmware/examples/esp32/uart-bridge/main/main.c` 顶部注释（GPIO26=TX / GPIO27=RX）+ `main/uart.c`（UART1）+ `examples/uart-bridge/net.c` 的 `s_state` 默认值（115200）；主控侧对应 UART4，`2.Firmware/dummy-ref-core-fw/Core/Src/usart.c:47` |
| `esp32-iot/firmware/examples/stm32/...` 那几千个文件要看吗？ | **不用。** 全是 mongoose 上游自带示例，与 Dummy 无关。Dummy 只改了 `examples/uart-bridge/net.c` 和新增 `examples/esp32/uart-bridge/main/{main,uart,cli}.c` |
| 为什么 `esp32/uart-bridge/main/net.c` 打开只有一行路径？ | 那几个文件是「软链接文本」（内容就是相对路径字符串），真代码在 `2.Firmware/esp32-iot/firmware/examples/uart-bridge/net.c` 和 `firmware/mongoose.c` |
| 项目里有硬编码的 API key / 密码吗？ | **没有发现任何硬编码凭据。** 唯一需要留意的是 `2.Firmware/esp32-iot/firmware/examples/esp32/uart-bridge/main/wifi.c` L96 会把用户输入的 WiFi 明文密码打进串口日志（泄露隐患，非硬编码） |

---

## 十一、学习资料与调研产出(非 Dummy 本体)

这两块都**不是 Dummy 机器人本体代码**,而是用户为补 STM32/嵌入式基础而收集的视频字幕语料,以及一次 B 站学习路线调研的工作区。改 Dummy 固件/上位机时不需要读这里;要查某个知识点、或想知道"该先学什么"时才来。

### 嵌入式学习/

共 191 个文件,4 门课程的 B 站视频字幕。全部是**纯文本语料**(md + srt),无代码、无工程。

| 路径 | 内容 | 体积 |
|---|---|---|
| `嵌入式学习/STM32课程字幕_P04-P49_合并版.md` | **江科大** STM32 入门教程(BV1th411z7sn)P04–P49 合并字幕 | 2.0 MB |
| `嵌入式学习/尚硅谷STM32字幕/STM32基础篇_字幕合并版.md` | 尚硅谷 STM32 **基础篇** P01–P194 | 3.3 MB |
| `嵌入式学习/尚硅谷STM32字幕/STM32高级篇_字幕合并版.md` | 尚硅谷 STM32 **高级篇+扩展篇** P01–P135 | 1.9 MB |
| `嵌入式学习/尚硅谷FreeRTOS教程字幕/FreeRTOS入门教程_校对版.md` | FreeRTOS 55 讲校对版(BV1vUpje9Ej2) | 1.4 MB 目录另含 55 个 srt |
| `嵌入式学习/尚硅谷PCB设计教程字幕/PCB设计教程_校对版.md` | 立创EDA PCB 设计 131 讲校对版(BV1AT421Y7DS) | 971 KB,srt 1.7 MB |

#### 校对版 .md 与 原始字幕srt/ 的关系

- **`*_校对版.md` / `*_合并版.md`**:由 srt 合并而来,一个 `## P0xx 标题` 一讲,正文是 ``` `00:00:00` 口播 ``` 的逐行(或逐段)文本。**检索内容用这个**——单文件 grep 即可跨全课搜关键词,且命中行自带时间戳。
- **`原始字幕srt/`**:yt-dlp 抓下的 `ai-zh` 原始轨,保留标准 srt 的起止时间区间。**要精确定位视频播放位置、或怀疑合并版有丢行时**回查这里。内容与校对版等价,属可再生中间产物。
- 两边都是 AI 自动字幕,术语常被误识别(如 "STM32"→"sm 32"、"I2C"→"IPHONEC"、"51 单片机"→"五一单片机")。**引用前务必按上下文校正,不要把字幕当权威资料**;芯片细节一律回查官方手册。

#### 尚硅谷STM32字幕/ 的讲次分组(本次新整理)

该目录**只有 2 个合并版 md,没有 srt 子目录**。两个 md 的 `## Pxx 章节_小节` 标题自带完整讲次名,因此可直接按 heading 定位。段落以 `**[HH:MM:SS]**` 标注起始时间。课程特点:**几乎每个案例都讲两遍——先"寄存器方式",再"HAL 库方式"**。

**基础篇(P01–P194)**

| 讲次 | 主题 |
|---|---|
| P01–P08 | 课程/ARM 内核/STM32 简介、命名规范、开发方式、Keil MDK 安装 |
| P09–P11 | 开发板原理图、STM32 最小系统、快速验证 |
| P12–P18 | 点灯案例:工程创建、编译配置、寄存器实现 + 三轮优化(宏定义/位运算/位宏) |
| P19–P28 | **GPIO**:概述、推挽/开漏/复用/输入模式、寄存器、流水灯与往返流水灯 |
| P29–P31 | **系统架构与时钟系统**、各时钟用途总结 |
| P32–P38 | **HAL 库**:简介、CubeMX 安装、HAL 工程创建、系统时钟配置源码解析 |
| P39–P53 | **中断系统**:基本概念、NVIC、优先级底层原理、EXTI 原理与寄存器、按键中断案例(寄存器/HAL) |
| P54–P76 | **USART**:串/并行、单工半双工全双工、同步异步、通讯协议、功能框图、波特率设置、收发案例(寄存器轮询/寄存器中断/HAL 轮询/HAL 中断)、Keil 断点调试、printf 重定向 |
| P77–P97 | **I2C**:底层协议、软件模拟 I2C 读写 M24C02 EEPROM(时序图→单字节→多字节)、STM32 I2C 外设原理框图与寄存器、硬件 I2C(寄存器/HAL) |
| P98–P100 | 综合案例:串口下发花式流水灯方案 |
| P101–P138 | **定时器**:整体介绍、SysTick 嘀嗒定时器+延时工具类、基本定时器、通用定时器(计数模式/PWM/输出比较/输入捕获/从模式/PWM 输入模式)、测周期、测占空比、高级定时器、呼吸灯与 LCD 背光调节练习 |
| P139–P145 | **DMA**:原理框图、寄存器、ROM→RAM 与 RAM→串口两个案例 |
| P146–P155 | **ADC**:基本参数、逐次逼近原理、外设工作原理、寄存器、单通道/多通道转换 |
| P156–P165 | **SPI**:通信介绍、W25Q32、软件模拟读写 Flash、SPI 外设与寄存器、硬件实现 |
| P166–P170 | **存储器与寄存器**:分类、STM32 存储器映射、寄存器本质与地址映射 |
| P171–P178 | **FSMC**:原理、外部设备地址映射、读写时序、扩展 SRAM(IS62WV51216) |
| P179–P194 | **LCD**:接口类型、液晶控制器、FSMC 控制 LCD(寻址/配置/读 ID/背景色/英文字符/字符串/汉字/图片/画点线矩形/画圆) |

**高级篇 + 扩展篇(P01–P135)**

| 讲次 | 主题 |
|---|---|
| P01 | 高级篇整体介绍(五章均为"物联网通信之 X") |
| P02–P29 | **CAN 总线**:产生背景、物理层、协议层(报文类型/数据帧远程帧/总线仲裁/位时序/位填充)、STM32 CAN 外设(三种工作模式+三种测试模式/功能框图/过滤器/位时序)、案例一环回静默模式(寄存器+HAL)、案例二双机收发 |
| P30–P48 | **以太网**:底层原理、OSI 七层、常见协议、W5500 芯片与官方库移植、TCP 服务端/客户端、UDP、简易 Web 服务器 |
| P49–P67 | **Wi-Fi**:802.11 标准、频段信道、ESP32-C3 模块与 AT 固件烧录、AT 指令测试、TCP 通讯完整案例 |
| P68–P79 | **蓝牙**:发展历程、协议栈、BLE 协议栈/角色/地址、广播扫描、透传模式案例 |
| P80–P95 | **LoRa**:低功耗广域网、组网架构、关键参数、LLCC68 芯片、官方库移植、普通节点 + 网关节点双向收发 |
| P96 | 扩展篇整体介绍 |
| P97–P111 | **电源控制**:框图、上电/掉电复位、PVD、三种低功耗模式(睡眠/停机/待机,每种寄存器+HAL 两套) |
| P112–P127 | **RTC / BKP**:RTC 功能框图、备份寄存器、BKP 案例、闹钟唤醒待机模式、实时时钟(含 LCD 显示) |
| P128–P133 | **看门狗**:独立看门狗 IWDG、窗口看门狗 WWDG、IWDG 唤醒待机 |
| P134–P135 | 附录:HAL 代码分析、Keil 编译过程与内存映像 |

#### STM32课程字幕_P04-P49_合并版.md 的结构

- 另一门课(**江科大 STM32 入门教程 2023 版**),与尚硅谷那两篇内容重叠但风格不同,更精简。
- 层级:`#` 文档标题 → `## 2-2 新建工程` 等 **46 个二级标题**(按"章-节"编号,不是 Pxx)。每节开头给出该分 P 的 B 站链接 `https://www.bilibili.com/video/BV1th411z7sn?p=N`。
- 正文**逐行带时间戳**,格式 `` `00:00:02.060` 文本 ``(毫秒精度)。
- 章节脉络:2-2 新建工程 → 3-x GPIO 输入输出 → 4-x OLED → 5-x EXTI → 6-x TIM(定时中断/输出比较/PWM/输入捕获/编码器接口) → 7-x ADC → 8-x DMA → 9-x USART → 10-x I2C+MPU6050 → 11-x SPI+W25Q64 → 12-x BKP/RTC → 13-x PWR → 14-x WDG → 15-x FLASH。P01–P03 未收录。

#### FreeRTOS 课程讲次简表(55 讲,BV1vUpje9Ej2)

| 讲次 | 主题 |
|---|---|
| P01–P03 | 课程介绍、裸机 vs 操作系统、FreeRTOS 简介 |
| P04–P10 | 内核原理:多任务与调度策略、任务状态、RTOS 滴答时钟、上下文切换时机、空闲任务 |
| P11–P16 | 移植:源码结构、HAL 库工程移植、HAL 与 RTOS 时钟源冲突、寄存器方式移植差异、系统配置文件、数据类型与命名规范 |
| P17–P20 | 任务创建与删除:API 与 TCB、动态方式、静态方式 |
| P21–P22 | 任务挂起与恢复 |
| P23–P24 | 中断管理 + 临界段原理 + 挂起调度器对比,编码演示 |
| P25 | 时间片调度 |
| P26–P28 | 任务实用函数:状态查询、运行时间统计 |
| P29–P30 | 时间管理:两种时间函数 |
| P31–P32 | 消息队列 |
| P33–P40 | 信号量:二值、计数型、优先级翻转问题与模拟、互斥信号量 |
| P41–P42 | 队列集 |
| P43–P44 | 事件标志组 |
| P45–P49 | 任务通知:简介、模拟信号量/消息队列/事件标志组、任务通知数组 |
| P50–P51 | 软件定时器 |
| P52–P53 | 低功耗模式 |
| P54–P55 | 内存管理:五种内存算法、分配与释放 |

#### PCB 设计课程讲次简表(131 讲,BV1AT421Y7DS,立创EDA)

**注意**:该课 srt 文件名和校对版标题都是 `P0xx NA`(无标题),定位只能靠下面这张表。

| 讲次 | 主题 |
|---|---|
| P001–P008 | 基础:PCB 发展史与工艺、双层板结构、元器件封装、设计到打样流程、EDA 软件对比、立创EDA 版本/界面/设置 |
| P009–P020 | **入门板**(纽扣电池点亮 LED):选型→原理图→DRC→导入 PCB→2D/3D→布线→板框→DRC→下单→元件采购 |
| P021–P048 | **进阶板**(74HC138 译码 + 74HC245 放大):74HC 系列、138 引脚与电路、自锁开关、排针、交叉选择、布局、布线原则(从电源起、禁直角)、铺铜、泪滴、丝印、USB 供电、数据手册精读、高低电平电压范围 |
| P049–P079 | **实战板原理图**(STC89C52RC 51 核心板):模块规划、Type-C 母座与充电协议、贴片选型、自恢复保险丝、电容滤波、5V→3.3V、电源开关、MCU 最小系统(单片机/晶振/复位)、供电指示灯、CH340N 下载模块、通信指示灯、P0 上拉排阻与开漏原理、自动冷启动电路(P 沟道 MOS/振铃效应/米勒效应/栅极 10Ω)、图纸美化、DRC |
| P080–P114 | **实战板 PCB**:板框尺寸、排针定位、模块布局、位号丝印、晶振禁铜、布线(电源/USB 差分/P0–P4 四组端口/复位/晶振)、功耗实测、丝印、铜箔 logo、泪滴、铺铜、缝合孔、DRC |
| P115–P121 | **三版实物迭代**:CH340N 经 RXD/TXD 向 MCU 倒灌电问题及修复、排针电源网络修正、电源走线优化对比 |
| P122–P131 | 附录工程技巧:元件库管理(系统库/工程库/个人库)、自制贴片电阻+0603 封装、封装绑定解绑、从数据手册从零制作 CH340N 元件与封装、修改默认图纸模板 logo |

### workspace/

一次 **B 站 STM32/嵌入式学习路线调研**的工作区,用 `video-understanding` 技能在 **2026-09-21** 单日完成。原共 173 个文件 / 2.8 GB,其中 2.75 GB 是视频。**2026-10-08 已清理 mp4 与切片缓存,现仅 3.6 MB**,保留了字幕与元数据。核心价值在 `deliverables/` 的 6 个文本文件(80 KB)。

| 路径 | 内容 |
|---|---|
| `workspace/stm32-roadmap-research/bilibili-discovery/` | **发现阶段**(292 KB,7 个文件)。`metadata/mediacrawler/<时间戳>/` 下是 MediaCrawler 抓的 `search_contents_*.jsonl` / `search_creators_*.jsonl` 原始搜索结果,外加 `search-plan.json`(关键词计划)。`gemini/` `videos/` `deliverables/` 三个子目录为空。 |
| `workspace/stm32-roadmap-video-evidence/` | **取证阶段**(2.8 GB)。 |
| └ `urls.txt` | 待下载队列(仅剩 3 行,大部分已消费) |
| └ `downloaded.txt` | 已下载清单,31 行,格式 `bilibili <BVID>`;技能据此做断点续传/去重 |
| └ `.video-understanding-workspace.json` | 工作区标记文件 `{"type":"video-understanding-workspace","version":1,"created_at":"2026-09-21T05:34:18Z"}`,技能靠它识别目录归属与清理范围 |
| └ `videos/` | **现 3.2 MB**,31 个分 P 目录(`BV1ptpFzCEix`、`BV19qKizsEw4_p4` …)。`source.mp4` 与 `source.jpg` **已于 2026-10-08 删除**;保留 `source.info.json` + `source.description`(各 31),及 `source.ai-zh.srt`(24,**报告 T 类证据的来源**) |
| └ `gemini/` | **已于 2026-10-08 删除 `chunks/`**(原 145 MB 切片缓存),目录现为空。**从来没有任何 Gemini 分析结果**——API 返 HTTP 402(账户预付额度耗尽),分析未完成,故所有结论仅基于本地字幕与 B 站元数据 |
| └ `deliverables/` | **最终产出,80 KB,6 个文件** |

#### deliverables/ 产出与结论

| 文件 | 作用 |
|---|---|
| `search-plan.md` | 检索方案:6 个固定主题(STM32 学习路线 / 嵌入式学习路线 / STM32 项目教程 / 无刷电机 FOC / CAN 总线教程 / FreeRTOS STM32)+ 允许的同义词,以及"下载前 A 候选"表(BVID、UP 主、初筛依据) |
| `a-candidate-urls-20260921.txt` | 通过初筛的 A 类候选 URL |
| `supplemental-page-urls-20260921.txt` | 6 条补充分 P 链接(BV15b4y1Z7Tk p2/p3、BV19qKizsEw4 p4/p10、BV19TSjB4EhV p2/p3) |
| `bilibili-stm32-roadmap-review-20260921.md` | **B 站审查报告(20.7 KB)**:20 个去重 A 条目白名单,每条带评分(1–5)、Dummy V2 阶段映射、≥2 条 `HH:MM:SS.mmm` 证据、商业导流筛选结论 |
| `zhihu-stm32-roadmap-review-20260921.md` | 知乎侧审查报告(16.6 KB),13 篇 A 类回答 |
| `zhihu-bilibili-synthesis-20260921.md` | **跨平台综合报告(13 KB),整个调研的最终结论,先读这个** |

**调研主题**:为 Dummy V2 复刻(E0–E13 阶段)确定"该怎么学 STM32、学到什么程度、用哪些材料"。

**核心结论**(摘自综合报告):
1. 既不"先学完再做",也不"不学基础直接抄项目",而是**以有边界的小项目为主线,按阻塞点补知识**。
2. **HAL / LL / 寄存器不是互斥路线**:工程层沿用项目现有抽象;理解和排障时下钻参考手册、寄存器、时钟树、中断状态。不为"追新"重写现有固件。
3. 独立开发 ≠ 不查资料。每个教程只允许完成一次"参考实现",之后必须做一次二次实现(空工程重建/换外设/加故障处理/加观测量)。
4. **FreeRTOS 和 Linux 不是前期门槛**:Motor-42 的传感器、校准、本地闭环、安全停机稳定后,才在 F405/REF 阶段引入 FreeRTOS(放到 E8);Linux/ROS/视觉属远期可选。
5. **B 站 FOC 视频只能迁移概念**(闭环、采样、PWM、电角度、坐标变换)。Dummy 的 Motor-42 用 MT6816 + TB67H450,是两相拓扑,**不能照搬三相桥、六步换相、相电流重构和引脚配置**。
6. **CAN 的验收标准不是"发出一帧"**,而是双向协议、节点寻址、心跳、超时、错误恢复和安全 STOP;只有发送演示不足以通过 E6。
7. 推荐优先级链:**Motor-42 单节点反馈与闭环 → UART/CAN → F405/FreeRTOS → 多轴 → (远期) Linux/ROS/视觉**。
8. 调试能力是核心产出:每阶段验收材料须含构建结果、串口日志/调试变量、输入条件、输出结果、失败现象、定位过程与恢复方法。没有观测证据的"能跑"不算完成。

**自述的证据局限**(报告第 9 节):AI 字幕会误识别 API/芯片术语;CAN 视频是 2020–2022 年材料,库 API 可能过时;播放量点赞不作技术正确性证明;**Gemini 提取未完成,报告未引用任何 Gemini 结论**。

### 可回答的典型问题 → 去哪里

| 问题 | 去哪里 |
|---|---|
| FreeRTOS 任务通知怎么用?能替代信号量/队列吗? | `尚硅谷FreeRTOS教程字幕/FreeRTOS入门教程_校对版.md` 的 P45–P49 段 |
| FreeRTOS 移植进 HAL 工程时,SysTick 时钟源该给谁? | 同上 P11–P16(尤其 P13 HAL 与 RTOS 时钟源问题) |
| 优先级翻转是什么?互斥信号量怎么解决? | 同上 P33–P40 |
| STM32 的 CAN 过滤器怎么配?双机收发怎么联调? | `尚硅谷STM32字幕/STM32高级篇_字幕合并版.md` P13、P21–P22、P27–P29 |
| STM32 定时器怎么输出 PWM / 做输入捕获测频率? | `尚硅谷STM32字幕/STM32基础篇_字幕合并版.md` P114–P118(PWM)、P121–P126(输入捕获);精简版见 `STM32课程字幕_P04-P49_合并版.md` 的 6-3 ~ 6-6 |
| 编码器接口模式怎么测速? | `STM32课程字幕_P04-P49_合并版.md` 的 `## 6-7` / `## 6-8` 两节 |
| 硬件 SPI 读写 Flash 的寄存器和 HAL 两种写法? | 基础篇 P162–P165(另 P156–P161 是软件模拟) |
| DMA 怎么把 ADC 多通道数据搬到内存? | 基础篇 P139–P145;或 `STM32课程字幕_P04-P49_合并版.md` 的 `## 8-2` |
| 低功耗停机/待机模式怎么进、怎么唤醒? | 高级篇 P97–P111(电源控制),唤醒配 RTC 闹钟见 P120–P122 |
| 画板子怎么布电源线?为什么不能走直角?怎么铺铜加泪滴? | `尚硅谷PCB设计教程字幕/PCB设计教程_校对版.md` P021–P048 段(布线原则 + 铺铜 + 泪滴) |
| CH340N 下载电路怎么画?为什么会向 MCU 倒灌电? | PCB 校对版 P049–P079(原理图)+ **P115–P121(三版实物踩坑与修复)** |
| 怎么从数据手册给一颗新芯片做元件库和封装? | PCB 校对版 P122–P131 |
| 我该先学 FreeRTOS 还是先搞定电机闭环? | `workspace/stm32-roadmap-video-evidence/deliverables/zhihu-bilibili-synthesis-20260921.md` 第 1、5 节 |
| 哪些 B 站视频值得看?评分和对应 Dummy 阶段? | `workspace/stm32-roadmap-video-evidence/deliverables/bilibili-stm32-roadmap-review-20260921.md` 第 3 节 A 类白名单 |
| 想定位某句口播在视频的第几分钟 | 用校对版 grep 到 `` `HH:MM:SS` `` 时间戳;需要精确起止区间再查对应课的 `原始字幕srt/` |

### 清理状态(2026-10-08 已执行)

`workspace/` 已从 **2.8 GB 降至 3.6 MB**。详细清理记录见「五、已知坑」F 节。

**已删除**:31 个 `source.mp4`(~2.6 GB)、31 个 `source.jpg` 封面(~11 MB)、`gemini/chunks/` 切片缓存(~145 MB)。

**已保留**:`deliverables/`(全部 6 个文本)、`videos/**/source.ai-zh.srt`(24 个,904 KB,**报告 `T` 类证据的来源,删了就无法核对引用**)、`videos/**/source.info.json` 与 `source.description`(各 31)、`downloaded.txt` / `urls.txt` / `.video-understanding-workspace.json`(重跑依据)、`stm32-roadmap-research/bilibili-discovery/metadata/`(jsonl 原始搜索结果,292 KB)。

如需复核报告里某条视频证据,字幕仍在;如需重看视频画面,按 `urls.txt` 的 BVID 重新下载。

`嵌入式学习/` 下的 `原始字幕srt/`(共 186 个文件,3.1 MB)严格说可由重新下载再生,但体积小且是校对版的核对依据,**不建议清理**。

> **已知小问题**:`尚硅谷STM32字幕/STM32基础篇_字幕合并版.md` 头部声明"修正规则和示例见同目录的 `字幕修正记录_*.md`",但该目录下只有两个合并版 md,**修正记录文件不存在**。基础篇/高级篇也**没有保留 srt 原始轨**(FreeRTOS 和 PCB 两门课有),所以这两篇无法回溯到原始时间区间,只能用段落级的 `**[HH:MM:SS]**` 标记。

---

## 十二、上游克隆 `source/dummy/`(Gitee auk 分支)

> **来源**:`git@gitee.com:switchpi/dummy.git`,2026-10-12 克隆(SSH)。
> **检出分支**:`auk`(上游默认分支),HEAD = `3a9d174`(2026-05-19)"move bbs open source files to here",共 54 个提交。
> **本机只保留 auk**:`master` / `fox` / `Fan-feature` 三个远程跟踪引用已删除,`gc --prune=now` 后 `.git` 从 501 MB 降到 43 MB。fetch refspec 已改为 `+refs/heads/auk:refs/remotes/origin/auk`,**以后 `git pull` 只拉 auk**。
> **体积**:工作区 180 MB / `.git` 43 MB / 3290 个文件。
>
> 要恢复其他分支(例如取 `Fan-feature` 的 step 模型):
> ```
> git config --unset-all remote.origin.fetch
> git config remote.origin.fetch '+refs/heads/*:refs/remotes/origin/*'
> git fetch origin
> ```

### 关于另外三个分支(已删,仅作认知记录)

| 分支 | 定位 | 最后更新 | 与 auk 的关系 |
|---|---|---|---|
| `master` | 原始基线 | 2023-11-16 | **是 auk 的祖先**,22 个提交全部包含在 auk 的 54 个里,历史没丢 |
| `fox` | **Dummy2,换代产品** | 2024-09-23 | 删掉整个 `firmware`/`hardware`,改为全 BLDC 方案(`rdrive` + `eth2can` + `dummy2-gui`)。**与本项目不是同一台机器**,没有 42/35 步进固件 |
| `Fan-feature` | B 站"断奶佛"的结构改版 | 2024-10-11 | 固件**就是 auk 的**(排除构建产物后仅 8 个 IDE 配置文件差异),真实贡献是 `3d-model` 重做:J1~J5 电机由 mini8 升级为 mini11/50 |

> **结论**:复刻本项目只需要 auk。`fox` 是另一个产品,`Fan-feature` 只在要改机械结构时才有参考价值。

### 1. 与 `<V2>/` 的全面比对结论(内容哈希,非文件名)

比对方法:两边全部文件算 md5,按**内容**做全局匹配,不受目录命名差异影响。

| 指标 | `<V2>/` | `source/dummy/`(auk) |
|---|---|---|
| 文件数 | 4137 | 3290 |
| 去重后唯一内容数 | 2488 | 1928 |
| **两边都有的内容** | **1781** | |
| 仅一方独有 | 707 种内容 / 1029 个文件 | 147 种内容 / 148 个文件 |

**auk 各目录被 `<V2>/` 覆盖的程度**:

| auk 目录 | 文件数 | 体积 | `<V2>/` 已有 | 判读 |
|---|---|---|---|---|
| `esp32-iot/` | 2519 | 89 MB | **100%** | 内容全覆盖,但 `<V2>/` 那份 332 个符号链接已损坏(见「五、已知坑」G3) |
| `3d-model/` | 24 | 18 MB | **100%** | 全在 `<V2>/4.Model/` 里 |
| `simple-cli/` | 3 | 16 KB | **100%** | 全在 `<V2>/3.Software/simple-cli/` |
| `firmware/` | 658 | 54 MB | 84% | 未覆盖的 83 个全在 ref-core:63 个纯 CRLF 差异 + 20 个 CubeMX 生成文件 |
| `harmonic_reducer/` | 3 | 276 KB | 67% | 两张参数图 `<V2>/6.Docs/减速器参数/` 已有,README 是新的 |
| `hardware/` | 19 | 2.1 MB | 56% | SchDoc 全部已有且同版,Gerber/手册/整板 BOM 是新的 |
| `images/` | 10 | 7.2 MB | 50% | 一半是 `<V2>/6.Docs/PCB/` 的实物照 |
| `ros2/` | 49 | 2.8 MB | **2%** | **几乎全新**,`<V2>/` 没有 ROS2 支持 |
| `bom/` | 2 | 32 KB | **0%** | `all_parts_dummy_1210.xlsx` 与 `<V2>/5.Bom/` 那份不是同一文件 |
| `bbs_backup_files/` | 1 | 7.8 MB | 0% | zip 本身是新的,但内含 5 个文件里 3 个 `<V2>/` 已有 |

### 2. 固件 baseline 溯源(已验证)

**结论:`<V2>/2.Firmware/` 的电机固件 = auk 分支 `ba5c088`(2023-12-10)。** auk 上改动过 42/35 固件的提交只有 4 个,最后一次就是 `ba5c088`"add latest motor 42/35 code to support Muzi Xiaowen's driver board",之后上游再未改动。

| 本地固件 | 对 auk 的比对结果 | 判读 |
|---|---|---|
| `dummy-42motor-fw` | 141 个文件中 **137 个 blob 哈希完全相同**,4 个不同 | **= auk**,4 处差异是你自己的 Linux 编译适配 |
| `dummy-35motor-fw` | 137 个文件 **全部相同,零差异** | **= auk**。`master` 分支根本没有 35motor 目录,反向印证 baseline 是 auk |
| `dummy-ref-core-fw` | 对 auk:137 个不同;对 `master`:**仅 5 个**不同 | **= master + 手工打上 auk 的 RGB 功能**,见下 |

**42motor 的 4 处差异(你的改动,非上游)**:

| 文件 | 改动 |
|---|---|
| `UserApp/configurations.h` | `#include "stdint-gcc.h"` → `<stdint.h>` |
| `UserApp/common_inc.h` | 同上 |
| `Port/Platform/Utils/st_hardware.h` | 同上 |
| `Ctrl/Sensor/Encoder/mt6816_base.h` | `virtual void SpiInit() {}` → `= 0`;`SpiTransmitAndRead16Bits` 同样改纯虚 |

> 前三条是 ARM GCC 私有头换标准头,第四条是修"非 void 函数无返回值"。这 4 处是 Linux 下编译通过的必要条件,**升级上游时需要重放**。

**ref-core 的特殊情况**:本地那份含 auk 独有的 `Bsp/gpio/rgb.cpp`、`rgb.hpp`、`usb-fs.tar.gz`,`dummy_robot.cpp` 里也有 `SetRGBMode`/`GetRGBEnabled`,但**与 auk 的 137 个差异中 117 个是纯 CRLF↔LF**(auk 做过一次 FreeRTOS 全量换行符转换),剩 20 个是 CubeMX 生成的 `Core/`。其中一处真实不一致:**本地 `Core/Inc/main.h` 缺 `RGB_Pin`(PA3)/`RGB_GPIO_Port` 定义**,即 RGB 应用层代码搬来了但 `.ioc` 没重新生成。全工程无人引用这两个宏,**编译不会断**,但将来真要点亮 LED Ring 时 PA3 没配成输出。

> ⚠️ **不要直接 `git checkout` 覆盖本地 ref-core** —— 换行符和 CubeMX 版本都与 auk 不一致,直接换会产生 117 个假 diff 淹没真改动。

### 3. auk 独有、`<V2>/` 没有的(真正的增量,148 个文件)

| 内容 | 路径 | 价值 |
|---|---|---|
| **ROS2 / MoveIt2 工作区** | `ros2/`(47 个新文件) | **最有价值的增量**,详见第 5 节 |
| 整板装配手册 | `hardware/dummy_boards_manual.pdf`(384 KB) | `<V2>/` 完全没有 |
| 三板整合 BOM | `hardware/dummy_boards_bom.xlsx`(19 KB) | 与 `<V2>/5.Bom/` 那份不同源 |
| 三块板 Gerber | `hardware/{ref-controller,motor42,motor35}/*-gerber.zip` | `<V2>/` 有自己的 Gerber,但内容不同(重新打包) |
| 全套物料清单 | `bom/all_parts_dummy_1210.xlsx`(24 KB) | 2023-12-10 版 |
| 论坛开源包 | `bbs_backup_files/bbs_backup.zip`(7.8 MB) | 见下表拆解 |
| 四个 README | `hardware/*/README.md`、`harmonic_reducer/README.md`、`bom/README.md`、`3d-model/README.md` | 含**减速器淘宝店、皮带计算工具、论坛 PCB 下载地址、J6 换 28 行星减速器的打算** |
| 63 个 CRLF 版 HAL 文件 + 20 个 CubeMX 文件 | `firmware/dummy-ref-core-fw/{Core,Drivers}/` | **无价值**,仅换行符/生成器版本差异 |
| 5 张图 | `images/`(35-driver / 42-driver / bldc / dummy_cnc / ref) | README 配图 |

**`bbs_backup.zip` 拆解**(已验证内容哈希):

| 包内文件 | 大小 | 状态 |
|---|---|---|
| `Cable_connection.pdf` | 291 KB | **`<V2>/6.Docs/Cable_connection.pdf` 已有**(哈希一致) |
| `Pins definations.pdf` | 245 KB | **`<V2>/6.Docs/Pins definations.pdf` 已有**(哈希一致) |
| `REF_V1.01.zip` | 3.0 MB | **`<V2>/1.Hardware/ref-controller/REF_V1.01.zip` 已有**(哈希一致) |
| `Motor-42_v1.01.zip` | 2.3 MB | **新** —— 含 5 个 SchDoc + `Motor-42.PcbDoc`,是**较旧的 V1.01 版**,与 `<V2>/` 的焊盘改版不同 |
| `Motor-35-V1.01.zip` | 2.3 MB | **新** —— 同上结构 |

### 4. `<V2>/` 独有、auk 没有的(1029 个文件)

| 内容 | 文件数 | 说明 |
|---|---|---|
| `2.Firmware/esp32-iot/` 的损坏符号链接 | 332 | **不是真内容**,是 332 个本该是符号链接的文本文件(见「五、已知坑」G3) |
| `3.Software/DummyStudio/` | 109 | 上位机 GUI,auk 完全没有 |
| `3.Software/CLI-Tool/` | 48 | auk 只有 `simple-cli`,CLI-Tool 来自 `Fan-feature` 分支的 `tool/` |
| `4.Model/`(木子晓汶版 70 + Dummy 58 + 原版 4) | 132 | auk 的 `3d-model/` 只有 24 个 stl,**`<V2>/` 的模型资料远比上游完整** |
| `2.Firmware/build/` | 136 | 你自己的 motor42-baseline 编译产物 |
| `6.Docs/复刻审计_2026-09-06/` | 49 | 你自己的审计产出 |
| `1.Hardware/` 的 PcbDoc 与 LedRing 板 | ~20 | **auk 没有任何 `.PcbDoc`(PCB 版图),也没有 LedRing 板** |
| `6.Docs/` 其余(芯片说明 6、DH参数 2、配色 2、其他 2) | 12 | 你整理的资料 |
| 5 份方案文档 + 使用指南 PDF | 6 | 你自己写的规划纲领 |
| `2.Firmware/Dummy 源码注释/` | 7 | 带注释版源码 |

> **判读**:`<V2>/` 在**模型、PCB 版图、上位机、文档**上比上游完整;上游在 **ROS2、Gerber、装配手册、esp32 符号链接完好性**上比 `<V2>/` 强。两者互补,都要留。

### 5. `ros2/` 索引(auk 独有,`<V2>/` 完全没有)

```
ros2/
├── README.md                       (仅一行 "ROS2 supports of Dummy")
└── dummy_ws/src/
    ├── dummy_moveit_config/        26 个文件  MoveIt2 配置包
    └── dummy-ros2_description/     22 个文件  URDF + 网格 + Gazebo
```

**`dummy_moveit_config/`** —— MoveIt Setup Assistant 生成:

| 文件 | 内容 |
|---|---|
| `config/dummy-ros2.urdf.xacro` / `.srdf` | 机器人描述与语义描述(规划组 `dummy_arm`) |
| `config/dummy-ros2.ros2_control.xacro` | ros2_control 硬件接口(**fake system,非真实 CAN**) |
| `config/joint_limits.yaml` | ⚠️ **只有速度限制**(`max_velocity: 3.15` 六轴相同),**无 position 限制**,加速度限制关闭 |
| `config/kinematics.yaml` | KDL 求解器,分辨率 0.005,超时 0.5 s |
| `config/initial_positions.yaml` | 六轴全 0 |
| `config/moveit_controllers.yaml` / `ros2_controllers.yaml` | 控制器声明 |
| `config/pilz_cartesian_limits.yaml` | Pilz 工业运动规划器的笛卡尔限制 |
| `config/moveit.rviz` / `moveit_empty.rviz` | RViz 布局 |
| `launch/`(10 个 .py) | `demo.launch.py`(一键起仿真)、`move_group.launch.py`、`moveit_rviz.launch.py`、`rsp.launch.py`、`spawn_controllers.launch.py`、`static_virtual_joint_tfs.launch.py`、`warehouse_db.launch.py`、`setup_assistant.launch.py`、`servo_cpp_interface_demo.launch.py` |
| `src/servo_keyboard_input.cpp` | **键盘遥操作**节点(对应 auk 提交 06febb4 "add dummy ros2 moveit2 and keyboard control files") |
| `src/servo_cpp_interface_demo.cpp` | MoveIt Servo C++ 接口示例 |

**`dummy-ros2_description/`** —— 模型描述包:

| 文件 | 内容 |
|---|---|
| `urdf/dummy-ros2.xacro` | **主 URDF**。7 个 link(base + link1~6)、6 个 revolute 关节。**含 `<mass>` 与完整 `<inertia>` 张量**(base 3.405 kg、link1 0.400 kg…)—— 全仓库唯一的动力学参数来源 |
| `urdf/dummy-ros2.trans` | 传动(transmission)定义 |
| `urdf/dummy-ros2.gazebo` | Gazebo 插件与材质 |
| `urdf/materials.xacro` | 颜色材质 |
| `meshes/*.stl`(7 个) | `base_link` + `link1_1_1`~`link6_1_1`,碰撞/可视化网格 |
| `launch/display.launch.py` | RViz 显示模型 |
| `launch/gazebo.launch.py` | Gazebo 仿真 |
| `config/display.rviz` | RViz 配置 |
| `setup.py` / `setup.cfg` / `package.xml` / `resource/` | ament_python 包定义 |
| `test/test_{copyright,flake8,pep257}.py` | ament 标准 lint 测试 |

**URDF 关节链**(`<origin xyz>`,单位 m):

| 关节 | parent → child | origin xyz | axis |
|---|---|---|---|
| Joint1 | base_link → link1 | `-0.019225, -0.000523, 0.100684` | `0,0,-1` |
| Joint2 | link1 → link2 | `-0.0155, 0.035, 0.0285` | `-1,0,0` |
| Joint3 | link2 → link3 | `0.03665, 0, 0.146` | `-1,0,0` |
| Joint4 | link3 → link4 | `-0.01855, -0.01, 0.052` | `0,-1,0` |
| Joint5 | link4 → link5 | `0.0168, 0.127, 0` | `-1,0,0` |
| Joint6 | link5 → link6 | `-0.018506, 0.077, -0.000106` | `0,-1,0` |

> ⚠️ 限位全是占位值、连杆原点与源码三吻合三冲突,详见「五、已知坑」G 节第 1、2 条。
> ⚠️ `ros2_control` 配的是 **fake system**,这套工程开箱只能跑仿真,**没有连到真实 CAN 总线**。要驱动实物需自己写 hardware_interface。

### 6. 其余目录速览

| 目录 | 内容 |
|---|---|
| `3d-model/` | 根部 7 个 stl(base/joint1/joint23/joint4/joint5/joint6/controller_enclosure)+ `latest/`(8 个,3D 打印最新版)+ `m35/` / `m42/`(电机支架,文件名含 `metal` 的是 CNC 件)+ `ref-controller/`(OLED 支架)+ `mini8/mini11-bracket-metal.stl` + `stps/`(**只有 README,指向已删除的 Fan-feature 分支**) |
| `firmware/` | `dummy-ref-core-fw`(主控)、`dummy-42motor-fw`、`dummy-35motor-fw`。**内容与 `<V2>/2.Firmware/` 对应,阅读请用第七、八章的详细索引** |
| `esp32-iot/` | `firmware/`(mongoose 库 + 大量示例)+ `tool/`。**编译 ESP32 例程用这份,不要用 `<V2>/` 那份** |
| `hardware/` | 三块板各一个 Gerber zip + 松散 SchDoc(与 `<V2>/` 同版)+ 整板手册 PDF + 整板 BOM xlsx。**无 PcbDoc、无 LedRing** |
| `harmonic_reducer/` | `mini8_parameters.JPG` / `mini11_parameters.JPG`(= `<V2>/6.Docs/减速器参数/`)+ README(厂家淘宝店) |
| `bom/` | `all_parts_dummy_1210.xlsx` + README(皮带计算工具链接) |
| `simple-cli/` | `simple-cli.py` + `chatgpt_gui.py` + README(= `<V2>/3.Software/simple-cli/`,见第十章) |
| `images/` | README 配图 + 实物照 |
| `bbs_backup_files/` | `bbs_backup.zip`,拆解见第 3 节 |

### 7. 本章可回答的典型问题 → 去哪个文件

| 问题 | 去哪 |
|---|---|
| 克隆的是哪个分支、其他分支还在吗 | 本章开头。只有 auk,其余已删且 fetch 已限定 |
| 我的固件 baseline 对应上游哪个提交 | 第 2 节:auk `ba5c088`(2023-12-10) |
| 我对固件改了什么 | 第 2 节表格,4 处 Linux 编译适配 |
| 上游有什么我没有的 | 第 3 节(148 个文件,核心是 `ros2/`) |
| 我有什么上游没有的 | 第 4 节(模型/PcbDoc/上位机/文档/审计) |
| 怎么跑 ROS2 仿真 | 第 5 节,`ros2/dummy_ws/src/dummy_moveit_config/launch/demo.launch.py` |
| URDF 里的参数能信吗 | 第 5 节 + 「五、已知坑」G1/G2。**限位不能信,连杆原点可作交叉参考** |
| 关节质量惯量在哪 | `ros2/dummy_ws/src/dummy-ros2_description/urdf/dummy-ros2.xacro` |
| 为什么 `<V2>/` 的 esp32 例程编不过 | 「五、已知坑」G3,332 个符号链接损坏,改用 `source/dummy/esp32-iot/` |
| 打板该用哪一版原理图 | 「五、已知坑」G4。`<V2>/` 与 auk 同版,**别用 bbs zip 里的 V1.01** |

---

## 十三、版本判定与打板选型(已定稿)

> **本章是决策记录,不是待讨论的选项。** 2026-10-12 定稿,后续打板/打印直接照此执行,不要再重新权衡。
>
> | 项目 | **定稿选择** | 路径 |
> |---|---|---|
> | **PCB(三块板)** | **auk 的 Gerber**(= 硬件 **V1.01**) | `source/dummy/hardware/{ref-controller,motor42,motor35}/*-gerber.zip` |
> | **结构件** | **「Dummy V2 版本 视频款」** | `<V2>/4.Model/Dummy V2 版本 视频款/` |
>
> 选 V1.01 的外部依据:B 站已有复刻者用 **V1.0.1 硬件 + 任同学包里的视频同款结构件**成功焊板点亮。本章的作用是把"V1.0.1 到底对应哪些文件"钉死,避免日后拿错版本。

### 1. 为什么会有版本混乱

同一块板在仓库里有**三份互不相同的版图**,文件名都不带版本号,只靠 mtime 根本分不清。实测的血脉关系:

```
                 V1.01 (2023-12, 丝印带 "V1.01")
                  │
      ┌───────────┴───────────┐
      │                       │
  PCB源文件                焊盘更改版
  (删掉版本丝印,            (删掉 4 个过孔,
   焊盘/铺铜微调)            保留 V1.01 丝印)
  2024-05~10                2024-07-17
```

**所有现存 Gerber 都导出自 V1.01 血脉**,焊盘更改版从未导出过 Gerber。

### 2. V1.01 的识别证据(四条独立证据)

**证据一:`V1.01` 是丝印上的真实字符串。** 从 PcbDoc 的 OLE `Texts6` 流中提取:

| 版图 | 丝印含 `V1.01` |
|---|---|
| `bbs_backup.zip` 内 Motor-42 / Motor-35 / REF | ✅ 有 |
| 焊盘更改版 Motor-42 / Motor-35 | ✅ 有 |
| `<V2>/1.Hardware/*/PCB源文件/` 的三块板 | ❌ **被删除** |

**证据二:过孔坐标指纹。** 解析 `Vias6` 流(X/Y 在记录 payload 偏移 13 / 17,各 4 字节 int32),提取全部过孔坐标做集合比对:

| 板 | bbs V1.01 vs `PCB源文件` | vs 焊盘更改版 |
|---|---|---|
| Motor-42 | **155 个坐标完全相同** | 少 4 个,Y 跨距 31.23 → 29.74 mm |
| Motor-35 | **132 个坐标完全相同** | 少 4 个,Y 跨距 32.11 → 26.72 mm |
| REF | **192 个坐标完全相同** | (无焊盘更改版) |

> 所以 **`PCB源文件` 与 V1.01 是同一套布线**,只是改了丝印和焊盘;**焊盘更改版是 V1.01 删掉 4 个过孔**的衍生版。

**证据三:过孔数 + 通孔焊盘数 = 钻孔总数**,用来验证 Gerber 归属:

| 板 | V1.01 过孔 | + 通孔焊盘 | = 应有孔数 | Gerber 实测 |
|---|---|---|---|---|
| Motor-42 | 155 | 22 | 177 | auk 包 **177** ✅ |
| Motor-35 | 132 | 22 | 154 | 两套都是 **154** ✅ |
| REF | 192 | 28 | 220 | 两套都是 **220** ✅ |

**证据四:REF 两套 Gerber 谁是 V1.01。** 走线量与丝印量方向一致:

| 指标 | auk(2023-11-13) | `<V2>` 平铺(2024-03-24) |
|---|---|---|
| `Tracks6`(对应版图) | bbs V1.01 = 140404 B | `PCB源文件` = 140458 B(+54) |
| GBL 底层铜 | 走线较少 | **多出一段**(40 行换 16 行) |
| GTO 顶层丝印 | 73917 B(丝印完整) | 44086 B(**精简,V1.01 字样消失**) |

> 结论:**auk 的 REF Gerber = V1.01 原版**;`<V2>` 平铺那套是 2024-03 的后续改版,**不是 V1.01**。
> ⚠️ 这一条推翻了"越新越好"的直觉。要 V1.01 就用 auk,不要用 `<V2>` 的平铺集。

### 3. Gerber 取用表(照此下单)

| 板 | **送厂文件** | 版本 | 孔数 | 备注 |
|---|---|---|---|---|
| **REF 主控板** | `source/dummy/hardware/ref-controller/ref-controller-gerber.zip` | **V1.01** | 220 | 等价于 `<V2>` 那个 zip 里的 `REF_V1/` 子目录(逐字节相同) |
| **Motor-42** | `source/dummy/hardware/motor42/motor42-gerber.zip` | **V1.01** | 177 | **唯一可用包**,`<V2>` 那个缺钻孔 |
| **Motor-35** | `source/dummy/hardware/motor35/motor35-gerber.zip` | **V1.01** | 154 | 铜层与 `<V2>` 包完全相同,仅底层丝印不同 |
| LedRing(选装) | `<V2>/1.Hardware/LedRing/led gaber.zip` | 2024-02-20 | 3 | **不属 V1.01 体系**,auk 没有这块板;装灯环才需要 |

**三块主板的板框尺寸(解析 GKO 得出,三版均一致,机械上可互换)**:

| 板 | 外形 |
|---|---|
| Motor-42 | 41.20 × 41.20 mm |
| Motor-35 | 26.01 × 35.03 mm |
| REF | 48.01 × 58.00 mm |

**配套的生产辅料**:

| 用途 | 文件 |
|---|---|
| 交互式 BOM(位号↔型号↔封装,点击高亮) | `<V2>/1.Hardware/{motor42/Motor-42.html, motor35/Motor-35.html, ref-controller/REF-Base.html}` —— InteractiveHtmlBom 生成,浏览器直接打开 |
| 三板整合 BOM | `source/dummy/hardware/dummy_boards_bom.xlsx`(sheet: REF / Motor-42 / Motor-35 / Screws / belts) |
| 整机 BOM(含淘宝链接与套餐价) | `<V2>/5.Bom/dummy V2版本_bom.xlsx` |
| **端口与拨码定义**(焊后接线必用) | `source/dummy/hardware/dummy_boards_manual.pdf` —— 三板 P1/P2/P3 定义 + S1 拨码的 CAN ID 对照表与终端电阻。**`<V2>` 没有这份** |
| 接线图 / 引脚定义 | `<V2>/6.Docs/Cable_connection.pdf`、`Pins definations.pdf` |

⚠️ **没有贴片坐标文件(Pick & Place)**。`<V2>/1.Hardware/ref-controller/PCB源文件/PnPout/` 里只有一个 html,没有 csv/txt。要板厂贴片得自己从 PcbDoc 导,或让板厂从 Gerber 反推(加钱且易错)。

### 4. 文件黑名单(不要用)

| 文件 | 为什么不能用 |
|---|---|
| `<V2>/1.Hardware/motor42/motor42 Gaber.zip` | **缺 `.TXT`/`.DRR`/`.LDP`,没有钻孔数据** |
| `<V2>/1.Hardware/ref-controller/ref-controller-gerber.zip` 的**平铺集** | 是 2024-03 后续改版,**不是 V1.01**。要用就只用里面的 `REF_V1/` 子目录 |
| `Motor-42（焊盘更改版）.rar`、`Motor-35（焊盘更改版）.rar` | 比 V1.01 少 4 个过孔,**没有对应 Gerber**,改动意图不明 |
| `bbs_backup.zip` 内的 `Motor-42_v1.01.zip` / `Motor-35-V1.01.zip` / `REF_V1.01.zip` | 只有 PcbDoc/SchDoc,**没有 Gerber**;是归档源文件,不是送厂文件 |
| 任何用 KiCad / 嘉立创EDA 转换后重新导出的 Gerber | 封装与焊盘可能有细微偏差,**打出来焊不上**。要重导只能用正版 Altium 开 `.PcbDoc` |

> 补充:**auk 里没有任何 `.PcbDoc`**(只有 11 个 `.SchDoc`),所以 auk 只能打板、不能改板。版图源文件只有 `<V2>/1.Hardware/*/PCB源文件/` 有。

### 5. 结构件:视频款(已定稿),与木子晓汶版互斥

`<V2>/4.Model/` 下是**三套**,不是一套:

| 套 | 文件数 | 内容 | 与 auk 的关系 |
|---|---|---|---|
| **Dummy V2 版本 视频款** ← **定稿选用** | 59 | 3D打印 STL + PCB外壳 + 控制器外壳 + 基座底板 + 亚克力盖板图纸 + CNC STEP + 全套 2D 工程图 + 整机装配体 | **`<V2>` 独有,auk 没有** |
| 木子晓汶版本3D模型 | 94 | 24 个 STL + `Out_stp1/` SolidWorks 源 | **= auk 的 `3d-model/`,24 个文件逐一对应、哈希全同** |
| 稚晖君原版模型 | 4 | 4 个 STEP | 原始参考 |

**两套几何完全不同,混装必然装不上**(STL 包围盒实测,mm):

| 零件 | 视频款(选用) | 木子晓汶(= auk) |
|---|---|---|
| J1 | 85.0 × 65.0 × 57.0 | 79.0 × 62.9 × 48.5 |
| J2J3 | 205.0 × 52.0 × 50.0 | 194.0 × 55.9 × 51.0 |
| J4 | 94.5 × 55.0 × 35.0 | 117.7 × 51.5 × 51.1 |
| J6 | 80.0 × 47.5 × 35.0 | 99.0 × 41.0 × 36.0 |
| 基座 | 100 × 100 × **82.7** | 100 × 100 × **99** |
| J5 | **拆 3 件**:J5A + J5B + J5法兰盘 | 单件 `joint5.stl` 151 × 48 × 39 |

> 螺丝孔位与皮带长度均不通用。**决定用视频款后,`<V2>/4.Model/木子晓汶版本3D模型/` 和 `source/dummy/3d-model/` 都不要再去打印。**

**视频款与 PCB 的装配兼容性(已验证)**:

| 外壳件 | 包围盒 | 对应板框 | 判读 |
|---|---|---|---|
| `42PCB外壳A/B.stl` | 42.00 × 42.00 × 3/8 | Motor-42 41.20 × 41.20 | ✅ 留 0.8 mm 间隙 |
| `35PCB外壳A/B.stl` | 35.20 × 35.20 × 3/8 | 35 mm 电机法兰 | ✅ |

**视频款要打印/加工的件**:

```
3D打印STL文件/   J1 · J2J3 · J4 · J4法兰盘 · J5A · J5B · J5法兰盘 · J6
                 外壳A/B/C · 基座 · 基座底板 · 控制器外壳 · 控制器内衬 · 控制器屏幕底板
                 42PCB外壳A/B · 35PCB外壳A/B
                 dummy 亚克力 PCB盖板 图纸.zip     ← 亚克力件,给激光切割厂
CNC加工STEP文件/  基座 · J1 · J23 · J4 · J4法兰盘 · J5A · J5B · J5法兰盘 · J6   ← 要金属件时用
Dummy-B 2D工程图/ 整套 2D 图(合并版 + 10 份拆分)   ← 查尺寸/公差
改版/            基座改版.step · J1改版.step · Dummy-B.STEP + 8 份改版工程图
Dummy-B v2装配体.step                              ← 整机装配参考
```

### 6. 已定稿但待实测:L1 / L4 / L6

**固件的运动学常数是按木子晓汶结构算的,不是视频款。** 判定依据:auk 自带 ROS2 URDF 的网格与木子晓汶**逐件精确吻合**:

| URDF link | URDF 网格 | 木子晓汶 | 视频款 |
|---|---|---|---|
| link1 | 79.0 × 62.9 × 48.5 | `joint1.stl` 79.0 × 62.9 × 48.5 ✅ | 无一件吻合 |
| link2 | 194.0 × 55.8 × 51.0 | `joint23.stl` 194.0 × 55.9 × 51.0 ✅ | |
| link3 | 117.7 × 51.5 × 51.1 | `joint4.stl` 117.7 × 51.5 × 51.1 ✅ | |
| link4 | 151.0 × 48.0 × 39.0 | `joint5.stl` 151.0 × 48.0 × 39.0 ✅ | |

但视频款的 2D 工程图里提取到的尺寸与固件**三项精确一致**:

| 固件 `dummy_robot.cpp:32` | 视频款图纸 | 结论 |
|---|---|---|
| L2 = 35 mm | `J1改版.pdf` → **35** | ✅ 一致 |
| L3 = 146 mm | `J23.pdf` → **146** | ✅ 一致 |
| L5 = 52 mm | `J4.pdf` → **52** | ✅ 一致 |
| L1 = 109 mm | 未提取到 | ❓ **待实测** |
| L4 = 115 mm | `J5B.pdf` 有 92 | ❓ **待实测** |
| L6 = 72 mm | `J6.pdf` 有 62.50 | ❓ **待实测** |

> **L2 / L3 / L5 这三项同时也是「五、已知坑」A1 里 DH 图与源码唯一不冲突的三项**,现在又被视频款图纸和 URDF 独立验证,可视为可信。
>
> ⚠️ 两条限制:① 工程图是矢量图,`pdftotext` 只能提取部分标注(`基座改版.pdf`、`J5A.pdf`、两份法兰盘图完全提不出文字);② **零件包围盒 ≠ 连杆长度**,视频款把 J5 拆三件又加了外壳,包围盒差异有一部分来自拆分方式而非运动学。
>
> **装配后必做**:六轴归零,量 J1轴心→J2轴心、J4轴心→J5轴心、J6轴心→末端法兰面,对照 `dummy_robot.cpp:32` 的 `DOF6Kinematic(0.109f, 0.035f, 0.146f, 0.115f, 0.052f, 0.072f)`。对不上就改这一行。
> **只影响 MoveL(笛卡尔)**,关节空间 MoveJ 不受影响,所以即使暂时不准也能先跑起来调试。

### 7. ROS2 仿真的注意事项

`source/dummy/ros2/` 那套 URDF 是**木子晓汶结构**的,与定稿选用的视频款不匹配。要跑仿真需二选一:

1. 仿真只当学习 MoveIt 用,不追求与实物一致 —— 直接用,不改
2. 要与实物一致 —— 得替换 `dummy-ros2_description/meshes/*.stl` 并重算 `urdf/dummy-ros2.xacro` 的 6 个 `<origin xyz>`

另注:URDF 的 `<limit>` 全是占位值 ±3.14,`ros2_control` 是 fake system,见「五、已知坑」G1。

### 8. 复核方法(结论可重跑)

本章结论全部可复现,不依赖记忆:

| 要查的 | 怎么查 |
|---|---|
| 某版图是不是 V1.01 | `python3` + `olefile` 读 PcbDoc,拼接 `Texts6` 流,搜 ASCII 字符串 `V1.01` |
| 两版图是否同一布线 | 解析 `Vias6`:记录头 1 字节类型 + 4 字节长度(LE),payload 偏移 13/17 各取 int32 为 X/Y,比对坐标集合 |
| Gerber 属于哪一版 | 读 `.DRR` 的 `Totals` 孔数,与「过孔数 + 通孔焊盘数」对照 |
| 两套 Gerber 是否同板 | `diff` 各层并排除 `^G04` 注释行;孔位用 `.TXT` 解析(注意 `INCH,LZ` 与 `INCH,TZ` 零压缩方向相反) |
| 板框尺寸 | 解析 `.GKO` 的 `X/Y` 坐标取包围盒,按 `%FSLAX..Y..%` 的小数位数换算 |
| STL 尺寸 | 二进制 STL:跳过 80 字节头 + 4 字节面数,每面 50 字节,取 12 个 float 的后 9 个为三顶点 |

### 9. 本章可回答的典型问题 → 去哪

| 问题 | 去哪 |
|---|---|
| 打板用哪个文件 | 第 3 节取用表。三块板全用 `source/dummy/hardware/` |
| 哪些文件不能用 | 第 4 节黑名单 |
| 怎么证明是 V1.01 | 第 2 节四条证据 |
| 打印用哪套结构件 | 第 5 节。视频款,且不可与木子晓汶版混装 |
| 为什么 REF 不用更新的那套 | 第 2 节证据四。`<V2>` 平铺集是 2024-03 后续改版,不是 V1.01 |
| 外壳能装下 PCB 吗 | 第 5 节装配兼容性表,已验证 |
| 连杆长度能信吗 | 第 6 节。L2/L3/L5 可信,L1/L4/L6 待实测 |
| 仿真和实物不一致怎么办 | 第 7 节 |
| 结论怎么复核 | 第 8 节,给了每一项的具体解析方法 |

---

## 附:本索引的维护

- **生成方式**:6 个子代理并行实读全仓库(打开源码、看图、解压交互式 BOM、跑 `diff -rq`、读 xlsx),非文件名推断。
- **覆盖范围**:`<V2>/` 等原有内容 4436 个文件(清理前 4524)+ `source/dummy/` 上游克隆 3290 个文件。业务代码逐文件详写;HAL/CMSIS/FreeRTOS 内核/mongoose 示例/Unity 运行时等第三方与自动生成内容只做一句话标注。
- **2026-10-12 增补(二)**:新增**第十三章「版本判定与打板选型」**,记录 PCB/结构件的定稿选择与判定证据。判定手段包括:读 PcbDoc 的 OLE `Texts6` 流取丝印字符串、解析 `Vias6` 流取过孔坐标做指纹比对、用「过孔数+通孔焊盘数=钻孔总数」验证 Gerber 归属、解析 `.GKO` 算板框、解析二进制 STL 算包围盒。每项的复核方法记在该章第 8 节。
- **2026-10-12 增补(一)**:新增第十二章(上游克隆索引)。比对方式为两边全部文件算 md5 后按**内容**全局匹配 + `git hash-object` 逐文件核对 blob,并对 CRLF/空白差异做了 `diff --strip-trailing-cr -w` 二次甄别,所以"相同/不同"的判定是字节级的,不是按文件名或体积推断。
- **需要更新本索引的时机**:固件业务代码有改动、硬件换版、`notes/` 路线图推进到新阶段、或新增了方案文档。
- **不要**把本索引当作参数的权威来源——凡数值都标了出处,冲突项见「五、已知坑」。
