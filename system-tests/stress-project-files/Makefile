all : test

test : main stats-tests
	./stats-tests
	./main < main_test.in > main_test.out
	diff main_test.out main_test.out.correct

main : main.cpp stats.cpp p1_library.cpp
	g++ -Wall -Werror -pedantic -O2 main.cpp stats.cpp p1_library.cpp -o main

stats-tests : stats-tests.cpp stats.cpp p1_library.cpp
	g++ -Wall -Werror -pedantic -O2 stats-tests.cpp stats.cpp p1_library.cpp -o stats-tests

clean :
	rm -vf main stats-tests *~ *.out
