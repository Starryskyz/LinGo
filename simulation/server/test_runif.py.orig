from typing import Union, List, Optional, Dict, Any, Tuple, Callable
from dataclasses import dataclass
from enum import Enum, auto
import cocotb, logging, threading, struct, numpy, heapq, json, copy
import dataclasses
from operator import attrgetter


class StreamFunction(Enum):
    CONFIG = auto()
    MEMCPY_HOSTTODEVICE = auto()
    MEMCPY_DEVICETOHOST = auto()
    EXECUTION_START = auto()
    MEMCPY_FENCE = auto()
    EVENT_WAIT = auto()
    EVENT_SET = auto()
    RELEASE = auto()
    APPLY = auto()


@dataclass
class DeviceInfo:
    # 目前假设
    # reg_cfg_base_addr_0, reg_cfg_num_0  长度为 reg_cfg_num_reglength
    # reg_cfg_en_tile_0, reg_exe_done_0, reg_exe_tile_ens_0 长度为 "tile_num"/ 8  取整到reg_bit_width
    # reg_exe_iob_ens_0 长度为 "tile_num"*"tile_iob_bank_num"/ 8  取整到reg_bit_width
    reg_bit_width: int
    tile_num: int
    tile_iob_bank_num: int
    tile_pe_address: int
    tile_spm_address: int

    config_start_address: int
    config_end_address: int
    cfg_spad_data_bytewidth: int  ## @jhlou 20250904

    reg_cfg_base_addr_0: int
    reg_cfg_num_0: int
    reg_cfg_num_reglength: int

    reg_cfg_en_tile_reglength: int
    reg_cfg_en_tile_0: int
    reg_cfg_en: int

    reg_exe_tile_ens_0: int
    reg_exe_iob_ens_reglength: int
    reg_exe_iob_ens_0: int
    reg_exe_start: int
    reg_exe_done_0: int

    cfg_addr_width: int = 16
    cfg_data_width: int = 32

    def ConvertConfigToByteArray(
        self, config_values: List[int], offset: int
    ) -> bytearray:
        # 目前假设config 16bit
        split_16bit = lambda x: [x & 0xFF, x >> 8]
        k1 = self.cfg_data_width // 16
        k2 = (self.cfg_data_width + self.cfg_addr_width) // 16
        config = bytearray()
        for index, value in enumerate(config_values):
            config.extend(split_16bit(value if index % k2 < k1 else value + offset))

        return config


# @jhlou
def create_device_info_factory(reg_json_path: str, adg_json_path: str) -> DeviceInfo:
    """
    工厂函数：创建 DeviceInfo 对象

    Args:
        reg_json_path: 寄存器配置文件路径, axilite_spec.json
        adg_json_path: 架构配置文件路径, vitra_cgra_adg.json

    Returns:
        DeviceInfo: 设备信息对象
    """
    # base_dir = os.path.dirname(os.path.abspath(__file__))

    # # 设置默认路径
    # if reg_json_path is None:
    #     reg_json_path = os.path.join(base_dir, "../../rtl/spec/axilite_spec.json")

    # if adg_json_path is None:
    #     adg_json_path = os.path.join(base_dir, "../../rtl/spec/vitra_cgra_adg.json")

    # 读取配置文件
    with open(reg_json_path, "r") as f:
        reg_cfg = json.load(f)
    with open(adg_json_path, "r") as f:
        arch_cfg = json.load(f)

    # 计算配置值
    reg_bit_width = reg_cfg["reg_bit_width"]
    # reg_bit_width = 8
    tile_num = reg_cfg.get("tile_num", arch_cfg.get("cgra_tile_num"))
    tile_iob_bank_num = reg_cfg["tile_iob_bank_num"]
    tile_pe_address = arch_cfg["cfg_tile_offset"]
    tile_spm_address = tile_iob_bank_num * arch_cfg["iob_spad_bank_size"]

    config_start_address = tile_num * tile_spm_address
    config_end_address = config_start_address + arch_cfg["cfg_spad_size"]

    cfg_spad_data_bytewidth = arch_cfg["cfg_spad_data_width"] // 8

    # 目前假设
    # reg_cfg_base_addr_0, reg_cfg_num_0  长度为 reg_cfg_num_reglength
    # reg_cfg_en_tile_0, reg_exe_done_0 长度为 "tile_num"/ "reg_bit_width"
    # reg_exe_iob_ens_0 长度为 "tile_num"*"tile_iob_bank_num"/ "reg_bit_width"
    reg_cfg_base_addr_0 = int(reg_cfg["reg_cfg_base_addr_0"], 16)
    reg_cfg_num_0 = int(reg_cfg["reg_cfg_num_0"], 16)
    reg_cfg_num_reglength = (
        int(numpy.ceil(numpy.log2(arch_cfg["cfg_spad_size"]) / reg_bit_width))
        * reg_bit_width
        // 8
    )

    reg_cfg_en_tile_reglength = (
        (tile_num + reg_bit_width - 1) // reg_bit_width * reg_bit_width // 8
    )
    reg_exe_iob_ens_reglength = (
        (tile_num * tile_iob_bank_num + reg_bit_width - 1)
        // reg_bit_width
        * reg_bit_width
        // 8
    )

    reg_cfg_en_tile_0 = int(reg_cfg["reg_cfg_en_tile_0"], 16)
    reg_cfg_en = int(reg_cfg["reg_cfg_en"], 16)

    reg_exe_iob_ens_0 = int(reg_cfg["reg_exe_iob_ens_0"], 16)
    reg_exe_tile_ens_0 = int(reg_cfg["reg_exe_tile_ens_0"], 16)
    reg_exe_start = int(reg_cfg["reg_exe_start"], 16)
    reg_exe_done_0 = int(reg_cfg["reg_exe_done_0"], 16)

    device1 = DeviceInfo(
        reg_bit_width=reg_bit_width,
        tile_num=tile_num,
        tile_iob_bank_num=tile_iob_bank_num,
        tile_pe_address=tile_pe_address,
        tile_spm_address=tile_spm_address,
        config_start_address=config_start_address,
        config_end_address=config_end_address,
        cfg_spad_data_bytewidth=cfg_spad_data_bytewidth,  # @jhlou 20250904
        reg_cfg_base_addr_0=reg_cfg_base_addr_0,
        reg_cfg_num_0=reg_cfg_num_0,
        reg_cfg_num_reglength=reg_cfg_num_reglength,
        reg_cfg_en_tile_reglength=reg_cfg_en_tile_reglength,
        reg_cfg_en_tile_0=reg_cfg_en_tile_0,
        reg_cfg_en=reg_cfg_en,
        reg_exe_tile_ens_0=reg_exe_tile_ens_0,
        reg_exe_iob_ens_reglength=reg_exe_iob_ens_reglength,
        reg_exe_iob_ens_0=reg_exe_iob_ens_0,
        reg_exe_start=reg_exe_start,
        reg_exe_done_0=reg_exe_done_0,
    )

    if (
        reg_cfg_num_0 < reg_cfg_base_addr_0 + reg_cfg_num_reglength
        or reg_cfg_en_tile_0 < reg_cfg_num_0 + reg_cfg_num_reglength
        or reg_cfg_en < reg_cfg_en_tile_0 + reg_cfg_en_tile_reglength
        or reg_exe_start < reg_exe_iob_ens_0 + reg_exe_iob_ens_reglength
    ):
        raise ValueError(f"wrong device config, with {device1}")

    # 创建并返回对象
    return device1


@dataclass
class DeviceData:
    address: int = 0
    size: int = 0

    def end(self) -> int:
        return self.address + self.size


@dataclass
class DeviceConfig:
    """len(iob_en)/tile_iob_bank_num = tile_num, iob_en每一位对应一个寄存器"""

    config_values: List[int]
    iob_en: List[int]
    tile_en: List[int]
    data_ptr: List[DeviceData]


@dataclass(repr=False)
class ResourceMappingHandler:
    stream_id: int

    device_id: int
    max_pe_usage_addr: int
    total_tiles: int
    offset_starting_tile: int
    offset_pe_address: int
    offset_spm_address: int

    config_num: int
    configs: List[DeviceConfig]
    iob_en_bytes: List[bytes]
    tile_en_bytes: List[bytes]
    config_total_size: int
    config_ptrs: List[DeviceData]  # 真正位置在address+对应device的config_start_address
    config_id_current: int
    running: bool  # True EXE.S后但尚未进行EXE.F

    arrival_time: float
    start_time: float
    exes_time: float
    exef_time: float
    valid: bool

    def __init__(self, stream_id: int):
        self.stream_id = stream_id
        self.configs = []
        self.tile_en_bytes = []  # @jhlou
        self.iob_en_bytes = []
        self.config_ptrs = []
        self.clear()

    def clear(self):

        self.device_id = -1
        self.max_pe_usage_addr = 0
        self.total_tiles = 0
        self.offset_starting_tile = 0
        self.offset_pe_address = 0
        self.offset_spm_address = 0

        self.config_num = 0
        self.configs.clear()
        self.iob_en_bytes.clear()
        self.config_total_size = 0
        self.config_ptrs.clear()
        self.config_id_current = -1
        self.running = False

        self.arrival_time = 0.0
        self.start_time = 0.0
        self.exes_time = 0.0
        self.exef_time = 0.0
        self.valid = False
        return

    def generate_en_bytes(self, device: DeviceInfo):
        self.iob_en_bytes.clear()
        offset_iob = self.offset_starting_tile * device.tile_iob_bank_num
        total_l_iob = device.reg_exe_iob_ens_reglength

        self.tile_en_bytes.clear()
        offset_tile = self.offset_starting_tile
        total_l_tile = device.reg_cfg_en_tile_reglength

        for cfg in self.configs:

            y = 0
            yy1 = 0
            for x in cfg.iob_en:
                y = y + (x << yy1)
                yy1 += 8
            y <<= offset_iob
            l_iob_bytes = (offset_iob + 7) // 8 + len(cfg.iob_en)
            self.iob_en_bytes.append(
                y.to_bytes(l_iob_bytes, "little") + bytes(total_l_iob - l_iob_bytes)
            )

            y = 0
            yy1 = 0
            for x in cfg.tile_en:
                y = y + (x << yy1)
                yy1 += 8
            y <<= offset_tile
            l_tile_bytes = (offset_tile + 7) // 8 + len(cfg.tile_en)
            self.tile_en_bytes.append(
                y.to_bytes(l_tile_bytes, "little") + bytes(total_l_tile - l_tile_bytes)
            )
        # print(
        #     f"iob_en from {cfg.iob_en} to {self.iob_en_bytes[-1].hex()}, with offset {self.offset_starting_tile}"
        # )
        # print(
        #     f"tile_en from {cfg.tile_en} to {self.tile_en_bytes[-1].hex()}, with offset {self.offset_starting_tile}"
        # )

    def __repr__(self):
        nodef_f_vals = (
            (f.name, attrgetter(f.name)(self))
            for f in dataclasses.fields(self)
            if f.name
            not in ["configs", "config_id_current", "running", "exes_time", "exef_time"]
        )

        nodef_f_repr = ", ".join(f"{name}={value}" for name, value in nodef_f_vals)
        return f"{self.__class__.__name__}({nodef_f_repr})"


# TODO
class DeviceEvent:
    def __init__(self):
        # self._event = asyncio.Event()
        self._event = cocotb.triggers.Event()

    def set(self):
        """Record the event on a stream"""
        self._event.set()

    async def wait(self):
        """Wait for the event to complete"""
        await self._event.wait()

    def is_set(self) -> bool:
        """Check if event has occurred"""
        return self._event.is_set()

    def clear(self):
        """Clear the event state"""
        self._event.clear()


@dataclass
class StreamScheduler_DeviceState:
    busy: bool
    event: DeviceEvent
    func: Callable


@dataclass
class DeviceStreamReorderQueue:
    # 根据memcpy任务的依赖重排序

    def __init__(
        self,
        runtime: "DeviceRuntime",
        handler: "ResourceMappingHandler",
        maxsize: int = 30,
    ):
        self.runtime = runtime
        self.handler = handler
        self.maxsize = maxsize
        self.count = 0
        # store CFG
        self._CFG_queue: List[int] = []
        self._H2D_queue: List[List] = [[], [], []]
        self._D2H_queue: List[List] = [[], []]
        # stroe D2H event with depend_type=1, legacy tasks
        self._rest_D2H: List[DeviceEvent] = []
        self._rest_count = 0
        self._in_processing_event = DeviceEvent()
        self._in_processing_event.set()

    async def _clear_rest(self):
        if self._rest_count > 0:
            for event in self._rest_D2H:
                await event.wait()
            self._rest_D2H.clear()
            self._rest_count = 0

    # 使用clear以保证所有任务结束
    async def clear(self):
        await self._in_processing_event.wait()
        if self.count > 0:
            await self.process(exe2_flag=False)
        await self._clear_rest()

    # 添加任务CFG,MEM,EXE.S
    # EXE.S或任务总会触发执行
    async def add_task(self, sf: StreamFunction, param: Any):
        self.count += 1
        if sf == StreamFunction.CONFIG:
            self._CFG_queue.append(param)
        elif sf == StreamFunction.MEMCPY_HOSTTODEVICE:
            task, depend_type = param[:-1], param[-1]
            if depend_type not in [0, 1, 2]:
                raise ValueError(f"wrong H2D depend type, with {depend_type}")
            self._H2D_queue[depend_type].append(task)
        elif sf == StreamFunction.MEMCPY_DEVICETOHOST:
            task, depend_type = param[:-1], param[-1]
            if depend_type not in [0, 1]:
                raise ValueError(f"wrong D2H depend type, with {depend_type}")
            self._D2H_queue[depend_type].append(task)

        if sf == StreamFunction.EXECUTION_START:
            await self.process(exe2_flag=True)
        elif self.count > self.maxsize:
            await self.process(exe2_flag=False)

    # 执行过程，按照依赖提交MEM任务
    async def process(self, exe2_flag: bool = False):
        self._in_processing_event.clear()
        await self._clear_rest()

        H2D_events = []
        D2H_events = []

        for task in self._H2D_queue[2]:
            event = await self.runtime.add_write_task(self.handler, *task)
            H2D_events.append(event)

        # 自动插入EXE.F任务
        if self.handler.running:
            await self.runtime.finish_execution(self.handler)

        for task in self._H2D_queue[1]:
            event = await self.runtime.add_write_task(self.handler, *task)
            H2D_events.append(event)
        for task in self._D2H_queue[0]:
            event = await self.runtime.add_read_task(self.handler, *task)
            D2H_events.append(event)
        for task in self._D2H_queue[1]:
            event = await self.runtime.add_read_task(self.handler, *task)
            self._rest_D2H.append(event)
        self._rest_count = len(self._rest_D2H)
        for task in self._CFG_queue:
            await self.runtime.enable_config(self.handler, task)

        for event in D2H_events:
            await event.wait()
        for task in self._H2D_queue[0]:
            event = await self.runtime.add_write_task(self.handler, *task)
            H2D_events.append(event)

        for event in H2D_events:
            await event.wait()
        if exe2_flag:
            await self.runtime.start_execution(self.handler)

        self._CFG_queue.clear()
        self._H2D_queue[0].clear()
        self._H2D_queue[1].clear()
        self._H2D_queue[2].clear()
        self._D2H_queue[0].clear()
        self._D2H_queue[1].clear()
        self.count = 0
        self._in_processing_event.set()


class DeviceStream:
    # 当不输入I/O depend_type(默认为0)时，即强制按任务提交顺序完成
    # execution_finish已删除，会自动在EXE与D2H/下个EXE之间插入
    # 由EXE.S或MEM.FENCE区分的连续的I/O任务，不与其余段交织
    def __init__(
        self,
        runtime: "DeviceRuntime",
        stream_id: int,
        priority: int = 1,
        task_queue_size: int = 100,
        task_reorder_queue_size: int = 30,
    ):
        self.runtime = runtime
        self.id = stream_id
        self.priority = priority
        # self._queue = asyncio.Queue(maxsize=task_queue_size)
        # self._queue = cocotb.queue.Queue(maxsize=task_queue_size)
        self._queue = cocotb.queue.Queue()
        self._running = False
        self._current_task = None
        self._handler: ResourceMappingHandler = ResourceMappingHandler(stream_id)
        # 用于同步完成状态
        self._completion_event = DeviceEvent()
        # 用于自动分析依赖，交换memcpy顺序，重叠执行以提高性能
        self._reorder_queue = DeviceStreamReorderQueue(
            runtime=self.runtime,
            handler=self._handler,
            maxsize=task_reorder_queue_size,
        )

    async def apply(self, configs: List[DeviceConfig]):
        """Apply enough resource for bunch of configs, each time only one config can be running"""
        configs_new = copy.deepcopy(configs)
        await self._queue.put((StreamFunction.APPLY, configs_new))
        self._start_processing()

    async def config(self, config_id: int = 0):
        """Switch a configuration on device, ignore if it is the same as the previous time"""
        await self._queue.put((StreamFunction.CONFIG, config_id))
        self._start_processing()

    async def memcpyHostToDevice(
        self,
        d_data: DeviceData,
        h_data: Union[bytearray, bytes, List, numpy.ndarray],
        size: Optional[int] = None,
        dtype: Optional[str] = None,
        depend_type: int = 0,
    ):
        """
        Add a memcpyHostToDevice task to the stream, dtype same as struct

        Args:
            d_data: Device spm ptr.
            h_data: Host-side data.
            size: None -> all the h_data
            Bytes or the length of assigned dtype
            depend_type: 0,1,2
            0 按原来次序
            1 可以提前至上一次任务结束后,D2H前
            2 可以提前至上一次任务执行

        Note:
            Only when dtype!=None, h_data can be a list
        """
        if not (
            isinstance(h_data, bytearray)
            or isinstance(h_data, bytes)
            or (isinstance(h_data, list) and dtype is not None)
            or isinstance(h_data, numpy.ndarray)
        ):
            raise TypeError(
                f"stream{self.id} memcpyHostToDevice h_data type wrong, with type {type(h_data)}"
            )

        if depend_type not in [0, 1, 2]:
            depend_type = 0
        await self._queue.put(
            (
                StreamFunction.MEMCPY_HOSTTODEVICE,
                (d_data, h_data, size, dtype, depend_type),
            )
        )
        self._start_processing()

    async def memcpyDeviceToHost(
        self,
        d_data: DeviceData,
        h_data: Union[bytearray, List, numpy.ndarray],
        size: int,
        dtype: Optional[str] = None,
        depend_type: int = 0,
    ):
        """
        Add a memcpyHostToDevice task to the stream

        Args:
            d_data: Device spm ptr.
            h_data: Host-side buffer.
            size: Bytes or the length of assigned dtype
            depend_type: 0,1
            0 按照原来顺序
            1 可以与后一次执行重叠

        Note:
            Only when dtype!=None, h_data can be a list
            replace numpy.ndarry or use extend to change h_data
        """
        # @jhlou
        if not (
            isinstance(h_data, bytearray)
            or (isinstance(h_data, list) and dtype is not None)
            or isinstance(h_data, numpy.ndarray)
        ):
            raise TypeError(
                f"stream{self.id} memcpyDeviceToHost h_data type wrong, with type {type(h_data)}"
            )

        if depend_type not in [0, 1]:
            depend_type = 0
        await self._queue.put(
            (
                StreamFunction.MEMCPY_DEVICETOHOST,
                (d_data, h_data, size, dtype, depend_type),
            )
        )

        self._start_processing()

    async def execution_start(self):
        """Add an execution start task to the stream"""
        await self._queue.put((StreamFunction.EXECUTION_START, None))
        self._start_processing()

    async def memcpyFence(self):
        """Wait for execution to finish"""
        await self._queue.put((StreamFunction.MEMCPY_FENCE, None))
        self._start_processing()

    async def release(self):
        """Release apply the applied resources, invalidate the handler"""
        await self._queue.put((StreamFunction.RELEASE, None))
        self._start_processing()

    async def wait_event(self, event: DeviceEvent):
        """Wait for an event before proceeding"""
        await self._queue.put((StreamFunction.EVENT_WAIT, event))
        self._start_processing()

    async def set_event(self, event: DeviceEvent):
        """Set an event at this point in the stream"""
        await self._queue.put((StreamFunction.EVENT_SET, event))
        self._start_processing()

    def _start_processing(self):
        """Start processing the queue if not already running"""
        if not self._running and self._current_task is None:
            # self._current_task = self.runtime.loop.create_task(self._process_queue())
            self._current_task = cocotb.start_soon(self._process_queue())
            self._completion_event.clear()  # 重置完成事件

    async def synchronize(self):
        """Wait for all tasks in the stream to complete"""
        # await self._queue.join()

        if self._current_task is not None:
            await self._completion_event.wait()
        # print("task len", self._queue.qsize())
        # 可能有新任务加入队列
        self._start_processing()
        if self._current_task is not None:
            await self._completion_event.wait()

    async def _process_queue(self):
        """Process tasks in the queue"""
        self._running = True
        try:
            while not self._queue.empty():
                try:
                    # 添加超时防止永久阻塞
                    task_type, task_data = await cocotb.triggers.with_timeout(
                        self._queue.get(), timeout_time=10, timeout_unit="ns"
                    )
                except TimeoutError:
                    # 队列空且超时则退出
                    break

                if task_type == StreamFunction.APPLY:
                    # avoid resources leaks
                    await self._reorder_queue.clear()
                    if self._handler.valid:
                        await self.runtime.release_config(self._handler)

                    await self.runtime.apply_resource(self._handler, task_data)

                elif task_type == StreamFunction.RELEASE:
                    # release applied resource
                    await self._reorder_queue.clear()
                    await self.runtime.release_config(self._handler)
                elif task_type == StreamFunction.EVENT_WAIT:
                    await self._reorder_queue.clear()
                    await task_data.wait()
                elif task_type == StreamFunction.EVENT_SET:
                    await self._reorder_queue.clear()
                    task_data.set()
                elif task_type == StreamFunction.MEMCPY_FENCE:
                    await self._reorder_queue.clear()
                    if self._handler.running:
                        await self.runtime.finish_execution(self._handler)
                # 以下注释部分已全由self._reorder_queue内部实现
                elif task_type == StreamFunction.CONFIG:
                    await self._reorder_queue.add_task(task_type, task_data)
                    # await self.runtime.enable_config(self._handler, task_data)
                elif task_type == StreamFunction.MEMCPY_HOSTTODEVICE:
                    await self._reorder_queue.add_task(task_type, task_data)
                    # event = await self.runtime.add_write_task(
                    #     self._handler, *task_data[:-1]
                    # )
                    # await event.wait()
                elif task_type == StreamFunction.MEMCPY_DEVICETOHOST:
                    await self._reorder_queue.add_task(task_type, task_data)
                    # event = await self.runtime.add_read_task(
                    #     self._handler, *task_data[:-1]
                    # )
                    # await event.wait()
                elif task_type == StreamFunction.EXECUTION_START:
                    await self._reorder_queue.add_task(task_type, task_data)
                    # await self.runtime.start_execution(self._handler)

                # self._queue.task_done()
        finally:
            await self._reorder_queue.clear()
            self._running = False
            self._completion_event.set()  # 标记处理完成
            self._current_task = None


class DeviceManager:
    # 设备资源管理，free_list
    def __init__(self, device: DeviceInfo, id: int, option: str = "First-Fit"):
        self.device = device
        self.device_id = id
        self.tile_num_idle = device.tile_num
        self.log = logging.getLogger(f"DeviceManager of device{id}")
        self.log.setLevel(logging.DEBUG)
        # 实际空间可能会小于这个数，因为要对齐
        self.cfg_spm_idle = device.config_end_address - device.config_start_address
        self.lock = cocotb.triggers.Lock()
        self.algorithm = option
        if self.algorithm != "First-Fit":
            raise ValueError(
                f"DeviceManager wrong alg {self.algorithm}, please use (First-Fit,Best-Fit)"
            )

        # 空闲空间链表，首地址递增
        self.tile_free_list: List[DeviceData] = [DeviceData(0, self.tile_num_idle)]
        self.cfg_free_list: List[DeviceData] = [DeviceData(0, self.cfg_spm_idle)]
        # self.tile_free_list: List[DeviceData] = [DeviceData(1, self.tile_num_idle - 1)]
        # self.cfg_free_list: List[DeviceData] = [DeviceData(80, self.cfg_spm_idle - 80)]

    def fit_first_one(self, size: int, free_location: List[DeviceData]) -> int:

        for i, ptr in enumerate(free_location):
            if ptr.size >= size:
                return i

        return -1

    def fit_best_one(self, size: int, free_location: List[DeviceData]) -> int:

        i = self.fit_first_one(size, free_location)
        if i == -1:
            return -1

        best_pos = i
        best_size = free_location[i].size
        l = len(free_location)

        for i in range(i, l):
            ptr = free_location[i]
            if size <= ptr.size < best_size:
                best_pos = i
                best_size = ptr.size

        return best_pos

    def upper_alignment(self, x: int) -> int:
        byte_width = self.device.cfg_spad_data_bytewidth
        l1 = x % byte_width
        if l1 > 0:
            x += byte_width - l1
        return x

    # 1成功分配，0失败
    def fit_configs(self, handler: ResourceMappingHandler) -> bool:
        """Allocate resources according to task requirements"""

        def reduce_free_list(target: List[DeviceData], index: int, size: int):
            if size == target[index].size:
                del target[index]
            else:
                # @jhlou 20250904: the access address should align with bus width.
                target[index].size -= size
                target[index].address += size
                # end @jhlou
            return

        handler.total_tiles = 1 + (
            handler.max_pe_usage_addr // self.device.tile_pe_address
        )
        self.log.debug(
            f"try to alloc {handler.total_tiles} tiles on device {self.device_id}"
        )
        self.log.debug(
            f"device {self.device_id}: tile free list {self.tile_num_idle} {self.tile_free_list}"
        )
        self.log.debug(
            f"device {self.device_id}:  cfg free list {self.cfg_spm_idle} {self.cfg_free_list}"
        )
        if handler.total_tiles == self.device.tile_num + 1:
            handler.total_tiles -= 1
            self.log.debug(f"this cfg includes the additional gibs")
        if (
            handler.total_tiles > self.tile_num_idle
            or handler.config_total_size > self.cfg_spm_idle
        ):
            return False

        if self.algorithm == "First-Fit":
            alg_fit = self.fit_first_one
        elif self.algorithm == "Best-Fit":
            alg_fit = self.fit_first_one
        else:
            alg_fit = self.fit_first_one

        # pe resource
        i1 = alg_fit(size=handler.total_tiles, free_location=self.tile_free_list)
        if i1 == -1:
            return False

        # config spm resource
        cfg_ptrs = handler.config_ptrs.copy()  # 浅拷贝，修改同步，此时只有size保持不变
        cfg_ptrs.sort(key=lambda x: x.size, reverse=True)  # 降序排序
        # 因为需要一次性全部映射,先暂存
        tmp_cfg_free_list = copy.deepcopy(self.cfg_free_list)
        size_total = 0
        for ptr in cfg_ptrs:
            size1 = self.upper_alignment(ptr.size)  # 对齐
            size_total += size1
            i2 = alg_fit(size=size1, free_location=tmp_cfg_free_list)
            if i2 == -1:
                return False
            ptr.address = tmp_cfg_free_list[i2].address
            reduce_free_list(tmp_cfg_free_list, i2, size1)

        pe_ptr = DeviceData(self.tile_free_list[i1].address, handler.total_tiles)
        reduce_free_list(self.tile_free_list, i1, handler.total_tiles)
        self.cfg_free_list = tmp_cfg_free_list

        self.tile_num_idle -= pe_ptr.size
        self.cfg_spm_idle -= size_total
        handler.offset_starting_tile = pe_ptr.address
        handler.offset_pe_address = pe_ptr.address * self.device.tile_pe_address
        handler.offset_spm_address = pe_ptr.address * self.device.tile_spm_address
        handler.device_id = self.device_id

        return True

        """Allocation failed"""
        return False

    def release_config(self, handler: ResourceMappingHandler):
        """Release allocated resources"""

        def merge_free_list(target: List[DeviceData]):
            target.sort(key=lambda x: x.address)
            l = 1
            while l < len(target):
                if target[l - 1].end() == target[l].address:
                    target[l - 1].size += target[l].size
                    del target[l]
                else:
                    l += 1
            return

        if not handler.valid:
            return
        pe_ptr = DeviceData(handler.offset_starting_tile, handler.total_tiles)
        self.tile_free_list.append(pe_ptr)
        for ptr in handler.config_ptrs:
            size1 = self.upper_alignment(ptr.size)  # 对齐
            self.cfg_free_list.append(DeviceData(ptr.address, size1))

        merge_free_list(self.tile_free_list)
        merge_free_list(self.cfg_free_list)
        self.cfg_spm_idle = 0
        self.tile_num_idle = 0
        for i in self.tile_free_list:
            self.tile_num_idle += i.size
        for i in self.cfg_free_list:
            self.cfg_spm_idle += i.size


class StreamScheduler:
    # 目前是多个优先级队列+FIFO
    def __init__(self, queue_num: int = 1):
        # 使用普通list，通过device_state等管理
        self._task_queue: List[List[Tuple[Any, DeviceEvent]]] = [
            [] for i in range(queue_num)
        ]
        self.log = logging.getLogger("StreamScheduler")
        self.log.setLevel(logging.DEBUG)
        self._total_task = 0
        self._running_tasks = 0
        self._new_task_event = DeviceEvent()
        self._current_prior = 0
        self._device_state: Dict[int, StreamScheduler_DeviceState] = {}
        self._all_device_busy = False
        self._any_device_idle = DeviceEvent()

        cocotb.start_soon(self._process())

    async def put(self, priority: int, task_param: Any) -> DeviceEvent:
        event = DeviceEvent()
        self._task_queue[priority].append((task_param, event))
        self._total_task += 1
        self._current_prior = max(self._current_prior, priority)
        self._new_task_event.set()  # 通知有新任务
        self._new_task_event.clear()  # 立即清除以便下次使用
        self.log.debug(f"new task {self._total_task}")
        return event

    # 逐个处理任务，阻塞，以后优化
    async def _process(self):
        count_fail = 0
        while True:
            # 等待有新任务或着查看更低优先级队列的任务
            if len(self._task_queue[self._current_prior]) == 0:
                if self._current_prior == 0:
                    await self._new_task_event.wait()
                    self._new_task_event.clear()
                else:
                    self._current_prior -= 1
                continue

            if self._all_device_busy:
                await self._any_device_idle.wait()
                self._all_device_busy = False
                self._any_device_idle.clear()

            task_param, task_event = self._task_queue[self._current_prior][0]

            flag = False
            for id, state in self._device_state.items():
                if state.func(*task_param):
                    task_event.set()
                    flag = True
                    break

            if flag:
                self._task_queue[self._current_prior].pop(0)
                count_fail = 0
            else:
                self._task_queue[self._current_prior].append((task_param, task_event))
                count_fail += 1
                await cocotb.triggers.Timer(10, units="ns")
                if count_fail > 5:
                    self._any_device_idle.clear()
                    self._all_device_busy = True

    # 添加设备
    def add_device(self, device_id: int, device_fit_config: Callable):
        self._device_state[device_id] = StreamScheduler_DeviceState(
            busy=False,
            event=DeviceEvent(),
            func=device_fit_config,
        )

    def device_state_update(self, device_id: int):
        self._device_state[device_id].event.set()
        self._any_device_idle.set()


class AsyncTaskQueue:
    # 用于缓冲I/O工作队列
    def __init__(
        self,
        func: Callable,
        task_queue_size: int = 20,
    ):
        self._func = func
        self._queue = cocotb.queue.Queue(maxsize=task_queue_size)
        self._running = False
        self._current_task = None
        self._completion_event = DeviceEvent()

    def size(self) -> int:
        return self._queue.qsize()

    async def add_task(self, param: Tuple[Any]) -> DeviceEvent:
        """Add task to queue and return a event"""
        event = DeviceEvent()
        await self._queue.put((param, event))
        self._start_processing()
        return event

    async def wait_all(self):
        """Wait for all tasks in the queue to complete"""
        if self._current_task is not None:
            await self._completion_event.wait()

    def _start_processing(self):
        """Start processing the queue if not already running"""
        if not self._running and self._current_task is None:
            self._current_task = cocotb.start_soon(self._process_queue())
            self._completion_event.clear()

    async def _process_queue(self):
        """Process tasks in the queue"""
        self._running = True
        try:
            while not self._queue.empty():
                param, event = await self._queue.get()
                await self._func(*param)
                event.set()
        finally:
            self._running = False
            self._current_task = None
            self._completion_event.set()


@dataclass
class DeviceExeRegInfo:
    exe_reg: bytes = b''
    resp_time: float = 0.0
    need_count: int = int(0)


class DeviceRuntime:

    def __init__(
        self,
        dut,
        axi,
        axil,
        axi_size: int,
        memcpy_queue_size: int = 20,
        stream_scheduler_queue_num: int = 3,
    ):
        self.dut = dut
        self.axi = axi
        self.axil = axil
        self.axi_size = axi_size
        self._axil_wlock = cocotb.triggers.Lock()
        self._axil_wait_event = DeviceEvent()
        self._axil_wait_event.set()

        self.log = logging.getLogger("test_runif")
        self.log.setLevel(logging.DEBUG)

        self._stream_ids: int = 0
        self._streams: Dict[int, DeviceStream] = {}

        self._device_managers: List[DeviceManager] = []
        self._device_exereg: List[DeviceExeRegInfo] = []
        self._device_fetch_exereg_interval: float = 10.0
        cocotb.start_soon(self._read_device_status())

        # 优先级越大越重要
        self._stream_scheduler_queue_num = stream_scheduler_queue_num
        self._stream_scheduler = StreamScheduler(queue_num=stream_scheduler_queue_num)

        self._memcpy_H2D_queue = AsyncTaskQueue(
            func=self._write_data, task_queue_size=memcpy_queue_size
        )
        self._memcpy_D2H_queue = AsyncTaskQueue(
            func=self._read_data, task_queue_size=memcpy_queue_size
        )

    def is_device_busy(self) -> bool:
        return self._streams.__len__() > 0

    async def destory_stream(self, stream: DeviceStream):
        stream_id = stream.id
        if stream_id in self._streams:
            await self._streams[stream_id].synchronize()
            await self.release_config(self._streams[stream_id]._handler)
            del self._streams[stream_id]
        del stream

    def create_stream(
        self,
        priority: int = 0,  # 优先级越大越重要
        task_queue_size: int = 1000,
        task_reorder_queue_size: int = 100,
    ) -> DeviceStream:
        """Create a new stream for concurrent operations"""

        # 避免无效优先级
        priority = int(priority)
        if priority < 0 or priority >= self._stream_scheduler_queue_num:
            priority = 0

        stream = DeviceStream(
            runtime=self,
            stream_id=self._stream_ids,
            priority=priority,
            task_queue_size=task_queue_size,
            task_reorder_queue_size=task_reorder_queue_size,
        )
        self._streams[self._stream_ids] = stream
        self._stream_ids += 1
        return stream

    def create_event(self) -> DeviceEvent:
        """Create a new synchronization event"""
        return DeviceEvent()

    def add_device(self, device: DeviceInfo) -> int:
        """Register a new device"""
        id = len(self._device_managers)
        self._device_managers.append(DeviceManager(device=device, id=id))
        self._stream_scheduler.add_device(
            device_id=id,
            device_fit_config=self._device_managers[-1].fit_configs,
        )

        self._device_exereg.append(DeviceExeRegInfo())

        self.log.debug(f"register device id {id}, {device}")
        return id

    async def _axi_write(self, address: int, data_bytes: Union[bytearray, bytes]):
        """Write data to device memory"""

        # await self.axi.write(address, data_bytes, size=self.axi_size, awid=0)
        await self.axi.write(address, data_bytes, size=self.axi_size)

        return

    async def _axi_read(self, address: int, total_bytes: int) -> bytes:
        """Read data from device memory"""

        # dbytes = await self.axi.read(address, total_bytes, size=self.axi_size, arid=0)
        dbytes = await self.axi.read(address, total_bytes, size=self.axi_size)

        return dbytes.data

    async def apply_resource(
        self, handler: ResourceMappingHandler, configs: List[DeviceConfig]
    ):
        """find an idle device, and write configs to the device"""
        # for config in configs:
        #     if len(config.data_ptr) > 0:
        #         config.data_ptr.sort(key=lambda x: x.address)

        # 一些预处理，对handler初始化
        handler.configs = configs
        handler.config_num = len(configs)

        # TODO: 此处对config预处理与device 耦合，待修改
        handler.max_pe_usage_addr = max(
            [max(cfg.config_values[2::3]) for cfg in configs]
        )
        handler.config_total_size = 0
        handler.config_ptrs.clear()
        for x in configs:
            size = len(x.config_values) * 2  # 每个16bit
            handler.config_ptrs.append(DeviceData(address=0, size=size))
            handler.config_total_size += size
        handler.arrival_time = cocotb.utils.get_sim_time(units="ns")
        stream1 = self._streams[handler.stream_id]

        # self.log.debug(f"APPLY task begin, handler {handler}")
        event1 = await self._stream_scheduler.put(
            priority=stream1.priority,
            task_param=(handler,),
        )
        await event1.wait()

        """Allocation successful"""
        device = self._device_managers[handler.device_id].device
        handler.start_time = cocotb.utils.get_sim_time(units="ns")
        handler.valid = True
        handler.generate_en_bytes(device)

        self.log.debug(f"APPLY task finish, handler {handler}")
        self.log.debug(
            f"device {handler.device_id}: tile free list {self._device_managers[handler.device_id].tile_free_list}"
        )
        self.log.debug(
            f"device {handler.device_id}:  cfg free list {self._device_managers[handler.device_id].cfg_free_list}"
        )

        # 把所有cfg地址增加偏移量后写入
        for config, ptr in zip(handler.configs, handler.config_ptrs):
            cfg_bytes = device.ConvertConfigToByteArray(
                config.config_values, handler.offset_pe_address
            )
            event2 = await self._memcpy_H2D_queue.add_task(
                (handler, ptr.address + device.config_start_address, cfg_bytes)
            )
            await event2.wait()
            # print("write cfg", ptr.address + device.config_start_address)
        return

    async def set_event_after(self, event: DeviceEvent, delay: float):
        """Set the event after delay ns"""
        await cocotb.triggers.Timer(delay, units="ns")
        event.set()

    # TODO
    async def enable_config(self, handler: ResourceMappingHandler, id: int):
        """Switch a configuration on the device"""
        # 可能cfg需要重新刷写，不能直接退出
        # if handler.config_id_current == id:
        #     return

        if id > handler.config_num or id < 0:
            self.log.debug(f"CFG task error, handler: {handler}")
            raise ValueError(
                f"config id ({id}) is out of range, with total config num {handler.config_num}"
            )

        self.log.debug(
            f"CFG task, stream {handler.stream_id}, cfg id {id}, cfg addr {handler.config_ptrs[id]}"
        )

        handler.config_id_current = id

        config_ptr = handler.config_ptrs[id]
        device = self._device_managers[handler.device_id].device
        base_addr = config_ptr.address
        cfg_num = config_ptr.size // 6  # 每个16bit,3个16bit组成1行
        en_tile = (1 << handler.total_tiles) - 1
        en_tile = en_tile << handler.offset_starting_tile
        # Set configuration registers
        async with self._axil_wlock:
            await self._axil_wait_event.wait()
            self._axil_wait_event.clear()

            # reg_cfg_base_addr_0
            event1 = self.axil.init_write(
                device.reg_cfg_base_addr_0,
                base_addr.to_bytes(device.reg_cfg_num_reglength, "little"),
            )

            # reg_cfg_num_0
            event2 = self.axil.init_write(
                device.reg_cfg_num_0,
                cfg_num.to_bytes(device.reg_cfg_num_reglength, "little"),
            )

            # reg_cfg_en_tile_0
            event3 = self.axil.init_write(
                device.reg_cfg_en_tile_0,
                en_tile.to_bytes(device.reg_cfg_en_tile_reglength, "little"),
            )

            await event1.wait()
            await event2.wait()
            await event3.wait()

            # reg_cfg_en
            await self.axil.write(
                device.reg_cfg_en,
                int(0x01).to_bytes(device.reg_bit_width // 8, "little"),
            )

            cocotb.start_soon(
                self.set_event_after(self._axil_wait_event, config_ptr.size // 3)
            )

        return

    async def _write_data(
        self,
        handler: ResourceMappingHandler,
        address: int,
        h_bytes: Union[bytearray, bytes],
    ):
        """Load data(bytes) from host to device"""

        await self._axi_write(address=address, data_bytes=h_bytes)

        return

    async def _read_data(
        self,
        handler: ResourceMappingHandler,
        d_data: DeviceData,
        h_data: Union[bytearray, List, numpy.ndarray],
        size: int,
        dtype: Optional[str] = None,
    ):
        """Load data(bytes) from device to host"""

        if dtype is not None:
            fmt_size = struct.calcsize(dtype)
        else:
            fmt_size = 1

        total_bytes = size * fmt_size

        if isinstance(h_data, numpy.ndarray) and total_bytes != h_data.nbytes:
            raise ValueError(
                f"Byte length mismatch: {len(h_bytes)} vs ndarray {h_data.nbytes}"
            )

        if total_bytes > d_data.size:
            raise ValueError(
                f"stream{handler.stream_id} read data size overflow, with{total_bytes} > {d_data.size}"
            )

        h_bytes = await self._axi_read(
            address=d_data.address + handler.offset_spm_address, total_bytes=total_bytes
        )

        # print(f"axi reader expbytes {total_bytes} data {h_bytes.hex()}")

        # @jhlou
        if isinstance(h_data, numpy.ndarray):
            # convert bytes into array of correct dtype + shape
            src = numpy.frombuffer(h_bytes, dtype=h_data.dtype).reshape(h_data.shape)

            if h_data.flags["C_CONTIGUOUS"] or h_data.flags["F_CONTIGUOUS"]:
                # Fast path: memory is contiguous
                numpy.copyto(h_data, src)
            else:
                # Slow path: non-contiguous view → assign element-wise
                h_data[...] = src

        elif isinstance(h_data, list):
            h_data.extend(struct.unpack(str(size) + dtype, h_bytes))
        elif isinstance(h_data, bytearray):
            h_data.extend(h_bytes)
        else:
            raise TypeError(f"Unsupported h_data type: {type(h_data)}")
        # end @jhlou

    async def add_write_task(
        self,
        handler: ResourceMappingHandler,
        d_data: DeviceData,
        h_data: Union[bytearray, bytes, List, numpy.ndarray],
        size: Optional[int] = None,
        dtype: Optional[str] = None,
    ) -> DeviceEvent:
        # 执行数据检查及转换，添加H2D任务到IO队列，返回event

        if type(h_data) == numpy.ndarray:
            h_bytes = h_data.tobytes()
        elif type(h_data) == list and dtype != None:
            if size is None:
                size = len(h_data)
                h_bytes = struct.pack(str(size) + dtype, *h_data)
            else:
                h_bytes = struct.pack(str(size) + dtype, *h_data[:size])
        elif type(h_data) == bytes or type(h_data) == bytearray:
            if size is None:
                h_bytes = h_data
            else:
                h_bytes = h_data[:size]
        else:
            raise TypeError(
                f"stream{handler.stream_id} write h_data type wrong, with type {type(h_data)}"
            )

        size1 = h_bytes.__len__()
        if size1 > d_data.size:
            raise ValueError(
                f"stream{handler.stream_id} write h_data size overflow, with {size1} > {d_data.size} {d_data}"
            )

        event = await self._memcpy_H2D_queue.add_task(
            (handler, d_data.address + handler.offset_spm_address, h_bytes)
        )

        return event

    async def add_read_task(
        self,
        handler: ResourceMappingHandler,
        d_data: DeviceData,
        h_data: Union[bytearray, List, numpy.ndarray],
        size: int,
        dtype: Optional[str] = None,
    ) -> DeviceEvent:
        # 添加D2H任务到IO队列，返回event
        event = await self._memcpy_D2H_queue.add_task(
            (handler, d_data, h_data, size, dtype)
        )
        return event

    # TODO
    async def start_execution(self, handler: ResourceMappingHandler):
        """Start execution (enable the iobs)"""

        handler.running = True
        # Set iob registers
        device = self._device_managers[handler.device_id].device

        async with self._axil_wlock:
            await self._axil_wait_event.wait()
            self._axil_wait_event.clear()

            # reg_exe_iob_ens_0
            event1 = self.axil.init_write(
                device.reg_exe_iob_ens_0,
                handler.iob_en_bytes[handler.config_id_current],
            )

            # reg_exe_tile_ens_0
            event2 = self.axil.init_write(
                device.reg_exe_tile_ens_0,
                handler.tile_en_bytes[handler.config_id_current],
            )

            await event1.wait()
            await event2.wait()

            # reg_exe_start
            await self.axil.write_byte(device.reg_exe_start, 0x01)

            cocotb.start_soon(self.set_event_after(self._axil_wait_event, 10))

        handler.exes_time = cocotb.utils.get_sim_time(units="ns")
        self.log.debug(f"EXE.S task, stream {handler.stream_id}")

        return

    async def _read_device_status(self):
        """Loop to read exe reg if needed"""
        while True:
            for device_id, reg in enumerate(self._device_exereg):
                self.log.info(
                    f"Device {device_id} status with active stream num {reg.need_count}"
                )
                if reg.need_count > 0:
                    reg_exe_done_0 = self._device_managers[
                        device_id
                    ].device.reg_exe_done_0
                    reg_len = self._device_managers[
                        device_id
                    ].device.reg_cfg_en_tile_reglength
                    resp = await self.axil.read(reg_exe_done_0, reg_len)
                    reg.exe_reg = resp.data
                    reg.resp_time = cocotb.utils.get_sim_time(units="ns")

            await cocotb.triggers.Timer(self._device_fetch_exereg_interval, units="ns")

    # TODO
    async def finish_execution(self, handler: ResourceMappingHandler):
        """Wait until execution finished"""

        def byte_include(a: bytes, b: bytes):
            for i, x in enumerate(b):
                if a[i] & x != x:
                    return False
            return True

        reg_len = self._device_managers[
            handler.device_id
        ].device.reg_cfg_en_tile_reglength

        # wait until exe is done
        en_tile = (1 << handler.total_tiles) - 1
        en_tile = en_tile << handler.offset_starting_tile
        en_tile = en_tile.to_bytes(reg_len, "little")

        cur_time = cocotb.utils.get_sim_time(units="ns")
        reg = self._device_exereg[handler.device_id]
        reg.need_count += 1

        count = 10000
        while count > 0:
            if reg.resp_time > cur_time:
                cur_time = cocotb.utils.get_sim_time(units="ns")
                if byte_include(reg.exe_reg, en_tile):
                    break
                count -= 1
                if count == 0:
                    self.log.debug(f"EXE time out")
                    break
            await cocotb.triggers.Timer(self._device_fetch_exereg_interval, units="ns")

        reg.need_count -= 1

        handler.exef_time = cocotb.utils.get_sim_time(units="ns")
        self.log.debug(
            f"EXE.F task, stream {handler.stream_id}, resp {reg.exe_reg.hex()}, tile {en_tile.hex()}, time {handler.exef_time-handler.exes_time} ns."
        )

        handler.running = False

        return

    async def release_config(self, handler: ResourceMappingHandler):
        """Release allocated resources"""

        if not handler.valid:
            return

        # 在device manager中释放已占用资源
        self._device_managers[handler.device_id].release_config(handler)

        # 通知scheduler有任务释放
        self._stream_scheduler.device_state_update(handler.device_id)

        self.log.debug(
            f"RELEASE task, stream {handler.stream_id}, device {handler.device_id}"
        )
        self.log.debug(
            f"device {handler.device_id}: tile free list {self._device_managers[handler.device_id].tile_free_list}"
        )
        self.log.debug(
            f"device {handler.device_id}:  cfg free list {self._device_managers[handler.device_id].cfg_free_list}"
        )
        handler.clear()
        return

    async def synchronize_all(self):
        """Wait for all streams to complete"""
        for stream in self._streams.values():
            await stream.synchronize()


## @jhlou
class Axi4LiteTb:
    CLOCKPERIOD = 2  ##ns

    def __init__(self, dut):
        """
        Testbench wrapper for a DUT with both AXI4 and AXI-Lite interfaces.

        This class handles:
        - Clock generation
        - AXI4 master interface setup
        - AXI-Lite master interface setup
        - Synchronous reset sequence

        Attributes:
            dut: The DUT handle provided by cocotb.
            log: Logger instance for the testbench.
            axi: AxiMaster instance for AXI4 transactions.
            axil: AxiLiteMaster instance for AXI-Lite transactions.
        """
        from cocotb.clock import Clock
        from cocotbext.axi import AxiBus, AxiMaster, AxiLiteBus, AxiLiteMaster

        self.dut = dut
        self.log = logging.getLogger("cocotb.tb")
        self.log.setLevel(logging.DEBUG)

        cocotb.start_soon(Clock(dut.clk, self.CLOCKPERIOD, units="ns").start())

        self.axi = AxiMaster(AxiBus.from_prefix(dut, "axi"), dut.clk, dut.rst)
        self.axil = AxiLiteMaster(AxiLiteBus.from_prefix(dut, "axil"), dut.clk, dut.rst)

    async def cycle_reset(self):
        from cocotb.triggers import RisingEdge

        self.dut.rst.setimmediatevalue(0)
        await RisingEdge(self.dut.clk)
        await RisingEdge(self.dut.clk)
        self.dut.rst.value = 1
        await RisingEdge(self.dut.clk)
        await RisingEdge(self.dut.clk)
        self.dut.rst.value = 0
        await RisingEdge(self.dut.clk)
        await RisingEdge(self.dut.clk)
