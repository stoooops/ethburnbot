import logging
import signal
import sys
import time
from threading import Thread
from typing import Optional

from eth.core.processor import BlockProcessor
from eth.core.reader import read_block
from eth.core.tweeter import Tweeter
from eth.types.block import SummaryBlock
from potpourri.python.ethereum.constants import LONDON

LOG = logging.getLogger(__name__)


exit_signal = False
caught_up = False


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


def run_processor() -> None:
    global caught_up
    # first block to process
    block_num = LONDON

    block_processor = BlockProcessor()
    while _still_running():
        time.sleep(0)

        block: Optional[SummaryBlock] = read_block(block_num)
        if block is None:
            if not caught_up:
                LOG.info("Processor caught up to Puller")
            caught_up = True
            LOG.debug(f"Block {block_num} not yet available")
            time.sleep(1)
            continue

        block_processor.process(block)

        block_num = block_num + 1

    LOG.info("Exit Block Processor")


def run_tweeter() -> None:
    global caught_up

    tweeter = Tweeter()

    wakeup_sec = 10
    while _still_running():
        time.sleep(0)

        tweeted = False
        if not caught_up:
            LOG.info("Waiting for processor to catch up before tweeting")
        else:
            tweeted = tweeter.process(dry_run=False)

        for _ in range(wakeup_sec if not tweeted else 1):
            if not _still_running():
                return
            time.sleep(1)


def main():
    setup_logging()

    signal.signal(signal.SIGINT, signal_handler)

    processor = Thread(target=run_processor, name="Block Processor")
    tweeter = Thread(target=run_tweeter, name="Tweeter")

    processor.start()
    tweeter.start()

    processor.join()
    tweeter.join()


if __name__ == "__main__":
    main()
