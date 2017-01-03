#!/bin/bash -x

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

export ANSIBLE_SSH_CONTROL_PATH='%(directory)s/%%h-%%r'
export ANSIBLE_HOST_KEY_CHECKING=False

CDIR=$(dirname $0)

while getopts a opt ; do
  case $opt in
    a) ACCEPTED_LICENSE=1 ;;
  esac
done

if [ $ACCEPTED_LICENSE = 1 ]
then
  bash $CDIR/bin/acceptlicense.sh -a
else
  echo "You have to run script with -a option as first argument to accept necessary licenses."
  exit 1
fi

shift
exec ansible-playbook tap-packager.yml -i inventory/all $@

RET=$?
echo "Deployment exited with return code: $RET"
exit $RET
