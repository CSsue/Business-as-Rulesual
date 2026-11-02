# 论文复现

## 准备工作

- 拉取 git clone https://github.com/oYoungCo/Business-as-Rulesual.git
- uv创建虚拟环境，py3.11
- 下载依赖uv pip install -r requirements.txt
- 配置DeepSeekAPI
- 补充下载`python-dotenv`， httpx[socks]

## 第一阶段复现

全部 409 篇的 Stage I 输出已完成。数据质量整体很好，格式统一，绝大多数文档都提取出了合理的规则。

### 问题

1. 部分输出格式不规范

Index 174、176、179、180、187 等，规则行的开头是 < 而不是 <<，或者缺少闭合的 >。这会影响后续 Stage II 的解析和评测。

2. 少数输出混入了英文

Index 110、222、300、354、355、404，槽位名和动作是英文的。模型自己切换了语言。

3. Index 86 出现了 <<None, None, None>, 扣除费用并打印凭条>

这是无效规则，Slot Type、Logical Operator、Reference Value 全是 None。

4. Index 203 和 204 内容重复

Index 203 和 204 的规则几乎一样，但 204 的动作描述更完整。

### 结论

原始数据集没问题，复现过程（Prompt 设计/模型特性）引入的噪声。

## 第二阶段复现

### F1与论文相差过大

## 调整策略

### 重写新的prompt

槽位对齐率从 59.62% 提升到 82.89%，低对齐率文档从 142 篇降到 6 篇。

# Business as Rulesual: A Benchmark and Framework for Business Rule Flow Modeling with LLMs

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Dataset: BREX](https://img.shields.io/badge/Dataset-BREX-blue.svg)](dataset/BREX.jsonl)
[![Hugging Face](<https://img.shields.io/badge/%F0%9F%A4%97%20Hugging%20Face-BREX-ffd21e>)](https://huggingface.co/datasets/XiaopiYu/BREX/)

## 📖 Abstract

Extracting structured procedural knowledge from unstructured business documents is a critical bottleneck in process automation. Prior work has largely focused on extracting linear action flows, often overlooking the complex logical structures—such as **conditional branching** and **parallel execution**—pervasive in real-world regulatory documents.

To bridge this **"Logic Gap,"** we introduce:

1. **BREX (Business Rule EXtraction Benchmark):** A carefully curated dataset comprising **409** real-world business documents and **2,855** expert-annotated rules spanning over 30 vertical domains.
2. **ExIde (Executable-grounded Idealization):** A structure-aware reasoning framework that bridges natural language regulations and executable rule flows using **pseudo-code generation** as an inductive bias.

Our experiments across 13 state-of-the-art LLMs reveal that executable grounding significantly outperforms standard prompting, and reasoning-optimized models demonstrate a distinct advantage in tracing long-range dependencies.

## 🌟 Key Features

* **Real-world Complexity:** Covers Scientific, Industrial, Administrative, and Financial regulations, not just simple instructional texts.
* **Structured Annotation:** Rules are annotated as `(Condition, Action)` pairs with explicit **Sequential**, **Conditional**, and **Parallel** dependencies.
* **ExIde Framework:** A decompose-and-reason strategy leveraging intermediate executable representations.

## 📂 Dataset: [BREX](dataset/BREX.jsonl)

The [BREX](dataset/BREX.jsonl) dataset focuses on **Business Rule Flow Modeling**. Unlike previous datasets, it explicitly annotates the logic that governs *when* actions occur.

| Metric                              | Count                             |
| :---------------------------------- | :-------------------------------- |
| **Documents**                 | 409                               |
| **Atomic Rules**              | 2,855                             |
| **Domains**                   | 30+ (Finance, Law, Admin, etc.)   |
| **Dependency Types**          | Sequential, Conditional, Parallel |
| **Inter-Annotator Agreement** | Kappa: 0.911 (Excellent)          |

### Data Format

The dataset is provided in `.jsonl` format, where each line represents a distinct business scenario.

| Field (Original)   | Field (English) | Description                                                                     |
| :----------------- | :-------------- | :------------------------------------------------------------------------------ |
| `领域`           | Domain          | The vertical domain of the business process (e.g., Healthcare, Finance).        |
| `意图`           | Intent          | The specific business intent or scenario (e.g., "Medical Checkup Appointment"). |
| `文本`           | Text            | The unstructured raw business document.                                         |
| `业务规则二元组` | Rule Pairs      | Atomic business rules formatted as`<Condition, Action>`.                      |
| `依赖关系`       | Dependencies    | Logical dependencies between rules (Sequential, Conditional, Parallel).         |

## 🚀 Methodology: ExIde Framework

ExIde adopts a two-stage strategy to recover the rule flow graph $G=(V, E)$:

### Stage I: Structure-Aware Rule Extraction

We employ **Executable Grounding (Prompt 5)**. The model first translates the text into an intermediate pseudo-code representation (using primitives like `select_from`,  `execute_action`) before extracting structured rules. This encourages early resolution of nested logic.

### Stage II: Dependency Graph Reconstruction

We treat dependency identification as a pairwise classification problem to identify **Sequential**, **Conditional**, and **Parallel** relationships, constructing a global dependency graph.

<p align="center">
  <img src="assets/methodology.png" alt="ExIde Framework Overview" width="800">
  <br>
  <em>Figure: Overview of the ExIde framework.</em>
</p>

## 🛠️ Quick Start

### Usage

```bash
conda create -n brex python=3.10
conda activate brex
pip install -r requirements.txt
```

### 2. Configuration

To run the LLM-based extraction, you need to configure your API key. We use a .env file to manage sensitive credentials securely.

Create a `.env` file in the root directory.

Add your API Key (e.g., Alibaba DashScope/DeepSeek) as follows:

```
DASHSCOPE_API_KEY=sk-your_api_key_here
```

### 3. Running the Extraction

#### Step 1: Business Rule Extraction

This script reads the raw business documents (prompts) and extracts atomic business rules (Conditions & Actions).

**Input**： `./business_rules.xlsx`

```bash
python business_rules_extraction.py
```

**Output**: Generates a `business_rules_results.xlsx` containing the extracted rule pairs.

#### Step 2: Dependency Identification

This script analyzes the extracted rules to identify logical relationships (Sequential, Conditional, Parallel).

**Input**：`./results.xlsx`

```bash
python dependency_extraction.py
```

**Output**: Generates a `dependency_results.xlsx`.

## 📝 Citation

If you find this work helpful, please cite our paper:

```bibtex
@article{yang2025business,
  title={Business as Rulesual: A Benchmark and Framework for Business Rule Flow Modeling with LLMs.},
  author={Yang, Chen and Xu, Ruping and Li, Ruizhe and Cao, Bin and Fan, Jing},
  journal={CoRR},
  year={2026}
}

```

Business-as-Rulesual
├─ README.md
├─ assets
│  ├─ dataset.png
│  └─ methodology.png
├─ business_rules_extraction
│  ├─ business_rules_extraction.py
│  └─ denpendency_extraction.py
├─ dataset
│  └─ BREX.jsonl
└─ requirements.txt

```

```
