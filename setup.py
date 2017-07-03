from setuptools import setup
setup(
    name='rst2sile',
    version='0.2.3',
    install_requires=open('requirements.txt').readlines(),
    scripts=['rst2sile', 'rst2pdf'],
    packages=['sile'],
    package_dir={'sile': 'sile'},
    include_package_data=True,
)
