#include <numeric>
#include <functional>
#include <parallel/algorithm>

#include "oi_algos.h"

namespace {

using namespace p4t;

auto const calc_set_difference(vector<int> const& lhs, vector<int> const& rhs) {
    vector<int> tmp;
    std::set_difference(begin(lhs), end(lhs), begin(rhs), end(rhs), back_inserter(tmp));
    return tmp;
}

auto find_exact(vector<Filter> const& filters, vector<int> const& bits_in_use) {
    auto exact = bits_in_use;
    for (auto const& filter : filters) {
        for (auto const bit : bits_in_use) {
            assert(bit < int(filter.size()));
            if (filter[bit] == Bit::ANY) {
                exact.erase(remove(begin(exact), end(exact), bit), end(exact));
            }
        }
    }
    return exact;
}

struct BitStats {
    BitStats(size_t n) : dontcare(n), zeros(n), ones(n), exact_bits{} {}

    vector<int> dontcare;
    vector<int> zeros;
    vector<int> ones;
    vector<int> exact_bits;
};

auto calc_bit_stats(vector<Filter> const& filters, vector<int> const& bits_in_use) {
    BitStats stats{filters[0].size()};

    for (auto const& filter : filters) {
        for (auto i : bits_in_use) {
            switch(filter[i]) {
                case Bit::ANY: stats.dontcare[i]++;
                    break;
                case Bit::ONE: stats.ones[i]++;
                    break;
                case Bit::ZERO: stats.zeros[i]++;
            }
        }
    }
    for (auto i : bits_in_use) {
        if (stats.dontcare[i] == 0) {
            stats.exact_bits.emplace_back(i);
        }
    }

    return stats;
}

auto is_oi(vector<Filter> const& filters, vector<int> const& bits_in_use) {
    vector<int> indices(filters.size());    
    iota(begin(indices), end(indices), 0);
    vector<bool> has_intersection(filters.size());

    auto const mask = bits_to_mask(bits_in_use);

    std::for_each(begin(indices), end(indices),
        [&filters, &has_intersection, &mask] (auto i) {
            for (auto j = 0; j < i; j++) {
                if (Filter::intersect(filters[i], filters[j], mask)) {
                    has_intersection[i] = true;
                    break;
                }
            }
        }
    );

    return std::find(begin(has_intersection), end(has_intersection), true) == end(has_intersection);
}

auto find_blockers(vector<Filter> const& filters, vector<int> const& bits_in_use) {
    log()->info("Calculating blockers...");
    assert(!filters.empty());
    vector<vector<bool>> blockers(filters.size(), vector<bool>(filters[0].size(), false));

    vector<int> indices(filters.size());    
    iota(begin(indices), end(indices), 0);

    auto const bits_mask = bits_to_mask(bits_in_use);

    __gnu_parallel::for_each(begin(indices), end(indices),
        [&filters, mask=bits_mask, &blockers] (auto i) {
            auto const& lower = filters[i];
            for (auto j = 0; j < i; j++) {
                auto const res = Filter::fast_blocker(lower, filters[j], mask);

                if (res.second == -1) {
                    blockers[i].assign(blockers[i].size(), true);
                    break;
                } else if (res.first) {
                    blockers[i][res.second] = true;
                }
            }
        }
    );

    log()->info("...Finished");

    return blockers;
}

template<class Function, class Cmp>
auto find_best_bits(
        vector<int> const& all_bits, vector<int> try_last, 
        Function value, Cmp cmp_value, int k = 1) -> vector<int> {

    auto const cmp = [cmp_value=cmp_value, value=value] (auto a, auto b) {
        return cmp_value(value(a), value(b));
    };

    vector<int> try_first = calc_set_difference(all_bits, try_last);

    vector<int> best{};

    if (int(try_first.size()) > k) {
        std::nth_element(begin(try_first), begin(try_first) + k, end(try_first), cmp);
        std::copy(begin(try_first), begin(try_first) + k, back_inserter(best));
    } else {
        std::copy(begin(try_first), end(try_first), back_inserter(best));
    }

    if (int(best.size()) <= k) {
        if (int(try_last.size() + best.size()) > k) {
            std::nth_element(begin(try_last), begin(try_last) + k - best.size(), end(try_last), cmp);
            std::copy(begin(try_last), begin(try_last) + k - best.size(), back_inserter(best));
        } else {
            std::copy(begin(try_last), end(try_last), back_inserter(best));
        }
    }

    std::sort(begin(best), end(best));

    return best;
}

template<class Function, class Cmp>
auto find_best_bit(
        vector<int> const& all_bits, vector<int> const& try_last, 
        Function value, Cmp cmp_value) -> int {
    return find_best_bits(all_bits, try_last, value, cmp_value, 1).front();
}

auto const check_if_use_dontcare_heuristic(
        vector<int> const& bits_in_use, 
        vector<int> const& bit_num_blockers, size_t l) {
    log()->info("Checking whether to use don't care heuristic...");
    if (bits_in_use.size() > 2 * l) {
        auto indices_sorted_by_blockers = bits_in_use;

        std::sort(begin(indices_sorted_by_blockers), end(indices_sorted_by_blockers), 
            [&bit_num_blockers](int a, int b) {
                return bit_num_blockers[b] > bit_num_blockers[a];
            }
        );

        log()->info("...blockers: [{:d}, {:d}, {:d}, ..., {:d}]", 
            bit_num_blockers[indices_sorted_by_blockers[0]], 
            bit_num_blockers[indices_sorted_by_blockers[1]], 
            bit_num_blockers[indices_sorted_by_blockers[2]], 
            bit_num_blockers[indices_sorted_by_blockers[l]]
        );

        if (bit_num_blockers[indices_sorted_by_blockers[0]] 
                >= 0.9 * bit_num_blockers[indices_sorted_by_blockers[2 * l]]) {
            log()->info("...YES, use heuristic!");
            return true;
        }
    }

    log()->info("...NO, don't use heuristic!");
    return false;
}

template<class Blockers>
auto const sum_blockers_by_bit(Blockers const& blockers) {
    vector<int> bit_num_blockers(blockers[0].size());

    for (auto const& blocker : blockers) {
        for (auto i = 0u; i < blocker.size(); i++) {
            if (blocker[i]) {
                bit_num_blockers[i]++;
            }
        }
    }

    return bit_num_blockers;
}

auto apply_dont_care_heuristic(
        vector<Filter> const& filters, vector<int> const& bits_in_use, 
        BitStats const& stats, bool only_exact, size_t l) 
    -> tuple<bool, vector<int>, vector<int>> {

    log()->info("Using ANY HEURISTIC!");

    auto const rm_bits = find_best_bits(bits_in_use, only_exact ? stats.exact_bits : vector<int>{}, 
        [&stats](auto b) { 
            return make_pair(stats.dontcare[b], std::min(stats.zeros, stats.ones));
        }, std::greater<>(), bits_in_use.size() - l);

    auto cur_mask = bits_to_mask(bits_in_use);
    for (auto bit : rm_bits) {
        cur_mask.set(bit, false);
    }

    if (only_exact) {
        vector<int> const exact_indices = [&]() {
            vector<int> retval;
            for (auto i = 0; i < int(filters.size()); i++) {
                if (filters[i].has_any(cur_mask)) {
                    continue;
                }
                retval.emplace_back(i);
            }
            return retval;
        }();

        if (exact_indices.size() < 0.001 * filters.size()) {
            log()->info("...any heuristinc FAILED, found only {:d} indices", exact_indices.size());
            return make_tuple(false, vector<int>{}, vector<int>{});
        } 
    
        auto const oi_indices = find_maximal_oi_subset_indices(filters, exact_indices, cur_mask);
        log()->info(
            "...found exact OI indices with {:d}/{:d} bits, exact {:d}, OI {:d}",
            bits_in_use.size() - rm_bits.size(), bits_in_use.size(), 
            exact_indices.size(), oi_indices.size());
        return make_tuple(true, rm_bits, oi_indices);
    }

    auto const oi_indices = find_maximal_oi_subset(filters, cur_mask);
    log()->info("...checking OI indices with {:d}/{:d} bits, OI {:d}", bits_in_use.size() - rm_bits.size(), bits_in_use.size(), oi_indices.size());
    return make_tuple(true, rm_bits, oi_indices);
}

auto remove_bits_w_blockers(
        vector<Filter> const filters, vector<int> const& bits_in_use, 
        BitStats const& stats, bool only_exact, size_t l) -> pair<vector<int>, vector<int>> {
    auto const blockers = find_blockers(filters, bits_in_use);
    auto const bit_num_blockers = sum_blockers_by_bit(blockers);


    if (check_if_use_dontcare_heuristic(bits_in_use, bit_num_blockers, l)) {
        bool success;
        vector<int> bits_to_remove, oi_indices;

        tie(success, bits_to_remove, oi_indices) = apply_dont_care_heuristic(filters, bits_in_use, stats, only_exact, l);
        if (success) {
            return make_pair(bits_to_remove, oi_indices);
        }
    }

    auto const best_bit = find_best_bit(
            bits_in_use, only_exact ? stats.exact_bits : vector<int>{}, 
            [&bit_num_blockers, &stats] (auto bit) { 
                return make_pair(bit_num_blockers[bit], -stats.dontcare[bit]); 
            }, std::less<>());

    vector<int> result{};

    for (auto i = 0u; i < blockers.size(); i++) {
        if (!blockers[i][best_bit]) {
            result.emplace_back(i);
        }
    }

    log()->info("Best bit is {:d} with {:d} rules and {:d} ANY bits", 
        best_bit, result.size(), stats.dontcare[best_bit]);

    return {{best_bit}, result};
}

auto remove_bits_oi(
        vector<Filter> const& filters, vector<int> const& bits_in_use, 
        BitStats const& stats, bool only_exact) 
    -> pair<vector<int>, vector<int>> {

    auto mask = bits_to_mask(bits_in_use);
    auto best = find_best_bits(bits_in_use, only_exact ? stats.exact_bits : vector<int>{},
            [&mask, &filters] (auto bit) {
                auto cur_mask = mask;
                cur_mask.set(bit, false);
                return int(find_maximal_oi_subset(filters, cur_mask).size());
            }, std::greater<>());

    mask.set(best.front(), false);
    return make_pair(best, find_maximal_oi_subset(filters, mask));
}


} // namespace


auto p4t::best_min_similarity_bits(vector<Filter> const& filters, size_t l) -> vector<int> {
    assert(!filters.empty());

    vector<int> result{};
    while (result.size() < l) {
        auto best_bit = -1;
        auto best_value = -1;
        for (auto i = 0u; i < filters[0].size(); i++) {
            if (find(begin(result), end(result), i) != end(result)) {
                continue;
            }
            auto count_zero = 0;
            auto count_one = 0;
            for (auto const& f : filters) {
                if (f[i] == Bit::ANY || f[i] == Bit::ONE) {
                    count_one++;
                } 
                if (f[i] == Bit::ANY || f[i] == Bit::ZERO) {
                    count_zero++;
                }
            }
            auto const value = std::max(count_zero, count_one);
            if (best_bit == -1 || value < best_value) {
                best_bit = i;
                best_value = value;
            }
        }
        assert(best_bit >= 0);
        result.emplace_back(best_bit);
    }

    return result;
}




auto p4t::best_to_stay_minme(vector<Filter> filters, size_t l, MinMEMode mode, bool only_exact) -> std::pair<vector<int>, vector<int>> {
    assert(!filters.empty());
    log()->info("starting minme; mode: {:d}; only exact: {:b}; total filters: {:d}", mode, only_exact, filters.size());

    vector<int> bits_in_use{};
    for (auto i = 0u; i < filters[0].size(); i++) {
        bits_in_use.emplace_back(i);
    }

    auto exact_bits_in_use = find_exact(filters, bits_in_use);

    vector<int> indices(filters.size());
    std::iota(begin(indices), end(indices), 0);

    while (bits_in_use.size() > l || (only_exact && bits_in_use != exact_bits_in_use)) {
        auto const stats = calc_bit_stats(filters, bits_in_use);

        vector<int> rm_bits;
        vector<int> oi_indices;
        switch(mode) {
            case MinMEMode::MAX_OI: 
                tie(rm_bits, oi_indices) = 
                    remove_bits_oi(filters, bits_in_use, stats, only_exact);
                break;
            case MinMEMode::BLOCKERS:
                tie(rm_bits, oi_indices) = 
                    remove_bits_w_blockers(filters, bits_in_use, stats, only_exact, l);
                break;
        }

        bits_in_use = calc_set_difference(bits_in_use, rm_bits);

        vector<int> new_indices{};
        vector<Filter> new_filters{};

        for (auto i : oi_indices) {
            new_indices.emplace_back(indices[i]);
            new_filters.emplace_back(filters[i]);
        }

        std::swap(indices, new_indices);
        std::swap(filters, new_filters);

        exact_bits_in_use = find_exact(filters, bits_in_use);

        log()->info("bits [{:d}...] have been found; bits left: {:d}; exact bits left: {:d}; entries left: {:d}", rm_bits.front(), bits_in_use.size(), exact_bits_in_use.size(), filters.size());
    }

    assert(is_oi(filters, bits_in_use));

    return make_pair(bits_in_use, indices);
}


auto p4t::find_maximal_oi_subset(vector<Filter> const& filters, Filter::BitArray const& mask) -> vector<int> {
    log()->info("Looking for a maximal oi subset...");
    vector<int> result{};

    for (auto i = 0u; i < filters.size(); i++) {
        auto intersects = false;
        for (auto j : result) {
            if (Filter::intersect(filters[j], filters[i], mask)) {
                intersects = true;
                break;
            }
        }
        if (!intersects) {
            result.emplace_back(i);
        }
    }

    log()->info("...Finished");
    return result;
}

auto p4t::find_maximal_oi_subset_indices(vector<Filter> const& filters, vector<int> const& indices, Filter::BitArray const& mask) -> vector<int> {
    log()->info("Looking for a maximal oi subset...");
    vector<int> result{};

    for (auto i : indices) {
        auto intersects = false;
        for (auto j : result) {
            if (Filter::intersect(filters[j], filters[i], mask)) {
                intersects = true;
                break;
            }
        }
        if (!intersects) {
            result.emplace_back(i);
        }
    }

    log()->info("...Finished");
    return result;
}

auto p4t::bits_to_mask(vector<int> const& bits) -> Filter::BitArray {
    Filter::BitArray res{}; 
    for (auto bit : bits) {
        res.set(bit, true);
    }
    return res;
}
