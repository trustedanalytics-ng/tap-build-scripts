#!/bin/bash
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

CDIR=$(dirname $0)
TPL=$CDIR/thirdpartylicenses

accept_license=0

while getopts ':a' flag; do
  case "${flag}" in
    :) ;;
    a) accept_license=1; ;;
  esac
done

if [ $accept_license == '1' ]; then
  echo "All licenses are automatically accepted"
fi

FILES=$(ls "$TPL")

for f in "$FILES"
do
  accept='n'
  echo "License: $f"
  echo ""
  cat "$TPL/$f"
  echo ""
  while [ $accept_license == '0' -a $accept != 'y' ]; do
    echo "Accept? [y/n]"
    read -n 1 -s accept
  done
done
