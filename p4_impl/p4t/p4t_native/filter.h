#ifndef FILTER_H
#define FILTER_H

#include <iterator>
#include <algorithm>

#include "common.h"
#include "bit_array.h"

namespace p4t {


enum class Bit {
    ONE, ZERO, ANY 
};

class Filter {
public:
    using BitArray = PackedBitArray<uint64_t, MAX_WIDTH>;
    
public:
    Filter() = default;

    Filter(py::object svmr)
        : value_{}, mask_{}, width_{size_t(len(svmr.attr("value")))} {
        assert(width_ <= MAX_WIDTH);

        for (auto i = 0u; i < width_; i++) {
            value_.set(i, py::extract<bool>(svmr.attr("value")[i]));
            mask_.set(i, py::extract<bool>(svmr.attr("mask")[i]));
        }
    }

    auto size() const {
        return width_;
    }

    auto operator[](size_t i) const -> Bit {
        return mask_.get(i) ? (value_.get(i) ? Bit::ONE : Bit::ZERO) : Bit::ANY;
    }

    auto has_any(BitArray const& mask) const -> bool {
        BitArray::BitChunk res = 0;
        for (auto i = 0u; i < BitArray::NUM_CHUNKS; i++) {
            res |= mask.chunk(i) & ~mask_.chunk(i);
        }
        return res;
    }

public:
    static auto fast_blocker(
            Filter const& f1, Filter const& f2, BitArray const& mask)
        -> pair<bool, int>;

    static auto intersect(
            Filter const& lhs, Filter const& rhs, BitArray const& mask) 
        -> bool;

private:
    BitArray value_;
    BitArray mask_;
    size_t width_;
};

}


auto inline p4t::Filter::fast_blocker(
        Filter const& f1, Filter const& f2, BitArray const& mask) -> pair<bool, int> {

    auto first_difference = -1;
    for (auto i = 0u; i < BitArray::NUM_CHUNKS; i++) {
        auto const diff = 
            (f1.value_.chunk(i) ^ f2.value_.chunk(i)) 
            & (mask.chunk(i) & f1.mask_.chunk(i) & f2.mask_.chunk(i));
        if (diff) {
            if (first_difference != -1) {
                return {false, first_difference};
            }
            auto const idx = __builtin_ctz(diff);
            first_difference = i * BitArray::BITS_PER_CHUNK + idx;
            if (diff & ~(1 << idx)) {
                return {false, first_difference};
            }
        }
    }
    return {true, first_difference};
}

auto inline p4t::Filter::intersect(
        Filter const& lhs, Filter const& rhs, BitArray const& mask) -> bool {

    assert(lhs.size() == rhs.size());

    for (auto i = 0u; i < BitArray::NUM_CHUNKS; i++) {
        if ((lhs.value_.chunk(i) ^ rhs.value_.chunk(i)) 
                & (mask.chunk(i) & lhs.mask_.chunk(i) & rhs.mask_.chunk(i))) {
            return false;
        }
    }

    return true;
}

#endif
