"""
Stop the agent.

In general, this should be invoked as a subprocess call.
"""
import argparse
import psutil
import time

import redis


from tasks import app

def read_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog='stop_agent')

    parser.add_argument(
        "delay",
        type=int,
        default=60,
        nargs=1,
        help="The delay before killing all processes.",
        metavar="delay",
        required=True
    )

    return parser.parse_args()


if __name__ == "__main__":
    args = read_args()

    # Wait for the specified delay time
    time.sleep(args.delay)
    
    app.control.shutdown()