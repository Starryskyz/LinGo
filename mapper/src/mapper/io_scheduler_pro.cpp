#include "mapper/io_scheduler.h"

#include <cctype>
#include <iomanip>
#include <sstream>
#include <stdexcept>

namespace {
struct ProTransfer {
    int dfgId;
    int address;
    int size;
    int hostOffset;
    std::string name;
};

std::string sanitizeIdentifier(std::string name)
{
    for(char &c : name){
        if(!std::isalnum(static_cast<unsigned char>(c)) && c != '_') c = '_';
    }
    if(name.empty()) name = "cgra_kernel";
    if(std::isdigit(static_cast<unsigned char>(name.front()))) name = "kernel_" + name;
    return name;
}
}

void IOScheduler::executePro(Mapping *mapping, std::ostream *os_cocotb,
                             std::ostream *os_sdk, std::ostream &os_bits,
                             const std::string &functionName)
{
    ioSchedule(mapping);
    const int banks = _adg->numIobNodes();
    for(int i = 0; i < banks; ++i){
        _older_bank_status[i] = _old_bank_status[i];
        _old_bank_status[i] = _cur_bank_status[i];
    }

    Configuration cfg(mapping);
    for(const auto &elem : _dfg_io_infos){
        cfg.setDfgIoSpadAddr(elem.first, elem.second.iobAddr);
    }
    std::vector<CfgDataPacket> packets;
    cfg.getCfgData(packets);
    cfg.dumpCfgData(os_bits);

    if(_adg->cfgDataWidth() != 32 || _adg->cfgAddrWidth() > 16){
        throw std::runtime_error("AuFORApro emitters require 32-bit configuration data and <=16-bit addresses");
    }
    for(const auto &packet : packets){
        if(packet.data.size() != 1){
            throw std::runtime_error("AuFORApro emitters require one 32-bit word per configuration packet");
        }
    }

    DFG *dfg = mapping->getDFG();
    std::map<int, DFGIONode*> ioNodes;
    std::vector<std::pair<int, int>> loadDeps;
    std::vector<int> storeIds;
    std::set<std::string> multiportLoads;
    std::set<std::string> multiportStores;
    std::map<std::string, int> arrayDeps;

    for(const auto &elem : _dfg_io_infos){
        const int id = elem.first;
        auto *node = dynamic_cast<DFGIONode*>(dfg->node(id));
        ioNodes[id] = node;
        const std::string name = node->memRefName();
        const bool multiport = dfg->isMultiportIoNode(node);
        if(elem.second.isStore){
            if(!multiport || !multiportStores.count(name)){
                storeIds.push_back(id);
                if(multiport) multiportStores.insert(name);
            }
        }else if(!multiport || !multiportLoads.count(name)){
            int sortDep = 0;
            if(elem.second.dep == LD_DEP_ST_LAST_SEC_TASK) sortDep = 1;
            else if(elem.second.dep == LD_DEP_EX_LAST_TASK) sortDep = 2;
            else if(elem.second.dep == LD_DEP_ST_LAST_TASK) sortDep = 3;
            loadDeps.emplace_back(id, sortDep);
            if(multiport) multiportLoads.insert(name);
            arrayDeps[name] = std::max(arrayDeps[name], sortDep);
        }
    }

    std::sort(loadDeps.begin(), loadDeps.end(), [&](const auto &a, const auto &b){
        const std::string an = ioNodes[a.first]->memRefName();
        const std::string bn = ioNodes[b.first]->memRefName();
        return an < bn || (an == bn && a.second < b.second);
    });
    std::stable_sort(loadDeps.begin(), loadDeps.end(), [&](const auto &a, const auto &b){
        return arrayDeps[ioNodes[a.first]->memRefName()] <
               arrayDeps[ioNodes[b.first]->memRefName()];
    });

    std::vector<ProTransfer> loads;
    std::vector<ProTransfer> stores;
    for(const auto &entry : loadDeps){
        auto *node = ioNodes[entry.first];
        loads.push_back({entry.first, _dfg_io_infos[entry.first].addr,
                         node->memSize(), node->memOffset(), node->realMemRefName()});
    }
    for(int id : storeIds){
        auto *node = ioNodes[id];
        stores.push_back({id, _dfg_io_infos[id].addr,
                          node->memSize(), node->memOffset(), node->realMemRefName()});
    }

    const int cfgBase = banks * _adg->iobSpadBankSize();
    const int iobBytes = std::max(1, (banks + 7) / 8);
    const std::string fn = sanitizeIdentifier(functionName);
    const int numArgIn = dfg->numArgIn();
    std::vector<std::string> arrayOrder;
    std::map<std::string, std::string> arrayArgs;
    std::set<std::string> usedArgNames = {"runtime"};
    const std::set<std::string> pythonKeywords = {
        "False", "None", "True", "and", "as", "assert", "async", "await",
        "break", "class", "continue", "def", "del", "elif", "else", "except",
        "finally", "for", "from", "global", "if", "import", "in", "is",
        "lambda", "nonlocal", "not", "or", "pass", "raise", "return", "try",
        "while", "with", "yield"
    };
    for(int i = 0; i < numArgIn; ++i)
        usedArgNames.insert("argIn" + std::to_string(i));
    auto registerArray = [&](const std::string &memoryName){
        if(arrayArgs.count(memoryName)) return;
        std::string argName = sanitizeIdentifier(memoryName);
        if(pythonKeywords.count(argName) || usedArgNames.count(argName))
            argName = "array_" + argName;
        const std::string baseName = argName;
        int suffix = 1;
        while(usedArgNames.count(argName))
            argName = baseName + "_" + std::to_string(suffix++);
        usedArgNames.insert(argName);
        arrayArgs[memoryName] = argName;
        arrayOrder.push_back(memoryName);
    };
    for(const auto &t : loads) registerArray(t.name);
    for(const auto &t : stores) registerArray(t.name);

    if(os_cocotb){
        auto &os = *os_cocotb;
        os << "# Generated by mapperPro for the current AuFORApro ADG.\n"
              "# Host buffers are NumPy arrays; transfer lengths are bytes.\n"
              "import numpy as np\n"
              "from typing import List\n"
              "from test_runif import DeviceConfig, DeviceData, DeviceRuntime, DeviceStream\n\n";
        os << "CONFIG_VALUES = [\n";
        for(const auto &packet : packets){
            const uint32_t data = packet.data.front();
            os << "    0x" << std::hex << std::setw(4) << std::setfill('0')
               << (data & 0xffff) << ", 0x" << std::setw(4)
               << ((data >> 16) & 0xffff) << ", 0x" << std::setw(4)
               << packet.addr << ",\n";
        }
        os << std::dec << "]\n";
        os << "IOB_ENABLE = [";
        for(int i = 0; i < iobBytes; ++i){
            if(i) os << ", ";
            os << "0x" << std::hex << ((_iob_ens >> (8 * i)) & 0xff);
        }
        os << std::dec << "]\nTILE_ENABLE = [0x01]\n\n";
        os << "def _input_bytes(array: np.ndarray, offset: int, size: int) -> np.ndarray:\n"
              "    data = np.ascontiguousarray(array).view(np.uint8).reshape(-1)\n"
              "    if data.nbytes < offset + size:\n"
              "        raise ValueError(f'input buffer has {data.nbytes} bytes, needs {offset + size}')\n"
              "    return data[offset:offset + size]\n\n"
              "def _output_bytes(array: np.ndarray, offset: int, size: int) -> np.ndarray:\n"
              "    if not isinstance(array, np.ndarray) or not array.flags.c_contiguous:\n"
              "        raise TypeError('output buffers must be C-contiguous NumPy arrays')\n"
              "    if not array.flags.writeable or array.nbytes < offset + size:\n"
              "        raise ValueError(f'output buffer has {array.nbytes} writable bytes, needs {offset + size}')\n"
              "    return array.view(np.uint8).reshape(-1)[offset:offset + size]\n\n"
              "async def aux_stream(\n"
              "    stream: DeviceStream, config: List[DeviceConfig],\n"
              "    iptrs: List[DeviceData], idata: List[np.ndarray],\n"
              "    optrs: List[DeviceData], odata: List[np.ndarray], olen: List[int],\n"
              "):\n"
              "    await stream.apply(config)\n"
              "    await stream.config(config_id=0)\n"
              "    for ptr, data in zip(iptrs, idata):\n"
              "        await stream.memcpyHostToDevice(\n"
              "            d_data=ptr, h_data=data, size=ptr.size\n"
              "        )\n"
              "    await stream.execution_start()\n"
              "    for ptr, data, size in zip(optrs, odata, olen):\n"
              "        await stream.memcpyDeviceToHost(\n"
              "            d_data=ptr, h_data=data, size=size\n"
              "        )\n"
              "    await stream.release()\n\n";
        os << "async def " << fn << "(runtime: DeviceRuntime";
        for(const auto &memoryName : arrayOrder)
            os << ", " << arrayArgs.at(memoryName) << ": np.ndarray";
        for(int i = 0; i < numArgIn; ++i)
            os << ", argIn" << i << ": int";
        os << "):\n"
              "    config_values = list(CONFIG_VALUES)\n";
        for(size_t i = 0; i < packets.size(); ++i){
            if(packets[i].argInIdx >= 0){
                os << "    config_values[" << (i * 3) << "] = int(argIn"
                   << packets[i].argInIdx << ") & 0xffff\n"
                   << "    config_values[" << (i * 3 + 1) << "] = (int(argIn"
                   << packets[i].argInIdx << ") >> 16) & 0xffff\n";
            }
        }
        os << "    iptrs = [\n";
        for(const auto &t : loads)
            os << "        DeviceData(0x" << std::hex << t.address << std::dec << ", "
               << t.size << "),  # " << t.name << " + " << t.hostOffset << " bytes\n";
        os << "    ]\n"
              "    idata = [\n";
        for(const auto &t : loads)
            os << "        _input_bytes(" << arrayArgs.at(t.name) << ", "
               << t.hostOffset << ", " << t.size << "),\n";
        os << "    ]\n"
              "    optrs = [\n";
        for(const auto &t : stores)
            os << "        DeviceData(0x" << std::hex << t.address << std::dec << ", "
               << t.size << "),  # " << t.name << " + " << t.hostOffset << " bytes\n";
        os << "    ]\n"
              "    odata = [\n";
        for(const auto &t : stores)
            os << "        _output_bytes(" << arrayArgs.at(t.name) << ", "
               << t.hostOffset << ", " << t.size << "),\n";
        os << "    ]\n"
              "    olen = [";
        for(size_t i = 0; i < stores.size(); ++i){
            if(i) os << ", ";
            os << stores[i].size;
        }
        os << "]\n"
              "    config = DeviceConfig(\n"
              "        config_values=config_values, iob_en=IOB_ENABLE,\n"
              "        tile_en=TILE_ENABLE, data_ptr=iptrs + optrs,\n"
              "    )\n"
              "    stream = runtime.create_stream()\n"
              "    await aux_stream(\n"
              "        stream=stream, config=[config],\n"
              "        iptrs=iptrs, idata=idata,\n"
              "        optrs=optrs, odata=odata, olen=olen,\n"
              "    )\n"
              "    await stream.synchronize()\n";
    }

    if(os_sdk){
        auto &os = *os_sdk;
        os << "/* Generated by mapperPro for the current AuFORApro ADG. */\n"
              "#include <stdint.h>\n#include <stdlib.h>\n"
              "#include \"cgra_cdma.h\"\n#include \"cgra_axil.h\"\n\n"
              "#ifndef AUFORAPRO_AXI_BASE\n#define AUFORAPRO_AXI_BASE 0x90000000U\n#endif\n\n"
              "static void HostToDeviceTransfer(XScuGic *IntcController, XAxiCdma *AxiCdmaInstance,\n"
              "                                 void *src_h, void *dst_d, int64_t bytelen) {\n"
              "  int status = XAxiCdma_DataTransfer(IntcController, AxiCdmaInstance,\n"
              "      (UINTPTR)src_h, (UINTPTR)dst_d, bytelen);\n"
              "  if (status != XST_SUCCESS) abort();\n}\n\n"
              "static void DeviceToHostTransfer(XScuGic *IntcController, XAxiCdma *AxiCdmaInstance,\n"
              "                                 void *src_d, void *dst_h, int64_t bytelen) {\n"
              "  int status = XAxiCdma_DataTransfer(IntcController, AxiCdmaInstance,\n"
              "      (UINTPTR)src_d, (UINTPTR)dst_h, bytelen);\n"
              "  if (status != XST_SUCCESS) abort();\n}\n\n";
        os << "void " << fn << "_sdk(XScuGic *IntcController, XAxiCdma *AxiCdmaInstance,\n"
              "                    void **din_addr, void **dout_addr";
        for(int i = 0; i < numArgIn; ++i) os << ", uint32_t argIn" << i;
        os << ")\n{\n  uint16_t cin[" << packets.size() << "][3] __attribute__((aligned("
           << _adg->cfgSpadDataWidth() / 8 << "))) = {\n";
        for(const auto &packet : packets){
            const uint32_t data = packet.data.front();
            os << "    {0x" << std::hex << std::setw(4) << std::setfill('0')
               << (data & 0xffff) << ", 0x" << std::setw(4)
               << ((data >> 16) & 0xffff) << ", 0x" << std::setw(4)
               << packet.addr << "},\n";
        }
        os << std::dec << "  };\n";
        for(size_t i = 0; i < packets.size(); ++i){
            if(packets[i].argInIdx >= 0){
                os << "  cin[" << i << "][0] = argIn" << packets[i].argInIdx << " & 0xffff;\n"
                   << "  cin[" << i << "][1] = (argIn" << packets[i].argInIdx << " >> 16) & 0xffff;\n";
            }
        }
        os << "  HostToDeviceTransfer(IntcController, AxiCdmaInstance, cin,\n"
           << "      (void *)(AUFORAPRO_AXI_BASE + 0x" << std::hex << cfgBase << std::dec
           << "), sizeof(cin));\n";
        for(size_t i = 0; i < loads.size(); ++i)
            os << "  HostToDeviceTransfer(IntcController, AxiCdmaInstance, din_addr[" << i
               << "], (void *)(AUFORAPRO_AXI_BASE + 0x" << std::hex << loads[i].address
               << std::dec << "), " << loads[i].size << "); /* " << loads[i].name << " */\n";
        os << "  cgra_config(0x0, " << packets.size() << ", 0x1);\n"
           << "  cgra_exe(0x" << std::hex << _iob_ens << std::dec << ", 0x1);\n"
              "  wait_cgra_all_finish();\n";
        for(size_t i = 0; i < stores.size(); ++i)
            os << "  DeviceToHostTransfer(IntcController, AxiCdmaInstance,\n"
               << "      (void *)(AUFORAPRO_AXI_BASE + 0x" << std::hex << stores[i].address
               << std::dec << "), dout_addr[" << i << "], " << stores[i].size
               << "); /* " << stores[i].name << " */\n";
        os << "}\n";
    }
    ++_task_id;
}
