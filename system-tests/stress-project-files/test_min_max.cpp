#include "stats_test_utilities.h"
#include "stats.h"
#include "p1_library.h"

#include <vector>
#include <cassert>

using std::vector;

int main()
{
    vector<double> data;

    data.push_back(20);
    data.push_back(16);
    data.push_back(42);
    data.push_back(43.25);
    data.push_back(15.5);
    data.push_back(35);

    assert(doubles_equal(15.5, min(data)));
    assert(doubles_equal(43.25, max(data)));

    sort(data);

    assert(doubles_equal(15.5, min(data)));
    assert(doubles_equal(43.25, max(data)));
}
