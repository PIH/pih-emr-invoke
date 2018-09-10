#!/usr/bin/env python

import getpass
import os
from invoke import task

BASE_PATH = os.path.dirname(os.path.realpath(__file__))

SERVER_NAME = "chiapas"
DB_NAME = "openmrs_" + SERVER_NAME


@task
def configure(ctx):
    config_file = "~/openmrs/" + SERVER_NAME + "/openmrs-runtime.properties"
    print("Starting config file:\n")
    ctx.run("cat " + config_file)
    print(
        "\n\nThe following should be a bunch of JSON files. If it's not, the "
        "pih config dir path is wrong and you need to edit this code."
    )
    pih_config_dir = "/home/brandon/Code/pih/mirebalais-puppet/mirebalais-modules/openmrs/files/config"
    ctx.run("ls " + pih_config_dir)
    new_lines = ["pih.config=mexico", "pih.config.dir=" + pih_config_dir]
    cmds = ["echo '{}' >> {}".format(l, config_file) for l in new_lines]
    for cmd in cmds:
        ctx.run(cmd)
    print("\n\nUpdated config file:\n")
    ctx.run("cat " + config_file)


@task
def deploy(ctx):
    """Runs Maven deploy for Mirebalais. Updates dependencies."""
    with ctx.cd(BASE_PATH + "/openmrs-module-mirebalais"):
        cmd = "mvn openmrs-sdk:deploy -Ddistro=api/src/main/resources/openmrs-distro.properties -U"
        ctx.run(cmd)


@task
def enable_modules(ctx):
    print "Requesting mysql root password..."
    ctx.run(
        "mysql -u root -p -e \"update global_property set property_value='true' where property like '%started%';\" "
        + DB_NAME
    )


@task
def install(ctx):
    cmd = "mvn clean install -e -DskipTests=true"
    ctx.run(cmd)


@task
def pull(ctx):
    cmd = "mvn openmrs-sdk:pull"
    ctx.run(cmd)


@task
def run(ctx):
    """Runs OpenMRS"""
    cmd = (
        "mvn openmrs-sdk:run -e -X -DserverId="
        + SERVER_NAME
        + " | tee /dev/tty"
        + ' | awk -Winteractive \'/Starting ProtocolHandler/ { system("textme OpenMRS is ready") }'
        + '                      /Connect remote debugger/ { system("notify-send debugger") }\''
    )
    with ctx.cd(BASE_PATH):
        ctx.run(cmd, pty=True)


@task
def setup(ctx):
    pswd = getpass.getpass("database root password:")
    cmd = (
        "mvn openmrs-sdk:setup -DserverId=" + SERVER_NAME + " "
        "-Ddistro=org.openmrs.module:mirebalais:1.2-SNAPSHOT "
        "-DdbUri=jdbc:mysql://localhost:3306/"
        + DB_NAME
        + " -DdbUser=root -DdbPassword='"
        + pswd
        + "'"
    )
    with ctx.cd(BASE_PATH):
        ctx.run(cmd)


@task
def watch(ctx):
    cmd = "mvn openmrs-sdk:watch -DserverId=" + SERVER_NAME
    ctx.run(cmd)
