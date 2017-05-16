#ifndef EXPANSION_AGLOS_H
#define EXPANSION_AGLOS_H

#include "support.h"
#include "common.h"

namespace p4t {

auto try_expand_chain(
    vector<Support> chain, 
    vector<Support> const& unique_supports, 
    vector<int> const& weights,
    int max_bits) -> pair<vector<Support>, support_map<Support>>;
    
}

#endif // EXPANSION_ALGOS
