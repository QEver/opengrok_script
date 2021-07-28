#!/usr/bin/env python3
import os
import stat
import time
import shutil
import urllib
import zipfile
import tempfile
import argparse
import subprocess

from lxml import etree
from urllib.request import urlopen
from urllib.error import HTTPError


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
        self.webapps_dir = None
        self.ctags_path = None
        self.opengrok_options = ['-H', '-S', '-G']
        self.java_options = ['-Xmx4096m']
        self.source_dir = None
        self.project_name = None
        self.need_login = False
        self.projects = False
        self.opengrok_jar = None
        self.source_war = None
        self.opengrok_data = None

    def check(self):
        if not os.path.exists(self.opengrok_dir):
            raise Exception('Can not found Opengrok in %s' % self.opengrok_dir)
        if not os.path.exists(self.opengrok_jar):
            raise Exception('Can not found opengrok.jar in %s' % self.opengrok_jar)
        if not os.path.exists(self.source_war):
            raise ('Can not found source.war in %s' % self.source_war)
        if not os.path.exists(self.webapps_dir):
            raise Exception('Can not found WebApps Dir in %s' % self.webapps_dir)
        if not os.path.exists(self.ctags_path):
            raise Exception('Can not found ctags in %s' % self.ctags_path)

    def show(self):
        print("[+] Opengrok Script Environment")
        if self.project_name:
            print('\tProject Name      : %s' % self.project_name)
        else:
            print('\tProject Name      : (Not Set)')
        print('\tOpenGrok Dir      : %s' % self.opengrok_dir)
        print('\tOpenGrok Options  : %s' % self.opengrok_options)
        print('\tOpenGrok Jar Path : %s' % self.opengrok_jar)
        print('\tOpenGrok Data Dir : %s' % self.opengrok_data)
        print('\tOpenGrok War Path : %s' % self.source_war)
        print('\tWebApps Dir       : %s' % self.webapps_dir)
        print('\tCtags Path        : %s' % self.ctags_path)
        print('\tNeed Login        : %s' % self.need_login)

    def set_ctags(self, ctags):
        self.ctags_path = ctags

    def set_webapps(self, webapps):
        self.webapps_dir = webapps

    def set_opengrok(self, opengrok):
        self.opengrok_dir = opengrok
        self.opengrok_jar = os.path.join(self.opengrok_dir, "lib/opengrok.jar")
        self.source_war = os.path.join(self.opengrok_dir, 'lib/source.war')
        if 'OPENGROK_DATA' in os.environ:
            self.opengrok_data = os.environ['OPENGROK_DATA']
        else:
            self.opengrok_data = os.path.join(self.opengrok_dir, "data")
        if not os.path.exists(self.opengrok_data):
            os.mkdir(self.opengrok_data)

    def set_source(self, src):
        self.source_dir = src

    def set_project_name(self, project_name):
        self.project_name = project_name

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
        cmd += '-U ' + self.env.tomcat_addr + '/' + name + ' '

        print('[+] Run Opengrok Script, Please Waiting ... ')
        r = os.system(cmd)
        if r == 0:
            print('[+] Run Opengrok Success!')
        else:
            print('[-] Failed to Run Opengrok!')

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
        print("[+] Waiting for url : %s" % url)
        s = False
        N = 30
        while True:
            try:
                r = urlopen(url)
                code = r.code
                r.close()
                N -= 1
            except HTTPError as e:
                code = e.code
            time.sleep(1)
            if code != 404:
                s = True
                break
        if s:
            print('[+] Url was created')
            return True
        else:
            print('[-] Failed to Created Url, check your tomcat settings')
            return False

    def update_root(self, name):
        target = os.path.join(self.env.webapps_dir, 'ROOT/index.html')
        line = '<a href="/%s" class="list-group-item">%s</a>\n' % (name, name)
        if os.path.exists(target):
            try:
                f = open(target, 'r')

                n = ''
                for i in f:
                    if i.find(line.strip()) != -1:
                        break
                    if i.find('<!--Source List-->') != -1:
                        n += line
                    n = n + i
                f.close()
                f = open(target, 'w')
                f.write(n)
                f.close()
            except Exception as e:
                print('[-] Update Root Failed : %s' % repr(e))

    def update_web_xml(self, webxml, name, login):
        configure = os.path.join(self.env.opengrok_data, name + '.xml')
        tree = etree.parse(webxml)
        root = tree.getroot()

        for i in root.getchildren():
            if 'context-param' in i.tag:
                f = False
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
            eles = self.login_config_elements()
            for i in eles:
                root.append(i)

        tree.write(webxml, pretty_print=True)

    def start(self):
        path = self.env.source_dir
        if not os.path.exists(path):
            raise Exception("%s is Not Exists" % path)

        path = os.path.abspath(path)

        if self.env.project_name:
            name = self.env.project_name
        else:
            name = os.path.basename(path)

        if not self.run_tomcat(name, self.env.need_login):
            return

        self.run_opengrok(path, name)
        
        self.update_root(name)

    @staticmethod
    def main():
        parser = argparse.ArgumentParser()
        parser.add_argument('-c', '--ctags', dest='ctags', required=True, help='ctags path')
        parser.add_argument('-w', '--webapps', dest='webapps', required=True, help='webapps directory of tomcat')
        parser.add_argument('-o', '--opengrok', dest='opengrok', required=True, help='opengrok directory')

        parser.add_argument('--source', '-s', dest='src_dir', default='.', help='source directory')
        parser.add_argument('--name', '-n', dest='project_name', default=None, help='repo name')
        parser.add_argument('--need-login', '-l', dest='need_login', action='store_true', default=False,
                            help='need login')
        parser.add_argument('--projects', '-p', dest='projects', action='store_true', default=False, help='as projects')

        opt = parser.parse_args()

        env = OpengrokScriptEnv()
        env.set_ctags(os.path.abspath(opt.ctags))
        env.set_webapps(os.path.abspath(opt.webapps))
        env.set_opengrok(os.path.abspath(opt.opengrok))

        env.set_source(os.path.abspath(opt.src_dir))
        env.set_project_name(opt.project_name)
        env.set_need_login(opt.need_login)
        env.set_projects(opt.projects)
        env.check()
        env.show()

        script = OpengrokScript(env)

        script.start()


if __name__ == '__main__':
    OpengrokScript.main()
