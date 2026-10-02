#include "api_axi.h"
#include "common.h"
#include <cstring>


namespace CocotbClient {

using namespace CocotbClient::common;


CGRAClientWithAXI::CGRAClientWithAXI(const std::string &host, int port) : CGRAClientWithStream(host, port)
{
    stream_ = CGRAClientWithStream::createStream();
    cfg_.resize(1);
}


bool CGRAClientWithAXI::makeEchoTest()
{
    auto ret = client_.makeEchoTest();
    zklogdiv();
    if (!ret)
        return false;
    return true;
}

bool CGRAClientWithAXI::makeIOTest()
{
    zklog("CGRAClientWithAXI start SPM I/O test");

    std::vector<uint8_t> data_send = {11, 22, 33, 44, 55};
    std::vector<uint8_t> data_fetch(data_send.size());

    CGRAClientWithStream::memcpyH2D(stream_, data_send.data(), 0, data_send.size());
    CGRAClientWithStream::memcpyD2H(stream_, data_fetch.data(), 0, data_fetch.size());
    CGRAClientWithStream::syncStream(stream_);

    zklogpure("send  data: ");
    for (auto i : data_send)
        zklogpure("%d, ", i);
    zklogpure("\n");
    zklogpure("fetch data: ");
    for (auto i : data_fetch)
        zklogpure("%d, ", i);
    zklogpure("\n");

    if (data_send != data_fetch)
    {
        zklog("CGRAClientWithAXI SPM I/O test [Failed]");
        zklogdiv();
        return false;
    } else
    {
        zklog("CGRAClientWithAXI SPM I/O test [Passed]");
        zklogdiv();
        return true;
    }
}

bool CGRAClientWithAXI::matmul(float *x, float *w, float *o){
    std::vector<uint16_t> cfg_value = {
        0x8000, 0x0000, 0x0010,
		0x0120, 0x0100, 0x0011,
		0x0000, 0x0000, 0x0012,
		0x0000, 0x0008, 0x0013,
		0x002c, 0x0200, 0x0091,
		0x0000, 0x0000, 0x0092,
		0x0010, 0x8007, 0x0093,
		0x0020, 0x0000, 0x0094,
		0x0100, 0x0080, 0x00a0,
		0x8000, 0x0000, 0x00a8,
		0x0120, 0x011e, 0x00a9,
		0x0000, 0x0000, 0x00aa,
		0x0000, 0x0008, 0x00ab,
		0x1000, 0x0000, 0x00b0,
		0x0120, 0x0100, 0x00b1,
		0x0000, 0x0000, 0x00b2,
		0x0000, 0x2408, 0x00b3,
		0x0000, 0x0000, 0x00b4,
		0x1000, 0x0000, 0x00b8,
		0x0120, 0x0100, 0x00b9,
		0x0000, 0x0000, 0x00ba,
		0x0000, 0x2408, 0x00bb,
		0x0080, 0x0000, 0x00bc,
		0x0000, 0x0000, 0x00c0,
		0x0120, 0x0100, 0x00c1,
		0x0000, 0x0000, 0x00c2,
		0x0000, 0x2488, 0x00c3,
		0x0000, 0x0000, 0x00c4,
		0x0000, 0x0000, 0x00c8,
		0x0033, 0x0010, 0x00d0,
		0x010a, 0x1400, 0x00e1,
		0x0000, 0x0000, 0x00f0,
		0x0000, 0x0000, 0x00f1,
		0x002c, 0x0200, 0x00f9,
		0x0000, 0x0000, 0x00fa,
		0x0010, 0x8008, 0x00fb,
		0x0020, 0x0000, 0x00fc,
		0x002c, 0x0200, 0x0101,
		0x0000, 0x0000, 0x0102,
		0x0010, 0x8007, 0x0103,
		0x0020, 0x0000, 0x0104,
		0x0000, 0x0040, 0x0128,
		0x000a, 0x2300, 0x0139,
		0x002c, 0x0200, 0x0141,
		0x0000, 0x0000, 0x0142,
		0x0010, 0x8007, 0x0143,
		0x0020, 0x0000, 0x0144,
		0x0020, 0x0000, 0x0148,
		0x0002, 0x0000, 0x0150,
		0x1000, 0x0000, 0x0158,
		0x0120, 0x0100, 0x0159,
		0x0000, 0x0000, 0x015a,
		0x0000, 0x2408, 0x015b,
		0x0080, 0x0000, 0x015c,
		0x8000, 0x0000, 0x0160,
		0x0120, 0x0100, 0x0161,
		0x0000, 0x0000, 0x0162,
		0x0000, 0x0008, 0x0163,
		0x9000, 0x0000, 0x0168,
		0x0120, 0x0100, 0x0169,
		0x0000, 0x0000, 0x016a,
		0x0000, 0x0008, 0x016b,
		0x8000, 0x0000, 0x0170,
		0x0120, 0x011e, 0x0171,
		0x0000, 0x0000, 0x0172,
		0x0000, 0x0008, 0x0173,
		0x0200, 0x0000, 0x0178,
		0x2000, 0x0003, 0x0180,
		0x000a, 0x0a00, 0x0189,
		0x0002, 0x0000, 0x0198,
		0x0100, 0x0000, 0x0199,
		0x0808, 0x0000, 0x01a1,
		0x0018, 0x0000, 0x01b9,
		0x0000, 0x0080, 0x01c0,
		0x100a, 0x1a00, 0x01c9,
		0x0400, 0x0000, 0x01d8,
		0x0018, 0x0000, 0x01d9,
		0x0000, 0x0003, 0x01f8,
		0x0000, 0x0003, 0x0200,
		0x8000, 0x0000, 0x0208,
		0x0120, 0x011e, 0x0209,
		0x0000, 0x0000, 0x020a,
		0x0000, 0x0008, 0x020b,
		0x8000, 0x0000, 0x0220,
		0x0120, 0x011e, 0x0221,
		0x0000, 0x0000, 0x0222,
		0x0000, 0x0008, 0x0223,
		0x0000, 0x0002, 0x0228,
		0x0000, 0x0000, 0x0230,
		0x0000, 0x0001, 0x02a8,
		0x8000, 0x0000, 0x02b8,
		0x0120, 0x0100, 0x02b9,
		0x0000, 0x0000, 0x02ba,
		0x0000, 0x0008, 0x02bb
    };
    std::vector<uint8_t> iob_en = {0xfe,0x67};//{0x67,0xfe};//{0xfe,0x67};
    std::vector<uint8_t> tile_en = {0x0f};

    sendConfig(cfg_value.data(), cfg_value.size());
    sendData(reinterpret_cast<uint8_t *>(x), 0x8000, 2048);
    sendData(reinterpret_cast<uint8_t *>(x), 0x28000, 2048);
    sendData(reinterpret_cast<uint8_t *>(x), 0x20000, 2048);
    sendData(reinterpret_cast<uint8_t *>(x), 0x30000, 2048);
    sendData(reinterpret_cast<uint8_t *>(w), 0x38000, 16384);
    sendData(reinterpret_cast<uint8_t *>(w+4096), 0x24000, 16384);
    sendData(reinterpret_cast<uint8_t *>(w+8192), 0x18000, 16384);
    sendData(reinterpret_cast<uint8_t *>(w+12288), 0x0000, 16384);
    enableArray(iob_en.data(), iob_en.size(), tile_en.data(), tile_en.size());
    // float tmp[8];
    // fetchData(reinterpret_cast<uint8_t *>(tmp), 0x2000, 32);
    fetchData(reinterpret_cast<uint8_t *>(o), 0xc000, 32);
    fetchData(reinterpret_cast<uint8_t *>(o+8), 0x10000, 32);
    fetchData(reinterpret_cast<uint8_t *>(o+16), 0x1c000, 32);
    fetchData(reinterpret_cast<uint8_t *>(o+24), 0x14000, 32);
    // fetchData(reinterpret_cast<uint8_t *>(o), 0x38000, 32);
    return true;
}


void CGRAClientWithAXI::sendConfig(uint16_t *cfg, uint32_t length)
{
    has_apply_ = false;
    cfg_[0].config_value.assign(cfg, cfg + length);
}

void CGRAClientWithAXI::enableArray(uint8_t *iob_en, uint32_t iob_en_len, uint8_t *tile_en, uint32_t tile_en_len)
{
    if (!has_apply_)
    {
        has_apply_ = true;
        cfg_[0].iob_en.assign(iob_en, iob_en + iob_en_len);
        cfg_[0].tile_en.assign(tile_en, tile_en + tile_en_len);
        CGRAClientWithStream::applyResource(stream_, cfg_);
    }
    CGRAClientWithStream::switchConfig(stream_, 0);
    for (const auto &i : memcpy_task_)
    {
        CGRAClientWithStream::memcpyH2D(stream_, i.data_ptr, i.address, i.length);
    }
    memcpy_task_.clear();
    CGRAClientWithStream::startExecution(stream_);
}

void CGRAClientWithAXI::sendData(uint8_t *data, uint32_t address, uint32_t length)
{
    memcpy_task_.push_back(DataInfoType(data, address, length));
}

void CGRAClientWithAXI::fetchData(uint8_t *data, uint32_t address, uint32_t length)
{
    CGRAClientWithStream::memcpyD2H(stream_, data, address, length);
    CGRAClientWithStream::syncStream(stream_);
}

} // namespace CocotbClient