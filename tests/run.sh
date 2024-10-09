#!/bin/bash

#
# Various tests are available:
#    [ ] use a TAP file as source
#      OR
#    [ ] use a program as source (any API)
#      THEN
#    [ ] check objects in RAM
#    [ ] check output representation (__str__)
#    [ ] check metrics (validity status, number of ok/not-ok testcases, ...)
#

export PYTHONPATH=$PYTHONPATH":.."

# check objects in RAM and exit code must be 0
normal_test=('test_taptc.py' 'test_tapdoc.py' 'test_exc.py'
             'test_examples.py' 'test_tapmerge.py')

for test in "${normal_test[@]}"
do
  echo "[[     Run testsuite $test     ]]"
  python3 "$test" || exit $?
done

# source TAP files
examples=('000.tap' '001.tap' '002.tap' '003.tap' '004.tap' '005.tap'
          '006.tap' '007.tap' '008.tap' '009.tap' '010.tap' '011.tap'
          '012.tap' '013.tap' '014.tap' '015.tap' '016.tap' '017.tap'
                    '019.tap' '020.tap' '021.tap' '022.tap' '023.tap'
          '024.tap' '025.tap' '026.tap')

for test in "${examples[@]}"
do
  echo "[[     Testing  $test     ]]"
  python3 "./testlib.py" "../examples/$test" || exit $?
done


# source TAP file generators
python_test=('proc_000.py' 'proc_001.py' 'proc_002.py' 'proc_003.py'
             'proc_004.py' 'proc_005.py' 'proc_006.py' 'proc_007.py'
             'proc_008.py' 'proc_009.py' 'proc_010.py' 'test_unittestrunner.py'
             'creator_001.py' 'simplecreator_001.py')

for test in "${python_test[@]}"
do
  echo "[[     Check output of  $test     ]]"
  python3 "./testlib.py" "./$test" || exit $?
done
