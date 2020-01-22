#!/usr/bin/env python3
import os
import stat
import re
import sys
from lxml import etree
import platform
import time
import shutil
import urllib
from urllib.request import urlopen
import subprocess
import tempfile
import zipfile


def run_cmd(cmd):
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE)
    data = p.communicate()
    return [i.decode() for i in data if i is not None]


TOMCAT_ADDR = "http://localhost:8080"

if platform.system() == 'Windows':
    OPENGROK_DIR = 'C:/Users/QEver/Tools/opengrok-0.13-rc4'
    TOMCAT_DIR = 'C:/Users/QEver/Tools/Tomcat 8.5'
    CTAGS_PATH = 'C:/Users/QEver/Tools/binary/ctags.exe'
elif platform.system() == 'Linux':
    cmd = ["whereis", "ctags"]
    CTAGS_PATH = run_cmd(cmd)[0].split(":")[1].strip().split(" ")[0]
    TOMCAT_DIR = '/var/lib/tomcat8'
    OPENGROK_DIR = os.path.expanduser('~/tools/opengrok')
elif platform.system() == 'Darwin':
    cmd = ['brew', '--prefix', 'tomcat@8']
    TOMCAT_DIR = run_cmd(cmd)[0].strip()
    TOMCAT_DIR = os.path.join(TOMCAT_DIR, 'libexec')
    OPENGROK_DIR = os.path.expanduser('~/tools/opengrok')
    cmd = ["brew", '--prefix', "universal-ctags"]
    CTAGS_PATH = os.path.join(run_cmd(cmd)[0].strip(), 'bin/ctags')
else:
    print("Unsupport Platform : ", platform.system())
    exit()


OPENGROK_OPTIONS = '-H -P -S -G'
JAVA_OPTIONS = '-Xmx4096m'
OPENGROK_JAR = os.path.join(OPENGROK_DIR, "lib/opengrok.jar")
WEBAPPS_DIR = os.path.join(TOMCAT_DIR, "webapps")
SOURCE_WAR = os.path.join(OPENGROK_DIR, 'lib/source.war')

if 'OPENGROK_DATA' in os.environ:
    OPENGROK_DATA = os.environ['OPENGROK_DATA']
else:
    OPENGROK_DATA = os.path.join(OPENGROK_DIR, "data")

if not os.path.exists(OPENGROK_DIR):
    print('Can not found Opengrok in %s' % OPENGROK_DIR)
    exit(0)
if not os.path.exists(OPENGROK_JAR):
    print('Can not found opengrok.jar in %s' % OPENGROK_JAR)
    exit(0)
if not os.path.exists(SOURCE_WAR):
    print('Can not found source.war in %s' % SOURCE_WAR)
    exit(0)
if not os.path.exists(TOMCAT_DIR):
    print('Can not found tomcat in %s' % TOMCAT_DIR)
    exit(0)
if not os.path.exists(WEBAPPS_DIR):
    print('Can not found WebApps Dir in %s' % WEBAPPS_DIR)
    exit(0)
if not os.path.exists(CTAGS_PATH):
    print('Can not found ctags in %s' % CTAGS_PATH)
    exit(0)
    
if not os.path.exists(OPENGROK_DATA):
    os.mkdir(OPENGROK_DATA)

print('OpenGrok Dir      : %s' % OPENGROK_DIR)
print('OpenGrok Options  : %s' % OPENGROK_OPTIONS)
print('OpenGrok Jar Path : %s' % OPENGROK_JAR)
print('OpenGrok Data Dir : %s' % OPENGROK_DATA)
print('OpenGrok War Path : %s' % SOURCE_WAR)
print()
print('Tomcat Dir  : %s' % TOMCAT_DIR)
print('WebApps Dir : %s' % WEBAPPS_DIR)
print()
print('Ctags Path : %s' % CTAGS_PATH)

def get_opengrok_version():
    cmd = 'java ' + JAVA_OPTIONS + ' -jar ' + OPENGROK_JAR + ' -V'
    vers = os.popen(cmd).read()
    regexp = 'OpenGrok (.+) rev'
    g = re.search(regexp, vers).groups()
    if len(g) != 1:
        raise Exception('Can not get version of opengrok\n, version data is : %s' % vers)
    return g[0]


def get_opengrok_indexer():
    return os.path.join(OPENGROK_DIR, 'bin/indexer.py')

def is_opengrok_has_indexer():
    path = get_opengrok_indexer()
    if os.path.exists(path):
        return True
    return False

'''
java -Djava.util.logging.config.file=/var/opengrok/logging.properties \
    -jar /opengrok/dist/lib/opengrok.jar \
    -c /path/to/universal/ctags \
    -s /var/opengrok/src -d /var/opengrok/data -H -P -S -G \
    -W /var/opengrok/etc/configuration.xml -U http://localhost:8080/source
'''

def run_opengrok(path, name):
    cmd = ''
    cmd += 'java ' + JAVA_OPTIONS + ' '
    cmd += '-Djava.util.logging.config.file=/var/opengrok/logging.properties' + ' '
    cmd += '-jar ' + OPENGROK_JAR + ' '
    cmd += '-c ' + CTAGS_PATH + ' '
    cmd += '-s ' + path + ' '
    cmd += '-d ' + os.path.join(OPENGROK_DATA, name) + ' '
    cmd += OPENGROK_OPTIONS + ' '
    cmd += '-W ' + os.path.join(OPENGROK_DATA, name + '.xml') + ' '
    cmd += '-U ' + TOMCAT_ADDR + '/' + name


    print(cmd)
    os.system(cmd)

def run_tomcat(name):
    webapps_dir = os.path.join(WEBAPPS_DIR, name)
    tmpdir = tempfile.TemporaryDirectory(prefix=name)

    zf = zipfile.ZipFile(SOURCE_WAR)

    zf.extractall(tmpdir.name)

    zf.close()

    webxml = os.path.join(tmpdir.name, 'WEB-INF', 'web.xml')
    update_web_xml(webxml, name)

    shutil.copytree(tmpdir.name, webapps_dir)
    os.chmod(webapps_dir, stat.S_IRWXU | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH)

    url = TOMCAT_ADDR + '/' + name
    while True:
        print("[*] Waiting for %s" % url)
        try:
            r = urlopen(url)
            code = r.code
            r.close()

        except urllib.error.HTTPError as e:
            code = e.code
        time.sleep(1)
        if code != 404:
            break


def update_root(name):
    target = os.path.join(WEBAPPS_DIR, 'ROOT/index.html')
    if os.path.exists(target):
        try:
            f = open(target, 'r')
            n = ''
            for i in f:
                n = n + i
                if i.find('<!--Source List-->') != -1:
                    n += '<a href="/%s" class="list-group-item">%s</a>\n' % (name, name)
            f.close()
            f = open(target, 'w')
            f.write(n)
            f.close()
        except:
            pass

   
def update_web_xml(webxml, name):
    configure = os.path.join(OPENGROK_DATA, name + '.xml')
    tree = etree.parse(webxml)
    root = tree.getroot()
    for i in root.getchildren(): 
        if 'context-param' in i.tag: 
            for j in i.getchildren(): 
                if 'param-name' in j.tag: 
                    if j.text == 'CONFIGURATION': 
                        f = True 
            if f: 
                for j in i.getchildren():  
                    if 'param-value' in j.tag: 
                        j.text = configure
                        break
                break
    tree.write(webxml, pretty_print=True)
                     

if __name__ == '__main__':
    path = '.'
    if len(sys.argv) > 1:
        path = sys.argv[1]

    path = os.path.abspath(path)
    if not os.path.exists(path):
        raise Exception("%s is Not Exists" % path)
    name = os.path.basename(path)

    run_tomcat(name)
    run_opengrok(path, name)
    update_root(name)
