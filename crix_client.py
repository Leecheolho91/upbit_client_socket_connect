"""www.upbit.com 웹사이트가 실제로 연결하는 실시간 시세 소켓 클라이언트.

공식 오픈API(client.py, wss://api.upbit.com/websocket/v1)가 아니라, 브라우저로
upbit.com에 접속했을 때 프론트엔드가 직접 여는
wss://crix-ws-first.upbit.com/websocket 에 연결한다. 이건 비공개/미문서화
내부 API이므로 예고 없이 바뀌거나 막힐 수 있다는 점을 감안해서 쓸 것.
"""
from __future__ import annotations

import asyncio
import json
import uuid
from typing import Awaitable, Callable, Iterable, Optional, Union

import websockets
import crix_upbit_pb
from message_handler import HANDLER_MAP
from message_type import SOCKET_TYPES, UnknownMessageType, RawType, PUBLIC_TYPES


CRIX_WS_URL = "wss://crix-ws-first.upbit.com/websocket"
# 업비트 웹사이트가 실제로 구독하는 공개(비로그인) 데이터 타입
# 우리가 쓰는 타입 이름 -> 실제 crix 프로토콜 타입 이름


CRIX_MARKET_PREFIX = "CRIX.UPBIT."


def decode_frames(raw: bytes) -> list:
    """[4바이트 길이][1바이트 타입][본문]을 잘라서 protobuf 객체로 변환"""
    results = []
    pos = 0
    while pos + 5 <= len(raw):
        length = int.from_bytes(raw[pos:pos + 4], "big")
        type_byte = raw[pos + 4]
        body = raw[pos + 5:pos + 4 + length]
        cls = SOCKET_TYPES.get(type_byte)['message_type']
        if cls:  # 모르는 타입은 건너뜀
            msg = cls()
            msg.ParseFromString(body)
            results.append(msg)
        else:
            msg = UnknownMessageType()
            msg.message = f"type_byte가 정의되어 있지 않음: {type_byte}"
            results.append(msg)
        pos += 4 + length

    return results

def decode_frames_raw(raw: bytes) -> list:
    results = []
    pos = 0
    while pos + 5 <= len(raw):
        length = int.from_bytes(raw[pos:pos + 4], "big")
        header = raw[pos:pos + 5]
        type_byte = raw[pos + 4]
        type_byte_raw = raw[pos + 4: pos + 5]
        body = raw[pos + 5:pos + 4 + length]
        cls = SOCKET_TYPES.get(type_byte)['message_type']
        if cls:
            msg = RawType()
            msg.type_byte = type_byte
            msg.type_byte_raw = type_byte_raw
            msg.header = header
            msg.body = body
            msg.whole_message = raw
            msg.msg_type = type(cls)
        else:
            msg = UnknownMessageType()
            msg.type_byte = type_byte
            msg.message = f"type_byte가 정의되어 있지 않음: {type_byte}"
        results.append(msg)
        pos += 4 + length
    return results



def market_to_crix_code(market: str) -> str:
    """'KRW-BTC' -> 'CRIX.UPBIT.KRW-BTC'"""
    if market.startswith(CRIX_MARKET_PREFIX):
        return market
    return f"{CRIX_MARKET_PREFIX}{market}"

class CrixWebSocketClient:
    """업비트 웹사이트 내부 소켓(crix) 클라이언트.

    - kinds: 구독할 데이터 종류 ('ticker'/'trade'/'orderbook')
    - markets: 구독할 마켓 코드 (예: ['KRW-BTC'])
    """

    def __init__(
        self,
        markets: Iterable[str],
        kinds: Iterable[str] = PUBLIC_TYPES,
        ping_interval: float = 60.0,
        is_raw: bool = False,
        on_handler: bool = True,
    ) -> None:
        self._markets = list(markets)
        self._kinds = list(kinds)
        self._ping_interval = ping_interval
        self._is_raw = is_raw
        self._on_handler = on_handler
        self._is_print: bool = True
        self.decoded_message = None
        self.data = None
        


    def _build_request(self) -> str:
        codes = [market_to_crix_code(m) for m in self._markets]
        request = [{"ticket": f"pytest-practice-{uuid.uuid4()}"}, {"format": "PRTBUF_LIST"}]
        for kind in self._kinds:
            sub: dict = {"type": kind, "codes": codes}
            if kind == crix_upbit_pb.CrixOrderbook:
                sub["level"] = "0"
            if kind == crix_upbit_pb.Forex:
                sub["codes"] = ["FRX.KRWUSD", "FRX.KRWJPY", "FRX.KRWCNY",
            "FRX.KRWEUR"]
            request.append(sub)
        return json.dumps(request)

    def _dispatch(self, data: list):
        for d in data:
            handler = HANDLER_MAP.get(type(d))
            try:
                print(handler(d))
            except TypeError as exc:
                print(f'\033[31m{exc} - {type(d)}: handler를 찾을 수 없습니다. 전체를 보여줍니다.\033[0m')
                print(d)



    async def run(self) -> None:
        """연결 -> 구독 -> 수신 루프. 연결이 끊기면 자동 재연결한다."""
        while True:
            try:
                await self._run_once()
            except (websockets.ConnectionClosed, OSError) as exc:
                print(f"[crix_socket] 연결이 끊어졌습니다 ({exc!r}). 3초 후 재연결합니다.")
                await asyncio.sleep(3)

    async def _run_once(self) -> None:
        request = self._build_request()
        headers = {"Origin": "https://www.upbit.com"}
        async with websockets.connect(
            CRIX_WS_URL, additional_headers=headers, ping_interval=None
        ) as ws:
            await ws.send(request)
            print(f"[crix_socket] 연결 및 구독 완료: {request}")

            # 클라이언트가 살아 있음을 서버에 확인하는 ping을 _ping_interval 마다 보냄
            ping_task = asyncio.create_task(self._ping_loop(ws))
            try:
                decode_func = decode_frames_raw if self._is_raw else decode_frames # _is_raw 값에 따라 raw 데이터를 받을 지 결정
                handler_func = self._dispatch if self._on_handler else print
                while True:
                    raw = await ws.recv()
                    if isinstance(raw, str):
                        # 에러 메시지 등은 텍스트(JSON)로 온다.
                        print(f"[crix_socket] 텍스트 메시지: {raw}")
                        continue

                    self.data = decode_func(raw)
                    handler_func(self.data)

            finally:
                ping_task.cancel()

    async def _ping_loop(self, ws) -> None:
        try:
            while True:
                await asyncio.sleep(self._ping_interval)
                await ws.send("PING")
        except asyncio.CancelledError:
            pass
