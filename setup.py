from distutils.core import setup

setup(
    name='persistent-identifier-service',
    version='0.0.1',
    packages=['ompid', 'tests'],
    url='',
    license='',
    author='Patrick Westphal',
    author_email='',
    description='',
    install_requires=[
        'fastapi==0.55.1',
        'uvicorn==0.12.3',
        'SQLAlchemy==1.3.17',
        'PyYAML==5.3.1',
        'pydantic==1.5.1',
        'psycopg2==2.8.5',
        'pytest-postgresql==2.5.3',
        'pytest==6.2.2',
        'requests==2.25.1',
    ]
)
