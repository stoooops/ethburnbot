import json
import logging
import os
import shutil
from decimal import Decimal

from eth.types.block import AggregateBlockMetrics, Block, HourlyAggregateBlockMetrics, UncleBlock
from eth.utils.file_utils import block_filepath, uncle_block_filepath

LOG = logging.getLogger(__name__)


# TODO compute accurately this is just a snapshot taken. Small rounding error for now.
SUPPLY = 119_712_770


def write_block(block: Block, warn_overwrite: bool = False) -> None:
    filepath: str = block_filepath(block.number)
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    exists: bool = os.path.exists(filepath)
    tmp_filepath: str = f"{filepath}.tmp"
    with open(tmp_filepath, "w") as f:
        if not exists:
            LOG.info(f"Write block {block.number} @ {block.timestamp_dt} to {filepath}")
        elif warn_overwrite:
            LOG.warning(f"Overwrite block {block.number} @ {block.timestamp_dt} to {filepath}")
        else:
            LOG.debug(f"Overwrite block {block.number} @ {block.timestamp_dt} to {filepath}")

        f.write(json.dumps(block.json, indent=2))

    shutil.move(tmp_filepath, filepath)


def write_uncle_block(uncle_block: UncleBlock, warn_overwrite: bool = False) -> None:
    filepath = uncle_block_filepath(uncle_block.mined_block_num, uncle_block.uncle_index)
    exists = os.path.exists(filepath)
    tmp_filepath = f"{filepath}.tmp"
    with open(tmp_filepath, "w") as f:
        if not exists:
            LOG.info(f"Write uncle block {uncle_block.mined_block_num}[{uncle_block.uncle_index}] to {filepath}")
        elif warn_overwrite:
            LOG.warning(f"Overwrite uncle block {uncle_block.mined_block_num}[{uncle_block.uncle_index}] to {filepath}")
        else:
            LOG.debug(f"Overwrite uncle block {uncle_block.number} @ {uncle_block.timestamp_dt} to {filepath}")

        f.write(json.dumps(uncle_block.json, indent=2))

    shutil.move(tmp_filepath, filepath)


# TWEETS


def get_emoji(burnt_eth: Decimal) -> str:
    emoji = "🔥"
    val = burnt_eth
    while val / 10 >= 1:
        emoji = emoji + "🔥"
        val = val / 10
    return emoji


def to_billion_usd(num: Decimal) -> str:
    return f"${num / 1_000_000_000:,.2f}B"


def write_tweet_fundamentals(metrics: AggregateBlockMetrics, eth_usd_price: Decimal) -> str:
    period_burn = metrics.burnt_eth * eth_usd_price

    annualized_burn = period_burn * 365 / 30
    market_cap = eth_usd_price * SUPPLY

    return "\n".join(
        [
            "Fundamentals $ETH",
            "",
            f"Price: ${eth_usd_price:,.2f}",
            f"Market Cap: {to_billion_usd(market_cap)}",
            "",
            f"30d 🔥: {metrics.burnt_eth:,.0f} ETH ({to_billion_usd(period_burn)})",
            f"Annualized: {metrics.burnt_eth * 365/30:,.0f} ETH ({to_billion_usd(annualized_burn)})",
            "",
            f"Price / Revenue: {market_cap / annualized_burn:,.2f}",
        ]
    )


def calc_inflation_rate(metrics: AggregateBlockMetrics) -> Decimal:
    issuance_multiplier = 365 * (24 if isinstance(metrics, HourlyAggregateBlockMetrics) else 1)
    change_per_year: Decimal = issuance_multiplier * metrics.net_issuance_eth
    inflation_pct: Decimal = 100 * change_per_year / SUPPLY

    return inflation_pct


def write_tweet_aggregate(metrics: AggregateBlockMetrics, eth_usd_price: Decimal) -> str:
    emoji = get_emoji(metrics.burnt_eth)

    burned_price_usd = metrics.burnt_eth * eth_usd_price
    cumulative_burned_price_usd = metrics.cumulative_burned_eth * eth_usd_price

    inflation_pct = calc_inflation_rate(metrics)
    # no_burn_change_per_year =  365*24*metrics.issuance_eth
    # no_burn_annualized = 100 * no_burn_change_per_year / SUPPLY

    time_phrase = "last hour" if isinstance(metrics, HourlyAggregateBlockMetrics) else "yesterday"
    header_line = f"{metrics.burnt_eth:,.2f} $ETH burned {emoji} {time_phrase}."
    if int(metrics.burnt_eth) == 69:
        header_line += " Nice."
    header_line += f" (${burned_price_usd:,.0f})"

    annualized_line = f"Annualized: {inflation_pct:.2f}%"
    if inflation_pct < 0:
        annualized_line = annualized_line + " 📉"

    avg_gwei = metrics.gas_fees_paid / metrics.gas_used / Decimal(1_000_000_000)

    return "\n".join(
        [
            header_line,
            "",
            f"Average BASEFEE: {avg_gwei:,.2f} gwei",
            f"Issuance: {metrics.issuance_eth:,.2f} ETH",
            f"Net Change: {'+' if metrics.net_issuance_eth > 0 else ''}{metrics.net_issuance_eth:,.2f} ETH",
            annualized_line,
            "",
            f"Current Price: ${eth_usd_price:,.2f}",
            # "",
            # f"{metrics.time_range_str(delimiter=' ')} UTC",
            # f"Last Block: {metrics.end_number}",
            # "",
            # f"Cumulative 🔥: {metrics.cumulative_burned_eth:,.4f} ETH (${cumulative_burned_price_usd:,.0f})",
        ]
    )


def write_tweet_threshold(*, burnt_eth: Decimal, eth_usd_price: Decimal) -> str:
    total_price = burnt_eth * eth_usd_price

    tweet = f"Cumulative {burnt_eth:,.0f} $ETH burned! 🔥 (${total_price:,.0f})"
    if burnt_eth == 690000:
        tweet += "\n\nNice."
    return tweet
