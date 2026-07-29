# Dummy Robot M0–M1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (- [ ]) syntax for tracking.

**Goal:** 建立可审计的 Dummy Robot V0 数字基线，并让两块 STM32F103 开发板通过实体 CAN 总线以 100 Hz 交换“目标角度/当前角度”，形成从读项目、读数据手册、写最小固件到仪器验收的第一个完整工程闭环。

**Architecture:** M0 只读原仓库的机械、硬件和固件资产，把“原始证据、工程推断、未知项”分开记录。M1 使用两块 NUCLEO-F103RB：节点 A 模拟 REF，产生目标角度并记录反馈；节点 B 模拟关节控制器，用限速模型生成当前角度。两节点经 SN65HVD230 实体 CAN 总线连接；GPIO/UART、PWM、ADC/DMA、SPI/MT6816 分别以独立最小工程学习，最后在 CAN 工程集成协议、日志和验收脚本。

**Tech Stack:** Git、Markdown/CSV、Python 3.10+ 标准库、GCC、FreeCAD 1.0+ 或已有 STEP/CAD 工具、STM32CubeMX 6.18.0、STM32CubeIDE 2.2.0 Eclipse 版、STM32CubeF1 1.8.0、STM32 HAL、NUCLEO-F103RB、SN65HVD230、MT6816、USB 串口、数字万用表、逻辑分析仪。

**Global Constraints:**

- M0–M1 不修改 `0.SubModules/` 至 `5.Docs/` 内的母本文件；根目录仅允许项目治理文件 `README.md`、`CONTRIBUTING.md` 和 `.gitignore`，其余新成果进入 `docs/reproduction/`、`learning/m1-embedded/` 和 `tools/reproduction/`。
- 只使用 USB/3.3 V/5 V 安全低压；本阶段不连接电机、24 V 电源、TB67H450 功率级或谐波减速器。
- 每个结论都标注 `evidence`（源文件/测量）、`inference`（基于证据的推断）或 `unknown`（尚需验证），不把推断写成原版事实。
- 每个实验必须先写预期和接线，后上电；任何改线都先断开 USB。
- 每一任务只有在测试命令通过、证据文件存在并写下结论后才提交。
- 版本号在开始执行时固定；若官方安装包不可获得，使用同一主版本的更新版，并在 `toolchain-lock.md` 记录实际版本与原因，不在 M1 中途升级。
- 本计划不按日历赶进度。阶段是否前进只看能力门和实测证据。

---

## File Map

计划执行后新增或生成以下文件：

```text
.gitignore
README.md
CONTRIBUTING.md
docs/reproduction/
├── README.md
├── templates/
│   ├── experiment-record.md
│   └── review-checklist.md
├── logs/
│   ├── decision-log.md
│   └── failure-log.md
├── m0/
│   ├── repository-inventory.csv
│   ├── assembly-tree.csv
│   ├── joint-parameters.csv
│   ├── mechanical-baseline.md
│   ├── electronics-board-map.csv
│   ├── connector-register.csv
│   ├── power-signal-flow.md
│   ├── firmware-control-flow.md
│   ├── v0-can-protocol.md
│   ├── software-assets.md
│   ├── bom-mechanical.csv
│   ├── bom-electronics.csv
│   ├── evidence-register.csv
│   ├── unknowns-and-risks.md
│   └── m0-review.md
└── m1/
    └── m1-review.md
learning/m1-embedded/
├── README.md
├── toolchain-lock.md
├── hardware/
│   ├── bench-bom.csv
│   ├── safety-checklist.md
│   └── wiring.md
├── common/
│   ├── angle_protocol.h
│   ├── angle_protocol.c
│   ├── mt6816_protocol.h
│   └── mt6816_protocol.c
├── tests/
│   ├── Makefile
│   ├── test_angle_protocol.c
│   ├── test_mt6816_protocol.c
│   └── test_validate_log.py
├── 01-gpio-uart/             # CubeMX/CubeIDE 工程及实验记录
├── 02-timer-pwm/             # CubeMX/CubeIDE 工程及实验记录
├── 03-adc-dma/               # CubeMX/CubeIDE 工程及实验记录
├── 04-mt6816-spi/            # CubeMX/CubeIDE 工程及实验记录
└── 05-can-angle/
    ├── node-a/               # 目标角度节点 Cube 工程
    ├── node-b/               # 当前角度节点 Cube 工程
    └── host/
        ├── requirements.txt
        ├── serial_logger.py
        └── validate_log.py
tools/reproduction/
├── inventory.py
├── test_inventory.py
└── validate_m0.py
```

CubeMX 自动生成的 `Core/`、`Drivers/`、启动文件、链接脚本和 `.ioc` 均随对应实验工程提交；`Debug/`、`Release/`、`.settings/` 等派生构建目录不提交。

## Fixed M1 Hardware and Interfaces

### Hardware choice

| 数量 | 器件 | 本阶段用途 | 验收前检查 |
|---:|---|---|---|
| 2 | ST NUCLEO-F103RB | 节点 A、节点 B；自带 ST-LINK、SWD 和虚拟串口 | 板号与主芯片为 STM32F103RBT6 |
| 2 | 3.3 V SN65HVD230 CAN 收发器模块 | 把 MCU CAN_TX/RX 转为差分 CANH/CANL | 确认不是 5 V TJA1050 模块；查清模块是否自带 120 Ω |
| 1 | MT6816 模块与轴向充磁的径向磁场磁铁 | SPI 角度读取 | 模块供电兼容 3.3 V；磁铁方向与安装间隙符合模块说明 |
| 2 | 120 Ω、1% 电阻 | 总线两端终端 | 断电测 CANH–CANL 总电阻约 60 Ω |
| 2 | 100 nF 陶瓷电容 | 收发器去耦 | 靠近每个收发器 VCC/GND |
| 1 | 10 kΩ 电位器 | ADC/DMA 实验 | 两端接 3.3 V/GND，滑端不超电源轨 |
| 1 | LED + 330 Ω 电阻 | PWM 实验 | LED 极性正确，串联限流 |
| 若干 | 面包板、杜邦线、USB 数据线 | 连接 | USB 线支持数据而非仅充电 |

建议在 M1 前购入温控焊台、数字万用表和 8 通道基础逻辑分析仪。示波器、实验室直流电源和 CAN 分析仪可推迟到 M2；M1 由 Nucleo USB 供电，不为买设备而制造额外前置条件。

### Pin contract

| 信号 | STM32 引脚 | Nucleo 接口 | 说明 |
|---|---|---|---|
| UART2_TX | PA2 | CN9 D1 | 默认接 ST-LINK 虚拟串口 |
| UART2_RX | PA3 | CN9 D0 | 默认接 ST-LINK 虚拟串口 |
| SPI1_SCK | PA5 | CN5 D13 | MT6816 时钟 |
| SPI1_MISO | PA6 | CN5 D12 | MT6816 数据返回 |
| SPI1_MOSI | PA7 | CN5 D11 | MT6816 读寄存器命令 |
| MT6816_CS | PB6 | CN5 D10 | 软件控制、低有效 |
| PWM | PB10 | CN9 D6 | TIM2_CH3，外接 LED/逻辑分析仪 |
| ADC | PA0 | CN8 A0 | ADC1_IN0，电位器滑端 |
| CAN_TX | PA12 | CN10 pin 12 | 接 SN65HVD230 D/TXD |
| CAN_RX | PA11 | CN10 pin 14 | 接 SN65HVD230 R/RXD |
| 3V3 | — | CN6 pin 4 | 传感器和 CAN 收发器供电 |
| GND | — | CN6 pin 6/7 | 两节点和收发器必须共地 |

### CAN bus contract

```text
Node A PA12 ──> transceiver A D      transceiver A CANH ───── CANH ───── transceiver B CANH
Node A PA11 <── transceiver A R      transceiver A CANL ───── CANL ───── transceiver B CANL
Node B PA12 ──> transceiver B D
Node B PA11 <── transceiver B R      120 Ω across H/L at A end and 120 Ω at B end
Both boards/transceivers share GND; each transceiver has 100 nF from VCC to GND.
SN65HVD230: VCC=3.3 V, GND=GND, RS=GND, Vref=NC.
```

CAN 固定为 500 kbit/s。72 MHz SYSCLK、36 MHz APB1 下使用 Prescaler=9、SJW=1 TQ、BS1=6 TQ、BS2=1 TQ，总计 8 TQ，采样点 87.5%。

### Learning CAN application protocol

| CAN ID | 方向 | 含义 | 周期 |
|---:|---|---|---:|
| `0x101` | A → B | 目标角度 | 10 ms |
| `0x181` | B → A | 当前角度 | 10 ms |

两种报文均为标准帧、数据帧、DLC=8：

| 字节 | 类型 | 含义 |
|---:|---|---|
| 0..3 | `int32_t`, little-endian | 角度，单位 mdeg，范围 -180000..180000 |
| 4..5 | `uint16_t`, little-endian | 单调递增序号，按 16 位回绕 |
| 6 | `uint8_t` | 状态；M1 正常为 0 |
| 7 | `uint8_t` | 字节 0..6 的 XOR |

CAN 本身已有链路层 CRC；这里的 XOR 不是安全机制，只用于练习应用层编码、离线测试和分层定位。

---

## Task 1: Establish the Reproduction Workspace

**Files:**

- Create: `.gitignore`
- Create: `docs/reproduction/README.md`
- Create: `docs/reproduction/templates/experiment-record.md`
- Create: `docs/reproduction/templates/review-checklist.md`
- Create: `docs/reproduction/logs/decision-log.md`
- Create: `docs/reproduction/logs/failure-log.md`

- [ ] **Step 1: Confirm a clean starting point**

Run:

```bash
git status --short
git log -1 --oneline
```

Expected: only the plan/spec edits for this planning commit are present before implementation begins.

- [ ] **Step 2: Add ignore rules for generated work**

Write `.gitignore` with:

```gitignore
# STM32CubeIDE derived output
Debug/
Release/
.settings/
.metadata/
*.launch

# Python
__pycache__/
*.py[cod]
.venv/

# Host-test output and captured raw data
learning/m1-embedded/tests/build/
learning/m1-embedded/**/captures/*.sal
learning/m1-embedded/**/captures/*.vcd
```

- [ ] **Step 3: Write the experiment template**

Every experiment record must contain these headings:

```markdown
# Experiment Record

- Date and operator:
- Git commit:
- Hardware and revision:
- Firmware project and build configuration:
- Instrument and settings:
- Safety boundary:

## Question
## Source Evidence
## Wiring
## Prediction
## Procedure
## Raw Data
## Result Against Acceptance Criteria
## Failure and Root Cause
## Mapping Back to Dummy Robot
## Decision and Next Action
```

When copying the template, replace the title with the concrete experiment name before committing the record.

- [ ] **Step 4: Define decision and failure log schemas**

`decision-log.md` fields: ID, date, decision, alternatives, evidence, consequence, revisit condition. `failure-log.md` fields: ID, symptom, reproduction, layer classification, measurements, root cause, correction, regression test.

Layer classification is exactly one of: `power`, `wiring`, `physical`, `peripheral`, `driver`, `protocol`, `application`, `toolchain`.

- [ ] **Step 5: Validate structure**

Run:

```bash
test -f docs/reproduction/templates/experiment-record.md
test -f docs/reproduction/logs/decision-log.md
test -f docs/reproduction/logs/failure-log.md
rg -n "Question|Prediction|Acceptance|Mapping Back" docs/reproduction/templates/experiment-record.md
```

Expected: all `test` commands exit 0; `rg` finds the four concepts.

- [ ] **Step 6: Commit**

```bash
git add .gitignore docs/reproduction
git commit -m "docs: scaffold reproduction engineering records"
```

## Task 2: Build a Reproducible Repository Inventory

**Files:**

- Create: `tools/reproduction/inventory.py`
- Create: `docs/reproduction/m0/repository-inventory.csv`
- Test: `tools/reproduction/test_inventory.py`

- [ ] **Step 1: Write the failing inventory test**

The test creates a temporary tree and asserts that inventory rows contain `path,top_level,extension,size_bytes,sha256`, use repository-relative POSIX paths, are sorted by path, and produce a 64-character SHA-256.

Run:

```bash
python3 -m unittest tools.reproduction.test_inventory -v
```

Expected before implementation: failure because `tools.reproduction.inventory` does not exist.

- [ ] **Step 2: Implement the inventory tool**

Requirements:

- walk only `0.SubModules`, `1.Hardware`, `2.Firmware`, `3.Software`, `4.Model`, `5.Docs`;
- skip `.git`, build directories and binary contents inspection;
- hash every file in 1 MiB chunks;
- emit UTF-8 CSV sorted by relative path;
- accept `--root` and `--output` arguments;
- exit nonzero if any of the six expected roots is missing.

- [ ] **Step 3: Make the unit test pass**

Run:

```bash
python3 -m unittest tools.reproduction.test_inventory -v
```

Expected: one or more tests report `OK`.

- [ ] **Step 4: Generate and inspect the real inventory**

```bash
python3 tools/reproduction/inventory.py --root . --output docs/reproduction/m0/repository-inventory.csv
python3 -c "import csv; p='docs/reproduction/m0/repository-inventory.csv'; r=list(csv.DictReader(open(p, encoding='utf-8'))); print(len(r), sorted({x['top_level'] for x in r}))"
```

Expected: a nonzero file count and all six source roots in the printed set.

- [ ] **Step 5: Record the important negative findings**

In `docs/reproduction/m0/unknowns-and-risks.md`, record with inventory evidence:

- native parametric CAD, formal drawings/tolerances/materials are absent;
- complete production BOM/CPL/Gerber coverage is absent;
- DummyStudio business source, URDF/ROS model and repository-level license are absent;
- Peak working tree is not initialized;
- dynamics and the 200 Hz trajectory path are not complete capabilities.

- [ ] **Step 6: Commit**

```bash
git add tools/reproduction docs/reproduction/m0/repository-inventory.csv docs/reproduction/m0/unknowns-and-risks.md
git commit -m "tools: inventory Dummy Robot source assets"
```

## Task 3: Reconstruct the V0 Mechanical Baseline

**Files:**

- Create: `docs/reproduction/m0/assembly-tree.csv`
- Create: `docs/reproduction/m0/joint-parameters.csv`
- Create: `docs/reproduction/m0/mechanical-baseline.md`
- Create: `tools/reproduction/validate_m0.py`

- [ ] **Step 1: Open the source model without altering it**

Open `4.Model/Dummy v164.step` in FreeCAD 1.0+ or the user's existing CAD system. Save no changes into `4.Model/`. Use the model tree, visibility isolation and section views to identify base, J1–J6, motor/drive covers, links, wrist and end interface.

- [ ] **Step 2: Create the assembly tree**

`assembly-tree.csv` columns are:

```text
item_id,parent_id,source_label,normalized_name,part_class,quantity,motion_relation,evidence_level,evidence_ref,notes
```

Rules:

- `item_id` is stable and hierarchical, such as `V0/J2/HOUSING`;
- `part_class` is one of `machined`, `printed`, `purchased`, `pcb`, `fastener`, `unknown`;
- `evidence_level` is one of `evidence`, `inference`, `unknown`;
- do not invent materials or tolerances when STEP metadata does not state them.

- [ ] **Step 3: Create the six-joint table**

`joint-parameters.csv` columns are:

```text
joint_id,node_id,parent_link,child_link,axis_in_parent,solver_parameter_m,reduction,inverse_direction,configured_limit_min_deg,configured_limit_max_deg,motor_class,source_ref,evidence_level,verification_action
```

Seed it from `2.Firmware/Core-STM32F4-fw/Robot/instances/dummy_robot.cpp` and independently check geometry in STEP. The required source-code baseline is:

```text
reduction: J1=50, J2=30, J3=30, J4=24, J5=30, J6=50
node/inverse/limits: J1=1/true/-170..170, J2=2/false/-73..90,
                     J3=3/true/35..180, J4=4/false/-180..180,
                     J5=5/true/-120..120, J6=6/true/-720..720
solver parameters in order: 0.109, 0.035, 0.146, 0.115, 0.052, 0.072 m
```

Do not silently call the six solver numbers DH parameters. Describe their semantic meaning only after reading the solver constructor and checking coordinate frames.

- [ ] **Step 4: Write the mechanical baseline narrative**

`mechanical-baseline.md` must explain:

- kinematic chain and wrist-axis relationship;
- motor-side encoder and harmonic-drive implication;
- which parts can be measured from STEP and which require drawings or physical samples;
- suspected output-support, bearing, cable-routing, base-stability and serviceability risks;
- how each risk will be tested at M3 before Rev.B freeze.

Include at least one labeled screenshot of the full assembly and one of the wrist axes in `docs/reproduction/m0/images/`. Screenshots are evidence, not dimension authority.

- [ ] **Step 5: Implement mechanical checks in `validate_m0.py`**

The validator must assert:

- joint IDs are exactly J1 through J6;
- node IDs equal `[1, 2, 3, 4, 5, 6]`, reductions equal `[50, 30, 30, 24, 30, 50]`, and inverse flags/limits match the constructor baseline;
- every joint has a nonempty `source_ref` and `verification_action`;
- every assembly row uses an allowed `part_class` and `evidence_level`;
- every referenced repository path exists unless the reference begins `measurement:`.

Run:

```bash
python3 tools/reproduction/validate_m0.py --root .
```

Expected: `mechanical checks: PASS`; other M0 sections may report `not yet checked` until their tasks are complete.

- [ ] **Step 6: Commit**

```bash
git add docs/reproduction/m0 tools/reproduction/validate_m0.py
git commit -m "docs: reconstruct V0 mechanical baseline"
```

## Task 4: Reconstruct Power, Electronics, and Control Flow

**Files:**

- Create: `docs/reproduction/m0/electronics-board-map.csv`
- Create: `docs/reproduction/m0/connector-register.csv`
- Create: `docs/reproduction/m0/power-signal-flow.md`
- Create: `docs/reproduction/m0/firmware-control-flow.md`
- Create: `docs/reproduction/m0/v0-can-protocol.md`
- Create: `docs/reproduction/m0/software-assets.md`
- Modify: `tools/reproduction/validate_m0.py`

- [ ] **Step 1: Map every board project**

Inventory Controller, Dangle, HandModule, LedRing, MotorDriver-20, MotorDriver-42, MotorDriver-57-unused, REF core and REF base. CSV columns:

```text
board_id,source_path,role,mcu,sensor,power_stage,transceiver,inputs,outputs,production_files,evidence_level,open_question
```

For MotorDriver-42 explicitly trace STM32F103CBT6, MT6816, two TB67H450FNG and SN65HVD232. For REF core explicitly trace STM32F405RGT6, CAN, USB/UART, OLED and MPU6050.

- [ ] **Step 2: Create the connector register**

Use one row per connector or external net. Columns:

```text
board_id,connector,pin,net,direction,voltage_domain,destination,source_ref,evidence_level,verification_method
```

Unknown pins remain literal `unknown` and receive a concrete verification method such as `open Altium schematic sheet X and trace net label` or `continuity-test first PCB`.

- [ ] **Step 3: Draw the two end-to-end flows**

`power-signal-flow.md` must explain power input → regulation → MCU/sensor rails → driver power output. `firmware-control-flow.md` must explain host command → Fibre/command parsing → REF motion logic → CAN → joint controller → encoder/current loop → feedback.

Every block links to a source path and symbol/function name. Mermaid is allowed, but the prose must remain understandable if Mermaid is not rendered.

- [ ] **Step 4: Document the original CAN protocol separately**

`v0-can-protocol.md` documents what the repository actually implements. It must not copy the M1 learning protocol into V0. For every frame or command include source file, identifier construction, payload encoding, units and recipient. Where code paths disagree or lack a specification, mark `unknown` and link the exact verification action.

- [ ] **Step 5: Document software assets and boundaries**

Explain what is available as source versus binary in CLI-Tool and DummyStudio; state that DummyStudio binary behavior may be used as a black-box comparison but is not a maintainable research interface.

- [ ] **Step 6: Extend and run validation**

Add checks that every board row has a source path and role, each connector row has a voltage domain and verification method, and all Markdown flow documents contain at least one repository source reference.

```bash
python3 tools/reproduction/validate_m0.py --root .
```

Expected: `mechanical checks: PASS` and `electronics/software checks: PASS`.

- [ ] **Step 7: Commit**

```bash
git add docs/reproduction/m0 tools/reproduction/validate_m0.py
git commit -m "docs: trace V0 electronics and control flow"
```

## Task 5: Close the M0 Gate

**Files:**

- Create: `docs/reproduction/m0/bom-mechanical.csv`
- Create: `docs/reproduction/m0/bom-electronics.csv`
- Create: `docs/reproduction/m0/evidence-register.csv`
- Create: `docs/reproduction/m0/m0-review.md`
- Modify: `tools/reproduction/validate_m0.py`

- [ ] **Step 1: Create two non-purchasing BOMs**

These are understanding BOMs, not order lists. Each row records subsystem, item/function, source evidence, known specification, unknown specification, Rev.B relevance and next verification. Do not add supplier links or prices for uncertain original parts.

- [ ] **Step 2: Consolidate the evidence register**

Columns:

```text
claim_id,subsystem,claim,evidence_level,source_ref,checked_by,check_method,confidence,next_action
```

`confidence` is `high`, `medium` or `low`; `unknown` claims cannot have `high` confidence.

- [ ] **Step 3: Perform two oral/written trace exercises**

Without opening the final diagrams, answer in `m0-review.md`:

1. A host MoveJ-style command passes through which software tasks, transports and control layers before physical motion?
2. Input power passes through which rails and devices before a motor winding is driven, and what protects each boundary?

Then reopen the sources, annotate every wrong or missing step, and link the correction to evidence.

- [ ] **Step 4: Run the complete gate validator**

```bash
python3 tools/reproduction/validate_m0.py --root . --require-complete
```

Expected:

```text
mechanical checks: PASS
electronics/software checks: PASS
evidence checks: PASS
M0 gate: PASS
```

- [ ] **Step 5: Review scope discipline**

Run:

```bash
git diff --name-only $(git merge-base HEAD master 2>/dev/null || git merge-base HEAD main)..HEAD
```

Expected: no M0/M1 implementation change under the six mother-project directories.

- [ ] **Step 6: Commit and tag**

```bash
git add docs/reproduction/m0 tools/reproduction/validate_m0.py
git commit -m "docs: pass Dummy Robot M0 architecture review"
git tag -a v0-digital-baseline -m "M0 V0 digital baseline passed"
```

## Task 6: Procure and Commission the M1 Low-Voltage Bench

**Files:**

- Create: `learning/m1-embedded/README.md`
- Create: `learning/m1-embedded/hardware/bench-bom.csv`
- Create: `learning/m1-embedded/hardware/safety-checklist.md`
- Create: `learning/m1-embedded/hardware/wiring.md`
- Create: `learning/m1-embedded/toolchain-lock.md`

- [ ] **Step 1: Write the purchase BOM before ordering**

Columns: item, exact requirement, quantity, required milestone, acceptance inspection, purchased model, supplier/order, received result. The first four fields are fixed by this plan; the last four are filled with actual purchasing evidence.

- [ ] **Step 2: Inspect hardware before power**

Photograph labels and both sides of each CAN/MT6816 module. Trace VCC, GND, D/R, CANH/L and termination with module documentation or continuity mode. Reject or reclassify any module whose schematic cannot be established.

- [ ] **Step 3: Perform the CAN resistance check while unpowered**

With both 120 Ω ends installed and all USB cables removed, measure CANH–CANL at the bus. Acceptance: 54–66 Ω. Measure 3V3–GND resistance on each assembled breadboard and record the stable reading; a near-zero or falling-to-zero reading blocks power-up.

- [ ] **Step 4: Freeze the toolchain**

Install and record:

- STM32CubeIDE 2.2.0 Eclipse edition;
- STM32CubeMX 6.18.0;
- STM32CubeF1 1.8.0;
- ST-LINK firmware shown by CubeProgrammer/IDE;
- host OS, Python and GCC versions.

Use official sources linked in the References section. Record installer SHA-256 when the downloaded file is retained.

- [ ] **Step 5: Verify both boards independently**

For each Nucleo board: enumerate ST-LINK, read device ID, erase, flash the ST board-example blink or a generated empty project, reset, and reconnect the debugger. Record board serial number as Node A or Node B.

- [ ] **Step 6: Commit**

```bash
git add learning/m1-embedded
git commit -m "docs: commission M1 embedded learning bench"
```

## Task 7: GPIO, UART, and SWD Minimum Project

**Files:**

- Create: `learning/m1-embedded/01-gpio-uart/01-gpio-uart.ioc`
- Create: generated CubeIDE project under `learning/m1-embedded/01-gpio-uart/`
- Create: `learning/m1-embedded/01-gpio-uart/experiment.md`

- [ ] **Step 1: Generate the project**

Board selector: `NUCLEO-F103RB`. Clock: HSE bypass from ST-LINK MCO, PLL x9, SYSCLK 72 MHz, APB1 36 MHz, APB2 72 MHz. Debug: Serial Wire. Configure PA5 as `LD2` output, PC13 as button input, USART2 asynchronous 115200/8-N-1 on PA2/PA3.

- [ ] **Step 2: Add application behavior in USER CODE blocks**

At 10 Hz transmit exactly:

```text
time_ms=%lu,button=%u,reset=0x%08lx\r\n
```

Toggle LD2 every 500 ms without `HAL_Delay()`; use elapsed `HAL_GetTick()` comparisons. Capture reset cause from `RCC->CSR` before clearing flags. All custom code remains inside Cube-generated USER CODE sections.

- [ ] **Step 3: Build and debug**

Set a breakpoint after clock/peripheral initialization, single-step one loop, inspect `HAL_GetTick()`, then run. Expected: zero compiler errors/warnings from user code, LD2 changes at 1 Hz full cycle, serial lines arrive at 10 Hz.

- [ ] **Step 4: Perform one deliberate fault**

Select the wrong serial baud once, record the garbled symptom under layer `toolchain` or `protocol`, restore 115200, and document why MCU execution was not the root cause.

- [ ] **Step 5: Regenerate safely**

Change only a GPIO label in CubeMX, regenerate, rebuild, and verify custom behavior survives. This proves correct use of `.ioc` and USER CODE regions.

- [ ] **Step 6: Commit**

```bash
git add learning/m1-embedded/01-gpio-uart
git commit -m "feat: add GPIO UART and SWD learning project"
```

## Task 8: Timer/PWM Minimum Project

**Files:**

- Create: `learning/m1-embedded/02-timer-pwm/02-timer-pwm.ioc`
- Create: generated CubeIDE project under `learning/m1-embedded/02-timer-pwm/`
- Create: `learning/m1-embedded/02-timer-pwm/experiment.md`

- [ ] **Step 1: Configure an independently generated project**

Reuse the 72/36/72 MHz clock tree and USART2. Configure PB10/D6 as TIM2_CH3 PWM. TIM2 clock is 72 MHz because APB1 prescaler is not 1. Set Prescaler=71, Counter Period=999, PWM Pulse=250, yielding 1 kHz and 25% duty.

- [ ] **Step 2: Start PWM and report calculated values**

Call `HAL_TIM_PWM_Start(&htim2, TIM_CHANNEL_3)` and emit one UART line per second containing timer input clock, PSC, ARR, CCR and predicted frequency/duty.

- [ ] **Step 3: Measure, do not infer from LED brightness**

Connect PB10 → 330 Ω → LED → GND and logic analyzer PB10/GND. Acceptance: measured frequency 990–1010 Hz and high-time duty 24–26%. Save analyzer screenshot/export and settings in `experiment.md`.

- [ ] **Step 4: Change duty at runtime**

Every two seconds cycle CCR3 through 100, 500, 900. Logic analyzer acceptance: 10±1%, 50±1%, 90±1%; frequency stays within 1%.

- [ ] **Step 5: Commit**

```bash
git add learning/m1-embedded/02-timer-pwm
git commit -m "feat: add timer PWM measurement project"
```

## Task 9: ADC/DMA Minimum Project

**Files:**

- Create: `learning/m1-embedded/03-adc-dma/03-adc-dma.ioc`
- Create: generated CubeIDE project under `learning/m1-embedded/03-adc-dma/`
- Create: `learning/m1-embedded/03-adc-dma/experiment.md`

- [ ] **Step 1: Wire a bounded analog source**

Connect 10 kΩ potentiometer ends to 3V3/GND and wiper to PA0/A0. Measure wiper voltage before connecting A0; acceptance is 0–3.3 V.

- [ ] **Step 2: Configure deterministic sampling**

Configure ADC1 channel 0, 12-bit right alignment, sample time 71.5 cycles, scan off, continuous off, external trigger TIM3 TRGO. Configure TIM3 update at 1 kHz and TRGO=Update. Configure DMA1 Channel1 peripheral-to-memory, halfword alignment, memory increment, circular mode, buffer length 64.

- [ ] **Step 3: Implement block processing**

Start DMA with a `uint16_t adc_samples[64]`, then start TIM3. Set half/full-ready flags in HAL DMA callbacks and compute min, max and integer mean outside interrupts. At 10 Hz print:

```text
adc_mean=%u,adc_min=%u,adc_max=%u,millivolts=%lu
```

Use `millivolts = mean * 3300UL / 4095UL`; label it an estimate based on nominal VDDA.

- [ ] **Step 4: Verify at three positions**

At low, middle and high potentiometer positions compare UART-estimated voltage with DMM. Acceptance: monotonic counts, no values above 4095, and absolute error below 100 mV at the middle position.

- [ ] **Step 5: Create and diagnose a controlled wiring fault**

Disconnect the wiper with USB removed, then power and observe unstable/floating readings; reconnect and verify recovery. Record it as a `physical` layer failure.

- [ ] **Step 6: Commit**

```bash
git add learning/m1-embedded/03-adc-dma
git commit -m "feat: add ADC DMA sampling project"
```

## Task 10: Test and Read the MT6816 over SPI

**Files:**

- Create: `learning/m1-embedded/common/mt6816_protocol.h`
- Create: `learning/m1-embedded/common/mt6816_protocol.c`
- Create: `learning/m1-embedded/tests/test_mt6816_protocol.c`
- Create: `learning/m1-embedded/04-mt6816-spi/04-mt6816-spi.ioc`
- Create: generated CubeIDE project under `learning/m1-embedded/04-mt6816-spi/`
- Create: `learning/m1-embedded/04-mt6816-spi/experiment.md`

- [ ] **Step 1: Write failing host tests for pure decoding logic**

Define:

```c
typedef enum {
    MT6816_OK = 0,
    MT6816_PARITY_ERROR,
    MT6816_NO_MAGNET
} mt6816_status_t;

uint16_t mt6816_build_read_word(uint8_t address);
mt6816_status_t mt6816_decode(uint16_t reg3_response,
                              uint16_t reg4_response,
                              uint16_t *raw_angle,
                              int32_t *angle_mdeg);
```

Tests must cover read words `0x8300`/`0x8400`, zero angle, a known quarter-turn raw angle of 4096, parity failure and no-magnet flag. Expected quarter-turn result: 90000 mdeg.

Run:

```bash
make -C learning/m1-embedded/tests test_mt6816
```

Expected before implementation: compile or link failure.

- [ ] **Step 2: Implement the protocol exactly as the mother firmware**

Read register commands are `(0x80 | address) << 8`. Form the 16-bit response as `low_byte(reg3) << 8 | low_byte(reg4)`. Even parity over all 16 response bits is valid; bit 1 is no-magnet; angle is bits 15..2. Convert with `(raw_angle * 360000L) / 16384L`.

- [ ] **Step 3: Pass host tests**

```bash
make -C learning/m1-embedded/tests test_mt6816
```

Expected: executable exits 0 and prints `mt6816 protocol: PASS`.

- [ ] **Step 4: Configure SPI hardware**

SPI1 master, full duplex, 16-bit, MSB first, software NSS, CPOL high, CPHA second edge, prescaler 8. At 72 MHz APB2 the SPI clock is 9 MHz, below the sensor's 16 MHz maximum. Configure PB6 as push-pull output, idle high. Wire D13/PA5→SCK, D12/PA6←MISO, D11/PA7→MOSI, D10/PB6→CS, 3V3 and GND. Add `../common` to the compiler include path and add `mt6816_protocol.c` as an Eclipse linked source pointing to `${PARENT-1-PROJECT_LOC}/common/mt6816_protocol.c`.

- [ ] **Step 5: Implement physical transfers**

For each register, drive CS low, call `HAL_SPI_TransmitReceive()` for one 16-bit word, then drive CS high. Retry a full two-register read up to three times only on parity failure. At 100 Hz print raw angle, mdeg, parity status and no-magnet status.

- [ ] **Step 6: Verify signal then mechanics**

First verify CS/SCK/MOSI with logic analyzer and no sensor interpretation. Then mount/center the magnet and rotate slowly through one revolution. Acceptance:

- decoded angle stays in 0..359978 mdeg;
- no-magnet remains false over the usable revolution;
- no discontinuity occurs except the expected 360°→0° wrap;
- accumulated unwrapped angle changes monotonically for a single-direction turn;
- parity errors are below 1 in 10,000 reads.

- [ ] **Step 7: Map the experiment back to Dummy**

Compare the minimum project to `mt6816_base.cpp`, `mt6816_stm32.cpp` and the original SPI configuration. Explain why motor-side single-turn sensing cannot directly observe harmonic-drive output backlash/compliance.

- [ ] **Step 8: Commit**

```bash
git add learning/m1-embedded/common learning/m1-embedded/tests learning/m1-embedded/04-mt6816-spi
git commit -m "feat: add tested MT6816 SPI learning project"
```

## Task 11: Define and Test the M1 Angle Protocol

**Files:**

- Create: `learning/m1-embedded/common/angle_protocol.h`
- Create: `learning/m1-embedded/common/angle_protocol.c`
- Create: `learning/m1-embedded/tests/test_angle_protocol.c`
- Create/Modify: `learning/m1-embedded/tests/Makefile`

- [ ] **Step 1: Write the public API and failing tests**

Use exactly:

```c
uint8_t protocol_checksum(const uint8_t *data, size_t length);
bool protocol_encode_angle_frame(int32_t angle_mdeg,
                                 uint16_t sequence,
                                 uint8_t status,
                                 uint8_t out[8]);
bool protocol_decode_angle_frame(const uint8_t in[8],
                                 int32_t *angle_mdeg,
                                 uint16_t *sequence,
                                 uint8_t *status);
```

Tests cover 0, -180000, +180000, rejection outside range, little-endian bytes, sequence 65535 and checksum corruption. Null pointers return false and never dereference.

Run:

```bash
make -C learning/m1-embedded/tests test_angle
```

Expected before implementation: failure.

- [ ] **Step 2: Implement explicit byte packing**

Do not cast packed structs or depend on host endianness/alignment. Pack and unpack each byte with shifts through unsigned integer types. XOR only bytes 0..6.

- [ ] **Step 3: Pass all common-code tests with warnings as errors**

The Makefile uses:

```make
CFLAGS := -std=c11 -Wall -Wextra -Werror -pedantic -I../common
```

Run:

```bash
make -C learning/m1-embedded/tests clean all
```

Expected: both protocol test executables exit 0.

- [ ] **Step 4: Commit**

```bash
git add learning/m1-embedded/common learning/m1-embedded/tests
git commit -m "test: define M1 CAN angle protocol"
```

## Task 12: Implement Node A and Node B CAN Firmware

**Files:**

- Create: `learning/m1-embedded/05-can-angle/node-a/node-a.ioc`
- Create: generated Node A CubeIDE project
- Create: `learning/m1-embedded/05-can-angle/node-b/node-b.ioc`
- Create: generated Node B CubeIDE project
- Create: `learning/m1-embedded/05-can-angle/experiment.md`

- [ ] **Step 1: Generate both projects with identical physical settings**

Use the established clock/UART settings. Configure CAN on PA11/PA12 at the fixed 500 kbit/s timings, normal mode, automatic retransmission enabled, auto bus-off enabled. Activate RX FIFO0 message-pending interrupt. In each CubeIDE project, add `../../common` to the compiler include path and add `angle_protocol.c` as an Eclipse linked source pointing to `${PARENT-2-PROJECT_LOC}/common/angle_protocol.c`; do not create copied protocol implementations.

- [ ] **Step 2: Configure exact acceptance filters**

Node A accepts only standard data ID `0x181`; Node B accepts only `0x101`. Use filter bank 0, 32-bit ID-mask mode, FIFO0 and activation enabled. Set `FilterIdHigh = accepted_id << 5`, `FilterIdLow = 0x0000`, `FilterMaskIdHigh = 0xFFE0`, and `FilterMaskIdLow = 0x0006` so all 11 identifier bits, IDE and RTR must match. Verify unrelated ID `0x123` does not increment the application receive counter.

- [ ] **Step 3: Implement Node A target generation**

Every 10 ms produce a triangular target between -90000 and +90000 mdeg at 30000 mdeg/s. With a 10 ms tick, change by 300 mdeg and reverse direction at the endpoints. Encode and send ID `0x101`; increment the 16-bit sequence after successful queueing.

On ID `0x181`, decode feedback, store current angle, feedback sequence and receive timestamp. Reject invalid checksum/range without updating state and increment a protocol-error counter.

- [ ] **Step 4: Implement Node B simulated joint**

On valid ID `0x101`, update target and last-command timestamp. Every 10 ms move current toward target with:

```c
error = target_mdeg - current_mdeg;
step = clamp(error, -1000, 1000);
current_mdeg += step;
```

Send current on ID `0x181`, echo the most recently received sequence, and set status bit 0 if command age exceeds 100 ms. On timeout, hold current rather than extrapolate.

- [ ] **Step 5: Add observable application state**

Node A emits this CSV header once and one row every 10 ms:

```text
time_ms,target_mdeg,current_mdeg,tx_seq,rx_seq,rx_age_ms,can_error,protocol_errors
```

Node B emits a human-readable status at 1 Hz on its own VCP. UART transmission must have a bounded timeout and must not occur in the CAN interrupt callback.

- [ ] **Step 6: Bring up the bus layer by layer**

1. Power off, wire both transceivers and common ground.
2. Confirm 54–66 Ω across CANH/CANL.
3. Power one board at a time and confirm 3.3 V rail.
4. Run both boards, inspect that CANH/CANL toggle differentially.
5. Check CAN error register/counters before interpreting payloads.
6. Only then inspect target/current values.

- [ ] **Step 7: Run fault-injection checks**

- remove one terminator: record changed resistance and whether communication still works on the short bench bus; do not call that configuration valid;
- disconnect CANL: confirm error counters or stale feedback indicate failure;
- unplug Node A: confirm Node B sets timeout status and holds;
- transmit ID `0x123` from a temporary debug build: confirm filters reject it;
- restore wiring and confirm clean recovery after reset.

- [ ] **Step 8: Commit**

```bash
git add learning/m1-embedded/05-can-angle
git commit -m "feat: exchange target and feedback over CAN"
```

## Task 13: Capture and Automatically Validate the 60-Second CAN Run

**Files:**

- Create: `learning/m1-embedded/05-can-angle/host/requirements.txt`
- Create: `learning/m1-embedded/05-can-angle/host/serial_logger.py`
- Create: `learning/m1-embedded/05-can-angle/host/validate_log.py`
- Create: `learning/m1-embedded/tests/test_validate_log.py`

- [ ] **Step 1: Write failing validator tests**

Use Python `unittest`. Construct deterministic passing rows in memory, then mutate copies to cover failures for short duration, stale feedback, nonzero CAN error, protocol errors, invalid headers and excessive RMS tracking error.

Fixed acceptance logic:

- exact CSV header from Task 12;
- at least 5,500 valid rows;
- final time minus first time at least 59,000 ms;
- after the first 500 ms, maximum `rx_age_ms` ≤ 50 ms;
- `can_error` and `protocol_errors` remain zero;
- target/current stay inside ±180000 mdeg;
- RMS target-current error after the first 1 s < 1500 mdeg.

Run:

```bash
python3 -m unittest discover -s learning/m1-embedded/tests -p 'test_validate_log.py' -v
```

Expected before implementation: import or assertion failure.

- [ ] **Step 2: Implement the validator as a library and CLI**

`validate_log.py` exposes `validate_rows(rows) -> list[str]`, returning an empty list on success, and a CLI that exits 0 with `M1 CAN log: PASS` or exits 1 printing each violated criterion.

- [ ] **Step 3: Pass the offline tests**

```bash
python3 -m unittest discover -s learning/m1-embedded/tests -p 'test_*.py' -v
```

Expected: all tests `OK`.

- [ ] **Step 4: Implement the serial logger**

Pin `pyserial==3.5` in `requirements.txt`. CLI arguments are `--port`, `--baud` (default 115200), `--seconds` (default 60), and `--output`. Ignore pre-header boot text, write the exact header once, flush at least once per second, and preserve malformed lines in a sibling `.rejects.log` file.

- [ ] **Step 5: Capture the physical run**

Create a virtual environment outside Git or under ignored `.venv/`, install requirements, then run using the actual Node A port:

```bash
python3 learning/m1-embedded/05-can-angle/host/serial_logger.py --port /dev/ttyACM0 --seconds 60 --output learning/m1-embedded/05-can-angle/captures/can-60s.csv
python3 learning/m1-embedded/05-can-angle/host/validate_log.py learning/m1-embedded/05-can-angle/captures/can-60s.csv
```

On Windows replace only the port value, for example `COM5`. Expected final line: `M1 CAN log: PASS`.

- [ ] **Step 6: Commit source, compact evidence, and result**

Keep the 60 s CSV if its size is reasonable; otherwise commit a deterministic decimated CSV plus SHA-256 and retain the raw file outside Git. Record hardware serials, wiring photo, logic-analyzer CAN capture, firmware commits and validator output in `experiment.md`.

```bash
git add learning/m1-embedded/05-can-angle learning/m1-embedded/tests
git commit -m "test: validate sustained M1 CAN exchange"
```

## Task 14: Close the M1 Gate and Retrospective

**Files:**

- Create: `docs/reproduction/m1/m1-review.md`
- Modify: `docs/reproduction/logs/decision-log.md`
- Modify: `docs/reproduction/logs/failure-log.md`
- Modify: `learning/m1-embedded/README.md`

- [ ] **Step 1: Run all software checks from a clean host-test build**

```bash
make -C learning/m1-embedded/tests clean all
python3 -m unittest discover -s learning/m1-embedded/tests -p 'test_*.py' -v
python3 learning/m1-embedded/05-can-angle/host/validate_log.py learning/m1-embedded/05-can-angle/captures/can-60s.csv
git diff --check
```

Expected: C tests pass, Python tests report `OK`, physical log reports `PASS`, `git diff --check` produces no output.

- [ ] **Step 2: Demonstrate independent fault isolation**

Select one previously recorded failure and repeat the diagnosis without reading its solution. In `m1-review.md`, show observations and elimination order across power → physical wiring → CAN peripheral → application protocol → application state.

- [ ] **Step 3: Answer the M1 competence questions**

Explain in the user's own words:

- why CAN needs a transceiver and two end terminations;
- how 36 MHz APB1 becomes the selected 500 kbit/s timing;
- why UART text success does not prove CAN success;
- how MT6816 register bits become millidegrees;
- what work belongs in an interrupt callback versus the main loop;
- how a `.ioc`, generated HAL layer, protocol module and application state differ;
- which M1 choices deliberately differ from original Dummy and why.

- [ ] **Step 4: Check the M1 gate**

The gate passes only if all are true:

- both boards can be erased, flashed and debugged through integrated ST-LINK;
- GPIO/UART, PWM, ADC/DMA and SPI experiments meet their numeric criteria;
- two physical CAN nodes run for 60 s and the automated validator passes;
- at least one hardware, one protocol/tooling and one application fault are recorded and correctly classified;
- user can create a new Cube project and explain the path from data sheet to measurement without copying the mother firmware blindly.

- [ ] **Step 5: Commit and tag**

```bash
git add docs/reproduction/m1 docs/reproduction/logs learning/m1-embedded/README.md
git commit -m "docs: pass M1 embedded capability review"
git tag -a m1-embedded-basics -m "M1 embedded basics passed"
```

- [ ] **Step 6: Stop before M2 purchasing**

Review the M1 evidence, original MotorDriver-42 schematic/PCB and procurement risk before writing the M2 plan. Do not order six motor drivers, motors or reducers at this gate. The next plan begins with one power-stage board and one motor/encoder bench only.

---

## Final Verification Before Declaring M0–M1 Complete

Run from the repository root:

```bash
python3 tools/reproduction/inventory.py --root . --output /tmp/dummy-inventory-check.csv
cmp /tmp/dummy-inventory-check.csv docs/reproduction/m0/repository-inventory.csv
python3 tools/reproduction/validate_m0.py --root . --require-complete
make -C learning/m1-embedded/tests clean all
python3 -m unittest discover -s learning/m1-embedded/tests -p 'test_*.py' -v
python3 learning/m1-embedded/05-can-angle/host/validate_log.py learning/m1-embedded/05-can-angle/captures/can-60s.csv
git diff --check
git status --short
```

Expected: inventory is reproducible, M0 gate passes, all host tests pass, the physical CAN log passes, whitespace check is empty, and working tree is clean after the final commit.

Manual evidence checklist:

- [ ] V0 full assembly and wrist-axis screenshots exist and are labeled.
- [ ] Both Nucleo serial numbers and toolchain versions are recorded.
- [ ] PWM waveform measurement exists with frequency and duty cursors.
- [ ] ADC/DMM three-point comparison exists.
- [ ] MT6816 raw and unwrapped one-revolution data exists.
- [ ] CANH/CANL termination resistance and logic capture exist.
- [ ] The 60-second physical CAN CSV and validator output exist.
- [ ] Decision/failure logs contain evidence and corrections.
- [ ] M0 and M1 reviews contain the user's own explanations, not only copied documentation.

## Authoritative References

- [STM32CubeIDE official product page](https://www.st.com/en/development-tools/stm32cubeide.html) — tool download and release information.
- [STM32CubeMX 6.18.0 documentation](https://dev.st.com/stm32cube-docs/stm32cubemx/6.18.0/en/index.html) — board/peripheral configuration and generated-code workflow.
- [STM32CubeF1 official package](https://www.st.com/en/embedded-software/stm32cubef1.html) — HAL/LL package version 1.8.0.
- [NUCLEO-F103RB product page](https://www.st.com/en/evaluation-tools/nucleo-f103rb.html) and [UM1724 Nucleo-64 manual](https://www.st.com/resource/en/user_manual/um1724-stm32-nucleo64-boards-mb1136-stmicroelectronics.pdf) — integrated ST-LINK/VCP, board power and connector pins.
- [STM32F103x8/B datasheet](https://www.st.com/resource/en/datasheet/stm32f103rb.pdf) and [RM0008 reference manual](https://www.st.com/resource/en/reference_manual/rm0008-stm32f101xx-stm32f102xx-stm32f103xx-stm32f105xx-and-stm32f107xx-advanced-armbased-32bit-mcus-stmicroelectronics.pdf) — electrical limits, clocks, GPIO, timers, ADC, SPI and bxCAN.
- [SN65HVD230 datasheet](https://www.ti.com/lit/ds/symlink/sn65hvd230.pdf) — 3.3 V CAN transceiver, pins, decoupling and ISO 11898-2 bus connection.
- [MT6816 official product page](https://www.magntek.com.cn/136/105) — 14-bit angle output, SPI timing and magnet status.
- Mother-project evidence: `README.md`, `2.Firmware/Core-STM32F4-fw/Robot/instances/dummy_robot.cpp`, `2.Firmware/Ctrl-Step-Driver-STM32F1-fw/Ctrl/Sensor/Encoder/mt6816_base.cpp`, `2.Firmware/Ctrl-Step-Driver-STM32F1-fw/Port/mt6816_stm32.cpp`, and the Altium projects under `1.Hardware/`.
