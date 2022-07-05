import os
import time
from datetime import datetime, timedelta
from decimal import Decimal
from logging import getLogger
from typing import List, Optional

from eth.core.image_drawer import make_svg
from eth.core.writer import write_tweet_aggregate, write_tweet_fundamentals, write_tweet_threshold
from eth.types.block import AggregateBlockMetrics, DayAggregateBlockMetrics, HourlyAggregateBlockMetrics, SummaryBlock
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
    def __init__(self, burned_eth: Decimal = Decimal(0)):
        self._blocks: List[SummaryBlock] = []
        self._cached_burned_eth = burned_eth
        self._burned_eth: Decimal = burned_eth
        self._burned_threshold = TWEET_THRESHOLD

        self._coinbase_client = CoinbaseClient()
        self._eth_usd_price: Decimal = self._coinbase_client.get_price("ETH")
        self._eth_usd_price_time: int = int(time.time())

        self._written = set()

    @property
    def last_block(self) -> Optional[SummaryBlock]:
        if len(self._blocks) == 0:
            return None
        return self._blocks[-1]

    def process(self, block: SummaryBlock) -> None:
        now = datetime.now()
        now_hour = now.replace(minute=0, second=0, microsecond=0)
        now_day = now_hour.replace(hour=0)
        prev_hour = now_hour - timedelta(hours=1)

        if len(self._blocks) == 0:
            LOG.info(f"Processing first block: #{block.number} @ ({block.timestamp_dt})")
            if block.timestamp_dt > now_day:
                raise RuntimeError(
                    f"Must start with block before: {now_day} since current time is {now}. Got block #{block.number} @ ({block.timestamp_dt})"
                )

        self._blocks.append(block)
        LOG.debug(f"Block #{block.number} ({block.timestamp_dt}) burned {block.burned_eth:.18f}")
        self._burned_eth = self._burned_eth + block.burned_eth

        if block.number % 10 == 0:
            now = int(time.time())
            if now >= self._eth_usd_price_time + 60:
                try:
                    self._eth_usd_price: Decimal = self._coinbase_client.get_price("ETH")
                    self._eth_usd_price_time = now
                    LOG.info(f"USD Price = ${self._eth_usd_price:,.2f}")

                except:
                    pass

            burned_usd: Decimal = self._burned_eth * self._eth_usd_price
            threshold_usd: Decimal = Decimal(6_000_000_000)
            filename_sub_str: str = f"burned_threshold_USD{threshold_usd:.0f}"
            LOG.info(f"Burned ${burned_usd:,.2f} ({self._burned_eth} ETH) as of block {block.number}")
            if burned_usd >= threshold_usd:
                # LOG.info(f"Threshold met: ${threshold_usd}")
                needs_tweet = self.needs_tweet(filename_sub_str)
                # LOG.info(f"Needs tweet: {filename_sub_str} = {needs_tweet}")
                if needs_tweet:
                    self._write_tweet_burned_eth_usd(filename_sub=filename_sub_str, threshold_usd=threshold_usd)

        if block.timestamp_dt >= now_hour:
            self._process_if_end_hour()

        if block.timestamp_dt >= prev_hour:
            self._process_if_threshold()

    # AMT BURNED

    def _write_tweet_burned_eth_usd(self, filename_sub: str, threshold_usd: Decimal) -> None:

        tweet_filename: str = self.tweet_filename(filename_sub)
        # write tweet to pending tweets dir

        tweet: str = f"Cumulative ${threshold_usd:,.0f} of ETH burned! 🔥 ({self._burned_eth:,.2f} ETH)"
        pending_filepath: str = os.path.join(pending_tweets_dir(), tweet_filename)
        LOG.info(f"Writing tweet {filename_sub} to {pending_filepath}")
        with open(pending_filepath, "w") as f:
            f.write(tweet)
        self._written.add(filename_sub)

    # FUNDAMENTALS

    def _process_if_fundamental_update(self) -> None:
        if self.last_block.timestamp_dt.hour == 12 + 7:
            fundamentals_hour_filename_str = f"fundamentals_{hour_str(self.last_block.hour_dt)}"
            if self.needs_tweet(fundamentals_hour_filename_str):
                metrics = self._trailing_aggregate(timedelta(days=30))

                # get price
                eth_usd_price: Decimal = self._coinbase_client.get_price("ETH")

                self._write_tweet_fundamentals(fundamentals_hour_filename_str, metrics, eth_usd_price)

    def _write_tweet_fundamentals(
        self, filename_sub: str, metrics: AggregateBlockMetrics, eth_usd_price: Decimal
    ) -> None:

        tweet_filename: str = self.tweet_filename(filename_sub)
        # write tweet to pending tweets dir

        tweet: str = write_tweet_fundamentals(metrics, eth_usd_price)
        pending_filepath: str = os.path.join(pending_tweets_dir(), tweet_filename)
        LOG.info(f"Writing tweet {filename_sub} to {pending_filepath}")
        with open(pending_filepath, "w") as f:
            f.write(tweet)
        self._written.add(filename_sub)

    # THRESHOLD

    MIN_BURN_THRESHOLD_TWEET: Decimal = Decimal(2_500_000)

    def _process_if_threshold(self) -> None:
        if self._burned_eth > self._burned_threshold:
            LOG.info(f"Burned: {self._burned_eth}")

            if self._burned_eth >= MIN_BURN_THRESHOLD_TWEET and self.needs_tweet(f"{self._burned_threshold}"):
                # get price
                eth_usd_price: Decimal = self._coinbase_client.get_price("ETH")

                self.write_tweet_threshold(eth_usd_price)
            self._burned_threshold += TWEET_THRESHOLD

    def write_tweet_threshold(self, eth_usd_price: Decimal) -> None:
        tweet_filename: str = self.tweet_filename(self._burned_threshold)
        # write tweet to pending tweets dir
        tweet: str = write_tweet_threshold(burnt_eth=self._burned_threshold, eth_usd_price=eth_usd_price)
        pending_filepath: str = os.path.join(pending_tweets_dir(), tweet_filename)
        LOG.info(f"Writing {self._burned_threshold} ETH burned tweet to {pending_filepath}")
        os.makedirs(os.path.dirname(pending_filepath), exist_ok=True)
        with open(pending_filepath, "w") as f:
            f.write(tweet)

    # TIME AGGREGATE

    def _process_if_end_hour(self) -> None:
        assert len(self._blocks) > 0
        # latest block
        block: Block = self._blocks[-1]

        if len(self._blocks) > 1:
            # block to summarize
            prev_block = self._blocks[-2]
            assert prev_block.number + 1 == block.number

            now = datetime.now()
            now_hour = now.replace(minute=0, second=0, microsecond=0)
            now_day = now_hour.replace(hour=0)
            prev_hour = now_hour - timedelta(hours=1)
            # new hour
            # summarize hour
            if block.hour_dt > prev_block.hour_dt:
                if self.needs_tweet(hour_str(prev_block.hour_dt)):
                    # check for bug
                    if block.timestamp_dt < now_hour:
                        LOG.error(f"Bad logic for block #{block.number} @ {block.timestamp_dt} vs now_hour={now_hour}")
                    else:
                        LOG.info(f"Processing hour before {block.timestamp_dt}...")
                        metrics: AggregateBlockMetrics = self.aggregate(hour_dt=prev_block.hour_dt)

                        # get price
                        eth_usd_price: Decimal = self._coinbase_client.get_price("ETH")
                        tweet_filename = self._write_tweet_aggregate(metrics=metrics, eth_usd_price=eth_usd_price)

                        self.write_svg(tweet_filename, metrics)

            # summarize day
            if block.day_dt > prev_block.day_dt:
                if self.needs_tweet(day_str(prev_block.day_dt)):
                    # get price
                    eth_usd_price: Decimal = self._coinbase_client.get_price("ETH")

                    LOG.info(f"Processing day before {block.timestamp_dt}...")
                    metrics: AggregateBlockMetrics = self.aggregate(day_dt=prev_block.day_dt)
                    tweet_filename = self._write_tweet_aggregate(metrics=metrics, eth_usd_price=eth_usd_price)

                    self.write_svg(tweet_filename, metrics)

    def tweet_filename(self, time_str: str) -> str:
        return f"tweet_{time_str}.txt"

    def needs_tweet(self, filename_substring: str) -> bool:
        if filename_substring in self._written:
            return False
        tweet_filename: str = self.tweet_filename(filename_substring)

        # check if already tweeted
        tweeted_filepath: str = os.path.join(tweeted_tweets_dir(), tweet_filename)
        if os.path.exists(tweeted_filepath):
            LOG.info(f"Tweet {filename_substring} already written")
            self._written.add(filename_substring)
            return False
        else:
            return True

    def _write_tweet_aggregate(self, metrics: AggregateBlockMetrics, eth_usd_price: Decimal) -> str:
        time_str = hour_str(metrics.hour) if isinstance(metrics, HourlyAggregateBlockMetrics) else day_str(metrics.day)
        time_range_str = (
            metrics.hour_range_str() if isinstance(metrics, HourlyAggregateBlockMetrics) else metrics.day_range_str()
        )

        tweet_filename: str = self.tweet_filename(time_str)
        # write tweet to pending tweets dir
        tweet: str = write_tweet_aggregate(metrics, eth_usd_price)
        pending_filepath: str = os.path.join(pending_tweets_dir(), tweet_filename)
        LOG.info(f"Writing tweet {time_range_str} to {pending_filepath}")
        with open(pending_filepath, "w") as f:
            f.write(tweet)

        return pending_filepath

    def write_svg(self, pending_filepath: str, metrics: AggregateBlockMetrics) -> None:
        assert pending_filepath.endswith(".txt")
        # svg
        eth_usd_price: Decimal = self._coinbase_client.get_price("ETH")
        svg: str = make_svg(metrics=metrics, eth_price_usd=eth_usd_price)
        pending_img_filepath_svg: str = pending_filepath.replace(".txt", ".svg")
        LOG.info(f"Write SVG file to {pending_img_filepath_svg}")
        with open(pending_img_filepath_svg, "w") as f:
            f.write(svg)

        # png
        pending_img_filepath_png: str = pending_filepath.replace(".txt", ".png")
        import cairosvg

        LOG.info(f"Write PNG file to {pending_img_filepath_png}")
        cairosvg.svg2png(url=pending_img_filepath_svg, write_to=pending_img_filepath_png)
        os.remove(pending_img_filepath_svg)

        return pending_img_filepath_png

    def _trailing_aggregate(self, delta: timedelta) -> None:
        last_block = self._blocks[len(self._blocks) - 1]
        start_dt = last_block.timestamp_dt - delta

        burnt_eth: Decimal = Decimal(0)
        start_number = None
        end_number = None
        cumulative_burnt_eth: Decimal = Decimal(0)
        base_issuance_eth: Decimal = Decimal(0)
        uncle_issuance_eth: Decimal = Decimal(0)
        for block in self._blocks:
            if block.timestamp_dt <= last_block.timestamp_dt:
                cumulative_burnt_eth += block.burned_eth

            if block.timestamp_dt >= start_dt and block.timestamp_dt <= last_block.timestamp_dt:
                burnt_eth = burnt_eth + block.burned_eth

                start_number = start_number if start_number is not None else block.number
                end_number = block.number

                base_issuance_eth = base_issuance_eth + block.base_issuance_eth
                uncle_issuance_eth = uncle_issuance_eth + block.uncle_reward_eth
        return AggregateBlockMetrics(
            start_number=start_number,
            end_number=end_number,
            burnt_eth=burnt_eth,
            cumulative_burned_eth=cumulative_burnt_eth,
            base_issuance_eth=base_issuance_eth,
            uncle_issuance_eth=uncle_issuance_eth,
        )

    def aggregate(
        self, hour_dt: Optional[datetime] = None, day_dt: Optional[datetime] = None
    ) -> DayAggregateBlockMetrics:
        assert (hour_dt is None) ^ (day_dt is None)
        burnt_eth: Decimal = Decimal(0)
        start_number = None
        end_number = None

        cumulative_burnt_eth: Decimal = self._cached_burned_eth
        base_issuance_eth: Decimal = Decimal(0)
        uncle_issuance_eth: Decimal = Decimal(0)
        for block in self._blocks:
            # count sum of previous
            if (hour_dt is not None and block.hour_dt <= hour_dt) or (day_dt is not None and block.day_dt <= day_dt):
                cumulative_burnt_eth = cumulative_burnt_eth + block.burned_eth

            # count within range
            if (hour_dt is not None and block.hour_dt == hour_dt) or (day_dt is not None and block.day_dt == day_dt):
                burnt_eth = burnt_eth + block.burned_eth

                start_number = start_number if start_number is not None else block.number
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
            return DayAggregateBlockMetrics(
                day=day_dt,
                start_number=start_number,
                end_number=end_number,
                burnt_eth=burnt_eth,
                cumulative_burned_eth=cumulative_burnt_eth,
                base_issuance_eth=base_issuance_eth,
                uncle_issuance_eth=uncle_issuance_eth,
            )
