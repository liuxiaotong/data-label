"""LLM prompt 模板集中管理。"""

# ============================================================
# 自动预标注 prompts
# ============================================================

PRELABEL_SYSTEM = """\
你是一个专业的数据标注助手。你需要根据标注规范（schema）对给定的数据进行预标注。
请严格按照要求的输出格式返回 JSON 结果。不要添加任何额外的说明文字。"""

PRELABEL_USER_BATCH = """\
## 标注规范

项目: {project_name}
标注类型: {annotation_type}

{annotation_spec}

## 待标注数据

{tasks_json}

## 输出格式

请返回 JSON 数组，每个元素包含:
- "task_id": 任务 ID
- {output_fields}
- "comment": 简短的标注理由（可选）

只返回 JSON 数组，不要包含其他内容。"""

# ============================================================
# 标注质量分析 prompts
# ============================================================

QUALITY_SYSTEM = """\
你是一个标注质量审核专家。你需要分析标注结果，检测可能存在问题的标注，
包括：与内容明显不匹配的标注、标注模式异常（如全部相同分数）、
标注理由与分数不一致等。请给出具体的分析和改进建议。"""

QUALITY_USER = """\
## 标注规范

项目: {project_name}
标注类型: {annotation_type}

{annotation_spec}

## 标注结果（抽样）

{results_json}

## 分析要求

请分析以上标注结果，返回 JSON 对象:
{{
  "issues": [
    {{
      "task_id": "任务ID",
      "issue_type": "suspicious|inconsistent|outlier",
      "severity": "high|medium|low",
      "description": "问题描述",
      "suggestion": "改进建议"
    }}
  ],
  "summary": "整体质量评估摘要"
}}

只返回 JSON，不要包含其他内容。"""

# ============================================================
# 分歧分析 prompts (多标注员)
# ============================================================

DISAGREEMENT_SYSTEM = """\
你是一个标注分歧分析专家。你需要分析多个标注员在同一数据上的标注差异，
找出分歧的原因，并给出解决建议。"""

DISAGREEMENT_USER = """\
## 标注规范

项目: {project_name}
标注类型: {annotation_type}

{annotation_spec}

## 标注分歧数据

以下任务存在标注员之间的分歧:

{disagreements_json}

## 分析要求

请分析每个分歧，返回 JSON 对象:
{{
  "analyses": [
    {{
      "task_id": "任务ID",
      "root_cause": "分歧原因分析",
      "recommended_label": "建议的正确标注",
      "suggestion": "如何避免类似分歧"
    }}
  ],
  "common_patterns": "分歧的共性模式总结",
  "guideline_suggestions": "标注规范改进建议"
}}

只返回 JSON，不要包含其他内容。"""

# ============================================================
# 标注指南生成 prompts
# ============================================================

GUIDELINES_SYSTEM_ZH = """\
你是一个标注指南撰写专家。请根据标注规范和样例数据，
生成一份详细、清晰、可操作的标注指南文档（Markdown 格式）。"""

GUIDELINES_SYSTEM_EN = """\
You are an expert at writing annotation guidelines. Based on the annotation schema \
and sample data, generate a detailed, clear, and actionable annotation guideline \
document in Markdown format."""

GUIDELINES_USER_ZH = """\
## 标注规范

{schema_json}

## 样例数据（部分）

{samples_json}

## 要求

请生成一份完整的标注指南，包含以下章节:
1. **项目概述** - 项目背景和目标
2. **数据字段说明** - 每个字段的含义和展示方式
3. **标注操作说明** - 如何进行标注（根据标注类型）
4. **评判标准** - 详细的评分/选择标准和依据
5. **标注示例** - 基于样例数据的标注示例和解释
6. **边界情况** - 常见的模糊/困难情况及处理方式
7. **注意事项** - 常见错误和避免方法

请直接输出 Markdown 内容，不要用代码块包裹。"""

GUIDELINES_USER_EN = """\
## Annotation Schema

{schema_json}

## Sample Data (partial)

{samples_json}

## Requirements

Generate a comprehensive annotation guideline with the following sections:
1. **Project Overview** - Background and objectives
2. **Data Fields** - Meaning and display of each field
3. **Annotation Instructions** - How to annotate (based on annotation type)
4. **Evaluation Criteria** - Detailed scoring/selection criteria
5. **Annotation Examples** - Examples based on sample data with explanations
6. **Edge Cases** - Common ambiguous/difficult cases and how to handle them
7. **Common Pitfalls** - Frequent mistakes and how to avoid them

Output Markdown content directly, do not wrap in code blocks."""
