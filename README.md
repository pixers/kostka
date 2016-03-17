Kostka
======
Kostka is a simple, extensible container manager written in Python.

It's main objective is to be replaced easily by something else. To achieve that, it creates containers using tools available in a standard Debian installation, so that one could easily reproduce the whole process in a shell script. Kostka creates standard systemd units and spawns them with systemd-nspawn. After creating a container, kostka does not have any relation with it. It does not maintain any central registry of containers, does not have a daemon, and generally is a simple interface for shell commands.

Motivation
==========
Most container managers out there try to manage important parts of your container without giving you much control. Examples include networking, startup, etc. Usually, there is no way to influence that, because everything is done by the container manager at runtime.

Kostka is different. Instead of using manifests to start a container, it creates a systemd unit file that can be modified freely. It will overwrite the unit when asked to, but otherwise doesn't care what's inside once the unit is created.

Installation
============

    # pip3 install -U .

Kostka is a python3 package, and can be installed as one. Because it writes to `/etc`, it has to be run as root.

Dependencies
============
Kostka requires systemd, systemd-nspawn, [setup-netns][1], and a kernel that supports overlayfs. That means debian stretch or higher.
Kostka assumes that it runs on debian (by, for example, writing to `/etc/network/interfaces.d` when available), but doesn't require it.

  [1]: https://github.com/pixers/setup-netns
