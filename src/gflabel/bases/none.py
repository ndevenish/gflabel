from __future__ import annotations

import argparse
import logging
import sys

from ..options import LabelStyle
from ..util import unit_registry
from . import LabelBase

logger = logging.getLogger(__name__)


class NoneBase(LabelBase):
    DEFAULT_WIDTH = None
    DEFAULT_WIDTH_UNIT = unit_registry.mm

    def __init__(self, args: argparse.Namespace):
        self.part = None
        self.area = None

    @classmethod
    def validate_arguments(cls, args):
        if args.width is None:
            sys.exit("Error: Must specify a width for 'None' labels")
        if args.width.units == unit_registry.u:
            sys.exit("Error: Cannot specify width in gridfinity units for empty base")
        if not args.width.check("[length]"):
            sys.exit(
                f"Error: Invalid unit for 'None' width: {args.width.u}. Try '30mm'"
            )
        # We cannot have debossed labels with no label
        if args.base == "none" and args.style != LabelStyle.EMBOSSED:
            logger.error(
                "Error: Can only generate 'Embossed' style labels without a base."
            )
            sys.exit(1)
        if args.height is None:
            args.height = unit_registry.Quantity(15, "mm")
        return super().validate_arguments(args)
