# 阶段1调研：GitHub/Benchmark 项目与标准转化矩阵

> 项目：《深度伪造识别标准研究》  
> 本文用途：支撑“国内外研究现状调研”阶段，将公开 GitHub 项目、数据集和 benchmark 转化为本项目可使用的能力维度、评价指标、试验方法和标准条款素材。  
> 编制日期：2026-08-03

## 1. 调研结论

GitHub 上与深度伪造识别相关的项目较多，但大多数属于以下三类：

1. **检测模型实现**：关注某个算法或网络结构，通常只报告准确率、AUC、F1 等模型性能。
2. **数据集与 benchmark**：提供统一数据、基线模型、评价指标和训练/测试协议，适合转化为本项目的试验方法。
3. **综述型资源清单**：汇总论文、代码、数据集、竞赛和方向分类，适合支撑国内外研究现状章节。

目前未发现与本项目完全等价的开源项目，即“深度伪造视频识别能力体系 + 指标体系 + 指标计算方法 + 能力等级划分 + 评估标准草案”的完整组合。因此，本项目的关键工作不是复现某一个 detection benchmark，而是把已有 benchmark 中分散的模型评价方法，上升为可执行、可复现、可分级的标准化评估体系。

## 2. 重点参考项目

| 序号 | 项目 | 类型 | 主要特点 | 对本项目的直接价值 |
|---|---|---|---|---|
| 1 | [DeepfakeBench](https://github.com/SCLBD/DeepfakeBench) | 综合检测 benchmark | 统一平台、统一数据管理、集成多种检测器、标准化评价协议；当前 README 显示支持 36 个检测方法，包含 frame-level/video-level AUC、ACC、EER、PR、AP 等指标。 | 可作为“统一评估流程、准确度指标、跨数据集泛化测试、benchmark 组织方式”的核心参考。 |
| 2 | [DF40](https://github.com/YZY-stack/DF40) | 下一代深度伪造数据集与 benchmark | 包含 40 种深度伪造技术，覆盖 face-swapping、face-reenactment、entire face synthesis、face editing 等类型，并给出多种训练/测试协议。 | 可支撑“已知/未知伪造方法”“同域/跨域”“一种方法训练、多方法测试”的泛化性试验设计。 |
| 3 | [AV-Deepfake1M](https://github.com/ControlNet/AV-Deepfake1M) | 大规模音视频伪造数据集与挑战 | 覆盖视频伪造、音频伪造、音视频共同伪造；元数据包含 `modify_type`、`fake_segments`、`audio_fake_segments`、`visual_fake_segments`；提供 AP/AR/AUC 评价接口。 | 非常适合支撑“音频伪造、视频伪造、多模态混合伪造、片段级定位、取证能力”评价。 |
| 4 | [LAV-DF](https://github.com/ControlNet/LAV-DF) | 音视频伪造检测与时间定位 benchmark | 面向 audio-visual forgery detection and localization，使用 AP@0.5、AP@0.75、AP@0.95、AR@K 等时间定位指标。 | 可支撑“伪造片段定位精度”和“多模态证据定位”条款。 |
| 5 | [FakeAVCeleb](https://github.com/DASH-Lab/FakeAVCeleb) | 音视频多模态数据集 | 同时包含 deepfake videos 与 synthesized cloned audios，并提供单模态/多模态训练评估代码。 | 可用于“音视频一致性检测能力”和“音频伪造识别能力”调研。 |
| 6 | [Audio-Deepfake-Detection](https://github.com/media-sec-lab/Audio-Deepfake-Detection) | 音频深度伪造检测资料库 | 汇总音频伪造检测数据集、论文、代码和常用指标，包含 EER、t-DCF 等。 | 可补齐项目文档中“音频伪造识别”部分，避免能力体系偏向视频画面。 |
| 7 | [Awesome-Deepfakes-Detection](https://github.com/Daisy-Zhang/Awesome-Deepfakes-Detection) | 综述型资源清单 | 按 datasets、competitions、generalization、interpretability、localization、multi-modal、robustness、adversarial attack 等分类。 | 可作为阶段1文献检索索引，支撑研究现状章节结构。 |
| 8 | [AI-Generated-Video-Detection](https://github.com/dxhou/AI-Generated-Video-Detection) | AI 生成视频检测资源清单 | 汇总 video-centered works、detection layers、generation settings、benchmark tracks，并持续跟踪 2024-2026 年新 benchmark。 | 可用于扩展“生成式视频/文本到视频”检测方向，尤其是非人脸视频伪造。 |

## 3. 与本项目能力体系的映射

| 本项目能力维度 | 可参考项目 | 可借鉴内容 | 标准化转化方向 |
|---|---|---|---|
| 识别伪造模态能力 | AV-Deepfake1M、LAV-DF、FakeAVCeleb、Audio-Deepfake-Detection | 音频、视频、音视频混合伪造的样本组织与标签字段 | 规定被测系统应声明支持的输入模态，并按音频、视频、图像、文本、多模态分别测试。 |
| 识别伪造对象能力 | DeepfakeBench、DF40、AI-Generated-Video-Detection | 人脸换脸、表情驱动、整脸合成、生成视频等任务 | 标准中应增加对象覆盖矩阵：人脸、物体目标、场景、文字。现有开源资源偏人脸，武器装备等目标需自建或专项补充。 |
| 识别准确度 | DeepfakeBench、AV-Deepfake1M、LAV-DF | AUC、ACC、EER、PR、AP、AR 等指标 | 建立视频级、帧级、片段级、区域级准确度指标；区分“检出真伪”和“定位伪造位置”。 |
| 识别效率 | DeepfakeBench | 统一预处理、数据加载、训练/评估流程 | 标准中应要求记录平均处理时长、FPS、吞吐量、硬件配置、模型大小和资源占用。 |
| 鲁棒性 | DeepfakeBench、DF40、AV-Deepfake1M++、Awesome-Deepfakes-Detection | 压缩、跨数据集、跨伪造方法、现实扰动相关评估 | 建议设置压缩、噪声、分辨率变化、重编码、裁剪、遮挡等扰动组，计算性能下降率。 |
| 泛化性 | DF40、DeepfakeBench | 同域/跨域、同伪造类型/异伪造类型、一对多测试协议 | 直接转化为四象限测试：已知方法+已知区域、已知方法+未知区域、未知方法+已知区域、未知方法+未知区域。 |
| 可解释性 | Awesome-Deepfakes-Detection、AV-Deepfake1M、LAV-DF | 解释性、定位、证据可视化方向的论文和 benchmark | 标准中可规定输出热力图、时间片段、伪造区域、跨模态冲突证据，并评价证据与人工标注的一致性。 |
| 取证能力 | AV-Deepfake1M、LAV-DF、C2PA/Content Credentials 相关项目 | fake segment、audio/visual fake segment、来源/元数据/证据链思想 | 标准中应要求输出检测依据、定位结果、置信度、日志、版本、处理参数，形成可复核评估报告。 |
| 易用性 | DeepfakeBench、C2PA 开源工具链 | Docker、SDK、CLI、Python 包、统一配置等工程化做法 | 标准中可规定接口形式、部署时间、平台兼容性、批处理能力、报告导出能力、错误处理能力。 |

## 4. 建议纳入本项目指标体系的外部指标

### 4.1 准确度类

| 指标 | 来源参考 | 建议标准化定义 |
|---|---|---|
| Accuracy / ACC | DeepfakeBench | 被测样本中真伪判断正确的比例。应分别报告总体 ACC、真实样本 ACC、伪造样本 ACC。 |
| Precision / 查准率 | 通用检测指标 | 判为伪造的样本中真实为伪造的比例，用于衡量误报风险。 |
| Recall / 查全率 | 通用检测指标 | 实际伪造样本中被检出的比例，用于衡量漏报风险。 |
| F1 | 基于查准率和查全率 | 查准率与查全率的调和平均，适合类别不均衡时使用。 |
| AUC | DeepfakeBench、AV-Deepfake1M、NIST GenAI | 衡量不同阈值下真伪区分能力，适合开放评分型检测系统。 |
| EER | DeepfakeBench、Audio-Deepfake-Detection、NIST GenAI | 误受率与误拒率相等时的错误率，常用于鉴伪/反欺骗场景。 |
| AP / mAP | AV-Deepfake1M、LAV-DF | 用于区域级或片段级检测，评价排序质量与定位检出能力。 |

### 4.2 定位与取证类

| 指标 | 来源参考 | 建议标准化定义 |
|---|---|---|
| 时间片段 AP@tIoU | AV-Deepfake1M、LAV-DF | 在给定 temporal IoU 阈值下，评价伪造片段定位准确性。 |
| AR@K | AV-Deepfake1M、LAV-DF | 在最多输出 K 个候选片段时的平均召回率。 |
| 区域 IoU | 图像/视频篡改定位任务 | 预测伪造区域与人工标注区域的交并比。 |
| 证据覆盖率 | 本项目扩展 | 被测系统输出的证据是否覆盖实际伪造模态、伪造对象、伪造区域或伪造片段。 |
| 证据可复核率 | 本项目扩展 | 专家或复核系统能够根据输出证据复现判断结论的比例。 |

### 4.3 鲁棒性与泛化性类

| 指标 | 来源参考 | 建议标准化定义 |
|---|---|---|
| 跨数据集性能保持率 | DeepfakeBench、DF40 | 跨数据集测试性能 / 同数据集测试性能。 |
| 未知伪造方法检出率 | DF40 | 训练或调参阶段未出现的伪造方法在测试阶段的检出率。 |
| 未知伪造区域检出率 | 本项目文档要求 | 伪造区域类型或位置未在训练/调参阶段出现时的检出率。 |
| 扰动后性能下降率 | 鲁棒性 benchmark | 原始测试性能与压缩、噪声、重编码、缩放、裁剪等扰动后性能的相对下降。 |
| 最差场景性能 | 标准建议 | 各测试子集中的最低性能，用于避免平均分掩盖薄弱场景。 |

### 4.4 效率、复杂性、易用性类

| 指标 | 建议标准化定义 |
|---|---|
| 平均识别时延 | 单个视频从输入到输出识别结果的平均时间。 |
| 实时率 | 视频时长 / 处理时长。大于 1 表示可快于实时处理。 |
| FPS | 每秒可处理帧数。 |
| 吞吐量 | 单位时间可处理的视频数量或总时长。 |
| 参数量 | 模型可训练参数总数。 |
| 模型文件大小 | 模型权重、配置、依赖包的存储大小。 |
| 算力需求 | CPU/GPU/NPU、显存、内存、操作系统要求。 |
| 部署复杂度 | 部署步骤数、部署耗时、依赖服务数量、是否支持容器化。 |
| 接口易用性 | 是否支持 CLI/API/SDK/批处理/报告导出。 |

## 5. 可转化为标准条款的初稿表达

以下不是正式标准条款，而是后续拟制标准时可展开的条款素材。

### 5.1 被测对象声明要求

被测对象应声明其支持的识别能力范围，包括但不限于：

- 支持的输入模态：音频、视频、图像、文本、多模态混合；
- 支持的伪造对象：人脸、物体目标、场景、文字；
- 支持的输出粒度：视频级、帧级、片段级、区域级；
- 支持的证据类型：置信度、伪造区域、伪造片段、热力图、跨模态不一致证据、日志和报告；
- 支持的运行环境：硬件、操作系统、部署方式、接口方式。

### 5.2 试验数据构成要求

评估用数据集宜覆盖以下类别：

- 真实样本与伪造样本；
- 已知伪造方法样本与未知伪造方法样本；
- 已知伪造区域样本与未知伪造区域样本；
- 音频伪造、视频伪造、图像伪造、文本伪造、多模态混合伪造样本；
- 人脸、物体目标、场景、文字等不同伪造对象样本；
- 不同压缩率、分辨率、噪声、裁剪、重编码、遮挡等扰动样本。

### 5.3 泛化性试验分组要求

泛化性试验建议至少包含四组：

| 组别 | 伪造方法 | 伪造区域 | 评价目的 |
|---|---|---|---|
| G1 | 已知 | 已知 | 基础能力验证 |
| G2 | 已知 | 未知 | 区域迁移能力验证 |
| G3 | 未知 | 已知 | 方法泛化能力验证 |
| G4 | 未知 | 未知 | 开放场景泛化能力验证 |

每组均应分别计算准确度、查全率、查准率、AUC/EER，以及必要时的片段级 AP/AR 或区域 IoU。

### 5.4 结果报告要求

评估报告应至少包含：

- 被测对象名称、版本、配置、运行环境；
- 测试数据来源、样本规模、模态分布、对象分布、伪造方法分布；
- 各指标计算结果；
- 各测试子集结果；
- 鲁棒性和泛化性下降情况；
- 取证证据输出示例；
- 失败样本分析；
- 能力等级判定结果。

## 6. 当前外部资源的不足与本项目补强方向

| 现有资源不足 | 对本项目的影响 | 补强建议 |
|---|---|---|
| 多数 benchmark 偏人脸伪造 | 难以直接覆盖“武器装备等目标” | 设计“重要人物 + 装备目标 + 场景 + 文字”的对象扩展测试集。 |
| 多数指标偏模型性能 | 难以评价系统部署、取证、易用性 | 增加系统能力指标：接口、部署、批处理、日志、报告、兼容性。 |
| 取证能力评价不充分 | 难以支撑标准应用中的复核需求 | 建立证据输出、证据定位、证据可复核率指标。 |
| 文本伪造/画面文字篡改覆盖不足 | 难以覆盖字幕、编号、标牌、文件标识等风险 | 增加 OCR + 文本一致性/篡改检测测试任务。 |
| 标准等级划分缺失 | benchmark 只能排序，不能形成能力等级 | 建立一级、二级、三级、四级能力等级或合格/增强/优秀等级。 |
| 数据许可复杂 | 公开数据不一定能直接用于标准验证 | 在标准草案中区分“公开参考数据集”和“标准验证数据集”。 |

## 7. 下一步建议

建议把阶段1继续推进为三个小产出：

1. **国内外研究现状调研报告框架**  
   按检测方法、数据集、评价指标、鲁棒性泛化性、取证解释性、标准/规范六类写。

2. **候选 benchmark 测试方案**  
   以 DeepfakeBench + DF40 + AV-Deepfake1M/LAV-DF 为基础，设计一套最小可行的标准验证实验。

3. **指标字典初稿**  
   对每个指标写清：定义、适用对象、输入、输出、计算公式、测试条件、等级划分建议。

## 8. 参考链接

- DeepfakeBench: https://github.com/SCLBD/DeepfakeBench
- DF40: https://github.com/YZY-stack/DF40
- AV-Deepfake1M: https://github.com/ControlNet/AV-Deepfake1M
- LAV-DF: https://github.com/ControlNet/LAV-DF
- FakeAVCeleb: https://github.com/DASH-Lab/FakeAVCeleb
- Audio-Deepfake-Detection: https://github.com/media-sec-lab/Audio-Deepfake-Detection
- Awesome-Deepfakes-Detection: https://github.com/Daisy-Zhang/Awesome-Deepfakes-Detection
- AI-Generated-Video-Detection: https://github.com/dxhou/AI-Generated-Video-Detection
- NIST GenAI evaluation program: https://ai-challenges.nist.gov/genai
- NIST GenAI Deepfakes 2026: https://ai-challenges.nist.gov/forensics
- NIST synthetic content report: https://www.nist.gov/publications/reducing-risks-posed-synthetic-content-overview-technical-approaches-digital-content
- OpenMFC: https://mfc.nist.gov/
- C2PA specification: https://spec.c2pa.org/specifications/specifications/2.2/specs/C2PA_Specification.html
