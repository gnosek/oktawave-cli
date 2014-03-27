from distutils.core import setup

setup(name='oktawave-cli',
      version='0.8.3',
      description='Oktawave API',
      author='Grzegorz Nosek (based on original code by Marek Siemdaj of Oktawave)',
      author_email='root@localdomain.pl, support@oktawave.com, marek.siemdaj@gmail.com',
      packages=['oktawave'],
      scripts=['oktawave-cli'],
      url='http://oktawave.com',
      install_requires=['requests', 'python-swiftclient',
                        'argparse', 'setproctitle', 'prettytable'],
      license='GPLv3',
      )
