Pygin is the basic implementation of a DeadDrop agent. 

## Assumptions

Messages take the following format:

```json
{
    // One of command_response, command_request, log_message, heartbeat, or init_message
    "message_type": "command_request",
    // A UUIDv4 identifying this message
    "message_id": "865fba01-654d-4ffb-849b-ccb830b131d2",
    // A UUIDv4 identifying the user associated with this message; may be
    // the null UUID
    "user_id": "865fba01-654d-4ffb-849b-ccb830b131d2",
    // A UUIDv4 identifying the source of this message; null by convention
    // if it's the server.
    "source_id": "865fba01-654d-4ffb-849b-ccb830b131d2",
    // A Unix timestamp. The semantic meaning of the timestamp is arbitrary;
    // it is not necessarily when the message was constructed, but may instead
    // reflect something meaningful about the payload.
    "timestamp": 1709002358,
    // Varies. See below.
    "payload": {},
    // If present, the signature or HMAC for this message. The underlying
    // mechanism for asserting message integrity is not specified in the message
    // standard, and is instead delegated to the protocol and the agent.
    "digest": "dGhpcyBpcyBhIHRlc3QgdGhpcyBpcyBhIHRlc3QgdGhpcyBpcyBhIHRlc3Q="
}
```

In the case of `command_request`, `payload` has the following structure:
```json
{
    // The name of the command, as identified by the agent in commands.json.
    "cmd_name": "ping",
    // A dictionary of strings to strings. These are converted to their proper
    // type at runtime as needed.
    "arguments": {
        "message": "this is a test",
        "delay": "10"
    }
}
```

For `command_response`, `payload` has the following structure:
```json
{
    // The name of the command executed.
    "cmd_name": "ping",
    // Unix timestamps. Denotes when the command started executing and when
    // the command finished.
    "start_time": 1709002358,
    "end_time": 1709002358,
    // The UUID of the original command_request message that caused this command
    // to execute.
    "request_id": "865fba01-654d-4ffb-849b-ccb830b131d2",
    // The "output" of the command. Arbitrary in structure, and may even
    // be empty. May be passed onto a command renderer serverside before presenting
    // the result to the user; in general, this is presented exactly as-is to
    // the user unless a renderer is set for this command.
    "result": {}
}
```

## Design

Much of the architecture of an agent is derived from Mythic's [example container for agent/payload development](https://github.com/MythicMeta/ExampleContainers) and [documentation](https://docs.mythic-c2.net/customizing/payload-type-development). These resources have been used to provide the foresight needed to figure out what an agent *needs* and a general idea of how to structure it, but the actual implementation has been done from scratch (naturally, with the side effect of reduced code quality).

At the absolute highest level, Pygin is a collection of five things required to build unique payloads:
- A Dockerfile, which builds an instance of the agent suitable for execution on Linux
- A set of commands, including their (Python) code and the metadata associated with each command
- If provided, a result renderer for certain commands (equivalent to Mythic's browser scripting) that takes in a command result and produces a valid HTML element
- The main codebase
- Any additional metadata required for the agent to function after bundling

Agents can be run "as-is" from this codebase with a fair degree of manual effort, but they can also be bundled using a Docker container if needed.

When an agent is installed, you can run `insert-thing-here` to automatically generate the metadata.