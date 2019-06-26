#!/usr/bin/env python
"""
This is an Invoke file. https://www.pyinvoke.org/

To use it, you'll need to install Invoke on your system.

Run `invoke -l` for a list of commands.

To get started, you'll need to create a .env file in this directory.
It should look something like

```
SERVER_NAME=myserver
MODULES=openmrs-module-mirebalais,mirebalais-puppet
PIH_CONFIG=mexico,mexico-salvador
```

PIH_CONFIG is used by `invoke configure`. REPOS is used by all of the
commands that run in each repository you're working on, such as
`invoke git-status`.

"""

from __future__ import print_function

import getpass
import os
from pprint import pprint

from dotenv import load_dotenv, find_dotenv
from invoke import task, watchers

BASE_PATH = os.path.dirname(os.path.realpath(__file__))

load_dotenv(find_dotenv())

SERVER_NAME = os.getenv("SERVER_NAME")
MODULES = os.getenv("REPOS").split(",")
PIH_CONFIG = os.getenv("PIH_CONFIG")


def db_name(server_name):
    return "openmrs_" + server_name


class bcolors:
    HEADER = "\033[95m"
    OKBLUE = "\033[94m"
    OKGREEN = "\033[92m"
    WARNING = "\033[93m"
    FAIL = "\033[91m"
    ENDC = "\033[0m"
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"


# OpenMRS Tasks ###############################################################


@task
def configure(ctx, server=SERVER_NAME):
    """Updates openmrs-runtime.properties, the configuration file, for the server.
    Sets the sites to mexico, mexico-salvador.
    """
    config_file = "~/openmrs/" + server + "/openmrs-runtime.properties"
    print("Starting config file:\n")
    ctx.run("cat " + config_file)
    print(
        "\n\nThe following should be a bunch of JSON files. If it's not, the "
        "pih config dir path is wrong and you need to edit this code."
    )
    pih_config_dir = "/home/brandon/Code/pih/mirebalais-puppet/mirebalais-modules/openmrs/files/config"
    ctx.run("ls " + pih_config_dir)
    new_lines = ["pih.config=" + PIH_CONFIG, "pih.config.dir=" + pih_config_dir]
    cmds = ["echo '{}' >> {}".format(l, config_file) for l in new_lines]
    for cmd in cmds:
        ctx.run(cmd)
    print("\n\nUpdated config file:\n")
    ctx.run("cat " + config_file)


@task
def deploy(ctx, no_prompt=False, offline=False, server=SERVER_NAME):
    """Runs Maven deploy for Mirebalais. Updates dependencies."""
    with ctx.cd(BASE_PATH + "/openmrs-module-mirebalais"):
        cmd = (
            ("yes | " if no_prompt else "")
            + "mvn openmrs-sdk:deploy"
            + " -Ddistro=api/src/main/resources/openmrs-distro.properties"
            + (" --offline" if offline else "")
            + " -U -DserverId="
            + server
        )
        ctx.run(cmd)


@task
def setenv(ctx, env_suffix):
    """
    Links the .env file with the given env_suffix.
    e.g. `invoke setenv chiapas` runs `ln -sf .env.chiapas .env`
    """
    file_name = ".env." + env_suffix
    if not os.path.isfile(file_name):
        print("ERROR: No such env: " + env_suffix)
        exit(1)
    ctx.run("ln -sf " + file_name + " .env")


@task
def run(
    ctx,
    offline=False,
    skip_pull=False,
    skip_deploy=False,
    skip_enable_modules=False,
    server=SERVER_NAME,
):
    """Pulls, deploys, enables modules, and then runs OpenMRS.
    Accepts default answers for openmrs-sdk:deploy.
    """
    if not skip_pull and not offline:
        git_pull(ctx)
    if not skip_deploy:
        deploy(ctx, True, offline, server)
    if not skip_enable_modules:
        enable_modules(ctx, server)
    cmd = (
        "mvn openmrs-sdk:run -e -X"
        + (" --offline" if offline else "")
        + " -DserverId="
        + server
        + " | tee /dev/tty"
        + ' | awk -Winteractive \'/Starting ProtocolHandler/ { system("textme OpenMRS is ready") }'
        + '                      /Connect remote debugger/ { system("notify-send debugger") }\''
    )
    with ctx.cd(BASE_PATH):
        ctx.run(cmd, pty=True)


@task
def setup(ctx, server=SERVER_NAME):
    """Runs mvn openmrs-sdk:setup with the appropriate arguments"""
    pswd = getpass.getpass("database root password:")
    cmd = (
        "mvn openmrs-sdk:setup -DserverId=" + server + " "
        "-Ddistro=org.openmrs.module:mirebalais:1.2-SNAPSHOT "
        "-DdbUri=jdbc:mysql://localhost:3306/"
        + db_name(server)
        + " -DdbUser=root -DdbPassword='"
        + pswd
        + "'"
    )
    with ctx.cd(BASE_PATH):
        ctx.run(cmd)


@task
def watch(ctx, server=SERVER_NAME):
    cmd = "mvn openmrs-sdk:watch -DserverId=" + server
    ctx.run(cmd)


# Git Tasks ###################################################################


@task
def git_branch_find(ctx, branch_name):
    """Tells you what directories have a branch named `branch_name`"""

    def fcn(d, branch_name):
        res = ctx.run(
            "git show-ref --verify --quiet refs/heads/" + branch_name, warn=True
        )
        if res.exited == 0:
            print(d)

    in_each_directory(ctx, fcn, branch_name)


@task
def git_checkout(ctx, branch_name):
    """Checks out `branch_name` in each directory in which it exists"""

    def fcn(d, branch_name):
        res = ctx.run(
            "git show-ref --verify --quiet refs/heads/" + branch_name, warn=True
        )
        if res.exited == 0:
            ctx.run("git checkout " + branch_name, hide=True)

    in_each_directory(ctx, fcn, branch_name)
    git_status(ctx)


@task
def git_pull(ctx):
    """Does `git pull` in each directory that is on `master`, and `git fetch` in each other directory"""

    def fcn(d):
        print(bcolors.BOLD + d + bcolors.ENDC)
        branch = ctx.run("git rev-parse --abbrev-ref HEAD", hide=True).stdout.strip()
        print("On branch " + branch)
        if branch == "master":
            print("Pulling...")
            ctx.run("git pull")
        else:
            print("Fetching...")
            ctx.run("git fetch")

    in_each_directory(ctx, fcn)


@task
def git_push(ctx, branch_name, force=False):
    """Does `git push fork $(branch_name)` for each directory on branch `branch_name`.
    
    Expects that there is a remote named 'fork'. Fork the repository you're interested in
    and do `git remote add fork $(my_fork_url)`.
    """

    def fcn(d, branch_name):
        res = ctx.run(
            "git show-ref --verify --quiet refs/heads/" + branch_name, warn=True
        )
        if res.exited == 0:
            print(bcolors.BOLD + d + bcolors.ENDC)
            ctx.run(
                "git push fork {} {}".format(branch_name, "--force" if force else "")
            )

    in_each_directory(ctx, fcn, branch_name)


@task
def git_status(ctx):
    """Shows server name and brief git status information for each directory.

    Ignores directories that are on master and have no changes."""

    def fcn(d):
        branch = ctx.run("git rev-parse --abbrev-ref HEAD", hide=True).stdout.strip()
        changes = ctx.run("git status -s -uno", hide=True).stdout
        if branch != "master" or changes:
            print(
                bcolors.BOLD
                + d
                + bcolors.ENDC
                + ": "
                + bcolors.OKBLUE
                + branch
                + bcolors.ENDC
            )
            if changes:
                print(bcolors.HEADER, end="")
                print(changes, end="")
                print(bcolors.ENDC, end="")

    print("Server: " + SERVER_NAME)
    in_each_directory(ctx, fcn)


# MySQL Tasks #################################################################


@task
def enable_modules(ctx, server=SERVER_NAME):
    """Ensures that the mirebalais modules will be loaded on server startup"""
    sql_cmd = "update global_property set property_value='true' where property like '%started%';"
    run_sql(ctx, sql_cmd, server)


@task
def clear_address_hierarchy(ctx, server=SERVER_NAME):
    """Clears the MySQL tables for address hierarchy. Deletes the configuration checksum to ensure it gets reloaded."""
    sql_code = (
        "set foreign_key_checks=0; "
        "delete from address_hierarchy_level; "
        "delete from address_hierarchy_entry; "
        "set foreign_key_checks=1; "
    )
    run_sql(ctx, sql_code, server)
    checksum_dir = "~/openmrs/" + server + "/configuration_checksums/"
    ctx.run("rm -r " + checksum_dir)


@task
def clear_idgen(ctx, server=SERVER_NAME):
    """Clears the MySQL tables for idgen."""
    sql_code = (
        "set foreign_key_checks=0; "
        "delete from idgen_auto_generation_option; "
        "delete from idgen_id_pool; "
        "delete from idgen_identifier_source; "
        "delete from idgen_log_entry; "
        "delete from idgen_pooled_identifier; "
        "delete from idgen_remote_source; "
        "delete from idgen_reserved_identifier; "
        "delete from idgen_seq_id_gen; "
        "set foreign_key_checks=1; "
    )
    run_sql(ctx, sql_code, server)


@task
def clear_all_data(ctx, server=SERVER_NAME):
    """ Deletes all patients, encounters, and obs. """
    sql_code = (
        "set foreign_key_checks=0; "
        "delete from obs; "
        "delete from encounter_provider; "
        "delete from encounter; "
        "delete from patient_identifier; "
        "delete from patient; "
        "delete from name_phonetics where person_name_id not in (1,2,3,4,5,6); "
        "delete from person_name where person_name_id not in (1,2,3,4,5,6); "
        "delete from person where person_id not in (1,2,3,4,5,6); "
        "set foreign_key_checks=1; "
    )
    run_sql(ctx, sql_code, server)


# Utils #######################################################################


def in_each_directory(ctx, function, *args):
    with ctx.cd(BASE_PATH):
        for d in MODULES:
            with ctx.cd(d):
                function(d, *args)


def run_sql(ctx, sql_code, server=SERVER_NAME):
    """Runs some SQL code as root user on the database `openmrs_<server>`.

    `sql_code` must not contain double-quotes.
    """
    print("Requesting mysql root password...")
    ctx.run('mysql -u root -p -e "{}" {}'.format(sql_code, db_name(server)))
