/* Copyright 2013-present Barefoot Networks, Inc.
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *   http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

/*
 * Antonin Bas (antonin@barefootnetworks.com)
 *
 */

#include <type_traits>
#include <boost/preprocessor/iteration/local.hpp>
#include <bm/bm_sim/actions.h>
#include <initializer_list>

#include "repeat.hpp"

template <typename... Args>
using ActionPrimitive = bm::ActionPrimitive<Args...>;

using bm::Data;
using bm::Field;
using bm::Header;

class modify_field : public ActionPrimitive<Field &, const Data &> {
  void operator ()(Field &f, const Data &d) {
    f.set(d);
  }
};

REGISTER_PRIMITIVE(modify_field);

class add_to_field : public ActionPrimitive<Field &, const Data &> {
  void operator ()(Field &f, const Data &d) {
    f.add(f, d);
  }
};

REGISTER_PRIMITIVE(add_to_field);

class drop : public ActionPrimitive<> {
  void operator ()() {
    get_field("standard_metadata.egress_port").set(511);
  }
};

REGISTER_PRIMITIVE(drop);

class no_op : public ActionPrimitive<> {
  void operator ()() {
  }
};

REGISTER_PRIMITIVE(no_op);

namespace detail {

template<typename... Args> 
class set_max_field_impl : public ActionPrimitive<Field &, Args...> {
  void operator()(Field &f, Args... args) {
    std::array<Data const *, sizeof...(args)> arr = { (&args)... };
    auto max = *std::max_element(begin(arr), end(arr), 
      [] (auto const a_1, auto const a_2) {
        return (*a_1) < (*a_2); 
      }
    );
    if (f < *max) {
      f.set(*max);
    }
  }   
};

template<typename... Args>
class compress : public ActionPrimitive<Field &, Args...> {
  void operator()(Field & f, Args... args) {
    static const Data one{1};

    auto arg_ptrs = std::make_tuple((&args)...); 

    constexpr auto num_args_per_source = 3;
    constexpr auto num_sources = sizeof...(args) / num_args_per_source;

    auto sources = get_stride<Field const *, num_args_per_source, 0>(arg_ptrs);
    auto from = get_stride<Data const *, num_args_per_source, 1>(arg_ptrs);
    auto to = get_stride<Data const *, num_args_per_source, 2>(arg_ptrs);

    f.set(0);
    Data tmp;
    Data mask;
    for (auto i = 0u; i < num_sources; ++i) {
      auto const length = to[i]->get_uint() - from[i]->get_uint();  
      tmp.shift_right(*sources[i], sources[i]->get_nbits() - to[i]->get_uint());

      mask.set(one);
      mask.shift_left(mask, length);
      mask.sub(mask, one);
      tmp.bit_and(tmp, mask);

      f.shift_left(f, length);
      f.bit_or(tmp, f);
    }
  }
};

}

#define BOOST_PP_LOCAL_LIMITS (1, SET_MAX_FIELD_NUM_SOURCES)

#define BOOST_PP_LOCAL_MACRO(n) \
    using set_max_field_##n = repeat_t<detail::set_max_field_impl, n, Data const&>; \
    REGISTER_PRIMITIVE(set_max_field_##n);
#include BOOST_PP_LOCAL_ITERATE()

#define BOOST_PP_LOCAL_LIMITS (1, COMPRESS_NUM_SOURCES)
#define BOOST_PP_LOCAL_MACRO(n) \
    using compress_##n = repeat_t<detail::compress, n, Field const&, Data const&, Data const&>; \
    REGISTER_PRIMITIVE(compress_##n);
#include BOOST_PP_LOCAL_ITERATE()
