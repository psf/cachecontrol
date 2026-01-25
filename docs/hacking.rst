=======================
Hacking on CacheControl
=======================

CacheControl is a pure Python library. We use uv_ to manage its development.

Linting and Formatting
======================

We use Ruff_ and mypy_ for linting/formatting and type checking. You can run
them with:

.. code-block:: console

  $ make lint
  $ make format

Tests
=====

The tests are all in ``cachecontrol/tests`` and are runnable by ``py.test``.

You can use ``make test`` to run the tests:

.. code-block:: console

  $ make test

Documentation
=============

The documentation is built with Sphinx_. You can build it by running
``make doc``:

.. code-block:: console

  $ make doc

.. _uv: https://docs.astral.sh/uv/
.. _Ruff: https://docs.astral.sh/ruff/
.. _mypy: https://mypy-lang.org/
.. _Sphinx: https://www.sphinx-doc.org/
