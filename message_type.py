import random
import crix_upbit_pb


SOCKET_TYPES = {
    0: {'request_type': 'forex', 'message_type': crix_upbit_pb.Forex},
    1: {'request_type': 'recentCrix', 'message_type': crix_upbit_pb.RecentCrix},
    2: {'request_type': 'crixTrade', 'message_type': crix_upbit_pb.CrixTrade},
    3: {'request_type': 'crixOrderbook', 'message_type': crix_upbit_pb.CrixOrderbook},
    4: {'request_type': 'crixOrder', 'message_type': crix_upbit_pb.CrixOrder},
    5: {'request_type': 'shortRecentCrix', 'message_type': crix_upbit_pb.ShortRecentCrix},
    6: {'request_type': 'crixEvent', 'message_type': crix_upbit_pb.CrixEvent},
    7: {'request_type': 'baseCandle', 'message_type': crix_upbit_pb.BaseCandle},
    8: {'request_type': 'crixAsset', 'message_type': crix_upbit_pb.CrixAsset},
    126: {'request_type': 'frontError', 'message_type': crix_upbit_pb.FrontError},
    127: {'request_type': 'pingMessage', 'message_type': crix_upbit_pb.PingMessage}
}

class UnknownMessageType():
    #Unkonw message type 클래스, 알 수 없는 type_byte일때 사용, message는 각 사용처에서 알맞게 가공
    def __init__(self):
        self.type_byte = None
        self.header = None
        self.body = None
        self.msg_type = None
        self.message = None
        def __str__(self):
            return str(self.message)

class RawType():
    def __init__(self):
        self.type_byte = None
        self.type_byte_raw = None
        self.whole_message = None
        self.header = None
        self.body = None
        self.msg_type = None
    def __str__(self):
        return str(self.whole_message)


ALL_TYPES = [SOCKET_TYPES[i]['request_type'] for i in SOCKET_TYPES.keys()]
PUBLIC_TYPES = [
    SOCKET_TYPES[1]['request_type'],
    SOCKET_TYPES[2]['request_type'],
    SOCKET_TYPES[3]['request_type'],
    ]

