# Doing a release

## Tag the release

1. Pick new version V.
1. Make sure [release notes](docs/release_notes.rst) on main branch have latest changelog entries with version V.
1. In GitHub UI, added release (or tag) with name `v<V>`, e.g. `v1.17.23`.

## Upload

At this point you build wheels and sdist:

```
$ python setup.py sdist
$ pip wheel -w dist/ --no-deps .
```

And then upload using `twine`:

```
$ ls dist/
$ twine upload dist/CacheControl*
```

This will be replaced with automation in the future.
