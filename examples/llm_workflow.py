#!/usr/bin/env python3
"""LLM 分析功能示例: 预标注、质量分析、指南生成。

Usage:
    # 需要设置 API key，例如:
    export MOONSHOT_API_KEY=sk-...
    python examples/llm_workflow.py

    # 或使用 OpenAI:
    export OPENAI_API_KEY=sk-...
    python examples/llm_workflow.py --provider openai

支持的提供商: moonshot (Kimi), openai, anthropic
"""

import json
import sys
import tempfile
from pathlib import Path

from datalabel.llm import (
    GuidelinesGenerator,
    LLMClient,
    LLMConfig,
    PreLabeler,
    QualityAnalyzer,
)

SCHEMA = {
    "project_name": "LLM 回答质量评估",
    "fields": [
        {"name": "instruction", "display_name": "用户指令", "type": "text"},
        {"name": "response", "display_name": "模型回答", "type": "text"},
    ],
    "scoring_rubric": [
        {"score": 1, "label": "优秀", "description": "回答完整准确，逻辑清晰"},
        {"score": 0.5, "label": "一般", "description": "基本正确但有遗漏"},
        {"score": 0, "label": "差", "description": "回答错误或离题"},
    ],
}

TASKS = [
    {
        "id": "T1",
        "data": {
            "instruction": "什么是机器学习？",
            "response": "机器学习是AI的一个分支，使计算机从数据中学习。",
        },
    },
    {
        "id": "T2",
        "data": {
            "instruction": "解释深度学习",
            "response": "深度学习使用多层神经网络学习层次化表示。",
        },
    },
    {
        "id": "T3",
        "data": {
            "instruction": "Python 和 Java 的区别？",
            "response": "Python 是动态类型语言，Java 是静态类型语言。",
        },
    },
]


def main():
    provider = "moonshot"
    if "--provider" in sys.argv:
        idx = sys.argv.index("--provider")
        if idx + 1 < len(sys.argv):
            provider = sys.argv[idx + 1]

    print(f"使用提供商: {provider}")
    print("=" * 50)

    config = LLMConfig(provider=provider)
    if not config.api_key:
        from datalabel.llm.client import ENV_KEYS

        env_var = ENV_KEYS[provider]
        print(f"错误: 请设置环境变量 {env_var}")
        print(f"  例如: export {env_var}=sk-your-key")
        sys.exit(1)

    client = LLMClient(config=config)

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        # 1. 自动预标注
        print("\n[1] 自动预标注")
        print("-" * 30)
        labeler = PreLabeler(client=client)
        pre_out = str(tmpdir / "prelabel.json")
        result = labeler.prelabel(SCHEMA, TASKS, output_path=pre_out, batch_size=5)

        if result.success:
            print(f"  标注数: {result.labeled_tasks}/{result.total_tasks}")
            print(f"  Token: {result.total_usage.total_tokens}")
            data = json.loads(Path(pre_out).read_text())
            for r in data["responses"]:
                print(f"  {r['task_id']}: score={r.get('score', '?')}, comment={r.get('comment', '')}")
        else:
            print(f"  失败: {result.error}")

        # 2. 标注质量分析 (使用预标注结果)
        print("\n[2] 标注质量分析")
        print("-" * 30)
        analyzer = QualityAnalyzer(client=client)
        report_out = str(tmpdir / "quality_report.json")
        report = analyzer.analyze(SCHEMA, [pre_out], output_path=report_out)

        if report.success:
            print(f"  摘要: {report.summary}")
            print(f"  问题数: {len(report.issues)}")
            for issue in report.issues:
                print(f"  - [{issue.severity}] {issue.task_id}: {issue.description}")
            print(f"  Token: {report.total_usage.total_tokens}")
        else:
            print(f"  失败: {report.error}")

        # 3. 生成标注指南
        print("\n[3] 生成标注指南")
        print("-" * 30)
        gen = GuidelinesGenerator(client=client)
        guide_out = str(tmpdir / "guidelines.md")
        guide_result = gen.generate(SCHEMA, tasks=TASKS, output_path=guide_out, language="zh")

        if guide_result.success:
            content = Path(guide_out).read_text()
            # 只打印前 500 字符预览
            preview = content[:500] + "..." if len(content) > 500 else content
            print(f"  字数: {len(content)}")
            print(f"  Token: {guide_result.total_usage.total_tokens}")
            print(f"\n  预览:\n{preview}")
        else:
            print(f"  失败: {guide_result.error}")

    print("\n" + "=" * 50)
    print("完成！")


if __name__ == "__main__":
    main()
