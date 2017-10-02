int return42() {
    #if defined RETURN_42_BUG
    return 43;
    #elif defined INFINITE_LOOP_BUG
    while (true); return 42;
    #else
    return 42;
    #endif
}

bool return_true() {
    #if defined RETURN_TRUE_BUG
    return false;
    #else
    return true;
    #endif
}

int return3() {
    #if defined RETURN_3_BUG
    return 4;
    #else
    return 3;
    #endif
}
