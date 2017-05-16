# ICNP 2017


## Prerequisites:

 1. [CMake](https://cmake.org/)
 2. [Boost](http://www.boost.org/)
 3. [Python 2.7](https://www.python.org/)
 4. [click](http://click.pocoo.org/5/) python package
 5. [p4c-bm](https://github.com/p4lang/p4c-bm)
 6. [behavioral-model](https://github.com/p4lang/behavioral-model)

## Steps to reproduce:

 1. Clone [repo](https://github.com/icnpconf/submission).
 2. __Switch__ to the cloned folder and then to the `p4t` folder:

     ```bash
     python setup.py build
     ```

 4. To calculate Table 1 (l = 16, 24, 32, 64) and Table 2 run:

     ```bash
     python checker.py optimize_for_paper \
         --bit-width 16 --bit-width 24 --bit-width 32 --bit-width 64 \
         --max-expanded-bits 4 --max-expanded-bits 8 test/*.txt
     ```

 6. To calculate Table 1 (l = 104) run:

     ```bash
     python checker.py optimize_lpm test/*.txt
     ```

All data will be located in `data.tsv`.
