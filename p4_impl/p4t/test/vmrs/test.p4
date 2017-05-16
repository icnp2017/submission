parser start {
    return ingress;
}

control ingress {
    apply(test_table);
    apply(test_aux_table);
}

header_type test_t {
    fields {
        a : 1;
        b : 2;
        c : 32;
    }
}

metadata test_t test;

action test_action(x) {
    modify_field(test.c, x);
}

table test_table {
    reads {
        test.a : lpm;
        test.b : lpm;
    }
    actions {
        test_action;
    }
    size: 1024;
}

table test_aux_table {
    reads {
        test.a : lpm;
        test.b : lpm;
    }
    actions {
        test_action;
    }
    size: 1024;
}
