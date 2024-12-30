from __future__ import annotations

import argparse
from abc import ABC, abstractmethod

from build123d import Part, Vector


class LabelBase(ABC):
    """
    Output object from base creation.
    """

    part: Part
    area: Vector

    @classmethod
    def generate_argparse(
        cls, common_argparse: argparse.ArgumentParser
    ) -> argparse.ArgumentParser:
        parser = argparse.ArgumentParser(parents=[common_argparse])
        return parser

    @classmethod
    def validate_arguments(cls, args: argparse.Namespace) -> bool:
        return True

    @abstractmethod
    def __init__(self, args: argparse.Namespace):
        pass
