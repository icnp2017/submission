import sys
import json
import argparse
from itertools import *

def _add_set_max_field_primitives(n, primitives):
    for k in range(1, n + 1):
        primitive = dict()
        primitive['num_args'] = k + 1
        primitive['properties'] = { 'dst' : { 
            'type' : [ 'field' ], 
            'access' : 'write' 
        }}
        primitive['args'] = ['dst'] + ['src{:d}'.format(l) for l in range(1, k + 1)]

        primitive['properties'].update({ arg : { 
            'type' : [ 'field', 'int', 'table_entry_data' ],
            'access' : 'read',
            'data_width' : 'dst'
            } for arg in primitive['args']
        })

        primitives['set_max_field_{:d}'.format(k)] = primitive

def _add_compress_primitives(n, primitives):
    for k in range(1, n + 1):
        primitive = dict()
        primitive['num_args'] = k + 1
        primitive['properties'] = { 'dst' : { 
            'type' : [ 'field' ], 
            'access' : 'write' 
        }}

        srcs = ['src{:d}'.format(l) for l in range(1, k + 1)]
        froms = ['from{:d}'.format(l) for l in range(1, k + 1)]
        tos = ['to{:d}'.format(l) for l in range(1, k + 1)]
        primitive['args'] = ['dst'] + list(chain(*izip(srcs, froms, tos)))

        primitive['properties'].update({ src : { 
            'type' : [ 'field' ],
            'access' : 'read',
            } for src in srcs
        })
        primitive['properties'].update({ var : {
            'type' : [ 'table_entry_data', 'int' ],
            'access' : 'read',
            } for var in chain(froms, tos)
        })

        primitives['compress_{:d}'.format(k)] = primitive

parser = argparse.ArgumentParser(description='primitives.json generator')
parser.add_argument('num_set_max', type=int)
parser.add_argument('num_compress', type=int)
parser.add_argument('-o')

if __name__ == '__main__':
    args = parser.parse_args()
    primitives = dict()
    _add_set_max_field_primitives(args.num_set_max, primitives)
    _add_compress_primitives(args.num_compress, primitives)
    with open(args.o, 'w') as f:
        json.dump(primitives, f)
