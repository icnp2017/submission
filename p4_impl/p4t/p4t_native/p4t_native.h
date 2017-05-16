#ifndef P4T_NATIVE_H
#define P4T_NATIVE_H

#include "common.h"

namespace p4t {

auto min_pmgr(py::object classifier) -> py::object;
auto min_bmgr1_w_expansions(py::object classifier, int max_expanded_bits) -> py::object;
auto min_bmgr(py::object classifiers, int max_num_groups) -> py::object;
auto best_subgroup(py::object classifier, int max_width, bool only_exact, string algo) -> py::object;
void set_num_threads(int num_threads);
void pylog(string msg);

}

#endif
