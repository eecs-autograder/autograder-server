CXX = g++
CXXFLAGS = -Wall -Werror -pedantic -O1 --std=c++11 -c

# Set this at the command line when running a *.buggy_impl target
valid_student_tests =

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

%.buggy_impl:
	rm -f proj_module.o student_tests.exe
	$(MAKE) CPPFLAGS=-D$* student_tests.exe
	./student_tests.exe $(valid_student_tests)

.PHONY: clean get_test_names
clean:
	rm -vf *.o *.exe
