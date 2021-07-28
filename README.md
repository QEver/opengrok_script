# How To Use (on Ubuntu)



**NOTICE: This Script Only Support Python3**

### 1. install jre and get java version
```
$ apt-get install default-jre
$ java --version
```


### 2. download and start tomcat

if you are using java with version larger than 11, download tomcat10
```
$ wget https://mirrors.bfsu.edu.cn/apache/tomcat/tomcat-10/v10.0.8/bin/apache-tomcat-10.0.8.tar.gz
$ tar vxf apache-tomcat-10.0.8.tar.gz
$ ./apache-tomcat-10.0.8/bin/catalina.sh start
```
else if are using java with version smaller than 11, download tomcat8
```
$ wget https://mirrors.bfsu.edu.cn/apache/tomcat/tomcat-8/v8.5.69/bin/apache-tomcat-8.5.69.tar.gz
$ tar vxf apache-tomcat-8.5.69.tar.gz
$ ./apache-tomcat-8.5.69/bin/catalina.sh start
```


### 3. download and unpack opengrok

if you are using java with version larger than 11, download opengrok 1.7.13
```
$ wget https://github.com/oracle/opengrok/releases/download/1.7.13/opengrok-1.7.13.tar.gz
$ tar vxf opengrok-1.7.13.tar.gz
```
else if you are using java with version smaller than 11, please use opengrok 1.4.9
```
$ wget https://github.com/oracle/opengrok/releases/download/1.4.9/opengrok-1.4.9.tar.gz
$ tar vxf opengrok-1.4.9.tar.gz
```

### 4. clone and install Universal ctags

```
$ apt install autoconf pkg-config
$ git clone https://github.com/universal-ctags/ctags
$ cd ctags && ./autogen.sh && ./configure && make
```

### 5. clone and run script

```
$ git clone http://github.com/QEver/opengrok_script
$ cd opengrok_script && python opengrok.py -c ../ctags/ctags -w ../apache-tomcat-10.0.8/webapps -o ../opengrok-1.7.13 -s <source dir>
```
OR
```
$ git clone http://github.com/QEver/opengrok_script
$ cd opengrok_script && python opengrok.py -c ../ctags/ctags -w ../apache-tomcat-8.5.69/webapps -o ../opengrok-1.4.9 -s <source dir>
```

### 6. wait for script done and visit `http://localhost:8080/<source dir name>`
