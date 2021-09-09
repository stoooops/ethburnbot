import json
import logging
import os
import shutil

from eth.types.block import Block, UncleBlock
from eth.utils.file_utils import block_filepath, uncle_block_filepath

LOG = logging.getLogger(__name__)


def write_block(block: Block) -> None:
    filepath = block_filepath(block.number)
    exists = os.path.exists(filepath)
    tmp_filepath = f"{filepath}.tmp"
    with open(tmp_filepath, "w") as f:
        if not exists:
            LOG.info(f"Write block {block.number} @ {block.timestamp_dt} to {filepath}")
        else:
            LOG.debug(
                f"Overwrite block {block.number} @ {block.timestamp_dt} to {filepath}"
            )

        f.write(json.dumps(block.json, indent=2))

    shutil.move(tmp_filepath, filepath)


def write_uncle_block(uncle_block: UncleBlock) -> None:
    filepath = uncle_block_filepath(
        uncle_block.mined_block_num, uncle_block.uncle_index
    )
    exists = os.path.exists(filepath)
    tmp_filepath = f"{filepath}.tmp"
    with open(tmp_filepath, "w") as f:
        if not exists:
            LOG.info(
                f"Write uncle block {uncle_block.mined_block_num}[{uncle_block.uncle_index}] to {filepath}"
            )
        else:
            LOG.debug(
                f"Overwrite block {uncle_block.mined_block_num}[{uncle_block.uncle_index}] to {filepath}"
            )

        f.write(json.dumps(uncle_block.json, indent=2))

    shutil.move(tmp_filepath, filepath)
