# Contributing to CacheControl

Thank you for your interest in contributing to `CacheControl`!

The information below will help you set up a local development environment
and perform common development tasks.

## Requirements

`CacheControl`'s only external development requirement is Python 3.7 or newer.

## Development steps

First, clone this repository:

```bash
git clone https://github.com/psf/cachecontrol
cd cachecontrol
```

Then, bootstrap your local development environment:

```bash
make bootstrap
# OPTIONAL: enter the new environment, if you'd like to run things directly
source .venv/bin/activate
```

Once you've run `make bootstrap`, you can run the other `make` targets
to perform particular tasks.

Any changes you make to the `cachecontrol` source tree will take effect
immediately in the development environment.

### Linting

You can run the current formatters with:

```bash
make format
```

### Testing

You can run the unit tests locally with:

```bash
# run the test suite in the current environment
make test

# OPTIONAL: use `tox` to fan out across multiple interpreters
make test-all
```

### Documentation

You can build the Sphinx-based documentation with:

```bash
# puts the generated HTML in docs/_build/html/
make doc
```

### Releasing

**NOTE**: If you're a non-maintaining contributor, you don't need the steps
here! They're documented for completeness and for onboarding future maintainers.

Releases of `CacheControl` are managed by GitHub Actions.

To perform a release:

1. Update `CacheControl`'s `__version__` attribute. It can be found under
   `cachecontrol/__init__.py`.

1. Create a new tag corresponding to your new version, with a `v` prefix. For example:

   ```bash
   # IMPORTANT: don't forget the `v` prefix!
   git tag v1.2.3
   ```

1. Push your changes to `master` and to the new remote tag.

1. Create, save, and publish a GitHub release for your new tag, including any
   `CHANGELOG` entries.
