"""
This module contains all available tasking for Celery.
"""

from typing import Optional, Any

from celery import Celery, signals
from celery.utils.log import get_task_logger
import click

from src.agent_code import config, message_dispatch
from src.libs.protocol_lib import ProtocolBase
from src.protocols._shared_lib import PyginMessage

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
app = Celery(
    "tasks", backend="redis://localhost:6379/0", broker="redis://localhost:6379/0"
)
# user_options is guaranteed to exist by Celery's documentation, but mypy can't find it
app.user_options["preload"].add(  # type: ignore[attr-defined]
    click.Option(
        ("-c", "--config"),
        type=click.Path(exists=True),
        help="Configuration file to use.",
    )
)
app.conf.enable_utc = False
app.conf.accept_content = ("pickle", "json")

# Global configuration object that can be used by tasks. Set once, read-only.
# Do NOT use this variable outside of this module.
_g_config: Optional[config.PyginConfig] = None


@signals.user_preload_options.connect
def on_preload_parsed(options, **kwargs):
    """
    Set the task-wide configuration object by loading it from the configuration
    file specified when Celery was invoked.

    The expectation is that Celery is invoked with something like the following:
    ```sh
    celery ... --config=./agent.cfg
    ```
    """
    global _g_config
    _g_config = config.PyginConfig.from_cfg_file(options["config"])

    # Set the default Redis key for PyginMessage. It's assumed that this is
    # synchronized with the "main thread", which will be using this prefix to
    # discover any messages stored in the Redis database.
    PyginMessage.REDIS_KEY_PREFIX = _g_config.REDIS_INTERNAL_MSG_PREFIX

@app.on_after_configure.connect
def setup_periodic_tasks(sender: Celery, **kwargs):
    """
    Set up Pygin's periodic tasks.
    
    I am now older, and therefore wiser, and have realized that having Celery beat
    constantly check for new messages when the main process might not even be alive 
    is a bad idea. (If the agent dies, there is no reason to check for messages and
    run all the anti-duplication logic; the result is that messages "read" by
    these tasks won't actually be acted on, even if the agent restarts!)
    
    In turn, this differs from the prototype agent in that it schedules two
    periodic tasks that can safely be performed (idempotently):
    - Checking whether or not there are enough logs to try and automatically
      send them back to the server. This will advance the "last sent log" marker,
      but this is safe since a) the logs will be *somewhere*, and b) Pygin
      provides `export_logs` to resend logs.
    - Sending heartbeats. In general, it's always safe to assert that a connection
      with the server still exists, as well as send diagnostic information. This
      doesn't strictly depend on the main process being alive (though it *can*
      report that the main process is dead). 
      
    These two operations don't return results, and so it doesn't really matter
    if these operations aren't ever read by the main process.
    """
    # TODO: If we do go the path of letting "get new messages" be a periodic
    # task, then each protocol will need its own timer. At this point, it's
    # become pretty obvious that we'll need to split apart the configuration file
    # into different pieces for this to really make sense.
    
    # TODO: The periodic time for these two tasks should be dictated by the
    # configuration object.
    sender.add_periodic_task(
        5.0,
        conditionally_send_log_bundles.s(_g_config),
        name="Send accumulated log bundles.",
    )
    sender.add_periodic_task(
        5.0,
        send_heartbeat.s(_g_config),
        name="Send a heartbeat message to the server.",
    )


@app.task(serializer="pickle")
def get_new_msgs(cfg: config.PyginConfig, drop_seen_msgs: bool) -> list[PyginMessage]:
    """
    Check for new messages over all specified protocols.
    
    Note that this retrieves *all* new messages, as determined by their respective
    protocols. The message dispatching module is responsible for logging the
    message IDs of messages that have already been seen, as well as handling
    apparent duplicates of messages.
    
    This function also sorts messages earliest to latest in a best-effort
    attempt to ensure a consistent execution order. It is important to note that
    the timestamp in the message is used, *not* the order in which the messages
    were actually received by the agent or the dead drop service.
    
    :param cfg: A PyginConfig object.
    :param drop_seen_msgs: Whether to drop messages that have already been seen
        from the result.
    :returns: A list of PyginMessages, sorted least recent first.
    """
    result: list[PyginMessage] = []
    # For each protocol, ask the message dispatching module to go find all the
    # new messages.
    for protocol_name in cfg.INCOMING_PROTOCOLS:
        

    # Sort all messages by time, earliest to latest.
    raise NotImplementedError

@app.task(serializer="pickle")
def send_msg(cfg: config.PyginConfig, msg: PyginMessage, protocol: ProtocolBase) -> dict[str, Any]:
    """
    Send a message over a specified protocol.
    
    :param cfg: A PyginConfig object.
    :returns: An arbitrary dictionary response, typically containing response
        information from the service used for the protocol.
    """
    # Delegate to the message dispatching module.
    raise NotImplementedError

@app.task(serializer="pickle")
def execute_command(cmd_name: str, cmd_args: dict[str, Any]) -> dict[str, Any]:
    """
    Execute a command asynchronously.
    """
    # Delegate to the command dispatching module.
    raise NotImplementedError
    
@app.task(serializer="pickle")
def conditionally_send_log_bundles(cfg: config.PyginConfig):
    """
    Send log bundles back to the server if the required conditions have been met.
    """
    # TODO: Should this issue log bundles over all protocols, or just one
    # preferred protocol?
    raise NotImplementedError

@app.task(serializer="pickle")
def send_heartbeat(cfg: config.PyginConfig):
    """
    Send a heartbeat message with diagnostic information to the server.
    """
    # TODO: Should this just issue a heartbeat over all protocols, or just
    # one preferred protocol?
    raise NotImplementedError