#ifndef REPEAT_HPP
#define REPEAT_HPP

#include<utility>

template<typename... Ts>
struct repeat {
    template<template <typename...> typename TT, int N, typename... Args>
    struct iterate {
        using result = typename iterate<TT, N - 1, Ts..., Args...>::result;
    };

    template<template <typename...> typename TT, typename... Args>
    struct iterate<TT, 0, Args...> {
        using result = TT<Args...>;
    };
};

template<template <typename...> typename TT, int N, typename... Ts>
using repeat_t = typename repeat<Ts...>::template iterate<TT, N>::result;

// copied from cppreference.com
namespace detail {
template <class T, class Tuple, std::size_t... I>
constexpr T make_from_tuple_impl( Tuple&& t, std::index_sequence<I...> )
{
  return T(std::get<I>(std::forward<Tuple>(t))...);
}
} // namespace detail
 
template <class T, class Tuple>
constexpr T make_from_tuple( Tuple&& t )
{
    return detail::make_from_tuple_impl<T>(std::forward<Tuple>(t),
        std::make_index_sequence<std::tuple_size<std::decay_t<Tuple>>::value>{});
}

template<typename AT, int N, int K, typename T, size_t... I>
auto get_stride_impl(T const& t, std::integer_sequence<size_t, I...>) -> std::array<AT, sizeof...(I)>{
    return {std::get<I * N + K>(t)...};
}

template<typename AT, int N, int K, typename... Args>
auto get_stride(std::tuple<Args...> const& t) {
    return get_stride_impl<AT, N, K>(t, std::make_integer_sequence<size_t,sizeof...(Args) / N>());
}

#endif // REPEAT_HPP
