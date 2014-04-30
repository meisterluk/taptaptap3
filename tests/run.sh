#!/bin/bash

tests=('test_taptc' 'test_tapdoc' 'test_exc' 'test_unittestrunner' \
       'test_examples' 'test_examples_programmatically' 'test_iterator' \
       'test_cli' 'test_proc_001' 'test_proc_002' 'test_proc_003' \
       'test_proc_004' 'test_proc_005' 'test_proc_006' \
       'test_tap_merge')

for test in "${tests[@]}"
do
  echo "[[     Executing $test     ]]"
  python $test".py" || exit $?
  #if [ "$?" -ne "0" ]; then exit $? fi;
done
