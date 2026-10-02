#include "api_axi.h"
#include <cstdint>
#include <cstdlib>
#include <iostream>
#include <vector>

void makeIntVecAdderTest(CocotbClient::CGRAClientWithAXI &client)
{
    printf("Start IntVec Adder test\n");

    std::vector<uint16_t> cfg_value =
        {0x9000,
         0x4000,
         0x0008,
         0x0001,
         0x0000,
         0x0009,
         0x0000,
         0x0000,
         0x000A,
         0x0000,
         0x0008,
         0x000B,
         0x8000,
         0x4000,
         0x0010,
         0x0001,
         0x0000,
         0x0011,
         0x0000,
         0x0000,
         0x0012,
         0x0000,
         0x0008,
         0x0013,
         0x0000,
         0x0000,
         0x0020,
         0x0000,
         0x0001,
         0x0030,
         0x0900,
         0x0000,
         0x0031,
         0x0000,
         0x0000,
         0x0041,
         0x0800,
         0x0000,
         0x0061,
         0x0800,
         0x0000,
         0x0081,
         0x0800,
         0x0000,
         0x00A1,
         0x0800,
         0x0000,
         0x00C1,
         0x2000,
         0x0000,
         0x00E0,
         0x8000,
         0x4000,
         0x00E8,
         0x0001,
         0x0000,
         0x00E9,
         0x0000,
         0x0000,
         0x00EA,
         0x0000,
         0x2308,
         0x00EB,
         0x0080,
         0x0000,
         0x00EC};

    std::vector<uint8_t> iob_en = {0x07};
    std::vector<uint8_t> tile_en = {0x01};

    std::vector<uint16_t> A(20), B(20), C(20), expected_C(20);
    for (int i = 0; i < 20; i++)
    {
        A[i] = i;
        B[i] = 2 * i;
        C[i] = 0;
        expected_C[i] = A[i] + B[i];
    }

    client.sendConfig(cfg_value.data(), cfg_value.size());
    client.sendData(reinterpret_cast<uint8_t *>(A.data()), 0x0, 40);
    client.sendData(reinterpret_cast<uint8_t *>(B.data()), 0x2000, 40);
    client.enableArray(iob_en.data(), iob_en.size(), tile_en.data(), tile_en.size());
    client.fetchData(reinterpret_cast<uint8_t *>(C.data()), 0x4000, 40);

    printf("Test A + B = C\n");
    printf("Vec A: ");
    for (auto i : A)
        printf("%d, ", i);
    printf("\n");
    printf("Vec B: ");
    for (auto i : B)
        printf("%d, ", i);
    printf("\n");
    printf("Vec C: ");
    for (auto i : C)
        printf("%d, ", i);
    printf("\n");

    if (expected_C != C)
    {
        printf("CGRAClientWithAXI IntVec Adder test [Failed]\n");
    } else
    {
        printf("CGRAClientWithAXI IntVec Adder test [Passed]\n");
    }
}

int main()
{
    CocotbClient::CGRAClientWithAXI client;

    client.makeEchoTest();
    client.makeIOTest();

    makeIntVecAdderTest(client);
}