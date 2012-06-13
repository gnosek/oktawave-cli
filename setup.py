from distutils.core import setup

setup(name='oktawave-cli',
      version='0.7',
      description='Command line interface to Oktawave',
      author='Marek Siemdaj',
      author_email='marek.siemdaj@monit24.pl',
      packages=['oktawave'],
      scripts=['oktawave-cli'],
      url='http://oktawave.com',
      requires=['suds', 'swift', 'argparse', 'setproctitle', 'prettytable'],
      license='GPLv3',
      data_files = [("", ["LICENSE.txt", "README"])]
     )
