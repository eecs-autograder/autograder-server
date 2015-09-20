#include "stats_test_utilities.h"
#include "stats.h"

#include <vector>
#include <cassert>

using std::vector;

int main()
{
    vector<double> data;

    data.push_back(2);
    data.push_back(1);
    data.push_back(42);
    data.push_back(43);

    assert(doubles_equal(23.68, stdev(data)));

    data.clear();

    data.push_back(2);
    data.push_back(12);
    data.push_back(8);
    data.push_back(10);
    data.push_back(6);
    data.push_back(4);

    assert(doubles_equal(3.74, stdev(data)));
}
