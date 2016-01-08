FROM ubuntu:trusty

RUN apt-get update

RUN apt-get install -y g++ valgrind clang

RUN mkdir -p /home/autograder/working_dir

RUN useradd autograder && \
   mkdir -p /home/autograder/working_dir && \
   chown -R autograder:autograder /home/autograder

COPY timeout_script.py /usr/local/bin/timeout_script.py
RUN chmod 555 /usr/local/bin/timeout_script.py

WORKDIR /home/autograder/working_dir
