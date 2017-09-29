# ICNP 2017


## Prerequisites:

 1. [CMake](https://cmake.org/)
 2. [Boost](http://www.boost.org/)
 3. [Python 2.7](https://www.python.org/)
 4. [click](http://click.pocoo.org/5/) python package
 5. [p4c-bm](https://github.com/p4lang/p4c-bm)
 6. [behavioral-model](https://github.com/p4lang/behavioral-model)

## Preparations:

 1. Clone the repository:

    ```bash
    git clone https://github.com/icnp2017/submission.git
    ```

 2. Build the optimization engine:

    ```bash
    cd submission/p4_impl/p4t
    python setup.py build
    ```

 3. Switch to the testing directory and add built engine to `PYTHONPATH`:

    ```bash
    cd ../../testing
    source setenv.sh
    ```

## Running:

All data will be located in `data.tsv`, with the following columns:

 * algorithm's name,
 * classifier's name,
 * maximal number of entries taken from the classifier,
 * number of entries after the range expansion,
 * algorithm used for rule-disjoint decomposition,
 * required bit width,
 * maximal number of groups,
 * actual number of groups,
 * number of entries left for traditional representation,
 * sorted group sizes,
 * maximal number of expanded bits,
 * sorted groups sizes after expansion

Below are the command line parameters necessary to reproduce all simulation
results, presented in the paper.

  * To calculate values from Table 1 (l = 16, 24, 32, 64):

    ```bash
    python checker.py --oi-bit-width 24 --lpm-max-groups 10 \
        optimize_oi_lpm_joint ../test/*.txt
    ```

  * To calculate values from Table 1 (l = 104):

    ```bash
    python checker.py --lpm-max-groups 10 optimize_lpm  ../test/*.txt ```

  * To calculate values from Table 2:

    ```bash
    python checker.py --oi-bit-width 24 --lpm-max-groups 10 \
        --lpm-max-expanded-bits 4 optimize_oi_lpm_joint ../test/*.txt
    ```

  * To calculate values for the plots from Figure 4:
    
    ```bash
    python checker.py --oi-bit-width 24 optimize_oi_lpm_joint ../test/acl1.txt
    python checker.py optimize_oi_lpm ../test/acl1.txt
    ```

    The 10th column of the output contains the number of rules in each group.

 * To calculate values for the plots from Figure 5:

    ```bash
    python checker.py --oi-bit-width 32 optimize_oi ../test/acl1.txt
    python checker.py --oi-bit-width 32 --oi-only-exact optimize_oi ../test/acl1.txt
    python checker.py --oi-bit-width 32 optimize_oi_lpm_joint ../test/acl1.txt
    python checker.py --oi-bit-width 32 --lpm-max-expanded-bits 8 \
        optimize_oi_lpm_joint ../test/acl1.txt
    ```

    The 10th column of the output contains the number of rules in each group.

