"""Tests for SchemaValidator."""

from datalabel.validator import SchemaValidator


class TestSchemaValidation:
    """Tests for schema validation."""

    def setup_method(self):
        self.validator = SchemaValidator()

    def test_valid_schema_with_scoring(self, sample_schema):
        """Test validation of a valid schema with scoring_rubric."""
        result = self.validator.validate_schema(sample_schema)
        assert result.valid
        assert not result.errors

    def test_valid_schema_with_annotation_config(self):
        """Test validation of a valid schema with annotation_config."""
        schema = {
            "project_name": "测试",
            "fields": [{"name": "text", "type": "text"}],
            "annotation_config": {
                "type": "single_choice",
                "options": [
                    {"value": "a", "label": "A"},
                    {"value": "b", "label": "B"},
                ],
            },
        }
        result = self.validator.validate_schema(schema)
        assert result.valid
        assert not result.errors

    def test_schema_not_dict(self):
        """Test that non-dict schema is rejected."""
        result = self.validator.validate_schema("not a dict")
        assert not result.valid
        assert any("字典" in e for e in result.errors)

    def test_schema_missing_project_name_warns(self):
        """Test that missing project_name produces a warning."""
        schema = {"fields": [{"name": "text"}]}
        result = self.validator.validate_schema(schema)
        assert result.valid
        assert any("project_name" in w for w in result.warnings)

    def test_schema_empty_fields_warns(self):
        """Test that empty fields produces a warning."""
        schema = {"project_name": "test", "fields": []}
        result = self.validator.validate_schema(schema)
        assert result.valid
        assert any("fields" in w for w in result.warnings)

    def test_schema_fields_not_list(self):
        """Test that non-list fields is rejected."""
        schema = {"fields": "not a list"}
        result = self.validator.validate_schema(schema)
        assert not result.valid
        assert any("列表" in e for e in result.errors)

    def test_schema_field_not_dict(self):
        """Test that non-dict field is rejected."""
        schema = {"fields": ["not a dict"]}
        result = self.validator.validate_schema(schema)
        assert not result.valid
        assert any("字典" in e for e in result.errors)

    def test_schema_field_missing_name(self):
        """Test that field without name is rejected."""
        schema = {"fields": [{"type": "text"}]}
        result = self.validator.validate_schema(schema)
        assert not result.valid
        assert any("name" in e for e in result.errors)

    def test_schema_no_annotation_or_scoring_warns(self):
        """Test that schema without annotation_config or scoring_rubric warns."""
        schema = {"project_name": "test", "fields": [{"name": "text"}]}
        result = self.validator.validate_schema(schema)
        assert result.valid
        assert any("scoring_rubric" in w or "annotation_config" in w for w in result.warnings)

    def test_annotation_config_not_dict(self):
        """Test that non-dict annotation_config is rejected."""
        schema = {"fields": [{"name": "text"}], "annotation_config": "bad"}
        result = self.validator.validate_schema(schema)
        assert not result.valid
        assert any("annotation_config" in e and "字典" in e for e in result.errors)

    def test_annotation_config_missing_type(self):
        """Test that annotation_config without type is rejected."""
        schema = {"fields": [{"name": "text"}], "annotation_config": {}}
        result = self.validator.validate_schema(schema)
        assert not result.valid
        assert any("type" in e for e in result.errors)

    def test_annotation_config_invalid_type(self):
        """Test that invalid annotation type is rejected."""
        schema = {
            "fields": [{"name": "text"}],
            "annotation_config": {"type": "invalid_type"},
        }
        result = self.validator.validate_schema(schema)
        assert not result.valid
        assert any("无效" in e for e in result.errors)

    def test_annotation_config_choice_missing_options(self):
        """Test that single_choice without options is rejected."""
        schema = {
            "fields": [{"name": "text"}],
            "annotation_config": {"type": "single_choice"},
        }
        result = self.validator.validate_schema(schema)
        assert not result.valid
        assert any("options" in e for e in result.errors)

    def test_annotation_config_choice_too_few_options(self):
        """Test that choice type with < 2 options is rejected."""
        schema = {
            "fields": [{"name": "text"}],
            "annotation_config": {
                "type": "multi_choice",
                "options": [{"value": "a", "label": "A"}],
            },
        }
        result = self.validator.validate_schema(schema)
        assert not result.valid
        assert any("2" in e for e in result.errors)

    def test_annotation_config_text_type_no_options_ok(self):
        """Test that text type doesn't require options."""
        schema = {
            "project_name": "test",
            "fields": [{"name": "text"}],
            "annotation_config": {"type": "text"},
        }
        result = self.validator.validate_schema(schema)
        assert result.valid

    def test_annotation_config_scoring_type_no_options_ok(self):
        """Test that scoring type doesn't require options."""
        schema = {
            "project_name": "test",
            "fields": [{"name": "text"}],
            "annotation_config": {"type": "scoring"},
        }
        result = self.validator.validate_schema(schema)
        assert result.valid

    def test_scoring_rubric_not_list(self):
        """Test that non-list scoring_rubric is rejected."""
        schema = {"fields": [{"name": "text"}], "scoring_rubric": "bad"}
        result = self.validator.validate_schema(schema)
        assert not result.valid
        assert any("列表" in e for e in result.errors)

    def test_scoring_rubric_item_not_dict(self):
        """Test that non-dict rubric item is rejected."""
        schema = {"fields": [{"name": "text"}], "scoring_rubric": ["bad"]}
        result = self.validator.validate_schema(schema)
        assert not result.valid

    def test_scoring_rubric_item_missing_score(self):
        """Test that rubric item without score is rejected."""
        schema = {
            "fields": [{"name": "text"}],
            "scoring_rubric": [{"description": "good"}],
        }
        result = self.validator.validate_schema(schema)
        assert not result.valid
        assert any("score" in e for e in result.errors)

    def test_all_valid_annotation_types(self):
        """Test that all valid annotation types are accepted."""
        for ann_type in ["scoring", "single_choice", "multi_choice", "text", "ranking"]:
            config = {"type": ann_type}
            if ann_type in ("single_choice", "multi_choice", "ranking"):
                config["options"] = [
                    {"value": "a", "label": "A"},
                    {"value": "b", "label": "B"},
                ]
            schema = {
                "project_name": "test",
                "fields": [{"name": "text"}],
                "annotation_config": config,
            }
            result = self.validator.validate_schema(schema)
            assert result.valid, f"Type {ann_type} should be valid but got errors: {result.errors}"


class TestTaskValidation:
    """Tests for task data validation."""

    def setup_method(self):
        self.validator = SchemaValidator()

    def test_valid_tasks(self, sample_tasks):
        """Test validation of valid tasks."""
        result = self.validator.validate_tasks(sample_tasks)
        assert result.valid
        assert not result.errors

    def test_tasks_not_list(self):
        """Test that non-list tasks is rejected."""
        result = self.validator.validate_tasks("not a list")
        assert not result.valid
        assert any("列表" in e for e in result.errors)

    def test_empty_tasks_warns(self):
        """Test that empty task list produces a warning."""
        result = self.validator.validate_tasks([])
        assert result.valid
        assert any("空" in w for w in result.warnings)

    def test_task_not_dict(self):
        """Test that non-dict task is rejected."""
        result = self.validator.validate_tasks(["bad"])
        assert not result.valid
        assert any("字典" in e for e in result.errors)

    def test_duplicate_task_ids(self):
        """Test that duplicate task IDs are rejected."""
        tasks = [
            {"id": "TASK_001", "data": {"text": "a"}},
            {"id": "TASK_001", "data": {"text": "b"}},
        ]
        result = self.validator.validate_tasks(tasks)
        assert not result.valid
        assert any("重复" in e for e in result.errors)

    def test_tasks_without_ids_ok(self):
        """Test that tasks without IDs are accepted."""
        tasks = [
            {"data": {"text": "a"}},
            {"data": {"text": "b"}},
        ]
        result = self.validator.validate_tasks(tasks)
        assert result.valid

    def test_mixed_tasks_with_and_without_ids(self):
        """Test tasks where some have IDs and some don't."""
        tasks = [
            {"id": "TASK_001", "data": {"text": "a"}},
            {"data": {"text": "b"}},
            {"id": "TASK_003", "data": {"text": "c"}},
        ]
        result = self.validator.validate_tasks(tasks)
        assert result.valid
