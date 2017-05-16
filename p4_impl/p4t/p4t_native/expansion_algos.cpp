#include "expansion_algos.h"
#include "numeric"

namespace p4t {

auto initialize_expansions(vector<Support> const& ss) -> support_map<Support> {
    support_map<Support> expansions{};
    for (auto const& s : ss) {
        expansions[s] = s;
    }
    return expansions;
}

auto get_preimage(support_map<Support> const& map, Support const& elem) -> vector<Support> {
    vector<Support> result{};
    for (auto const& ss : map) {
        if (ss.second == elem) {
            result.emplace_back(ss.first);
        }
    }
    return result;
}
}

auto p4t::try_expand_chain(
        vector<Support> chain, 
        vector<Support> const& unique_supports, 
        vector<int> const& weights,
        int max_bits) -> pair<vector<Support>, support_map<Support>> {

    log()->info("trying to expand some bits...");

    support_set in_chain(begin(chain), end(chain));
    vector<int> non_chain_indices{};
    for (auto i = 0; i < int(unique_supports.size()); i++) {
        if (!in_chain.count(unique_supports[i])) {
            non_chain_indices.emplace_back(i);
        }
    }

    sort(begin(non_chain_indices), end(non_chain_indices), 
        [&weights](auto i, auto j) {
            return weights[i] > weights[j];
        });

    auto expansions = initialize_expansions(unique_supports);
    support_map<int> bits_expanded{};

    for (auto idx : non_chain_indices) {
        auto const candidate = unique_supports[idx];
        auto insertion_point = int(chain.size()) - 1; 
        while (insertion_point >= 0 && is_subset(candidate, chain[insertion_point])) {
            insertion_point--;
        }

        if (insertion_point < 0) {
            chain.emplace(begin(chain), candidate);
            continue;
        }

        auto const sunion = get_union(candidate, chain[insertion_point]);
        auto const bits_to_expand = 
            std::max(int(sunion.size()) - int(candidate.size()), 
                     int(sunion.size()) - int(chain[insertion_point].size()) + bits_expanded[chain[insertion_point]]);

        log()->info("... group# {:d} bits to expand: {:d}", idx, bits_to_expand);

        if (bits_to_expand > max_bits) {
            continue;
        }

        expansions[candidate] = sunion;
        for (auto const& s : get_preimage(expansions, chain[insertion_point])) {
            expansions[s] = sunion;
        }

        if (insertion_point < int(chain.size()) - 1 && sunion == chain[insertion_point + 1]) {
            auto const max_bits_to_expand = std::max(bits_expanded[sunion], bits_to_expand);
            bits_expanded[sunion] = max_bits_to_expand;
            chain.erase(begin(chain) + insertion_point);
        } else {
            bits_expanded[sunion] = bits_to_expand;
            chain[insertion_point] = sunion;
        }
    }

    return make_pair(chain, expansions);
}

