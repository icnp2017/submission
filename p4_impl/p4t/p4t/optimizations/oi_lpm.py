from itertools import chain, product

# TODO avoid this import?
from p4t.vmrs.simple import SimpleVMREntry
import p4t_native


def expand(vmr_entry, bits):
    """ Performs an expansion of set of bits in the given entry.

    Args:
        vmr_entry: VMR entry.
        bits: Bit indices where exact match is required

    Returns:
        The list of expanded entries
    """
    bits = set(bits)
    mask = []
    value_options = []
    for i, (v, m) in enumerate(zip(vmr_entry.value, vmr_entry.mask)):  # pylint: disable=invalid-name
        mask.append(m or (i in bits))
        value_options.append([v] if m or (i not in bits) else [True, False])
    return [SimpleVMREntry(tuple(value), mask, vmr_entry.action, vmr_entry.priority)
            for value in product(*value_options)]


def _chain2diffs(bitchain):
    """ Returns adjacent differences of a given bit indices chain."""
    diffs = []
    last = set()
    for support in (set(bits) for bits in bitchain):
        diffs.append(sorted(list(support - last)))
        last = support
    return diffs


def _chain2bits(bitchain, bitwidth):
    """ Returns the sequence of bit indices corresponding to a given chain."""
    return tuple(chain(*_chain2diffs(bitchain + [list(range(bitwidth))])))


def set_number_of_threads(num_threads):
    """ Sets the number of threads to be used by an optimization engine."""
    p4t_native.set_num_threads(num_threads)


def minimize_num_groups(classifier):
    """ Splits the classifier into the minimal possible number of LPM classifiers.

    Args:
        classifier: Original classifier.

    Returns:
        The list of LPM classifiers equivalent to the original.
    """
    partition, partition_indices = p4t_native.min_pmgr(classifier)

    subclassifiers = []
    for bitchain, indices in zip(partition, partition_indices):
        subclassifiers.append(classifier.subset(indices).reorder(_chain2bits(bitchain, classifier.bit_width), match_type='lpm'))

    return subclassifiers


def maximize_coverage_bounded(classifiers, max_num_groups):
    """ Maximize the number of rules covered by the limited number of LPM groups.

    Args:
        classifiers: The set of original classifiers.
        max_num_groups: The maximal number of groups.

    Returns:
        The pair of LPM subclassifiers list and the leftover subclassifiers.
    """
    n_partitions, n_partition_indices = p4t_native.min_bmgr(classifiers, max_num_groups)

    subclassifiers = []
    traditionals = []
    for classifier, (partition, partition_indices) in zip(classifiers, zip(n_partitions, n_partition_indices)):
        remaining_indices = set(range(len(classifier)))

        for bitchain, indices in zip(partition, partition_indices):
            subclassifiers.append(classifier.subset(indices).reorder(_chain2bits(bitchain, classifier.bit_width)))
            remaining_indices -= set(indices)

        traditionals.append(classifier.subset(remaining_indices))

    return subclassifiers, traditionals


def minimize_oi_lpm(classifier, max_width, algo, max_num_groups,
                    max_expanded_bits=None, provide_non_expanded=False):
    """ Minimizes the number of subclassifiers, which are both LPM and OI.

    Args:
        classifier: Initial classifier.
        max_width: Maximal allowed classification width in the resulting subclassifiers.
        algo: Algorithm to use (Possible values 'icnp_oi', 'incp_blockers', 'min_similarity')
        max_num_groups: Maximal allowed number of subclassifiers.
        max_expanded_bits: Maximal allowed number of expanded bits.
        provide_non_expanded: Whether non-expanded versions should be returned.

    Returns:
        Pair of subclassifiers list and classifier with leftover rules. If
        provide_non_expanded is True, then the third element in a tuple  is
        a list of non-expanded classifiers.
    """
    assert max_expanded_bits is not None or not provide_non_expanded

    subclassifiers = []
    non_expanded_subclassifiers = []
    while len(classifier) > 0 and len(subclassifiers) < max_num_groups:
        p4t_native.log(
            "OI-LPM has started for group #{:d}".format(len(subclassifiers) + 1))

        oi_bits, oi_indices = p4t_native.best_subgroup(classifier, max_width, False, algo)
        oi_classifier = classifier.subset(oi_indices).reorder(oi_bits)

        if max_expanded_bits is None:
            [[bitchain]], [[lpm_indices]] = p4t_native.min_bmgr([oi_classifier], 1)
            subclassifiers.append(oi_classifier.subset(lpm_indices).reorder(_chain2bits(bitchain, oi_classifier.bit_width)))
        else:
            bitchain, lpm_indices, expansions = p4t_native.min_bmgr1_w_expansions(
                oi_classifier, max_expanded_bits)

            expanded = oi_classifier.subset([])
            for i, exp in zip(lpm_indices, expansions):
                for entry in expand(oi_classifier[i], exp):
                    expanded.vmr.append(entry)

            if provide_non_expanded:
                non_expanded_subclassifiers.append(
                    oi_classifier.subset(lpm_indices).reorder(
                        _chain2bits(bitchain, oi_classifier.bit_width)))

            subclassifiers.append(expanded.reorder(
                _chain2bits(bitchain, oi_classifier.bit_width)))

        classifier = classifier.subset(set(range(len(classifier))) - set(oi_indices[i] for i in lpm_indices))
    
        p4t_native.log("OI decomposition has finished")

    if provide_non_expanded:
        return subclassifiers, classifier, non_expanded_subclassifiers
    else:
        return subclassifiers, classifier


def decompose_oi(classifier, max_width, algo, only_exact=False, max_num_groups=None):
    """ Decomposes given classifier into a set of order-independent subclassifiers.

    Args:
        classifier: Initial classifier.
        max_width: Maximal allowed classification width in the resulting subclassifiers.
        algo: Algorithm to use (Possible values 'icnp_oi', 'incp_blockers', 'min_similarity')
        only_exact: Whether only exact bits should be allowed (False by default).
        max_num_groups: Maximal allowed number of subclassifiers.

    Returns:
        Pair of subclassifiers list and classifier with leftover rules.
    """

    p4t_native.log("OI decomposition has started: exact={:s}".format(str(only_exact)))

    subclassifiers = []
    while (max_num_groups is None or len(subclassifiers) < max_num_groups) and len(classifier) > 0:
        bits, indices = p4t_native.best_subgroup(classifier, max_width, only_exact, algo)
        subclassifiers.append(classifier.subset(indices).reorder(bits))
        classifier = classifier.subset(set(range(len(classifier))) - set(indices))

    p4t_native.log("OI decomposition has completed")

    return subclassifiers, classifier
