#include "stats_test_utilities.h"
#include "stats.h"

#include <vector>
#include <cassert>

using std::vector;

int main()
{
    vector<double> data;
    for (int i = 0; i < 1001; ++i)
    {
      assert(count(data) == i);
      data.push_back(i);
    }
    return 0;
}
