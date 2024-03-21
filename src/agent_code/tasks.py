"""
This module contains all available tasking for Celery.
"""

from pathlib import Path
from typing import Any
import sys

from celery import Celery, Task
from celery.utils.log import get_task_logger
import redis

from src.agent_code import config, message_dispatch, command_dispatch, utility
from deaddrop_meta.protocol_lib import DeadDropMessage

# from src.protocols._shared_lib import PyginMessage

# Set up logging for tasks.
logger = get_task_logger(__name__)

# Set up the application:
# - Use the local Redis database for the backend *and* broker, assuming the default
#   port of 5379.
# - Add an argument to the celery invocation that accepts a path to a configuration
#   file. This is used to generate a PyginConfig object.
# - Set the timezone for the Celery application to the system timezone. For now,
#   we're going to avoid using UTC to avoid having to make that conversion for
#   tasking.
# - Permit both the pickle and JSON serializers to be used. Normally, JSON is
#   the sole serializer permitted, but all the inputs are assumed to be trusted;
#   if somebody wants to sabotage the framework, they would either need to break
#   the encryption system or gain access to the machine the agent is running on
#   (in which case there's basically nothing we can really do right now).
REDIS_HOST = "redis"  # The name of the docker container
if sys.platform == "win32":
    REDIS_HOST = "127.0.0.1"  # redis-server.exe

app = Celery(
    # FIXME: This ought to be declared as an envvar.
    "tasks",
    # backend="redis://localhost:6379/0",
    # broker="redis://localhost:6379/0",
    backend=f"redis://{REDIS_HOST}:6379/0",
    broker=f"redis://{REDIS_HOST}:6379/0",
)

app.conf.enable_utc = False
app.conf.accept_content = ("pickle", "json")
app.conf.task_serializer = "pickle"
app.conf.result_serializer = "pickle"

# Hardcoded configuration path. I was unable to get Celery's custom command-line
# arguments to work, but I've decided that (theoretically) there should never
# really be a need to hot-swap agent configurations anyways.
#
CONFIG_PATH = Path("./agent_cfg.json")


@app.on_after_configure.connect
def setup_periodic_tasks(sender: Celery, **kwargs):
    """
    Set up Pygin's periodic tasks.

    This differs from the prototype agent in that it schedules three
    periodic tasks that can safely be performed (idempotently):
    - Checking for new messages. Although the main process (the "control unit")
      may die and fail to act on these messages, the design has been changed
      so that the main process now has its own "inbox" as opposed to having
      to scan the entire Redis database for available messages.
    - Checking whether or not there are enough logs to try and automatically
      send them back to the server. This will advance the "last sent log" marker,
      but this is safe since a) the logs will be *somewhere*, and b) Pygin
      provides `export_logs` to resend logs.
    - Sending heartbeats. In general, it's always safe to assert that a connection
      with the server still exists, as well as send diagnostic information. This
      doesn't strictly depend on the main process being alive (though it *can*
      report that the main process is dead).
    """
    # TODO: Can't figure out how to pass the name of the config file in
    # at runtime
    _g_config = config.PyginConfig.from_json5_file(CONFIG_PATH)

    # Schedule checkins for each configured protocol.
    for protocol_name, protocol_cfg in _g_config.protocol_configuration.items():
        if protocol_name not in _g_config.INCOMING_PROTOCOLS:
            logger.info(f"Skipping {protocol_name} from checkins")
            continue

        proto_interval = protocol_cfg.get_checkin_interval()
        logger.info(
            f"Setting up check-ins every {proto_interval} seconds for {protocol_name}"
        )
        sender.add_periodic_task(
            proto_interval,
            get_new_msgs.s(_g_config, protocol_name, True),
            name=f"Check for new messages over the {protocol_name} protocol.",
        )

    # Schedule conditional log bundling and heartbeats.
    logger.info(
        f"Setting up conditional log bundling every {_g_config.LOGGING_INTERVAL} seconds for {_g_config.LOGGING_PROTOCOL}"
    )
    sender.add_periodic_task(
        _g_config.LOGGING_INTERVAL,
        conditionally_send_log_bundles.s(_g_config, _g_config.LOGGING_PROTOCOL),
        name=f"Send accumulated log bundles over the {_g_config.LOGGING_PROTOCOL} protocol.",
    )
    logger.info(
        f"Setting up heartbeats every {_g_config.HEARTBEAT_INTERVAL} seconds for {_g_config.HEARTBEAT_PROTOCOL}"
    )
    sender.add_periodic_task(
        _g_config.HEARTBEAT_INTERVAL,
        send_heartbeat.s(_g_config, _g_config.HEARTBEAT_PROTOCOL),
        name=f"Send a heartbeat message over the {_g_config.HEARTBEAT_PROTOCOL} protocol.",
    )


# See https://docs.celeryq.dev/en/stable/userguide/tasks.html#bound-tasks
# for more information on bound tasks. This is used to retrieve our own
# task ID.
#
# The soft time limit raises an exception in the task when the time limit
# is hit. This is an effort to avoid runaway tasks; note that the default
# number of retries is 3.
#
# TODO: shouldn't the time limit be documented somewhere? lol
@app.task(bind=True, serializer="pickle", soft_time_limit=120)
def get_new_msgs(
    self: Task, cfg: config.PyginConfig, protocol_name: str, drop_seen_msgs: bool
) -> list[DeadDropMessage]:
    """
    Check for new messages over the specified protocol.

    Note that this retrieves *all* new messages, as determined by their respective
    protocols. The message dispatching module is responsible for logging the
    message IDs of messages that have already been seen, as well as handling
    apparent duplicates of messages.

    This function also sorts messages earliest to latest in a best-effort
    attempt to ensure a consistent execution order. It is important to note that
    the timestamp in the message is used, *not* the order in which the messages
    were actually received by the agent or the dead drop service.

    :param cfg: A PyginConfig object.
    :param protocol_name: The name of the protocol to get new messages for.
    :param drop_seen_msgs: Whether to drop messages that have already been seen
        from the result.
    :returns: A list of DeadDropMessages, sorted least recent first.
    """
    redis_con: redis.Redis = utility.get_redis_con(app)

    # For each protocol enabled for listening, ask the message dispatching module
    # to go find all the new messages for that protocol.
    result = message_dispatch.retrieve_new_messages(
        protocol_name, cfg, redis_con, drop_seen_msgs
    )

    # Sort all messages by time, earliest to latest.
    result.sort(key=lambda msg: msg.timestamp)

    # Store this task's ID in the control unit's "inbox", so it can retrieve
    # the AsyncResult of this periodic task later on.
    #
    # mypy complains that self.request.id could be None, which it won't be
    # inside a task.
    redis_con.sadd(cfg.REDIS_NEW_MESSAGES_KEY, self.request.id)  # type: ignore[arg-type]
    logger.warning(redis_con.smembers(cfg.REDIS_NEW_MESSAGES_KEY))

    return result


@app.task(serializer="pickle")
def send_msg(
    cfg: config.PyginConfig, msg: DeadDropMessage, protocol_name: str
) -> dict[str, Any]:
    """
    Send a message over a specified protocol.

    :param cfg: A PyginConfig object.
    :returns: An arbitrary dictionary response, typically containing response
        information from the service used for the protocol.
    """
    # Delegate to the message dispatching module.
    return message_dispatch.send_message(msg, protocol_name, cfg)


@app.task(serializer="pickle")
def execute_command(cmd_name: str, cmd_args: dict[str, Any]) -> dict[str, Any]:
    """
    Execute a command asynchronously.

    `cmd_args` is assumed to be an unparsed dictionary of command arguments,
    taken directly from the `payload` field of the `command_request` message.
    """
    # Delegate to the command dispatching module.
    return command_dispatch.execute_command(cmd_name, cmd_args)


@app.task(serializer="pickle")
def conditionally_send_log_bundles(cfg: config.PyginConfig, protocol_name: str):
    """
    TODO: Send log bundles back to the server if the required conditions have been met.
    """
    # For each protocol available in the PyginConfig object, determine if that
    # protocol is set to be a log bundling protocol.
    logger.warning(
        "Log bundling hasn't been implemented yet, but it would be executed right now"
    )


@app.task(serializer="pickle")
def send_heartbeat(cfg: config.PyginConfig, protocol_name: str):
    """
    TODO: Send a heartbeat message with diagnostic information to the server.
    """
    # For each protocol available in the PyginConfig object, determine if that
    # protocol is set to be a heartbeat protocol.
    logger.warning(
        "Heartbeats haven't been implemented yet, but it would be executed right now"
    )
