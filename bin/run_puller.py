import functools
import logging
import os
import signal
import sys
import time
from argparse import ArgumentParser, Namespace
from datetime import datetime
from threading import Thread

from eth.core.ethereum_client import EthereumClient, GethClient
from eth.core.puller import BlockPuller
from eth.types.block import DetailedBlock
from potpourri.python.ethereum.constants import LONDON

LOG = logging.getLogger(__name__)


exit_signal = False


def signal_handler(sig, frame):
    global exit_signal
    LOG.info(f"Exit signal received: {sig}")
    exit_signal = True
    time.sleep(1)
    LOG.info("Shutdown in 3")
    time.sleep(1)
    LOG.info("Shutdown in 2")
    time.sleep(1)
    LOG.info("Shutdown in 1")
    time.sleep(1)
    sys.exit(1)


def _still_running() -> bool:
    global exit_signal
    return not exit_signal


def setup_logging() -> None:
    root = logging.getLogger()
    root.setLevel(logging.INFO)

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter("%(asctime)s %(levelname)7s (%(threadName)9s) [%(name)s:%(lineno)s] %(message)s")
    handler.setFormatter(formatter)
    root.addHandler(handler)


def log_progress(block: DetailedBlock, prefix: str = "") -> None:
    prefix = f"{prefix}    " if prefix != "" else prefix
    LOG.info(f"{prefix}block={block.number} time={block.timestamp_dt}")


def run_puller(eth_addr: str, eth_port: int, use_cache: bool, block: int) -> None:
    eth_client: EthereumClient = GethClient(ip_addr=eth_addr, port=eth_port)
    block_puller: BlockPuller = BlockPuller(eth_client=eth_client)

    prev_sha3_uncles = ""

    start_block = block
    while _still_running():
        time.sleep(0)
        latest_block_number = block_puller.eth_blockNumber()
        block: DetailedBlock = block_puller.eth_getBlockByNumber(
            latest_block_number, cached=use_cache, prev_sha3_uncles=prev_sha3_uncles
        )
        log_progress(block, "latest")

        if start_block != latest_block_number:
            for block_num in range(start_block, latest_block_number):
                block = block_puller.eth_getBlockByNumber(
                    block_num, cached=use_cache, prev_sha3_uncles=prev_sha3_uncles
                )
                prev_sha3_uncles = block._sha3_uncles

                if not _still_running():
                    log_progress(block, prefix="exit block cacher")
                    return

        sleep_sec = 1 if datetime.now().minute in [59, 0, 1] else 20
        for _ in range(sleep_sec):
            if not _still_running():
                log_progress(block, prefix="exit block cacher")
                return
            time.sleep(1)
        start_block = latest_block_number

    LOG.info("Exit Block Cacher")


def parse_args() -> Namespace:
    parser = ArgumentParser()
    parser.add_argument(
        "--eth.addr",
        type=str,
        default=os.getenv("ETHBURNBOT_ETHEREUM_RPC", "localhost"),
        help="HTTP-RPC server listening interface",
    )
    parser.add_argument("--eth.port", type=int, default=8545, help="HTTP-RPC server listening port")
    parser.add_argument("--no-cache", action="store_true")
    parser.add_argument("--block", type=int, default=LONDON, help="Start block")
    return parser.parse_args()


def main():
    setup_logging()

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGHUP, signal_handler)
    signal.signal(signal.SIGQUIT, signal_handler)

    args: Namespace = parse_args()
    addr: str = getattr(args, "eth.addr")
    port: int = getattr(args, "eth.port")
    use_cache: bool = not getattr(args, "no_cache")
    block: int = getattr(args, "block")

    puller = Thread(
        name="Block Cacher",
        target=functools.partial(run_puller, eth_addr=addr, eth_port=port, use_cache=use_cache, block=block),
    )
    puller.start()
    puller.join()


if __name__ == "__main__":
    main()
