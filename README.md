# DataLabel

轻量级数据标注工具 - 生成独立的 HTML 标注界面，无需服务器，浏览器直接打开即可使用。

## 特性

- **零依赖部署** - 生成的 HTML 文件包含所有样式和逻辑，无需服务器
- **离线可用** - 标注数据保存在浏览器 localStorage，支持断点续标
- **多标注员支持** - 合并多个标注结果，计算一致性指标
- **DataRecipe 集成** - 直接从 DataRecipe 分析结果生成标注界面
- **MCP 协议支持** - 可作为 Claude 的工具使用

## 安装

```bash
pip install datalabel

# 安装 MCP 支持
pip install datalabel[mcp]
```

## 快速开始

### 从 DataRecipe 分析结果生成

```bash
# 从 DataRecipe 分析输出目录生成标注界面
datalabel generate ./analysis_output/my_dataset/
```

生成的 HTML 文件位于 `./analysis_output/my_dataset/10_标注工具/annotator.html`，在浏览器中打开即可开始标注。

### 从自定义 Schema 创建

```bash
# 从 Schema 和任务文件创建标注界面
datalabel create schema.json tasks.json -o annotator.html
```

### 合并标注结果

```bash
# 合并多个标注员的结果
datalabel merge annotator1.json annotator2.json annotator3.json -o merged.json

# 使用不同的合并策略
datalabel merge *.json -o merged.json --strategy average
```

### 计算标注一致性

```bash
# 计算 IAA (Inter-Annotator Agreement)
datalabel iaa annotator1.json annotator2.json annotator3.json
```

## 合并策略

| 策略 | 说明 |
|------|------|
| `majority` | 多数投票，选择最多标注员选择的分数 |
| `average` | 取所有分数的平均值 |
| `strict` | 仅当所有标注员一致时才确定，否则标记为需审核 |

## 数据格式

### Schema 格式

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

## MCP 集成

在 Claude Desktop 配置文件中添加：

```json
{
  "mcpServers": {
    "datalabel": {
      "command": "datalabel-mcp"
    }
  }
}
```

或使用 Python 模块方式：

```json
{
  "mcpServers": {
    "datalabel": {
      "command": "python",
      "args": ["-m", "datalabel.mcp_server"]
    }
  }
}
```

### MCP 工具

| 工具 | 说明 |
|------|------|
| `generate_annotator` | 从 DataRecipe 分析结果生成标注界面 |
| `create_annotator` | 从 Schema 和任务创建标注界面 |
| `merge_annotations` | 合并多个标注结果 |
| `calculate_iaa` | 计算标注员间一致性 |

## 与 DataRecipe 协同

DataLabel 是 DataRecipe 生态的一部分：

```
DataRecipe (数据分析) → DataLabel (数据标注) → DataSynth (数据合成) → DataCheck (数据质检)
```

从 DataRecipe 分析结果生成标注界面：

```python
from datalabel import AnnotatorGenerator

generator = AnnotatorGenerator()
result = generator.generate_from_datarecipe(
    analysis_dir="./analysis_output/my_dataset/",
)
print(f"标注界面已生成: {result.output_path}")
```

## API 使用

### 生成标注界面

```python
from datalabel import AnnotatorGenerator

generator = AnnotatorGenerator()

# 从 Schema 和任务生成
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

# 合并多个标注结果
result = merger.merge(
    result_files=["ann1.json", "ann2.json", "ann3.json"],
    output_path="merged.json",
    strategy="majority",
)

print(f"一致率: {result.agreement_rate:.1%}")
print(f"冲突数: {len(result.conflicts)}")
```

### 计算 IAA

```python
from datalabel import ResultMerger

merger = ResultMerger()
metrics = merger.calculate_iaa(["ann1.json", "ann2.json", "ann3.json"])

print(f"完全一致率: {metrics['exact_agreement_rate']:.1%}")
print(f"两两一致矩阵: {metrics['pairwise_agreement']}")
```

## 开发

```bash
# 克隆仓库
git clone https://github.com/yourusername/data-label.git
cd data-label

# 安装开发依赖
pip install -e ".[dev]"

# 运行测试
pytest
```

## License

MIT
