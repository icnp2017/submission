#ifndef BIT_ARRAY_H
#define BIT_ARRAY_H

#include <array>

namespace p4t {

template<class BitChunkT, size_t WidthT>
struct PackedBitArray {
    using BitChunk = BitChunkT;

    static auto constexpr WIDTH = WidthT;
    static auto constexpr BITS_PER_CHUNK = 8 * sizeof(BitChunk);
    static auto constexpr NUM_CHUNKS = (WIDTH + BITS_PER_CHUNK - 1) / BITS_PER_CHUNK;

public:
    PackedBitArray() = default;

    void set(size_t i, bool x) {
        if (x) {
            bits_[i / BITS_PER_CHUNK] |= (static_cast<BitChunk>(1) << (i % BITS_PER_CHUNK));
        } else {
            bits_[i / BITS_PER_CHUNK] &= ~(static_cast<BitChunk>(1) << (i % BITS_PER_CHUNK));
        }
    }

    auto get(size_t i) const -> bool {
        return bits_[i / BITS_PER_CHUNK] & (static_cast<BitChunk>(1) << (i % BITS_PER_CHUNK));
    }

    auto chunk(size_t i) const -> BitChunk {
        return bits_[i];
    }

private:
    std::array<BitChunk, NUM_CHUNKS> bits_; 
};

}

#endif // BIT_ARRAY_H
