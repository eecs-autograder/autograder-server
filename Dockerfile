FROM ubuntu 

RUN apt-get update

RUN apt-get install -y g++ valgrind

RUN useradd autograder && mkdir /home/autograder && chown autograder:autograder /home/autograder

