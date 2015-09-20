#include "stats_test_utilities.h"
#include "stats.h"

#include <vector>
#include <cassert>

using std::vector;

int main()
{
    vector<double> data;
    data.push_back(42.25);
    data.push_back(15);
    data.push_back(57);
    data.push_back(35.25);

    double expected = (35.25 + 42.25) / 2.;
    assert(doubles_equal(expected, median(data)));

    data.push_back(6);
    assert(doubles_equal(35.25, median(data)));
}
