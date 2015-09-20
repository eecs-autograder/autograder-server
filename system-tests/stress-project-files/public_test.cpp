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
#include <iostream>
#include <cassert>
#include <vector>
using namespace std;

void test_small_data_set();

// Add prototypes for you test functions here.

int main() {
  // Here is a free test case!  They are woefully incomplete, but you can
  // model your tests after these.
  test_small_data_set();

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

// Add the test function implementations here.
