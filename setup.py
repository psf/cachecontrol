# SPDX-FileCopyrightText: 2015 Eric Larson
#
# SPDX-License-Identifier: Apache-2.0

import setuptools

long_description = open("README.rst").read()

VERSION = "0.13.0"

setup_params = dict(
    name="CacheControl",
    version=VERSION,
    author="Eric Larson",
    author_email="eric@ionrock.org",
    url="https://github.com/ionrock/cachecontrol",
    keywords="requests http caching web",
    packages=setuptools.find_packages(exclude=["tests", "tests.*"]),
    package_data={"": ["LICENSE.txt"], "cachecontrol": ["py.typed"]},
    package_dir={"cachecontrol": "cachecontrol"},
    include_package_data=True,
    description="httplib2 caching for requests",
    long_description=long_description,
    install_requires=["requests>=2.16.0", "msgpack>=0.5.2"],
    extras_require={"filecache": ["filelock>=3.8.0"], "redis": ["redis>=2.10.5"]},
    entry_points={"console_scripts": ["doesitcache = cachecontrol._cmd:main"]},
    python_requires=">=3.6",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Environment :: Web Environment",
        "License :: OSI Approved :: Apache Software License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Topic :: Internet :: WWW/HTTP",
    ],
)


if __name__ == "__main__":
    setuptools.setup(**setup_params)
