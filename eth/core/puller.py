import os
from logging import getLogger
from typing import List

from eth.core.eth import EthereumClient
from eth.core.reader import read_block, read_uncle_block
from eth.core.writer import write_block, write_uncle_block
from eth.types.block import Block, DetailedBlock, UncleBlock
from eth.utils.file_utils import uncle_block_filepath

LOG = getLogger(__name__)


class BlockPuller:
    def __init__(self, eth_client: EthereumClient):
        self._eth_client: EthereumClient = eth_client

    def eth_blockNumber(self) -> int:
        return self._eth_client.eth_blockNumber()

    def _get_uncles(
        self, block: Block, cached: bool = False, prev_sha3_uncles: str = ""
    ) -> List[UncleBlock]:

        has_uncles = prev_sha3_uncles != block._sha3_uncles
        uncles: List[UncleBlock] = []
        # fetch uncles
        if has_uncles:
            # LOG.info(f"Block {block._number} has uncles: {prev_sha3_uncles} -> {block._sha3_uncles}")
            num_uncles: int = self.eth_getUncleCountByBlockNumber(
                block.number, cached=cached
            )
            if num_uncles > 0:
                # LOG.info(f"Block {num} has {num_uncles} uncle{'s' if num_uncles > 1 else ''}")

                # pull and cache uncle blocks
                # do it in reverse so that we know its complete when index 0 is written
                # that way we can count how many there are by checking filenames if they exist on disk
                for i in reversed(range(num_uncles)):
                    # check if uncle is cached
                    uncle_block = None
                    if cached:
                        uncle_block = read_uncle_block(block.number, i)
                    found_cached = uncle_block is not None

                    if uncle_block is None:
                        uncle_block = (
                            self._eth_client.eth_getUncleByBlockNumberAndIndex(
                                block.number, i
                            )
                        )
                        write_uncle_block(uncle_block, warn_overwrite=found_cached)

                    uncles.append(uncle_block)

        return uncles

    def eth_getBlockByNumber(
        self, num: int, cached: bool = False, prev_sha3_uncles: str = ""
    ) -> DetailedBlock:
        block = None
        if cached:
            block = read_block(num)
        found_cached = block is not None

        if block is None:
            # else we need to pull it and write it
            block = self._eth_client.eth_getBlockByNumber(num)

        uncles: List[UncleBlock] = self._get_uncles(
            block, cached=cached, prev_sha3_uncles=prev_sha3_uncles
        )
        detailed_block: DetailedBlock = DetailedBlock(block, uncles)
        write_block(detailed_block, warn_overwrite=found_cached)
        return block

    def eth_getUncleCountByBlockNumber(self, num: int, cached: bool) -> int:
        # one block can include up to two uncles
        if cached and os.path.exists(uncle_block_filepath(num, 1)):
            return 2
        elif cached and os.path.exists(uncle_block_filepath(num, 0)):
            return 1
        else:
            return self._eth_client.eth_getUncleCountByBlockNumber(num)
