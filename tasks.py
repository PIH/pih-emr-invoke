#!/usr/bin/env python

import getpass
import os
import re
from invoke import task, watchers

BASE_PATH = os.path.dirname(os.path.realpath(__file__))

SERVER_NAME = "chiapas"


class AlertWatcher(watchers.StreamWatcher):
    def __init__(self, pattern):
        self.pattern = pattern

    def submit(self, stream_data):
        # Search, across lines if necessary
        matches = re.findall(self.pattern, stream_data, re.S)
        if matches:
            print("FOUND A MATCH, TEXTING!!!!")
            os.system('textme "OpenMRS is running"')


@task
def setup(ctx):
    pswd = getpass.getpass("database root password:")
    cmd = (
        "mvn openmrs-sdk:setup -DserverId=" + SERVER_NAME + " "
        "-Ddistro=org.openmrs.module:mirebalais:1.2-SNAPSHOT "
        "-DdbUri=jdbc:mysql://localhost:3306/openmrs_"
        + SERVER_NAME
        + " -DdbUser=root -DdbPassword='"
        + pswd
        + "'"
    )
    with ctx.cd(BASE_PATH):
        ctx.run(cmd)


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
def run(ctx):
    """Runs OpenMRS"""
    watcher = AlertWatcher(r"Apache Maven")
    # watcher = AlertWatcher(r"Checking if port 8080 is in use... \[free\]")
    cmd = (
        "mvn openmrs-sdk:run -e -X -DserverId="
        + SERVER_NAME
        + " 2>&1 "
        + " | tee /dev/tty"
        + " | awk '/org.apache.coyote.AbstractProtocol start/ { system(\"textme OpenMRS\") }'"
        # + " | awk '/Starting ProtocolHandler/ { system(\"textme OpenMRS\") }'"
        # + " | awk '/platform encoding: UTF-8/ { system(\"textme UTF\") }'"
        # + ' | awk \'/OS name: "linux"/ { system("textme openmrs") }\''
        # + " | awk '/Checking if port 8080 is in use... \[free\]/ { system(\"textme openmrs\") }'"
        # + " | awk '/Apache Maven 3.5.2/ { system(\"textme\") }'"
    )
    with ctx.cd(BASE_PATH):
        ctx.run(cmd, watchers=[watcher])


@task
def clean(ctx):
    cmd = "mvn clean"
    ctx.run(cmd)


@task
def install(ctx):
    cmd = "mvn install -e -DskipTests=true"
    ctx.run(cmd)


@task
def deploy(ctx):
    """Runs Maven deploy for Mirebalais. Updates dependencies."""
    with ctx.cd(BASE_PATH + "/openmrs-module-mirebalais"):
        cmd = "mvn openmrs-sdk:deploy -Ddistro=api/src/main/resources/openmrs-distro.properties -U"
        ctx.run(cmd)


@task
def pull(ctx):
    cmd = "mvn openmrs-sdk:pull"
    ctx.run(cmd)


@task
def watch(ctx):
    cmd = "mvn openmrs-sdk:watch -DserverId=" + SERVER_NAME
    ctx.run(cmd)
