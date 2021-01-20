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
import argparse


class OpengrokUtils:
    @staticmethod
    def run_cmd(cmd):
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE)
        data = p.communicate()
        return [i.decode() for i in data if i is not None]


class OpengrokScriptEnv:
    def __init__(self):
        self.tomcat_addr = "http://localhost:8080"
        self.opengrok_dir = None
        self.tomcat_dir = None
        self.ctags_path = None
        self.opengrok_options = ['-H', '-S', '-G']
        self.java_options = ['-Xmx4096m']
        self.source_dir = None
        self.dst_name = None
        self.need_login = False
        self.projects = False
        self.init()

    def init(self):
        if platform.system() == 'Windows':
            self.opengrok_dir = 'C:/Users/QEver/Tools/opengrok-0.13-rc4'
            self.tomcat_dir = 'C:/Users/QEver/Tools/Tomcat 8.5'
            self.ctags_path = 'C:/Users/QEver/Tools/binary/ctags.exe'
        elif platform.system() == 'Linux':
            cmd = ["whereis", "-b", "ctags"]
            self.ctags_path = OpengrokUtils.run_cmd(cmd)[0].split(":")[1].strip().split(" ")[0]
            self.tomcat_dir = '/var/lib/tomcat8'
            self.opengrok_dir = os.path.expanduser('~/tools/opengrok')
        elif platform.system() == 'Darwin':
            cmd = ['brew', '--prefix', 'tomcat@8']
            self.tomcat_dir = OpengrokUtils.run_cmd(cmd)[0].strip()
            self.tomcat_dir = os.path.join(self.tomcat_dir, 'libexec')
            self.opengrok_dir = os.path.expanduser('~/tools/opengrok')
            cmd = ["brew", '--prefix', "universal-ctags"]
            self.ctags_path = os.path.join(OpengrokUtils.run_cmd(cmd)[0].strip(), 'bin/ctags')
        else:
            raise Exception("Unsupport Platform : %s" % platform.system())
        
        self.opengrok_jar = os.path.join(self.opengrok_dir, "lib/opengrok.jar")
        self.webapps_dir = os.path.join(self.tomcat_dir, "webapps")
        self.source_war = os.path.join(self.opengrok_dir, 'lib/source.war')

        if 'OPENGROK_DATA' in os.environ:
            self.opengrok_data = os.environ['OPENGROK_DATA']
        else:
            self.opengrok_data = os.path.join(self.opengrok_dir, "data")
        if not os.path.exists(self.opengrok_data):
            os.mkdir(self.opengrok_data)

    def check(self):
        if not os.path.exists(self.opengrok_dir):
            raise Exception('Can not found Opengrok in %s' % self.opengrok_dir)
        if not os.path.exists(self.opengrok_jar):
            raise Exception('Can not found opengrok.jar in %s' % self.opengrok_jar)
        if not os.path.exists(self.source_war):
            raise('Can not found source.war in %s' % self.source_war)
        if not os.path.exists(self.tomcat_dir):
            raise Exception('Can not found tomcat in %s' % self.tomcat_dir)
        if not os.path.exists(self.webapps_dir):
            raise Exception('Can not found WebApps Dir in %s' % self.webapps_dir)
        if not os.path.exists(self.ctags_path):
            raise Exception('Can not found ctags in %s' % self.ctags_path)

    def show(self):
        print('OpenGrok Dir      : %s' % self.opengrok_dir)
        print('OpenGrok Options  : %s' % self.opengrok_options)
        print('OpenGrok Jar Path : %s' % self.opengrok_jar)
        print('OpenGrok Data Dir : %s' % self.opengrok_data)
        print('OpenGrok War Path : %s' % self.source_war)
        print()
        print('Tomcat Dir  : %s' % self.tomcat_dir)
        print('WebApps Dir : %s' % self.webapps_dir)
        print()
        print('Ctags Path : %s' % self.ctags_path)

    def set_source(self, src):
        self.source_dir = src

    def set_dst_name(self, dst_name):
        self.dst_name = dst_name

    def set_need_login(self, need_login):
        self.need_login = need_login

    def set_projects(self, projects):
        self.projects = projects
        if self.projects:
            self.opengrok_options.append('-P')

class OpengrokScript:
    def __init__(self, env):
        self.env = env

    def run_opengrok(self, path, name):
        cmd = ''
        cmd += 'java ' + ' '.join(self.env.java_options) + ' '
        cmd += '-Djava.util.logging.config.file=/var/opengrok/logging.properties' + ' '
        cmd += '-jar ' + self.env.opengrok_jar + ' '
        cmd += '-c ' + self.env.ctags_path + ' '
        cmd += '-s ' + path + ' '
        cmd += '-d ' + os.path.join(self.env.opengrok_data, name) + ' '
        cmd += ' '.join(self.env.opengrok_options) + ' '
        cmd += '-W ' + os.path.join(self.env.opengrok_data, name + '.xml') + ' '
        cmd += '-U ' + self.env.tomcat_addr + '/' + name

        print(cmd)
        os.system(cmd)

    def login_config_elements(self):
        eles = []
        text = '''
            <security-constraint>
            <web-resource-collection>                                               
                <web-resource-name>API endpoints are checked separately by the web app</web-resource-name>
                <url-pattern>/api/*</url-pattern>                                   
            </web-resource-collection>                                              
            </security-constraint>
        '''
        eles.append(etree.fromstring(text))
        text = '''
            <security-constraint>
                <web-resource-collection>
                    <web-resource-name>In general everything needs to be authenticated</web-resource-name>
                    <url-pattern>/*</url-pattern> <!-- protect the whole application -->
                    <url-pattern>/api/v1/search</url-pattern> <!-- protect search endpoint whitelisted above -->
                    <url-pattern>/api/v1/suggest/*</url-pattern> <!-- protect suggest endpoint whitelisted above -->
                </web-resource-collection>

                <auth-constraint>
                    <role-name>*</role-name>
                </auth-constraint>

                <user-data-constraint>
                    <!-- transport-guarantee can be CONFIDENTIAL, INTEGRAL, or NONE -->
                    <transport-guarantee>NONE</transport-guarantee>
                </user-data-constraint>
            </security-constraint>
        '''
        eles.append(etree.fromstring(text))
        text = '''
            <security-role>
                <role-name>*</role-name>
            </security-role>
        '''
        eles.append(etree.fromstring(text))
        text = '''
            <login-config>
                <auth-method>BASIC</auth-method>
            </login-config>
        '''
        eles.append(etree.fromstring(text))
        
        return eles


    def run_tomcat(self, name, login):
        webapps_dir = os.path.join(self.env.webapps_dir, name)
        tmpdir = tempfile.TemporaryDirectory(prefix=name)

        zf = zipfile.ZipFile(self.env.source_war)

        zf.extractall(tmpdir.name)

        zf.close()

        webxml = os.path.join(tmpdir.name, 'WEB-INF', 'web.xml')
        self.update_web_xml(webxml, name, login)
        if os.path.exists(webapps_dir):
            shutil.rmtree(webapps_dir)
            
        shutil.copytree(tmpdir.name, webapps_dir)
        os.chmod(webapps_dir, stat.S_IRWXU | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH)

        url = self.env.tomcat_addr + '/' + name
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


    def update_root(self, name):
        target = os.path.join(self.env.webapps_dir, 'ROOT/index.html')
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


    def update_web_xml(self, webxml, name, login):
        configure = os.path.join(self.env.opengrok_data, name + '.xml')
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
        if (login):
            eles = login_config_elements()
            for i in eles:
                root.append(i)
                
        tree.write(webxml, pretty_print=True)

    def start(self):
        path = self.env.source_dir
        if not os.path.exists(path):
            raise Exception("%s is Not Exists" % path)

        path = os.path.abspath(path)
        
        if self.env.dst_name:
            name = self.env.dst_name
        else:
            name = os.path.basename(path)

        self.run_tomcat(name, self.env.need_login)
        self.run_opengrok(path, name)
        self.update_root(name)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', '-s', dest='src_dir', default='.', help='source directory')
    parser.add_argument('--name', '-n', dest='dst_name', default=None, help='repo name')
    parser.add_argument('--need-login', '-l', dest='need_login', action='store_true', default=False, help='need login')
    parser.add_argument('--projects', '-p', dest='projects', action='store_true', default=False, help='as projects')

    opt = parser.parse_args()

    env = OpengrokScriptEnv()
    env.set_source(opt.src_dir)
    env.set_dst_name(opt.dst_name)
    env.set_need_login(opt.need_login)
    env.set_projects(opt.projects)
    
    env.show()

    script = OpengrokScript(env)

    script.start()


if __name__ == '__main__':
    main()
