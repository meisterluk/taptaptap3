#!/usr/bin/env python3


import re
import sys
import codecs
import subprocess
import taptaptap3

success = lambda x: print("  [ OK ]  " + x)


def call_module(filepath):
    """Call TAP file with module loading and return the metrics tuple"""
    cmd = "python -R -t -t -m taptaptap3.__main__".split() + [filepath]
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    encoding = sys.stdout.encoding or "utf-8"
    out, err = [v.decode(encoding) for v in proc.communicate()]
    valid = proc.returncode
    doc = taptaptap3.parse_string(out)
    ok, total, bailout = doc.count_ok(), len(doc), doc.bailed()

    # err and out exchanged by intention
    return valid, ok, total, bailout, err, out


def call_tapvalidate(args):
    """Call tapvalidate with args and return the metrics tuple"""
    cmd = ["tapvalidate"] + args

    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    proc.communicate()

    # if the error message of 'tapvalidate' prints something like
    #    >>> __import__('pkg_resources').run_script('taptaptap3==3.0.0', 'main')
    #   Traceback (most recent call last):
    #     File "<stdin>", line 1, in <module>
    #     File ".../venv/lib/python3.6/site-packages/pkg_resources/__init__.py", line 654, in run_script
    #       self.require(requires)[0].run_script(script_name, ns)
    #     File ".../venv/lib/python3.6/site-packages/pkg_resources/__init__.py", line 1425, in run_script
    #       .format(**locals()),
    #   pkg_resources.ResolutionError: Script 'scripts/main' not found in metadata at '.../venv/lib/python3.6/site-packages/taptaptap3-3.0.0-py3.6.egg/EGG-INFO'
    # then make sure, that you create a development version of the package, not a production version:
    #   NOT python3 setup.py install
    #   BUT python3 setup.py develop
    # this works for me(tm)

    with codecs.open(args[0], encoding="utf-8") as fp:
        err = fp.read()
    out = ""

    valid = proc.returncode
    doc = taptaptap3.parse_string(err)
    ok, total, bailout = doc.count_ok(), len(doc), doc.bailed()

    return valid, ok, total, bailout, out, err


def run_python_file(filepath):
    """Run a python file using taptaptap3 and return the metrics tuple"""
    encoding = sys.stdout.encoding or "utf-8"

    proc = subprocess.Popen(
        ["python", filepath], stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    proc.wait()
    out, err = proc.communicate()
    out, err = out.decode(encoding), err.decode(encoding)
    print(out, err)

    with codecs.open(filepath, encoding="utf-8") as fp:
        source = fp.read()

    if "## " in source:
        # check conditions
        output = out or err
        doc = taptaptap3.parse_string(output)

        total = len(doc)
        bailout, ok = doc.bailed(), doc.count_ok()
        if doc.bailed():
            valid = -2
        elif doc.valid():
            valid = 0
        else:
            valid = -1

        for line in source.splitlines():
            check_line(line, valid, ok, total, bailout, out, err)

        success("Checked conditions in file")
    else:
        # only check exit code
        code = proc.returncode
        assert code == 0, "Unexpected exit code " + str(code)
        success("Exit code is fine")


def run_tap_file(filepath):
    """Interpret a TAP file and test its conditions"""
    doc = taptaptap3.parse_file(filepath)

    with codecs.open(filepath, encoding="utf-8") as fp:
        err = fp.read()

    if doc.bailed():
        valid = -2
    elif doc.valid():
        valid = 0
    else:
        valid = -1

    return (valid, doc.count_ok(), len(doc), doc.bailed(), "", err)


validity = re.compile(r"##     validity: (-?\d+)", flags=re.I)
tests = re.compile(r"## ok testcases: (\d+) / (\d+)", flags=re.I)
rbailout = re.compile(r"##      bailout: (no|yes)", flags=re.I)
inout = re.compile(r"##       stdout: (~?)(\S*)", flags=re.I)
inerr = re.compile(r"##       stderr: (~?)(\S*)", flags=re.I)


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
        assert (expect_ok, expect_total) == (ok, total), msg.format(
            expect_ok, expect_total, ok, total
        )
        success("Ratio of ok / not-ok testcases is fine")

    elif matches[2]:
        expect_bailout = matches[2].group(1) == "yes"
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
    with codecs.open(filepath, encoding="utf-8") as fp:
        for line in fp.readlines():
            check_line(line, valid, ok, total, bailout, stdout, stderr)


def validate(filepath):
    if filepath.endswith(".py"):
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


if __name__ == "__main__":
    try:
        arg = sys.argv[1]
    except IndexError:
        print("Usage: ./testlib.py <file>")
        print("  If it's a TAP file, interpret it and check conditions")
        print("  If it's a python file, run it and check conditions")
        sys.exit(1)

    sys.exit(validate(arg))
