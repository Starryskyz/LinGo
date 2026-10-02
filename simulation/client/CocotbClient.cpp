#include "CocotbClient.h"
#include "common.h"
#include <algorithm>
#include <chrono>
#include <cstring>
#include <iostream>
#include <sstream>
#include <unistd.h>


namespace CocotbClient {

using namespace CocotbClient::common;

void ResponseData::print() const
{
    std::cout << "Response Code: " << static_cast<int>(response_code) << std::endl;
    std::cout << "Date Length: " << data_length << " bytes" << std::endl;
    std::cout << "Extra Info Length: " << extra_info_length << " bytes" << std::endl;

    if (!extra_info.empty())
    {
        std::cout << "Extra Info: " << extra_info << std::endl;
    }

    // 打印数据uint8
    if (data_length > 0)
    {
        std::cout << "Received Data(uint8): ";
        // size_t sz = std::min(static_cast<size_t>(10), data.size());
        size_t sz = data.size();
        std::cout << std::hex;
        for (size_t i = 0; i < sz; ++i)
        {
            std::cout << static_cast<int>(data[i]) << " ";
        }
        if (data.size() > sz)
            std::cout << "...";
        std::cout << std::dec;
        std::cout << std::endl;
    }
}


void ResponseData::setResponseCode(ResponseCodeEnum responseCode)
{
    response_code = static_cast<uint8_t>(responseCode);
}

bool ResponseData::isSuccess() const
{
    return response_code == static_cast<uint8_t>(ResponseCodeEnum::SUCCESS);
}


SocketClient::SocketClient(const std::string &host, int port)
{
    // 创建socket
    if ((sock_ = socket(AF_INET, SOCK_STREAM, 0)) < 0)
    {
        std::cerr << "Socket创建失败" << std::endl;
        return;
    }

    serv_addr_.sin_family = AF_INET;
    serv_addr_.sin_port = htons(port);

    // 转换IP地址
    if (inet_pton(AF_INET, host.c_str(), &serv_addr_.sin_addr) <= 0)
    {
        std::cerr << "无效地址/地址不支持" << std::endl;
        return;
    }

    // 设置超时
    struct timeval timeout;
    timeout.tv_sec = 5;
    timeout.tv_usec = 0;
    setsockopt(sock_, SOL_SOCKET, SO_RCVTIMEO, &timeout, sizeof(timeout));
    setsockopt(sock_, SOL_SOCKET, SO_SNDTIMEO, &timeout, sizeof(timeout));

    // 连接服务器
    if (connect(sock_, (struct sockaddr *)&serv_addr_, sizeof(serv_addr_)) < 0)
    {
        std::cerr << "连接失败" << std::endl;
        return;
    }

    std::cout << "已连接到服务器" << std::endl;
}


SocketClient::~SocketClient()
{
    if (sock_ > 0)
    {
        close(sock_);
    }
}

bool SocketClient::isConnected() const
{
    return sock_ > 0;
}

bool SocketClient::makeEchoTest()
{
    zklog("SocketClient start echo test");
    if (!isConnected())
    {
        zklog("SocketClient Disconnected");
        return false;
    }
    std::vector<uint8_t> data = {10, 20, 30, 40, 50};
    auto resp = sendCommand("echo", data.data(), data.size());
    zklog("SocketClient receive response:");
    resp.print();
    if (data != resp.data)
    {
        zklog("SocketClient echo test [Falied]");
        return false;
    } else
    {
        zklog("SocketClient echo test [Passed]");
        return true;
    }
}

// 发送消息并接收响应
ResponseData SocketClient::sendCommand(const std::string &command, const uint8_t *data, uint32_t dataLength)
{
    ResponseData resp;

    try
    {
        // 发送请求
        if (!sendRequest(command, data, dataLength))
        {
            zklog("Send Request Error, with command %s", command.c_str());
            resp.setResponseCode(ResponseCodeEnum::ERROR);
            return resp;
        }

        // 接收响应
        if (!receiveResponse(resp))
        {
            zklog("Receive Response Error, with command %s", command.c_str());
            resp.setResponseCode(ResponseCodeEnum::ERROR);
        }

    } catch (const std::exception &e)
    {
        zklog("Error %s, with command %s", e.what(), command.c_str());
        resp.setResponseCode(ResponseCodeEnum::ERROR);
    }

    return resp;
}

bool SocketClient::sendRequest(const std::string &command, const uint8_t *data, uint32_t dataLength)
{
    // 创建header
    std::vector<uint8_t> header(8);

    writeUint32ToPtr(&header[0], command.length());
    writeUint32ToPtr(&header[4], dataLength);

    // 发送header
    ssize_t sent1 = send(sock_, header.data(), header.size(), 0);
    if (sent1 != static_cast<ssize_t>(header.size()))
    {
        zklog("Send Header Failed, with command %s", command.c_str());
        return false;
    }

    // 发送command
    ssize_t sent2 = send(sock_, command.data(), command.size(), 0);
    if (sent2 != static_cast<ssize_t>(command.size()))
    {
        zklog("Send Command Failed, with command %s", command.c_str());
        return false;
    }

    // 发送data
    ssize_t sent3 = send(sock_, data, dataLength, 0);
    if (sent3 != static_cast<ssize_t>(dataLength))
    {
        zklog("Send Data Failed, with command %s", command.c_str());
        return false;
    }

    return true;
}

// 接收服务器响应
bool SocketClient::receiveResponse(ResponseData &resp)
{
    // 接收响应头
    std::vector<uint8_t> header(9);
    auto r1 = receiveAll(&header[0], 9);
    if (!r1)
    {
        zklog("Receive Response Header Failed");
        return false;
    }

    resp.response_code = header[0];
    resp.data_length = readUint32FromPtr(&header[1]);
    resp.extra_info_length = readUint32FromPtr(&header[5]);

    // {
    //     std::cout << "header:  ";
    //     size_t sz = header.size();
    //     std::cout << std::hex;
    //     for (size_t i = 0; i < sz; ++i)
    //     {
    //         std::cout << static_cast<int>(header[i]) << " ";
    //     }
    //     std::cout << std::dec;
    //     std::cout << std::endl;
    // }

    // 读取数据
    resp.data = {};
    // std::cout << (int)resp.response_code << "  expect resp data length  " << resp.data_length << "  exta " << resp.extra_info_length << std::endl;
    if (resp.data_length > 0)
    {
        resp.data.resize(resp.data_length);
        auto r2 = receiveAll(&resp.data[0], resp.data_length);
        if (!r2)
            return false;
    }

    resp.extra_info = "";
    if (resp.extra_info_length > 0)
    {
        resp.extra_info.resize(resp.extra_info_length);
        // 直接读取到 string 的数据中
        auto r3 = receiveAll(reinterpret_cast<uint8_t *>(resp.extra_info.data()), resp.extra_info_length);
        if (!r3)
            return false;
    }

    return true;
}

bool SocketClient::receiveAll(uint8_t *buffer, size_t length)
{
    size_t totalReceived = 0;

    while (totalReceived < length)
    {
        ssize_t bytesRead = recv(sock_, buffer + totalReceived,
                                 length - totalReceived, 0);

        if (bytesRead < 0)
        {
            // 错误处理
            if (errno == EINTR)
            {
                continue; // 被信号中断，继续
            }
            zklog("Recv Error:%s", strerror(errno));
            return false;
        } else if (bytesRead == 0)
        {
            // 连接被对端关闭
            zklog("Disconnect");
            return false;
        }

        totalReceived += bytesRead;
    }
    return true;
}

} // namespace CocotbClient
