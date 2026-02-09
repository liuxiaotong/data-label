"""MCP 资源单元测试."""

import json

import pytest

from datalabel.mcp_server._resources import (
    ANNOTATION_TYPES_REFERENCE,
    SCHEMA_TEMPLATES,
    read_resource_content,
)
from datalabel.validator import SchemaValidator


class TestSchemaTemplates:
    """测试 Schema 模板数据."""

    def test_all_annotation_types_covered(self):
        expected = {"scoring", "single_choice", "multi_choice", "text", "ranking"}
        assert set(SCHEMA_TEMPLATES.keys()) == expected

    def test_each_template_has_description(self):
        for ann_type, template in SCHEMA_TEMPLATES.items():
            assert "description" in template, f"{ann_type} 缺少 description"
            assert "schema" in template, f"{ann_type} 缺少 schema"

    def test_each_template_is_valid_schema(self):
        validator = SchemaValidator()
        for ann_type, template in SCHEMA_TEMPLATES.items():
            result = validator.validate_schema(template["schema"])
            assert result.valid, f"{ann_type} 模板无效: {result.errors}"

    def test_scoring_template_has_rubric(self):
        schema = SCHEMA_TEMPLATES["scoring"]["schema"]
        assert "scoring_rubric" in schema
        assert len(schema["scoring_rubric"]) >= 2

    def test_choice_templates_have_options(self):
        for ann_type in ("single_choice", "multi_choice", "ranking"):
            schema = SCHEMA_TEMPLATES[ann_type]["schema"]
            config = schema["annotation_config"]
            assert config["type"] == ann_type
            assert len(config["options"]) >= 2

    def test_text_template_has_config(self):
        schema = SCHEMA_TEMPLATES["text"]["schema"]
        config = schema["annotation_config"]
        assert config["type"] == "text"


class TestAnnotationTypesReference:
    """测试标注类型参考数据."""

    def test_has_all_types(self):
        types = {t["type"] for t in ANNOTATION_TYPES_REFERENCE["annotation_types"]}
        assert types == {"scoring", "single_choice", "multi_choice", "text", "ranking"}

    def test_each_type_has_required_fields(self):
        for t in ANNOTATION_TYPES_REFERENCE["annotation_types"]:
            assert "type" in t
            assert "description" in t
            assert "response_keys" in t
            assert "use_cases" in t


class TestReadResourceContent:
    """测试资源读取."""

    def test_read_scoring_schema(self):
        content = read_resource_content("datalabel://schemas/scoring")
        data = json.loads(content)
        assert "scoring_rubric" in data

    def test_read_single_choice_schema(self):
        content = read_resource_content("datalabel://schemas/single_choice")
        data = json.loads(content)
        assert data["annotation_config"]["type"] == "single_choice"

    def test_read_annotation_types_reference(self):
        content = read_resource_content("datalabel://reference/annotation-types")
        data = json.loads(content)
        assert "annotation_types" in data

    def test_unknown_schema_type_raises(self):
        with pytest.raises(ValueError, match="未知"):
            read_resource_content("datalabel://schemas/nonexistent")

    def test_unknown_uri_raises(self):
        with pytest.raises(ValueError, match="未知"):
            read_resource_content("datalabel://unknown/path")
