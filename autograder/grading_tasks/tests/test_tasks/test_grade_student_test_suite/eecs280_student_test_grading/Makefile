CXX = g++
CXXFLAGS = -Wall -Werror -pedantic -O1 --std=c++11 -c
CPPFLAGS =

LD = g++
LDFLAGS = -Wall

student_tests.exe: student_tests.o unit_test_framework.o proj_module.o
	$(LD) $(LDFLAGS) $^ -o $@

%.o: %.cpp
	$(CXX) $(CXXFLAGS) $(CPPFLAGS) $^ -o $@

get_test_names:
	-@test -f student_tests.exe && ./student_tests.exe --show_test_names

%.validity_check: student_tests.exe
	./student_tests.exe $*

# When running a *.with_buggy_impl target, be sure to pas
# CPPFLAGS=-D<bug name> on the command line as well.
%.with_buggy_impl:
	rm -f proj_module.o student_tests.exe
	$(MAKE) student_tests.exe
	./student_tests.exe $*

.PHONY: clean get_test_names
clean:
	rm -vf *.o *.exe
