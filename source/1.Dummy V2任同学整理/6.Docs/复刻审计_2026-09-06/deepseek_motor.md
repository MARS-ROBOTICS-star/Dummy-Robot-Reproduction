> 原始子代理意见，保留用于审计追溯，不是执行依据。本文的 HSE、HAL DOUBLEWORD 等判断已被复核纠正；现场操作建议也不直接采纳。以 [审计结论与证据](审计结论与证据.md) 及根目录详细方案为准。

# Dummy V2 电机板固件审计报告（dummy-42motor-fw / dummy-35motor-fw）

**审计范围**：仅 `2.Firmware/dummy-42motor-fw` 与 `dummy-35motor-fw` 的全部自研代码（Ctrl / Port / UserApp / Core 外设与中断 / startup / 链接脚本 / CMake 构建），第三方（HAL/CMSIS）只查集成边界。全程只读，未编译、未烧录、未改动文件，未读取项目外凭据。

## 一、覆盖目录与实测关键文件

两固件目录结构完全一致（35 仅多无用的 `.DS_Store`）。实际逐行阅读的自研文件：

- `UserApp/main.cpp`、`configurations.h`、`common_inc.h`、`protocols/interface_uart.cpp`、`interface_can.cpp`
- `Ctrl/Motor/motor.{h,cpp}`、`motion_planner.{h,cpp}`
- `Ctrl/Driver/driver_base.h`、`tb67h450_base.{h,cpp}`、`sin_map.h`（引用）
- `Ctrl/Sensor/Encoder/encoder_base.h`、`mt6816_base.{h,cpp}`、`encoder_calibrator_base.{h,cpp}`
- `Ctrl/Signal/button_base.cpp`、`led_base.cpp`
- `Port/mt6816_stm32.{h,cpp}`、`tb67h450_stm32.{h,cpp}`、`encoder_calibrator_stm32.{h,cpp}`、`led_stm32.cpp`、`button_stm32.cpp`
- `Port/Platform/Memory/*`（`emulated_eeprom.{h,cpp}`、`eeprom_interface.h`、`stockpile_f103cb.{h,c}`、`stockpile_config.h`）
- `Port/Platform/Utils/st_hardware.{h,c}`、`Port/Platform/retarget.{h,c}`
- `Core/Src/{main,usart,can,tim,spi,gpio,adc,stm32f1xx_it}.c` 及对应 `Inc` 头
- `startup/startup_stm32f103xb.s`、`STM32F103CBTx_FLASH.ld`、`CMakeLists.txt`、`README.md`

第三方集成边界：`Drivers/STM32F1xx_HAL_Driver`、`Drivers/CMSIS` 未逐行审，仅确认宏定义（`HSE_VALUE` 默认 8MHz、`stm32f103xb` 器件、`FLASH_PAGE_SIZE=1K`）。

**35 与 42 的差异**：全目录递归 diff（排除 Drivers/.idea/启动）后，唯一实质差异是 `UserApp/main.cpp:45` 的默认 DCE 增益 `dce_kp`：42 为 `200`，35 为 `195`。其余自研源文件、链接脚本、启动文件、CMake **逐字节一致**。故下面所有发现（除已注明外）对两固件同样成立。

## 二、已确认事实与调用链

- **启动链**：`Reset_Handler → SystemInit → main() → HAL_Init → SystemClock_Config → MX_x_Init... → Main()`。
- **20kHz 闭环入口**：`main.c:104 Main()` → `HAL_TIM_Base_Start_IT(&htim4)` → `stm32f1xx_it.c:359 TIM4_IRQHandler → Tim4Callback20kHz()` → `main.cpp:149` → `motor.Tick20kHz()` → `motor.cpp:7` → `encoder->UpdateAngle()`（SPI 读 MT6816）+ `CloseLoopControlTick()`。
  - 位置展开/速度估计/状态机：`motor.cpp:29~355`；DCE 输出 `motor.cpp:382`；电流矢量 `tb67h450_base.cpp:10`。
- **100Hz 慢任务**：`main.cpp:121 Tim1Callback100Hz`（按钮/LED/温度节拍）。
- **UART**：USART1 重映射到 PB6/PB7，115200 8N1，DMA 循环收 + IDLE 中断分帧（`usart.c:49`、`stm32f1xx_it.c:374`），命令见 `interface_uart.cpp:8`（`c/v/p`）。
- **CAN**：1Mbit（Prescaler=4, BS1=5TQ, BS2=3TQ @72MHz），标准帧，filter 掩码全 0（放行所有 ID），软件判 `id==0||id==canNodeId`（ID0 即广播），`can.c:48/189`；命令解析 `interface_can.cpp:20`。
- **电流单位**：内部控制一律 **mA 整数**（`ratedCurrent=1000`、`caliCurrent=2000`），UART `c` 与 CAN 0x03/0x12 均 `atof/float ×1000` 转 mA；`GetFocCurrent()` 输出 `/1000`（A）。TB67H450 满量程映射 0~3300mA/12bit→10bit PWM（`tb67h450_base.cpp:18~24`）。
- **Flash 分区**（`stockpile_config.h` + `mt6816_stm32.h`）：校准表 0x08017C00（32K，16K 个 uint16）；参数 EEPROM 0x0801FC00（1K，`emulated_eeprom` 用末页 `FLASH_BASE_ADDRESS = 0x0801FC00`）。两套存储库地址一致、互不重叠。
- **默认模式/使能**：`main.cpp:40 defaultMode=MODE_COMMAND_POSITION`，`enableMotorOnBoot=false`；`motor.cpp:557` 上电 `requestMode = MODE_STOP`。未使能时 `CloseLoopControlTick` 走 `driver->Sleep()` 且清积分（`motor.cpp:96~103`）。
- **未校准保护**：`mt6816_base.cpp:3 Init()` 遍历 16384 点校验（0xFFFF 判无效）→ `IsCalibrated()` 决定 `STATE_NO_CALIB`，控制回读休眠（`motor.cpp:98`、`301`）。

## 三、P0 发现（安全/正确性阻塞项，需修复后再通电）

**P0-1 控制环实际频率不匹配（定时器频率疑点，固件假设 72MHz）**
- 证据：`tim4` Prescaler=71、Period=49；`tim1` Prescaler=71、Period=9999。`motion_planner.h:12 CONTROL_FREQUENCY=20000`、`CONTROL_PERIOD=50us`。
- 计算：若 HSE=12MHz（PLLMUL6→72MHz，APB1 定时器时钟 72MHz）则 TIM4=72e6/72/50=**20kHz**✓、TIM1=72e6/72/10000=**100Hz**✓。但 `system_stm32f1xx.c:78` 中 `HSE_VALUE=8000000`（默认，未被 hal_conf 覆盖），且 `main.c:136 PLLMUL=RCC_PLL_MUL6`→48MHz，此时 TIM4=**13.33kHz**、TIM1=**66.7Hz**。
- 触发：板上晶振实际频率决定一切；8MHz 晶振则整个控制环、速度估计、位置/速度积分（全用 `CONTROL_FREQUENCY=20000`）系统性偏慢 33%，堵转计时（`motor.cpp:277 stalledTime += CONTROL_PERIOD`）也随之失准。
- 影响：位置闭环增益、额定速度/加速度、堵转超时全部错误；低速可能振荡或失控保护失效。
- 修复：上电前用逻辑分析仪/示波器实测 TIM4 中断频率，据板上晶振修正 `HSE_VALUE` 或重新设计预分频；确认 CONTROL_FREQUENCY 与实际一致后再调参。
- 验收：示波器测 PB 电机 PWM 或 TIM4 中断脚，确认 20kHz（或按实测重标定）；阶跃响应不含系统性偏置。

**P0-2 noMag（无磁）状态未接入控制，磁铁脱落会盲目驱动**
- 证据：`mt6816_base.cpp:52` 解析出 `noMagFlag`，但全工程除赋值外无任何读取（`grep noMagFlag` 仅此一处）；`motor.cpp` 控制回读仅判断 `checksumFlag` 间接、`IsCalibrated()`，不读 `noMagFlag`。
- 触发：运行中磁铁松动/脱落，SPI 仍返回数据（校验可能通过），闭环用错误的 rectifiedAngle 继续驱动。
- 影响：电机飞转/大幅误动，机械损坏或伤人。
- 修复：在 `CloseLoopControlTick` 或 `UpdateAngle` 上报 noMag，触发 `MODE_STOP`+Sleep，并上报异常位/state。
- 验收：运行中拔磁铁/远离磁铁，电机应立即 sleep 且状态可判别（如 LED 或 UART 遥测）。

**P0-3 parity（奇偶校验）失败时角度静默保持旧值，无故障上报**
- 证据：`mt6816_base.cpp:25~47` 连续 3 次校验（奇数 `1` 计数为偶则成功 break），若全部失败，`angleData.rawAngle/rectifiedAngle` 沿用上一次值，且 `noMagFlag` 也只在成功分支更新。
- 触发：SPI 干扰/磁传感器噪声大时校验持续失败。
- 影响：位置冻结但实际已转，闭环产生错误的滞后/阶跃，estVelocity 出错。
- 修复：记录连续校验失败计数，超阈值强制 Safe 并置异常态。
- 验收：注入 SPI 坏帧，观察遥测相位/校验计数能正确上报而非静默。

## 四、P1 发现（高优先级，首月需验证/修复）

**P1-1 通信无超时/看门狗：断流后电机保持最后指令**
- `interface_uart.cpp`(c/v/p) 与 `interface_can.cpp`(0x01/0x03/0x04/0x05) 均直发目标，无命令超时监控；TrajectoryTracker 有 200ms 超时但仅用于 mode `MODE_COMMAND_Trajectory`，首月 UART 位置模式不经过它。断开串口/CAN 后电机不会自动停。初稿“断开命令源行为符合预期”需自行补充：至少用 `MODE_COMMAND_Trajectory` 或加看门狗。属首月必修。
- 修复：UART/CAN 增加命令存活超时→Stop/Brake；验收断流测试。

**P1-2 危险命令无门槛/无确认，易误触发**
- `interface_can.cpp` 0x02（DO Calibration）只置 `isTriggered=true`，立即满电流 2000mA 注入（`encoder_calibrator_base.cpp:143` `SetFocCurrentVector(goPosition, caliCurrent)`）；0x7e 擦配置、0x7f 重启、0x15 写 home 均无二次确认。未校准/误发即可使电机满流甩动。
- 修复：校准与擦除加重试/确认或按 ID 门控；首月 UART 不含校准则风险较低，CAN 阶段必须加门槛。
- 验收：误发 0x02 时电机不会突然满流转动。

**P1-3 校准电流默认 2000mA 与额定 1000mA 不一致，参数来源易误导**
- `main.cpp:44 calibrationCurrent=2000` 而 `currentLimit=1000`；`motor.h:16 caliCurrent=2000`、`:17 ratedCurrent=1000`。EEPROM 优先（`main.cpp:30` 起），源码默认在首次上电写一次后即失效。初稿“不得直接按默认 2A 校准”成立，需进一步强调首次上电前必须确认电机额定相电流并在写 EEPROM 前改保守值。
- 验收：读回并导出当前有效 EEPROM 参数表。

**P1-4 UART `p` 命令与 `v`/CAN 模式切换不一致**
- `interface_uart.cpp:35~39` 用 `requestMode = MODE_COMMAND_POSITION`（未调用 `SetCtrlMode`、未重置 `ratedVelocity`），而 `v` 与 CAN 分支会 `ratedVelocity=boardConfig.velocityLimit`。轻微，但会造成位置模式沿用被改小的 ratedVelocity。建议统一走 `SetCtrlMode`。

**P1-5 CAN 帧 DLC 未被强制校验，短帧读到残留数据**
- `txHeader.DLC=8` 后固定 8；`can.c:202` 用 `RxHeader.DLC` 传 `_len`，但 `interface_can.cpp` 多处读 `_data[4]`（`0x05/0x06/0x11...`）做 ACK/store 判断，DLC<5 时 `RxData[4]` 为上次残留值，会误触发 ACK 或持久化。低概率但需统一 DLC 约定。

**P1-6 QFN 温度/ADC 通道与 `motor_temperature` 半初始化**
- `main.cpp:56` 无条件 `enableTempWatch=false`，故上电后温度永不被采集（`Tim1Callback100Hz` 受其门控，`motor_temperature` 恒 0，CAN 0x25 返回 0）。与 `enableTempWatch` 的 EEPROM 字段语义冲突。若首月要做温升记录，需另加采样。

## 五、P2 发现（低优先级/需注意）

- **P2-1** `ApplyPosAsHomeOffset`(`motor.cpp:615`) 取 `realPosition % 51200`，多圈累计后设置 home 会丢圈信息；单圈内使用才正确。
- **P2-2** `GetSerialNumber()`(`st_hardware.c`) 计算后被丢弃（`main.cpp:20 serialNum` 未使用）。
- **P2-3** `Main()` 内 `for(;;)` 循环体 `encoderCalibrator.TickMainLoop()` 与 EEPROM commit/restore 处理放主循环，校准计算（`CALI_CALCULATING` 分支）实际在主循环而非中断，长计算会阻塞但不会破坏环（校准期本就禁用闭环）。
- **P2-4** `stm32f1xx_it.c` 中 `EXTI9_5`、`TIM3` 被 `return` 短路（`TIM3_IRQHandler`、`EXTI9_5_IRQHandler` 直接 return），SIGNAL_COUNT_DIR 计数/Step-Dir 输入当前被放弃；若要用 Step/Dir 模式需恢复。
- **P2-5** 链接脚本 `FLASH LENGTH=128K` 全量授权，但校准表/参数位于 0x08017C00 之后；若固件 `__etext` 增长越过 0x08017C00，会覆盖校准表且无编译期告警。建议加链接断言或缩小 `.text` 上界。
- **P2-6** `emulated_eeprom` 用 `FLASH_TYPEPROGRAM_DOUBLEWORD`（F1 不支持双字编程，实际 HAL 会降级/失败风险），建议核实该库在 F103 的实际写宽与 `stockpile_f103cb.c`（半字/字/双字混合）一致性。
- **P2-7** CMake `include_directories` 含不存在的 `Ctrl/LowLevel、Ctrl/MotorControl`（无害）；`add_definitions(-DSTM32F1 -DSTM32F1xx -DSTM32F103xB)` 与 `__MICROLIB` 与 retarget 的 `_write` 并存需注意 `--specs` 未显式给，构建选项是否真正生效需在真实编译时验证。

## 六、已确认参数表（源码默认，EEPROM 可覆盖）

| 参数 | 值 | 来源 |
|---|---|---|
| 控制环名义频率 | 20000 Hz（实际见 P0-1） | motion_planner.h:12 |
| 控制周期名义 | 50 µs | motion_planner.h:13 |
| 整步/细分数 | 200 × 256 = 51200/圈 | motor.h:45-47 |
| 编码器分辨率 | 2^14=16384，32K 校准表 | encoder_base.h:23 |
| 额定电流 | 1000 mA | motor.h:17 / main.cpp:41 |
| 校准电流 | 2000 mA | motor.h:16 / main.cpp:44 |
| 额定速度 | 30 圈/s | main.cpp:42 |
| 额定加速度 | 100 圈/s²（motor.h 里 ratedVelocityAcc=1000，main 覆盖为 100） | main.cpp:43 |
| DCE 增益 kp/kv/ki/kd | 200/80/300/250（35 为 195/80/300/250） | main.cpp:45-48 |
| PID（速度环） kp/ki/kd | 5/30/0 | motor.h:25-27 |
| 默认模式 | COMMAND_POSITION | main.cpp:40 |
| 上电使能 | false（STOP） | main.cpp:50 |
| 堵转保护/温度监视 | 默认 false | main.cpp:51,56 |
| UART | 115200 8N1，PB6/PB7，DMA+IDLE | usart.c:49 |
| CAN 波特率 | Prescaler4/BS1_5/BS2_3（@72MHz=1M，@48MHz=667k） | can.c:49-53 |
| SPI1 | 模式3、16bit、预分频8、PB3/4/5+PA15片选 | spi.c:40-47 |
| 电机桥 PWM | TIM2 CH3/CH4（PB10/PB11），46.875kHz@48MHz | tim.c:88-121 |
| 100Hz 慢任务 | TIM1（实测见 P0-1） | tim.c:48 |
| Flash 校准表/参数 | 0x08017C00(32K) / 0x0801FC00(1K) | stockpile_config.h:85-89 |

## 七、初稿必须修改/更新的条目

1. **§2.2/§4 的 "20 kHz" 与 "100 Hz" 未经验证**：增加"控制环名义 20kHz，实际随板上晶振缩放（8MHz 晶振=13.3kHz/66.7Hz；12MHz=20kHz/100Hz），首月必须先示波器实测"。
2. **§4.2 说 UART `c/v/p` 即可"位置闭环"**：补充前提——未校准会休眠保护、`p` 走 `requestMode` 且不失速即目标，但**无超时/看门狗**，断流不停机，首月必须先验证断流行为。
3. **§第 3 周遥测项**应把 `noMagFlag`、`checksumFlag`（parity 失败计数）一并列入，而不只是 `rawAngle/rectifiedAngle`（初稿已列 raw/rectified/noMag，需补 parity 失败计数与 noMag 未入环的说明）。
4. **§12 高优先级 "磁铁规格不完整，不能直接用默认 2A 校准"**：确认成立，补充"且默认额定仅 1A，校准/额定两档都在首次上电写 EEPROM 前确定"。
5. **§5 第 1 周 "不改源码构建"**：CMake `include_directories` 指向不存在的目录、`__MICROLIB` 与 retarget 并存的构建选项是否有效，需在真实构建日志中确认（当前环境无编译工具，无法验证——见"未验证"节）。
6. **§8 CAN 命令表**应注明：ID0 为广播；0x02 校准、0x7e 擦除、0x7f 重启为**无确认危险命令**，需门控。
7. **§9.1 说 REF `main.cpp:165` 等 MPU6050**：电机板固件无此逻辑（那是 REF 固件，不在本次审计范围），初稿表述已正确归属，无需改。

## 八、本领域（电机板固件）分阶段执行建议

1. **冻结与工具链（G0）**：建立只读副本+Git；实测板上晶振值 → 修正时钟认知（P0-1）。
2. **可观测最小闭环（G1·第1-3周）**：先只烧录+读编码器；用宏开关加 20~50Hz 遥测导出 raw/rectified/noMag/parityFail/state；手转一圈验证单调性、回绕、噪声。
3. **安全校准（第4周）**：先读回/改保守 EEPROM；物理断电；用极小 `c……`（≤额定 1A）验证 Sleep/Brake/小电流，再校（校准时满 2A）——务必先修 P0-3/P0-2 或在校准期人工盯守。
4. **闭环回归**：正反向、阶跃、慢速往返、冷启动、15min 低载；用逻辑分析仪核对 SPI 时序与 TIM4 周期；逐条验证 P0/P1 的回归验收。
5. **CAN（G2 之后）**：抓包解码 ID/DLC，验证广播 ID0、0x05 ACK、危险命令门槛与断流停机，再上第二板（35 固件除 dce_kp 外与 42 一致，可作为交叉对照样本）。

## 九、未验证项与缺件（如实说明）

- **未编译**：当前环境未安装 `cmake`、`arm-none-eabi-gcc` 等，无法构建、无法读 `map`/`size`，无法确认固件真实体积是否逼近 0x08017C00 校准表边界、`__MICROLIB`/retarget 是否真生效。
- **未用二进制解析工具**：仅源码静态审计，未运行任何程序。
- **板上晶振真实频率未确认**（P0-1 关键前提），Motor-42 原理图 `Power.SchDoc`/`MCU.SchDoc` 未在本审计范围展开验证，晶振值需查硬件资料。
- **未验证运行时行为**：所有 P0/P1 结论为源码推导，需实物+示波器/逻辑分析仪回归。
- 缺件：UART/CAN 无超时看门狗（P1-1）、noMag 未入环（P0-2）、parity 静默（P0-3）为当前阻塞项，建议按 P0→P1 顺序在首次上电前完成修复或至少建立物理断电与人工盯守流程。
