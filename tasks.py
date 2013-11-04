from invoke import run, task

from distutils.version import StrictVersion


VENV = 'venv'

def env_do(tail, **kw):
    return run('%s/bin/%s' % (VENV, tail), **kw)


@task
def virtualenv():
    run('virtualenv %s' % VENV)


@task('virtualenv')
def bootstrap():
    env_do('pip install -r dev_requirements.txt')


@task
def clean_env():
    run('rm -r venv')


@task
def test(args):
    env_do('py.test %s' % ' '.join(args))
