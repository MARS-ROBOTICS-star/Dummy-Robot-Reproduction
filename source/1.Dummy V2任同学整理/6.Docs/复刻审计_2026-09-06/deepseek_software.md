> 原始子代理意见，保留用于审计追溯，不是执行依据。本文对 GPL 商用、fibre 源码、VID、simple-cli 适用对象和两种校准有误判或过度推断；以 [审计结论与证据](审计结论与证据.md) 为准，不直接使用本文的操作或法律结论。

Now I have everything. Writing the final report.

---

# Dummy V2 项目软件/固件专项审计报告

受委托子代理（DeepSeek V4 Pro），仅执行只读审计，未运行项目程序、未连硬件、未改动任何文件。审计期间系统未配置 arm-none-eabi 交叉工具链、未安装 ESP-IDF，**所有"能否编译/运行"结论均基于源码静态分析，未实际编译验证**，特此先行声明。

## 一、覆盖目录与已读关键文件

**实际覆盖**：`3.Software/` 全目录、`2.Firmware/esp32-iot/` 全目录、`2.Firmware/{dummy-42motor-fw, dummy-35motor-fw, dummy-ref-core-fw, Dummy 源码注释}/` 主线源文件、根 `README.md`、根 `LICENSE`、`dummy使用指南v1.3.pdf`（经 extracted 文本核对）、`6.Docs/复刻审计_2026-09-06/` 清单与 extracted 资料（仅作索引，均已回溯原始文件）。

**已逐行读过的关键文件**：`run_shell.py`、`ref_tool/__init__.py`、`ref_tool/shell.py`、`ref_tool/configuration.py`、`fibre/__init__.py`、`simple-cli/simple-cli.py`、`chatgpt_gui.py`、`DummyStudio_Data/StreamingAssets/serial_config.txt`、`app.info`、`esp32-iot/{README,firmware/README,firmware/LICENSE,firmware/Makefile}`、`examples/{uart-bridge,esp32/uart-bridge}/{main.c,net.c,cli.c,wifi.c,config.json,Makefile}`、`src/{device_dummy.c,config.h}`、`42motor-fw/{main.cpp, interface_uart.cpp, interface_can.cpp, CMakeLists.txt, README, mt6816_base.cpp}`、`ref-core-fw/{main.cpp, ascii_protocol.cpp, dummy_robot.cpp, CMakeLists.txt}`。

## 二、P0 级发现（安全/阻塞，必须处理）

**P0-1 ESP32 网络串口桥无认证，可远程控制机械臂电机总线**
证据：`esp32-iot/firmware/examples/uart-bridge/net.c:6-8` 默认监听 `tcp://0.0.0.0:4001`、`ws://0.0.0.0:4002`（esp32 版 main.c:7 用 `:80`），并 `DEFAULT_MQTT = mqtt://broker.hivemq.com:1883?tx=dummy/tx&rx=dummy/rx`；`config.json` 直接 `enable:true` 启用 MQTT 且主题为公开可订阅的 `dummy/tx`、`dummy/rx`。`main.c:212-216` 的 `mg_http_match_uri(hm,"/api/config/set")` 接口无鉴权即可改写 UART 端口/代理地址。
触发条件：设备联网后，局域网任意主机或 HiveMQ 公共 broker 上任意订阅方均可向 UART 注入 `!START`/`>...`/CAN 透传指令。
影响：机械臂可在无物理接触、无授权时被使能和驱动，存在人身/设备伤害风险。
修复：默认关闭 MQTT/套接字监听，串口桥加鉴权令牌；`/api/config/*` 加认证；改私有 broker 与随机主题。
回归验收：未授权连接下无法使能电机；抓包确认无明文控制通道。

**P0-2 固件默认校准电流 2000mA，直接执行校准有烧机风险**
证据：`42motor-fw/UserApp/main.cpp:44` `.calibrationCurrent=2000`；`main.cpp:96-97`、`170` 仅按键长按即触发 `encoderCalibrator.isTriggered=true`；CAN `0x02`（interface_can.cpp:32-33）与 `!CALIBRATION` 同样触发。
触发条件：新用户按默认参数上电后长按 Key1 或发校准命令，在未确认 42 电机额定相电流（多数 42 步进约 1.2~2.0A 但具体待核实）时以 2A 通流。
影响：可能烧毁绕组或驱动。
修复：校准前强制核对额定电流并下调；`calibrationCurrent` 改保守值并写 EEPROM 前确认。
回归验收：额定电流未知时校准流程拒绝执行。

**P0-3 许可证/商业限制互相冲突，商用即违规**
证据：根 `LICENSE`＝GPLv3（copyleft）；根 `README.md:24` 声明"禁止一切商用行为"；`esp32-iot/firmware/LICENSE`＝Mongoose（Cesanta）GPLv2 或商业双许可；`mongoose.c/h`、`Assembly-CSharp.dll` 均为第三方/闭源产物。
影响：GPL 传染性与"禁商"条款叠加，任何分发/商用均需逐一清算；Mongoose 商业使用需向 Cesanta 单独购买。
修复：明确项目为学习用途，不改许可；若未来商用须重写或取得授权。
回归验收：存档许可清单与授权边界。

## 三、P1 级发现（影响可用性/正确性，需修复）

**P1-1 Python CLI 无法直接运行且仍是 ODrive 改名残留**
`run_shell.py:9-11` 插入 `Firmware/fibre/python` 死路径（该目录不存在），`ref_tool/__init__.py:4-6` 同样。实际 `fibre` 包位于 `3.Software/CLI-Tool/fibre/`（Python 3.7 的卵 .pyc）。`ref_tool/shell.py:22` 仍打印 `odrv0.motor0.pos_setpoint`，`branding` 仅浅改（"dummy"）。全目录无 `requirements.txt`，依赖 ipython、pyserial/pyusb 未声明。倾向判为 **odrivetool 分叉的半成品**，非 Dummy 自研协议栈。
影响：新用户无法开箱运行、无依赖清单、文档与行为脱节。
修复：整理依赖清单，修正 import 路径，去掉 ODrive 文案。
回归验收：`python3 run_shell.py --version` 可执行且提示连接 Dummy。

**P1-2 DummyStudio 为纯 Windows 成品，无源码**
`DummyStudio/` 是编译后 Unity 工程（`.exe` PE32+ x64、`Assembly-CSharp.dll`、`spap.dll` 原生插件），全仓无任何 `.cs` 源文件。`serial_config.txt` 写 `VendorID=1209`（此为 ODrive 的 USB VID `1209:0d32`），与 REF 实际 USB CDC 可能不符，需实测；`BaudRate=115200`。包含商用资产 `SerialPort Utility Pro`（strings 可见）。
影响：无法二次开发/审计内部逻辑；VID 疑点需硬件验证。
修复：标注成品定位；确认上位机发现机制依赖的 VID/PID。
回归验收：连接真实 REF 后 DummyStudio 能发现设备。

**P1-3 ESP32 真实固件/工具链缺位 + 多处空占位**
真源码仅在 `examples/esp32/uart-bridge/`（main.c+uart.c+wifi.c+cli.c，依赖 ESP-IDF：`esp_vfs_spiffs`、`nvs_flash`）。`tool/esputil.zip`＝0 字节、`firmware/hex/dummy-iot.hex`＝0 字节、`make` 文件＝0 字节（经 `file` 与 inventory 确认）。`esputil` 仅 Mach-O（macOS）可执行文件，**无 Linux/Windows 二进制品**。`README.md` 的 `make build`/`esputil mkhex` 命令在 Linux 下不可用。
影响：README 烧录指引在本机无法执行；"dummy-iot.hex 已提供"为假象。
修复：补 Linux esputil 或改为用户自编译；删除/标注空占位。
回归验收：能按 README 在 Linux 产出 `bridge.hex`。

**P1-4 simple-cli 硬编码串口路径，跨平台不可用**
`simple-cli.py:7` `sername="/dev/tty.usbmodem204C397F32321"`、`chatgpt_gui.py:41` 同，属 macOS 私有机型路径；README 声称 `python3 simple_cli.py` 直接可用。`chatgpt_gui.py:48` 发 `#GETMPU` 但 REF `ascii_protocol.cpp` 并未实现 `GETMPU`，为死代码。
影响：Windows/Linux 用户无法直接使用。
修复：改为命令行/环境变量传串口；删除或实现 GETMPU。
回归验收：传入正确串口后可 `start`。

## 四、P2 级发现（需澄清/低风险）

- **REF 主控 `MPU6050` 自旋等待**：`ref-core-fw/UserApp/main.cpp:166-170` `do{mpu6050.Init();}while(!testConnection())`，未贴 IMU 时程序卡死于此（与初稿 §9.2 一致）。未贴 OLED/IMU 的 REF 需改启动逻辑。
- **CAN 广播擦除配置**：`interface_can.cpp:248` 命令 `0x7e` 置 `CONFIG_RESTORE`，`0x7f` 直接 `NVIC_SystemReset`，无二次确认。
- **`CalibrateHomeOffset()` 副作用**：`dummy_robot.cpp:199-229` 校准过程中把 J2/J3 电流临时降到 0.5A、两次 ApplyHome 后强制 `Reboot()`，属整机系统复位。
- **UART 直控无使能门**：`interface_uart.cpp` 的 `c/v/p` 命令不检查 `enableMotorOnBoot`，串口即发即控（P0-1 的物理入口）。
- **ODE 编译可用性**：`42motor-fw`/`ref-core-fw` 的 `CMakeLists.txt` 声明 `cmake_minimum_required(3.20/3.19)`、`arm-none-eabi-gcc`、`-mcpu=cortex-m3/m4`、链接脚本齐全，结构完整；`README` 明示"CubeMX 重新生成后需撤销 `stm32f1xx_it.c` 更改"。**本机无工具链，未能实测编译**。
- **`6.Docs/电机PID/` 仅一张 `PID.png`**，无对应可执行 PID 小工具源码，"PID 工具与固件匹配"缺乏软件实体（固件侧 DCE 参数见 `boardConfig.dce_kp/kv/ki/kd`）。
- **`Dummy 源码注释/`** 为 7 个注释版 ref 源文件，非独立工具。

## 五、已确认参数表

| 项 | 值 | 证据 |
|---|---|---|
| 根许可证 | GPLv3 | LICENSE |
| Mongoose 许可 | GPLv2/Commercial | esp32-iot/firmware/LICENSE |
| REF 关节减速比 | 30/30/30/24/30/50 | dummy_robot.cpp:24-29 |
| 关节角度范围 | J1 -170~170 … J6 -720~720 | 同上 |
| DH | 0.109/0.035/0.146/0.115/0.052/0.072 | dummy_robot.cpp:32 |
| 伺服采样 | htim4=20kHz / htim1=100Hz | 42motor main.cpp:93-94 |
| REF 调度 | 200Hz（htim7） | ref main.cpp:9 |
| CAN 位置 ACK | StdId=(nodeID<<7)|0x23 | interface_can.cpp:66 |
| UART 波特率 | 115200 / 8N1 | serial_config / usart |
| 默认校准电流 | 2000mA | main.cpp:44 |
| 默认限流/速 | 1A / 30 r/s / 100 r/s² | main.cpp:41-43 |
| DCE 默认增益 | kp200 kv80 ki300 kd250 | main.cpp:45-48 |
| 电机上电使能 | false | main.cpp:50 |
| ESP32 UART | RX27 / TX26 / 115200 | config.json:1 |
| DummyStudio | Windows x64 成品，VID 1209 | serial_config.txt |

## 六、初稿必须修改的条目

1. **§12 中优先级"Python CLI 存在脆弱的路径假设"应升级为 P1 阻塞**：CLI 实为 odrivetool 分叉、import 死路径、无依赖清单，不能当作可用的"木子 simple-cli"。
2. **§2.2/源码证据表** 建议补充 ESP32 uart-bridge 位于 `examples/esp32/uart-bridge/`，并标明其为 Mongoose 官方示例改造、非自研。
3. **新增安全条目**：ESP32 串口桥/MQTT/HTTP 均无鉴权（P0-1），首月若接 ESP32 必须默认关闭网络透传。
4. **§3.2 "暂不进入范围"已后置 ESP32，正确**；但应在采购/接线上电前把 P0-2 校准电流核对列为硬性 Gate。
5. **§14 不应采用路线末尾补一条**：不在无鉴权网络透传下使能机械臂。
6. **§12 高风险"6 针 24V+CAN 接错损坏硬件"应保留并强调**（使用指南 v1.3 证实 IN/OUT 与同向/反向线易错接）。

## 七、本领域分阶段执行建议（软件审计结论侧）

**阶段 A（阻塞项先行，0 依赖）**：固化许可边界（学习+禁止商用+GPL）；核对 42 电机额定电流并把校准保护写入流程；给 ESP32 桥接加关/鉴权 tag。产出=安全处置清单。

**阶段 B（工具链与最小闭环）**：装 arm-none-eabi 工具链，从 `CMakeLists.txt` 干净构建 `42motor-fw`/`ref-core-fw` 并留存固件尺寸；用 STM32F103 开发板做 GPIO/UART/SPI/SWD 四实验（呼应初稿第 1 周）。产出=两份构建日志 + `main()`→中断调用图。

**阶段 C（串口闭环）**：绕过 REF，用 `simple-cli`（改串口传参后）或自制脚本走 UART `c/v/p` 验证单 42 板；读 `MT6816Base::Init` 校准表校验逻辑，实操磁铁/回绕实验。产出=单板闭环日志。

**阶段 D（CAN 与多节点）**：按 StdId=(nodeID<<7)|cmd 抓取并解码，跑 6 节点静态通信；再上 REF 两轴。产出=CAN 抓包与掉线恢复记录。

**阶段 E（上位机与 ESP32）**：DummyStudio 连接真实 REF 实测 VID；ESP32 用 ESP-IDF 重编 uart-bridge 并默认关 MQTT。产出=带鉴权的网络桥。

## 八、未验证与缺件

- **未实际编译任何固件/程序**（无 arm-none-eabi、无 ESP-IDF、无 Python 依赖环境），"能否编译"仅凭工程结构判断。
- **DummyStudio 未运行**（Windows x64 成品，本 Linux 环境无法执行，且受只读约束未运行）。
- **USART 波特率暂以 usart.c 配置推算**，未回读 cubemx 外设时钟具体分频（42motor `usart.c` 未在本轮逐行核对）。
- **40/PID 工具无源码实体**，仅一张 PNG；无法验证"PID 工具与固件匹配"。
- **电机额定相电流、编码器磁铁规格仍缺件**（初稿已列，属实物采购前必须补齐）。
- **REF VID/PID 与 DummyStudio `1209` 的匹配未验**。
- Mongoose 版本（`src/version.h`）未读取具体版本号，建议归档时记录。

（约 4900 字）
