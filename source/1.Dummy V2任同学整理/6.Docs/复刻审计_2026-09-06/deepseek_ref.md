> 原始子代理意见，保留用于审计追溯，不是执行依据。本文的方向位、位与表达式、温度监视接口、IMU 初始化顺序等有误判；以 [审计结论与证据](审计结论与证据.md) 的复核裁定为准，不能照搬急停修复建议。

I have complete coverage. Writing the final report now.

---

# Dummy V2 复刻项目 — REF 核心固件（dummy-ref-core-fw）审计报告

**审计对象**：`2.Firmware/dummy-ref-core-fw/`（STM32F405 REF 主控固件）
**审计方式**：只读静态审计，未编译、未烧录、未运行任何程序、未改动任何文件。

## 一、覆盖目录与实际读过并逐行核对的关键文件

审计覆盖全部自研代码目录（UserApp / Robot / Bsp / Core / startup / USB_DEVICE / 3rdParty fibre），第三方库（HAL/CMSIS/FreeRTOS/u8g2/fibre/MPU6050 寄存器表）只确认集成边界，不逐行审查。已完整逐行读过的文件：

| 关键文件 | 作用 |
|---|---|
| `UserApp/main.cpp` | 应用入口、任务/定时器/IMU/OLED 初始化 |
| `Robot/instances/dummy_robot.cpp` / `.h` | 6 轴实例、DH、限位、命令处理、急停/回零/校准 |
| `Robot/actuators/ctrl_step/ctrl_step.cpp` / `.hpp` | CAN 电机协议封装 |
| `Robot/algorithms/kinematic/6dof_kinematic.cpp` / `.h` | 六轴 FK/IK |
| `Bsp/communication/interface_can.cpp` / `.hpp` | CAN 收发、心跳、错误处理 |
| `Bsp/communication/interface_uart.cpp` | UART4/5 DMA 环形接收、ASCII 解析 |
| `Bsp/communication/ascii_processor.cpp` / `.hpp` | ASCII 行解析器 |
| `Bsp/communication/interface_usb.cpp` | USB-CDC 收发 |
| `Bsp/communication/communication.cpp` / `.hpp` | 通信总调度 |
| `UserApp/protocols/ascii_protocol.cpp` | ASCII 命令实现（!STOP/START/HOME/CALIBRATION…） |
| `UserApp/protocols/can_protocol.cpp` | CAN 接收回解析 |
| `UserApp/protocols/cmd_protocol.cpp` | fibre 协议树 |
| `Core/Src/main.c`、`freertos.c`、`can.c`、`usart.c`、`stm32f4xx_it.c`、`timer.cpp/hpp`、`pwm.cpp`、`emulated_eeprom.cpp`、`STM32F405RGTx_FLASH.ld`、`CMakeLists.txt`、`REF-STM32F4-fw.ioc`、`FreeRTOSConfig.h` | 启动/中断/外设/构建/链接 |

## 二、P0 发现（阻塞项，必须先修订）

### P0-1 急停 `!STOP` 不会真正切断电机使能，仅令本地 `isEnabled=false` 且无法阻止正在进行的定速运动
- **证据**：`dummy_robot.cpp:402-409` `EmergencyStop()` 仅 `MoveJ(当前角度)`→`MoveJoints`→`isEnabled=false`→清 FIFO；`isEnabled` 只在 `ThreadControlLoopFixUpdate`（`main.cpp:27`）判断后停止下发新轨迹。
- **触发条件**：COMMAND_CONTINUES_TRAJECTORY 或 MOTOR_TUNING 模式下急停；或任一节点 CAN 反馈丢失时。
- **影响**：急停不向节点发 `SetEnable(false)`（即不发 `0x7d`/置 0 使能帧），电机不立即失能；`MoveJoints` 是阻塞等待 `IsMoving()` 的（`dummy_robot.cpp:458-459`），在命令线程内长时间 `osDelay(5)`。
- **修复**：`EmergencyStop()` 必须对 1..6 节点调用 `SetEnable(false)` + `SetEnableTemp(false)` 下发失能 CAN 帧；`isEnabled=false` 前先关使能。物理急停（电源/使能开关）应在硬件链路立即切断功率级。

### P0-2 `!HOME` 与 `!CALIBRATION` 会自动运动，且 `Homing()` 可能无视方向/限位撞机械限位
- **证据**：`dummy_robot.cpp:232-243 Homing()` 无任何使能检查即 `MoveJ(0,0,90,0,0,0)` + `MoveJoints`；`CalibrateHomeOffset()`（199-229）会 `SetEnable(true)`、把 J2/J3 电流限 0.5、`ApplyPositionAsHome()`、再 `Resting()` 自动运动并最终 `Reboot()`。
- **触发条件**：发送 `!HOME` 或 `!CALIBRATION` 时关节/机械未装配到位、编码器未校准、`inverseDirection` 与实物方向不符。
- **影响**：自动运动可能直接撞机械限位或人；校准失败仍会 `Reboot()` 复位，状态不可控。
- **修复**：初稿必须写清"HOME/CALIBRATION 是自动运动，需有人在场 + 物理急停 + 先确认六轴方向/减速比/零位"；建议 Homing/Calibrate 前增加使能与位置合理性前置检查。

### P0-3 IMU（MPU6050）未贴装时启动死循环阻塞（与初稿 9.1 所提一致，且更严重）
- **证据**：`main.cpp:165-171` `do{ mpu6050.Init(); osDelay(100);} while(!mpu6050.testConnection());` 是**上电后即执行**的忙等死循环，早于 OLED/pwm/线程启动——不是"后面才停"，而是**整机无法启动**（不会进入任何任务，CAN 也不工作）。
- **触发条件**：REF 板未贴 MPU6050、或 I2C1 断线。
- **影响**：不贴 IMU 的"最小 REF"路线（初稿 9.2 设想）完全无法工作。
- **修复**：初稿明确：若第一版不贴 IMU，必须把该循环改为"有限次数尝试+超时跳过"或宏开关；并注意 `oled.Init()` 也在其后（167 行后会因 `ThreadOledUpdate` 调用 `mpu6050.Update()` 同样依赖）。

### P0-4 电机节点使能命令与 CRC/校验缺失耦合，CAN 反馈无节点有效性过滤，位选未校验越界
- **证据**：`can_protocol.cpp:17-45` 对 `StdId>>7` 得到的 `id` 直接 `dummy.motorJ[id]`（id 可为 0…7），无 id 范围校验（id=7 会越界访问 `motorJ[7]` 为 `hand` 区域之外）；`UpdateAngleCallback` 直接 `*(float*)data` 取角度（无奇偶/长度校验，但节点端的自定义协议本身无 CRC）。`ascii_protocol.cpp:70` 等处 `node >= 1 & node <= 6` 是**位与（&）运算**而非逻辑与（&&），`node=2` 时 `(1&2)=0` 为假、`node=3` 时 `(0&3)=0` 亦为假，边界判断错误（node=5、6 等偶数被误拒绝，node=0/7 之类可能误放行）。
- **触发条件**：CAN 总线上出现非预期节点 ID 帧、或用户发 `#SET_DCE_KP 5 xxx`。
- **影响**：数组越界读 → 潜在 HardFault；命令误拒绝/误放行。
- **修复**：id 校验 `id>=1 && id<=6`；位选判断全部改用 `&&`；`UpdateAngleCallback` 前对 id/cmd 做白名单。

## 三、P1 发现（高风险，需修订）

### P1-1 移动阻塞占用命令线程，`MoveJoints` 的 `while(IsMoving())` 可能永久卡死
- **证据**：`dummy_robot.cpp:458-459` 在 `ParseCommand` 内 `while(IsMoving()&&IsEnabled()) osDelay(5)`；`IsMoving()`（296-299）判断 `jointsStateFlag != 0b1111110`，而 `jointsStateFlag` 由 `UpdateJointAnglesCallback`（`can_protocol.cpp:38` 调用）依据节点 `FINISH` 回包更新。若节点不回 ACK（`ctrl_step.cpp:102` `canBuf[4]=1` 需 ACK），标志永不满足条件 → 该命令线程死等，后续命令队列入口（`commandHandler.Push`）虽在另一处但响应被堵。
- **影响**：一节点掉线即可能使整条命令处理链卡死；无超时。
- **修复**：所有 `while(IsMoving())` 加超时与看门狗；CAN 节点心跳监测超时置失能（见 P1-3）。

### P1-2 CAN 无节点在线监测/超时失能机制，掉线不停止
- **证据**：`interface_can.cpp` 仅累积计数 `received_msg_cnt/unexpected_errors`，`can_protocol.cpp` 无任何"超时未收到心跳→失能"逻辑；`CanSendMessage`（237-249）用二进制信号量（初值 1，`osSemaphoreNew(1,1,...)`）实现单缓冲区互斥，TX 失败回调 `tx_aborted_callback` 只计数不重发。`interface_can.hpp` 中 `node_ids_in_use_*` 是 ODrive fibre 的心跳机制但被注释未真正用于节点超时。
- **影响**：严重违背初稿 8.2/第三阶段 Gate"CAN 掉线时关节可安全停止"——当前固件**不具备**这一能力。
- **修复**：初稿需明确此功能必须新增实现；节点超时→`SetEnable(false)`+报警。

### P1-3 调试/量产关键命令（使能、写 EEPROM、设 ID）通过 `#`/fibre 暴露且无鉴权、无写保护
- **证据**：`ascii_protocol.cpp:53-107` 暴露 `SET_DCE_KP/KI/KD`、`REBOOT`、`CMDMODE`；`ctrl_step.hpp:62-90` 暴露 `set_node_id`、`erase_configs`、`set_enable_on_boot`、`set_current_limit`（均写 Flash）。`CalibrateHomeOffset` 也经 fibre `calibrate_home_offset` 暴露。
- **影响**：误发 `#REBOOT 6`/`erase_configs`/`set_node_id` 会破坏参数甚至改坏节点 ID，导致整机失联。
- **修复**：初稿应增加"危险命令加保护/确认"条款，并强调节点 ID 勿在生产中线改。

### P1-4 逆运动学 `MoveL` 只做关节限位过滤，未做可达性/奇异处理保护
- **证据**：`dummy_robot.cpp:104-158` `MoveL` 选 8 组解中限位合法且距当前最近者，但 `SolveIK`（`6dof_kinematic.cpp:182-499`）对奇异（`R36[8]≈±1`）分支依赖 `_lastJoint6D` 的历史值；`MoveJ` 计算的 `time`（87 行）分母依赖 `jointSpeed`（可被 `SetJointSpeed(0)` 置 0）→ **除零风险**。
- **触发条件**：`!...#SET...` 后 `jointSpeed=0`，再发 `>`/`@`。
- **影响**：除零产生 inf/NaN 速度，`SetAngleWithVelocityLimit` 下发异常速度。
- **修复**：`jointSpeed` 下限钳位（>0）；`SetJointSpeed` 已钳 0~100（`dummy_robot.cpp:180-186`），但 `jointSpeed=0` 仍可达（`_speed=0` 时 `jointSpeed=0`）。

## 四、P2 发现（需记录/低危）

- **P2-1** `dummy_robot.cpp:64-66` `MoveJoints` 下发 `_joints.a[j-1]-initPose.a[j-1]`，而 `initPose` 初始 = `REST_POSE{0,-73,180,0,0,0}`，`currentJoints` 也 = `REST_POSE`（`dummy_robot.h:115-117`），但 `UpdateJointAnglesCallback` 用 `angle+initPose`（170 行）——零位/基准叠加逻辑易与"两轴最小化改两轴问题"混淆，初稿需单列核对。
- **P2-2** 单位混用：IK 输入 mm（`MoveL` 传 mm，`SolveIK` 里 `/1000`），FK 输出 mm×1000（`dummy_robot.cpp:290-292`）；ASCII `@` 命令直接 mm。初稿 5 轴表未明写单位。
- **P2-3** `thread_local` 被注释降级为全局（`interface_uart.cpp:15`），多通道并发有竞态风险（UART4/5 共享 `ASCII_protocol_parse_stream` 的 `static parse_buffer`——两路 UART 会互相覆盖解析缓冲）。
- **P2-4** `pwm.cpp:15` TIM9 预分频 `168000/freq-1`，Project `pwm(21000,21000)` 时 PSC=7，与 `.ioc` `TIM9.Prescaler=7` 一致，但构造函数会覆盖 `.ioc` 值——若依赖 CubeMX 重新生成需撤销（初稿 12 条已提及）。
- **P2-5** `emulated_eeprom.cpp` 使用**最后 1 个扇区**（`FLASH_DATA_SECTOR=FLASH_SECTOR_TOTAL-1`，即 sector 11/12 之一）做参数存储，`EraseConfigs`→`eeprom_buffer_flush` 全扇擦写，擦写期间无掉电保护（无双 bank 备份），掉电可能破坏整个参数表。
- **P2-6** 手抓 `DummyHand::SetAngle` 角度钳位在类内 0~45 但 `dummy_robot.h:52` `maxAngle=45` 未用于 CAN 限位，夹爪无对应机械固件（初稿已识别）。

## 五、已确认参数表（源码实证，非推断）

| 项 | 值 | 证据位置 |
|---|---|---|
| MCU / 时钟 | STM32F405RGTx，HSE→PLL 168MHz，APB1=42M/APB2=84M | `main.c:161-198`、`.ioc` |
| CAN 波特率 | **1 Mbit/s**（Prescaler=7, BS1=3TQ, BS2=2TQ） | `can.c:42-46`、`.ioc:31-35` |
| CAN StdId | `(nodeID<<7) \| cmd` | `ctrl_step.cpp:27` |
| UART | UART4(PA0/1)、UART5(PC12/PD2)、USART1(PA9/10)，全 115200 8N1 | `usart.c:46-118` |
| 控制环频率 | 200 Hz（`Timer(&htim7,200)`，TIM7 中断通知任务） | `main.cpp:9`、`timer.cpp:55/61` |
| OLED/IMU I2C | OLED=软件 I2C `hi2c0`，MPU6050=硬件 I2C1 `hi2c1` | `main.cpp:5-7` |
| 六轴减速比 | J1..J6 = **30/30/30/24/30/50** | `dummy_robot.cpp:24-29` |
| 六轴软件范围 | J1 -170~170、J2 -73~90、J3 35~180、J4 -180~180、J5 -120~120、J6 -720~720 | `dummy_robot.cpp:24-29` |
| 方向反转 | J1=false、J2=**true**、J3=false、J4=**true**、J5=false、J6=**true** | 同上 |
| DH 尺寸(mm) | 109 / 35 / 146 / 115 / 52 / 72 | `dummy_robot.cpp:32` |
| REST_POSE | {0, -73, 180, 0, 0, 0} | `dummy_robot.h:107` |
| initPose/currentJoints 初值 | = REST_POSE | `dummy_robot.h:115-117` |
| 默认命令模式 | COMMAND_TARGET_POINT_INTERRUPTABLE | `dummy_robot.h:112` |
| 默认速度/加速度 | speed 30 °/s；accel 基 {150,100,200,200,200,200}；低 30/高 100 | `dummy_robot.h:108-111` |
| DCE 默认参数 | current 2A、accel 30、Kp/Kv/Ki/Kd 见头注释 | `dummy_robot.h:10-17` |
| 夹爪 | nodeID 7，maxCurrent 0.7A | `dummy_robot.h:24-25` |
| FreeRTOS | 堆 65536B(.ccmram)、Tick 1000Hz、最大优先级 56 | `FreeRTOSConfig.h:68-71`、`main.c:58` |
| 栈大小 | 各任务 2000B，commTask **45000B**，OLED/RGB 2000B | `main.cpp:178-206`、`communication.cpp:22` |
| 构建 | STM32Cube FW_F4 **V1.26.1**，CubeMX，硬件 FPU，arm_cortexM4lf_math.a | `.ioc:353`、`CMakeLists.txt:25-27/102` |
| 链接 | Flash 1024K / RAM 128K / CCMRAM 64K | `STM32F405RGTx_FLASH.ld:62-67` |

**重要**：环境中**无 `cmake`、无 `arm-none-eabi-gcc`**（仅 `make` 存在）。因此**未做编译验证**，上述参数均来自源码静态读取，非编译产物或实物测量。

## 六、初稿必须修改的条目

1. 第 9.1/9.2 条：将 IMU 描述从"`main.cpp:165` 循环等待"升级为 **P0 级**——该循环在任务启动前，未贴 IMU 整机不运行；需给出"有限重试+超时跳过"或宏裁剪方案。
2. 第 8.2/第三阶段 Gate"CAN 掉线安全停止"：改为**固件当前不具备**此能力，是必须**新开发**的功能，不是默认已有（P1-2）。
3. 第 4/14 条急停：补充 `!STOP` 的真实行为缺陷（P0-1）与"物理急停开关直接切功率级"为强制项。
4. 第 10.3 条整机调试顺序：`!HOME`、`!CALIBRATION` 标注为**自动运动会撞限位**（P0-2），且 `!CALIBRATION` 末尾会 `Reboot()`。
5. 第 12 条 "高优先级"新增：`ascii_protocol.cpp` 位选 `&` 应为 `&&`（P0-4 b）；`jointSpeed=0` 导致 `MoveJ` 除零（P1-4）；逆解奇异依赖历史状态（P1-4）。
6. 第 2.2 条信号链/5 章：明确 200 Hz 为**REF 侧下发调度频率**，电机本环 20 kHz 在 `dummy-42motor-fw`（不在本审计范围），避免混淆。
7. 第 6 章采购：新增 USB-CAN（SocketCAN/candleLight 优先），因验证"节点超时失能"必须抓总线（P1-3）。

## 七、本领域分阶段执行建议（固件审计视角）

1. **阶段 0（立即）**：安装 arm-none-eabi 工具链 + cmake ≥3.19，先对 `dummy-ref-core-fw` 与 `dummy-42motor-fw` 做一次**原始源码编译**，留存 build log/固件 size，作为后续一切改动的基线（当前环境缺工具，须先补）。
2. **阶段 1（安全加固，改 REF）**：修复 P0-1 急停失能下发、P0-3 IMU 启动阻塞、P0-4 位选 `&&` 与节点 id 校验——这些是"上电即危险/不可用"项，优先于一切功能开发。
3. **阶段 2（通信鲁棒性）**：实现节点心跳超时→失能+报警、`IsMoving()` 超时看门狗、`jointSpeed` 下界钳位。硬件在环回归：单节点故意拔线，验证 1s 内失能且命令线程不卡死。
4. **阶段 3（运动安全）**：Homing/Calibrate 增加前置检查与可见确认；`MoveL` 增加奇异/可达性返回码；两轴最小化路径下重核 `initPose/currentJoints` 叠加（P2-1）。
5. **阶段 4（工程化）**：为 ASCII/fibre 危险命令加保护；EEPROM 双 bank 掉电保护；多 UART 通道解析缓冲独立（P2-3）。
每阶段均须以"单节点 CAN 记录 + 断电/拔线/错误 ID 注入"的回归验收收口，重点验证急停、超时失能、除零防护三类。

## 八、未验证事项与缺件（如实说明）

- **未做编译/烧录/运行**：环境缺 `cmake`、`arm-none-eabi-gcc`，无法产出固件或任何实测结果；所有结论为静态源码审计。
- **未接触实物**：无 REF 板、电机板、电机、IMU、OLED；减速比/方向/DH 单位为源码字面值，**未**经 CAD 或实物反向验证（尤其 J2/J4/J6 的 `inverseDirection=true` 是否与实物线序一致，必须在两轴阶段实测，否则 HOME/CALIBRATION 必然反向撞限位）。
- **未验证电机节点侧协议**：本审计范围为 REF 主控；`dummy-42motor-fw`（20kHz 环、MT6816、TB67H450、UART 命令 c/v/p、校准表）不在本次覆盖，需单独审计。
- **缺件**：无 ROS/URDF、无夹爪机械、无 J6 行星减速精确型号（初稿已识别）；0x23/0x25 之外 CAN 反馈帧无 CRC/序列号，链路级完整性依赖 CAN 本身与自定义协议，需实测确认。
- **`.ioc` 未核对项**：TIM7 Period/Prescaler 在 `.ioc` 为 9999/83，但运行时被 `Timer` 构造函数覆盖（`timer.cpp:30-39` 重新计算），依赖">=Normal 优先级+timer 回调"的时序正确性需在编译后通过逻辑分析仪验证 200Hz 实际周期。

（报告完）
