from __future__ import division

from collections import defaultdict
import csv

import click
import numpy as np
import matplotlib.pyplot as plt

def to_instance_name(fname, width):
    return '{}_{}'.format(fname, width)


@click.command()
@click.option('--data', default='data.tsv', help='Where testing results are located')
def test(data):
    kinds = ['oi', 'oi_exact', 'oi_lpm_joint', 'oi_lpm_joint_exp']
    widths = ['32']
    #files = ['fw1.txt', 'fw2.txt', 'fw3.txt', 'fw4.txt', 'fw5.txt']
    #files = ['ipc1.txt', 'ipc2.txt']
    files = ['acl1.txt', 'acl2.txt', 'acl3.txt', 'acl4.txt', 'acl5.txt']


    plots = defaultdict(dict)
    with open(data, 'rb') as datatsv:
        results_reader = csv.reader(datatsv, delimiter='\t')
        for row in results_reader:
            kind, fname, width, rest, groups = row[0], row[1], row[5], row[8], row[9]
            rest, groups = int(rest), eval(groups)

            plots[to_instance_name(fname, width)][kind] = {
                'total': sum(groups) + rest,
                'rest': rest,
                'groups': groups
            }

    
    colors = ['r', 'g', 'b', 'm']
    for w_idx, width in enumerate(widths):
        for f_idx, fname in enumerate(files):
            plt.subplot(
                len(widths), len(files), f_idx * len(widths) + w_idx + 1
            )
            plt.title(to_instance_name(fname, width))
            plt.xlabel('Number of groups')
            plt.ylabel('Coverage, %')

            x = list(range(21))
            for k_idx, kind in enumerate(kinds):
                data = plots[to_instance_name(fname, width)][kind]
                y = [100 * sum(data['groups'][:i]) / data['total'] for i in range(21)]
                plt.plot(x, y, label=kind, color=colors[k_idx] , marker='+')
            plt.legend()
            plt.grid(True)
    plt.show()

if __name__ == '__main__':
    test()
