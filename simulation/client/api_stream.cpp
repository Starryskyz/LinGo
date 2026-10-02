#include "api_stream.h"
#include "common.h"
#include <cstring>

namespace CocotbClient {

using namespace CocotbClient::common;

int CGRAClientWithStream::createStream(uint32_t priority)
{
    std::vector<uint8_t> buf(4);
    writeUint32ToPtr(&buf[0], priority);
    auto resp = client_.sendCommand(kCmd_createStream, buf.data(), buf.size());
    auto id = readUint32FromPtr(&resp.data[0]);
    stream_cfg_num_[id] = 0;
    return id;
}

void CGRAClientWithStream::memcpyH2D(uint32_t stream, uint8_t *data, uint32_t address, uint32_t length, uint32_t dependType)
{
    std::vector<uint8_t> buf(length + 16);
    writeUint32ToPtr(&buf[0], stream);
    writeUint32ToPtr(&buf[4], dependType);
    writeUint32ToPtr(&buf[8], address);
    writeUint32ToPtr(&buf[12], length);
    std::memcpy(&buf[16], data, length);
    auto resp = client_.sendCommand(kCmd_memcpyH2D, buf.data(), buf.size());
}

int CGRAClientWithStream::memcpyD2H(uint32_t stream, uint8_t *data, uint32_t address, uint32_t length, uint32_t dependType)
{
    std::vector<uint8_t> buf(16);
    writeUint32ToPtr(&buf[0], stream);
    writeUint32ToPtr(&buf[4], dependType);
    writeUint32ToPtr(&buf[8], address);
    writeUint32ToPtr(&buf[12], length);
    auto resp = client_.sendCommand(kCmd_memcpyD2H, buf.data(), buf.size());
    auto id = readUint32FromPtr(&resp.data[0]);
    rtn_data_[id] = data;
    rtn_data_len_[id] = length;
    return id;
}

void CGRAClientWithStream::applyResource(uint32_t stream, const std::vector<CGRAConfigType> &configs)
{
    stream_cfg_num_[stream] = configs.size();
    size_t len = 8;
    for (const auto &cfg : configs)
    {
        len += 16;
        len += cfg.config_value.size() * sizeof(uint16_t);
        len += cfg.iob_en.size() * sizeof(uint8_t);
        len += cfg.tile_en.size() * sizeof(uint8_t);
        len += cfg.data_ptr.size() * 2 * sizeof(uint32_t);
    }
    std::vector<uint8_t> buf(len);
    writeUint32ToPtr(&buf[0], stream);
    writeUint32ToPtr(&buf[4], configs.size());
    size_t offset = 8;
    for (const auto &cfg : configs)
    {
        // iob_en
        size_t l = cfg.iob_en.size() * sizeof(uint8_t);
        writeUint32ToPtr(&buf[offset], l);
        offset += 4;
        std::memcpy(&buf[offset], cfg.iob_en.data(), l);
        offset += l;

        // tile_en
        l = cfg.tile_en.size() * sizeof(uint8_t);
        writeUint32ToPtr(&buf[offset], l);
        offset += 4;
        std::memcpy(&buf[offset], cfg.tile_en.data(), l);
        offset += l;

        // data_ptr
        writeUint32ToPtr(&buf[offset], cfg.data_ptr.size());
        offset += 4;
        for (const auto &i : cfg.data_ptr)
        {
            writeUint32ToPtr(&buf[offset], i.address);
            offset += 4;
            writeUint32ToPtr(&buf[offset], i.length);
            offset += 4;
        }

        // config_value
        l = cfg.config_value.size() * sizeof(uint16_t);
        writeUint32ToPtr(&buf[offset], l);
        offset += 4;
        std::memcpy(&buf[offset], cfg.config_value.data(), l);
        offset += l;
    }

    auto resp = client_.sendCommand(kCmd_applyResource, buf.data(), buf.size());
}

void CGRAClientWithStream::releaseResource(uint32_t stream)
{
    std::vector<uint8_t> buf(4);
    writeUint32ToPtr(&buf[0], stream);
    auto resp = client_.sendCommand(kCmd_releaseResource, buf.data(), buf.size());
    stream_cfg_num_[stream] = 0;
}

void CGRAClientWithStream::switchConfig(uint32_t stream, uint32_t config_id)
{
    std::vector<uint8_t> buf(8);
    zkassert(config_id < stream_cfg_num_[stream]);
    writeUint32ToPtr(&buf[0], stream);
    writeUint32ToPtr(&buf[4], config_id);
    auto resp = client_.sendCommand(kCmd_switchConfig, buf.data(), buf.size());
}

void CGRAClientWithStream::startExecution(uint32_t stream)
{
    std::vector<uint8_t> buf(4);
    writeUint32ToPtr(&buf[0], stream);
    auto resp = client_.sendCommand(kCmd_startExecution, buf.data(), buf.size());
}

void CGRAClientWithStream::syncStream(uint32_t stream)
{
    std::vector<uint8_t> buf(4);
    writeUint32ToPtr(&buf[0], stream);
    auto resp = client_.sendCommand(kCmd_syncStream, buf.data(), buf.size());
    // resp.print();
    uint32_t ret_num = readUint32FromPtr(&resp.data[0]);
    size_t offset = 4;
    for (uint32_t i = 0; i < ret_num; i++)
    {
        uint32_t key = readUint32FromPtr(&resp.data[offset]);
        offset += 4;
        uint32_t len = readUint32FromPtr(&resp.data[offset]);
        offset += 4;
        zkassert(rtn_data_len_[key] == len);
        std::memcpy(rtn_data_[key], &resp.data[offset], len);
        offset += len;
        rtn_data_.erase(key);
        rtn_data_len_.erase(key);
    }
}

void CGRAClientWithStream::memcpyFence(uint32_t stream)
{
    std::vector<uint8_t> buf(4);
    writeUint32ToPtr(&buf[0], stream);
    auto resp = client_.sendCommand(kCmd_memcpyFence, buf.data(), buf.size());
}

} // namespace CocotbClient