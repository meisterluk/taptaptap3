#!/usr/bin/env python

"""Contains all testcases which are run on the commandline
using the files in the `examples` directory
"""

import sys
sys.path.append('../..')

import os.path
import subprocess
import taptaptap


EXAMPLES = "taptaptap/examples/"

# testsuite

def callTaptaptap(example_file, tests):
    cmd = ['python', '-R', '-t', '-t', '-m', 'taptaptap.__main__', example_file]
    print('Running:  {}'.format(' '.join(cmd)))
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, cwd='../..')
    out, err = proc.communicate()
    #print(out)
    #print(out, err, proc.returncode)

    for testcode in tests:
        verify(testcode, out, err, proc.returncode)

def runProgram(cmd, tests):
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = proc.communicate()

    for testcode in tests:
        verify(testcode, out, err, proc.returncode)

def verify(code, out, err, retcode):
    local = {'out': out, 'err': err, 'retcode': retcode}
    try:
        exec 'assert {}'.format(code) in {}, local
    except AssertionError:
        raise AssertionError("Failed: " + code)

# testcase specification

# cli tools
cli_validate = ['/usr/bin/python', '../bin/tapvalidate']
cli_merge = ['python', '../tapmerger.py']
e = lambda filename: os.path.join(EXAMPLES, filename + '.tap')

NO_ERROR0 = ['"Error" not in err and "Exception" not in err', 'retcode == 0']
NO_ERROR1 = ['"Error" not in err and "Exception" not in err', 'retcode == 1']
NO_BAILOUT = ['"Bail out!" not in out']

TESTCASES_TAPTAPTAP = {
    e('001'):
        ['"Read the rest" in out', '"Not written" in out', '"1..4" in out'] + \
        NO_ERROR1 + NO_BAILOUT,
    e('002'):
        ['"1..48" in out', '"ok 48" in out', '"more tests" in out'] + \
        NO_ERROR1 + NO_BAILOUT,
    e('003'):
        ['"The object isa Board" in out', '"Board size is 1" in out'] + \
        NO_ERROR0 + NO_BAILOUT,
    e('004'):
        ['"need to ping 6 servers" in out', '"1..7" in out'] + \
        NO_ERROR1 + NO_BAILOUT,
    e('005'):
        ['"database handle" in out', 'retcode == 2', \
        '"Bail out! Couldn\'t" in out',
        '"Error" not in err and "Exception" not in err'],
    e('006'):
        ['"SKIP no /sys directory" in out'] + NO_ERROR0 + NO_BAILOUT,
    e('007'):
        ['"English-to-French translator" in out'] + NO_ERROR0 + NO_BAILOUT,
    e('008'): NO_ERROR1 + NO_BAILOUT,
    e('009'): NO_ERROR0 + NO_BAILOUT,
    e('010'): NO_ERROR0 + NO_BAILOUT,
    e('011'):
        ['"First line invalid" in out', '"data:" in out', '"ok 3" in out'] + \
        NO_ERROR1 + NO_BAILOUT
}

TESTCASES_CLI = [
    (cli_validate + [e('001')], ['retcode == 1', 'not out', 'not err']),
    (cli_validate + [e('002')], ['retcode == 1', 'not out', 'not err']),
    (cli_validate + [e('003')], ['retcode == 0', 'not out', 'not err']),
    (cli_validate + [e('004')], ['retcode == 1', 'not out', 'not err']),
    (cli_validate + [e('005')], ['retcode == 1', 'not out', 'not err']),
    (cli_validate + [e('006')], ['retcode == 0', 'not out', 'not err']),
    (cli_validate + [e('007')], ['retcode == 0', 'not out', 'not err']),
    (cli_validate + [e('008')], ['retcode == 0', 'not out', 'not err']),
    (cli_validate + [e('009')], ['retcode == 0', 'not out', 'not err']),
    (cli_validate + [e('010')], ['retcode == 0', 'not out', 'not err']),
    (cli_validate + [e('011')], ['retcode == 0', 'not out', 'not err']),
    (cli_merge + [e('001'), e('004')], ['"Input file opened" in out',
        '"First line of the input" in out', '"1..11" in out',
        'out.count("not ok") == 4']),
    (cli_merge + [e('001'), e('005')], ['"Not written" in out',
        '"1..577" in out', 'out.count("not ok") == 3', '"Bail out!" in out']),
    (cli_merge + [e('005'), e('001')], ['"Not written" not in out',
        '"1..577" in out', '"Bail out!" in out'])
]


if __name__ == '__main__':
    for (filepath, tests) in TESTCASES_TAPTAPTAP.iteritems():
        print 'Running TAPTAPTAP testcase {}'.format(filepath)
        callTaptaptap(filepath, tests)
        print '      [passed successfully]'

    for (cmd, tests) in TESTCASES_CLI:
        print 'Running CLI testcase {}'.format(' '.join(cmd))
        runProgram(cmd, tests)
        print '      [passed successfully]'
