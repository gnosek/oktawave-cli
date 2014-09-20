from distutils.core import setup

setup(name='oktawave-cli',
      version='0.8.5',
      description='Oktawave API',
      author='Grzegorz Nosek (based on original code by Marek Siemdaj of Oktawave)',
      author_email='root@localdomain.pl, support@oktawave.com, marek.siemdaj@gmail.com',
      packages=['oktawave'],
      url='http://oktawave.com',
      install_requires=['requests>=0.12.1', 'python-swiftclient',
                        'argparse', 'setproctitle', 'prettytable', 'click'],
      license='GPLv3',
      entry_points='''
        [console_scripts]
        oktawave-cli=oktawave.cli:cli
        ''',
      )
