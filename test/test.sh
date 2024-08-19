#!/usr/bin/env bash

set -euo pipefail

function run() {
    if ! LOG=$("$@" 2>&1); then
      STATUS=$?
      echo "$LOG"
      exit $STATUS
    fi
}

echo "Running default test"
run python -m ansible.cli.playbook playbook_prepare.yaml
ANSIBLE_CALLBACK_PLUGINS=.. run python -m ansible.cli.playbook default/playbook.yaml -i default/inventory.yaml -vvv
run python -m ansible.cli.playbook playbook_check.yaml -e expected_records=20 -vvv
run python -m ansible.cli.playbook playbook_cleanup.yaml

# Check with dumps
echo "Running dump test"
run python -m ansible.cli.playbook playbook_prepare.yaml
LOKI_ENABLED_DUMPS=task ANSIBLE_CALLBACK_PLUGINS=.. run python -m ansible.cli.playbook default/playbook.yaml -i default/inventory.yaml -vvv
run python -m ansible.cli.playbook playbook_check.yaml -e expected_records=26 -vvv
run python -m ansible.cli.playbook playbook_cleanup.yaml