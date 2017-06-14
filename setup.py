from setuptools import setup, find_packages

setup(
    name='dump2polarion',
    version='0.5',
    url='https://github.com/mkoura/dump2polarion',
    description='Dump testcases results to xunit file and submit it to Polarion xunit importer',
    long_description=open('README.rst').read().strip(),
    author='Martin Kourim',
    author_email='mkourim@redhat.com',
    license='GPL',
    packages=find_packages(exclude=('tests',)),
    scripts=['csv2sqlite.py', 'polarion_dumper.py'],
    install_requires=['requests', 'pyyaml', 'stomp.py'],
    keywords=['polarion', 'testing'],
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Topic :: Software Development :: Testing',
        'License :: OSI Approved :: GNU General Public License v2 (GPLv2)',
        'Programming Language :: Python :: 2.7'],
    include_package_data=True
)
