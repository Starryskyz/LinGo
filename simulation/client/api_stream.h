#pragma once

#include "CocotbClient.h"
#include <unordered_map>
#include <unordered_set>

namespace CocotbClient {

class CGRAConfigType {
public:
    struct DataPtr {
        uint32_t address, length;
        DataPtr(uint32_t addr, uint32_t len) : address(addr), length(len) {}
    };
    std::vector<uint16_t> config_value;
    std::vector<DataPtr> data_ptr; // 可以为空
    std::vector<uint8_t> iob_en;
    std::vector<uint8_t> tile_en;

    CGRAConfigType() = default;
};

class CGRAClientWithStream {
protected:
    SocketClient client_;

public:
    CGRAClientWithStream(const std::string &host = "127.0.0.1", int port = 8888) : client_(host, port) {}

    ~CGRAClientWithStream() = default;

public:
    /**
     * @brief Create a Stream object
     * @param priority 数字越大，优先级越高
     * @return stream id
     */
    int createStream(uint32_t priority = 0);
    void memcpyH2D(uint32_t stream, uint8_t *data, uint32_t address, uint32_t length, uint32_t dependType = 0);
    /**
     * @brief 异步，当使用syncStream后得到数据
     * @return data tag
     */
    int memcpyD2H(uint32_t stream, uint8_t *data, uint32_t address, uint32_t length, uint32_t dependType = 0);
    /**
     * @brief 一次加载多份配置，依照最大cfg分配硬件资源，单次执行其中一份配置
     */
    void applyResource(uint32_t stream, const std::vector<CGRAConfigType> &configs);
    void releaseResource(uint32_t stream);
    /**
     * @brief 根据先前加载的选择一份配置执行
     */
    void switchConfig(uint32_t stream, uint32_t config_id);
    void startExecution(uint32_t stream);
    void syncStream(uint32_t stream);
    void memcpyFence(uint32_t stream);

public:
    const std::string kCmd_createStream = "createStream";
    const std::string kCmd_memcpyH2D = "memcpyH2D";
    const std::string kCmd_memcpyD2H = "memcpyD2H";
    const std::string kCmd_applyResource = "apply";
    const std::string kCmd_releaseResource = "release";
    const std::string kCmd_switchConfig = "config";
    const std::string kCmd_startExecution = "exeStart";
    const std::string kCmd_syncStream = "synchronize";
    const std::string kCmd_memcpyFence = "memcpyFence";

protected:
    std::unordered_map<uint32_t, uint8_t *> rtn_data_;
    std::unordered_map<uint32_t, uint32_t> rtn_data_len_;
    std::unordered_map<int, int> stream_cfg_num_; // stream_id -> cfg_num [Resource]
};

} // namespace CocotbClient