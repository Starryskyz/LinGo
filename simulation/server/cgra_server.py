import CocotbServer, CommandHandler
import test_runif
import os, logging
import cocotb


@cocotb.test()
async def cgra_server_run(dut) -> None:
    """
    Run a CGRA hardware Simulation.

    Args:
        dut: cocotb DUT object (Design Under Test).
    """
    # Reset DUT
    axibus = test_runif.Axi4LiteTb(dut)
    await axibus.cycle_reset()
    axibus.log.info("[CGRA] Reset CGRA")

    # set log level
    # axibus.log.setLevel(logging.WARNING)
    logging.getLogger("cocotb.test_cgra.axi").disabled = True
    logging.getLogger("cocotb.test_cgra.axil").disabled = True
    # logging.getLogger("test_runif").setLevel(logging.DEBUG)
    logging.getLogger("test_runif").setLevel(logging.INFO)

    # 加载硬件信息
    base_dir = os.path.dirname(os.path.abspath(__file__))
    reg_json_path = os.path.join(base_dir, "../circuits/axilite_spec.json")
    adg_json_path = os.path.join(base_dir, "../circuits/vitra_cgra_adg.json")
    device1 = test_runif.create_device_info_factory(
        reg_json_path=reg_json_path, adg_json_path=adg_json_path
    )

    # 加载运行时驱动
    runtime = test_runif.DeviceRuntime(
        dut=dut,
        axi=axibus.axi,
        axil=axibus.axil,
        axi_size=axibus.axi.write_if.max_burst_size,
    )

    runtime.add_device(device1)

    # 加载socket服务器
    server_logger = CocotbServer.getServerDefaultLogger()
    message_queue = CocotbServer.CocotbMessageManager()
    server_thread = CocotbServer.CocotbServerThread(
        message_queue=message_queue, host='127.0.0.1', port=8888, logger=server_logger
    )
    server_thread.start()
    server_logger.info("Server thread started")

    # 加载服务器消息处理器
    command_handler = CommandHandler.CGRACommandHandler(
        message_queue=message_queue,
        runtime=runtime,
        logger=server_logger,
    )

    # 主循环
    await command_handler.start()
