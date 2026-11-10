import crix_upbit_pb
from typing import Any
from message_type import RawType, UnknownMessageType


def format_recentcrix(data: crix_upbit_pb.RecentCrix) -> str:
    rate = data.change_rate
    rate_str = f"{rate:+.2%}" if rate is not None else "N/A"
    return (
        f"[TICKER   ] {data.front_model_info.code:<10} "
        f"현재가={data.trade_price:>15,.0f} "
        f"전일대비={rate_str} "
        f"누적거래량={data.acc_trade_volume:.2f}"
    )



def format_crixtrade(data: crix_upbit_pb.CrixTrade) -> str:
    return (
        f"[TRADE    ] {data.front_model_info.code:<10} "
        f"가격={data.trade_price:>15,.0f} "
        f"수량={data.trade_volume:.4f}"
    )


def format_orderbook(data: crix_upbit_pb.CrixOrderbook) -> str:
    if not data.orderbook_units:
        return f"[ORDERBOOK] {data.market:<10} (레벨 없음)"
    best = data.orderbook_units[0]
    return (
        f"[ORDERBOOK] {data.front_model_info.code:<10} "
        f"매도호가={best.ask_price.value:>15,.0f} "
        f"매수호가={best.bid_price.value:>15,.0f} "
        f"총매도잔량={data.total_ask_size:.4f} "
        f"총매수잔량={data.total_bid_size:.4f}"
    )


def format_unknown(data: UnknownMessageType) -> str:
    return(
        f"[UNKNOWN] {data.message}"
    )

def format_raw(data: RawType) -> str:
    return(
        f"[RAW] "
        f"TYPE_BYTE: {data.type_byte_raw} / {data.type_byte}\n"
        f"HEADER: {data.header}\n"
        f"BODY: {data.body}\n"
    )



HANDLER_MAP = {
    crix_upbit_pb.RecentCrix: format_recentcrix,
    crix_upbit_pb.CrixTrade: format_crixtrade,
    crix_upbit_pb.CrixOrderbook: format_orderbook,
    RawType: format_raw,
}