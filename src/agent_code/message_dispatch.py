"""
This implements the messaging dispatch module as described in DeadDrop's
generic architecture model for agents.

If any additional operations are needed before handing the message off to
a particular protocol, it should be done here. This may include adding
protocol-specific arguments that are not already present in the configuration
object, and therefore must be handled on a case-by-case basis.

The spirit of this design is that any edge case handling can be centralized
to this module, allowing the protocols to remain (relatively) loosely bound
from the rest of Pygin's libraries.
"""

from typing import Any, Type, Optional
import logging

from Cryptodome.Cipher import AES
from Cryptodome.Util.Padding import pad, unpad
from Cryptodome.Hash import SHA512
from Cryptodome.PublicKey import ECC
from Cryptodome.Signature import eddsa
import redis

from deaddrop_meta.protocol_lib import ProtocolConfig, ProtocolBase
from deaddrop_meta import protocol_lib
from deaddrop_meta.protocol_lib import DeadDropMessage

# Make all protocols visible. This is an intentional star-import so that
# our helper functions work.
from src.protocols import *  # noqa: F401,F403
from src.agent_code import config


logger = logging.getLogger(__name__)


def retrieve_new_messages(
    protocol_name: str,
    cfg: config.PyginConfig,
    redis_con: Optional[redis.Redis] = None,
    drop_seen: bool = True,
) -> list[DeadDropMessage]:
    """
    Retrieve all new messages over the specified service.

    This function searches for the associated protocol handler (a subclass of
    `ProtocolBase`) and asks it to retrieve all messages from the service. Protocol
    handlers may store state information in the Redis database passed into this
    function; for example, a YouTube-based service may store the upload date of
    the most recent message seen.

    This function also keeps track of the message IDs of all messages seen, and
    by default will explicitly drop any messages that have already been recorded
    by this function. Even when disabled, this function will log duplicate messages.

    :param protocol_name: The name of the protocol to retrieve messages from.
    :param cfg: The Pygin configuration object, which may also contain static
        configuration for the underlying protocols.
    :param redis_con: A Redis connection, typically `app.backend.client` when
        invoked from Celery's tasking module. If None, then no duplicate message
        checking is performed.
    :param drop_seen: Whether to drop any messages with IDs that have already
        been seen, as stored by the Redis database.
    """
    result: list[DeadDropMessage] = []

    # Get a handle to the relevant protocol class, if it exists. Parse the arguments
    # accordingly from the PyginConfig class.
    protocol_class = protocol_lib.lookup_protocol(protocol_name)

    # mypy complains about properties as usual
    protocol_config_model: Type[ProtocolConfig] = protocol_class.config_model  # type: ignore[assignment]
    
    # Merge the global config with the protocol config. Pydantic will ignore 
    # additional dictionary elements; the syntax below prefers the existing
    # keys for the protocol over those that are global.
    merged_config = cfg.model_dump() | cfg.protocol_configuration[protocol_name]
    
    validated_config = protocol_config_model.model_validate(merged_config)
    protocol_args = validated_config.model_dump()

    # Invoke the protocol's message retrieval function. At this point, any protocol-specific
    # arguments are added in by the message dispatch unit, such as the inclusion of
    # a handle to the Redis database in the keyword arguments.
    #
    # TODO: I'm holding off on this for now. This should probably call another function
    # that adds more arguments as needed, then combines the protocol_args dictionary
    # with our new dictionary containing runtime arguments.
    #
    # When bytes are supported, assume that encryption was used if an encrpytion
    # key is set.
    new_msgs: list[DeadDropMessage] = []

    # mypy: this is a property, not a function
    if protocol_class.supports_bytes:  # type: ignore[truthy-function]
        logger.debug(f"{protocol_class.name} supports bytes, will use decryption")
        new_msgs_bytes = protocol_class.get_new_messages_bytes(protocol_args)
        for msg_bytes in new_msgs_bytes:
            try:
                # Note that even if no encryption key is set, we still defer to
                # `decrypt_msg` to perform the process of decoding bytes to
                # DeadDropMessage.
                new_msgs.append(decrypt_msg(msg_bytes, cfg))
            except Exception as e:
                logger.error(
                    f"Failed to decrypt {msg_bytes!r} to a DeadDropMessage, ignoring message: {e}"
                )
    else:
        new_msgs = protocol_class.get_new_messages(protocol_args)

    # Verify that the messages are from the server if the server's public key
    # is set.
    #
    # Note this directly complicates any sort of forwarding mechanism, but we're
    # going to assume that all messages we receive are from the server for now.
    verified_msgs: list[DeadDropMessage] = []
    if cfg.SERVER_PUBLIC_KEY is not None:
        logger.debug("Server public key set, performing verification checks")
        for msg in new_msgs:
            if verify_msg(msg, cfg):
                logger.debug(f"{msg.message_id=} is authentic")
                verified_msgs.append(msg)
            else:
                logger.error(
                    f"Verification failed for {msg.message_id=}, dropping ({msg})"
                )
    else:
        # All messages are "verified"
        logger.debug("No server public key set, assuming all messages are authentic")
        verified_msgs = new_msgs

    # For each message, check if was already seen and act accordingly based on
    # `drop_seen`. In all cases, add message IDs to the set.
    for msg in verified_msgs:
        # String comparisons to UUIDs don't work as expected, so you have
        # to explicitly convert a uuid.UUID to a string for it to work with
        # the strings contained in the Redis database
        msg_id = str(msg.message_id)

        if redis_con is not None:
            if redis_con.sismember(cfg.REDIS_MESSAGES_SEEN_KEY, msg_id):
                logger.debug(
                    f"Duplicate message {msg_id} seen by message dispatch unit"
                )
                if drop_seen:
                    logger.debug(f"Dropping duplicate message {msg_id}")
                    continue

            # Add this new message to the set if it hasn't been seen already
            redis_con.sadd(cfg.REDIS_MESSAGES_SEEN_KEY, msg_id)

        result.append(msg)

    # It's possible that protocols are shared mediums. It's our responsibility
    # to drop or forward messages that aren't intended for us, since we don't want
    # to execute commands that don't belong to us.
    result_2 = []
    for msg in result:
        if msg.destination_id != cfg.AGENT_ID:
            if cfg.DROP_MISDIRECTED_MESSAGES:
                logger.warning(
                    f"Dropping message {msg.message_id} because it is intended for {msg.destination_id} (and I am {cfg.AGENT_ID})"
                )
                continue
            else:
                logger.warning(
                    f"{msg.message_id} was intended for {msg.destination_id}, but is being read anyways"
                )
        result_2.append(msg)

    # Return the remaining set of messages.
    return result_2


def send_message(
    msg: DeadDropMessage,
    protocol_name: str,
    cfg: config.PyginConfig,
) -> dict[str, Any]:
    """
    Send a message over the specified protocol.

    Note that if a message is signed at this point, the signature will be
    overwritten. Individual protocols may elect to re-sign the message
    if desired.
    """
    # Sign the message if the required keys are set.
    if cfg.AGENT_PRIVATE_KEY is not None:
        logger.debug("Signing message")
        msg = sign_msg(msg, cfg)

    # Get a handle to the relevant protocol class, if it exists. Parse the arguments
    # accordingly from the PyginConfig class.
    protocol_class: Type[ProtocolBase] = protocol_lib.lookup_protocol(protocol_name)

    # mypy complains about properties as usual
    protocol_config_model: Type[ProtocolConfig] = protocol_class.config_model  # type: ignore[assignment]
    
    # Merge the global config with the protocol config. Pydantic will ignore 
    # additional dictionary elements; the syntax below prefers the existing
    # keys for the protocol over those that are global.
    merged_config = cfg.model_dump() | cfg.protocol_configuration[protocol_name]
    
    validated_config = protocol_config_model.model_validate(merged_config)
    protocol_args = validated_config.model_dump()

    # Invoke the protocol's message sending function. Again, pass in the Redis
    # connection as a keyword argument; it's up to the protocol whether or not
    # to use this for any state management. Directly return the result; any error
    # handling or message re-sending must occur at the protocol level.
    #
    # If arbitrary bytes are supported, encrypt the message and use the byte-based
    # function instead. Note that if an encryption key is not set, this amounts
    # to simply encoding the DeadDropMessage as bytes ahead of time (instead of
    # deferring it to the protocol).
    if protocol_class.supports_bytes:  # type: ignore[truthy-function]
        data = encrypt_msg(msg, cfg)
        return protocol_class.send_msg_bytes(data, protocol_args)

    return protocol_class.send_msg(msg, protocol_args)


def sign_msg(msg: DeadDropMessage, cfg: config.PyginConfig) -> DeadDropMessage:
    """
    Sign a message with EDDSA.

    The process for signing is as follows:
    - Replace the `digest` field with None, overwriting the value if any.
    - Convert the stripped message to a JSON string with no formatting.
    - Evaluate the EDDSA signature over that stripped message.
    - Add the signature to the original message, replcaing the `digest` field.

    If this function is called and the agent's private key is not set, this
    returns immediately and does nothing to the message.
    """
    if not cfg.AGENT_PRIVATE_KEY:
        logger.debug("Agent private key not set, returning message as-is")
        return msg

    # Strip the message of its digest and get its JSON representation (in theory
    # this should be deterministic)
    msg.digest = None
    data = msg.model_dump_json().encode("utf-8")

    # Calculate signature, SHA512/EDDSA
    key = ECC.import_key(cfg.AGENT_PRIVATE_KEY)
    signer = eddsa.new(key, "rfc8032")

    h = SHA512.new(data)
    signature = signer.sign(h)

    # Apply signature to original message object and return
    msg.digest = signature
    return msg


def verify_msg(msg: DeadDropMessage, cfg: config.PyginConfig) -> bool:
    """
    Verify a message with EDDSA.

    The process for verification is identical to that as signing, except that
    the stripped digest is used as the signature to verify against.

    On a failing verification, this returns False.

    If this function is called and the server's public key is not set, this
    always returns True.
    """
    if not cfg.SERVER_PUBLIC_KEY:
        logger.debug("Server public key not set, assuming message is valid")
        return True

    if msg.digest is None:
        raise RuntimeError("Message was not signed!")

    # Create deep copy of message, strip it of its digest and get JSON representation
    msg_copy = msg.model_copy(deep=True)
    msg_copy.digest = None
    raw_data = msg_copy.model_dump_json().encode("utf-8")

    # Reconstruct hash and verify against server's public key
    key = ECC.import_key(cfg.SERVER_PUBLIC_KEY)
    h = SHA512.new(raw_data)
    verifier = eddsa.new(key, "rfc8032")
    try:
        assert msg.digest is not None
        verifier.verify(h, msg.digest)
        return True
    except ValueError:
        return False


def encrypt_msg(msg: DeadDropMessage, cfg: config.PyginConfig) -> bytes:
    """
    Use AES-128-CBC to encrypt a message.

    This simply dumps the entire message as JSON, then runs it through CBC.
    PKCS7 padding is used, then the IV is prepended to the resulting message.

    If this method is called and no encryption key is set, this simply dumps
    the message out as a plaintext UTF-8 encoded message with with no padding.
    """
    data = msg.model_dump_json().encode("utf-8")

    if not cfg.ENCRYPTION_KEY:
        logger.debug("Encryption key not set, no encryption performed")
        return data

    logger.debug("Padding and encrypting message")
    cipher = AES.new(cfg.ENCRYPTION_KEY, AES.MODE_CBC)
    data = cipher.encrypt(pad(data, AES.block_size))

    result = bytes(cipher.iv) + data
    logger.debug(f"{len(data)=}, {len(result)=}")

    return result


def decrypt_msg(data: bytes, cfg: config.PyginConfig) -> DeadDropMessage:
    """
    Decrypt a single message with AES-128-CBC. PKCS7 padding is assumed, and the
    first sixteen bytes are the IV.

    If, after decryption, the message cannot be converted to a DeadDropMessage,
    this simply re-raises ValidationError.

    If this method is called and no encryption key is set, this simply assumes
    that the message is already in plaintext.
    """
    # If an encryption key has not been set, attempt to validate directly.
    if cfg.ENCRYPTION_KEY is None:
        logger.debug("No encryption key set, assuming plaintext")
        return DeadDropMessage.model_validate_json(data)

    # Assume that the first sixteen bytes are the IV. The rest is the padded
    # message.
    logger.debug("Removing padding and decrypting message")
    iv = data[:16]
    ct = data[16:]

    cipher = AES.new(cfg.ENCRYPTION_KEY, AES.MODE_CBC, iv=iv)
    pt = unpad(cipher.decrypt(ct), AES.block_size)

    return DeadDropMessage.model_validate_json(pt)
