FROM ubuntu:trusty

RUN apt-get update

RUN apt-get install -y g++ valgrind clang mysql-server python3-pip 
RUN apt-get install -y libmysqlclient-dev
RUN apt-get install -y python3-dev
RUN pip3 install mysqlclient

RUN mkdir -p /home/autograder/working_dir

RUN useradd autograder && \
   mkdir -p /home/autograder/working_dir && \
   chown -R autograder:autograder /home/autograder

COPY timeout_script.py /usr/local/bin/timeout_script.py
RUN chmod 555 /usr/local/bin/timeout_script.py

COPY initialize_db.py /usr/local/bin/initialize_db
RUN chmod 550 /usr/local/bin/initialize_db

COPY reinitialize_db.py /usr/local/bin/reinitialize_db
RUN chmod 550 /usr/local/bin/reinitialize_db

WORKDIR /home/autograder/working_dir
