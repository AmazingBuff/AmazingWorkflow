//
// Created by AmazingBuff on 2026/9/11.
//

#pragma once
#include <cstddef>
#include <cstdint>
#include <functional>
#include <type_traits>
#include "plugin.h"

template<typename T>
    requires(std::is_integral_v<T>)
constexpr size_t hash_str(T const* str, size_t const len, size_t const& seed)
{
    size_t hash = seed;
    for (size_t i = 0; i < len; ++i)
        hash = (hash ^ static_cast<size_t>(str[i])) * 16777619ull;

    return hash;
}

template<typename T, typename... Rest>
constexpr void hash_combine_mul(size_t& seed, T const& val, Rest const&... rest)
{
    if constexpr (std::is_convertible_v<T, size_t>)
        seed ^= (static_cast<size_t>(val) + 0x9e3779b9 + (seed << 6) + (seed >> 2));
    else
        seed ^= (std::hash<T>()(val) + 0x9e3779b9 + (seed << 6) + (seed >> 2));
    (hash_combine_mul(seed, rest), ...);
}

template<typename T>
constexpr size_t hash_combine(size_t const& seed, T const& val)
{
    if constexpr (std::is_convertible_v<T, size_t>)
        return seed ^ (static_cast<size_t>(val) + 0x9e3779b9 + (seed << 6) + (seed >> 2));
    else
        return seed ^ (std::hash<T>()(val) + 0x9e3779b9 + (seed << 6) + (seed >> 2));
}

inline size_t hash_combine(size_t const& seed, void const* mem, size_t const& length)
{
    uint8_t const* bytes = static_cast<uint8_t const*>(mem);
    size_t hash = seed;
    for (size_t i = 0; i < length; ++i)
        hash = (hash ^ static_cast<size_t>(bytes[i])) * 16777619ull;

    return hash;
}

static constexpr size_t Author_Hash = hash_str(Plugin::Plugin_Author.data(), Plugin::Plugin_Author.size(), 0);