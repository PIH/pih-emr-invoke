# CES OpenMRS

Dev server set up using local MySQL. Server port 8080, debug port 8081.
See the settings in detail in the Invoke file.

## Ubuntu Setup

Starting from Ubuntu 16.04...

sudo add-apt-repository 'deb http://archive.ubuntu.com/ubuntu trusty universe'
sudo apt-get update

sudo apt install -y \
    build-essential \
    git \
    maven \
    openjdk-8-jdk \
    openjdk-8-jre \
    mysql-server-5.6 \
    mysql-client-5.6 \
    python-pip \
    python-dev

sudo pip install --upgrade pip 
sudo pip install --upgrade virtualenv
pip install invoke getpass

sudo service mysql start

mvn org.openmrs.maven.plugins:openmrs-sdk-maven-plugin:setup-sdk

git clone https://github.com/PIH/mirebalais-puppet.git


