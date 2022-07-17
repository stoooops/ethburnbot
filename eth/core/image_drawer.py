from datetime import datetime
from decimal import Decimal
from logging import getLogger

from eth.core.writer import calc_inflation_rate, to_billion_usd
from eth.types.block import AggregateBlockMetrics, DayAggregateBlockMetrics, HourlyAggregateBlockMetrics

LOG = getLogger(__name__)


def day_str(day: datetime) -> str:
    return day.strftime(f"%Y-%m-%d")


def hour_str(hour: datetime, delimiter="T") -> str:
    return hour.strftime(f"%Y-%m-%d{delimiter}%H:%M%Z")


def make_svg(metrics: AggregateBlockMetrics, eth_price_usd: Decimal) -> str:
    is_hourly = isinstance(metrics, HourlyAggregateBlockMetrics)
    report_name = f"{'Hourly' if is_hourly else 'Daily'} Report"
    time_str = metrics.hour_range_str(delimiter=" ") if is_hourly else metrics.day_range_str(delimiter=" ")

    graph_bar_width = 120
    graph_height = 400

    graph_start_x = 80
    graph_start_y = 320
    graph_end_x = 1000
    graph_text_pad = 8

    graph_issuance_start_x = 200
    graph_issuance_center_x = graph_issuance_start_x + graph_bar_width / 2
    graph_burn_start_x = 400
    graph_burn_center_x = graph_burn_start_x + graph_bar_width / 2

    cumulative_burned_eth = metrics.cumulative_burned_eth
    cumulative_burned_usd = cumulative_burned_eth * eth_price_usd
    cumulative_burned_usd_billions = to_billion_usd(cumulative_burned_usd)
    burned_eth = metrics.burnt_eth
    burned_usd = metrics.burnt_eth * eth_price_usd
    issuance_eth = metrics.issuance_eth
    net_change_eth = metrics.issuance_eth - metrics.burnt_eth
    inflation_pct = calc_inflation_rate(metrics)

    burn_ratio: Decimal = burned_eth / issuance_eth
    graph_burned_height: int = int(round(burn_ratio * graph_height))
    too_big_ratio = Decimal(1.2)
    if burn_ratio > too_big_ratio:
        # scale back graph so it is 1.5* the issuance size?
        graph_height *= too_big_ratio / burn_ratio
        graph_burned_height = int(round(burn_ratio * graph_height))

    issuance_color: str = "#4f7942"
    graph_net_change_color: str = "transparent" if net_change_eth < 0 else issuance_color
    graph_net_change_height = graph_height - graph_burned_height  # transparent when negative
    graph_end_y = graph_start_y + graph_height

    text_color: str = "white"
    bar_radius_issuance: int = 0
    bar_radius_burn: int = 0
    background_color: str = "#181818"

    return f"""
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1600 900">
    <style>
    .txt {{
        fill: {text_color};
        font-family: Roboto Mono, monospace;
    }}
    .header {{
        font-size: 84px ;
    }}
    .hanging {{
        dominant-baseline: hanging;
    }}
    .report {{
        font-size: 36px;
    }}
    .small {{
        font-size: 20px;
    }}
    .midsmall {{
        font-size: 22px;
    }}
    .medium {{
        font-size: 24px;
    }}
    .bold {{
        font-weight: bold;
    }}
    .big {{
        font-size: 26px;
    }}
    .transparent {{
        fill: transparent;
        stroke: transparent;
    }}
    .issuance-bar {{
        fill: {issuance_color};
        stroke: {issuance_color};
        stroke-width: 4px;
    }}
    .bottom-line {{
        stroke: {issuance_color};
    }}
    .graph-net-change-block {{
        fill: {graph_net_change_color};
        stroke: {graph_net_change_color};
    }}
    .white {{
        fill: white;
        stroke: white;
        stroke-width: 4px;
    }}
    .red {{
        fill: #B23227;
        stroke: #B23227;
    }}
    .inflation {{
        font-size: 48pt;
    }}
    .line {{
        stroke-width: 4px;
    }}
    .dashed {{
        stroke-dasharray: 4 8;
    }}
    .totalburntxt {{
        font-size: 96px;
    }}
    .graph-soft {{
        stroke-opacity: 0.8;
    }}
    .fade {{
        stroke-opacity: 0.65;
        opacity: 0.65;
    }}
    .hardfade {{
        stroke-opacity: 0.25;
        opacity: 0.25;
    }}
    .deflationary {{
        fill: #F4900C;
    }}
    .darkgrey {{
        fill: #393A3C;
    }}
    .background {{
        fill: {background_color};
    }}
    .nostroke {{
        stroke: none;
        storke-width: 0px;
    }}
    </style>
    <!-- background color -->
    <rect width="1600" height="900" class="background"/>

    <!-- Main header text -->
    <svg viewBox="0 0 400 200">
        <g transform="translate(20,8)">
            <path fill="#B23227" d="M35 19c0-2.062-.367-4.039-1.04-5.868-.46 5.389-3.333 8.157-6.335 6.868-2.812-1.208-.917-5.917-.777-8.164.236-3.809-.012-8.169-6.931-11.794 2.875 5.5.333 8.917-2.333 9.125-2.958.231-5.667-2.542-4.667-7.042-3.238 2.386-3.332 6.402-2.333 9 1.042 2.708-.042 4.958-2.583 5.208-2.84.28-4.418-3.041-2.963-8.333C2.52 10.965 1 14.805 1 19c0 9.389 7.611 17 17 17s17-7.611 17-17z"/>
            <path fill="#F4900C" d="M28.394 23.999c.148 3.084-2.561 4.293-4.019 3.709-2.106-.843-1.541-2.291-2.083-5.291s-2.625-5.083-5.708-6c2.25 6.333-1.247 8.667-3.08 9.084-1.872.426-3.753-.001-3.968-4.007C7.352 23.668 6 26.676 6 30c0 .368.023.73.055 1.09C9.125 34.124 13.342 36 18 36s8.875-1.876 11.945-4.91c.032-.36.055-.722.055-1.09 0-2.187-.584-4.236-1.606-6.001z"/>
        </g>
    </svg>
    <text x="250" y="180" class="txt header">{burned_eth:,.2f} ETH Burned</text>
    <text x="260" y="225" class="txt medium">${burned_usd:,.0f}</text>

    <!-- Top right rect -->
    <rect x="1000" width="600" height="56" class="red"/>
    <polygon points="1000,0 1000,56 944,0" class="red" />
    <text x="1580" y="6" class="txt report hanging" writing-mode="rl" text-anchor="end">@ethburnbot | {report_name}</text>
    <text x="1580" y="66" class="txt report small hanging" writing-mode="rl" text-anchor="end">{time_str} UTC</text>

    <!-- Bottom left rect -->
    <polygon points="0,900 604,900 560,856 0,856" class="red fade" />
    <text x="20" y="885" class="txt small fade">moneyblocks.eth</text>
    <line x1="210" x2="210" y1="900" y2="856" class="white fade" />
    <text x="228" y="885" class="txt small fade"> Contact @cory_eth for inquiries</text>

    <!-- Graph -->

    <!-- Issuance -->
    <text x="{graph_issuance_center_x}" y="{graph_start_y - graph_text_pad}" class="txt small" text-anchor="middle" >Issued</text>
    <text x="{graph_issuance_center_x}"
          y="{graph_start_y + graph_text_pad}"
          class="txt small"
          text-anchor="middle" style="dominant-baseline: hanging">+{issuance_eth:,.2f}</text>
    <rect x="{graph_issuance_start_x}"
          width="{graph_bar_width}"
          y="{graph_start_y + 3}"
          height="{ min(graph_burned_height, graph_height)}"
          class="issuance-bar hardfade graph-soft nostroke"
          />
    <line x1="{graph_issuance_start_x}"
          x2="{graph_issuance_start_x}"
          y1="{graph_start_y + 3}"
          y2="{graph_start_y + min(graph_burned_height, graph_height)}"
          class="issuance-bar line dashed graph-soft"/>
    <line x1="{graph_issuance_start_x + graph_bar_width}"
          x2="{graph_issuance_start_x + graph_bar_width}"
          y1="{graph_start_y + 3}"
          y2="{graph_start_y + min(graph_burned_height, graph_height)}"
          class="issuance-bar line dashed graph-soft"/>
    <!-- radius -->
    <rect x="{graph_issuance_start_x}"
          width="{graph_bar_width}"
          y="{graph_end_y - graph_net_change_height}"
          height="{graph_net_change_height}"
          rx="{bar_radius_issuance}"
          ry="{bar_radius_issuance}"
          class="graph-net-change-block graph-soft nostroke"
          />
    <!-- overlay except bottom radius part -->
    <rect x="{graph_issuance_start_x}"
          width="{graph_bar_width}"
          y="{graph_end_y - graph_net_change_height}"
          height="{max(0, graph_net_change_height - bar_radius_issuance)}"
          class="graph-net-change-block graph-soft nostroke"
          />
    <!-- Net Change -->
    <text x="{graph_issuance_center_x}"
          y="{graph_end_y + graph_text_pad}"
          class="txt small hanging"
          text-anchor="middle">Net Change</text>
    <text x="{graph_issuance_center_x}"
          y="{graph_end_y + graph_text_pad + 20 + graph_text_pad}"
          class="txt small"
          text-anchor="middle"
          style="dominant-baseline: hanging">{'+' if net_change_eth > 0 else ''}{net_change_eth:,.2f}</text>

    <!-- Top Line -->
    <line x1="{graph_start_x}"
          y1="{graph_start_y}"
          x2="{graph_end_x}"
          y2="{graph_start_y}"
          class="red line graph-soft" />
    <!-- Bottom Line -->
    <line x1="{graph_start_x}"
          y1="{graph_start_y + graph_height}"
          x2="{graph_burn_start_x + graph_bar_width + 120}"
          y2="{graph_start_y + graph_height}"
          class="bottom-line line graph-soft" />

    <!-- Burn -->
    <text x="{graph_burn_center_x}"
          y="{graph_start_y - graph_text_pad}"
          class="txt small"
          text-anchor="middle">Burned</text>
    <text x="{graph_burn_center_x}"
          y="{graph_start_y + graph_burned_height + graph_text_pad}"
          class="txt small"
          text-anchor="middle"
          style="dominant-baseline: hanging">-{burned_eth:,.2f}</text>
    <rect x="{graph_burn_start_x}"
          width="{graph_bar_width}"
          y="{graph_start_y}"
          height="{graph_burned_height}"
          rx="{bar_radius_burn}"
          ry="{bar_radius_burn}"
          class="red graph-soft nostroke" />
    <rect x="{graph_burn_start_x}"
          width="{graph_bar_width}"
          y="{graph_start_y}"
          height="{max(0, graph_burned_height - bar_radius_burn)}"
          class="red graph-soft nostroke" />

    <!-- Inflation Pct -->
    <text x="800"
          y="{graph_start_y - graph_text_pad}"
          class="txt small"
          text-anchor="middle">Annualized Inflation</text>
    <text x="800"
          y="{graph_start_y + graph_text_pad + 50}"
          class="txt inflation{'' if inflation_pct > 0 else ' deflationary'}"
          text-anchor="middle"
          style="dominant-baseline: middle">{'+' if inflation_pct > 0 else ''}{inflation_pct:,.2f}%</text>

    <!-- Cumlative Burn graphic -->
    <svg viewBox="0 0 150 75">
        <g transform="translate(108,30)" class="fade">
            <path fill="#B23227" d="M35 19c0-2.062-.367-4.039-1.04-5.868-.46 5.389-3.333 8.157-6.335 6.868-2.812-1.208-.917-5.917-.777-8.164.236-3.809-.012-8.169-6.931-11.794 2.875 5.5.333 8.917-2.333 9.125-2.958.231-5.667-2.542-4.667-7.042-3.238 2.386-3.332 6.402-2.333 9 1.042 2.708-.042 4.958-2.583 5.208-2.84.28-4.418-3.041-2.963-8.333C2.52 10.965 1 14.805 1 19c0 9.389 7.611 17 17 17s17-7.611 17-17z"/>
            <path fill="#F4900C" d="M28.394 23.999c.148 3.084-2.561 4.293-4.019 3.709-2.106-.843-1.541-2.291-2.083-5.291s-2.625-5.083-5.708-6c2.25 6.333-1.247 8.667-3.08 9.084-1.872.426-3.753-.001-3.968-4.007C7.352 23.668 6 26.676 6 30c0 .368.023.73.055 1.09C9.125 34.124 13.342 36 18 36s8.875-1.876 11.945-4.91c.032-.36.055-.722.055-1.09 0-2.187-.584-4.236-1.606-6.001z"/>
        </g>
    </svg>
    <!-- Cumlative Burn label -->
    <text x="1342"
          y="580"
          class="txt totalburntxt"
          text-anchor="middle"
          style="dominant-baseline: middle">{cumulative_burned_usd_billions}</text>
    <text x="1342"
          y="650"
          class="txt big bold"
          text-anchor="middle"
          style="dominant-baseline: hanging">Cumulative Burn</text>
    <text x="1342"
          y="688"
          class="txt midsmall"
          text-anchor="middle"
          style="dominant-baseline: hanging">{cumulative_burned_eth:,.2f} ETH</text>

    <!-- Block Height label -->
    <text x="{1600 - graph_text_pad}"
          y="{900 - graph_text_pad}"
          class="txt small fade"
          writing-mode="rl"
          text-anchor="end">Block Height: {metrics.end_number}</text>

</svg>

"""


def draw_graph(metrics, eth_usd_price, svg_filename):
    """
    Draws the graph and writes it to the output file.
    """
    import os

    import cairosvg

    # Render the SVG.
    svg = make_svg(metrics=metrics, eth_price_usd=eth_usd_price)

    # Write the SVG.
    with open(svg_filename, "w") as f:
        f.write(svg)

    cairosvg.svg2png(url=svg_filename, write_to=svg_filename.replace("svg", "png"))
    os.remove(svg_filename)


def main() -> None:
    """
    Main function.
    """
    from potpourri.python.ethereum.coinbase.client import CoinbaseClient

    # Get the data.
    eth_usd_price: Decimal = CoinbaseClient().get_price("ETH")
    metrics = DayAggregateBlockMetrics(
        day=datetime.now().date(),
        start_number=1,
        end_number=1000000,
        burnt_eth=Decimal(100),
        cumulative_burned_eth=Decimal(2500000),
        base_issuance_eth=Decimal(500),
        uncle_issuance_eth=Decimal(0),
    )
    draw_graph(metrics=metrics, eth_usd_price=eth_usd_price, svg_filename="graph.svg")

    metrics2 = DayAggregateBlockMetrics(
        day=metrics.day,
        start_number=metrics.start_number,
        end_number=metrics.end_number,
        cumulative_burned_eth=metrics.cumulative_burned_eth,
        burnt_eth=Decimal(500),
        base_issuance_eth=Decimal(500),
        uncle_issuance_eth=metrics.uncle_issuance_eth,
    )
    draw_graph(metrics=metrics2, eth_usd_price=eth_usd_price, svg_filename="graph2.svg")

    metrics3 = DayAggregateBlockMetrics(
        day=metrics.day,
        start_number=metrics.start_number,
        end_number=metrics.end_number,
        cumulative_burned_eth=metrics.cumulative_burned_eth,
        burnt_eth=Decimal(700),
        base_issuance_eth=Decimal(500),
        uncle_issuance_eth=metrics.uncle_issuance_eth,
    )
    draw_graph(metrics=metrics3, eth_usd_price=eth_usd_price, svg_filename="graph3.svg")


if __name__ == "__main__":
    main()
