#include "stats_test_utilities.h"
#include "stats.h"

#include <vector>
#include <cassert>

using std::vector;

int main()
{
    vector<double> data;

    for (int i = 0; i < 10; ++i)
    {
    data.push_back(42.25);
    assert(doubles_equal(42.25, mode(data)));

    data.push_back(12);
    assert(doubles_equal(12, mode(data)));
    }

    data.push_back(75);
    assert(doubles_equal(12, mode(data)));
}
