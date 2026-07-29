# M0 未知项与风险

## 基线与判定边界

- 检查日期：2026-07-29
- 母本提交：`09fb3f43bb94c60a46012809c9f58c4e2a7d2405`
- 文件证据：`repository-inventory.csv`，共 8,136 个文件、537,898,933 字节
- 扫描范围：`0.SubModules`、`1.Hardware`、`2.Firmware`、`3.Software`、`4.Model`、`5.Docs`

本文的“缺失”只表示在上述锁定 checkout 和扫描范围内未找到可识别文件，不等价于作者从未制作过相关资料。文件名与扩展名搜索无法证明 STEP、PCB 或二进制文件内部不存在某项元数据，因此这类结论保持为 `unknown`。

## 风险清单

### M0-RISK-001：缺少可识别的原生参数化机械 CAD 与正式制造定义

- **状态：** confirmed absence / unknown
- **证据：** `repository-inventory.csv` 中 `4.Model` 只有 `upstream:4.Model/Case v17.step`、`upstream:4.Model/Dummy v164.step`、`upstream:4.Model/Motor42-上盖.step`、`upstream:4.Model/Motor42-下盖.step` 四个 STEP 文件；未找到 SolidWorks、Fusion 360、FreeCAD、Inventor 等可识别原生参数化格式，也未在 `4.Model` 找到 DWG、DXF、SLDDRW、IDW 或 PDF 工程图。
- **边界：** STEP 可能携带名称、颜色或材料元数据，本阶段没有解析其内部属性；因此“正式公差、材料和表面处理定义是否存在于 STEP 内”仍为 `unknown`。
- **影响：** 不能直接恢复特征历史、设计意图和完整制造要求，机械升级前需要建立自有参数化模型并验证关键尺寸。
- **后续动作：** M0 机械基线阶段从 STEP、固件 DH 参数和实物测量三方交叉重建；公差、材料和工艺单独建表，不从几何外形臆测。

### M0-RISK-002：电子生产资料覆盖不完整

- **状态：** confirmed absence
- **证据：** `1.Hardware` 中有 9 个 Altium PCB 工程、9 个 PCB 文件和 21 个原理图文件；Gerber 目录只出现在 `upstream:1.Hardware/MotorDriver-42/Gerber` 与标记为 unused 的 `upstream:1.Hardware/MotorDriver-57-unused/Gerber`。未找到名称可识别的 BOM、CPL、centroid 或 pick-and-place 文件。
- **影响：** 现有资料不能直接视为全部控制板的可下单生产包；元器件型号、封装、替代料和贴装坐标仍需从 Altium 工程导出并人工复核。
- **后续动作：** 按板卡逐项建立“原理图—PCB—Gerber—BOM—CPL”覆盖矩阵；在许可证边界确认前，不把母本生产文件复制到复现仓库。

### M0-RISK-003：DummyStudio 只有可执行发行物，没有业务源码

- **状态：** confirmed absence
- **证据：** `upstream:3.Software/DummyStudio` 由 `DummyStudio.exe`、78 个 DLL、Unity 资源和运行时配置组成；未找到 C# 源文件或 Unity 的 `Assets`、`Packages`、`ProjectSettings` 项目结构。`upstream:README.md` 的“关于上位机”明确说明上位机暂时没有开源计划。
- **影响：** 无法在原工程上修改可视化、通信或仿真功能，也不能把该二进制程序当作未来智能控制实验平台的可维护基础。
- **后续动作：** 后续自行建立开放的主机端工具链，优先定义可测试的通信接口、日志格式和仿真接口。

### M0-RISK-004：缺少标准机器人描述与 ROS 工程

- **状态：** confirmed absence
- **证据：** 六个资产根中未找到 `.urdf`、`.xacro` 或 ROS `package.xml`，路径名搜索也未发现 MoveIt 工程。
- **影响：** 无法直接接入 ROS、MoveIt、常见动力学库或强化学习仿真环境。
- **后续动作：** 在机械参数基线稳定后，自行创建 URDF/Xacro、碰撞几何、惯量参数和关节限制；其数值必须标注 evidence、measurement 或 assumption。

### M0-RISK-005：仓库级许可证不明确

- **状态：** confirmed absence / legal unknown
- **证据：** 母本根 Git 树中没有仓库级 `LICENSE` 或 `COPYING`；`0.SubModules/Peak` 内的第三方依赖许可证只适用于相应依赖，不能替代 Dummy Robot 项目许可证。
- **影响：** 可以为个人学习进行分析和记录，但母本 CAD、PCB、固件和二进制资产的再分发、改作和商业使用权限不能据此推定。
- **后续动作：** 复现仓库继续只保存自产代码、参数表和证据引用；任何母本资产再分发前单独确认许可。

### M0-RISK-006：Peak 子模块工作树未按声明路径初始化

- **状态：** confirmed anomaly
- **证据：** 母本索引把 `upstream:0.SubModules/Peak` 记录为 gitlink `c7a90eda10683c1fb92665297bd86d3de2400d43`；`git submodule status --recursive` 的该项以 `-` 开头，表示声明的子模块工作树未初始化。当前机器另有嵌套 checkout `upstream:0.SubModules/Peak/Peak`，不在 `.gitmodules` 声明的预期层级。
- **影响：** 当前 CSV 能审计本机实际扫描到的 Peak 文件及哈希，但仅凭母本提交和 `.gitmodules` 不能重建这个嵌套目录状态；在另一台机器重新生成清单可能不同。
- **后续动作：** 保持当前母本只读；后续用全新临时 checkout 验证标准 `git submodule update --init --recursive` 的结构和提交，再决定是否扩展来源锁以记录子模块状态。

### M0-RISK-007：动力学与 200 Hz 轨迹链路不是完整能力

- **状态：** confirmed incomplete
- **证据：** `upstream:README.md` 的“关于控制算法”明确写明动力学尚未完全实现，并把 TRJ 轨迹跟踪标为 `ToDo`。`upstream:2.Firmware/Core-STM32F4-fw/UserApp/main.cpp` 存在 200 Hz 控制定时器和 TRJ 模式分支；`upstream:2.Firmware/Core-STM32F4-fw/Robot/instances/dummy_robot.cpp` 也定义了 TRJ 模式，但现有证据不足以证明固定周期轨迹点缓冲、插值、时序错误处理和端到端轨迹验收已经实现。
- **影响：** 不能把当前固件直接视为动力学控制或精确 200 Hz 外部轨迹跟踪平台；未来算法实验需要自建并验证实时接口、安全约束和降级策略。
- **后续动作：** 先复现运动学与关节级位置控制，再建立仿真、硬件在环和低速真机三级验证；动力学、轨迹缓冲和智能控制接口作为后续独立里程碑。

## 当前结论

母本足以支持 V0 几何、板卡设计、核心固件和通信协议的取证，但不足以直接构成一套完整、可制造、可维护、可用于智能控制研究的生产工程。后续所有补全项应进入复现仓库，并保留“原始证据—工程推断—实测结果”的区分。
