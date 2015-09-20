#include "stats_test_utilities.h"
#include "stats.h"

#include <vector>
#include <cassert>

using std::vector;

int main()
{
  vector<double> data;
  double sum_so_far = 0;
  for (double i = 0; i < 100; i += 0.25)
  {
    sum_so_far += i;
    data.push_back(i);
    assert(doubles_equal(sum_so_far, sum(data)));
  }

  for (double i = -200; i < 0; i += 0.25)
  {
    sum_so_far += i;
    data.push_back(i);
    assert(doubles_equal(sum_so_far, sum(data)));
  }
}
