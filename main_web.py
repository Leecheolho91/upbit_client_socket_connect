"""www.upbit.com 웹사이트가 실제로 연결하는 실시간 소켓 데이터를 콘솔에 출력.

공식 오픈API(main.py)가 아니라 crix_client.py를 통해 브라우저와 동일한
wss://crix-ws-first.upbit.com/websocket 에 접속한다.

사용 예:
    python main_web.py                                # KRW-BTC, 전체 타입
    python main_web.py --market KRW-BTC KRW-ETH
    python main_web.py --market KRW-BTC --types ticker
    python main_web.py --market KRW-BTC --types trade orderbook
    python main_web.py --market KRW-BTC --raw          # 디코딩 없이 원본 바이트 출력
"""
from __future__ import annotations

import argparse
import asyncio
from datetime import datetime

from crix_client import PUBLIC_TYPES, CrixWebSocketClient



def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="업비트 웹사이트 실시간 소켓(crix) 시세 조회")
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
    parser.add_argument(
        "--raw",
        action="store_true",
        help="디코딩하지 않고 수신한 원본 바이너리 프레임을 그대로 출력한다.",
    )
    parser.add_argument(
        "--off_handler",
        action="store_false",
        help="handler로 메세지를 가공할지 안할지 결정한다",
    )
    return parser.parse_args()


def print_raw(raw: bytes) -> None:
    now = datetime.now().strftime("%H:%M:%S")
    print(f"{now} [RAW] {len(raw)} bytes: {raw!r}")


async def main() -> None:
    args = parse_args()
    client = CrixWebSocketClient(markets=args.market, kinds=args.types, is_raw=args.raw, on_handler=args.off_handler)

    print(f"[crix_socket] 마켓={args.market} 타입={args.types} 구독을 시작합니다. (Ctrl+C 종료)")
    await client.run()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[crix_socket] 종료합니다.")
