FROM ubuntu

RUN apt-get update

RUN apt-get install -y g++ valgrind

RUN useradd autograder && \
    mkdir -p /home/autograder/working_dir && \
    chown -R autograder:autograder /home/autograder

WORKDIR /home/autograder/working_dir
