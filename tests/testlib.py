#!/usr/bin/env python

from __future__ import print_function

import re
import sys
import codecs
import subprocess
import taptaptap

success = lambda x: print('  [ OK ]  ' + x)


def call_module(filepath):
    """Call TAP file with module loading and return the metrics tuple"""
    cmd = u'python -R -t -t -m taptaptap.__main__'.split() + [filepath]
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE)

    encoding = sys.stdout.encoding or 'utf-8'
    out, err = [v.decode(encoding) for v in proc.communicate()]
    valid = proc.returncode
    doc = taptaptap.parse_string(out)
    ok, total, bailout = doc.count_ok(), len(doc), doc.bailed()

    # err and out exchanged by intention
    return valid, ok, total, bailout, err, out


def call_tapvalidate(args):
    """Call tapvalidate with args and return the metrics tuple"""
    cmd = ['tapvalidate'] + args
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE)

    proc.communicate()
    with codecs.open(args[0], encoding='utf-8') as fp:
        err = fp.read()
    out = u''

    valid = proc.returncode
    doc = taptaptap.parse_string(err)
    ok, total, bailout = doc.count_ok(), len(doc), doc.bailed()

    return valid, ok, total, bailout, out, err


def run_python_file(filepath):
    """Run a python file using taptaptap and return the metrics tuple"""
    proc = subprocess.Popen(['python', filepath], stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE)
    proc.wait()
    out, err = proc.communicate()

    with codecs.open(filepath, encoding='utf-8') as fp:
        source = fp.read()

    print()
    if '## ' in source:
        # check conditions
        output = out or err
        doc = taptaptap.parse_string(output)

        total = len(doc)
        bailout, ok = doc.bailed(), doc.count_ok()
        if doc.bailed():
            valid = -2
        elif doc.valid():
            valid = 0
        else:
            valid = -1

        for line in output.splitlines():
            check_line(line, valid, ok, total, bailout, out, err)

        success('Checked conditions in file')
    else:
        # only check exit code
        code = proc.returncode
        assert code == 0, 'Unexpected exit code ' + str(code)
        success('Exit code is fine')


def run_tap_file(filepath):
    """Interpret a TAP file and test its conditions"""
    doc = taptaptap.parse_file(filepath)

    with codecs.open(filepath, encoding='utf-8') as fp:
        err = fp.read()

    if doc.bailed():
        valid = -2
    elif doc.valid():
        valid = 0
    else:
        valid = -1

    return (valid, doc.count_ok(), len(doc), doc.bailed(), u'', err)


validity = re.compile(u'##     validity: (-?\d+)', flags=re.I)
tests    = re.compile(u'## ok testcases: (\d+) / (\d+)', flags=re.I)
rbailout = re.compile(u'##      bailout: (no|yes)', flags=re.I)
inout    = re.compile(u'##       stdout: (~?)(\S*)', flags=re.I)
inerr    = re.compile(u'##       stderr: (~?)(\S*)', flags=re.I)


def check_line(line, valid, ok, total, bailout, stdout, stderr):
    matches = [validity, tests, rbailout, inout, inerr]
    matches = [r.match(line) for r in matches]

    if matches[0]:
        expect_ec = int(matches[0].group(1))
        expect_ec, valid = expect_ec % 256, valid % 256
        msg = "Expected validity {}, but was {}"
        assert expect_ec == valid, msg.format(expect_ec, valid)
        success("Validity state is fine")

    elif matches[1]:
        expect_ok = int(matches[1].group(1))
        expect_total = int(matches[1].group(2))

        msg = "Expected {} of {} to be 'ok' testcases. But got {}/{}"
        assert (expect_ok, expect_total) == (ok, total), \
            msg.format(expect_ok, expect_total, ok, total)
        success("Ratio of ok / not-ok testcases is fine")

    elif matches[2]:
        expect_bailout = matches[2].group(1) == 'yes'
        if expect_bailout and not bailout:
            raise AssertionError("Expected Bailout was not thrown")
        elif expect_bailout:
            success("Bailout was thrown as expected")
        else:
            success("No bailout was thrown as expected")

    elif matches[3]:
        substr = matches[3].group(2)
        if matches[3].group(1):
            msg = "String '{}' must not be in stdout:\n{}"
            assert substr not in stdout, msg.format(substr, repr(stdout))
        else:
            msg = "Expected string '{}' missing in stdout:\n{}"
            assert substr in stdout, msg.format(substr, repr(stdout))

    elif matches[4]:
        substr = matches[4].group(2)
        if matches[4].group(1):
            msg = "String '{}' must not be in stderr:\n{}"
            assert substr not in stdout, msg.format(substr, repr(stderr))
        else:
            msg = "Expected string '{}' missing in stderr:\n{}"
            assert substr in stderr, msg.format(substr, repr(stderr))


def read_file(filepath, valid, ok, total, bailout, stdout, stderr):
    with codecs.open(filepath, encoding='utf-8') as fp:
        for line in fp.readlines():
            check_line(line, valid, ok, total, bailout, stdout, stderr)


def validate(filepath):
    if filepath.endswith('.py'):
        run_python_file(filepath)
    else:
        print()
        read_file(filepath, *run_tap_file(filepath))
        print()
        read_file(filepath, *call_tapvalidate([filepath]))
        print()
        read_file(filepath, *call_module(filepath))

    print()
    return 0

if __name__ == '__main__':
    try:
        arg = sys.argv[1]
    except IndexError:
        print("Usage: ./testlib.py <file>")
        print("  If it's a TAP file, interpret it and check conditions")
        print("  If it's a python file, run it and check conditions")
        sys.exit(1)

    sys.exit(validate(arg))
