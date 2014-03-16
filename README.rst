Introduction
============

:name:          taptaptap
:author:        Lukas Prokop
:date:          Feb-Mar 2014
:license:       BSD 3-clause
:issues:        http://github.com/meisterluk/taptaptap/issues

Test Anything Protocol handling for cats \*rawwr*

.. contents:: Table of contents

``taptaptap`` provides parsers, writers and APIs to handle the Test Anything Protocol (TAP).
The implementation focuses on the most-current TAP version 13.

Compatibility
-------------

``taptaptap`` has been tested with
* TODO 2.6
* TODO 2.7

You can run the ``taptaptap`` testcases yourself using::

    ./runtests.py

The `examples` directory contains many examples how to use ``taptaptap``.

Format
------

A basic introduction is given by Wikipedia. The format was specified by the Perl community.

* `The Wikipedia article <https://en.wikipedia.org/wiki/Test_Anything_Protocol>`_
* `Original specification <http://web.archive.org/web/20120730055134/http://testanything.org/wiki/index.php/TAP_specification>`_
* `Test::Harness <https://metacpan.org/pod/release/PETDANCE/Test-Harness-2.64/lib/Test/Harness/TAP.pod#THE-TAP-FORMAT>`_

Command line tools
------------------

Pickling
--------

The ``TapDocument`` and ``TapTestcase`` objects are pickable.


How to use ``taptaptap``
------------------------


