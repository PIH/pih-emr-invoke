#!/bin/bash

cp -r dotfiles ~
cd ~/dotfiles
./link

cd /etc
sudo git clone https://github.com/PIH/mirebalais-puppet puppet
cd /etc/puppet
sudo ./install.sh
