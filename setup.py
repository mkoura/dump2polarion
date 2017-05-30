from setuptools import setup, find_packages

setup(
    name='dump2polarion',
    version='0.2',
    url='https://github.com/mkoura/dump2polarion',
    description='Dump testcases results to xunit file and submit it to Polarion xunit importer',
    long_description=open('README.md').read().strip(),
    author='Martin Kourim',
    author_email='mkourim@redhat.com',
    license='GPL',
    packages=find_packages(exclude=('tests',)),
    scripts=['csv2sqlite.py', 'polarion_dumper.py'],
    install_requires=['requests', 'pyyaml', 'stomp.py'],
    keywords='polarion',
    classifiers=['Private :: Do Not Upload'],  # hack to avoid uploading to pypi
    include_package_data=True,
    zip_safe=False
)
