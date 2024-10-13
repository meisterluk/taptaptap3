Documentation
=============

:name:          taptaptap
:author:        Lukas Prokop
:date:          Feb-Apr 2014, Jul 2018, Oct 2024
:license:       BSD 3-clause
:version:       3.1.0
:issues:        http://github.com/meisterluk/taptaptap3/issues

Test Anything Protocol handling for cat lovers \*rawwr*

.. contents:: Table of contents

``taptaptap3`` provides parsers, writers and APIs to handle the Test Anything Protocol (TAP). The implementation focuses on the most-current TAP version 13. TAP originates from the Perl community, but is a general format to document runs of testsuites. The reference to cats is just a pun for the noise of cats sneaking on floors and "3" is part of "<3", thus "lovers".

Compatibility
-------------

``taptaptap3`` is only supposed to be working with python 3.5 upwards.
It was written for python 2.7 as package `taptaptap <https://github.com/meisterluk/taptaptap>`_ and this implementation is the modern port to python3.
It has been tested with Python 3.12.6 on Arch Linux (Linux 6.10 on x86_64) 

The File Format
---------------

A basic introduction is given by Wikipedia. The format was specified by the Perl community.

* `The Wikipedia article <https://en.wikipedia.org/wiki/Test_Anything_Protocol>`_
* `Original specification <http://web.archive.org/web/20120730055134/http://testanything.org/wiki/index.php/TAP_specification>`_
* `Test::Harness <https://metacpan.org/pod/release/PETDANCE/Test-Harness-2.64/lib/Test/Harness/TAP.pod#THE-TAP-FORMAT>`_

Testsuite & Examples
--------------------

``taptaptap3`` comes with a testsuite, which covers many special cases of the TAP format and tests the provided APIs. Please don't hesitate to report any issues_.

You can run the ``taptaptap3`` testcases yourself using::

    ./run.sh

in the tests directory. The testsuite also shows some API usage examples, but I want to provide some here. The procedural API is well-suited if you are in the python REPL::

    from taptaptap3.proc import plan, ok, not_ok, out
    plan(tests=10)
    ok('Starting the robot')
    not_ok('Starting the engine')
    not_ok('Find the object', skip='Setup required')
    not_ok('Terminate', skip='Setup required')

    out()

The output looks like this::

    1..10
    ok - Starting the robot
    not ok - Starting the engine
    not ok - Find the object  # SKIP Setup required
    not ok - Terminate  # SKIP Setup required

Be aware that the state is stored within the module. This is not what you want if you are outside the REPL. The ``TapWriter`` class is more convenient in this case::

    import taptaptap3

    writer = taptaptap3.TapWriter()
    writer.plan(1, 3)
    writer.ok('This testcase went fine')
    writer.ok('And another one')
    writer.ok('And also the last one')

If you like python's generators, you want to use ``SimpleTapCreator``::

    @taptaptap3.SimpleTapCreator
    def runTests():
        yield True
        yield True
        yield False

    print runTests()

Giving us::

    1..3
    ok
    ok
    not ok

Or take a look at the more sophisticated ``TapCreator``. If you are a real expert, you can use ``TapDocument`` directly, which covers all possibilities of TAP.

Command line tools
------------------

You can also invoke ``taptaptap3`` directly from the command line::

    tapvalidate some_tap_file_to_validate.tap

This command will parse the file and write the file in a way how it was understood by the module. The exit code indicates its validity:

0
  Everything fine.
1
  The TAP file is missing some testcases or contains failed testcases.
2
  A bailout was raised. So the testing environment crashed during the run.

Pickling
--------

All objects are pickable.

When to use ``taptaptap3``
--------------------------

Does ``taptaptap3`` suite your needs?
It does, if you are looking for a parser and validator for your TAP documents and you don't want to care about details and just need a gentle API.

best regards,
meisterluk

.. _issues: https://github.com/meisterluk/taptaptap
