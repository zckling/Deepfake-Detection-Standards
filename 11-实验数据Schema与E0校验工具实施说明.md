# 实验数据 Schema 与 E0 校验工具实施说明

> 文件性质：`10-最小可行实验实施方案.md` 中 WP1 和 E0 的实现记录。
>
> 实现目录：`experiments/mvp/`。
>
> 当前状态：七类 Schema、受控词表、D0-FIXTURE、核心指标参考实现、校验器和自动测试已建立。
>
> 证据边界：当前结果仅支持 P1 初始 Schema 完整性和 P2 已实现用例的计算正确性，不代表 E1—E4 已执行，也不代表 39 项指标均已实现。

## 1. 实施目的

本阶段把 09 的数据要求和 10 的实验设计转化为首批机器可执行资产，消除以下风险：

1. 文档中的字段定义无法被程序强制执行；
2. 不同被测对象输出同名不同义或缺字段后被静默填充；
3. 指标公式方向、分母、并列分数和未定义状态处理错误；
4. E0 只靠人工观察，没有可重复回归测试；
5. 实验结果缺少版本、输入、预期和实际值的对应记录。

本阶段遵循“测试先行”。每个生产模块在实现前先建立失败测试，确认测试能够因目标功能缺失而失败，再编写最小实现使其通过。

## 2. 实施范围

### 2.1 已实现

- 七类 Draft 2020-12 JSON Schema；
- D/M/O/R/G、状态和方法族受控词表；
- 每个 Schema 一条可直接复制的合法示例；
- 单记录和 JSONL 批量 Schema 校验器；
- 二分类核心指标参考实现；
- 单时间区间 tIoU 和轴对齐 bbox IoU；
- 10 个冻结 E0 用例及人工预期；
- E0 执行器、机器可读报告和 Markdown 摘要；
- 17 项自动测试。

### 2.2 尚未实现

- 39 项指标的全部生产计算器；
- AP、AR、置信区间、聚类 bootstrap 和配对比较；
- 多实例片段/区域匹配；
- mask、polygon、track 和证据一致性计算；
- 跨文件来源组、分区和近重复关系约束；
- 外部数据集获取、真实媒体清单和真实 SUT 适配；
- E1—E4 实验执行。

未实现项均保留为后续工作，不以空结果宣称已经完成。

## 3. 实现结构

```text
experiments/mvp/
├─ README.md
├─ requirements.txt
├─ schemas/
│  ├─ sample-manifest.schema.json
│  ├─ annotation.schema.json
│  ├─ system-registry.schema.json
│  ├─ prediction.schema.json
│  ├─ run-manifest.schema.json
│  ├─ metric-result.schema.json
│  └─ exclusion.schema.json
├─ vocabularies/
│  └─ vocabularies.json
├─ fixtures/
│  ├─ e0-cases.json
│  └─ schema-examples/
│     ├─ sample-manifest.example.json
│     ├─ annotation.example.json
│     ├─ system-registry.example.json
│     ├─ prediction.example.json
│     ├─ run-manifest.example.json
│     ├─ metric-result.example.json
│     └─ exclusion.example.json
├─ tools/
│  ├─ __init__.py
│  ├─ schema_validation.py
│  ├─ metrics.py
│  └─ run_e0.py
├─ tests/
│  ├─ test_schema_validation.py
│  ├─ test_metrics.py
│  └─ test_e0_runner.py
└─ reports/
   ├─ e0-report.json
   └─ E0-report.md
```

## 4. 环境与依赖

### 4.1 最低环境

| 项目 | 要求 |
|---|---|
| Python | 3.11 或更高版本 |
| JSON Schema | Draft 2020-12 |
| 外部 Python 依赖 | `jsonschema>=4.25,<5` |
| 指标实现依赖 | 仅 Python 标准库 |
| 文件编码 | UTF-8 |

本次验证实际使用 Python 3.13.9 和 jsonschema 4.25.0。该环境记录只说明本轮执行条件，不替代后续锁文件和容器环境。

### 4.2 安装

```powershell
cd D:\git-project\Deepfake-Detection-Standards\experiments\mvp
python -m pip install -r requirements.txt
```

## 5. 七类 Schema

### 5.1 样本清单 Schema

`sample-manifest.schema.json` 固定样本身份、来源组、父样本、文件、哈希、来源类型、媒体类型、真值、M/O 标签、方法族、作用域、媒体属性、D0—D3 分区、许可、访问、标注和排除状态。

已实现的条件约束包括：

- `label_state=FAKE` 时，`fake_modalities`、`fake_objects` 至少各有一项；
- FAKE 样本必须具有 `method_family`、`scope_id` 和 `granularity`；
- `label_state=REAL` 时，伪造模态和对象列表必须为空；
- 排除或隔离样本必须具有非空 `exclusion_reason`；
- SHA-256 必须是 64 位小写十六进制；
- Schema、标注版本采用三段式数字版本。

这些约束只验证单条记录，不能替代跨样本的 `group_id` 防泄漏检查。

### 5.2 标注 Schema

`annotation.schema.json` 为样本、模态、时间、帧、空间、文字、证据和扰动标注提供统一外壳。具体标注内容暂存于 `payload`，其内部子 Schema 将在定位和取证计算器实施时继续拆分。

### 5.3 被测对象登记 Schema

`system-registry.schema.json` 记录系统编号、名称、版本、类型、代码修订、权重哈希、能力声明和运行环境。合成基线允许 `weights_sha256=null`；真实模型应保存实际权重哈希。

### 5.4 统一预测 Schema

`prediction.schema.json` 固定样本、系统、运行、标签、分数、耗时、状态和错误码，并预留模态、对象、片段、区域和证据字段。

当 `status=ok` 时：

- `is_fake_pred` 必须为布尔值；
- `fake_score` 必须处于 `[0,1]`；
- `processing_time_sec` 必须为非负数；
- `error_code` 必须为 `null`。

当状态为 `runtime_error`、`timeout` 或 `missing_output` 时，必须提供错误码。

### 5.5 运行记录 Schema

`run-manifest.schema.json` 绑定 E0—E4 实验、数据版本、SUT 版本、配置哈希、环境哈希、开始结束时间和运行状态。日期时间使用 RFC 3339 兼容格式，并由格式检查器强制校验。

### 5.6 指标结果 Schema

`metric-result.schema.json` 记录指标编号、状态、值、分子、分母、分析单位、置信区间和计算器版本。未定义、不支持和不适用状态允许 `value=null`，避免用零掩盖不可计算性。

### 5.7 排除记录 Schema

`exclusion.schema.json` 记录样本在采集、标注、去重、分区、运行或分析阶段的排除申请、原因、审核和决定，为“不得静默删除失败样本”提供审计载体。

## 6. 受控词表

`vocabularies/vocabularies.json` 当前包括：

- D0—D3 数据分区；
- M1—M5 伪造模态；
- O1—O4 伪造对象；
- R1—R8 扰动组；
- G1—G4 泛化组；
- 七种预测状态；
- 十类主要方法族以及 `other`、`unknown`。

词表版本与 Schema 版本分开管理。后续增加类别时应升级词表版本，并判断是否需要同步升级 Schema。

## 7. Schema 校验器

### 7.1 单记录接口

```python
from pathlib import Path
from tools.schema_validation import validate_record

errors = validate_record(
    Path("schemas/prediction.schema.json"),
    prediction_record,
)
```

返回空列表表示结构合法；否则返回带字段路径的错误消息。校验器显式启用 `FormatChecker`，因此日期时间等 `format` 约束会实际执行。

### 7.2 JSONL 接口

```powershell
python -m tools.schema_validation `
  --schema schemas/prediction.schema.json `
  --jsonl <预测结果.jsonl>
```

批量结果包括：

- `total`：非空记录行总数；
- `valid`：合法记录数；
- `invalid`：JSON 解析失败或 Schema 不通过的记录数；
- `errors`：逐行聚合错误。

一条记录即使同时违反多个字段规则，也只计作一条无效记录；全部字段错误会在同一消息中保留。

## 8. E0 核心指标参考实现

### 8.1 阈值与混淆矩阵

当前约定 `fake_score >= threshold` 判为伪造。参考实现计算 TP、TN、FP 和 FN，并据此计算：

```text
Accuracy = (TP + TN) / N
Precision = TP / (TP + FP)
Recall = TP / (TP + FN)
Specificity = TN / (TN + FP)
F1 = 2TP / (2TP + FP + FN)
Balanced Accuracy = (Recall + Specificity) / 2
```

分母为零时返回 `null`，不得自动填零。若 Recall 或 Specificity 任一未定义，Balanced Accuracy 也返回 `null`。

### 8.2 AUC

E0 参考实现使用正负样本分数的成对排序定义：正样本分数更高计 1，相等计 0.5，更低计 0。该实现透明处理并列分数，适合小规模边界用例。只有单一类别时 AUC 返回 `null`。

正式大规模实验可换用经过独立验证的高效实现，但必须先证明与 E0 参考实现和冻结用例一致。

### 8.3 EER

参考实现按不同分数阈值构造 ROC 点，寻找 FPR 与 FNR 的交点；若交点落在相邻点之间，采用线性插值。只有单一类别时 EER 返回 `null`。

### 8.4 时间 IoU

对左闭右开时间区间 `[start,end)`：

```text
tIoU = intersection_duration / union_duration
```

零长度或反向区间直接拒绝，不返回看似合法的零。

### 8.5 空间 bbox IoU

对轴对齐框 `(x1,y1,x2,y2)` 计算交并比。宽或高非正的框直接拒绝。当前尚未验证图像边界、坐标系和归一化坐标，这些约束应在实际标注 Schema 中进一步固定。

## 9. D0-FIXTURE

### 9.1 用例清单

| case_id | 类型 | 人工预期 |
|---|---|---|
| E0-BIN-PERFECT | 二分类 | ACC/F1/AUC=1，EER=0 |
| E0-BIN-INVERSE | 二分类 | ACC/AUC=0，EER=1 |
| E0-BIN-CONSTANT | 二分类 | AUC/EER=0.5，验证并列与阈值等号 |
| E0-BIN-SINGLE-CLASS | 二分类 | AUC/EER/Recall 等无合法分母项为 `null` |
| E0-TEMPORAL-EXACT | 时间定位 | tIoU=1 |
| E0-TEMPORAL-PARTIAL | 时间定位 | tIoU=1/3 |
| E0-TEMPORAL-DISJOINT | 时间定位 | tIoU=0 |
| E0-BBOX-PARTIAL | 空间定位 | IoU=1/7 |
| E0-BBOX-DISJOINT | 空间定位 | IoU=0 |
| E0-TEMPORAL-INVALID | 异常处理 | 抛出 `ValueError` |

### 9.2 浮点容差

冻结用例采用绝对容差 `1e-12`，不使用相对容差。该设置用于简单人工算例，不应直接外推到复杂 AP、bootstrap 或硬件效率结果。

### 9.3 防伪通过测试

自动测试会临时篡改第一个用例的预期 ACC，并确认 E0 运行器返回失败。这样可以证明测试不是无论实现如何都通过。

## 10. 测试驱动实施记录

| 循环 | RED 证据 | GREEN 结果 | 实施内容 |
|---|---|---|---|
| Schema 校验 | `ModuleNotFoundError: tools.schema_validation` | 首轮 5/5 通过 | 七类 Schema 和校验器 |
| 指标实现 | `ModuleNotFoundError: tools.metrics` | 7/7 通过 | 分类、AUC/EER、tIoU、bbox IoU |
| E0 运行器 | `ModuleNotFoundError: tools.run_e0` | 3/3 通过 | 冻结用例执行与报告 |
| 格式与示例 | 日期格式未被拒绝；Schema 示例 0/7 | 7/7 通过 | `FormatChecker` 和七条示例 |

Schema 首轮实现后曾出现一项中间失败：同一 JSONL 记录的两个约束错误产生两条消息。修正后的设计以无效记录为计数单位，在记录内聚合全部字段错误。

## 11. 执行方法

### 11.1 运行全部测试

```powershell
cd D:\git-project\Deepfake-Detection-Standards\experiments\mvp
$env:PYTHONDONTWRITEBYTECODE='1'
python -m unittest discover -s tests -p 'test_*.py' -v
```

### 11.2 运行 E0

```powershell
python -m tools.run_e0 `
  --cases fixtures/e0-cases.json `
  --output reports/e0-report.json
```

退出码为 0 表示全部冻结用例通过；退出码为 1 表示至少一项失败。无论结果如何，都应保留报告并记录对应代码版本。

## 12. 本轮验证结果

### 12.1 自动测试

```text
Ran 17 tests in 0.110s
OK
```

测试构成为：

- Schema 与校验器：7 项；
- 指标边界：7 项；
- E0 运行器：3 项。

### 12.2 正式 E0 冻结用例

```text
total=10
passed=10
failed=0
```

机器可读报告位于 `experiments/mvp/reports/e0-report.json`，摘要位于 `experiments/mvp/reports/E0-report.md`。

### 12.3 当前可以支持的结论

- 七类初始 Schema 均为合法 Draft 2020-12 Schema；
- 七类 Schema 均具有一条通过校验的示例；
- 已实现分类和定位参考指标在 10 个冻结边界用例上与人工预期一致；
- E0 运行器能够检测被篡改的预期值；
- JSONL 校验能够区分合法、Schema 非法和 JSON 解析失败记录。

### 12.4 当前不能支持的结论

- 不能声称全部 39 项指标已经实现；
- 不能声称 E0 全部边界已经穷尽；
- 不能声称真实检测模型可以接入；
- 不能声称数据无泄漏或 D1 样本充足；
- 不能声称任何系统达到 L1—L4；
- 不能用本轮结果确定正式阈值。

## 13. 与上游文件的对应关系

| 实现资产 | 上游要求 | 当前证据 |
|---|---|---|
| 七类 Schema | 09 第8、13、14章；10 第7章 | Schema 合法性和示例测试 |
| 受控词表 | 09 第5—7章 | JSON 文件可解析，核心编码固定 |
| 状态枚举 | 08 第7.2节；10 第7.3节 | `prediction.schema.json` 条件约束 |
| 分类指标 | 08 第8.3节和 E0 | 完美、反向、恒定、单类用例 |
| tIoU/bbox IoU | 07 C-8—C-10；08 E0 | 重合、部分重合、分离和非法边界 |
| E0 报告 | 08 E0；10 第9章 | 10/10 用例通过 |
| 排除记录 | 08 排除预注册；09 审计要求 | `exclusion.schema.json` 和日期格式测试 |

## 14. 阶段门判断

### 14.1 P1 Schema 完整

对“首批七类 Schema 的初始范围”，P1 已满足：所有 Schema 合法、示例通过、关键条件约束有测试。对完整标准数据模型，P1 尚未最终关闭，因为空间/时间/证据 payload、跨文件引用和关系约束仍待实现。

### 14.2 P2 E0 正确

对当前实现的分类、单区间 tIoU 和 bbox IoU，P2 已通过 10 个冻结用例。对 39 项指标整体，P2 尚未通过；新增任何指标都必须先增加能够失败的 E0 用例和人工预期。

因此，项目可以进入 E1 的准备工作，但不能直接启动完整 E1 正式运行。进入真实 SUT 冒烟前，还需补齐适配器协议、D0-SMOKE 清单、关系校验和必要的指标路由。

## 15. 已知技术债与处理顺序

| 优先级 | 技术债 | 风险 | 处理阶段 |
|---|---|---|---|
| P0 | 39 项指标尚无完整路由表 | E1 无法证明全部指标可执行 | E1 准备 |
| P0 | 预测适配器协议尚未实现 | 不同 SUT 输出不可比较 | E1 准备 |
| P0 | 无 D0-SMOKE 实际清单 | 无法执行真实媒体冒烟 | 许可门后 |
| P1 | Schema 缺少跨文件关系校验 | `group_id` 和引用可能失配 | E1 准备 |
| P1 | 定位仅支持单实例 | 无法计算 AP@IoU/tIoU | E1/E5 前 |
| P1 | AUC/EER 未与独立库交叉验证 | 复杂边界仍可能有偏差 | E1 前 |
| P2 | 无 Wilson/聚类 bootstrap | 不能开展 E3/E4 正式分析 | E3/E4 前 |
| P2 | 环境只有 requirements，无完整锁文件 | 跨机复现可能漂移 | SUT 接入时 |

## 16. 下一步工作

下一步建议编制并实施：

> `12-E1冒烟测试准备与被测对象适配规范.md`

下一阶段应完成：

1. 39 项指标适用性和输入输出路由表；
2. SUT 适配器接口与示例适配器；
3. D0-SMOKE 清单生成和跨文件关系校验；
4. 外部数据许可登记模板，不在许可通过前下载媒体；
5. 至少一个合成 SUT 和一个真实候选 SUT 的统一输出冒烟；
6. E1 可计算性矩阵与失败原因编码。

E1 准备完成后，应先使用合成 SUT 验证端到端调度和状态处理，再接入真实模型。不得为了填满指标矩阵而伪造定位、证据或多模态输出。
