import functools
import logging
import signal
import sys
import time
from argparse import ArgumentParser, Namespace
from datetime import datetime
from threading import Thread

from eth.core.eth import EthereumClient, GethClient
from eth.core.puller import BlockPuller
from potpourri.python.ethereum.constants import LONDON

LOG = logging.getLogger(__name__)


exit_signal = False


def signal_handler(sig, frame):
    global exit_signal
    LOG.info("SIGINT!")
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
    formatter = logging.Formatter(
        "%(asctime)s %(levelname)s (%(threadName)s) [%(name)s:%(lineno)s] %(message)s"
    )
    handler.setFormatter(formatter)
    root.addHandler(handler)


def run_puller(eth_addr: str, eth_port: int) -> None:
    eth_client: EthereumClient = GethClient(ip_addr=eth_addr, port=eth_port)
    block_puller: BlockPuller = BlockPuller(eth_client=eth_client)

    prev_sha3_uncles = ""

    start_block = LONDON
    while _still_running():
        time.sleep(0)
        latest_block_number = block_puller.eth_blockNumber()
        LOG.info(f"Latest block number: {latest_block_number}")

        if start_block != latest_block_number:
            for block_num in range(start_block, latest_block_number):
                block = block_puller.eth_getBlockByNumber(
                    block_num, cached=True, prev_sha3_uncles=prev_sha3_uncles
                )
                prev_sha3_uncles = block._sha3_uncles

                if block_num % 100 == 0:
                    LOG.info(f"Cached block {block_num} @ {block.timestamp_dt}")

                if not _still_running():
                    LOG.info("Exit Block Cacher")
                    return

        sleep_sec = 1 if datetime.now().minute in [59, 0, 1] else 10
        for _ in range(sleep_sec):
            if not _still_running():
                LOG.info("Exit Block Cacher")
                return
            time.sleep(1)
        start_block = latest_block_number

    LOG.info("Exit Block Cacher")


def parse_args() -> Namespace:
    parser = ArgumentParser()
    parser.add_argument(
        "--eth.addr",
        type=str,
        default="localhost",
        help="HTTP-RPC server listening interface",
    )
    parser.add_argument(
        "--eth.port", type=int, default=8545, help="HTTP-RPC server listening port"
    )
    return parser.parse_args()


def main():
    setup_logging()

    signal.signal(signal.SIGINT, signal_handler)

    args: Namespace = parse_args()
    addr: str = getattr(args, "eth.addr")
    port: int = getattr(args, "eth.port")

    puller = Thread(
        name="Block Cacher",
        target=functools.partial(run_puller, eth_addr=addr, eth_port=port),
    )
    puller.start()
    puller.join()


if __name__ == "__main__":
    main()
