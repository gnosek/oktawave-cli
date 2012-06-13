from distutils.core import setup

setup(name='oktawave-cli',
      version='0.7',
      description='Command line interface to Oktawave',
      author='Oktawave Development Team (by Marek Siemdaj)',
      author_email='support@oktawave.com, marek.siemdaj@gmail.com',
      packages=['oktawave'],
      scripts=['oktawave-cli'],
      url='http://oktawave.com',
      requires=['suds', 'swift', 'argparse', 'setproctitle', 'prettytable'],
      license='GPLv3',
      data_files = [("", ["LICENSE.txt", "README"])]
     )
