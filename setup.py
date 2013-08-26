from distutils.core import setup

setup(name='oktawave-cli',
      version='0.7.5',
      description='Command line interface to Oktawave',
      author='Oktawave Development Team (by Marek Siemdaj)',
      author_email='support@oktawave.com, marek.siemdaj@gmail.com',
      packages=['oktawave'],
      scripts=['oktawave-cli'],
      url='http://oktawave.com',
      install_requires=['suds-philpem', 'python-swiftclient',
          'argparse', 'setproctitle', 'prettytable'],
      license='GPLv3',
      )
