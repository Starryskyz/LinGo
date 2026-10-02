#pragma once
#include <cassert>
#include <cstdint>
#include <cstdio>


#define LOG_DEBUG
#define ASSERT_DEBUG

#ifdef LOG_DEBUG
#define zklog(fmt, ...)                         \
    do                                          \
    {                                           \
        printf("[%s:%d] ", __FILE__, __LINE__); \
        printf(fmt, ##__VA_ARGS__);             \
        printf("\n");                           \
    } while (0)
#define zklogpure(fmt, ...)         \
    do                              \
    {                               \
        printf(fmt, ##__VA_ARGS__); \
    } while (0)
#define zklogdiv()                                                                        \
    do                                                                                    \
    {                                                                                     \
        printf("\n==================================================================\n"); \
    } while (0)
#else
#define zklog(fmt, ...) ((void)0)
#define zklogdiv() ((void)0)
#endif

#ifdef ASSERT_DEBUG
#define zkassert(expr) assert(expr)
#define zkerror(fmt, ...)                              \
    do                                                 \
    {                                                  \
        printf("ERROR [%s:%d]: ", __FILE__, __LINE__); \
        printf(fmt, ##__VA_ARGS__);                    \
        printf("\n");                                  \
        exit(EXIT_FAILURE);                            \
    } while (0)
#define zkexit(code)                                   \
    do                                                 \
    {                                                  \
        printf("Exit at %s:%d\n", __FILE__, __LINE__); \
        exit(code);                                    \
    } while (0)
#else
#define zkassert(expr) ((void)0)
#define zkerror(fmt, ...) exit(EXIT_FAILURE)
#define zkexit(code) exit(code)
#endif

namespace CocotbClient::common {

inline uint32_t readUint32FromPtr(const uint8_t *ptr)
{
    uint32_t data = (uint32_t)ptr[0] | ((uint32_t)ptr[1] << 8) | ((uint32_t)ptr[2] << 16) | ((uint32_t)ptr[3] << 24);
    return data;
}

inline void writeUint32ToPtr(uint8_t *ptr, uint32_t data)
{
    ptr[0] = data & 0xFF;
    ptr[1] = (data >> 8) & 0xFF;
    ptr[2] = (data >> 16) & 0xFF;
    ptr[3] = (data >> 24) & 0xFF;
}

} // namespace CocotbClient::common