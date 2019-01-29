import setuptools

long_description = open("README.rst").read()

VERSION = "0.12.5"

setup_params = dict(
    name="CacheControl",
    version=VERSION,
    author="Eric Larson",
    author_email="eric@ionrock.org",
    url="https://github.com/ionrock/cachecontrol",
    keywords="requests http caching web",
    packages=setuptools.find_packages(),
    package_data={"": ["LICENSE.txt"]},
    package_dir={"cachecontrol": "cachecontrol"},
    include_package_data=True,
    description="httplib2 caching for requests",
    long_description=long_description,
    install_requires=["requests", "msgpack>=0.5.2"],
    extras_require={"filecache": ["lockfile>=0.9"], "redis": ["redis>=2.10.5"]},
    entry_points={"console_scripts": ["doesitcache = cachecontrol._cmd:main"]},
    python_requires=">=2.7, !=3.0.*, !=3.1.*, !=3.2.*, !=3.3.*",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Environment :: Web Environment",
        "License :: OSI Approved :: Apache Software License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 2",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.4",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Topic :: Internet :: WWW/HTTP",
    ],
)


if __name__ == "__main__":
    setuptools.setup(**setup_params)
