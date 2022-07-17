import functools
import logging
import signal
import sys
import time
from argparse import ArgumentParser, Namespace
from decimal import Decimal
from threading import Thread
from typing import Dict, Optional

from eth.core.processor import BlockProcessor
from eth.core.reader import read_block
from eth.core.tweeter import Tweeter, TweeterException
from eth.types.block import SummaryBlock
from potpourri.python.ethereum.constants import LONDON

LOG = logging.getLogger(__name__)
LOG_WIDTH = 40


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
    formatter = logging.Formatter("%(asctime)s %(levelname)7s %(message)s [%(name)s:%(lineno)s]")
    handler.setFormatter(formatter)
    root.addHandler(handler)


CHECKPOINT_1 = 13233800
CHECKPOINT_2 = 13596500
CHECKPOINT_3 = 13648000
CHECKPOINT_4 = 14000000
CHECKPOINT_5 = 14100000
CHECKPOINT_6 = 15000000
CHECKPOINT_7 = 15080000
BURNED_ETH: Dict[int, Decimal] = {
    LONDON: Decimal(0),
    CHECKPOINT_1: Decimal("301720.664913446243502258"),
    CHECKPOINT_2: Decimal("848916.085936463748695936"),
    CHECKPOINT_3: Decimal("949398.242163151858483080"),
    CHECKPOINT_4: Decimal("1487958.407215919376807183"),
    CHECKPOINT_5: Decimal("1688489.510719468494472673"),
    CHECKPOINT_6: Decimal("2470957.033914244745381122"),
    CHECKPOINT_7: Decimal("2512085.166061214922158636"),
}


def run_processor(last_known_block: int) -> None:
    burned_eth = BURNED_ETH[last_known_block]
    # first block to process
    block_num = last_known_block + 1 if last_known_block != 0 else last_known_block

    block_processor = BlockProcessor(burned_eth=burned_eth)
    caught_up = False
    while _still_running():
        time.sleep(0)

        block: Optional[SummaryBlock] = read_block(block_num)
        if block is None:
            if not caught_up:
                LOG.info(f"{'Processor caught up'.ljust(LOG_WIDTH)}block={block_num}")
            caught_up = True
            LOG.debug(f"Block {block_num} not yet available")
            time.sleep(1)
            continue

        block_processor.process(block)

        block_num = block_num + 1

    LOG.info("Exit Block Processor")


def run_tweeter(dry_run: bool) -> None:
    tweeter = Tweeter()

    wakeup_sec = 20
    tweets = 0
    failures = 0
    while _still_running():
        time.sleep(0)
        LOG.info(f"{'Tweeter Heartbeat!'.ljust(LOG_WIDTH)}tweets={tweets} failures={failures} dry_run={dry_run}")

        tweeted: bool = False
        try:
            tweeted = tweeter.process(dry_run=dry_run)
        except TweeterException as e:
            failures += 1
        tweets = tweets + 1 if tweeted else tweets

        for _ in range(wakeup_sec if not tweeted else 1):
            if not _still_running():
                return
            time.sleep(1)


def parse_args() -> Namespace:
    parser = ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Dry run")
    parser.add_argument("--process", action="store_true", help="Run processor")
    return parser.parse_args()


def main():
    setup_logging()

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGHUP, signal_handler)
    signal.signal(signal.SIGQUIT, signal_handler)

    args: Namespace = parse_args()
    dry_run: bool = getattr(args, "dry_run")

    last_known_block = max([k for k in BURNED_ETH.keys()])
    if args.process:
        run_processor(last_known_block=last_known_block)
    else:
        run_tweeter(dry_run=dry_run)


if __name__ == "__main__":
    main()
