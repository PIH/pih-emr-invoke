# PIH OpenMRS Runner

This is a [PyInvoke](https://www.pyinvoke.org/) program that facilitates working
with OpenMRS. It helps with setup, running, and git management of multiple
repositories.

This repository should be the parent directory of all of your OpenMRS
directories. Please see the "Setup" section appropriate to your situation, whether
you need to set up PIH EMR or you just want to use this with an existing
setup.

## What does it do?

Once everything is set up, you can view the list of commands with

```
invoke -l
```

There are a few different families of commands:

- Git commands such as `invoke git-status` (I alias this to `igs`—I use it a lot)
- MySQL commands such as `invoke enable-modules`
- Maven commands such as `invoke run` (try `invoke run --help`) 
- `invoke setenv`, which changes which `.env.*` file is active (by virtue of being symlinked to `.env`)


## Setup with existing OpenMRS development environment

These are the instructions for people who already have modules checked out and
servers set up. If you're new to OpenMRS / PIH-EMR, please see the instructions
below under "First-time setup."

Assuming the parent directory of your OpenMRS directories is not yet a git
repository, `cd` to that directory and do

```
git init
git remote add origin git@github.com:PIH/pih-emr-invoke.git
git pull origin master
sudo pip install -r requirements.txt
```

If you prefer, rather than doing `sudo pip` to install to your global Python
environment, you could create a virtualenv for this. But as of this writing
it's just [PyInvoke](https://www.pyinvoke.org/index.html) and
[python-dotenv](https://github.com/theskumar/python-dotenv), which you're liable
to want to use in every project for the rest of your life.

At this point we should create an `.env.*` file, which will define an OpenMRS
working environment. Please see "[The .env file](#the-env-file)" below to finish
setup. Once done, you should be able to run `invoke` commands.

## First-time setup of OpenMRS on Ubuntu

I suggest [installing Docker](https://docs.docker.com/install/linux/docker-ce/ubuntu/)
and using a dockerized MySQL (don't worry, the OpenMRS SDK will manage it all
for you). Otherwise, you will need to install MySQL 5.6 (no other version will do).

```
sudo add-apt-repository 'deb http://archive.ubuntu.com/ubuntu trusty universe'
sudo apt-get update

# Install Git, Java, Maven, and PyInvoke
sudo apt install -y \
    build-essential \
    git \
    maven \
    openjdk-8-jdk \
    openjdk-8-jre \
    python-dev \
    python-invoke

# Set up OpenMRS SDK
mvn org.openmrs.maven.plugins:openmrs-sdk-maven-plugin:setup-sdk

# Set up PIH EMR Invoke
git clone git@github.com:brandones/pih-emr-workspace.git pihemr
cd pihemr/
git clone https://github.com/PIH/mirebalais-puppet.git
```

At this point we should create an `.env.*` file, which will define an OpenMRS
working environment. Please see "[The .env file](#the-env-file)" below,
then come back here.

...

Okay, you have a `.env` file? Let's continue then.

```
invoke setup
```

The only tricky question is which MySQL to use. If you're using docker, always
pick (2), even if you already have a docker container.

```
invoke run -sk
```

Navigate to http://localhost:8080/openmrs (or whatever port, if you 
used a different port). It will do some initial setup. In the end, 
the logs will show a bunch of errors, but the UI will show that the 
instance has been set up.  You should cancel the current run (Ctrl-C 
in the terminal window).

```
invoke configure
```
And check that the utput looks okay. If so,
```
invoke run -sk
```
once again. Startup should take several minutes as it loads in all 
required metadata, etc, for the first time.

Future runs can be executed with `invoke run`, which automatically
does a git pull, maven deploy, and enables all modules before running.

## The .env file

To set up the `.env` file, do `cp .env.sample .env.mysite` and then edit
`.env.mysite` to have the correct values:

- `SERVER_NAME` is the OpenMRS SDK [serverId](https://wiki.openmrs.org/display/docs/OpenMRS+SDK+Step+By+Step+Tutorials). Write something lowercase with dashes, like `foo-bar`. The corresponding MySQL database will be `openmrs_foo_bar`.
- `REPOS` should be a comma-separated list of the subdirectories of the current directory that you are working with. The ones that are git repositories will be used for all the `git-` Invoke commands. The ones that are OpenMRS modules will be used for all the Invoke commands that use Maven.
- `APP_DATA_DIR` should be the path to the directory containing the application data directory configuration files, such as `configuration/addresshierarchy` or `frontend/`. It's probably `/path/to/mirebalais-puppet/mirebalais-modules/openmrs/files/app-data-config`.
- `PIH_CONFIG_DIR` should be the path to the directory containing your PIH Config file. It's probably `/path/to/mirebalais-puppet/mirebalais-modules/openmrs/files/config`.
- `PIH_CONFIG` is a comma-separated list of PIH Config files. See the files in the [PIH Config Directory](https://github.com/PIH/mirebalais-puppet/tree/master/mirebalais-modules/openmrs/files/config), and drop the `pih-config-` prefix and the `.json` suffix.
- `MYSQL_INSTALLATION` should be set to `docker` if you are using openmrs-sdk-mysql for MySQL. Otherwise omit it.

Finally, run `invoke setenv mysite`, where `mysite` is the suffix of your `.env` file.

