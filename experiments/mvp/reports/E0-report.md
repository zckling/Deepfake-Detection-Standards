# E0 计算链路单元验证报告

> 执行日期：2026-09-23
>
> 用例版本：D0-FIXTURE 1.0.0
>
> 绝对浮点容差：`1e-12`
>
> 机器可读结果：`e0-report.json`

## 1. 执行结论

本轮共执行 10 个冻结用例，通过 10 个，失败 0 个。结果仅证明当前参考计算器在这些已登记边界上与人工预期一致，不代表全部 39 项指标已经完成验证。

| case_id | 类型 | 验证内容 | 结果 |
|---|---|---|---|
| E0-BIN-PERFECT | 二分类 | 完美预测的上界、混淆矩阵和 AUC/EER 方向 | 通过 |
| E0-BIN-INVERSE | 二分类 | 完全反向预测的下界 | 通过 |
| E0-BIN-CONSTANT | 二分类 | 并列分数、阈值等号和 AUC/EER 插值 | 通过 |
| E0-BIN-SINGLE-CLASS | 二分类 | 单一类别下未定义指标返回 `null` | 通过 |
| E0-TEMPORAL-EXACT | 时间定位 | 完全重合 tIoU | 通过 |
| E0-TEMPORAL-PARTIAL | 时间定位 | 部分重合 tIoU | 通过 |
| E0-TEMPORAL-DISJOINT | 时间定位 | 相邻但不重叠区间 | 通过 |
| E0-BBOX-PARTIAL | 空间定位 | 部分重合 bbox IoU | 通过 |
| E0-BBOX-DISJOINT | 空间定位 | 完全分离 bbox | 通过 |
| E0-TEMPORAL-INVALID | 异常处理 | 零长度区间必须抛出 `ValueError` | 通过 |

## 2. 同轮自动测试

同一实现还通过 17 项单元测试，覆盖：

- 七类 Schema 的 Draft 2020-12 合法性；
- 七条 Schema 示例；
- FAKE 样本条件必填约束；
- 分数范围和日期时间格式；
- JSONL 合法、非法和解析失败记录汇总；
- 二分类、tIoU 和 bbox IoU 边界；
- 预期值被篡改时 E0 必须失败；
- UTF-8 JSON 报告写入和读取。

## 3. 发现并修正的问题

1. 初版 JSONL 汇总会把一条记录的多个字段错误误计为多条无效记录。现改为“每条无效记录一条聚合消息”，消息内保留全部字段错误。
2. JSON Schema 的 `format` 默认只是注释，不会自动验证日期时间。现显式启用 `FormatChecker`，非法日期时间能够被拒绝。

## 4. 未覆盖范围

- AP、AR、Wilson 区间和聚类 bootstrap；
- 多片段匹配、AP@tIoU 和边界容差；
- mask、polygon、track 和 AP@IoU；
- 失败样本进入正式指标分母的端到端处理；
- 真实 SUT、真实媒体和跨来源组统计；
- A—H 全部 39 项指标的完整计算路径。

因此，本轮结果只能作为进入 E1 开发前的计算链路证据，不能用于能力等级判定。
