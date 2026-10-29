"""Built-in detectors and the factory that wires them to configuration."""

from smell_detector.config import Config
from smell_detector.detectors.base import FileDetector, ProjectDetector
from smell_detector.detectors.deep_nesting import DeepNestingDetector
from smell_detector.detectors.duplicate_blocks import DuplicateBlockDetector
from smell_detector.detectors.large_class import LargeClassDetector
from smell_detector.detectors.long_method import LongMethodDetector

RULES = ("long-method", "deep-nesting", "large-class", "duplicate-block")


def default_detectors(config: Config) -> list[FileDetector | ProjectDetector]:
    return [
        LongMethodDetector(config.max_function_lines),
        DeepNestingDetector(config.max_nesting_depth),
        LargeClassDetector(config.max_class_methods, config.max_class_lines),
        DuplicateBlockDetector(config.duplicate_min_statements, config.duplicate_min_lines),
    ]


__all__ = [
    "RULES",
    "DeepNestingDetector",
    "DuplicateBlockDetector",
    "FileDetector",
    "LargeClassDetector",
    "LongMethodDetector",
    "ProjectDetector",
    "default_detectors",
]
