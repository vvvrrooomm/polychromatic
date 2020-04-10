#!/bin/bash
#
# Validates Python files for errors. Uses 'pylint'.
#

if [ -z "$(which pylint)" ]; then
    echo "'pylint' not installed."
    exit 1
fi

errors=false
function check_status() {
    if [ $? != 0 ]; then
        errors=true
    fi
}

pylint --errors-only \
    --disable="relative-beyond-top-level" \
    --disable="no-name-in-module" \
    polychromatic-controller \
    polychromatic-tray-applet \
    polychromatic-cli \
    pylib/*.py \
    pylib/backends/*.py

check_status $?

if [ $errors == true ]; then
    exit 1
fi