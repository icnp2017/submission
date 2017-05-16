#ifndef CHAIN_ALGOS_H
#define CHAIN_ALGOS_H

#include "support.h"

namespace p4t {

auto find_min_chain_partition(vector<Support> const& ss) -> vector<vector<Support>>;
auto find_min_bounded_chain_partition(
        vector<vector<Support>> const& sss, 
        vector<vector<int>> const& weights, 
        int max_num_chains) -> vector<vector<vector<Support>>>;
}

#endif
