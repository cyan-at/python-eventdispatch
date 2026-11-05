from setuptools import setup, find_packages

setup(
    name='eventdispatch',
    version='0.2.31',
    description='Event Dispatch, a discrete time synchronizer',
    url='http://github.com/cyan-at/python-eventdispatch',
    author='Charlie Yan',
    author_email='cyanatg@gmail.com',
    license='Apache-2.0',
    install_requires=[],
    packages=find_packages(),
    entry_points=dict(
        console_scripts=[
            'eventdispatch_example_core=eventdispatch.example_core:main',
            'eventdispatch_cs_main=eventdispatch.composite_semaphore:main',
            'eventdispatch_example_cs=eventdispatch.example_cs:main',
            'eventdispatch_example_sim_mujoco=eventdispatch.example_sim_mujoco:main'
        ]
    )
)