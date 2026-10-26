"""Council prompt builders (AD-5): pure text over a `RoomView`, or over photo bytes for the Architect.

Each builder renders one request and returns the arguments of one
`ModelProvider` call; none imports an adapter, reads a `Room` or sees a
solution (AD-3). The pipeline makes the call and hands the stored photo bytes
to the adapter as `images`; the greeting builds over `derived` only.
"""
