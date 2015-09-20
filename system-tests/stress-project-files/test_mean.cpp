#include "stats_test_utilities.h"
#include "stats.h"

#include <vector>
#include <cassert>

using std::vector;

int main()
{
    vector<double> data;
    double sum_so_far = 0;
    for (int i = 0; i < 200; ++i)
    {
    data.push_back(i);
    sum_so_far += i;
    assert(doubles_equal(sum_so_far / data.size(), mean(data)));
    }

    for (int i = -400; i < 0; ++i)
    {
    data.push_back(i);
    sum_so_far += i;
    assert(doubles_equal(sum_so_far / data.size(), mean(data)));
    }
}
