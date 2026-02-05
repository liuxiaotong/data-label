<div align="center">

# DataLabel

**轻量级数据标注工具 - 零服务器依赖的 HTML 标注界面**

[![PyPI](https://img.shields.io/pypi/v/datalabel?color=blue)](https://pypi.org/project/datalabel/)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![MCP](https://img.shields.io/badge/MCP-4_Tools-purple.svg)](#mcp-server)

[快速开始](#快速开始) · [结果合并](#结果合并) · [MCP Server](#mcp-server) · [Data Pipeline 生态](#data-pipeline-生态)

</div>

---

生成独立的 HTML 标注界面，无需部署服务器，浏览器直接打开即可使用。支持多标注员结果合并与一致性分析。

## 核心能力

```
数据 Schema + 任务列表 → 生成 HTML → 浏览器标注 → 导出结果 → 合并分析
```

### 特性一览

| 特性 | 说明 |
|------|------|
| 🚀 **零依赖部署** | 生成的 HTML 包含所有样式和逻辑，无需服务器 |
| 💾 **离线可用** | 标注数据保存在 localStorage，支持断点续标 |
| 👥 **多标注员** | 合并多个标注结果，计算一致性指标 (IAA) |
| 🔗 **DataRecipe 集成** | 直接从 DataRecipe 分析结果生成标注界面 |
| 🤖 **MCP 支持** | 可作为 Claude 的工具使用 |

### 工作流

| 步骤 | 命令 | 产出 |
|------|------|------|
| 1️⃣ 生成界面 | `datalabel generate` | `annotator.html` |
| 2️⃣ 分发标注 | 发送 HTML 给标注员 | 浏览器中完成标注 |
| 3️⃣ 收集结果 | 标注员导出 JSON | `annotator_*.json` |
| 4️⃣ 合并分析 | `datalabel merge` | `merged.json` + 一致性报告 |

## 安装

```bash
pip install datalabel
```

可选依赖：

```bash
pip install datalabel[mcp]      # MCP 服务器
pip install datalabel[dev]      # 开发依赖
pip install datalabel[all]      # 全部功能
```

## 快速开始

### 从 DataRecipe 分析结果生成

```bash
# 从 DataRecipe 分析输出目录生成标注界面
datalabel generate ./analysis_output/my_dataset/
```

<details>
<summary>输出示例</summary>

```
正在从 ./analysis_output/my_dataset/ 生成标注界面...
✓ 生成成功: ./analysis_output/my_dataset/10_标注工具/annotator.html
  任务数量: 50

在浏览器中打开此文件即可开始标注
```

</details>

### 从自定义 Schema 创建

```bash
# 从 Schema 和任务文件创建标注界面
datalabel create schema.json tasks.json -o annotator.html

# 附带标注指南
datalabel create schema.json tasks.json -o annotator.html -g guidelines.md
```

<details>
<summary>Schema 格式示例</summary>

```json
{
  "project_name": "我的标注项目",
  "fields": [
    {"name": "instruction", "display_name": "指令", "type": "text"},
    {"name": "response", "display_name": "回复", "type": "text"}
  ],
  "scoring_rubric": [
    {"score": 1, "label": "差", "description": "回复质量差"},
    {"score": 2, "label": "中", "description": "回复质量一般"},
    {"score": 3, "label": "好", "description": "回复质量好"}
  ]
}
```

</details>

---

## 结果合并

### 合并多个标注员结果

```bash
# 合并三个标注员的结果
datalabel merge ann1.json ann2.json ann3.json -o merged.json

# 使用不同的合并策略
datalabel merge *.json -o merged.json --strategy average
```

<details>
<summary>输出示例</summary>

```
正在合并 3 个标注结果...
  策略: majority
✓ 合并成功: merged.json
  任务总数: 100
  标注员数: 3
  一致率: 78.0%
  冲突数: 22
```

</details>

### 合并策略

| 策略 | 说明 | 适用场景 |
|------|------|----------|
| `majority` | 多数投票，选择最多人选择的分数 | 通用场景 (默认) |
| `average` | 取所有分数的平均值 | 连续评分 |
| `strict` | 仅当所有人一致时才确定，否则标记需审核 | 高质量要求 |

### 计算标注一致性 (IAA)

```bash
datalabel iaa ann1.json ann2.json ann3.json
```

<details>
<summary>输出示例</summary>

```
正在计算 3 个标注结果的 IAA...

标注员间一致性 (IAA) 指标:
  标注员数: 3
  共同任务: 100
  完全一致率: 45.0%

两两一致矩阵:
              ann1.json  ann2.json  ann3.json
ann1.json       100.0%      72.0%      68.0%
ann2.json        72.0%     100.0%      75.0%
ann3.json        68.0%      75.0%     100.0%
```

</details>

---

## 数据格式

### 任务格式

```json
{
  "samples": [
    {
      "id": "TASK_001",
      "data": {
        "instruction": "请解释什么是机器学习",
        "response": "机器学习是..."
      }
    }
  ]
}
```

### 标注结果格式

```json
{
  "metadata": {
    "annotator": "annotator_name",
    "completed_at": "2024-01-01T12:00:00"
  },
  "responses": [
    {
      "task_id": "TASK_001",
      "score": 3,
      "comment": "回复准确且详细"
    }
  ]
}
```

---

## MCP Server

在 Claude Desktop / Claude Code 中直接使用。

### 配置

添加到 `~/Library/Application Support/Claude/claude_desktop_config.json`：

```json
{
  "mcpServers": {
    "datalabel": {
      "command": "uv",
      "args": ["--directory", "/path/to/data-label", "run", "python", "-m", "datalabel.mcp_server"]
    }
  }
}
```

### 可用工具

| 工具 | 功能 |
|------|------|
| `generate_annotator` | 从 DataRecipe 分析结果生成标注界面 |
| `create_annotator` | 从 Schema 和任务创建标注界面 |
| `merge_annotations` | 合并多个标注结果 |
| `calculate_iaa` | 计算标注员间一致性 |

### 使用示例

```
用户: 帮我从 ./output/my_dataset 生成标注界面

Claude: [调用 generate_annotator]
        ✅ 标注界面已生成:
        - 输出路径: ./output/my_dataset/10_标注工具/annotator.html
        - 任务数量: 50

        在浏览器中打开此文件即可开始标注。
```

---

## Data Pipeline 生态

DataLabel 是 Data Pipeline 生态的标注组件：

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           Data Pipeline 生态                                │
├──────────────────┬──────────────────┬──────────────────┬────────────────────┤
│   DataRecipe     │    DataLabel     │    DataSynth     │     DataCheck      │
│     数据分析      │      数据标注     │      数据合成     │       数据质检      │
├──────────────────┼──────────────────┼──────────────────┼────────────────────┤
│  · 逆向工程分析   │  · HTML标注界面   │  · LLM批量生成    │  · 规则验证        │
│  · Schema提取    │  · 多标注员合并    │  · 种子数据扩充   │  · 重复检测        │
│  · 成本估算      │  · IAA一致性计算  │  · 成本追踪       │  · 分布分析        │
│  · 样例生成      │  · 断点续标       │  · 交互/API模式   │  · 质量报告        │
└──────────────────┴──────────────────┴──────────────────┴────────────────────┘
```

### 生态项目

| 项目 | 功能 | 仓库 |
|------|------|------|
| **DataRecipe** | 数据集逆向分析 | [data-recipe](https://github.com/liuxiaotong/data-recipe) |
| **DataLabel** | 轻量级标注工具 | [data-label](https://github.com/liuxiaotong/data-label) |
| **DataSynth** | 数据合成扩充 | [data-synth](https://github.com/liuxiaotong/data-synth) |
| **DataCheck** | 数据质量检查 | [data-check](https://github.com/liuxiaotong/data-check) |

### 端到端工作流

```bash
# 1. DataRecipe: 分析数据集，生成 Schema 和样例
datarecipe deep-analyze tencent/CL-bench -o ./output

# 2. DataLabel: 生成标注界面，人工标注/校准种子数据
datalabel generate ./output/tencent_CL-bench/

# 3. DataSynth: 基于种子数据批量合成
datasynth generate ./output/tencent_CL-bench/ -n 1000

# 4. DataCheck: 质量检查
datacheck validate ./output/tencent_CL-bench/
```

### 四合一 MCP 配置

```json
{
  "mcpServers": {
    "datarecipe": {
      "command": "uv",
      "args": ["--directory", "/path/to/data-recipe", "run", "datarecipe-mcp"]
    },
    "datalabel": {
      "command": "uv",
      "args": ["--directory", "/path/to/data-label", "run", "python", "-m", "datalabel.mcp_server"]
    },
    "datasynth": {
      "command": "uv",
      "args": ["--directory", "/path/to/data-synth", "run", "python", "-m", "datasynth.mcp_server"]
    },
    "datacheck": {
      "command": "uv",
      "args": ["--directory", "/path/to/data-check", "run", "python", "-m", "datacheck.mcp_server"]
    }
  }
}
```

---

## 命令参考

| 命令 | 功能 |
|------|------|
| `datalabel generate <dir>` | 从 DataRecipe 分析结果生成标注界面 |
| `datalabel create <schema> <tasks> -o <out>` | 从自定义 Schema 创建标注界面 |
| `datalabel merge <files...> -o <out>` | 合并多个标注结果 |
| `datalabel merge <files...> -s <strategy>` | 指定合并策略 |
| `datalabel iaa <files...>` | 计算标注员间一致性 |

---

## API 使用

### 生成标注界面

```python
from datalabel import AnnotatorGenerator

generator = AnnotatorGenerator()
result = generator.generate(
    schema={"fields": [...], "scoring_rubric": [...]},
    tasks=[{"id": "1", "data": {...}}],
    output_path="annotator.html",
    guidelines="# 标注指南\n\n请按照以下标准...",
    title="我的标注项目",
)
```

### 合并标注结果

```python
from datalabel import ResultMerger

merger = ResultMerger()
result = merger.merge(
    result_files=["ann1.json", "ann2.json", "ann3.json"],
    output_path="merged.json",
    strategy="majority",
)

print(f"一致率: {result.agreement_rate:.1%}")
print(f"冲突数: {len(result.conflicts)}")
```

---

## 项目架构

```
src/datalabel/
├── generator.py          # HTML 标注界面生成器
├── merger.py             # 标注结果合并 & IAA 计算
├── cli.py                # CLI 命令行工具
├── mcp_server.py         # MCP Server (4 工具)
└── templates/
    └── annotator.html    # Jinja2 HTML 模板
```

---

## License

[MIT](LICENSE)

---

<div align="center">
<sub>为数据标注团队提供轻量级、零部署的标注解决方案</sub>
</div>
