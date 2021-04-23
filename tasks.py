#!/usr/bin/env python
"""
This is an Invoke file. https://www.pyinvoke.org/

To use it, you'll need to install Invoke on your system, and to
create a `.env` file in this directory.
It should look something like the `.env.sample` file. Please see
`README.md` for additional documentation.

Once set up, run `invoke -l` for a list of commands.
"""

from __future__ import print_function

try:
    input = raw_input
except NameError:
    pass

import getpass
import os
from pprint import pprint
from functools import partial
from time import sleep
import subprocess

from dotenv import load_dotenv, find_dotenv
from invoke import task, watchers, Failure


class bcolors:
    HEADER = "\033[95m"
    OKBLUE = "\033[94m"
    OKGREEN = "\033[92m"
    WARNING = "\033[93m"
    FAIL = "\033[91m"
    ENDC = "\033[0m"
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"


BASE_PATH = os.path.dirname(os.path.realpath(__file__))

SERVER_NAME = None
CONFIG_REPO_PATH = None
PIH_CONFIG = None
MYSQL_INSTALLATION = None
DOCKER = False
MODULES = (
    []
)  # an array of 3-tuples like ['org.openmrs.module', 'pihcore', '/path/to/openmrs-module-pihcore']
OTHER_REPOS = []


def load_env_vars():
    global SERVER_NAME, PIH_CONFIG, CONFIG_REPO_PATH, MYSQL_INSTALLATION, DOCKER, MODULES, OTHER_REPOS
    load_dotenv(find_dotenv(), override=True)
    SERVER_NAME = os.getenv("SERVER_NAME")
    CONFIG_REPO_PATH = os.path.normpath(
        os.path.join(
            BASE_PATH, os.getenv("CONFIG_REPO") or os.getenv("CONFIG_REPO_PATH")
        )
    )
    OTHER_REPOS = [
        os.path.normpath(os.path.join(BASE_PATH, r))
        for r in (os.getenv("OTHER_REPOS") or os.getenv("REPOS") or "").split(",")
        if r
    ]
    PIH_CONFIG = os.getenv("PIH_CONFIG")
    MYSQL_INSTALLATION = os.getenv("MYSQL_INSTALLATION")
    if MYSQL_INSTALLATION not in (None, "", "docker"):
        raise Exception(
            "Invalid environment variable MYSQL_INSTALLATION=" + MYSQL_INSTALLATION
        )
    DOCKER = MYSQL_INSTALLATION == "docker"
    if DOCKER:
        # OpenMRS handles server name differently if mysql is dockerized
        SERVER_NAME = db_name(SERVER_NAME)
    if os.path.exists(
        os.path.expanduser("~/openmrs/") + SERVER_NAME + "/openmrs-server.properties"
    ):
        watched_projects_line = subprocess.Popen(
            [
                "cat ~/openmrs/{env}/openmrs-server.properties | grep watched.projects".format(
                    env=SERVER_NAME
                )
            ],
            shell=True,
            stdout=subprocess.PIPE,
        ).communicate()[0]

        if watched_projects_line:
            MODULES = [
                m.split(",")
                for m in watched_projects_line.strip().split("=")[1].split(";")
            ]


def print_env_vars():
    print("Server: " + bcolors.BOLD + SERVER_NAME + bcolors.ENDC)
    print("Watched modules: " + ", ".join([m[1] for m in MODULES]))
    print("Config repo: " + CONFIG_REPO_PATH)
    print("Other repos: " + ", ".join(OTHER_REPOS))
    print("pih.config: " + PIH_CONFIG)
    print("MySQL installation type: " + (MYSQL_INSTALLATION or "normal install"))


def db_name(server_name):
    server_name_fixed = server_name.replace("-", "_")
    if DOCKER:
        return server_name_fixed
    return "openmrs_" + server_name_fixed


load_env_vars()


# OpenMRS Tasks ###############################################################


@task
def configure(ctx):
    """Updates openmrs-runtime.properties, the configuration file, for the server.
    Sets the sites according to PIH_CONFIG.
    """
    config_file = "~/openmrs/" + SERVER_NAME + "/openmrs-runtime.properties"
    print("Initial config file:\n")
    ctx.run("cat " + config_file)
    new_lines = ["pih.config=" + PIH_CONFIG]
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
def setenv(ctx, env_suffix):
    """
    Links the .env file with the given env_suffix.
    e.g. `invoke setenv chiapas` runs `ln -sf .env.chiapas .env`
    """
    file_name = ".env." + env_suffix
    if not os.path.isfile(os.path.join(BASE_PATH, file_name)):
        print("ERROR: No such env: " + env_suffix)
        print("  Try one of ")
        ctx.run("ls .env*")
        exit(1)
    with ctx.cd(BASE_PATH):
        ctx.run("ln -sf " + file_name + " .env")
    load_env_vars()


@task
def run(
    ctx,
    offline=False,
    skip_pull=False,
    skip_deploy=False,
    skip_enable_modules=False,
    env=None,
):
    """Pulls, deploys, enables modules, and then runs OpenMRS.
    Accepts default answers for openmrs-sdk:deploy.

    The `--env` flag can be used to change the active server and
    run that server at the same time. To just run a particular server,
    leaving the active server as-is, you can use the `--server` flag.
    """
    if env:
        setenv(ctx, env)
    print_env_vars()
    print()
    git_status(ctx)
    print()
    input("Check the above, then press Enter to continue, or Ctrl-C to abort.")
    print()
    if not skip_enable_modules:
        enable_modules(ctx)
    if not skip_pull and not offline:
        git_pull(ctx)
    if not skip_deploy:
        deploy(ctx, True, offline)
    build_config(ctx)
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
    if DOCKER:
        root_pswd = "Admin123"
    else:
        root_pswd = getpass.getpass("Database root password:")
    cmd = (
        "mvn openmrs-sdk:setup -DserverId=" + SERVER_NAME + " "
        "-Ddistro=org.openmrs.module:mirebalais:1.2-SNAPSHOT "
        "-DdbUri=jdbc:mysql://localhost:3306/"
        + db_name(SERVER_NAME)
        + " -DdbPassword='"
        + root_pswd
        + "' -e -X"
    )
    with ctx.cd(BASE_PATH):
        ctx.run(cmd, echo=True)
    build_config(ctx)


@task
def build_config(ctx):
    with ctx.cd(CONFIG_REPO_PATH):
        ctx.run("./install.sh " + SERVER_NAME)


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
    """Shows server name and brief git status information for each directory."""

    def fcn(d):
        branch = ctx.run("git rev-parse --abbrev-ref HEAD", hide=True).stdout.strip()
        changes = ctx.run("git status -s -uno", hide=True).stdout
        print(
            bcolors.BOLD
            + d.split("/")[-1]
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
def run_sql_file(ctx, file_path):
    with open(file_path) as f:
        file_text = f.read()
    run_sql(ctx, file_text)


@task
def mysql_shell(ctx):
    run_mysql_command(ctx, "", "-it", pty=True)


@task
def enable_modules(ctx):
    """Ensures that the mirebalais modules will be loaded on server startup"""
    sql_cmd = "update global_property set property_value='true' where property like '%started%';"
    run_sql(ctx, sql_cmd)


@task
def clear_address_hierarchy(ctx):
    """Clears the MySQL tables for address hierarchy. Deletes the configuration checksum to ensure it gets reloaded."""
    sql_code = (
        "set foreign_key_checks=0; "
        "delete from address_hierarchy_level; "
        "delete from address_hierarchy_entry; "
        "set foreign_key_checks=1; "
    )
    run_sql(ctx, sql_code)
    checksum_dir = "~/openmrs/" + SERVER_NAME + "/configuration_checksums/"
    ctx.run("rm -r " + checksum_dir)


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
def clear_all_data(ctx, num_persons_to_keep=2):
    """ Deletes all data (not metadata). """
    persons_id_string = ",".join([str(i) for i in range(1, num_persons_to_keep + 1)])
    sql_code = (
        "set foreign_key_checks=0; "
        "delete from patient_program; "
        "delete from obs; "
        "delete from encounter_provider; "
        "delete from encounter; "
        "delete from visit; "
        "delete from relationship; "
        "delete from patient_identifier; "
        "delete from patient; "
        "delete from person_address; "
        "delete from name_phonetics where person_name_id not in ("
        + persons_id_string
        + "); "
        "delete from person_name where person_name_id not in ("
        + persons_id_string
        + "); "
        "delete from person where person_id not in (" + persons_id_string + "); "
        "delete from provider where person_id not in (" + persons_id_string + "); "
        "delete from users where person_id not in (" + persons_id_string + "); "
        "delete from notification_alert_recipient; "
        "delete from notification_alert; "
        "set foreign_key_checks=1; "
    )
    run_sql(ctx, sql_code)


# Utils #######################################################################


def all_repos():
    return sorted(set([m[2] for m in MODULES] + OTHER_REPOS + [CONFIG_REPO_PATH]))


def in_each_directory(ctx, function, *args):
    with ctx.cd(BASE_PATH):
        for d in all_repos():
            with ctx.cd(d):
                function(d, *args)


def run_mysql_command(ctx, mysql_args, docker_args="", **ctx_run_args):
    user_result = ctx.run(
        "grep connection.username ~/openmrs/"
        + SERVER_NAME
        + '/openmrs-runtime.properties | cut -f2 -d"="',
        warn=False,
        hide=True,
    )
    pass_result = ctx.run(
        "grep connection.password ~/openmrs/"
        + SERVER_NAME
        + '/openmrs-runtime.properties | cut -f2 -d"="',
        warn=False,
        hide=True,
    )
    user = user_result.stdout.strip()
    password = pass_result.stdout.strip()
    command = "mysql -u {} --password='{}' {} {}".format(
        user, password, mysql_args, db_name(SERVER_NAME)
    )

    if DOCKER:
        start_mysql_docker_container(ctx)
        container_id_result = ctx.run(
            "docker ps | grep openmrs-sdk-mysql | cut -f1 -d' '", warn=False, hide=True
        )
        container_id = container_id_result.stdout.strip()
        command = "docker exec {} {} {}".format(docker_args, container_id, command)

    try:
        ctx.run(command, hide="stderr", **ctx_run_args)
    except Failure as e:
        if password:
            e.result.command = e.result.command.replace(password, "<redacted>")
        print(e)
        print(
            "If the password is incorrect, please check connection.properties in openmrs-server.properties"
        )


def run_sql(ctx, sql_code):
    """Runs some SQL code as root user on the database `openmrs_<server>`.

    `sql_code` must not contain double-quotes.
    """
    mysql_args = '-e "{}" 2>&1'.format(sql_code)
    run_mysql_command(ctx, mysql_args, "")


def start_mysql_docker_container(ctx):
    ctx.run("docker container start openmrs-sdk-mysql-v3-2")  # seems to be idempotent
