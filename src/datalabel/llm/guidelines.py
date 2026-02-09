"""标注指南生成 — 使用 LLM 根据 schema 和样例数据自动生成标注指南。"""

from __future__ import annotations

import json
from dataclasses import dataclass, field

from datalabel.llm.client import LLMClient, LLMUsage
from datalabel.llm.prompts import (
    GUIDELINES_SYSTEM_EN,
    GUIDELINES_SYSTEM_ZH,
    GUIDELINES_USER_EN,
    GUIDELINES_USER_ZH,
)


@dataclass
class GuidelinesResult:
    """指南生成结果。"""

    success: bool = True
    content: str = ""
    total_usage: LLMUsage = field(default_factory=LLMUsage)
    output_path: str | None = None
    error: str | None = None


class GuidelinesGenerator:
    """标注指南生成器。"""

    def __init__(self, client: LLMClient | None = None, **kwargs):
        if client is None:
            client = LLMClient(**kwargs)
        self.client = client

    def generate(
        self,
        schema: dict,
        tasks: list[dict] | None = None,
        output_path: str | None = None,
        language: str = "zh",
        sample_count: int = 5,
    ) -> GuidelinesResult:
        """生成标注指南。

        Args:
            schema: 标注规范
            tasks: 样例任务（可选，用于生成示例）
            output_path: 输出文件路径（Markdown 格式）
            language: 语言，"zh" 或 "en"
            sample_count: 使用的样例数量

        Returns:
            GuidelinesResult
        """
        schema_json = json.dumps(schema, ensure_ascii=False, indent=2)

        samples = []
        if tasks:
            samples = tasks[:sample_count]
        samples_json = json.dumps(samples, ensure_ascii=False, indent=2) if samples else "（无样例数据）"

        if language == "en":
            system_prompt = GUIDELINES_SYSTEM_EN
            user_template = GUIDELINES_USER_EN
        else:
            system_prompt = GUIDELINES_SYSTEM_ZH
            user_template = GUIDELINES_USER_ZH

        user_content = user_template.format(
            schema_json=schema_json,
            samples_json=samples_json,
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ]

        response = self.client.chat(messages)
        if not response.success:
            return GuidelinesResult(success=False, error=f"LLM 调用失败: {response.error}")

        result = GuidelinesResult(
            success=True,
            content=response.content,
            total_usage=response.usage,
        )

        if output_path:
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(response.content)
            result.output_path = output_path

        return result
