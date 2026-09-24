# 真实候选 SUT 接入与 D0-SMOKE 执行记录

> 文件性质：E1 真实候选 SUT 接入门、候选决策和执行状态记录。
>
> 记录日期：2026-09-23。
>
> 当前状态：真实接入包验证器已实现；候选优先级已初选；真实代码、权重、数据和媒体均未下载；真实推理尚未执行。
>
> 阶段结论：`blocked_by_external_assets_and_review`。阻断是正常的许可与环境门，不以合成结果替代。

## 1. 本阶段目的

第 12 阶段已经证明统一数据、合成适配器、指标路由和报告链路可运行。本阶段要把“能够运行合成管线”推进到“能够安全接收真实候选 SUT 运行包”，并在真实资产到位前完成所有可独立完成的静态验收工作。

本阶段不擅自执行以下操作：

- 不代表项目负责人接受第三方数据条款或 EULA；
- 不下载大型数据集、模型权重或来历不明的媒体；
- 不在主 Python 环境中安装老旧、冲突或 GPU 专用依赖；
- 不把逻辑夹具、占位文件或真值感知合成 SUT 认定为真实运行；
- 不因尚未有真实结果而填写零分或虚构能力输出。

## 2. 候选系统核验

### 2.1 官方信息核验范围

本轮只核验官方仓库公开说明：

1. [DeepfakeBench 官方仓库](https://github.com/SCLBD/DeepfakeBench)；
2. [DeepfakeBench 官方 releases](https://github.com/SCLBD/DeepfakeBench/releases)；
3. [DF40 官方仓库](https://github.com/YZY-stack/DF40)；
4. [LAV-DF 官方仓库](https://github.com/ControlNet/LAV-DF)。

核验日期为 2026-09-23。仓库后续可能变化，真正接入时必须重新冻结提交哈希、release 资产摘要和许可证文本哈希。

### 2.2 当前官方信息摘要

| 项目 | 当前可用于决策的信息 | 对 E1 的影响 |
|---|---|---|
| DeepfakeBench | 官方 README 声明支持 36 种检测方法，其中包括 Xception；提供预训练权重入口；快速安装示例使用 Python 3.7.2，也提供 Dockerfile；聚合数据版权属于原始提供方 | 适合作为首个视觉分类适配候选，但需隔离旧环境并单独审查 checkpoint 和数据 |
| DF40 | 官方仓库提供 Xception 等多种 protocol/checkpoint；声明数据和代码为 CC BY-NC 4.0；完整测试伪造数据约 93 GB | 可作为第二视觉候选，不适合为了 E1 直接下载完整数据；必须冻结一个明确训练协议 |
| LAV-DF | 官方仓库提供 BA-TFD/BA-TFD+ 预训练模型入口；使用数据前要求同意条款；主要版本要求 Python `>=3.7,<3.11`、PyTorch `>=1.13`、torchvision `>=0.14`、pytorch_lightning `1.7.*` | 能覆盖音视频和时间定位，但条款、旧环境、数据与算力成本高于首个视觉分类候选 |

以上信息只用于候选排序，不等于法律批准、环境兼容性证明或模型可运行证明。

## 3. 候选优先级决定

### 3.1 首选：SUT-V1-XCEPTION-DFB

首个真实适配目标暂定为 DeepfakeBench 中的 Xception，原因是：

- 与 `10-最小可行实验实施方案.md` 已冻结的 SUT-V1 角色一致；
- 输出形态主要是二分类分数，适配面小于时间定位系统；
- 官方仓库存在明确检测器配置和预训练权重入口；
- 可以先验证 C-1—C-6、D-1 和基础工程字段，不要求伪造定位或证据输出；
- 后续可在同一框架中选择第二种检测器做接口可比性检查。

当前状态仍为阻断：`blocked_pending_license_environment_and_weight_review`。在以下事项完成前，`download_authorized=false`：

1. 审查代码和目标 checkpoint 对本项目用途的许可条件；
2. 确认独立 Python/容器环境策略；
3. 冻结确切提交和 release 资产；
4. 获取后立即记录权重 SHA-256；
5. 准备独立许可通过的 D0 媒体；
6. 编写不读取真值的适配器。

### 3.2 第二候选：SUT-V2-DF40-XCEPTION

DF40 的 Xception checkpoint 可作为第二视觉对象，但不作为第一接入目标。DF40 提供多种训练协议和 checkpoint，若不先冻结训练域、方法族和 protocol，模型间差异会和配置选择混在一起。

本项目不为 E1 下载约 93 GB 的完整测试集。E1 只需要许可明确的小规模 D0 媒体；模型与数据可来自不同审查记录，但必须避免训练/测试泄漏并保存来源关系。

### 3.3 音视频候选：SUT-AV1-BATFD-PLUS

BA-TFD+ 保留为多模态与时间定位候选。它的重要价值是验证：

- M1/M2/M5 能力声明；
- `segments` 输出映射；
- C-9 时间定位精度；
- 多模态输入不支持、缺轨或解码失败状态。

但该候选在数据条款、Python 版本、PyTorch Lightning 版本和 GPU 资源上具有更高接入成本，应在 SUT-V1 的统一输出路径稳定后推进。

## 4. 许可与下载状态

机器可读登记位于：

- `experiments/mvp/config/candidate-sut-register.json`；
- `experiments/mvp/config/source-license-register.json`。

三个候选当前均为：

```text
download_status = not_downloaded
download_authorized = false
```

其中：

- DeepfakeBench 记录仅覆盖代码和 checkpoint 入口初审，不批准其聚合数据；
- DF40 记录不批准完整数据、衍生帧或底层真实来源；
- LAV-DF 的数据条款必须由授权人员阅读、决定并留证，不能由自动化流程代为接受。

## 5. 真实候选接入包规范

### 5.1 目录结构

真实运行完成后，应形成自包含包：

```text
candidate-package/
├─ system.json
├─ run.json
├─ license-register.json
├─ samples.jsonl
├─ predictions.jsonl
├─ license-evidence/
│  ├─ license.txt
│  └─ approval-record.pdf
└─ media/
   └─ ...
```

当前验证器不允许媒体路径逃逸包目录。这样可以避免报告依赖未归档的绝对路径，也降低路径替换和误读其他文件的风险。

### 5.2 文件要求

| 文件 | 要求 |
|---|---|
| `system.json` | 符合系统登记 Schema；真实 `model` 的权重哈希不得为空 |
| `run.json` | 符合运行 Schema；必须为 E1 且状态为 `completed`；系统身份与版本一致 |
| `license-register.json` | 每个来源均须 approved + approved_for_download，并绑定许可文本哈希、审核身份和包内证据 |
| `samples.jsonl` | 非空；全部属于 D0；许可状态须精确为 `approved` 或受控的 `approved_*` 值；全部为 `included` |
| `predictions.jsonl` | 符合预测 Schema；每个输入有且只有一条对应预测或失败记录 |
| `media/` | 文件实际存在、位于包内且 SHA-256 与清单一致 |

若真实 SUT 是远程服务而非本地模型，`system_type=service` 可没有模型权重，但必须在环境和代码修订字段中记录 API 版本、服务构建号或其他可追踪身份。正式方案后续还应增加服务响应签名和请求配置摘要。

## 6. 接入包验证器

### 6.1 执行命令

```powershell
cd D:\git-project\Deepfake-Detection-Standards\experiments\mvp
python -m tools.sut_package_validation `
  --package <candidate-package> `
  --output <candidate-package>\validation-report.json
```

默认要求媒体存在。`--allow-missing-media` 只用于结构调试，不能作为正式接入证据。

### 6.2 校验层次

验证器按以下层次检查：

1. 五个必需清单文件存在：系统、运行、许可登记、样本和预测；
2. JSON/JSONL 可解析；
3. 系统、运行、样本和预测分别通过 Schema，许可登记通过独立审批证据校验；
4. 不允许 `synthetic_baseline` 通过真实候选门；
5. 模型类型必须记录权重哈希；
6. 运行必须是已完成的 E1；
7. 系统和运行身份/版本一致；
8. 清单非空、样本属于 D0、许可已批准、未被排除；
9. 输入输出关系无未知、重复、漏出和身份错配；
10. 许可文本和审批证据位于包内，许可文本 SHA-256 匹配；
11. 媒体路径位于包内、文件存在且 SHA-256 匹配；
12. 生成一套 39×1 可计算性矩阵。

### 6.3 主要阻断码

| 阻断码 | 含义 |
|---|---|
| `required_file_missing` | 必需清单文件缺失 |
| `schema_validation_failed` | 记录未通过对应 Schema |
| `synthetic_system_not_allowed` | 合成系统试图进入真实候选门 |
| `model_weights_hash_missing` | 模型没有冻结权重哈希 |
| `non_e1_run` / `run_not_completed` | 运行类型或状态不合格 |
| `system_identity_mismatch` | 系统登记和运行登记不一致 |
| `empty_sample_manifest` | D0 清单为空 |
| `non_d0_sample` | E1 包混入其他分区 |
| `sample_license_not_approved` | 样本许可状态未批准 |
| `sample_not_included` | 清单含排除或隔离样本 |
| `media_path_outside_package` | 路径逃逸自包含包 |
| `media_file_missing` | 媒体不存在 |
| `media_hash_mismatch` | 媒体内容与清单哈希不同 |
| `missing_prediction` | 某个输入没有任何结果记录 |

跨文件校验器的其他阻断码继续沿用第 12 阶段定义。

## 7. 测试驱动记录

### 7.1 第一轮

先建立四项测试，要求：

- 完整的非合成候选包可通过；
- 合成系统不可通过真实门；
- 媒体哈希不一致必须失败；
- 漏预测必须失败。

RED 阶段为：

```text
ModuleNotFoundError: tools.sut_package_validation
```

完成验证器后 4/4 通过。

### 7.2 安全收紧轮

再增加三项测试，首次执行均正确失败：

- 包外路径未被拦截；
- 真实模型缺权重哈希未被拦截；
- D1 和许可待审样本未被拦截。

实现约束后，接入包测试为：

```text
Ran 7 tests
OK
```

完成本阶段接入门后，整个 MVP 测试集达到 36 项；继续实现 D-1/D-2/D-4、复跑比较器、全成功输出字段交集和独立许可证据门后达到 54 项；审查驱动的乱序关联、版本一致性、非有限数、运行时间和降级模式回归将其扩展至 63 项。本轮最终全量验证为 63/63 通过。

## 8. 当前真实执行记录

| 项目 | 状态 | 证据/原因 |
|---|---|---|
| 候选优先级 | 已初选 | SUT-V1 Xception → SUT-V2 DF40 Xception → SUT-AV1 BA-TFD+ |
| 代码许可初审 | 待最终确认 | 官方仓库许可证和说明已定位 |
| checkpoint 条款审查 | 未完成 | 尚未选择和下载具体资产 |
| 数据/媒体许可 | 未批准 | 无来源记录达到 approved + approved_for_download |
| 候选代码下载 | 未执行 | `download_authorized=false` |
| 权重下载 | 未执行 | `download_authorized=false` |
| 真实 D0 媒体 | 0 条 | 逻辑 D0-SMOKE 不计入真实媒体 |
| 隔离环境 | 未建立 | 待候选提交和依赖冻结 |
| 真实适配器 | 未实现 | 已有模板和验收清单 |
| 真实推理运行 | 0 次 | 前置条件未满足 |
| 真实可计算性矩阵 | 未生成 | 不能用合成矩阵替代 |

因此，本文件标题中的“执行记录”当前记录的是“未执行及其可追踪原因”。这是合规且诚实的状态，不是项目失败。

## 9. 进入真实执行的最小输入

继续推进真实 E1 需要外部提供或明确批准以下内容：

1. 对 SUT-V1 代码与一个明确 checkpoint 的使用授权结论；
2. 允许创建隔离环境和下载对应代码/权重；
3. 至少一对许可明确的 REAL/FAKE 视觉媒体，优选 4—12 条组成多个来源组；
4. 每条媒体的来源、许可证据、标签和父子关系；
5. 可用算力信息，至少说明是否有 CUDA GPU 及显存；
6. 若使用容器，允许的容器运行方式和镜像留存位置。

如果只能提供自有可控媒体，优先使用自建 D0：由项目方拥有或获授权的真实素材生成少量明确许可的伪造样本。这样比直接下载大型公开数据更适合 E1 接口冒烟，但仍需记录生成方法、工具版本、人员权限和生物特征数据处理依据。

## 10. 获批后的执行顺序

1. 复制许可模板形成正式审核记录，保存许可证文本哈希；
2. 冻结候选仓库提交，不直接追随 `main`；
3. 在独立目录或容器中建立环境，不污染 MVP 工具环境；
4. 获取一个明确 checkpoint，计算 SHA-256 并登记；
5. 准备自包含 D0 媒体包，逐文件计算哈希；
6. 编写只读取 `sample_id/file_path/media_type` 的适配器；
7. 首先运行 1 条 REAL 和 1 条 FAKE，检查分数方向与错误状态；
8. 扩展至全部 D0-SMOKE，保存任何失败记录；
9. 生成系统、运行、样本和预测清单；
10. 执行接入包验证器；
11. 通过后生成真实 39×1 可计算性矩阵；
12. 至少复跑一次，比较预测和状态哈希；
13. 编制 E1 真实冒烟报告，不做等级判定。

## 11. 阶段门判断

### 已完成

- 真实候选优先级和替代顺序已形成机器可读登记；
- 许可登记已从空模板推进到三个候选的初审状态；
- 自包含真实接入包结构已固定；
- 真实/合成隔离、权重哈希、D0/许可、媒体路径和哈希均有自动阻断；候选包报告记录清单及已核验媒体的 SHA-256；
- 样本许可声明会按 `source_id` 与独立许可登记交叉核对；许可文本和批准证据必须在包内，许可文本哈希必须一致；
- 输入输出关系和 39 项路由可复用；
- 接入包验收现有 16 项自动测试（7 项是早期安全收紧轮的历史节点，后续新增许可、输出约束和审查加固用例）。
- D-1 时延摘要已实现并接入统一指标结果；
- D-2 实时率已实现冻结口径；失败时间和超时上限不会从分母中静默删除；
- D-4 成功吞吐量已实现；运行 Schema 新增墙钟时间、批大小、并发、排队时间、超时上限和计时范围上下文；
- `--allow-missing-media` 现在明确输出 `validation_profile=structure_only`、`media_validation_performed=false`，并且永远不能产生 `ready_for_e1_smoke=true`；
- 预测必须按 `sample_id` 与真值连接，记录中的系统版本必须与冻结登记一致；非标准 `NaN`/`Infinity` 和倒置运行时间会被阻断。

仍需注意信任边界：包内许可登记、许可文本和批准证据可以证明“同包材料的一致性”，不能单独证明批准主体可信；权重、配置和环境摘要目前也尚未绑定包内实际制品。正式外部提交场景必须在评测方只读暂存区运行，并增加外部许可批准信任库或数字签名、权重/配置/环境制品绑定及不可变内容寻址存储。未完成这些组织级设施前，本验证器只应作为受控项目内部的静态接入门。
- 两次运行的语义哈希、分数容差、状态/标签差异、漏记录和耗时均值已有比较器及 4 项测试。

### 尚未通过

- P0 许可与资源门；
- 真实候选环境可运行门；
- 真实媒体 D0 门；
- 真实适配器输出门；
- 真实 E1 重复运行门。

项目可以继续完善不依赖外部资产的错误码、报告模板和环境登记，但不能宣布真实 E1 完成。

## 12. 下一步

在外部批准到位前，内部可继续推进：

1. 为真实接入包增加运行日志索引和适配器日志哈希；
2. 将 `metric-result.schema.json` 接入真实报告写出；
3. 设计 D0 媒体技术检查，包括解码、时长、尺寸和音轨存在性；
4. 增加候选服务型 SUT 的请求/响应审计字段；
5. 为 D-3 FPS 增加实际处理帧数和抽帧策略字段及冻结用例；
6. 在真实两次运行到位后执行复跑比较器并预注册容差。

外部批准到位后，首要动作是接入 SUT-V1-XCEPTION-DFB 的一个明确 checkpoint 和最小视觉 D0，而不是同时部署三个候选。
