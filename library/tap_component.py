#!/usr/bin/python
# -*- coding: utf-8 -*-

#
# Copyright (c) 2016 Intel Corporation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

DOCUMENTATION = '''
---
module: tap_component
short_description: Builds TAP components.
description: Idempotency is provided by checking special commit file, which stores
component commit hash. Commit file is created in component directory after successful build. If commit file is
not present, or it's content doesn't represent current commit in component's repository, component will be rebuilded.

Handling proxy
Pass following parameter:
proxy_settings:
  http_proxy <http_proxy>

in module invocation in order to pass proxy settings to build commands.
For Maven components, please configure proxy settings before running 
this module.
'''

COMMIT_FILE_NAME = '.tap_component_build.txt'
DATA_CATALOG_BUILD_TAG = 'tapimages:8080/data-catalog-build'
GRADLE_TOMCAT_URL = 'http://repo2.maven.org/maven2/org/apache/tomcat/tomcat/7.0.70/tomcat-7.0.70.tar.gz'
GRADLE_TOMCAT_PACKAGE_NAME = 'apache-tomcat-7.0.70.tar.gz'


# Status returned, when component is already build.
NOTHING_TO_CHANGE = {'success': True}

import os
import subprocess


from ansible.module_utils.basic import AnsibleModule

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

def call_build_command(cmd, path):
    if is_component_already_build(path):
        return NOTHING_TO_CHANGE

    output = ''
    try:
        build_process = subprocess.Popen(cmd, cwd=path, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        out, err = build_process.communicate()
        output = out
        if build_process.returncode != 0:
            raise subprocess.CalledProcessError(cmd, build_process.returncode)

    except subprocess.CalledProcessError:
        return {'success': False, 'output': output}

    return {'success': True, 'output': output}

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

def build_maven(path, skip_tests=False):
    command = ['mvn', '-B', 'clean', 'package', 'docker:build']
    if skip_tests:
        command.append('-Dmaven.test.skip=true')

    return call_build_command(command, path)

def build_pack_sh(path):
    return call_build_command(['bash', 'pack.sh'], path)

def build_go_exe(path):
    return call_build_command(['make', 'build_anywhere'], path)

def build_data_catalog(path, proxy_settings=None):
    docker_build_cmd = ['docker', 'build', '-t', DATA_CATALOG_BUILD_TAG]
    if proxy_settings and proxy_settings.get('http_proxy'):
        docker_build_cmd.extend(['--build-arg',
                                 'HTTP_PROXY={0}'.format(proxy_settings['http_proxy'])])
    docker_build_cmd.append('build-image/')

    return call_build_command_chain(lambda: call_build_command(docker_build_cmd, path),
                                    lambda: call_build_command(['bash', 'archive-deps.sh'], path),
                                    lambda: call_build_command(['bash', 'pack.sh'], path))

def build_auth_gateway(path, skip_tests):
    package_cmd = ['mvn', '-B', 'clean', 'package']
    if skip_tests:
        package_cmd.append('-Dmaven.test.skip=true')

    return call_build_command_chain(lambda: call_build_command(package_cmd, path),
                                    lambda: call_build_command(['mvn', '-B', '-f',
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
        lambda: call_build_command(['wget', GRADLE_TOMCAT_URL, '-O', GRADLE_TOMCAT_PACKAGE_NAME],
                                   path),
        lambda: call_build_command(gradle_cmd, path))

def build_tap_metrics(path, proxy_settings=None):
    build_anywhere_cmd = ['bash', 'build_anywhere.sh']
    if proxy_settings and proxy_settings.get('http_proxy'):
        build_anywhere_cmd.append('build_arg_HTTP_PROXY={0}'.format(proxy_settings['http_proxy']))

    return call_build_command_chain(lambda: call_build_command(build_anywhere_cmd, path),
                                    lambda: call_build_command(['bash', 'build_docker_images.sh'], path))

def build_tap_blob_store(path, proxy_settings=None):
    build_blob_store_cmd = ['docker', 'build', '-t', 'tap-blob-store']
    build_minio_cmd = ['docker', 'build', '-t', 'tap-blob-store/minio']
    if proxy_settings and proxy_settings.get('http_proxy'):
        build_blob_store_cmd.append('build_arg_HTTP_PROXY={0}'.format(proxy_settings['http_proxy']))
        build_minio_cmd.append('build_arg_HTTP_PROXY={0}'.format(proxy_settings['http_proxy']))
    build_blob_store_cmd.append('.')
    build_minio_cmd.append('minio/')

    return call_build_command_chain(lambda: build_pack_sh(path),
                                    lambda: call_build_command(build_blob_store_cmd, path),
                                    lambda: call_build_command(build_minio_cmd, path))


def main():
    module = AnsibleModule(
        argument_spec=dict(
            state=dict(default='build', choices=['build']),
            name=dict(required=True, type='str'),
            path=dict(required=True, type='str'),
            category=dict(required=True, choices=['maven', 'pack_sh', 'gradle', 'data-catalog', 'auth-gateway',
                                                  'go_exe', 'tap-metrics', 'tap-blob-store']),
            skip_tests=dict(required=False, default=True, type='bool'),
            proxy_settings=dict(required=False, default=None, type='dict')
        )
    )

    params = module.params

    build_result = {'success': False, 'output': 'Unsupported build category.'}

    if params['category'] == 'maven':
        build_result = build_maven(params['path'], params['skip_tests'])
    elif params['category'] == 'pack_sh':
        build_result = build_pack_sh(params['path'])
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
