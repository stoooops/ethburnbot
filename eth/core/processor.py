import os
from datetime import datetime
from decimal import Decimal
from logging import getLogger
from typing import List, Optional

from eth.types.block import (
    AggregateBlockMetrics,
    HourlyAggregateBlockMetrics,
    SummaryBlock,
)
from eth.utils.file_utils import pending_tweets_dir, tweeted_tweets_dir
from potpourri.python.ethereum.block import Block

LOG = getLogger(__name__)


def get_emoji(burnt_eth: int) -> str:
    emoji = "🔥"
    val = burnt_eth
    while val / 10 >= 1:
        emoji = emoji + "🔥"
        val = val / 10
    return emoji


def write_tweet(metrics: AggregateBlockMetrics) -> str:
    emoji = get_emoji(metrics.burnt_eth)

    # TODO compute accurately this is just a snapshot taken. Small rounding error for now.
    SUPPLY = 117031591

    issuance_multiplier = 365 * (
        24 if isinstance(metrics, HourlyAggregateBlockMetrics) else 1
    )
    change_per_year = issuance_multiplier * metrics.net_issuance_eth
    inflation_pct = 100 * change_per_year / SUPPLY
    # no_burn_change_per_year =  365*24*metrics.issuance_eth
    # no_burn_annualized = 100 * no_burn_change_per_year / SUPPLY

    time_phrase = (
        "last hour" if isinstance(metrics, HourlyAggregateBlockMetrics) else "yesterday"
    )
    header_line = f"{metrics.burnt_eth:,.4f} $ETH burned {emoji} {time_phrase}."
    if int(metrics.burnt_eth) == 69:
        header_line = header_line + " Nice."

    annualized_line = f"Annualized: {inflation_pct:.2f}%"
    if inflation_pct < 0:
        annualized_line = annualized_line + " 📉"

    return "\n".join(
        [
            header_line,
            "",
            f"Issuance: {metrics.issuance_eth:,.4f} ETH",
            f"Net Change: {'+' if metrics.net_issuance_eth > 0 else ''}{metrics.net_issuance_eth:,.4f} ETH",
            annualized_line,
            "",
            f"{metrics.time_range_str(delimiter=' ')} UTC",
            f"Last Block: {metrics.end_number}",
            "",
            f"Cumulative 🔥: {metrics.cumulative_burned_eth:,.4f} ETH",
        ]
    )


class BlockProcessor:
    def __init__(self):
        self._blocks: List[SummaryBlock] = []

    def process(self, block: SummaryBlock) -> None:
        self._blocks.append(block)
        LOG.debug(
            f"Block #{block.number} ({block.timestamp_dt}) burned {block.burned_eth:.18f}"
        )

        self._process_if_end_hour()

    def _process_if_end_hour(self) -> None:
        assert len(self._blocks) > 0
        block: Block = self._blocks[-1]

        if len(self._blocks) > 1:
            prev_block = self._blocks[-2]
            assert prev_block.number + 1 == block.number

            # summarize hour
            if block.hour_dt > prev_block.hour_dt:
                LOG.info(f"Processing hour before {block.timestamp_dt}...")
                metrics: AggregateBlockMetrics = self.aggregate(
                    hour_dt=prev_block.hour_dt
                )
                self.write_tweet_if_not_tweeted(metrics)

            # summarize day
            if block.day_dt > prev_block.day_dt:
                LOG.info(f"Processing day before {block.timestamp_dt}...")
                metrics: AggregateBlockMetrics = self.aggregate(
                    day_dt=prev_block.day_dt
                )
                self.write_tweet_if_not_tweeted(metrics)

    def write_tweet_if_not_tweeted(self, metrics: AggregateBlockMetrics) -> None:
        tweet: str = write_tweet(metrics)
        time_str = (
            metrics.hour_str()
            if isinstance(metrics, HourlyAggregateBlockMetrics)
            else metrics.day_str()
        )
        time_range_str = (
            metrics.hour_range_str()
            if isinstance(metrics, HourlyAggregateBlockMetrics)
            else metrics.day_range_str()
        )
        tweet_filename: str = f"tweet_{time_str}.txt"

        # check if already tweeted
        tweeted_filepath: str = os.path.join(tweeted_tweets_dir(), tweet_filename)
        if os.path.exists(tweeted_filepath):
            LOG.debug(f"Tweet {time_range_str} already written")
            return

        # write tweet to pending tweets dir
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
