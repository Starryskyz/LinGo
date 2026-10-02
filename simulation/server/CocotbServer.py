import asyncio, logging
import threading
import queue
from typing import Dict, Any, Optional, Tuple
import json, struct
from enum import IntEnum


class ResponseCode(IntEnum):
    """响应码枚举"""

    SUCCESS = 0
    ERROR = 1
    INVALID = 2


class CocotbMessageManager:
    """管理 cocotb 和 server 之间的消息队列"""

    def __init__(self):
        # 线程安全的队列
        self.to_cocotb_queue = queue.Queue()  # server -> cocotb Tuple[int,str,bytes]
        self.to_server_queue = queue.Queue()  # cocotb -> server Tuple[int,bytes]

        # 存储连接信息的字典
        self.connections = {}
        self.client_event: Dict[int, asyncio.Event] = {}
        self.client_resp: Dict[int, bytes] = {}

    def put_to_cocotb(self, id: int, command: str, data: bytes, event: asyncio.Event):
        """server 向 cocotb 发送消息"""
        self.client_event[id] = event
        self.to_cocotb_queue.put((id, command, data))

    def get_cocotb_response_message(self, id: int) -> bytes:
        return self.client_resp[id]

    def put_to_server(self, id: int, response: bytes):
        """cocotb 向 server 发送响应"""
        self.to_server_queue.put((id, response))

    def clear_client(self, id: int):
        """client断开连接后清除数据"""
        if id in self.client_event:
            self.client_event[id].set()
            del self.client_event[id]
        if id in self.client_resp:
            del self.client_resp[id]

    async def start_drain_message_from_cocotb(self):
        while True:
            if not self.to_server_queue.empty():
                id, resp = self.to_server_queue.get()
                if id in self.client_event:
                    self.client_event[id].set()
                self.client_resp[id] = resp
            else:
                await asyncio.sleep(0.1)


def getServerDefaultLogger() -> logging.Logger:
    logger = logging.getLogger("cocotb_server")
    logger.setLevel(logging.DEBUG)

    file_handler = logging.FileHandler('cocotb_server.log')
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    file_handler.setFormatter(file_formatter)

    # console_handler = logging.StreamHandler()
    # console_handler.setLevel(logging.DEBUG)
    logger.addHandler(file_handler)
    return logger


class CocotbServerThread(threading.Thread):
    """在独立线程中运行 server"""

    def __init__(
        self,
        message_queue: CocotbMessageManager,
        host='127.0.0.1',
        port=8888,
        logger=logging.Logger,
    ):
        super().__init__(daemon=True)
        self.message_queue = message_queue
        self.host = host
        self.port = port
        self.server = None
        self.loop = None
        self.logger = logger

    def run(self):
        """在新线程中运行 asyncio 事件循环"""
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

        # 修改 server 以使用消息队列
        self.server = CocotbSocketServer(
            message_queue=self.message_queue,
            logger=self.logger,
            host=self.host,
            port=self.port,
        )

        # 运行 server
        self.loop.run_until_complete(self.server.start())

    def stop(self):
        """停止 server"""
        if self.loop and self.server:
            self.loop.call_soon_threadsafe(self.loop.create_task, self.server.stop())


class CocotbSocketServer:
    def __init__(
        self, message_queue: CocotbMessageManager, logger, host='127.0.0.1', port=8888
    ):
        self.logger = logger
        self.host = host
        self.port = port
        self.server = None
        self.message_queue = message_queue
        self.client_counter = 0

    async def start(self):
        """
        启动服务器
        """
        self.server = await asyncio.start_server(
            self.handle_client, self.host, self.port
        )

        self.logger.info(f"Cocotb Server Launch at {self.host}:{self.port}")

        await self.message_queue.start_drain_message_from_cocotb()

        async with self.server:
            await self.server.serve_forever()

    async def handle_client(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ):
        """
        处理客户端连接

        请求格式:
        [header][command][data]
        [8 header]:[4 cmd长度][4 data长度]
        """
        addr = writer.get_extra_info('peername')
        id = self.client_counter
        self.client_counter += 1
        event = asyncio.Event()

        self.logger.info(f"Client {addr} Connect with id {id}")

        try:
            while True:
                # 1. 接收消息头
                header = await reader.readexactly(8)
                cmd_length = struct.unpack('<I', header[0:4])[0]
                data_length = struct.unpack('<I', header[4:8])[0]

                # 2. 接收完整消息
                command = await reader.readexactly(cmd_length)
                command = command.decode('utf-8')
                data = await reader.readexactly(data_length)

                self.logger.info(
                    f"[Socket] Receive command from {id}: {command}, data_length:{data_length}"
                )

                # 3. 将消息放入队列，交给 cocotb 处理
                event.clear()
                self.message_queue.put_to_cocotb(id, command, data, event)

                # 4. 从队列获取响应
                await event.wait()
                response_msg = self.message_queue.get_cocotb_response_message(id)

                self.logger.info(
                    f"[Socket] Send response to {id}: data_length:{response_msg.__len__()}"
                )

                self.logger.debug(
                    f"[Socket] Send response to {id}: data:{response_msg.hex()}"
                )

                # 发送响应
                writer.write(response_msg)
                await writer.drain()

        except (
            asyncio.IncompleteReadError,
            ConnectionResetError,
            ConnectionError,
        ) as e:
            self.logger.info(f"Client {addr} Disconnect: {e}")
        except Exception as e:
            self.logger.error(f"Error with {id}: {e}")
        finally:
            # 清理
            event.clear()
            self.message_queue.put_to_cocotb(id, "clear", b'', event)
            await event.wait()
            self.message_queue.clear_client(id)
            writer.close()
            await writer.wait_closed()
            self.logger.info(f"Client {addr} id {id} clear")


def build_response_message(
    response_code: ResponseCode, data: bytes, extra_info: dict
) -> bytes:
    """构建响应消息"""
    extra_info_json = json.dumps(extra_info).encode('utf-8')

    response = (
        struct.pack('<B', response_code)  # 响应码
        + struct.pack('<I', len(data))  # 数据长度
        + struct.pack('<I', len(extra_info_json))  # 额外信息长度
        + data  # 数据
        + extra_info_json  # 额外信息
    )

    return response
