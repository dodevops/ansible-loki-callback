# ansible-loki-callback: An Ansible callback plugin that logs to a loki instance

## Requirements

* Python3
* Ansible

## Installation

Download or clone the repository and install the requirements:

   pip install -r requirements.txt

## Usage

Use the following environment variables to configure the plugin:

* LOKI_URL: URL to the Loki Push API endpoint (https://loki.example.com/api/v1/push)
* LOKI_USERNAME: Username to authenticate at loki (optional)
* LOKI_PASSWORD: Password to authenticate at loki (optional)
* LOKI_DEFAULT_TAGS: A comma separated list of key:value pairs used for every log line (optional)
* LOKI_ORG_ID: Loki organization id (optional)

Then set `ANSIBLE_CALLBACK_PLUGINS` to the path where you downloaded or cloned the repository to.

## Testing

The example directory contains a test playbook that can be used to test the callback plugin. Run it using

    ANSIBLE_CALLBACK_PLUGINS="${PWD}" ansible-playbook -i example/inventory.yaml example/playbook.yaml -vvvvvv 2>/dev/null
