# CES OpenMRS

Dev server set up using local MySQL. Server port 8080, debug port 8081.
See the settings in detail in the Invoke file.

## Ubuntu Setup

Starting from Ubuntu 16.04...

```
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
    python-dev \
    python-invoke

sudo service mysql start

mvn org.openmrs.maven.plugins:openmrs-sdk-maven-plugin:setup-sdk

git clone git@github.com:brandones/pih-emr-workspace.git pihemr
cd pihemr/
git clone https://github.com/PIH/mirebalais-puppet.git

invoke setup
invoke run
```

`chromium http://localhost:8080`

ctrl-c out of the 'invoke run' when the database update completes

```
invoke configure
invoke run
```

`chromium http://localhost:8080/openmrs/login.htm`

