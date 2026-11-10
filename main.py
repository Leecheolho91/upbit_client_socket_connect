"""Upbit 실시간 웹소켓 데이터를 콘솔에 출력하는 예제 스크립트.

사용 예:
    python main.py                                   # KRW-BTC, 전체 타입
    python main.py --market KRW-BTC KRW-ETH           # 여러 마켓
    python main.py --market KRW-BTC --types ticker    # 현재가만 필터링
    python main.py --market KRW-BTC --types trade orderbook
"""
from __future__ import annotations

import argparse
import asyncio
from datetime import datetime

from client import PUBLIC_TYPES, Subscription, UpbitWebSocketClient


def format_ticker(data: dict) -> str:
    return (
        f"[TICKER   ] {data['code']:<10} "
        f"현재가={data['trade_price']:>15,} "
        f"전일대비={data['signed_change_rate']:+.2%} "
        f"거래량={data['trade_volume']:.4f}"
    )


def format_trade(data: dict) -> str:
    side = "매수" if data["ask_bid"] == "BID" else "매도"
    return (
        f"[TRADE    ] {data['code']:<10} "
        f"{side} 가격={data['trade_price']:>15,} "
        f"수량={data['trade_volume']:.4f}"
    )


def format_orderbook(data: dict) -> str:
    best = data["orderbook_units"][0]
    return (
        f"[ORDERBOOK] {data['code']:<10} "
        f"매도호가={best['ask_price']:>15,} "
        f"매수호가={best['bid_price']:>15,} "
        f"총매도잔량={data['total_ask_size']:.4f} "
        f"총매수잔량={data['total_bid_size']:.4f}"
    )


FORMATTERS = {
    "ticker": format_ticker,
    "trade": format_trade,
    "orderbook": format_orderbook,
}


def print_message(data: dict) -> None:
    now = datetime.now().strftime("%H:%M:%S")
    formatter = FORMATTERS.get(data.get("type", ""))
    line = formatter(data) if formatter else str(data)
    print(f"{now} {line}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="업비트 실시간 웹소켓 시세 조회")
    parser.add_argument(
        "--market",
        nargs="+",
        default=["KRW-BTC"],
        help="구독할 마켓 코드 (예: KRW-BTC KRW-ETH). 기본값: KRW-BTC",
    )
    parser.add_argument(
        "--types",
        nargs="+",
        choices=PUBLIC_TYPES,
        default=list(PUBLIC_TYPES),
        help="구독 및 출력할 데이터 타입. 기본값: 전체(ticker trade orderbook)",
    )
    return parser.parse_args()


async def main() -> None:
    args = parse_args()
    subscriptions = [Subscription(type=t, codes=args.market) for t in args.types]

    client = UpbitWebSocketClient(subscriptions=subscriptions, types=args.types)
    client.on_message(print_message)

    print(f"[upbit_socket] 마켓={args.market} 타입={args.types} 구독을 시작합니다. (Ctrl+C 종료)")
    await client.run()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[upbit_socket] 종료합니다.")
