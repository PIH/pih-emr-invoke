#!/usr/bin/env python

import os
from invoke import task

BASE_PATH = os.path.dirname(os.path.realpath(__file__))


@task
def run_disk(ctx, disk):
    ctx.run(
        "sudo qemu-system-x86_64 -enable-kvm -m 4G "  # CPU virtualization and RAM
        + "-usb -device usb-tablet "  # make touchpad & keyboard work
        + "-vga cirrus "  # grapics card driver supporting higher resolutions
        + "-drive format=raw,file="
        + disk
    )
