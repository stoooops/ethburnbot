from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from logging import getLogger
from typing import Any, Dict, List, Optional

from potpourri.python.ethereum.block import BaseBlock, Block, UncleBlock

LOG = getLogger(__name__)


@dataclass
class AggregateBlockMetrics:
    burnt_eth: Decimal
    day: datetime
    start_number: int
    end_number: int
    cumulative_burned_eth: Decimal
    base_issuance_eth: Decimal
    uncle_issuance_eth: Decimal

    @property
    def num_blocks(self) -> int:
        return self.end_number - self.start_number + 1

    @property
    def issuance_eth(self) -> Decimal:
        return self.base_issuance_eth + self.uncle_issuance_eth

    @property
    def net_issuance_eth(self) -> Decimal:
        return self.issuance_eth - self.burnt_eth

    def time_range_str(self, delimiter="T") -> str:
        return self.day_range_str(delimiter=delimiter)

    def day_range_str(self, delimiter="T") -> str:
        next_day = self.day + timedelta(days=1)
        return (
            self.day.strftime(f"%Y-%m-%d{delimiter}%H:%M")
            + "-"
            + next_day.strftime("24:%M%Z")
        )

    def day_str(self) -> str:
        return self.day.strftime(f"%Y-%m-%d")

    def __str__(self) -> str:
        return str(vars(self))


@dataclass
class HourlyAggregateBlockMetrics(AggregateBlockMetrics):
    hour: datetime

    def hour_range_str(self, delimiter="T") -> str:
        next_hour = self.hour + timedelta(hours=1)
        return (
            self.hour.strftime(f"%Y-%m-%d{delimiter}%H:%M")
            + "-"
            + next_hour.strftime("%H:%M%Z")
        )

    def hour_str(self, delimiter="T") -> str:
        return self.hour.strftime(f"%Y-%m-%d{delimiter}%H:%M%Z")

    def time_range_str(self, delimiter="T") -> str:
        return self.hour_range_str(delimiter=delimiter)


class SummaryBlock(BaseBlock):
    def __init__(self, data: Dict[str, Any]):
        super().__init__(data)

        self._uncle_count: int = int(data["__uncle_count"])
        self._uncle_reward: int = int(data["__uncle_reward"])

    @property
    def uncle_count(self) -> int:
        return self._uncle_count

    @property
    def uncle_reward(self) -> int:
        return self._uncle_reward

    @property
    def uncle_reward_eth(self) -> Decimal:
        return Decimal(self._uncle_reward) / Decimal(10 ** 18)


class DetailedBlock(BaseBlock):
    def __init__(self, block: Block, uncles: Optional[List[UncleBlock]] = None):
        super().__init__(block._data)
        self._uncles = uncles if uncles is not None else []

    @property
    def uncle_count(self) -> int:
        return len(self._uncles)

    @property
    def uncle_reward(self) -> Decimal:
        return sum([u.uncle_reward for u in self._uncles])

    @property
    def json(self) -> Dict[str, Any]:
        return {
            **self._data,
            **{
                "__uncle_count": str(self.uncle_count),
                "__uncle_reward": str(self.uncle_reward),
            },
        }
