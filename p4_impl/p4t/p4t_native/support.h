#ifndef SUPPORT_H
#define SUPPORT_H

#include <unordered_map>
#include <unordered_set>
#include <boost/functional/hash.hpp>

#include "common.h"
#include "filter.h"

namespace p4t { 
using Support = vector<int>;

template<class T>
using support_map = std::unordered_map<Support, T, boost::hash<Support>>;
using support_set = std::unordered_set<Support, boost::hash<Support>>;

inline auto select_unique(vector<Support> supports) -> vector<Support> {
    std::sort(begin(supports), end(supports));
    auto last = std::unique(begin(supports), end(supports));
    supports.erase(last, end(supports));

    return supports;
}

inline auto to_support(Filter const& filter) -> Support {
    Support result{};
    for (auto i = 0; i < int(filter.size()); i++) {
        if (filter[i] != Bit::ANY) {
            result.emplace_back(i);
        }
    }
    return result;
}

inline auto to_supports(vector<Filter> const& filters) -> vector<Support> {
    vector<Support> supports{};
    transform(begin(filters), end(filters), back_inserter(supports), to_support);
    return supports;
}

inline auto is_subset(Support const& lhs, Support const& rhs) {
    return std::includes(begin(rhs), end(rhs), begin(lhs), end(lhs)); 
}

inline auto is_in_conflict(Support const& lhs, Support const& rhs) {
    return !is_subset(lhs, rhs) && !is_subset(rhs, lhs);
}

inline auto get_union(Support const& rhs, Support const& lhs) -> Support {
    Support result{};
    set_union(begin(rhs), end(rhs), begin(lhs), end(lhs), back_inserter(result));
    return result;
}

template<class OStream>
OStream& operator<<(OStream& os, Support const& s) {
    os << "{";
    for (auto it = begin(s); next(it) != end(s); ++it) {
        os << (*it) << ", ";
    }
    os << s.back() << "}";
    return os;
}

}

#endif
