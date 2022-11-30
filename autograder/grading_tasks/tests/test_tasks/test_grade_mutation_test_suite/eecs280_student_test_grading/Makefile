CXX = g++
CXXFLAGS = -Wall -Werror -pedantic -O1 --std=c++11 -c

# Set these at the command line when running the buggy_impl target
student_test =
bug_name =
student_test_batch =

LD = g++
LDFLAGS = -Wall

student_tests.exe: student_tests.o unit_test_framework.o proj_module.o
	$(LD) $(LDFLAGS) $^ -o $@

student_tests_bug_%.exe: student_tests.o unit_test_framework.o proj_module_bug_%.o
	$(LD) $(LDFLAGS) $^ -o $@

proj_module_bug_%.o: proj_module.cpp
	$(CXX) $(CXXFLAGS) $(CPPFLAGS) $^ -o $@

%.o: %.cpp
	$(CXX) $(CXXFLAGS) $(CPPFLAGS) $^ -o $@

get_test_names:
	-@test -f student_tests.exe && ./student_tests.exe --show_test_names

%.validity_check: student_tests.exe
	./student_tests.exe $*

buggy_impl: CPPFLAGS += -D$(bug_name)
buggy_impl: student_tests_bug_$(bug_name).exe
	./student_tests_bug_$(bug_name).exe $(student_test)

buggy_impl_batch: CPPFLAGS += -D$(bug_name)
buggy_impl_batch: student_tests_bug_$(bug_name).exe
	./student_tests_bug_$(bug_name).exe $(student_test_batch)

.SECONDARY:

.PHONY: clean get_test_names buggy_impl
clean:
	rm -vf *.o *.exe
