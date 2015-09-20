/* main.cpp
 * 
 * Command line statistics program
 *
 * EECS 280 Project 1
 *
 * Andrew DeOrio <awdeorio@umich.edu>
 * 2015-03-28
 */

#include "stats.h"
#include "p1_library.h"
#include <iostream>
#include <string>
#include <vector>
using namespace std;

int main() {
  // ask user for filename
  cout << "enter a filename\n";
  string filename;
  cin >> filename;
  
  // ask user for column_name
  cout << "enter a column name\n";
  string column_name;
  cin >> column_name;

  // extract column of data from file corresponding to column_name
  cout << "reading column " << column_name << " from " << filename << "\n";
  vector<double> v = extract_column(filename, column_name);

  // print the dataset
  cout << "Summary (value: frequency)\n";
  summarize(v);
  cout << "\n";

  cout << "count = " << count(v) << "\n"
       << "sum = " << sum(v) << "\n"
       << "mean = " << mean(v) << "\n"
       << "stdev = " << stdev(v) << "\n"
       << "median = " << median(v) << "\n"
       << "mode = " << mode(v) << "\n"
       << "min = " << min(v) << "\n"
       << "max = " << max(v) << "\n"
       << "  0th percentile = " << percentile(v, 0.0) << "\n"
       << " 25th percentile = " << percentile(v, 0.25) << "\n"
       << " 50th percentile = " << percentile(v, 0.50) << "\n"
       << " 75th percentile = " << percentile(v, 0.75) << "\n"
       << "100th percentile = " << percentile(v, 1.0) << "\n"
    ;
}
