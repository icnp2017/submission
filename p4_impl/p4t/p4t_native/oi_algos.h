#ifndef OI_ALGOS_H
#define OI_ALGOS_H

#include "common.h"
#include "filter.h"

namespace p4t {

enum MinMEMode {
    MAX_OI, BLOCKERS
};

auto best_min_similarity_bits(vector<Filter> const& filters, size_t l) -> vector<int>;
auto best_to_stay_minme(vector<Filter> filters, size_t l, MinMEMode mode, bool only_exact) -> pair<vector<int>, vector<int>>;
auto find_maximal_oi_subset(vector<Filter> const& filters, Filter::BitArray const& mask) -> vector<int>;
auto find_maximal_oi_subset_indices(vector<Filter> const& filters, vector<int> const& indices, Filter::BitArray const& mask) -> vector<int>;
auto bits_to_mask(vector<int> const& bits) -> Filter::BitArray;

}

#endif
