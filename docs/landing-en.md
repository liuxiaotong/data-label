<div align="right">

**English** | [中文](landing-zh.md)

</div>

<div align="center">

<h1>DataLabel</h1>

<h3>Serverless Human-in-the-Loop Annotation Framework<br/>with LLM Pre-Labeling and Inter-Annotator Agreement</h3>

<p><em>Generate self-contained HTML files for offline annotation. No server, no network, no deployment.</em></p>

<a href="https://github.com/liuxiaotong/data-label">GitHub</a> ·
<a href="https://pypi.org/project/knowlyr-datalabel/">PyPI</a> ·
<a href="https://knowlyr.com">knowlyr.com</a>

</div>

## The Problem

Annotation tools today force a painful choice: heavyweight platforms (Label Studio, Prodigy) that require servers and databases, or throwaway scripts with zero quality guarantees. Neither provides statistical agreement metrics or LLM-assisted acceleration out of the box.

**DataLabel** takes a different approach: generate a single HTML file, send it to annotators, get results back. No server. No Docker. No network required.

## What You Get

- **Serverless HTML Annotation** -- self-contained files with all styles, logic, and data baked in. Works offline, supports dark mode and keyboard shortcuts
- **LLM Pre-Labeling** -- Kimi / OpenAI / Anthropic generate initial labels so annotators start from calibration, not from scratch
- **Inter-Annotator Agreement** -- Cohen's kappa, Fleiss' kappa, Krippendorff's alpha with pairwise agreement matrices and disagreement reports
- **Multi-Strategy Merging** -- majority vote, average, or strict consensus with automatic conflict flagging
- **5 Annotation Types** -- scoring, single choice, multi choice, free text, and ranking (with Borda count merging)
- **Visual Dashboard** -- standalone HTML report with progress tracking, distribution charts, and agreement heatmaps

## Quick Start

```bash
pip install knowlyr-datalabel

# Create annotation interface
knowlyr-datalabel create schema.json tasks.json -o annotator.html

# Optional: LLM pre-labeling
knowlyr-datalabel prelabel schema.json tasks.json -o pre.json -p moonshot

# Merge results + compute agreement
knowlyr-datalabel merge ann1.json ann2.json ann3.json -o merged.json

# Generate analytics dashboard
knowlyr-datalabel dashboard ann1.json ann2.json -o dashboard.html
```

```python
from datalabel import AnnotatorGenerator, ResultMerger

gen = AnnotatorGenerator()
gen.generate(schema=schema, tasks=tasks, output_path="annotator.html")

merger = ResultMerger()
result = merger.merge(["ann1.json", "ann2.json"], strategy="majority")
print(f"Agreement: {result.agreement_rate:.1%}")
```

## Annotation Pipeline

```mermaid
graph LR
    S["Schema"] --> P["LLM Pre-Label"]
    P --> G["HTML Generator"]
    G --> B["Browser Annotation"]
    B --> R["Results"]
    R --> M["Merge + IAA"]
    M --> D["Dashboard"]

    style G fill:#0969da,color:#fff,stroke:#0969da
    style M fill:#8b5cf6,color:#fff,stroke:#8b5cf6
    style D fill:#2da44e,color:#fff,stroke:#2da44e
    style S fill:#1a1a2e,color:#e0e0e0,stroke:#444
    style P fill:#1a1a2e,color:#e0e0e0,stroke:#444
    style B fill:#1a1a2e,color:#e0e0e0,stroke:#444
    style R fill:#1a1a2e,color:#e0e0e0,stroke:#444
```

## MCP Integration

12 MCP tools, 6 resources, and 3 prompt templates for seamless AI IDE integration -- create annotations, merge results, compute IAA, and generate dashboards directly from your editor.

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

## Ecosystem

DataLabel is part of the **knowlyr** data infrastructure:

| Layer | Project | Role |
|:---|:---|:---|
| Discovery | **AI Dataset Radar** | Dataset intelligence and trend analysis |
| Analysis | **DataRecipe** | Reverse analysis, schema extraction, cost estimation |
| Production | **DataSynth** / **DataLabel** | LLM batch synthesis / serverless annotation |
| Quality | **DataCheck** | Rule validation, anomaly detection, auto-fix |
| Audit | **ModelAudit** | Distillation detection, model fingerprinting |

<div align="center">
<br/>
<a href="https://github.com/liuxiaotong/data-label">GitHub</a> ·
<a href="https://pypi.org/project/knowlyr-datalabel/">PyPI</a> ·
<a href="https://knowlyr.com">knowlyr.com</a>
<br/><br/>
<sub><a href="https://github.com/liuxiaotong">knowlyr</a> -- serverless annotation with LLM pre-labeling and inter-annotator agreement</sub>
</div>
