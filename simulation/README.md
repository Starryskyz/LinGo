# Cocotb-CGRA-Simulator

#### author:zevick

## 链接

[https://github.com/orgs/FDU-ME-ARC/repositories](https://github.com/orgs/FDU-ME-ARC/repositories)

[https://github.com/cocotb/cocotb](https://github.com/cocotb/cocotb)


## 环境安装
```bash
conda create -n cocotb python=3.12
conda activate cocotb
pip install "cocotb~=1.9.2"
pip install cocotbext-axi
pip install numpy

# 推荐从源码编译下载 Verilator 5.044
git clone https://github.com/verilator/verilator.git
cd verilator
git checkout v5.044
autoconf
./configure
make -j8
export PATH=xxx/verilator/bin:$PATH
```

## 快速开始

### 指定仿真器

在`Makefile`中自行选择一个仿真器
```
SIM ?= icarus
SIM ?= verilator
```

### 运行IntVecAdd示例（Python）

将`Makefile`中修改为`MODULE = $(DUT)`

```bash
export PYTHONPATH=$(pwd)/server:$PYTHONPATH
export PYTHONPATH=$(pwd)/workspace:$PYTHONPATH
make [-j8]
```

### 运行server与C++ API示例（C++）

将`Makefile`中修改为`MODULE = $(SERVER)`

```bash
export PYTHONPATH=$(pwd)/server:$PYTHONPATH
make
```

已启动server,切换至另一终端

```bash
g++ -o test workspace/test.cpp client/*.cpp -I client
./test
```

关闭`server`，可使用
```bash
# 关闭server端口
fuser -k 8888/tcp

# 或者手动找到后台进程
ps aux | grep cocotb
kill -9 <PID>
```

## 仿真tb编写说明

注意切换硬件时请同步修改circuits目录下的所有硬件描述。

### 基本概念

- 异步编程
- stream流与并发
- AXI协议
- CGRA执行逻辑
  - 传输配置信息，`apply`
  - 加载配置信息，`config`
  - 传输数据，`memcpyH2D`（Host to Device主机到设备）
  - 启动阵列，`execution_start`
  - 等待阵列运算结束，`memcpyFence`，（可以不用，自动判断结束）
  - 取回结果，`memcpyD2H`


### 在Python中仿真

详细讲述了python中的tb编写方式。

直接读代码更快。

1. 获取硬件描述
    ```python
        base_dir = os.path.dirname(os.path.abspath(__file__))
        # 阵列信息
        reg_json_path = os.path.join(base_dir, "../circuits/axilite_spec.json")
        adg_json_path = os.path.join(base_dir, "../circuits/vitra_cgra_adg.json")
        # 创建设备描述符
        device1 = test_runif.create_device_info_factory(
            reg_json_path=reg_json_path, adg_json_path=adg_json_path
        )
    ```

2. 加载运行时
    ```python
        axibus = Axi4LiteTb(dut)
        await axibus.cycle_reset()

        runtime = DeviceRuntime(
            dut=dut,
            axi=axibus.axi,
            axil=axibus.axil,
            axi_size=axibus.axi.write_if.max_burst_size,
        )

        runtime.add_device(device1)
    ```

3. 准备测试数据
    ```python
        cfgbit_IntVecAdd = [0x9000, 0x4000, 0x0008, ...]
        a = np.random.randint(0, 10, size=(20), dtype=np.int16)
        b = np.random.randint(0, 10, size=(20), dtype=np.int16)
        c = np.zeros(shape=(20), dtype=np.int16)

        a_ptr = DeviceData(0x0, 40)
        b_ptr = DeviceData(0x2000, 40)
        c_ptr = DeviceData(0x4000, 40)

        config_IntVecAdd = DeviceConfig(
            config_values=cfgbit_IntVecAdd, iob_en=[0x07], tile_en=[0x01], data_ptr=[a_ptr, b_ptr, c_ptr]
        )
    ```


4. 递交任务
    ```python
        # 注意，await是异步编程必须，执行顺序与任务递交顺序一致，但非阻塞直接返回

        stream = runtime.create_stream()

        # 申请运算所需资源（锁定并独占）
        await stream.apply(config_IntVecAdd)
        await stream.config(config_id=0)
            
        # 传输数据(内部调用AXI)
        await stream.memcpyHostToDevice(d_data=a_ptr, h_data=a, size=len(a))
        await stream.memcpyHostToDevice(d_data=b_ptr, h_data=b, size=len(b))
        
        await stream.execution_start()
    
        await stream.memcpyDeviceToHost(d_data=c_ptr, h_data=c, size=len(c))


        # 在此步后强制同步，拿到仿真结果
        await stream.synchronize()
        
        # 清理资源
        await runtime.destory_stream(stream)

    ```

#### 对于Python的补充

编译器已经支持一键生成`4. 递交任务`中的逻辑，用户只需准备数据及检查返回结果即可。

想了解`runtime`内部的具体工作逻辑可以找`zwzhong`。

### 在C++中仿真

实际操作是使用TCP/IP协议进行了进程间通信（暂时未改用UDP）。

1. 使用`api_stream.h`，则逻辑与python中完全一致。

2. 使用`api_axi.h`，则化简到只有4条命令。
   1. void sendConfig();
   2. void enableArray();
   3. void sendData();
   4. void fetchData();


