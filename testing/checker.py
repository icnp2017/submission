from __future__ import print_function

import os.path
import functools
from itertools import islice
from collections import namedtuple

import click

from p4t.classifiers.simple import BasicClassifier
import p4t.optimizations.oi_lpm as opt

import parsing


GlobalParams = namedtuple('GlobalParams', ['max_entries', 'output_file'])
PARAMS = GlobalParams(None, 'data.tsv')

OIParams = namedtuple('OIParams', ['algo', 'cutoff', 'bit_width', 'only_exact'])
OI_PARAMS = OIParams('icnp_blockers', 20, 32, False)

LPMParams = namedtuple('LPMParams', ['max_groups', 'max_expanded_bits'])
LPM_PARAMS = LPMParams(None, None)

def add_row(kind, filename, num_entries, oi_algorithm,
            bit_width, max_groups, num_groups, num_entries_traditional, groups,
            max_expanded_bits, expanded_groups):
    with open(PARAMS.output_file, 'a') as f:
        print(kind, filename, PARAMS.max_entries, num_entries, oi_algorithm, bit_width,
              max_groups, num_groups, num_entries_traditional, sorted(groups, reverse=True) if groups is not None  else None,
              max_expanded_bits, sorted(expanded_groups, reverse=True) if expanded_groups is not None else None, sep='\t', file=f)


def read_classifier(filename):
    with open(filename, 'r') as input_file:
        classifier = parsing.read_classifier(
            parsing.classbench_expanded,
            islice(input_file, 0, PARAMS.max_entries)
        )
    return classifier


@click.group()
@click.option('--max-entries', default=PARAMS.max_entries, type=int,
              help='Maximal number of entries to take from the input')
@click.option('--output_file', default=PARAMS.output_file,
              help='File to store')
@click.option('--num-threads', default=None, type=int,
              help='Number of threads to use')
@click.option('--oi-cutoff', default=OI_PARAMS.cutoff, type=int,
              help='Maximal allowed number of groups in any OI invocation')
@click.option('--oi-algo', default=OI_PARAMS.algo, type=str,
              help='OI algorithm to use')
@click.option('--oi-bit-width', default=OI_PARAMS.bit_width, type=int,
              help='Required OI bit width')
@click.option('--oi-only-exact', help='Use only exact bits in OI?', is_flag=True)
@click.option('--lpm-max-groups', default=LPM_PARAMS.max_groups, type=int,
              help='Maximal allowed number of groups')
@click.option('--lpm-max-expanded-bits', default=LPM_PARAMS.max_expanded_bits, type=int,
              help='Maximal number of entries')
def greet(max_entries, output_file, num_threads,
          oi_cutoff, oi_algo, oi_bit_width, oi_only_exact,
          lpm_max_groups, lpm_max_expanded_bits):
    global PARAMS      # pylint: disable=global-statement
    global OI_PARAMS   # pylint: disable=global-statement
    global LPM_PARAMS  # pylint: disable=global-statement

    PARAMS = GlobalParams(max_entries=max_entries, output_file=output_file)
    OI_PARAMS = OIParams(
        cutoff=oi_cutoff, algo=str(oi_algo),
        only_exact=oi_only_exact, bit_width=oi_bit_width)
    LPM_PARAMS = LPMParams(max_groups=lpm_max_groups,
            max_expanded_bits=lpm_max_expanded_bits)

    if num_threads is not None:
        opt.set_number_of_threads(num_threads)

    print('Hey, we are gonna test some algos!!')


def do_optimize_oi(input_files, oi_params):
    kind = 'oi'
    kind += '' if not oi_params.only_exact else '_exact'

    for input_file in input_files:
        print("performing {:s} on {:s}: bitwidth = {:d}, algo = {:s}".format(
            kind, os.path.basename(input_file), oi_params.bit_width, oi_params.algo
            ))

        classifier = read_classifier(input_file)

        subclassifiers, traditional = opt.decompose_oi(
            classifier, oi_params.bit_width,
            oi_params.algo, oi_params.only_exact, oi_params.cutoff)

        add_row(kind, os.path.basename(input_file), len(classifier), oi_params.algo,
                oi_params.bit_width, None, len(subclassifiers), len(traditional),
                [len(s) for s in subclassifiers], None, None)


def do_optimize_oi_lpm_joint(input_files, oi_params, lpm_params):
    kind = 'oi_lpm_joint'

    if lpm_params.max_expanded_bits is not None:
        kind += "_exp"

    if lpm_params.max_groups is not None:
        kind += "_bounded"

    for input_file in input_files:
        print("performing {:s} on {:s}: bitwidth = {:d}, algo = {:s}{:s}{:s}".format(
            kind, os.path.basename(input_file), oi_params.bit_width, oi_params.algo,
            '' if lpm_params.max_groups is None else
            ', max_groups = {:d}'.format(lpm_params.max_groups),
            '' if lpm_params.max_expanded_bits is None else
            ', max_exp_bits = {:d}'.format(lpm_params.max_expanded_bits),
            ))

        classifier = read_classifier(input_file)

        max_groups = min(oi_params.cutoff, lpm_params.max_groups) \
            if lpm_params.max_groups is not None else oi_params.cutoff

        if lpm_params.max_expanded_bits is not None:
            subclassifiers, traditional, nexp_subclassifiers = opt.minimize_oi_lpm(
                classifier, oi_params.bit_width, oi_params.algo, max_groups,
                max_expanded_bits=lpm_params.max_expanded_bits,
                provide_non_expanded=True)
            add_row(kind, os.path.basename(input_file), len(classifier), oi_params.algo,
                    oi_params.bit_width, None, len(subclassifiers), len(traditional), [len(s) for s in nexp_subclassifiers],
                    lpm_params.max_expanded_bits, [len(s) for s in subclassifiers])
        else:
            subclassifiers, traditional = opt.minimize_oi_lpm(
                classifier, oi_params.bit_width, oi_params.algo, max_groups)

            add_row(kind, os.path.basename(input_file), len(classifier), oi_params.algo,
                    oi_params.bit_width, None, len(subclassifiers), len(traditional), [len(s) for s in subclassifiers],
                    None, None)


def do_optimize_oi_lpm(input_files, oi_params, lpm_params):
    kind = 'oi_lpm'
    assert lpm_params.max_expanded_bits is None

    if lpm_params.max_groups is not None:
        kind += "_bounded"

    for input_file in input_files:
        print("performing {:s} on {:s}: bitwidth = {:d}, algo = {:s}{:s}".format(
            kind, os.path.basename(input_file), oi_params.bit_width, oi_params.algo,
            '' if lpm_params.max_groups is None else
            ', max_groups = {:d}'.format(lpm_params.max_groups),
            ))

        classifier = read_classifier(input_file)

        subclassifiers, oi_traditional = opt.decompose_oi(
            classifier, oi_params.bit_width, oi_params.algo,
            only_exact=False, max_num_groups=oi_params.cutoff)

        all_group_sizes = []

        if lpm_params.max_groups is not None:
            subclassifiers, traditionals = opt.maximize_coverage_bounded(subclassifiers, lpm_params.max_groups)

            add_row(kind, os.path.basename(input_file), len(classifier), oi_params.algo,
                    oi_params.bit_width, lpm_params.max_groups, len(subclassifiers), 
                    len(oi_traditional) + sum(len(x) for x in traditionals), [len(s) for s in subclassifiers],
                    None, None)
        else:
            for subclassifier in subclassifiers:
                mgc = opt.minimize_num_groups(subclassifier)
                all_group_sizes.extend(len(s) for s in mgc)

            add_row(kind, os.path.basename(input_file), len(classifier), oi_params.algo,
                    oi_params.bit_width, None, len(all_group_sizes), len(oi_traditional), all_group_sizes,
                    None, None)


def do_optimize_lpm(input_files, lpm_params):
    kind = 'lpm' if lpm_params.max_groups is None else 'lpm_bounded'
    for input_file in input_files:
        print("performing lpm on {:s}{:s}".format(
            os.path.basename(input_file),
            "" if lpm_params.max_groups is None else ": max_groups = {:d}".format(lpm_params.max_groups)
            ))

        classifier = read_classifier(input_file)

        if lpm_params.max_groups is not None:
            subclassifiers, traditionals = opt.maximize_coverage_bounded([classifier], lpm_params.max_groups)
        else:
            subclassifiers, traditionals = opt.minimize_num_groups(classifier), []

        add_row(kind, os.path.basename(input_file), len(classifier), 'NA',
                classifier.bit_width, lpm_params.max_groups, len(subclassifiers), sum(len(x) for x in traditionals),
                [len(s) for s in subclassifiers], 'NA', [len(s) for s in subclassifiers])


def do_optimize_lpm_oi(input_files, oi_params):
    for input_file in input_files:
        print("performing lpm_oi on {:s}: bitwidth = {:d}, algo = {:s}".format(
            os.path.basename(input_file), oi_params.bit_width, oi_params.algo,
            ))

        classifier = read_classifier(input_file)

        mgc = opt.minimize_num_groups(classifier)

        all_group_sizes = []
        size_traditional = 0
        for pr_classifier in mgc:
            subclassifiers, traditional = opt.decompose_oi(
                pr_classifier, oi_params.bit_width,
                oi_params.algo, False, oi_params.oi_cutoff)
            all_group_sizes.extend(len(sc) for sc in subclassifiers)
            size_traditional += len(traditional)

        add_row('lpm_oi', os.path.basename(input_file), len(classifier), oi_params.algo,
                oi_params.bit_width, None, len(all_group_sizes), size_traditional, all_group_sizes)


@greet.command()
@click.argument('input_files', nargs=-1)
def optimize_oi(input_files):
    do_optimize_oi(input_files, OI_PARAMS)


@greet.command()
@click.argument('input_files', nargs=-1)
def optimize_oi_lpm(input_files):
    do_optimize_oi_lpm(input_files, OI_PARAMS, LPM_PARAMS)


@greet.command()
@click.argument('input_files', nargs=-1)
def optimize_oi_lpm_joint(input_files):
    do_optimize_oi_lpm_joint(input_files, OI_PARAMS, LPM_PARAMS)


@greet.command()
@click.argument('input_files', nargs=-1)
def optimize_lpm(input_files):
    do_optimize_lpm(input_files, LPM_PARAMS)


@greet.command()
@click.argument('input_files', nargs=-1)
def optimize_lpm_oi(input_files):
    do_optimize_lpm_oi(input_files, OI_PARAMS)


if __name__ == '__main__':
    greet()
