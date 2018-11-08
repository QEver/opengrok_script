#!/usr/bin/python
import os
import re
import sys
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
    OPENGROK_DIR = os.path.expanduser('~/tools/opengrok-1.1-rc58')
elif platform.system() == 'Darwin':
    cmd = ['brew', '--prefix', 'tomcat@8.0']
    TOMCAT_DIR = run_cmd(cmd)[0].strip()
    TOMCAT_DIR = os.path.join(TOMCAT_DIR, 'libexec')
    OPENGROK_DIR = os.path.expanduser('~/tools/opengrok')
    cmd = ["whereis", "ctags"]
    CTAGS_PATH = run_cmd(cmd)[0].strip()
else:
    print "Unsupport Platform : ", platform.system()
    exit()


OPENGROK_OPTIONS = '-r on -a on -S -P -C'
JAVA_OPTIONS = '-Xmx4096m'
OPENGROK_DATA = os.path.join(OPENGROK_DIR, "data")
OPENGROK_JAR = os.path.join(OPENGROK_DIR, "lib/opengrok.jar")
WEBAPPS_DIR = os.path.join(TOMCAT_DIR, "webapps")
SOURCE_WAR = os.path.join(OPENGROK_DIR, 'lib/source.war')

if not os.path.exists(OPENGROK_DIR):
    print 'Can not found Opengrok in %s' % OPENGROK_DIR
    exit(0)
if not os.path.exists(OPENGROK_JAR):
    print 'Can not found opengrok.jar in %s' % OPENGROK_JAR
    exit(0)
if not os.path.exists(SOURCE_WAR):
    print 'Can not found source.war in %s' % SOURCE_WAR
    exit(0)
if not os.path.exists(TOMCAT_DIR):
    print 'Can not found tomcat in %s' % TOMCAT_DIR
    exit(0)
if not os.path.exists(WEBAPPS_DIR):
    print 'Can not found WebApps Dir in %s' % WEBAPPS_DIR
    exit(0)
if not os.path.exists(CTAGS_PATH):
    print 'Can not found ctags in %s' % CTAGS_PATH
    exit(0)
    
if not os.path.exists(OPENGROK_DATA):
    os.mkdir(OPENGROK_DATA)

print 'OpenGrok Dir      : %s' % OPENGROK_DIR
print 'OpenGrok Options  : %s' % OPENGROK_OPTIONS
print 'OpenGrok Jar Path : %s' % OPENGROK_JAR
print 'OpenGrok Data Dir : %s' % OPENGROK_DATA
print 'OpenGrok War Path : %s' % SOURCE_WAR
print
print 'Tomcat Dir  : %s' % TOMCAT_DIR
print 'WebApps Dir : %s' % WEBAPPS_DIR
print 
print 'Ctags Path : %s' % CTAGS_PATH


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


def run_opengrok(path, name):
    cmd = ''
    version = get_opengrok_version()
    if version > 'v1.1-rc11' and is_opengrok_has_indexer():
        indexer = get_opengrok_indexer()
        #./indexer.py -a ../lib/opengrok.jar -- -s /home/qever/source/v8/ -d ../data -W ../data/v8.xml -U http://localhost:8080
        cmd += indexer + ' '
        cmd += '-a ' + OPENGROK_JAR + ' -- '
    else:
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


def new_context_param(name, value):
    context = ET.Element('ns0:context-param')

    param_name = ET.Element('ns0:param-name')
    param_name.text = name
    param_value = ET.Element('ns0:param-value')
    param_value.text = value

    context.append(param_name)
    context.append(param_value)
    return context


def addto_webxml(xml, config, src_root, data_root):
    ET.register_namespace('', 'http://java.sun.com/xml/ns/javaee')
    ET.register_namespace('xsi', 'http://www.w3.org/2001/XMLSchema-instance')
    try:
        tree = ET.fromstring(xml)
    except ImportError,e:
        print e
        from xml.etree import ElementTree
        from elementtree import SimpleXMLTreeBuilder
        ElementTree.XMLTreeBuilder = SimpleXMLTreeBuilder.TreeBuilder
        tree = ET.fromstring(xml)


    for child in tree:
        if 'context-param' in child.tag:
            for i in child:
                if 'param-name' in i.tag:
                    if i.text == 'CONFIGURATION':
                        for j in child:
                            if 'param-value' in j.tag:
                                j.text = config
    
    src_root_elem = new_context_param('SRC_ROOT', src_root)
#    data = '''
#  <context-param>
#   <param-name>SRC_ROOT</param-name>
#   <param-value>%s</param-value>
#  </context-param>
#  ''' % src_root
#
#    e = ET.fromstring(data)
    data_root_elem = new_context_param('DATA_ROOT', data_root)
#    data = '''
#  <context-param>
#   <param-name>DATA_ROOT</param-name>
#   <param-value>%s</param-value>
#  </context-param>''' % data_root
#
#    t = ET.fromstring(data)

    tree.insert(3, src_root_elem)
    tree.insert(3, data_root_elem)

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
           

if __name__ == '__main__':
    if len(sys.argv) > 1:
        path = sys.argv[1]
    else:
        path = os.path.abspath(".")
    name = os.path.basename(path)

    run_tomcat(name, path)
    run_opengrok(path, name)
    
    update_root(name)
