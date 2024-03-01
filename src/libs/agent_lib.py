"""
Library adhering to the standard definition of a DeadDrop agent.

Although this can be used at runtime, its intended purpose is to facilitate
exposing various metadata to the server. This defines certain constants
that are intended to be shared across all agents (including those not
written in Python), such that a JSON metadata file can be generated
for the agent.
"""