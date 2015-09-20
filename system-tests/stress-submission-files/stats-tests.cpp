/* stats-tests.cpp
 *
 * Unit tests for the simple statistics library
 *
 * EECS 280 Project 1
 *
 * EXTEND THE MAIN FUNCTION IN THIS FILE TO INCLUDE MORE COMPREHENSIVE TESTS!
 *
 * Protip #1: Write tests for the functions BEFORE you implement them!  For
 * example, write tests for median() first, and then write median().  It sounds
 * like a pain, but it helps make sure that you are never under the illusion
 * that your code works when it's actually full of bugs.
 *
 * Protip #2: Instead of putting all your tests in main(),  put each test case
 * in a function!
 */


#include "stats.h"
#include "p1_library.h"

#include <iostream>
#include <cassert>
#include <vector>
#include <cmath>

using namespace std;

bool doubles_equal(double first, double second);

void test_small_data_set();

void test_count();
void test_sum();
void test_mean();
void test_median();
void test_mode();
void test_min_max();
void test_stdev();
void test_percentile();

// Add prototypes for you test functions here.

int main() {
  // Here is a free test case!  They are woefully incomplete, but you can
  // model your tests after these.
  test_small_data_set();

  test_count();
  test_sum();
  test_mean();
  test_median();
  test_mode();
  test_min_max();
  test_stdev();
  test_percentile();

  return 0;
}

void test_small_data_set() {
  cout << "test_small_data_set" << endl;

  // create a simple vector
  vector<double> v;
  v.push_back(1);
  v.push_back(2);
  v.push_back(3);

  // test each function on vector
  assert(count(v) == 3);
  assert(sum(v) == 6);
  assert(mean(v) == 2);
  assert(median(v) == 2);
  assert(mode(v) == 1);
  assert(min(v) == 1);
  assert(max(v) == 3);
  assert(stdev(v) == 1);
  assert(percentile(v, 0.5) == 2);

  cout << "PASS!\n";
}// test_small_data_set

void test_count()
{
    vector<double> data;
    for (int i = 0; i < 1001; ++i)
    {
      assert(count(data) == i);
      data.push_back(i);
    }
}// test_count

void test_sum()
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
}// test_sum

void test_mean()
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
}// test_mean

void test_median()
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
}// test_median

void test_mode()
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
}// test_mode

void test_min_max()
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
}// test_min_max

void test_stdev()
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
}// test_stdev

void test_percentile()
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

//------------------------------------------------------------------------------

bool doubles_equal(double first, double second)
{
  cout << "first: " << first << " second: " << second << endl;
  return abs(first - second) < 0.01;
}

