from paver.easy import sh, task, needs, options, Bunch, consume_args

from distutils.version import StrictVersion


options(
    venv=Bunch(dir='.')
)


def env_do(tail, **kw):
    return sh('%s/bin/%s' % (options.venv.dir, tail), **kw)


@task
def virtualenv():
    sh('virtualenv %s' % options.venv.dir)


@task
@needs(['virtualenv'])
def bootstrap():
    env_do('python setup.py develop')
    env_do('pip install -r dev_requirements.txt')


@task
def clean_env():
    sh('rm -r lib')
    sh('rm -r bin')
    sh('rm -r include')


@task
@consume_args
def test(args):
    env_do('py.test %s' % ' '.join(args))


@task
@consume_args
def release(args):
    version = args[0]
    StrictVersion(version)
    env_do('python setup.py sdist upload')
