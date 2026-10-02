#pragma once

#include "api_stream.h"
#include <cstdint>


namespace CocotbClient {


class CGRAClientWithAXI : protected CGRAClientWithStream {
public:
    CGRAClientWithAXI(const std::string &host = "127.0.0.1", int port = 8888);
    ~CGRAClientWithAXI() = default;

    bool makeEchoTest();
    bool makeIOTest();
    bool makeIntVecAdderTest();
    bool matmul(float *x, float *w, float *o);

    void sendConfig(uint16_t *cfg, uint32_t length);

    /**
     * @brief 启用上一次sendConfig的配置
     */
    void enableArray(uint8_t *iob_en, uint32_t iob_en_len, uint8_t *tile_en, uint32_t tile_en_len);

    /**
     * @brief 仅用于写入SPM的数据，不包含cfg
     */
    void sendData(uint8_t *data, uint32_t address, uint32_t length);

    /**
     * @brief 仅用于读取SPM的数据
     */
    void fetchData(uint8_t *data, uint32_t address, uint32_t length);

private:
    struct DataInfoType {
    public:
        uint8_t *data_ptr;
        uint32_t address, length;
        DataInfoType(uint8_t *ptr, uint32_t addr, uint32_t len) : data_ptr(ptr), address(addr), length(len) {}
    };

    std::vector<DataInfoType> memcpy_task_; // memcpyH2D，sendData
    int stream_;
    std::vector<CGRAConfigType> cfg_;
    bool has_apply_ = false;
};

} // namespace CocotbClient