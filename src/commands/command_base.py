"""
Generic definition of a command, possibly including a reference to a renderer.

TODO: In reality, this should be a completely separate library in a completely separate
repo. But we'll export it later as needed.
"""
# TODO: make these pydantic models
# overkill? yea absolutely, but whatever lol

class RendererBase():
    pass

class CommandBase():
    # The use of abstract properties, as used by Mythic in stock classes,
    # is also valid for Pydantic - see https://github.com/pydantic/pydantic/discussions/2410
    pass

def export_all_commands():
    """
    Return a list of available command classes.
    """
    pass

def export_commands_as_json():
    """
    Return a nicely formatted dictionary containing all command information,
    suitable for presentation in the DeadDrop interface.
    """
    pass