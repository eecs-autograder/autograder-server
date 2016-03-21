FROM ubuntu:trusty

RUN apt-get update --fix-missing

RUN apt-get install -y g++
RUN apt-get install -y valgrind
RUN apt-get install -y clang
    # mysql-server python3-pip
# RUN apt-get install -y libmysqlclient-dev
# RUN apt-get install -y python3-dev

RUN mkdir -p /home/autograder/working_dir

RUN useradd autograder && \
   mkdir -p /home/autograder/working_dir && \
   chown -R autograder:autograder /home/autograder

COPY timeout_script.py /usr/local/bin/timeout_script.py
RUN chmod 555 /usr/local/bin/timeout_script.py

WORKDIR /home/autograder/working_dir

# RUN apt-get install -y xvfb
# RUN apt-get install -y firefox
# RUN apt-get install -y dbus
# RUN apt-get install -y python3-lxml
# RUN pip3 install mysqlclient
# RUN pip3 install requests
# RUN pip3 install beautifulsoup4
# RUN pip3 install selenium
# RUN pip3 install pyvirtualdisplay
