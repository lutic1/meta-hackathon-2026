"""Council prompt builders (AD-5): pure text over a `RoomView`, or over photo bytes for the Architect.

Each builder renders one request and receives its `ModelProvider` by
injection; none imports an adapter, reads a `Room` or sees a profile (AD-3).
"""
