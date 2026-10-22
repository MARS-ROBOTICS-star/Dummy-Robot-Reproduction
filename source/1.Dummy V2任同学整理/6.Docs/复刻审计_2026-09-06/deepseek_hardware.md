> 原始子代理意见，保留用于审计追溯，不是执行依据。本文含有已发现的错误或过度断言，必须以 [审计结论与证据](审计结论与证据.md) 的复核裁定及根目录详细方案为准；不得直接据本文接线、投板、采购或使能电机。

以下为完整审计报告。

---

# Dummy V2 复制项目 —— 硬件/电子制造审计报告

**审计人身份**：项目审计专职子代理（只读，未改动任何文件、未运行任何可执行程序、未连接机器人、未读取项目外凭据）。无法解析 Altium 二进制、无法读取图片（模型不支持图像输入）、本机无 `arm-none-eabi-gcc`/`cmake`（经 `inventory` 与 typical 判断，未实测编译），均已在下文如实标注为"待 EDA/人工核验"，不凭文件名宣布可投产。

## 0. 覆盖目录与关键已读文件

**已系统清点的目录**：`1.Hardware/`（motor42、motor35、ref-controller、LedRing 全部子目录含 `PCB源文件/History`）、`5.Bom/`（1 个 xlsx）、`6.Docs/`（接线/引脚/芯片资料/减速器参数/DH 参数/复刻审计目录）。

**实际解析并读取的关键文件（非仅 ls）**：
- `1.Hardware/motor42/Motor-42.html` → 用 `LZString` 解码出 `pcbdata` IBOM（82 个 footprint，含顶层/底层焊盘坐标与层属），得到完整器件清单与层分布
- `1.Hardware/motor35/Motor-35.html`、`ref-controller/REF-Base.html` → 同上解码，得到三块板 BOM
- `motor42/motor42 Gaber.zip`、`motor35/motor35 Gaber.zip`、`ref-controller/ref-controller-gerber.zip`、`LedRing/led gaber.zip` → 列目录逐一核对 Gerber 层与钻孔文件
- `Motor-42（焊盘更改版）.rar`、`Motor-35（焊盘更改版）.rar`、`REF_V1.01.zip` → 仅 `7z l` 列目录，确认内含单文件 PcbDoc/SchDoc（未解压、未解析）
- `6.Docs/复刻审计/extracted/dummy V2版本_bom.json`（= `5.Bom/dummy V2版本_bom.xlsx` 全量转出，5 个 sheet：REF/Motor-42/Motor-35/部分淘宝购买版123元/一键购买版443元）
- `6.Docs/芯片说明/ME3116.pdf`、`SY8090.pdf`、`LP2992.pdf`、`OLED 13H.pdf`、`STM32F405.pdf`（提取文本）
- `6.Docs/Cable_connection.pdf`、`Pins definations.pdf`、`dummy使用指南v1.3.pdf`（提取文本）
- 固件交叉取证（只读）：`2.Firmware/dummy-42motor-fw/Core/Src/can.c`、`stm32f1xx_hal_conf.h`、`Ctrl/Driver/tb67h450_base.cpp`（确认 CAN 时序/晶振/电流采样换算，属硬件关联证据）

**未解析（Altium 二进制）**：`*.SchDoc`、`*.PcbDoc` 均为 `Composite Document File V2`（OLE），本环境无 Altium/编辑器，标为**待 EDA 核验**。

---

## 1. 三类板型号与电源树（已确认）

| 板 | MCU | 供电拓扑（器件证据） | 驱动/编码器/CAN |
|---|---|---|---|
| **Motor-42** | STM32F103CBT6 (LQFP-48, U3) | 24V → SS54(反接 D1)+SMBJ28CA(TVS D2) → **ME3116** 高压DC-DC(SOT23-6 U6, L1=6.8uH) → **LP2992 3V3** LDO(U7) | 2×TB67H450FNG(U1/U2, SO-8-PAD) · MT6816(U8, SO-8) · SN65HVD232D(U5) · 120R R12 |
| **Motor-35** | STM32F103CBT6 (U3) | 同上（ME3116 U6 + LP2992 U7 + SS54 D1 + SMBJ28CA D2） | 2×TB67H450FNG · MT6816(U8) · SN65HVD232D(U5) · 120R R12 |
| **REF-Base** | STM32F405RGT6(LQFP-64 U12) | 24V → SS54 + SMBJ28CA → **ME3116** → 再经 **SY8089 2A**（SOT23-5 U3, L2=2.2uH；SY8089 为 2.7–5.5V/2A 同步降压，供 ESP32/1.8V 等） | CP2102(U1 USB-UART)、ESP32_SIP(U2)、NRF24L01(U7)、MPU6050(U10)、OLED-12880、SN65HVD232D(U11)、**R24=120R/NC（默认不贴）** |

证据：IBOM `bom.both` 全部行 + `5.Bom` REF/Motor-42/Motor-35 三个 sheet；ME3116 手册"最高输入 40V、带载 1A"（`ME3116.pdf.txt:2-7`）；SY8089 手册"2A continuous/3A peak, 2.7-5.5V"（`SY8090.pdf.txt:8-10`）。

---

## 2. 制造文件清点与放行矩阵

**Gerber/钻孔/贴片坐标清点结果：**

| 板 | Gerber 层文件 | 钻孔文件 (.TXT/.DRR/.LDP) | 独立贴片坐标(CPL/PNP/.pos) | 结论 |
|---|---|---|---|---|
| Motor-42 | 有（4 层：.GTL/.G1/.G2/.GBL + 丝印/阻焊/钢网/分割层等 27 文件，`motor42 Gaber.zip`） | **缺**：zip 内仅有 `.RUL`（布线层），无 `.TXT`/`.DRR`/`.LDP` | **无** | **Gerber 可制裸板，但缺钻孔数据→不可直接投产** |
| Motor-35 | 有（.GTL/.GBL/.GBO/… 共 34 文件，含 .TXT/.DRR/.LDP 钻孔） | 有 | **无** | **制造资料基本完整，可制裸板** |
| REF-Base | 有（`ref-controller-gerber.zip` 含 Gerber+钻孔，66 文件，另含 `REF_V1/Design Rule Check` HTML/DRC） | 有 | **无**（`PnPout/` 内仅 `REF-Base.html`，非 CPL） | **Gerber+钻孔齐全，可制裸板** |
| LedRing | 有（`led gaber.zip` 33 文件，含 .TXT/.DRR 钻孔） | 有 | 无 | 可制裸板 |

**关键安全阻塞（P0）**：三块板均**没有任何机器可读的贴片坐标文件（CPL/PNP）**；Motor-42 的 Gerber 包**还缺钻孔文件**。因此"现成 Gerber 可制裸板"只对 Motor-35/REF/LedRing 成立；Motor-42 需重新从 `Motor-42.PcbDoc` 输出钻孔，全部板需从 PcbDoc 输出或手工整理 CPL 才能委外贴片。（初稿 §12 已提到贴片 BOM/CPL 需重做，与此一致，但未点出 Motor-42 钻孔缺失。）

---

## 3. 分险发现（P0/P1/P2）

### P0（阻塞制造/可能损坏硬件）

- **P0-1 无贴片坐标(CPL)文件**。证据：全仓 `file_inventory.csv` 无 `.cpl/.pnp/.pos`（`grep` 仅命中 4 个 `.html`）；REF `PnPout/` 仅 HTML。触发条件：委外贴片/上钢网即被卡。影响：无法核对元件位号-坐标-角度，无法贴片。修复：用 Altium 从 PcbDoc 导出 CPL 后逐位号核对；回归验收：CPL 坐标/角度与 IBOM 焊盘层（F/B）逐条比对一致。
- **P0-2 Motor-42 Gerber 缺钻孔层**。证据：`motor42 Gaber.zip` 清单 31 文件，仅 `.RUL` 无 `.TXT/.DRR/.LDP`（Motor-35 与 REF 均含）。触发条件：拿此 zip 直接下单打样。影响：厂商无法钻孔或按默认补偿出错。修复：从 `Motor-42.PcbDoc` 重出 NC Drill；回归验收：新钻孔与 `.GG1/.GM13` 孔位对齐。
- **P0-3 版本一致性风险：Gerber(2024-03-24) 早于"焊盘更改版"PcbDoc(2024-07-17)**。证据：Motor-42/Motor-35 各自 `Gaber.zip` 生成时间 3/24，而同目录 `（焊盘更改版）.rar` 内 PcbDoc 时间 7/17（`unrar l`）。触发条件：拿旧 Gerber 下单、用新 PcbDoc 做 CPL/BOM，二者焊盘（"焊盘更改版"）不一致。影响：器件贴装后断连/短路。修复：冻结单一版本，重新统一导出 Gerber+钻孔+CPL+BOM 四件套；回归验收：校验和与版本号一致。
- **P0-4 连接线方向/电源-CAN 共线 6 针，接错直接损坏**（已由文档确认，非推断）。证据：`Cable_connection.pdf.txt`"只有第一条线是同向线，其余都是反向线"；`dummy使用指南v1.3.pdf.txt:21`"Ref to j1 使用同向线，需要交换中间两根 canbus 线，剩下 j1 至 j6 都使用反向线"；`:27`"电源线两根一组"；`:38`"6pin 接口 24V 在 IN 侧(实际左边)"。触发条件：REF→J1 线序与 J1→J2…j6 不同，6 针中 24V(×2) 与 CAN_H/CAN_L 同束。影响：24V 灌入 CAN 收发器或 MCU → 烧板。修复/验收：首板量 6 针逐针线序表+上电前通断校验，REF→J1 必须换中间两针；单轴阶段严禁用 REF 线接 Motor 板。
- **P0-5 电机额定电流/绕组参数/磁铁规格未定，原始校准电流 2000mA 不可直接用**。证据：初稿 §5/§12；驱动换算 `tb67h450_base.cpp:48`"0.1Ω 采样 V-ref 0~3300mV ⇔ 0~3300mA"（即默认校准电流按 2000mA≈2A 对应 V-ref）。触发条件：在校定电机前以默认 2A 执行校准/驱动。影响：过流发热/退磁/损伤驱动。修复：先测/查 42×40 电机额定相流、绕组电阻电感、磁铁规格，写保守值进 EEPROM 前。验收：校准前 EEPROM 电流 ≤ 额定值。

### P1（影响进度/正确性，需专项处理）

- **P1-1 CAN 终端 120R 拓扑：电机板 R12=120R（贴装），REF R24=120R/NC（默认不贴）**。证据：Motor IBOM R12=120R（F 层，BOM 备注无 NC）；REF BOM `"120R/NC", R24`。影响：6 节点链式 CAN 终端数量/位置须与拓扑匹配，多终/少终导致总线不稳定（初稿 §7.2 提到 120Ω 终端但未给默认贴装状态）。修复：验收时核对"仅总线两端的 120R 贴装、其余节点不贴"。
- **P1-2 晶振频率标注歧义**。证据：BOM"一键购买版"同时含 8MHz（X32258MSB4SI）与 12MHz（X322512MSB4SI，`bom.json` 行 C2682774/C9002）；而 `dummy-42motor-fw/Core/Inc/stm32f1xx_hal_conf.h:86` 为 `HSE_VALUE 12000000U`（12MHz）。影响：若按 8MHz 采购/焊接而固件按 12MHz，则 UART/CAN/计时全错。属于电机/RMC 硬件-固件联动项，需人工核对最终选定晶体的频率与哪块板（REF/F405 常 12M 或 8M）。
- **P1-3 REF OLED 接口/型号疑点**（初稿 §12 中优先级已提）。证据：BOM REF 行 `"OLED-12880"`（备注链接 0.78″ SH1107 SPI，`bom.json` 行 A72）；固件侧指南歧义。影响：接口(SPI 4线)/分辨率 128×80 vs 固件假设需核对。
- **P1-4 ME3116 只有 1A**：REF 板 ESP32+外设经 SY8089 再降压；SY8089 输入限 5.5V，故 SY8089 前级必然是 ME3116 的 ~5V 轨。需 EDA 确认 ME3116 输出标称电压及其能否支撑 REF 满载（含 OLED/NRF/MPU）。属"能自证但须原理图级验证"项。

### P2（记录/提醒，不阻塞）

- **P2-1 Hub 重复/复制文件**：`inventory_summary.json` 显示 Motor-35 与 Motor-42 的 MCU.SchDoc、Port.SchDoc 完全相同（`duplicate_groups` 内本条）。提醒：两板 MCU/端口拓扑一致，但不可据此假设 Drive/Power 也一致，仍需分别核对。
- **P2-2 减速器/传动比、DH 尺寸、J6 行星比、42-34/42-40 混用、线缆方向**等初稿 §12 已列条目，本审计在硬件文档内**无法进一步证实**（`mini11/mini8_parameters.JPG`、`DH参数.png` 为图片，本模型不可读；`Pins definations.pdf` 正文为整页图片，无文本）。标记为"需人工/EDA 核验"。
- **P2-3 历史备份**：motor42 `History/` 有 24 个 `PcbDoc.Zip` 版本、motor35 有 3 个、REF 有 2 个——版本演进未收敛，印证 P0-3 冻结版本必要。

---

## 4. 已确认参数表（凭文档/固件证据，非实测）

| 参数 | 值 | 证据来源 |
|---|---|---|
| 电机板 MCU | STM32F103CBT6 (LQFP-48, 128K/20K) | IBOM U3 / BOM |
| REF MCU | STM32F405RGT6 (LQFP-64) | IBOM U12 / BOM |
| 双驱动 | 2× TB67H450FNG (SO-8-PAD) | IBOM U1/U2 |
| 电流采样 | 0.1R(1206)×2；V-ref 0–3.3V ⇔ 0–3300mA | BOM R3/R8 / `tb67h450_base.cpp:48` |
| 编码器 | MT6816 (SO-8, 14 位磁角) | IBOM U8 / 固件 `mt6816_base.cpp` |
| CAN 收发器 | SN65HVD232D ×1/板 | IBOM U5/U11 |
| CAN 位时序 | SJW=1TQ, BS1=5TQ, BS2=3TQ | `can.c:51-53` |
| CAN 终端 | 电机板 120R 贴装；REF 120R/NC | IBOM R12 / REF BOM R24 |
| 主降压 | ME3116 (≤40V, 1A, 550kHz) | ME3116.pdf |
| 逻辑 LDO | LP2992 3V3 (SOT23-5) | IBOM U7 |
| REF 二次降压 | SY8089/89A 2A (2.7–5.5V, SOT23-5) | SY8090.pdf |
| 输入保护 | SS54(SMA) + SMBJ28CA(SMB, 28V CA) | BOM D1/D2 |
| 连接器 | ZH1.5 6P（P1/P2 主链路，P3 烧录口），3P（REF P3） | IBOM / 使用指南 |
| 温度传感 | NCP15XH103F03RC 10k NTC(0402) | BOM R4 |
| 拨码 | DSHP04TSGER 4 位（节点 ID） | BOM S1 |
| 层数 | Motor 板 4 层（GTL/G1/G2/GBL） | Gerber EXTREP |

---

## 5. 初稿必须修改的条目（硬证据驱动）

1. **§2.1** "REF、Motor-42、Motor-35… Gerber 和 HTML"表述过宽——应改写为：Motor-42 **Gerber 缺钻孔、三板均缺 CPL**，不能宣布"制造资料齐全"。
2. **§5 第 2 周任务 3/4**："仓库现成 Gerber 可制裸板，但没有 Motor-42 独立贴片坐标"→ 补正为"Motor-42 Gerber 包还缺钻孔文件，需从 PcbDoc 重出"。
3. **§4.2/§5** 关于"原始校准电流 2000mA"已在初稿点出，但可加一句量级依据：驱动换算为 0.1R 采样、V-ref 3.3V ⇔ 3.3A 满量程，2A 对应约 2/3 满量程。
4. **§12 高优先级** "Motor-42 现成 Gerber 可制裸板"需改为精确表述（见上）。
5. **§12 中优先级** 补一条 P0 级：**Motor-42/35 的 `（焊盘更改版）.rar`(2024-07) 新于 Gerber(2024-03)**，下单前必须冻结版本并重出 Gerber+钻孔+CPL+BOM 四件套。
6. **§6.2 单轴实物批** "连接器 ZH1.5、22AWG" 应强调：REF→J1 与其余链路线序**方向相反且中间两针 CAN 需交换**（初稿 §12 已提"线缆方向不同"，可提升到采购前必读）。

---

## 6. 本领域分阶段执行建议

**第一阶段（制造放行前，纯数字）**
1. 冻结所用 PcbDoc 版本（选"焊盘更改版"还是旧 gerber，二选一）。
2. 在 Altium 中从选定 PcbDoc 统一导出 Gerber、NC Drill、CPL(含元件角度/层)、BOM 四件套，四件套校验和互锁。
3. 用 IBOM 焊盘坐标（我已在 `m42.json/m35.json/ref.json` 给出 F/B 层）与 CPL 逐一比对。
4. 补 Motor-42 钻孔层，核对孔位表(.DRR)。

**第二阶段（单轴最小闭环，对应初稿首月）**
5. 首板只买 Motor-35 或委外 Motor-42（资料更全者优先），Motor-42 裸板在钻孔补齐前不下单。
6. 采购前把"42×40 电机额定相流/绕组/磁铁"落实，EEPROM 电流设为保守值再校准。
7. 6 针线序逐针核对表 + 上电前通断/方向校验；REF 不在单轴阶段接入。

**第三阶段（扩展到 CAN/多节点）**
8. 确认 120R 终端只贴总线两端节点。
9. 复核晶振频率(8M/12M)与固件 `HSE_VALUE` 一致后再量产。

---

## 7. 未验证与缺件（如实申报）

- **Altium 原理图/PCB 全量未能核验**：`*.SchDoc/*.PcbDoc/*.PrjPCB` 为 OLE 二进制，本机无解析器——所有网表级连性（每个电容/电阻两端接哪条网、GND 归属、24V 走线路径）均**未验证**，标"待 EDA 核验"。
- **无贴片坐标(CPL)**（P0-1）、**Motor-42 无钻孔**（P0-2）——已述。
- **MT6816、TB67H450FNG 的数据手册不在仓库**（`6.Docs/芯片说明/` 仅有 LP2992、ME3116、SY8090、OLED、STM32F405、MT6050 陀螺仪文本）；电机板两块核心芯片规格需另行获取。
- **图片类资料本模型不可读**：`减速器参数/mini8、mini11 JPG`、`DH参数.png`、`Pins definations.pdf`（整页图片）、`PCB/*.jpg` 实拍图——传动比/引脚定义/实物核对依赖人工。
- **编译工具链未实测**：本机未见 `arm-none-eabi-gcc/cmake`（符合初始环境描述），固件可构建性此处**未验证**，初稿动作 1"完成 Motor-42 首次构建"仍待执行。
- **无任何测试结果可引用**：本审计未上电、未焊接、未仿真，报告中一切"参数/拓扑"均来自文档与固件源码证据，不构成实物验证。

**结论**：三块板器件型号、电源树、驱动/编码器/CAN 拓扑、连接线方向均已凭文档证据交叉确认，**但制造层面存在两个 P0 阻塞（无 CPL、Motor-42 缺钻孔）与一个 P0 版本一致性风险**，加上接错线/默认 2A 校准两个 P0 安全隐患——在这些解除前，不能宣布"可投产"，只能停留在"可制 Motor-35/REF/LedRing 裸板"层面，且贴片仍需补齐 CPL。
