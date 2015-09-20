#include "stats_test_utilities.h"

#include <iostream>
#include <cmath>

using std::cout;
using std::endl;
using std::abs;

bool doubles_equal(double first, double second)
{
  cout << "first: " << first << " second: " << second << endl;
  return abs(first - second) < 0.01;
}
