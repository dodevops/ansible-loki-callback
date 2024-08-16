import datetime
import logging
import os

import jsonpickle
import logging_loki
from ansible.plugins.callback import CallbackBase

DOCUMENTATION = '''
    callback: loki
    type: loki
    short_description: Ansible output logging to loki
    version_added: 0.1.0
    description:
      - This plugin sends Ansible output to loki
    extends_documentation_fragment:
      - default_callback
    requirements:
      - set as loki in configuration
    options:
      loki_url:
        description: URL to access loki gateway
        required: True
        env:
          - name: LOKI_URL
        ini:
          - section: loki
            key: url
      loki_username:
        description: Username to access loki gateway
        env:
          - name: LOKI_USERNAME
        ini:
          - section: loki
            key: username
      loki_password:
        description: Password to access loki gateway
        env:
          - name: LOKI_PASSWORD
        ini:
          - section: loki
            key: password
      loki_org_id:
        description: Organization to use as a tenant when connecting to loki
        env:
          - name: LOKI_ORG_ID
        ini:
          - section: loki
            key: org_id
      loki_default_tags:
        description: "Tags (key:value) to set for each log line"
        env:
          - name: LOKI_DEFAULT_TAGS
        ini:
          - section: loki
            key: default_tags
        type: list
      result_format:
        default: json
        description: Format used in results (will be set to json)
      pretty_results:
        default: False
        description: Whether to print results pretty (will be set to false)
      enabled_dumps:
        description: |
            Dumps to enable. The values playbook, diff, play, task and runner are available. 
            This usually requires that max_line_size in Loki is set to a higher value than 256kb.
        type: list
        env:
          - name: LOKI_ENABLED_DUMPS
        ini:
          - section: loki
            key: enabled_dumps
'''


# For logging detailed data, we sometimes need to access protected object members
# noinspection PyProtectedMember
class CallbackModule(CallbackBase):
    CALLBACK_VERSION = 2.0
    CALLBACK_TYPE = 'loki'
    CALLBACK_NAME = 'loki'
    ALL_METRICS = ["changed", "custom", "dark", "failures", "ignored", "ok", "processed", "rescued", "skipped"]

    def __init__(self, display=None, options=None):
        super().__init__(display, options)
        self.set_options()
        auth = ()

        if self.get_option("loki_username") and self.get_option("loki_password"):
            auth = (self.get_option("loki_username"), self.get_option("loki_password"))

        headers = {}
        if self.get_option("loki_org_id"):
            headers["X-Scope-OrgID"] = self.get_option("loki_org_id")

        tags = {}
        if self.get_option("loki_default_tags"):
            for tagvalue in self.get_option("loki_default_tags"):
                (tag, value) = tagvalue.split(":")
                tags[tag] = value

        handler = logging_loki.LokiHandler(
            url=self.get_option("loki_url"),
            tags=tags,
            auth=auth,
            headers=headers,
            level_tag="level"
        )

        self.logger = logging.getLogger("loki")
        self.logger.addHandler(handler)
        if self._display.verbosity == 0:
            self.logger.setLevel(logging.WARN)
        elif self._display.verbosity == 1:
            self.logger.setLevel(logging.INFO)
        else:
            self.logger.setLevel(logging.DEBUG)

        self.set_option("result_format", "json")
        self.set_option("pretty_results", False)

    def _dump_enabled(self, dump):
        return self.get_option("enabled_dumps") and dump in self.get_option("enabled_dumps")


    def v2_playbook_on_start(self, playbook):
        self.playbook = os.path.join(playbook._basedir, playbook._file_name)
        self.run_timestamp = datetime.datetime.now().isoformat()
        self.logger.info(
            "Starting playbook %s" % self.playbook,
            extra={"tags": {"playbook": self.playbook, "run_timestamp": self.run_timestamp}}
        )
        if self._dump_enabled("playbook"):
            self.logger.debug(
                jsonpickle.encode(playbook.__dict__),
                extra={"tags": {"playbook": self.playbook, "run_timestamp": self.run_timestamp, "dump": "playbook"}}
            )

    def v2_playbook_on_play_start(self, play):
        self.current_play = play.name
        self.logger.info(
            "Starting play %s" % play.name,
            extra={"tags": {"playbook": self.playbook, "run_timestamp": self.run_timestamp, "play": self.current_play}}
        )
        if self._dump_enabled("play"):
            self.logger.debug(
                jsonpickle.encode(play.__dict__),
                extra={
                    "tags": {
                        "playbook": self.playbook,
                        "run_timestamp": self.run_timestamp,
                        "play": self.current_play,
                        "dump": "play"
                    }
                }
            )

    def v2_playbook_on_task_start(self, task, is_conditional):
        self.current_task = task.name
        self.logger.info(
            "Starting task %s" % self.current_task,
            extra={
                "tags": {
                    "playbook": self.playbook,
                    "run_timestamp": self.run_timestamp,
                    "play": self.current_play,
                    "task": self.current_task
                }
            }
        )
        if self._dump_enabled("task"):
            self.logger.debug(
                jsonpickle.encode(task.__dict__),
                extra={
                    "tags": {
                        "playbook": self.playbook,
                        "run_timestamp": self.run_timestamp,
                        "play": self.current_play,
                        "task": self.current_task,
                        "dump": "task"
                    }
                }
            )

    def v2_runner_on_ok(self, result):
        self.logger.debug(
            "Task %s was successful" % result.task_name,
            extra={
                "tags": {
                    "playbook": self.playbook,
                    "run_timestamp": self.run_timestamp,
                    "play": self.current_play,
                    "task": self.current_task
                }
            }
        )
        if self._dump_enabled("runner"):
            self.logger.debug(
                self._dump_results(result._result),
                extra={
                    "tags": {
                        "playbook": self.playbook,
                        "run_timestamp": self.run_timestamp,
                        "play": self.current_play,
                        "task": self.current_task,
                        "dump": "runner"
                    }
                }
            )

    def v2_runner_on_failed(self, result, ignore_errors=False):
        level = logging.WARNING if ignore_errors else logging.ERROR
        self.logger.log(
            level,
            "Task %s was not successful%s: %s" % (
                self.current_task,
                ", but errors were ignored" if ignore_errors else "",
                result._result['msg']
            ),
            extra={
                "tags": {
                    "playbook": self.playbook,
                    "run_timestamp": self.run_timestamp,
                    "play": self.current_play,
                    "task": self.current_task
                }
            }
        )
        if self._dump_enabled("runner"):
            self.logger.debug(
                self._dump_results(result._result),
                extra={
                    "tags": {
                        "playbook": self.playbook,
                        "run_timestamp": self.run_timestamp,
                        "play": self.current_play,
                        "task": self.current_task,
                        "dump": "runner"
                    }
                }
            )

    def v2_runner_on_skipped(self, result):
        self.logger.info(
            "Task %s was skipped" % self.current_task,
            extra={
                "tags": {
                    "playbook": self.playbook,
                    "run_timestamp": self.run_timestamp,
                    "play": self.current_play,
                    "task": self.current_task
                }
            }
        )
        if self._dump_enabled("runner"):
            self.logger.debug(
                self._dump_results(result._result),
                extra={
                    "tags": {
                        "playbook": self.playbook,
                        "run_timestamp": self.run_timestamp,
                        "play": self.current_play,
                        "task": self.current_task,
                        "dump": "runner"
                    }
                }
            )

    def runner_on_unreachable(self, host, result):
        self.logger.error(
            "Host %s was unreachable for task %s" % (host, self.current_task),
            extra={
                "tags": {
                    "playbook": self.playbook,
                    "run_timestamp": self.run_timestamp,
                    "play": self.current_play,
                    "task": self.current_task
                }
            }
        )
        if self._dump_enabled("runner"):
            self.logger.debug(
                self._dump_results(result),
                extra={
                    "tags": {
                        "playbook": self.playbook,
                        "run_timestamp": self.run_timestamp,
                        "play": self.current_play,
                        "task": self.current_task,
                        "dump": "runner"
                    }
                }
            )

    def v2_playbook_on_no_hosts_matched(self):
        self.logger.error(
            "No hosts matched for playbook %s" % self.playbook,
            extra={
                "tags": {
                    "playbook": self.playbook,
                    "run_timestamp": self.run_timestamp
                }
            }
        )

    def v2_on_file_diff(self, result):
        diff_list = result._result['diff']
        self.logger.info(
            "Task %s produced a diff:\n%s" % (self.current_task, self._get_diff(diff_list)),
            extra={
                "tags": {
                    "playbook": self.playbook,
                    "run_timestamp": self.run_timestamp,
                    "play": self.current_play,
                    "task": self.current_task
                }
            }
        )
        if self._dump_enabled("diff"):
            for diff in diff_list:
                self.logger.debug(
                    self._serialize_diff(diff),
                    extra={
                        "tags": {
                            "playbook": self.playbook,
                            "run_timestamp": self.run_timestamp,
                            "play": self.current_play,
                            "task": self.current_task,
                            "dump": "diff"
                        }
                    }
                )

    def v2_playbook_on_stats(self, stats):
        summarize_metrics = {}
        host_metrics = {}
        for metric in self.ALL_METRICS:
            value = 0
            for host, host_value in stats.__dict__[metric].items():
                value += host_value
                if host not in host_metrics:
                    host_metrics[host] = {}
                    for m in self.ALL_METRICS:
                        host_metrics[host][m] = 0
                host_metrics[host][metric] = host_value
            summarize_metrics[metric] = value
        self.logger.info(
            "Stats for playbook %s" % self.playbook,
            extra={
                "tags": {
                            "playbook": self.playbook,
                            "run_timestamp": self.run_timestamp,
                            "stats_type": "summary"
                        } | summarize_metrics
            }
        )
        for host in host_metrics:
            self.logger.debug(
                "Stats for playbook %s, host %s" % (self.playbook, host),
                extra={
                    "tags": {
                                "playbook": self.playbook,
                                "run_timestamp": self.run_timestamp,
                                "stats_type": "host"
                            } | host_metrics[host]
                }
            )
