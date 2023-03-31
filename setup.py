from setuptools import setup

with open("requirements.txt", "r") as handle:
    requirements = handle.readlines()

if __name__ == "__main__":
    setup(
        install_requires=requirements
    )
