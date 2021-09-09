import json
import os
from typing import Optional

from eth.types.block import Block, DetailedBlock, SummaryBlock, UncleBlock
from eth.utils.file_utils import block_filepath, uncle_block_filepath


def read_block(num: int) -> Optional[SummaryBlock]:

    filepath = block_filepath(num)

    if not os.path.exists(filepath):
        return None

    with open(filepath, "r") as f:
        content = json.loads(f.read())
        return SummaryBlock(content)


def read_uncle_block(num: int, uncle_index: int) -> Optional[UncleBlock]:
    filepath = uncle_block_filepath(num, uncle_index)

    if not os.path.exists(filepath):
        return None

    with open(filepath, "r") as f:
        content = json.loads(f.read())
        return UncleBlock(content, num, uncle_index)
