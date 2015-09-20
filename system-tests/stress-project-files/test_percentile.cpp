#include "stats_test_utilities.h"
#include "stats.h"

#include <vector>
#include <cassert>

using std::vector;

int main()
{
    vector<double> data;

    data.push_back(2);
    data.push_back(6);
    data.push_back(10);
    data.push_back(12);
    data.push_back(8);
    data.push_back(4);
    data.push_back(15);
    data.push_back(19);
    data.push_back(23);
    data.push_back(35);
    data.push_back(27);
    data.push_back(32);
    data.push_back(22);
    data.push_back(14);

    assert(doubles_equal(2, percentile(data, 0)));
    assert(doubles_equal(3.3, percentile(data, 0.05)));
    assert(doubles_equal(4.6, percentile(data, 0.1)));
    assert(doubles_equal(5.9, percentile(data, 0.15)));
    assert(doubles_equal(7.2, percentile(data, 0.2)));
    assert(doubles_equal(8.5, percentile(data, 0.25)));
    assert(doubles_equal(9.8, percentile(data, 0.3)));
    assert(doubles_equal(11.1, percentile(data, 0.35)));
    assert(doubles_equal(12.4, percentile(data, 0.40)));
    assert(doubles_equal(13.7, percentile(data, 0.45)));
    assert(doubles_equal(14.5, percentile(data, 0.5)));
    assert(doubles_equal(15.6, percentile(data, 0.55)));
    assert(doubles_equal(18.2, percentile(data, 0.60)));
    assert(doubles_equal(20.35, percentile(data, 0.65)));
    assert(doubles_equal(22.1, percentile(data, 0.70)));
    assert(doubles_equal(22.75 , percentile(data, 0.75)));
    assert(doubles_equal(24.6, percentile(data, 0.80)));
    assert(doubles_equal(27.25, percentile(data, 0.85)));
    assert(doubles_equal(30.5, percentile(data, 0.90)));
    assert(doubles_equal(33.05, percentile(data, 0.95)));
    assert(doubles_equal(35, percentile(data, 1)));
}
