"""업비트 웹사이트(www.upbit.com)가 실제로 사용하는 내부 실시간 시세 소켓
(wss://crix-ws-first.upbit.com/websocket) 프로토콜 디코더.

이 소켓은 공식 오픈API(api.upbit.com/websocket/v1)와는 완전히 다른,
비공개/미문서화 API다. 구독 시 반드시 {"format": "PRTBUF_LIST"}로 응답을
요청해야 하며(SIMPLE/JSON 등은 서버가 거부한다), 응답은 Protocol Buffers
바이너리로 온다. 공개된 .proto 스키마가 없어서, 실제 브라우저 트래픽을
캡처한 뒤 알려진 시세 값(가격/등락률/거래대금 등)과 대조하며 필드 번호의
의미를 역추적했다.

각 바이너리 프레임의 첫 1바이트는 메시지 종류를 나타내는 타입 바이트다.
    1 -> recentCrix   (현재가/등락/거래대금 등 - 공개API의 ticker에 해당)
    2 -> crixTrade    (체결)
    3 -> crixOrderbook (호가)
나머지 바이트가 Protocol Buffers 메시지 본문이다.

주의: 미문서화 API라 필드 의미 중 일부(특히 enum 값들)는 여러 상태(상승/
하락/보합, 매수/매도 등)를 다 관측하지 못해 확신도가 낮다. 그런 필드는
원본 값을 *_raw로 같이 남겨두었으니 실제로 이상하면 raw 값을 직접 비교해
보정하면 된다.
"""
from __future__ import annotations

import struct
from dataclasses import dataclass, field
from typing import Optional

CRIX_MARKET_PREFIX = "CRIX.UPBIT."

TYPE_BYTE_TICKER = 1
TYPE_BYTE_TRADE = 2
TYPE_BYTE_ORDERBOOK = 3

TYPE_BYTE_TO_KIND = {
    TYPE_BYTE_TICKER: "ticker",
    TYPE_BYTE_TRADE: "trade",
    TYPE_BYTE_ORDERBOOK: "orderbook",
}


def market_to_crix_code(market: str) -> str:
    """'KRW-BTC' -> 'CRIX.UPBIT.KRW-BTC'"""
    if market.startswith(CRIX_MARKET_PREFIX):
        return market
    return f"{CRIX_MARKET_PREFIX}{market}"


def crix_code_to_market(code: str) -> str:
    """'CRIX.UPBIT.KRW-BTC' -> 'KRW-BTC'"""
    return code[len(CRIX_MARKET_PREFIX):] if code.startswith(CRIX_MARKET_PREFIX) else code


# ---------------------------------------------------------------------------
# 최소한의 Protocol Buffers wire-format 파서 (스키마 없이 필드번호 기준으로 파싱)
# ---------------------------------------------------------------------------

def _read_varint(buf: bytes, pos: int) -> tuple[int, int]:
    result = 0
    shift = 0
    while True:
        b = buf[pos]
        pos += 1
        result |= (b & 0x7F) << shift
        if not (b & 0x80):
            return result, pos
        shift += 7


def parse_fields(buf: bytes) -> dict[int, list]:
    """필드번호 -> 값 리스트(반복 가능) 로 파싱한다.

    varint(wire 0) -> int
    fixed64(wire 1) -> 8바이트 원본 bytes (as_double로 변환해서 쓴다)
    length-delimited(wire 2) -> bytes (문자열이거나 중첩 메시지)
    fixed32(wire 5) -> 4바이트 원본 bytes
    """
    fields: dict[int, list] = {}
    pos = 0
    n = len(buf)
    while pos < n:
        tag, pos = _read_varint(buf, pos)
        field_no = tag >> 3
        wire_type = tag & 0x7
        if wire_type == 0:
            val, pos = _read_varint(buf, pos)
        elif wire_type == 1:
            val = buf[pos:pos + 8]
            pos += 8
        elif wire_type == 2:
            length, pos = _read_varint(buf, pos)
            val = buf[pos:pos + length]
            pos += length
        elif wire_type == 5:
            val = buf[pos:pos + 4]
            pos += 4
        else:
            # 알 수 없는 wire type을 만나면 더 이상 안전하게 파싱할 수 없으므로 중단.
            break
        fields.setdefault(field_no, []).append(val)
    return fields


def as_double(raw: bytes) -> float:
    return struct.unpack("<d", raw)[0]


def first(fields: dict[int, list], key: int, default=None):
    vals = fields.get(key)
    return vals[0] if vals else default


def first_double(fields: dict[int, list], key: int, default: Optional[float] = None) -> Optional[float]:
    vals = fields.get(key)
    if not vals:
        return default
    return as_double(vals[0])


def unwrap_double(raw: bytes) -> float:
    """오더북 호가 레벨에서 쓰이는 '래핑된 double' (하위 메시지 {1: fixed64}) 언래핑."""
    inner = parse_fields(raw)
    return as_double(inner[1][0])


# ---------------------------------------------------------------------------
# 타입별 디코더
# ---------------------------------------------------------------------------

@dataclass
class Trade:
    code: str
    market: str
    trade_price: float
    trade_volume: float
    prev_closing_price: float
    change_price: float
    trade_date: Optional[int]
    trade_time: Optional[int]
    trade_timestamp: Optional[int]
    change_raw: Optional[int]
    ask_bid_raw: Optional[int]


@dataclass
class Ticker:
    code: str
    market: str
    trade_price: float
    opening_price: float
    high_price: float
    low_price: float
    prev_closing_price: float
    change_price: float
    acc_trade_volume: float
    acc_trade_volume_24h: float
    acc_trade_price: float
    acc_trade_price_24h: float
    acc_ask_volume: Optional[float]
    acc_bid_volume: Optional[float]
    highest_52_week_price: Optional[float]
    highest_52_week_date: Optional[int]
    lowest_52_week_price: Optional[float]
    lowest_52_week_date: Optional[int]
    trade_date: Optional[int]
    trade_time: Optional[int]
    change_raw: Optional[int]
    ask_bid_raw: Optional[int]

    @property
    def change_rate(self) -> Optional[float]:
        if not self.prev_closing_price:
            return None
        return (self.trade_price - self.prev_closing_price) / self.prev_closing_price


@dataclass
class OrderbookUnit:
    ask_price: float
    bid_price: float
    ask_size: float
    bid_size: float


@dataclass
class Orderbook:
    code: str
    market: str
    total_ask_size: float
    total_bid_size: float
    total_ask_value: float
    total_bid_value: float
    units: list = field(default_factory=list)


def _decode_code(fields: dict[int, list]) -> tuple[str, str]:
    sub = parse_fields(first(fields, 1))
    code = first(sub, 1, b"").decode("utf-8", errors="replace")
    return code, crix_code_to_market(code)


def decode_trade(body: bytes) -> Trade:
    fields = parse_fields(body)
    code, market = _decode_code(fields)
    return Trade(
        code=code,
        market=market,
        trade_price=first_double(fields, 5, 0.0),
        trade_volume=first_double(fields, 6, 0.0),
        prev_closing_price=first_double(fields, 8, 0.0),
        change_price=first_double(fields, 10, 0.0),
        trade_date=first(fields, 2),
        trade_time=first(fields, 3),
        trade_timestamp=first(fields, 4),
        change_raw=first(fields, 7),
        ask_bid_raw=first(fields, 9),
    )


def decode_ticker(body: bytes) -> Ticker:
    fields = parse_fields(body)
    code, market = _decode_code(fields)
    return Ticker(
        code=code,
        market=market,
        trade_price=first_double(fields, 2, 0.0),
        opening_price=first_double(fields, 3, 0.0),
        high_price=first_double(fields, 4, 0.0),
        low_price=first_double(fields, 5, 0.0),
        acc_trade_volume=first_double(fields, 6, 0.0),
        acc_trade_volume_24h=first_double(fields, 7, 0.0),
        acc_trade_price=first_double(fields, 8, 0.0),
        acc_trade_price_24h=first_double(fields, 9, 0.0),
        trade_date=first(fields, 10),
        trade_time=first(fields, 11),
        change_raw=first(fields, 12),
        ask_bid_raw=first(fields, 13),
        prev_closing_price=first_double(fields, 16, 0.0),
        change_price=first_double(fields, 18, 0.0),
        acc_ask_volume=first_double(fields, 22),
        acc_bid_volume=first_double(fields, 23),
        highest_52_week_price=first_double(fields, 24),
        highest_52_week_date=first(fields, 25),
        lowest_52_week_price=first_double(fields, 26),
        lowest_52_week_date=first(fields, 27),
    )


def decode_orderbook(body: bytes) -> Orderbook:
    fields = parse_fields(body)
    code, market = _decode_code(fields)
    units = []
    for level_raw in fields.get(4, []):
        level = parse_fields(level_raw)
        units.append(
            OrderbookUnit(
                ask_price=unwrap_double(level[1][0]),
                bid_price=unwrap_double(level[2][0]),
                ask_size=unwrap_double(level[3][0]),
                bid_size=unwrap_double(level[4][0]),
            )
        )
    return Orderbook(
        code=code,
        market=market,
        total_ask_size=first_double(fields, 2, 0.0),
        total_bid_size=first_double(fields, 3, 0.0),
        total_ask_value=first_double(fields, 5, 0.0),
        total_bid_value=first_double(fields, 6, 0.0),
        units=units,
    )


def _split_entries(raw: bytes) -> list[tuple[int, bytes]]:
    """하나의 웹소켓 바이너리 프레임 안에는 메시지가 하나만 들어있을 수도,
    여러 개가 [4바이트 빅엔디안 길이][1바이트 타입][본문] 형태로 이어붙어
    올 수도 있다(구독 직후 스냅샷들이 한꺼번에 오는 경우 등). 길이 접두사
    구조로 끝까지 깔끔하게 나뉘면 그걸로 쓰고, 아니면 접두사 없이 프레임
    전체가 [1바이트 타입][본문] 하나짜리 메시지인 것으로 간주한다.
    """
    entries: list[tuple[int, bytes]] = []
    pos = 0
    n = len(raw)
    while pos < n:
        if pos + 5 > n:
            entries = []
            break
        length = int.from_bytes(raw[pos:pos + 4], "big")
        type_byte = raw[pos + 4]
        if length < 1 or pos + 4 + length > n or type_byte not in TYPE_BYTE_TO_KIND:
            entries = []
            break
        entries.append((type_byte, raw[pos + 5:pos + 4 + length]))
        pos += 4 + length
    if entries and pos == n:
        return entries
    if n >= 1:
        return [(raw[0], raw[1:])]
    return []


def decode_frames(raw: bytes):
    """수신한 웹소켓 바이너리 프레임 -> [(kind, 디코딩된 객체), ...].

    kind는 'ticker' / 'trade' / 'orderbook'. 알 수 없는 타입/파싱 실패는
    건너뛴다.
    """
    results = []
    for type_byte, body in _split_entries(raw):
        kind = TYPE_BYTE_TO_KIND.get(type_byte)
        try:
            if kind == "trade":
                results.append((kind, decode_trade(body)))
            elif kind == "ticker":
                results.append((kind, decode_ticker(body)))
            elif kind == "orderbook":
                results.append((kind, decode_orderbook(body)))
        except (IndexError, KeyError, struct.error):
            # 알 수 없는 변형 메시지는 조용히 건너뛴다 (미문서화 프로토콜 특성상 발생 가능).
            continue
    return results
