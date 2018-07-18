#!/usr/bin/env python

import os
from invoke import task

BASE_PATH = os.path.dirname(os.path.realpath(__file__))

SERVER_NAME = "chiapas"

@task
def setup(ctx):
    cmd = "mvn openmrs-sdk:setup -DserverId=" + SERVER_NAME + " " \
          "-Ddistro=org.openmrs.module:mirebalais:1.2-SNAPSHOT " \
          "-DdbUri=jdbc:mysql://localhost:3306/openmrs_chiapas " \
          "-DdbUser=root -DdbPassword='asdf;lkj'"
    with ctx.cd(BASE_PATH):
        ctx.run(cmd)

@task
def configure(ctx):
    config_file = "~/openmrs/" + SERVER_NAME + "/openmrs-runtime.properties"
    print("Starting config file:\n")
    ctx.run("cat " + config_file)
    print("\n\nThe following should be a bunch of JSON files. If it's not, the "
          "pih config dir path is wrong and you need to edit this code.")
    pih_config_dir = "/home/brandon/Code/pih/mirebalais-puppet/mirebalais-modules/openmrs/files/config"
    ctx.run("ls " + pih_config_dir)
    new_lines = [
            "pih.config=mexico",
            "pih.config.dir=" + pih_config_dir]
    cmds = ["echo '{}' >> {}".format(l, config_file) for l in new_lines]
    for cmd in cmds:
        ctx.run(cmd)
    print("\n\nUpdated config file:\n")
    ctx.run("cat " + config_file)

@task
def run(ctx):
    """Runs OpenMRS"""
    cmd = "mvn openmrs-sdk:run -e -X -DserverId=" + SERVER_NAME
    with ctx.cd(BASE_PATH):
        ctx.run(cmd)

@task
def clean(ctx):
    cmd = "mvn clean"
    ctx.run(cmd)

@task
def install(ctx):
    cmd = "mvn install -e -DskipTests=true"
    ctx.run(cmd)

@task
def pull(ctx):
    cmd = "mvn openmrs-sdk:pull"
    ctx.run(cmd)

@task
def watch(ctx):
    cmd = "mvn openmrs-sdk:watch -DserverId=" + SERVER_NAME
    ctx.run(cmd)

