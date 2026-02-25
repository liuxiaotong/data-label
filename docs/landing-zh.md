<div align="right">

[English](landing-en.md) | **中文**

</div>

<div align="center">

<h1>DataLabel</h1>

<h3>零服务器人机协同标注框架<br/>LLM 预标注 · 标注者间一致性分析</h3>

<p><em>生成独立 HTML 文件，离线完成标注。无需服务器、无需网络、无需部署。</em></p>

<a href="https://github.com/liuxiaotong/data-label">GitHub</a> ·
<a href="https://pypi.org/project/knowlyr-datalabel/">PyPI</a> ·
<a href="https://knowlyr.com">knowlyr.com</a>

</div>

## 问题

当前的标注工具迫使你做一个痛苦的选择：重量级平台（Label Studio、Prodigy）需要服务器和数据库，轻量脚本则没有任何质量保证。两者都不提供开箱即用的统计一致性指标或 LLM 辅助加速。

**DataLabel** 采用不同的方式：生成一个 HTML 文件，发给标注员，收回结果。无需服务器、无需 Docker、无需网络。

## 你将获得

- **零服务器 HTML 标注** -- 独立文件内嵌所有样式、逻辑和数据，支持离线使用、暗黑模式和快捷键
- **LLM 预标注** -- Kimi / OpenAI / Anthropic 生成初始标签，标注员从校准开始，而非从零标注
- **标注者间一致性** -- Cohen's kappa、Fleiss' kappa、Krippendorff's alpha，输出两两一致矩阵和分歧报告
- **多策略合并** -- 多数投票、平均值、严格一致三种策略，自动标记冲突
- **5 种标注类型** -- 评分、单选、多选、文本、排序（支持 Borda 计数法合并）
- **可视化仪表盘** -- 独立 HTML 报告，包含进度追踪、分布图表和一致性热力图

## 快速开始

```bash
pip install knowlyr-datalabel

# 创建标注界面
knowlyr-datalabel create schema.json tasks.json -o annotator.html

# 可选：LLM 预标注
knowlyr-datalabel prelabel schema.json tasks.json -o pre.json -p moonshot

# 合并结果 + 计算一致性
knowlyr-datalabel merge ann1.json ann2.json ann3.json -o merged.json

# 生成分析仪表盘
knowlyr-datalabel dashboard ann1.json ann2.json -o dashboard.html
```

```python
from datalabel import AnnotatorGenerator, ResultMerger

gen = AnnotatorGenerator()
gen.generate(schema=schema, tasks=tasks, output_path="annotator.html")

merger = ResultMerger()
result = merger.merge(["ann1.json", "ann2.json"], strategy="majority")
print(f"一致率: {result.agreement_rate:.1%}")
```

## 标注管线

```mermaid
graph LR
    S["Schema 定义"] --> P["LLM 预标注"]
    P --> G["HTML 生成器"]
    G --> B["浏览器标注"]
    B --> R["标注结果"]
    R --> M["合并 + IAA"]
    M --> D["仪表盘"]

    style G fill:#0969da,color:#fff,stroke:#0969da
    style M fill:#8b5cf6,color:#fff,stroke:#8b5cf6
    style D fill:#2da44e,color:#fff,stroke:#2da44e
    style S fill:#1a1a2e,color:#e0e0e0,stroke:#444
    style P fill:#1a1a2e,color:#e0e0e0,stroke:#444
    style B fill:#1a1a2e,color:#e0e0e0,stroke:#444
    style R fill:#1a1a2e,color:#e0e0e0,stroke:#444
```

## MCP 集成

12 个 MCP 工具、6 个资源和 3 个提示词模板，无缝集成 AI IDE -- 在编辑器中直接创建标注、合并结果、计算 IAA 和生成仪表盘。

```json
{
  "mcpServers": {
    "knowlyr-datalabel": {
      "command": "uv",
      "args": ["--directory", "/path/to/data-label", "run", "python", "-m", "datalabel.mcp_server"]
    }
  }
}
```

## 生态系统

DataLabel 是 **knowlyr** 数据基础设施的一部分：

| 层 | 项目 | 职责 |
|:---|:---|:---|
| 发现 | **AI Dataset Radar** | 数据集竞争情报、趋势分析 |
| 分析 | **DataRecipe** | 逆向分析、Schema 提取、成本估算 |
| 生产 | **DataSynth** / **DataLabel** | LLM 批量合成 / 零服务器标注 |
| 质量 | **DataCheck** | 规则验证、异常检测、自动修复 |
| 审计 | **ModelAudit** | 蒸馏检测、模型指纹 |

<div align="center">
<br/>
<a href="https://github.com/liuxiaotong/data-label">GitHub</a> ·
<a href="https://pypi.org/project/knowlyr-datalabel/">PyPI</a> ·
<a href="https://knowlyr.com">knowlyr.com</a>
<br/><br/>
<sub><a href="https://github.com/liuxiaotong">knowlyr</a> -- 零服务器标注框架，LLM 预标注与标注者间一致性分析</sub>
</div>
