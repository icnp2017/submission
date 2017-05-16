#include <boost/graph/adjacency_list.hpp>
#include <boost/graph/max_cardinality_matching.hpp>
#include <boost/graph/breadth_first_search.hpp>
#include <boost/graph/successive_shortest_path_nonnegative_weights.hpp>

#include "chain_algos.h"

namespace {

using namespace boost;
using namespace p4t;

using p4t::tuple;
using p4t::pair;
using std::begin;
using std::end;

using MaxMatchingGraph = adjacency_list<vecS, vecS, undirectedS>;

using AntichainGraph = adjacency_list<vecS, vecS, directedS>;

using MinCostMaxFlowTraits = adjacency_list_traits<vecS, vecS, directedS>;
using MinCostMaxFlowGraph = adjacency_list<vecS, vecS, directedS, no_property,
        property<edge_capacity_t, int,
            property<edge_residual_capacity_t, int,
                property<edge_reverse_t, MinCostMaxFlowTraits::edge_descriptor,
                    property<edge_weight_t, int>
                >
            >
        >
    >;

template<class VD>
auto calculate_chains(vector<Support> const& ss, vector<VD> const& mate, VD absent) {
    // Note that vertices mapped to itself are not considered start  vertices and, thus, they won't be added to any chain 
    vector<bool> is_chain_start(ss.size(), true);
    for (VD i = 0; i < ss.size(); i++) {
        if (mate[i] != absent) {
            is_chain_start[mate[i] - ss.size()] = false;
        }
    }

    vector<vector<Support>> result{}; 
    for (VD i = 0; i < ss.size(); ++i) {
        if (is_chain_start[i]) {
            vector<Support> chain{};
            for (VD j = i; j != absent; j = mate[j] - ss.size()) {
                chain.emplace_back(ss[j]);
                if (mate[j] == absent) {
                    break;
                }
            }
            result.emplace_back(chain);
        }
    }
    return result;
}

template<class Graph>
auto add_dilworths_edges(vector<Support> const& ss, Graph& g) {
    using VD = graph_traits<MaxMatchingGraph>::vertex_descriptor;

    for (VD i = 0; i < ss.size(); i++) {
        for (VD j = 0; j < ss.size(); j++) {
            if (is_subset(ss[i], ss[j]) && ss[i] != ss[j]) {
                add_edge(i, ss.size() + j, g);
            }
        }
    }
}

auto construct_dilworths_mates(vector<Support> const& ss) {
    using VD = graph_traits<MaxMatchingGraph>::vertex_descriptor;

    MaxMatchingGraph g{2 * ss.size()};

    add_dilworths_edges(ss, g);

    vector<VD> mate(2 * ss.size());
    auto const success = checked_edmonds_maximum_cardinality_matching(g, &mate[0]);
    assert(success);

    return mate;
}

auto find_max_antichain(vector<Support> const& ss) -> vector<size_t> {
    using VD = graph_traits<AntichainGraph>::vertex_descriptor;
    auto const mate = construct_dilworths_mates(ss);

    AntichainGraph g{2 * ss.size() + 1};
    auto const source = 2 * ss.size();

    add_dilworths_edges(ss, g);

    for (VD i = 0; i < ss.size(); i++) {
        // TODO: I don't like that we must know what the type of "no_mate" is.
        if (mate[i] != graph_traits<MaxMatchingGraph>::null_vertex()) {
            remove_edge(i, mate[i], g);
            add_edge(mate[i], i, g);
        } else {
            add_edge(source, i, g);
        }
    }
    
    vector<graph_traits<AntichainGraph>::vertices_size_type> distance(num_vertices(g), 0);
    breadth_first_search(g, source, visitor(make_bfs_visitor(record_distances(&distance[0], on_tree_edge()))));

    vector<size_t> result{};
    for (VD i = 0; i < ss.size(); i++) {
        if (distance[i] != 0 && distance[i + ss.size()] == 0) {
            result.emplace_back(i);
        }
    }

    auto const num_edges = count_if(begin(mate), begin(mate) + ss.size(), [] (auto const x) { return x != graph_traits<MaxMatchingGraph>::null_vertex(); });

    log()->info("for a set of size {:d} with a chain cover of size {:d} antichain of size {:d} is found", ss.size(), ss.size() - num_edges, result.size());

    return result;
}

auto calc_memory_increase(size_t s1_idx, size_t s2_idx, vector<Support> const& ss, vector<int> const& weights) {
    auto const res = get_union(ss[s1_idx], ss[s2_idx]);
    return ((long long) weights[s1_idx]) * ((1ll << (res.size() - ss[s1_idx].size())) - 1)
        + ((long long) weights[s2_idx]) * ((1ll << (res.size() - ss[s2_idx].size())) - 1);
}

}

auto p4t::find_min_chain_partition(vector<Support> const& ss) -> vector<vector<Support>> {
    auto const mate = construct_dilworths_mates(ss);
    return calculate_chains(ss, mate, graph_traits<MaxMatchingGraph>::null_vertex());
}


auto p4t::find_min_bounded_chain_partition(
        vector<vector<Support>> const& sss, 
        vector<vector<int>> const& weights, 
        int max_num_chains) -> vector<vector<vector<Support>>> {
    using namespace boost;
    
    using std::begin; // confilcts with boost
    using std::end; // conflicts with boost
    using VD = graph_traits<MinCostMaxFlowGraph>::vertex_descriptor;

    vector<int> ss_offset{};
    auto total_size = 0;
    for (auto const& ss : sss) {
        ss_offset.emplace_back(total_size);
        total_size += ss.size();
    }

    MinCostMaxFlowGraph g(2 * total_size + 3); // source, aux_source, target
    auto const source = 2 * total_size;
    auto const aux_source = 2 * total_size + 1;
    auto const target = 2 * total_size + 2;

    auto capacity = get(edge_capacity, g);
    auto rev = get(edge_reverse, g);
    auto weight = get(edge_weight, g);

    auto add_edge = [&capacity, &rev, &weight, &g]
        (VD u, VD v, int c, int w) {
            auto e = boost::add_edge(u, v, g).first;
            auto er = boost::add_edge(v, u, g).first;
            rev[e] = er;
            rev[er] = e;

            capacity[e] = c;
            capacity[er] = 0;
            weight[e] = w;
            weight[er] = -w;
        };


    for (auto ss_idx = 0; ss_idx < int(sss.size()); ss_idx++) {
        auto const& ss = sss[ss_idx];
        auto const offset = ss_offset[ss_idx];

        for (VD i = 0; i < ss.size(); i++) {
            for (VD j = 0; j < ss.size(); j++) {
                if (is_subset(ss[i], ss[j]) && ss[i] != ss[j]) {
                    add_edge(offset + i, total_size + offset + j, 1, 0);
                }
            }

            add_edge(offset + i, total_size + offset + i, 1, weights[ss_idx][i]);
        }

    }

    for (VD i = 0; int(i) < total_size; i++) {
        add_edge(aux_source, i, 1, 0);
        add_edge(total_size + i, target, 1, 0);
    }

    add_edge(source, aux_source, std::max(0, total_size - max_num_chains), 0);

    successive_shortest_path_nonnegative_weights(g, source, target);

    auto res_capacity = get(edge_residual_capacity, g);

    vector<vector<vector<Support>>> result{};
    for (auto ss_idx = 0; ss_idx < int(sss.size()); ss_idx++) {
        auto const& ss = sss[ss_idx];
        auto const offset = ss_offset[ss_idx];

        vector<VD> mate(ss.size() * 2, graph_traits<MinCostMaxFlowGraph>::null_vertex());

        for (VD i = 0; i < ss.size(); i++) {
            for (VD j = 0; j < ss.size(); j++) {
                auto edge_ok = edge(offset + i, total_size + offset + j, g);
                if (edge_ok.second && res_capacity[edge_ok.first] == 0) {
                    mate[i] = j + ss.size();
                    mate[j + ss.size()] = i;
                }
            }
        }

        result.emplace_back(calculate_chains(ss, mate, graph_traits<MinCostMaxFlowGraph>::null_vertex()));
    }

    return result;
}
