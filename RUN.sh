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
SCRIPT_ARGS=""

ACCEPTED_LICENSE=0
for var in "$@"
do
 if [ "$var" = "-a" ]; then
   ACCEPTED_LICENSE=1
 else
   SCRIPT_ARGS="$SCRIPT_ARGS $var"
 fi
done

if [ $ACCEPTED_LICENSE = 1 ]
then
  bash $CDIR/bin/acceptlicense.sh -a
else
  bash $CDIR/bin/acceptlicense.sh
fi

exec ansible-playbook tap-packager.yml -i inventory/all $SCRIPT_ARGS

RET=$?
echo "Deployment exited with return code: $RET"
exit $RET
