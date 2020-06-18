#include "unit_test_framework.h"
#include "proj_module.h"


TEST(test_return_42) {
    ASSERT_EQUAL(return42(), 42);
}

TEST(test_return_true) {
    ASSERT_TRUE(return_true());
}

TEST(incorrectly_test_return3) {
    ASSERT_EQUAL(return3(), 8);
}

TEST(this_test_times_out) {
    while (true);
}

TEST_MAIN()
