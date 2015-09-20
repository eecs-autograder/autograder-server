/* p1_library.cpp
 *
 * Libraries needed for EECS 280 project 1
 *
 * by Andrew DeOrio <awdeorio@umich.edu>
 * 2015-04-28
 */

#include "p1_library.h"
#include <vector>
#include <string>
#include <iostream>
#include <fstream>
#include <sstream>
#include <algorithm>
using namespace std;


void sort(std::vector<double> &v) {
  std::sort(v.begin(), v.end());
}


std::vector<double> extract_column(std::string filename, std::string column_name) {

  // open file
  ifstream fin;
  fin.open(filename.c_str());
  if (!fin.is_open()) {
    cout << "Error opening " << filename << "\n";
    exit(1);
  }

  // read first line, which is the header
  string line;
  if (!getline(fin, line)) {
    cout << "Error reading " << filename << "\n";
    exit(1);
  }

  // search for column name in header, finding its index
  istringstream iss(line);
  int column_index = 0;
  string token;
  while (iss >> token) {
    if (token == column_name) break; //found it!
    column_index += 1;
  }

  // check for column name not found
  if (token != column_name) {
    cout << "Error: column name " << column_name << " not found in " << filename << "\n";
    exit(1); 
  }

  // extract column of data
  vector<double> column_data;
  int line_no = 2;
  while (getline(fin, line)) {
    istringstream iss(line);
    int i = 0;
    string token;
    while (getline(iss, token, '\t')) { //read one token, delimited by tabs
      if (i == column_index) break;
      i += 1;
    }

    if (i == column_index) {
      istringstream iss2(token); //convert to double
      double value = 0;
      iss2 >> value;
      column_data.push_back(value);
    } else {
      cout << "Warning: " << filename << ":" << line_no << " has no value for column " << column_name << "\n";
    }

    line_no += 1;
  }

  fin.close();
  return column_data;
}
