from setuptools import setup, find_packages

setup(
    name='dump2polarion',
    use_scm_version=True,
    url='https://github.com/mkoura/dump2polarion',
    description='Dump testcases results to xunit file and submit it to Polarion xunit importer',
    long_description=open('README.rst').read().strip(),
    author='Martin Kourim',
    author_email='mkourim@redhat.com',
    license='GPL',
    packages=find_packages(exclude=('tests',)),
    scripts=['csv2sqlite.py', 'polarion_dumper.py'],
    setup_requires=['setuptools_scm'],
    install_requires=['requests', 'pyyaml', 'stomp.py'],
    keywords=['polarion', 'testing'],
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Topic :: Software Development :: Testing',
        'License :: OSI Approved :: GNU General Public License v2 (GPLv2)',
        'Programming Language :: Python :: 2.7',
        "Programming Language :: Python :: 3.3",
        "Programming Language :: Python :: 3.4",
        "Programming Language :: Python :: 3.5",
        'Intended Audience :: Developers'],
    include_package_data=True
)
