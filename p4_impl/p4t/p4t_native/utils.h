#ifndef UTILS_H
#define UTILS_H

#include "filter.h"

namespace p4t {


inline auto svmr2filters(py::object const& svmr) {
    if (len(svmr) == 0) {
        throw std::invalid_argument("svmr should not be empty");
    }
    vector<Filter> filters{};
    for (auto i = 0; i < len(svmr); i++) {
        filters.emplace_back(Filter(svmr[i]));
    }

    return filters;
}

}

namespace std { // Need std for ADL

template<class T>
auto to_python(T const& x) -> T {
    return x;
}

template<class T1, class T2>
auto to_python(pair<T1, T2> const& p) -> boost::python::tuple {
    return boost::python::make_tuple(to_python(p.first), to_python(p.second));
}

template<class T>
auto to_python(vector<T> const& xs) -> boost::python::list {
    boost::python::list result{};
    for (auto const& x : xs) {
        result.append(to_python(x));
    }
    return result;
}

template<class T>
auto to_python(set<T> const& xs) -> boost::python::list {
    boost::python::list result{};
    for (auto const& x : xs) {
        result.append(to_python(x));
    }
    return result;
}

}

#endif
