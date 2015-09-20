/* stats.cpp
 *
 * Simple statistics library
 *
 * EECS 280 Project 1
 *
 * Andrew DeOrio <awdeorio@umich.edu>
 * 2015-03-28
 */


#include "p1_library.h"
#include <vector>
#include <cassert>
#include <cmath> //sqrt, modf
#include <iostream> //cout
using namespace std;


void summarize(std::vector<double> v) {
  assert(!v.empty());
  sort(v);

  double value = v[0]; //counting occurrences of this value
  int count = 1;       //number of occurrences of current value
  for (int i=1; i<int(v.size()); i+=1) {
    if (v[i] != value) {
      cout << value << ": " << count << "\n";
      value = v[i];
      count = 0;
    }
    count += 1;
  }

  cout << value << ": " << count << "\n";
}

int count(vector<double> v) {
  return v.size();
}

double sum(vector<double> v) {
  assert(!v.empty());
  double sum = 0;
  for (int i=0; i<int(v.size()); ++i) sum += v[i];
  return sum;
}

double mean(vector<double> v) {
  assert(!v.empty());
  return sum(v) / v.size();
}

double mode(vector<double> v) {
  assert(!v.empty());
  sort(v);
  int mode_index = 0;
  int mode_count = 0;

  for (int i=0; i<int(v.size()); ++i) {
    int count = 0; // count how many copies of v[i] there are
    for (int j=i+1; j<int(v.size()); ++j) {
      if (v[i] != v[j]) break;
      count += 1;
    }
    if (count > mode_count) { //found new mode
      mode_index = i;
      mode_count = count;
    }
  }
  return v[mode_index];
}

double min(vector<double> v) {
  assert(!v.empty());
  double min = v[0];
  for (int i=0; i<int(v.size()); ++i) {
    if (v[i] < min) min = v[i];
  }
  return min;
}

double max(vector<double> v) {
  assert(!v.empty());
  double max = v[0];
  for (int i=0; i<int(v.size()); ++i) {
    if (v[i] > max) max = v[i];
  }
  return max;
}

double stdev(vector<double> v) {
  assert(!v.empty());
  double u = mean(v);
  double tmp = 0;
  for (int i=0; i<int(v.size()); ++i) {
    tmp += (v[i] - u)*(v[i] - u);
  }
  tmp = tmp / (v.size() - 1);
  tmp = sqrt(tmp);
  return tmp;
}

double percentile(vector<double> v, double p) {
  assert(!v.empty());
  assert(p >=0 && p <= 1);
  sort(v);
  double n = p*(v.size() - 1) + 1; //rank, indexed from 1
  double k = 0; //integer component
  double d = 0; //fractional component
  d = modf(n, &k); //SPEC GIVE EXAMPLE

  if (n == 0) return v[0];
  if (n == v.size()) return v[v.size() - 1];
  return v[k-1] + d*(v[k] - v[k-1]);
}

double median(vector<double> v) {
  assert(!v.empty());
  return percentile(v, 0.5);
}
