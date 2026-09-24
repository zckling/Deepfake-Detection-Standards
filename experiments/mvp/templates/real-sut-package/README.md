# 真实候选 SUT 接入包目录规范

验证器要求候选包为自包含目录：

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

要求：

- `system.json`：一条被测对象登记，真实模型必须记录权重 SHA-256；
- `run.json`：一条 `experiment_id=E1` 且 `status=completed` 的运行登记；
- `license-register.json`：每个 `source_id` 的独立批准记录，必须包含许可文本路径与哈希、审核人、时间和至少一项批准证据；
- `samples.jsonl`：非空 D0 清单，许可状态精确为 `approved` 或受控的 `approved_*` 值，记录均为 `included`；
- `predictions.jsonl`：每个样本恰好一条预测或失败状态记录；
- `license-evidence/`：许可文本和审核证据必须位于包内，许可文本 SHA-256 必须与登记一致；
- `media/`：实际媒体必须位于包内，清单 SHA-256 必须匹配；不接受 `synthetic://` URI 或 `..` 逃逸路径。

执行验证：

```powershell
python -m tools.sut_package_validation `
  --package <candidate-package> `
  --output <candidate-package>/validation-report.json
```

退出码 `0` 表示该静态接入包满足当前 E1 冒烟验收门；退出码 `1` 表示存在阻断项。通过静态包验证不等于模型性能达标，也不证明许可判断正确；许可批准仍须由授权人员完成并保留证据。

调试时可使用 `--allow-missing-media` 只检查结构；报告会标记 `validation_profile=structure_only` 和 `media_validation_performed=false`，并强制 `ready_for_e1_smoke=false`。

信任边界：当前静态门核对包内许可材料之间的一致性，但包内材料本身不是外部可信批准锚。面对外部或不完全可信提交者时，必须另接评测方控制的许可批准库或数字签名，并把权重、配置和环境摘要绑定到不可变制品；候选包还应先复制到只读暂存区再验证和消费。
