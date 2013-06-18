import setuptools

setup_params = dict(
    name='CacheControl',
    version='0.5',
    author="Eric Larson",
    author_email="eric@ionrock.org",
    url="http://github/ionrock/cachecontrol",
    packages=setuptools.find_packages(),
    install_requires=[
        'requests',
    ],
)


if __name__ == '__main__':
    setuptools.setup(**setup_params)
