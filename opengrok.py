#! /bin/python
import os
import sys
import shutil
import platform
import zipfile
import subprocess
import xml.etree.ElementTree as ET

def run_cmd(cmd):
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE)
    data = p.communicate()
    return data

if platform.system() == 'Windows':
    OPENGROK_DIR = 'C:/Users/QEver/Tools/opengrok-0.13-rc4'
    TOMCAT_DIR = 'C:/Users/QEver/Tools/Tomcat 8.5'
    CTAGS_PATH = 'C:/Users/QEver/Tools/binary/ctags.exe'
elif platform.system() == 'Linux':
    cmd = ["whereis", "ctags"]
    CTAGS_PATH = run_cmd(cmd)[0].split(":")[1].strip().split(" ")[0]
    TOMCAT_DIR = '/var/lib/tomcat8'
    OPENGROK_DIR = '/home/qever/tools/opengrok'

OPENGROK_OPTIONS = '-r on -a on -S -P -C'
JAVA_OPTIONS = '-Xmx4096m'
OPENGROK_DATA = os.path.join(OPENGROK_DIR, "data")
OPENGROK_JAR = os.path.join(OPENGROK_DIR, "lib/opengrok.jar")
WEBAPPS_DIR = os.path.join(TOMCAT_DIR, "webapps")
SOURCE_WAR = os.path.join(OPENGROK_DIR, 'lib/source.war')



def run_opengrok(path, name):
    cmd = ''
    cmd += 'java ' + JAVA_OPTIONS + ' '
    cmd += '-jar ' + OPENGROK_JAR + ' '
    cmd += OPENGROK_OPTIONS + ' '
    cmd += '-c ' + CTAGS_PATH + ' '
    cmd += '-w ' + name +' '
    cmd += '-W ' + os.path.join(OPENGROK_DATA, name + '.xml') + ' '
    cmd += '-d ' + os.path.join(OPENGROK_DATA, name) + ' '
    cmd += '-s ' + path

    print cmd
    os.system(cmd)


def addto_webxml(xml, config, src_root, data_root):
    ET.register_namespace('', 'http://java.sun.com/xml/ns/javaee')
    ET.register_namespace('xsi', 'http://www.w3.org/2001/XMLSchema-instance')
    tree = ET.fromstring(xml)

    for child in tree:
        if 'context-param' in child.tag:
            for i in child:
                if 'param-name' in i.tag:
                    if i.text == 'CONFIGURATION':
                        for j in child:
                            if 'param-value' in j.tag:
                                j.text = config

    data = '''
  <context-param>
   <param-name>SRC_ROOT</param-name>
   <param-value>%s</param-value>
  </context-param>
  ''' % src_root

    e = ET.fromstring(data)

    data = '''
  <context-param>
   <param-name>DATA_ROOT</param-name>
   <param-value>%s</param-value>
  </context-param>''' % data_root

    t = ET.fromstring(data)

    tree.insert(3, e)
    tree.insert(3, t)

    return ET.tostring(tree, method='xml')

def configure_xml_name(name):
    return os.path.join(OPENGROK_DATA, name + '.xml')

def data_root_path(name):
    return os.path.join(OPENGROK_DATA, name)


def run_tomcat(name, dir):
    if not zipfile.is_zipfile(SOURCE_WAR):
        print '%s is not a zip file!' % SOURCE_WAR
        raise

    zf = zipfile.ZipFile(SOURCE_WAR)
    zf.extractall(os.path.join(WEBAPPS_DIR,name))
    f = zf.open(r'WEB-INF/web.xml', 'r')
    xml = f.read()
    f.close()
    zf.close()

    new = addto_webxml(xml, configure_xml_name(name), dir, data_root_path(name))

    f = open(os.path.join(WEBAPPS_DIR, name, "WEB-INF/web.xml"), "w")
    f.write(new)
    f.close()


if __name__ == '__main__':
    if len(sys.argv) > 1:
        path = sys.argv[1]
    else:
		path = os.path.abspath(".")
    name = os.path.basename(path)

    run_tomcat(name, path)
    run_opengrok(path, name)