"""DataLabel - 轻量级数据标注工具

生成独立的 HTML 标注界面，无需服务器，浏览器直接打开即可使用。
"""

__version__ = "0.1.0"

from datalabel.generator import AnnotatorGenerator
from datalabel.merger import ResultMerger
from datalabel.validator import SchemaValidator

__all__ = ["AnnotatorGenerator", "ResultMerger", "SchemaValidator", "__version__"]
