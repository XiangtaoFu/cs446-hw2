# Design

*One to two pages (handout Section 8.2). Explain your decisions and their trade-offs, not only what the code does. The headings below are suggestions, except the comparison of failure detection, which is required.*

## Code organization

*How you split the code into packages and files, and why. What the three programs share through `rpc/`.*

## Framing and connections

*How a receiver rebuilds frames from a TCP byte stream, and how you handle timeouts, idle connections, and malformed input.*

## Registry and heartbeats

## Load balancing

## Retries and circuit breakers

## Detecting failures: heartbeats and circuit breakers (required)

*Compare the registry's heartbeats with the client's circuit breakers as two ways of detecting a failed instance. Which one notices a failure first? What can each one miss? What happens when they disagree?*

## Protocol version 2

*After the change request: what you changed, where, and how you kept version 1 messages working.*

## What you would do differently
