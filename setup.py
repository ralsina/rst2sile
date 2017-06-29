from setuptools import setup
setup(
    name='rst2sile',
    version='0.1',
    install_requires=open('requirements.txt').readlines(),
    scripts=['rst2sile'],
    packages=['sile'],
    package_dir={'sile': 'sile'},
    include_package_data=True,
)
