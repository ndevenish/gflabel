from __future__ import annotations

import argparse
from abc import ABC, abstractmethod

from build123d import Part, Vector

from ..util import unit_registry


class LabelBase(ABC):
    """
    Output object from base creation.
    """

    part: Part
    area: Vector

    # The width for this base to use if none is specified
    DEFAULT_WIDTH = None
    # The unit to use for the user-specified width if it was dimensionless
    DEFAULT_WIDTH_UNIT = None
    DEFAULT_MARGIN = unit_registry.Quantity(0.2, "mm")

    @classmethod
    def generate_argparse(
        cls, common_argparse: argparse.ArgumentParser
    ) -> argparse.ArgumentParser:
        parser = argparse.ArgumentParser(parents=[common_argparse])
        return parser

    @classmethod
    def validate_arguments(cls, args: argparse.Namespace) -> bool:
        if not args.margin:
            args.margin = cls.DEFAULT_MARGIN

        return True

    @abstractmethod
    def __init__(self, args: argparse.Namespace):
        pass
