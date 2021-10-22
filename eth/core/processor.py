import os
from datetime import datetime
from decimal import Decimal
from logging import getLogger
from typing import List, Optional

from eth.core.writer import write_tweet_aggregate, write_tweet_threshold
from eth.types.block import (
    AggregateBlockMetrics,
    HourlyAggregateBlockMetrics,
    SummaryBlock,
)
from eth.utils.file_utils import pending_tweets_dir, tweeted_tweets_dir
from potpourri.python.ethereum.block import Block
from potpourri.python.ethereum.coinbase.client import CoinbaseClient

LOG = getLogger(__name__)


def day_str(day: datetime) -> str:
    return day.strftime(f"%Y-%m-%d")


def hour_str(hour: datetime, delimiter="T") -> str:
    return hour.strftime(f"%Y-%m-%d{delimiter}%H:%M%Z")


TWEET_THRESHOLD = 10000


class BlockProcessor:
    def __init__(self):
        self._blocks: List[SummaryBlock] = []
        self._burned_eth: Decimal = Decimal(0)
        self._burned_threshold = TWEET_THRESHOLD

        self._coinbase_client = CoinbaseClient()

    def process(self, block: SummaryBlock) -> None:
        self._blocks.append(block)
        LOG.debug(
            f"Block #{block.number} ({block.timestamp_dt}) burned {block.burned_eth:.18f}"
        )
        self._burned_eth = self._burned_eth + block.burned_eth

        self._process_if_end_hour()
        self._process_if_threshold()

    # THRESHOLD

    def _process_if_threshold(self) -> None:
        if self._burned_eth > self._burned_threshold:
            LOG.info(f"Burned: {self._burned_eth}")

            if self.needs_tweet(f"{self._burned_threshold}"):
                # get price
                eth_usd_price: Decimal = self._coinbase_client.get_price("ETH")

                self.write_tweet_threshold(eth_usd_price)
            self._burned_threshold += TWEET_THRESHOLD

    def write_tweet_threshold(self, eth_usd_price: Decimal) -> None:
        tweet_filename: str = self.tweet_filename(self._burned_threshold)
        # write tweet to pending tweets dir
        tweet: str = write_tweet_threshold(
            burnt_eth=self._burned_threshold, eth_usd_price=eth_usd_price
        )
        pending_filepath: str = os.path.join(pending_tweets_dir(), tweet_filename)
        LOG.info(
            f"Writing {self._burned_threshold} ETH burned tweet to {pending_filepath}"
        )
        with open(pending_filepath, "w") as f:
            f.write(tweet)

    # TIME AGGREGATE

    def _process_if_end_hour(self) -> None:
        assert len(self._blocks) > 0
        block: Block = self._blocks[-1]

        if len(self._blocks) > 1:
            prev_block = self._blocks[-2]
            assert prev_block.number + 1 == block.number

            # summarize hour
            if block.hour_dt > prev_block.hour_dt:
                if self.needs_tweet(hour_str(prev_block.hour_dt)):
                    # get price
                    eth_usd_price: Decimal = self._coinbase_client.get_price("ETH")

                    LOG.info(f"Processing hour before {block.timestamp_dt}...")
                    metrics: AggregateBlockMetrics = self.aggregate(
                        hour_dt=prev_block.hour_dt
                    )
                    self._write_tweet_aggregate(
                        metrics=metrics, eth_usd_price=eth_usd_price
                    )

            # summarize day
            if block.day_dt > prev_block.day_dt:
                if self.needs_tweet(day_str(prev_block.day_dt)):
                    # get price
                    eth_usd_price: Decimal = self._coinbase_client.get_price("ETH")

                    LOG.info(f"Processing day before {block.timestamp_dt}...")
                    metrics: AggregateBlockMetrics = self.aggregate(
                        day_dt=prev_block.day_dt
                    )
                    self._write_tweet_aggregate(
                        metrics=metrics, eth_usd_price=eth_usd_price
                    )

    def tweet_filename(self, time_str: str) -> str:
        return f"tweet_{time_str}.txt"

    def needs_tweet(self, time_str: str) -> bool:
        tweet_filename: str = self.tweet_filename(time_str)

        # check if already tweeted
        tweeted_filepath: str = os.path.join(tweeted_tweets_dir(), tweet_filename)
        if os.path.exists(tweeted_filepath):
            LOG.info(f"Tweet {time_str} already written")
            return False
        else:
            return True

    def _write_tweet_aggregate(
        self, metrics: AggregateBlockMetrics, eth_usd_price: Decimal
    ) -> None:
        time_str = (
            hour_str(metrics.hour)
            if isinstance(metrics, HourlyAggregateBlockMetrics)
            else day_str(metrics.day)
        )
        time_range_str = (
            metrics.hour_range_str()
            if isinstance(metrics, HourlyAggregateBlockMetrics)
            else metrics.day_range_str()
        )

        tweet_filename: str = self.tweet_filename(time_str)
        # write tweet to pending tweets dir
        tweet: str = write_tweet_aggregate(metrics, eth_usd_price)
        pending_filepath: str = os.path.join(pending_tweets_dir(), tweet_filename)
        LOG.info(f"Writing tweet {time_range_str} to {pending_filepath}")
        with open(pending_filepath, "w") as f:
            f.write(tweet)

    def aggregate(
        self, hour_dt: Optional[datetime] = None, day_dt: Optional[datetime] = None
    ) -> AggregateBlockMetrics:
        assert (hour_dt is None) ^ (day_dt is None)
        burnt_eth: Decimal = Decimal(0)
        start_number = None
        end_number = None

        cumulative_burnt_eth: Decimal = Decimal(0)
        base_issuance_eth: Decimal = Decimal(0)
        uncle_issuance_eth: Decimal = Decimal(0)
        for block in self._blocks:
            # count sum of previous
            if (hour_dt is not None and block.hour_dt <= hour_dt) or (
                day_dt is not None and block.day_dt <= day_dt
            ):
                cumulative_burnt_eth = cumulative_burnt_eth + block.burned_eth

            # count within range
            if (hour_dt is not None and block.hour_dt == hour_dt) or (
                day_dt is not None and block.day_dt == day_dt
            ):
                burnt_eth = burnt_eth + block.burned_eth

                start_number = (
                    start_number if start_number is not None else block.number
                )
                end_number = block.number

                base_issuance_eth = base_issuance_eth + block.base_issuance_eth
                uncle_issuance_eth = uncle_issuance_eth + block.uncle_reward_eth

        if hour_dt is not None:
            return HourlyAggregateBlockMetrics(
                day=hour_dt.replace(hour=0),
                hour=hour_dt,
                start_number=start_number,
                end_number=end_number,
                burnt_eth=burnt_eth,
                cumulative_burned_eth=cumulative_burnt_eth,
                base_issuance_eth=base_issuance_eth,
                uncle_issuance_eth=uncle_issuance_eth,
            )
        else:
            return AggregateBlockMetrics(
                day=day_dt,
                start_number=start_number,
                end_number=end_number,
                burnt_eth=burnt_eth,
                cumulative_burned_eth=cumulative_burnt_eth,
                base_issuance_eth=base_issuance_eth,
                uncle_issuance_eth=uncle_issuance_eth,
            )
