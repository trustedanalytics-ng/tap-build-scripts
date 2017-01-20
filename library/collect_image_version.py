#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Copyright (c) 2017 Intel Corporation
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
module: collect_image_version
short_description: |
  Collects docker image name and ID (sha256). Collected information is written to a given
  version file.
'''

VERSION_FILE_HEADER = 'Name\tcommit-SHA\n'

import os
import subprocess

from ansible.module_utils.basic import AnsibleModule

def get_image_hash(image_name, image_tag=None):
    image_identifier = image_name
    if image_tag:
        image_identifier = image_identifier + ':' + image_tag
    cmd = ['docker', 'inspect', '--format', '{{.Id}}', image_identifier]
    return subprocess.check_output(cmd).rstrip()

def collect_version_info(image_name, image_tag=None):
    try:
        name = image_name
        image_hash = get_image_hash(image_name, image_tag)
    except subprocess.CalledProcessError as e:
        return {'success': False, 'result': str(e)}

    version_info = '{name} {commit}\n'.format(name=name, commit=image_hash)
    return {'success': True, 'result': version_info}

def write_version_file_header(version_file_path):
    with open(version_file_path, "w") as version_file:
        version_file.write(VERSION_FILE_HEADER)

def is_version_info_present(version_file_path, version_info):
    image_name = version_info.split()[0]

    with open(version_file_path, "r+") as version_file:
        version_file_content = version_file.readlines()
        version_file.seek(0)
        for line in version_file_content:
            if line == version_info:
                return True
            # Omit old version info
            elif image_name not in line:
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
            image_name=dict(required=True, type='str'),
            image_tag=dict(required=False, type='str'),
            version_file_path=dict(required=True, type='str')
        )
    )

    version_info = collect_version_info(module.params['image_name'], module.params.get('image_tag'))
    if not version_info['success']:
        module.fail_json(msg="Failed to obtain image hash. Log: {0}".format(version_info['result']))
    write_version_result = write_version_info(module.params['version_file_path'], version_info['result'])

    if write_version_result['changed']:
        module.exit_json(changed=True)
    else:
        module.exit_json(changed=False)

if __name__ == '__main__':
    main()
