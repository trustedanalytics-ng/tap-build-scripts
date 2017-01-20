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
module: collect_repo_version
short_description: |
  Collects git repository name, branch and hash of current commit. Collected information is written to a given
  version file.
'''

VERSION_FILE_HEADER = 'Name\tVersion\tcommit-SHA\tBranch\n'
COMPONENT_VERSION_PLACEHOLDER = 'source'

import os
import subprocess

from ansible.module_utils.basic import AnsibleModule

def get_commit_hash(repo_path):
    return subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=repo_path).rstrip()

def get_branch(repo_path):
    return subprocess.check_output(['git', 'rev-parse', '--abbrev-ref', 'HEAD'], cwd=repo_path).rstrip()

def get_repository_name(repo_path):
    return subprocess.check_output(['basename', repo_path], cwd=repo_path).rstrip()

def collect_version_info(repo_path):
    try:
        name = get_repository_name(repo_path)
        version = COMPONENT_VERSION_PLACEHOLDER
        commit_hash = get_commit_hash(repo_path)
        branch = get_branch(repo_path)
    except subprocess.CalledProcessError as e:
        return {'success': False, 'result': str(e)}

    version_info = '{name} {version} {commit} {branch}\n'.format(name=name, commit=commit_hash,
                                                                 version=version,  branch=branch)
    return {'success': True, 'result': version_info}

def write_version_file_header(version_file_path):
    with open(version_file_path, "w") as version_file:
        version_file.write(VERSION_FILE_HEADER)

def is_version_info_present(version_file_path, version_info):
    repo_name = version_info.split()[0]

    with open(version_file_path, "r+") as version_file:
        version_file_content = version_file.readlines()
        version_file.seek(0)
        for line in version_file_content:
            if line == version_info:
                return True
            # Omit old version info
            elif repo_name not in line:
                version_file.write(line)

        version_file.truncate()

    return False

def write_version_info(version_file_path, version_info):
    if not os.path.isfile(version_file_path): 
        write_version_file_header(version_file_path)

    if is_version_info_present(version_file_path, version_info):
        return {'changed': False}
    else:
        with open(version_file_path, "a") as version_file:
            version_file.write(version_info)
        return {'changed': True}

def main():
    module = AnsibleModule(
        argument_spec=dict(
            repository_path=dict(required=True, type='str'),
            version_file_path=dict(required=True, type='str')
        )
    )

    if not os.path.isdir(module.params['repository_path']):
        module.fail_json(msg="Specified repository path {0} does not exist.".format(module.params['repository_path']))

    version_info = collect_version_info(module.params['repository_path'])
    if not version_info['success']:
        module.fail_json(msg="Failed to obtain repository info. Log: {0}".format(version_info['result']))
    write_version_result = write_version_info(module.params['version_file_path'], version_info['result'])

    if write_version_result['changed']:
        module.exit_json(changed=True)
    else:
        module.exit_json(changed=False)

if __name__ == '__main__':
    main()
