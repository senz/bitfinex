from setuptools import setup

# Runtime dependencies. See requirements.txt for development dependencies.
dependencies = [
    'requests',
    'httpretty'
]

version = '0.1.1'

setup(name='bitfinex-saf',
    version=version,
    description = 'Python client for the Bitfinex API',
    author = 'Scott Barr, Senz',
    author_email = 'scottjbarr@gmail.com',
    url = 'https://github.com/senz/bitfinex',
    license = 'MIT',
    packages=['bitfinex_saf'],
    scripts = ['scripts/bitfinex-poll-orderbook'],
    install_requires = dependencies,
    download_url = 'https://github.com/senz/bitfinex/tarball/%s' % version,
    keywords = ['bitcoin', 'btc', 'bitfinex'],
    classifiers = [],
    zip_safe=True)
