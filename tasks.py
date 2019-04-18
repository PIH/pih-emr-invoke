#!/usr/bin/env python

from __future__ import print_function

import getpass
import os
from pprint import pprint
from invoke import task, watchers

BASE_PATH = os.path.dirname(os.path.realpath(__file__))

SERVER_NAME = "chiapas"
DB_NAME = "openmrs_" + SERVER_NAME


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
def configure(ctx):
    """Updates openmrs-runtime.properties, the configuration file, for the server.
    Sets the sites to mexico, mexico-salvador.
    """
    config_file = "~/openmrs/" + SERVER_NAME + "/openmrs-runtime.properties"
    print("Starting config file:\n")
    ctx.run("cat " + config_file)
    print(
        "\n\nThe following should be a bunch of JSON files. If it's not, the "
        "pih config dir path is wrong and you need to edit this code."
    )
    pih_config_dir = "/home/brandon/Code/pih/mirebalais-puppet/mirebalais-modules/openmrs/files/config"
    ctx.run("ls " + pih_config_dir)
    new_lines = [
        "pih.config=mexico,mexico-salvador",
        "pih.config.dir=" + pih_config_dir,
    ]
    cmds = ["echo '{}' >> {}".format(l, config_file) for l in new_lines]
    for cmd in cmds:
        ctx.run(cmd)
    print("\n\nUpdated config file:\n")
    ctx.run("cat " + config_file)


@task
def deploy(ctx, no_prompt=False, offline=False):
    """Runs Maven deploy for Mirebalais. Updates dependencies."""
    with ctx.cd(BASE_PATH + "/openmrs-module-mirebalais"):
        cmd = (
            ("yes | " if no_prompt else "")
            + "mvn openmrs-sdk:deploy"
            + " -Ddistro=api/src/main/resources/openmrs-distro.properties"
            + (" --offline" if offline else "")
            + " -U -DserverId="
            + SERVER_NAME
        )
        ctx.run(cmd)


@task
def update_dep(ctx):
    """Runs openmrs-sdk:deploy from outside any module.

    Use this when on starting you encounter error messages of the form

    `Foo Module cannot be started because it requires the following module(s): Bar 1.2.3-SNAPSHOT`
    """
    print("When prompted, respond:")
    print("  1 - module")
    print("  2 - default (org.openmrs.module)")
    print("  3 - the name of the missing module")
    print("  4 - latest snapshot version that you need")
    print()
    cmd = "mvn openmrs-sdk:deploy" + " -U -DserverId=" + SERVER_NAME
    ctx.run(cmd)


@task
def update_deps(ctx, missing_modules_list):  # doesn't work
    """Doesn't work, don't use.
    
    Runs update-dep for each module and version in the given list.

    List should be in the format given by the "Error starting Module" error,
    something like:

        "paperrecord 1.3.0, radiologyapp 1.4.0, edtriageapp 1.1.0-SNAPSHOT"
    """
    cmd = "mvn openmrs-sdk:deploy" + " -U -DserverId=" + SERVER_NAME
    name_version_strings = missing_modules_list.split(", ")
    name_version_pairs = [nv.split(" ") for nv in name_version_strings]
    pprint(name_version_pairs)
    for module_name, version in name_version_pairs:
        responders = []
        responders.append(watchers.Responder("What would you like to deploy?", "1\n"))
        responders.append(watchers.Responder("Please specify groupId", "\n"))
        print("\n\nNow running for {} {}\n".format(module_name, version))
        responders.append(
            watchers.Responder("Please specify artifactId", module_name + "\n")
        )
        test_string = "You can deploy the following versions of the module:(.*\n){{1,7}}{}\) {}(.*\n){{1,7}}Which one do you choose\? \[.*\]:"
        for i in range(1, 7):
            responders.append(
                watchers.Responder(test_string.format(i, version), str(i) + "\n")
            )
        ctx.run(cmd, watchers=responders)


@task
def install(ctx):
    """Runs mvn clean install -e -DskipTests=true"""
    cmd = "mvn clean install -e -DskipTests=true"
    ctx.run(cmd)


@task
def run(ctx, offline=False, skip_pull=False, skip_deploy=False):
    """Pulls, deploys and then runs OpenMRS. Accepts default answers for openmrs-sdk:deploy."""
    if not skip_pull and not offline:
        git_pull(ctx)
    if not skip_deploy:
        deploy(ctx, True, offline)
    cmd = (
        "mvn openmrs-sdk:run -e -X"
        + (" --offline" if offline else "")
        + " -DserverId="
        + SERVER_NAME
        + " | tee /dev/tty"
        + ' | awk -Winteractive \'/Starting ProtocolHandler/ { system("textme OpenMRS is ready") }'
        + '                      /Connect remote debugger/ { system("notify-send debugger") }\''
    )
    with ctx.cd(BASE_PATH):
        ctx.run(cmd, pty=True)


@task
def setup(ctx):
    """Runs mvn openmrs-sdk:setup with the appropriate arguments"""
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
    """Shows brief git status information for each directory.

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

    in_each_directory(ctx, fcn)


# MySQL Tasks #################################################################


@task
def enable_modules(ctx):
    """Ensures that the mirebalais modules will be loaded on server startup"""
    sql_cmd = "update global_property set property_value='true' where property like '%started%';"
    run_sql(ctx, sql_cmd)


@task
def clear_address_hierarchy(ctx):
    """Clears the MySQL tables for address hierarchy."""
    sql_code = (
        "set foreign_key_checks=0; "
        "delete from address_hierarchy_level; "
        "delete from address_hierarchy_entry; "
        "set foreign_key_checks=1; "
    )
    run_sql(ctx, sql_code)


@task
def clear_idgen(ctx):
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
    run_sql(ctx, sql_code)


@task
def clear_all_data(ctx):
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
    run_sql(ctx, sql_code)


# Utils #######################################################################


def in_each_directory(ctx, function, *args):
    dirs = [
        "openmrs-module-mirebalais",
        "openmrs-module-pihcore",
        "openmrs-module-mirebalaismetadata",
        "mirebalais-puppet",
        "openmrs-module-initializer",
    ]
    with ctx.cd(BASE_PATH):
        for d in dirs:
            with ctx.cd(d):
                function(d, *args)


def run_sql(ctx, sql_code):
    """Runs some SQL code as root user on the database specified by `DB_NAME`.

    `sql_code` must not contain double-quotes.
    """
    print("Requesting mysql root password...")
    ctx.run('mysql -u root -p -e "{}" {}'.format(sql_code, DB_NAME))
