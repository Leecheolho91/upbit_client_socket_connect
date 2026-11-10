# upbit_socket

업비트(www.upbit.com) 실시간 시세 소켓에 연결해서 현재가(ticker) / 체결(trade)
/ 호가(orderbook) 데이터를 실시간으로 콘솔에 출력하는 예제입니다.

두 가지 클라이언트가 있습니다.

| 구분 | 소켓 주소 | 데이터 포맷 | 파일 |
|---|---|---|---|
| **공식 오픈API** | `wss://api.upbit.com/websocket/v1` | JSON | `client.py` / `main.py` |
| **www.upbit.com 웹사이트 내부 소켓** | `wss://crix-ws-first.upbit.com/websocket` | Protocol Buffers(바이너리) | `crix_client.py` / `crix_protocol.py` / `main_web.py` |

처음엔 공식 오픈API로 만들었는데, "업비트 웹사이트가 실제로 붙는 소켓"을
원하셔서 Playwright로 www.upbit.com에 직접 접속해 개발자도구 네트워크
트래픽을 캡처하고, 실제 시세 값과 대조해 바이너리 프로토콜을 역추적해서
`crix_client.py` 쪽을 새로 만들었습니다.

## ⚠️ crix 소켓은 비공식/미문서화 API입니다

`crix-ws-first.upbit.com`은 업비트가 공식 문서로 공개한 API가 아니라, 웹
프론트엔드가 내부적으로 쓰는 엔드포인트입니다. 즉:

- 언제든 예고 없이 바뀌거나 막힐 수 있습니다.
- 공개된 `.proto` 스키마가 없어서, 실제 값(가격/거래량/등락률 등)과
  대조해가며 필드 번호의 의미를 역추적했습니다. 가격/거래량/등락률/체결/
  호가 핵심 필드는 실측값과 정확히 맞아떨어져 신뢰도가 높지만, enum성
  필드 일부(상승/하락 신호, 매수/매도 구분 등)는 관측 표본이 적어 확신도가
  낮습니다 (`crix_protocol.py` 상단 주석 참고).
- 실서비스/트레이딩에 쓸 용도가 아니라면, 안정성이 필요할 땐 공식
  오픈API(`client.py`) 사용을 권장합니다.

## 설치

```bash
pip install -r requirements.txt
```

## 실행 — 웹사이트 내부 소켓 (crix)

```bash
# 기본값: KRW-BTC, 전체 타입(ticker/trade/orderbook) 출력
python main_web.py
python main_web.py --raw

# 여러 마켓 구독
python main_web.py --market KRW-BTC KRW-ETH

# 특정 타입만 필터링해서 출력 (현재가만)
python main_web.py --market KRW-BTC --types ticker

# 체결 + 호가만
python main_web.py --market KRW-BTC --types trade orderbook
```

## 실행 — 공식 오픈API

```bash
python main.py --market KRW-BTC KRW-ETH --types ticker trade
```

종료는 둘 다 `Ctrl+C`.

## 구조

- `crix_protocol.py` — crix 바이너리 프로토콜 디코더. 스키마 없이 Protocol
  Buffers wire format을 직접 파싱하고, 필드 번호 -> 의미(trade_price,
  acc_trade_volume 등) 매핑을 적용한다. 구독 요청에 여러 타입을 동시에
  넣으면 서버가 여러 메시지를 `[4바이트 길이][1바이트 타입][본문]` 형태로
  한 프레임에 묶어 보내는 경우가 있어, 그 배치 프레이밍도 함께 처리한다.
- `crix_client.py` — `CrixWebSocketClient`: crix 소켓 연결/구독/수신/재연결
  /PING 유지 및 타입별 콜백 디스패치.
- `main_web.py` — crix 클라이언트를 쓰는 CLI 예제.
- `client.py` / `main.py` — 공식 오픈API 클라이언트 및 CLI 예제.

## 타입 필터링을 코드에서 직접 쓰고 싶다면

```python
import asyncio
from crix_client import CrixWebSocketClient

async def main():
    client = CrixWebSocketClient(markets=["KRW-BTC"], kinds=["ticker", "trade"])
    client.on("ticker", lambda data: print(data.trade_price))  # ticker만 처리
    await client.run()

asyncio.run(main())
```
