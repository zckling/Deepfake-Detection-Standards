# 深度伪造识别标准 MVP 实验工具

本目录实现 `10-最小可行实验实施方案.md` 的 E0 基础和 `12-E1冒烟测试准备与被测对象适配规范.md` 的合成预检：七类 JSON Schema、受控词表、D0-FIXTURE、E0 核心指标、39 项指标路由、跨文件关系校验、SUT 适配器协议和 D0-SMOKE 逻辑夹具。

当前 E1 结果只服务于管线预检。逻辑夹具不含媒体字节，合成 SUT 会读取真值，因而不代表真实检测性能，不产生正式能力等级。

## 环境

- Python 3.11 或更高版本；
- `jsonschema` 4.25 或兼容的 4.x 版本；
- 核心指标参考实现仅使用 Python 标准库。

安装依赖：

```powershell
python -m pip install -r requirements.txt
```

## 运行全部测试

在本目录执行：

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
python -m unittest discover -s tests -p 'test_*.py' -v
```

当前预期结果为 63 项测试全部通过。

## 执行 E0 冻结用例

```powershell
python -m tools.run_e0 `
  --cases fixtures/e0-cases.json `
  --output reports/e0-report.json
```

进程退出码为 `0` 表示全部用例与人工预期一致；退出码为 `1` 表示至少一个用例失败。报告不会覆盖用例文件。

## 校验 JSONL

```powershell
python -m tools.schema_validation `
  --schema schemas/prediction.schema.json `
  --jsonl <预测结果.jsonl>
```

输出包含总记录数、合法记录数、无效记录数和逐行错误。每条无效记录聚合为一项错误，项内保留全部字段问题。

## 执行 E1 合成预检

```powershell
python -m tools.run_e1
```

默认把 12 条 D0-SMOKE 逻辑样本送入 perfect 和 inverse 两个真值感知合成适配器，生成统一预测、运行登记、39×2 可计算性矩阵和预检报告。输出位于 `reports/e1-synthetic/`。这些结果只能验证链路的正反向边界，不能用于模型排名或阈值校准。

## 验证真实候选 SUT 接入包

```powershell
python -m tools.sut_package_validation `
  --package <候选包目录> `
  --output <候选包目录>/validation-report.json
```

默认要求包内存在真实媒体并核对 SHA-256；同时检查真实/合成身份、权重哈希、E1/D0 状态、许可标志、Schema、输入输出基数、引用关系和 39 项可计算性。目录规范见 `templates/real-sut-package/README.md`。

## 比较两次运行的重复性

```powershell
python -m tools.repeatability `
  --first <run-1-predictions.jsonl> `
  --second <run-2-predictions.jsonl> `
  --score-tolerance 0 `
  --output <repeatability-report.json>
```

比较器按 `sample_id` 对齐，忽略 `run_id` 与单样本耗时后计算语义哈希，并分别报告状态、标签、分数、其他语义和缺失记录差异。确定性 SUT 使用零容差；随机性 SUT 的容差必须预注册，不能观察结果后调整。

## 目录说明

| 路径 | 作用 |
|---|---|
| `schemas/` | 七类 Draft 2020-12 JSON Schema |
| `vocabularies/` | D/M/O/R/G、状态和方法族受控词表 |
| `fixtures/e0-cases.json` | E0 冻结输入与人工预期 |
| `fixtures/schema-examples/` | 每个 Schema 的合法示例 |
| `config/metric-routing.json` | 冻结 39 项指标的任务、输入、输出、能力和计算器状态路由 |
| `templates/` | 许可登记、真实 SUT 适配器和验收清单模板 |
| `tools/schema_validation.py` | 单记录和 JSONL Schema 校验器 |
| `tools/metrics.py` | 分类、定位与 D-1/D-2/D-4 性能指标参考实现 |
| `tools/run_e0.py` | 冻结用例运行和对照报告生成器 |
| `tools/metric_routing.py` | 39 项指标路由表校验和可计算性矩阵 |
| `tools/relationship_validation.py` | 样本、父子、分区和预测引用关系校验 |
| `tools/sut_adapter.py` | SUT 协议和合成适配器 |
| `tools/d0_smoke.py` | 无媒体字节的 D0-SMOKE 逻辑清单生成器 |
| `tools/run_e1.py` | E1 合成预检执行和产物写出器 |
| `tools/sut_package_validation.py` | 真实候选 SUT 接入包静态验收门 |
| `tools/repeatability.py` | E2 两次运行语义一致性和耗时均值比较器 |
| `tests/` | Schema、指标和运行器测试 |
| `reports/e0-report.json` | 最近一次正式 E0 机器可读报告 |
| `reports/e1-synthetic/` | 最近一次 E1 合成预检产物；不是正式性能报告 |

## 当前限制

- 尚未实现 39 项指标的完整生产计算器；
- 尚未接入真实媒体、外部数据集或检测模型；
- 已实现来源组、父子、分区和预测引用关系校验，但近重复媒体检测仍待实现；
- D0-SMOKE 当前仅为逻辑清单，不含真实媒体字节；
- 尚未接入真实 SUT；
- AUC/EER 实现用于小规模 E0 参考验证，进入正式实验前还需与独立实现交叉核对；
- 时间和空间定位目前只覆盖单区间与轴对齐框，尚未实现 AP、mask、polygon 和 track。
