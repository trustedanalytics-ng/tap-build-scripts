#
# Copyright (c) 2016 Intel Corporation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

DOCUMENTATION = ''' |
---
module: tap_component
short_description: Builds TAP components.
description: Idempotency is provided by checking special commit file, which stores
component commit hash. Commit file is created in component directory after successful build. If commit file is
not present, or it's content doesn't represent current commit in component's repository, component will be rebuilded.

Handling proxy
Pass following parameter:
proxy_settings:
  http_proxy: <http_proxy>

in module invocation in order to pass proxy settings to build commands.
For Maven components, please configure proxy settings before running 
this module.

Copying files in proper destinations before component build
Pass following parameter:
copy_files:
- src: <dependency file location>
  dest: <dependency file destination>
'''

COMMIT_FILE_NAME = '.tap_component_build.txt'
DATA_CATALOG_BUILD_TAG = 'tapimages:8080/data-catalog-build'
GRADLE_TOMCAT_URL = 'http://repo2.maven.org/maven2/org/apache/tomcat/tomcat/7.0.70/tomcat-7.0.70.tar.gz'
GRADLE_TOMCAT_PACKAGE_NAME = 'apache-tomcat-7.0.70.tar.gz'


# Status returned, when component is already build.
NOTHING_TO_CHANGE = {'success': True}

import os
import glob
import subprocess
import threading


from ansible.module_utils.basic import AnsibleModule

class BuildRunner:
    timeout_mins = 30

    @staticmethod
    def call_build_command(cmd, path):
        if is_component_already_build(path):
            return NOTHING_TO_CHANGE

        output = ''
        try:
            build_process = subprocess.Popen(cmd, cwd=path, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            timer = threading.Timer(BuildRunner.timeout_mins*60, build_process.terminate)
            try:
                timer.start()
                output, err = build_process.communicate()
            finally:
                timer.cancel()
            if build_process.returncode != 0:
                raise subprocess.CalledProcessError(cmd, build_process.returncode)

        except subprocess.CalledProcessError:
            # Assume that process is killed by threading.Timer, if no output is received
            if not output:
                output = 'Timeout ({0} min.) exceeded.'.format(BuildRunner.timeout_mins)
            return {'success': False, 'output': output}

        return {'success': True, 'output': output}


def get_commit_hash(path):
    return subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=path)

def create_commit_file(path):
    """
    :param path: Path to directory, where commit file will be created.
    """
    with open(os.path.join(path, COMMIT_FILE_NAME), "w") as commit_file:
        commit_file.write(get_commit_hash(path))

def is_component_already_build(path):
    """
    :param path: Path to component's directory.
    :return: True, if current hash is the same as in last successful build, False otherwise.
    """
    commit_file_path = os.path.join(path, COMMIT_FILE_NAME)
    if not os.path.isfile(commit_file_path):
        return False

    with open(commit_file_path, "r") as commit_file:
        return commit_file.read() == get_commit_hash(path)

def call_pipelined_command(cmd):
    try:
        return_code = subprocess.call(cmd, shell=True)
        if return_code != 0:
            raise subprocess.CalledProcessError(cmd, return_code)

    except subprocess.CalledProcessError:
        return {'success': False, 'output': return_code}

    return {'success': True, 'output': return_code}

def call_build_command_chain(*build_commands):
    build_result = {}
    for build_command in build_commands:
        build_result = build_command()
        if build_result == NOTHING_TO_CHANGE or not build_result['success']:
            break

    return build_result

def get_proxy_host(http_proxy):
    return http_proxy.split(':')[1].replace('//', '')

def get_proxy_port(http_proxy):
    return http_proxy.split(':')[2]

def build_maven(path, skip_tests=True, goals='clean package docker:build'):
    command = ['mvn', '-B']
    command.extend(goals.split())
    if skip_tests:
        command.append('-Dmaven.test.skip=true')

    return BuildRunner.call_build_command(command, path)

def build_pack_sh(path):
    return BuildRunner.call_build_command(['bash', 'pack.sh'], path)

def build_console(path):
    return BuildRunner.call_build_command(['sudo', 'PATH={0}'.format(os.environ['PATH']), 'bash', 'pack.sh'], path)

def build_rpm(path):
    return call_pipelined_command('cd {} && make build_rpm PKG_VERSION=TAP'.format(path))

def build_go_exe(path):
    return BuildRunner.call_build_command(['make', 'build_anywhere'], path)

def build_data_catalog(path, proxy_settings=None):
    docker_build_cmd = ['docker', 'build', '-t', DATA_CATALOG_BUILD_TAG]
    if proxy_settings and proxy_settings.get('http_proxy'):
        docker_build_cmd.extend(['--build-arg',
                                 'HTTP_PROXY={0}'.format(proxy_settings['http_proxy'])])
    docker_build_cmd.append('build-image/')

    return call_build_command_chain(lambda: BuildRunner.call_build_command(docker_build_cmd, path),
                                    lambda: BuildRunner.call_build_command(['bash', 'archive-deps.sh'], path),
                                    lambda: BuildRunner.call_build_command(['bash', 'pack.sh'], path))

def build_auth_gateway(path, skip_tests):
    package_cmd = ['mvn', '-B', 'clean', 'package']
    if skip_tests:
        package_cmd.append('-Dmaven.test.skip=true')

    return call_build_command_chain(lambda: BuildRunner.call_build_command(package_cmd, path),
                                    lambda: BuildRunner.call_build_command(['mvn', '-B', '-f',
                                                                os.path.join(path, 'auth-gateway-engine/pom.xml'),
                                                                'docker:build'],
                                                               path))

def build_gradle(path, skip_tests, proxy_settings=None):
    gradle_cmd = ['./gradlew', 'build']
    if skip_tests:
        gradle_cmd.extend(['-x', 'test'])
    if proxy_settings and proxy_settings.get('http_proxy'):
        gradle_cmd.extend(['-Dhttp.proxyHost={0}'.format(get_proxy_host(proxy_settings['http_proxy'])),
                           '-Dhttp.proxyPort={0}'.format(get_proxy_port(proxy_settings['http_proxy']))])

    return call_build_command_chain(
        lambda: BuildRunner.call_build_command(['wget', GRADLE_TOMCAT_URL, '-O', GRADLE_TOMCAT_PACKAGE_NAME],
                                   path),
        lambda: BuildRunner.call_build_command(gradle_cmd, path))

def build_tap_metrics(path, proxy_settings=None):
    build_anywhere_cmd = ['bash', 'build_anywhere.sh']
    if proxy_settings and proxy_settings.get('http_proxy'):
        build_anywhere_cmd.append('build_arg_HTTP_PROXY={0}'.format(proxy_settings['http_proxy']))

    return call_build_command_chain(lambda: BuildRunner.call_build_command(build_anywhere_cmd, path),
                                    lambda: BuildRunner.call_build_command(['bash', 'build_docker_images.sh'], path))

def build_tap_blob_store(path, proxy_settings=None):
    build_blob_store_cmd = ['docker', 'build', '-t', 'tap-blob-store']
    build_minio_cmd = ['docker', 'build', '-t', 'tap-blob-store/minio']
    if proxy_settings and proxy_settings.get('http_proxy'):
        build_blob_store_cmd.append('build_arg_HTTP_PROXY={0}'.format(proxy_settings['http_proxy']))
        build_minio_cmd.append('build_arg_HTTP_PROXY={0}'.format(proxy_settings['http_proxy']))
    build_blob_store_cmd.append('.')
    build_minio_cmd.append('minio/')

    return call_build_command_chain(lambda: build_pack_sh(path),
                                    lambda: BuildRunner.call_build_command(build_blob_store_cmd, path),
                                    lambda: BuildRunner.call_build_command(build_minio_cmd, path))

def copy_files(files):
    for file in files:
        src = file['src']
        dest = file['dest']
        if not os.path.isdir(dest):
            os.makedirs(dest)

        if os.path.isfile(src):
            cmd = ['cp', src, dest]
        elif os.path.isdir(src):
            cmd = ['cp', '-r', src, dest]
        elif glob.glob(src):
            cmd = ['cp']
            cmd.extend(glob.glob(src))
            cmd.append(dest)
        else:
            return {'success': False,
                    'output': 'Source file/directory {0} does not exist.'.format(src)}

        try:
            subprocess.call(cmd)
        except subprocess.CalledProcessError as e:
            return {'success': False,
                    'output': 'Failed to copy file {0}.'.format(str(e))}

    return {'success': True, 'output': 'Files copied.'}

def build_gearpump_dashboard(path, skip_tests=True):
    return call_build_command_chain(lambda: build_pack_sh(path),
                                    lambda: build_maven(path, skip_tests))

def build_gearpump_broker(path, skip_tests=True):
    return call_build_command_chain(lambda: build_maven(path, skip_tests, 'clean install'),
                                    lambda: build_pack_sh(path),
                                    lambda: build_maven(path, skip_tests))

def build_scoring_engine(path, skip_tests=True):
    return call_build_command_chain(lambda: build_maven(path, skip_tests, 'clean install -P dev'),
                                    lambda: build_maven(path, skip_tests, 'package -P build-server -f docker/pom.xml'))

def build_space_shuttle_demo(path):
    return call_build_command_chain(lambda: build_pack_sh(path),
                                    lambda: BuildRunner.call_build_command(['bash', 'copy_artifacts.sh'], path))

def main():
    module = AnsibleModule(
        argument_spec=dict(
            state=dict(default='build', choices=['build']),
            name=dict(required=True, type='str'),
            path=dict(required=True, type='str'),
            category=dict(required=True, choices=['maven', 'pack_sh', 'rpm', 'gradle', 'data-catalog', 'auth-gateway',
                                                  'go_exe', 'tap-metrics', 'tap-blob-store', 'console',
                                                  'gearpump-dashboard', 'gearpump-broker', 'scoring-engine',
                                                  'space-shuttle-demo']),
            skip_tests=dict(required=False, default=True, type='bool'),
            proxy_settings=dict(required=False, default=None, type='dict'),
            copy_files=dict(required=False, default=None, type='list'),
            timeout=dict(required=False, default=30, type='int')
        )
    )

    params = module.params

    if params['copy_files']:
        copy_files_result = copy_files(params['copy_files'])
        if not copy_files_result['success']:
            module.fail_json(msg=copy_files_result['output'])

    if params['timeout']:
        BuildRunner.timeout_mins = params['timeout']

    build_result = {'success': False, 'output': 'Unsupported build category.'}

    if params['category'] == 'maven':
        build_result = build_maven(params['path'], params['skip_tests'])
    elif params['category'] == 'pack_sh':
        build_result = build_pack_sh(params['path'])
    elif params['category'] == 'rpm':
        build_result = build_rpm(params['path'])
    elif params['category'] == 'gradle':
        build_result = build_gradle(params['path'], params['skip_tests'], params['proxy_settings'])
    elif params['category'] == 'go_exe':
        build_result = build_go_exe(params['path'])
    elif params['category'] == 'data-catalog':
        build_result = build_data_catalog(params['path'], params['proxy_settings'])
    elif params['category'] == 'auth-gateway':
        build_result = build_auth_gateway(params['path'], params['skip_tests'])
    elif params['category'] == 'tap-metrics':
        build_result = build_tap_metrics(params['path'], params['proxy_settings'])
    elif params['category'] == 'tap-blob-store':
        build_result = build_tap_blob_store(params['path'])
    elif params['category'] == 'console':
        build_result = build_console(params['path'])
    elif params['category'] == 'gearpump-dashboard':
        build_result = build_gearpump_dashboard(params['path'], params['skip_tests'])
    elif params['category'] == 'gearpump-broker':
        build_result = build_gearpump_broker(params['path'], params['skip_tests'])
    elif params['category'] == 'scoring-engine':
        build_result = build_scoring_engine(params['path'], params['skip_tests'])
    elif params['category'] == 'space-shuttle-demo':
        build_result = build_space_shuttle_demo(params['path'])

    if not build_result['success']:
        module.fail_json(msg="Building {name} failed. Log: {output}".format(name=params['name'],
                                                                            output=build_result['output']))
    elif 'output' not in build_result:
        module.exit_json(changed=False)
    else:
        create_commit_file(params['path'])
        module.exit_json(changed=True)


if __name__ == '__main__':
    main()
