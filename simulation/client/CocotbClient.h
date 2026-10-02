#pragma once
#include <arpa/inet.h>
#include <cstdint>
#include <string>
#include <sys/socket.h>
#include <vector>

namespace CocotbClient {

/**
 * [header][command][data]
 * [8 header]:[4 cmd长度][4 data长度]
 *
 * [header][data][extra_info(JSON)]
 * [9 header]:[1 响应码][4 data长度][4 extra_info长度]
 */

enum class ResponseCodeEnum : uint8_t {
    SUCCESS,
    ERROR,
    INVALID,
};

class ResponseData {
public:
    uint8_t response_code;
    uint32_t data_length;
    uint32_t extra_info_length;
    std::vector<uint8_t> data;
    std::string extra_info;

    ResponseData() : response_code(0), data_length(0), extra_info_length(0) {}

    void print() const;

    void setResponseCode(ResponseCodeEnum responseCode);

    bool isSuccess() const;
};

class SocketClient {
private:
    int sock_ = 0;
    struct sockaddr_in serv_addr_;

public:
    SocketClient(const std::string &host = "127.0.0.1", int port = 8888);

    ~SocketClient();

    bool isConnected() const;

    // 发送消息并接收响应
    ResponseData sendCommand(const std::string &command, const uint8_t *data, uint32_t dataLength);

    bool makeEchoTest();

private:
    // 发送请求到服务器
    bool sendRequest(const std::string &command, const uint8_t *data, uint32_t dataLength);

    // 接收服务器响应
    bool receiveResponse(ResponseData &resp);

    bool receiveAll(uint8_t *buffer, size_t length);
};


} // namespace CocotbClient
