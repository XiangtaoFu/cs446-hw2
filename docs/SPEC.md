# CS446/CS646 Homework 2: Interface Specification

**Protocol version 2.** Document version 2.0, released November 24, 2026. The Word version on Canvas has the same content.

This document defines how the three programs in Homework 2 talk to each other over the network, how they are started, and what they print. The assignment handout describes what to build and how it is graded. This document gives the exact formats and behaviors your code must follow. The course's grading tests are written against this document, so if the handout and this document disagree about a format or a number, follow this document and tell the instructor about the disagreement.

**Must** means required; the grading tests check it. **May** means allowed but not required. Values described as defaults can be changed on the command line. The grading tests often start your programs with non-default values so that the tests run faster, so read every setting from the command line instead of writing the default into your code.

**What changed from version 1.** Protocol version 2 adds a request ID and a deadline to the header of every frame (Sections 2.2 and 2.5). Programs that implement version 2 must still accept version 1 requests (Section 2.4). The change request, `docs/CHANGE-REQUEST-v2.md`, summarizes the changes.

## 1  The three programs

Your system has three programs:

- **Registry.** Keeps the list of service instances that are currently running. Instances add themselves to the list and send heartbeats to stay on it.
- **Stats service.** Performs simple computations: sum, average, minimum, maximum, and product. You run several copies of it, called instances, usually on different machines.
- **Client.** Asks the registry which stats instances exist, chooses one for each request (load balancing), and handles failures with retries and circuit breakers.

Figure 1 shows who sends requests to whom. Every arrow is a request sent over TCP in the format of Sections 2 to 4, and the receiver sends back one response.

```
stats instance  --- registry.register, registry.heartbeat --->  registry
client          --- registry.lookup ------------------------->  registry
client          --- stats.compute --------------------------->  stats instance
                    (instance chosen by the client's load balancer)
```

*Figure 1. Requests between the programs.*

## 2  Framing

TCP delivers a stream of bytes, not separate messages. One call to `recv()` can return part of a message, exactly one message, or the end of one message together with the start of the next. To mark where each message ends, every message is sent as a frame that begins with a header giving the length of the message. There are two versions of the frame. The first byte of every frame is its version number, so a receiver can tell them apart.

### 2.1  Version 1 frames

*Table 1. Version 1 frame layout.*

| Bytes | Field | Contents |
|---|---|---|
| 0 | version | 1, as an unsigned 8-bit integer. |
| 1 to 4 | length | Number of bytes in the body, as an unsigned 32-bit integer in big-endian (network) byte order. The 5 header bytes are not counted. |
| 5 to 4 + length | body | The message: one JSON object encoded as UTF-8 (Section 3). |

### 2.2  Version 2 frames

*Table 1b. Version 2 frame layout.*

| Bytes | Field | Contents |
|---|---|---|
| 0 | version | 2, as an unsigned 8-bit integer. |
| 1 to 4 | length | Number of bytes in the body, as an unsigned 32-bit integer in big-endian byte order. The 17 header bytes are not counted. |
| 5 to 12 | request_id | Identifies the request, as an unsigned 64-bit integer in big-endian byte order (Section 2.5). |
| 13 to 16 | deadline_ms | Time left for the request in milliseconds, as an unsigned 32-bit integer in big-endian byte order, or 0 for no deadline (Section 2.5). |
| 17 to 16 + length | body | The message, exactly as in version 1 (Section 3). |

### 2.3  Rules for all frames

- The length must be at most 1,048,576 (1 MiB).
- A receiver reads the version byte first, then the rest of that version's header, then the body. It must keep reading until it has each part completely. It must not assume that one read returns exactly one frame.
- A receiver must handle several frames arriving in one read, and must process them in the order they arrived.
- If the connection closes partway through a frame, the receiver discards the partial frame.
- A version byte other than 1 or 2 is an error (UNSUPPORTED_VERSION, Section 4).

### 2.4  Which version to send

- A program that implements version 2 sends every request as a version 2 frame.
- Every server must accept both version 1 and version 2 requests, and must answer each request with a frame of the same version as the request. A version 1 client therefore always gets version 1 responses.
- A client must accept a response of either version. A version 2 client receives a version 1 response only from a server that does not support version 2; that response is UNSUPPORTED_VERSION.
- Because a version 2 program sends only version 2 requests, it can only talk to servers that already support version 2. A stats instance is a client of the registry, and the client calls both. When a running system is upgraded, each server must therefore be upgraded before the programs that call it.

### 2.5  Request IDs and deadlines

- **request_id.** The client chooses a request_id for each request and sends the same value in every attempt of that request, including retries. Requests sent by one run of the client must have different values; otherwise any 64-bit value is allowed. A server copies the request_id of each version 2 request into its response. If a response's request_id is not the one the client sent, the client treats the attempt as PROTOCOL_ERROR.
- **deadline_ms.** How many more milliseconds the sender is willing to wait for the response, counted from when it sends the frame. 0 means no deadline. The deadline is an amount of time, not a clock time, so the clocks of different machines do not need to agree. Responses always carry 0 in this field, and version 1 requests are treated as having no deadline.
- The stats service enforces deadlines on stats.compute (Section 6.3). The registry and the ping method ignore deadlines, so a stats instance may send 0 in its requests to the registry. The client sets deadlines as described in Section 8.8.

### 2.6  Examples

The request `{"method":"ping","params":{}}` has a 29-byte body (1D in hexadecimal). As a version 1 frame it is 34 bytes:

```
01 00 00 00 1D 7B 22 6D 65 74 68 6F 64 22 3A 22
70 69 6E 67 22 2C 22 70 61 72 61 6D 73 22 3A 7B
7D 7D
```

The first byte (01) is the version, the next four bytes (00 00 00 1D) are the length, and the remaining 29 bytes are the UTF-8 text of the body. As a version 2 frame with request_id 7 and a deadline of 2000 milliseconds (7D0 in hexadecimal), the same request is 46 bytes:

```
02 00 00 00 1D 00 00 00 00 00 00 00 07 00 00 07
D0 7B 22 6D 65 74 68 6F 64 22 3A 22 70 69 6E 67
22 2C 22 70 61 72 61 6D 73 22 3A 7B 7D 7D
```

Here byte 0 is the version (02), bytes 1 to 4 are the length (00 00 00 1D), bytes 5 to 12 are the request_id (7), bytes 13 to 16 are the deadline (00 00 07 D0), and the body follows.

## 3  Messages

### 3.1  Requests

A request body is a JSON object with two fields:

```
{"method": "stats.compute", "params": {"op": "sum", "values": [1, 2, 3.5]}}
```

- `method` is a string naming the operation (Section 6).
- `params` is an object holding the operation's inputs. It is `{}` when an operation has no inputs.

A receiver must ignore any other top-level fields. In version 2, the request ID and the deadline are in the frame header, not in the JSON body.

### 3.2  Responses

Every request gets exactly one response. A successful response has `ok` set to true and a `result` object:

```
{"ok": true, "result": {"value": 6.5, "instance_id": "127.0.0.1:9001"}}
```

A failed response has `ok` set to false and an `error` object containing a `code` from Table 2 and a human-readable `message`:

```
{"ok": false, "error": {"code": "INVALID_PARAMS", "message": "values must not be empty"}}
```

The grading tests check the code, not the message.

### 3.3  JSON rules

- Bodies must be standard JSON as defined in RFC 8259. In particular, NaN, Infinity, and -Infinity are not valid JSON and must never be sent.
- true and false are booleans, not numbers.
- All numbers are handled as 64-bit floating-point values (IEEE 754 double precision). Results are compared numerically, so 6 and 6.0 are equal.

## 4  Connections

- A client opens a TCP connection, sends a request frame, and reads the response frame. It may then send another request on the same connection, or close it.
- A server answers the requests on one connection in the order they arrived, with one response per request.
- A server must handle at least 32 connections at the same time. A slow request on one connection must not delay responses on other connections.
- A server may close a connection when no bytes have arrived on it for 30 seconds. It must not close a connection for being idle any sooner, including while it is waiting for the rest of a partly received frame.
- If the frame header cannot be used (error codes UNSUPPORTED_VERSION and FRAME_TOO_LARGE), the server sends an error response and then closes the connection, because it can no longer tell where the next frame starts. An UNSUPPORTED_VERSION response is a version 1 frame, because the server cannot know which versions the client understands. Every other response uses the version of the request (Section 2.4), and for version 2 it carries the request's request_id.
- If the frame is fine but the body has a problem (any other error code), the server sends an error response and keeps the connection open.
- A server must never crash or stop accepting connections because of what a client sent. A problem on one connection must not affect other connections.

## 5  Error codes

Table 2 lists every error code. Codes sent by the client side are never sent over the network: the client uses them in its own output and event log (Section 8) to describe failures it detected itself. The last column says whether the client retries after an attempt fails with that code (Section 8.5).

*Table 2. Error codes.*

| Code | Sent by | Meaning | Client retries |
|---|---|---|---|
| UNSUPPORTED_VERSION | Any server | The version byte is not 1 or 2. The server closes the connection after replying. | No |
| FRAME_TOO_LARGE | Any server | The length field is larger than 1,048,576. The server closes the connection after replying. | No |
| MALFORMED_REQUEST | Any server | The body is not valid UTF-8 JSON, is not an object, or does not have a string `method` and an object `params`. | No |
| UNKNOWN_METHOD | Any server | The server does not provide the named method. | No |
| INVALID_PARAMS | Any server | A parameter is missing, has the wrong type, or is out of range (Section 6). | No |
| RESULT_NOT_FINITE | Stats | The inputs are valid, but the result is infinite or not a number. | No |
| DEADLINE_EXCEEDED | Stats, client side | The request's deadline passed before a result was ready (Sections 6.3 and 8.8). | No |
| UNKNOWN_INSTANCE | Registry | A heartbeat named an instance the registry does not have. | Does not apply |
| INTERNAL | Any server | An unexpected error happened while handling a valid request. | Yes |
| TIMEOUT | Client side | The attempt did not finish within the attempt timeout. | Yes |
| CONNECTION_ERROR | Client side | The connection could not be opened, or it was closed or reset before the full response arrived. | Yes |
| PROTOCOL_ERROR | Client side | The response did not follow this specification (bad frame, bad JSON, or missing fields). | Yes |
| NO_INSTANCES | Client side | No instance was eligible when the attempt started (Section 8.3). | Yes |

## 6  Methods

### 6.1  ping

Every server provides `ping`. Its params are `{}`, and its result says which kind of server answered:

```
request:   {"method": "ping", "params": {}}
registry:  {"ok": true, "result": {"service": "registry"}}
stats:     {"ok": true, "result": {"service": "stats", "instance_id": "127.0.0.1:9000"}}
```

### 6.2  Registry methods

*Table 3. Registry methods.*

| Method | Params | Result |
|---|---|---|
| registry.register | `service` (string), `instance_id` (string), `host` (string), `port` (integer from 1 to 65535) | `{"heartbeat_interval_ms": N}` |
| registry.heartbeat | `instance_id` (string) | `{}`, or error UNKNOWN_INSTANCE |
| registry.deregister | `instance_id` (string) | `{}` |
| registry.lookup | `service` (string) | `{"instances": [...]}`, where each element has `instance_id`, `host`, and `port` |

All strings must be non-empty. A missing parameter, a parameter of the wrong type, or a port outside the allowed range is INVALID_PARAMS.

- **register** adds the instance. If an instance with the same instance_id is already registered, the new entry replaces it. The result tells the instance how often to send heartbeats: N is the registry's TTL (time to live, Section 7.2) divided by 3 and rounded down to a whole number of milliseconds.
- **heartbeat** marks the instance as still alive. If the registry does not have the instance, because it expired or because the registry was restarted, the registry returns UNKNOWN_INSTANCE.
- **deregister** removes the instance. It succeeds even if the instance was not registered.
- **lookup** returns the live instances of the named service, sorted by instance_id in ascending order of character codes. An unknown service name returns an empty list.
- **Expiry.** An instance expires when no register or heartbeat for it has arrived for TTL milliseconds. After its last register or heartbeat, an instance must still appear in lookup results for at least TTL milliseconds, and must stop appearing no later than TTL + 1000 milliseconds.

Example lookup:

```
request:   {"method": "registry.lookup", "params": {"service": "stats"}}
response:  {"ok": true, "result": {"instances": [
              {"instance_id": "127.0.0.1:9000", "host": "127.0.0.1", "port": 9000},
              {"instance_id": "127.0.0.1:9001", "host": "127.0.0.1", "port": 9001}]}}
```

### 6.3  Stats method

Besides ping, the stats service provides one method, `stats.compute`. Its params are `op`, one of the strings in Table 4, and `values`, an array of numbers. The result is `{"value": V, "instance_id": ID}`, where ID identifies the instance that did the computation.

*Table 4. Operations.*

| op | Value returned |
|---|---|
| sum | Sum of the values. |
| avg | Sum of the values divided by the number of values. |
| min | Smallest value. |
| max | Largest value. |
| multiply | Product of the values. |

The instance returns INVALID_PARAMS if `op` is not one of these five strings, or if `values` is not an array, is empty, or contains anything other than a number (including true, false, null, and strings). A number too large to store as a 64-bit floating-point value is also invalid. If the inputs are valid but the result is infinite or not a number, for example when multiplying 1e308 by 10, the instance returns RESULT_NOT_FINITE.

**Deadlines.** When a stats.compute request has a deadline of D milliseconds (D greater than 0), the instance must send its response no later than D milliseconds after the complete frame arrived. If the result is not ready by then, it sends DEADLINE_EXCEEDED instead. When the instance can tell in advance that it cannot finish in time, for example because `--delay-ms` is at least D, it should reply DEADLINE_EXCEEDED right away instead of waiting.

## 7  Running the programs

### 7.1  Rules for all programs

- Your code must run with Python 3.10 or newer and use only the Python standard library. Run every command in this section from the root of your repository.
- Standard output is reserved for the output that this section specifies. Write all log and debug messages to standard error.
- When a server is ready to accept connections, it must print one line containing exactly `READY` to standard output and flush it immediately. The grading tests wait for this line before connecting.
- Addresses are written HOST:PORT, for example 127.0.0.1:8000.
- When a server receives SIGINT (Ctrl-C) or SIGTERM, it must shut down and exit with status 0 within 2 seconds.
- If its command-line arguments are invalid, a program prints a usage message to standard error and exits with status 2.

### 7.2  Registry

```
python3 -m registry [--host HOST] [--port PORT] [--ttl-ms MS]
```

*Table 5. Registry options.*

| Option | Default | Meaning |
|---|---|---|
| --host | 0.0.0.0 | Address to listen on. 0.0.0.0 means every network interface of the machine. |
| --port | 8000 | TCP port to listen on. |
| --ttl-ms | 6000 | Time to live: how long an instance stays registered without a heartbeat (Section 6.2). |

### 7.3  Stats service

```
python3 -m services.stats --registry HOST:PORT [--host HOST] [--port PORT]
        [--advertise-host HOST] [--advertise-port PORT] [--id ID] [--delay-ms MS]
```

*Table 6. Stats service options.*

| Option | Default | Meaning |
|---|---|---|
| --registry | (required) | Address of the registry. |
| --host | 0.0.0.0 | Address to listen on. |
| --port | 9000 | TCP port to listen on. |
| --advertise-host | 127.0.0.1 | Address that clients should use to reach this instance. This is the host sent to the registry. |
| --advertise-port | the value of --port | Port that clients should use to reach this instance. This is the port sent to the registry. |
| --id | see meaning | The instance_id sent to the registry. By default it is the advertised host and port joined by a colon, for example 127.0.0.1:9000. |
| --delay-ms | 0 | Wait this many milliseconds before answering each stats.compute request (not ping). Use it to simulate a slow instance when testing. |

**Why the advertised address can differ from the listening address.** On Google Cloud, a VM with an external IP address does not see that address on its own network interface. Google's network translates between the external address and the VM's internal address (one-to-one NAT). A server on the VM listens on 0.0.0.0, but it must tell the registry its external address so that a client on your laptop can reach it.

Required behavior of a stats instance:

- After printing READY, the instance registers. If registration fails because the registry cannot be reached or returns an error, the instance tries again every 1000 milliseconds.
- After registering, the instance sends a heartbeat every heartbeat_interval_ms milliseconds, using the value the registry returned.
- If a heartbeat returns UNKNOWN_INSTANCE, the instance registers again immediately.
- If the registry cannot be reached, the instance keeps trying at the same interval. An instance must never exit because the registry is unavailable.
- On SIGINT or SIGTERM, the instance tries to deregister, gives up on deregistering after 1 second, and exits.

### 7.4  Client

```
python3 -m client call [OPTIONS] OP VALUE [VALUE ...]
python3 -m client load [OPTIONS] OP VALUE [VALUE ...]
```

`call` sends one stats.compute request. `load` sends the same request many times, possibly several at once, and reports totals. OP is one of the operations in Table 4, and each VALUE is a number. Negative numbers such as -2.5 must be accepted as values.

*Table 7. Client options.*

| Option | Default | Meaning |
|---|---|---|
| --registry HOST:PORT | (required) | Address of the registry. |
| --strategy | round_robin | Load-balancing strategy: round_robin or least_connections (Section 8.4). |
| --timeout-ms | 2000 | Time limit for one attempt (Section 8.1). |
| --deadline-ms | 5000 | Time limit for a whole request, including retries and backoff waits (Section 8.8). 0 means no limit. |
| --max-retries | 3 | Retries after the first attempt, so each request makes at most 1 + max-retries attempts. |
| --base-delay-ms | 100 | Base delay for exponential backoff (Section 8.5). |
| --breaker-threshold | 3 | Consecutive failures that open a circuit breaker (Section 8.6). |
| --breaker-reset-ms | 5000 | Time an open breaker waits before it allows a trial attempt. |
| --breaker-successes | 2 | Successful trial attempts that close a half-open breaker. |
| --refresh-ms | 1000 | How often to fetch the instance list from the registry (Section 8.2). |
| --events FILE | none | Write the event log (Section 8.7) to FILE. |
| --requests | 100 | load only: number of requests to send. |
| --concurrency | 1 | load only: number of requests in progress at the same time. |

**Output of call.** The client prints one line of JSON to standard output and exits with status 0 if the request succeeded or 1 if it failed. `attempts` is the number of attempts made.

```
{"ok": true, "value": 6.5, "instance_id": "127.0.0.1:9001", "attempts": 1}
{"ok": false, "error": {"code": "TIMEOUT", "message": "timed out"}, "attempts": 4}
```

**Output of load.** When every request has finished, the client prints one JSON object to standard output and exits with status 0, even if some requests failed. The object may span several lines, but the whole of standard output must be that one object. In this example, instance 127.0.0.1:9002 stopped partway through the run; three attempts to it failed and were retried successfully on other instances.

```
{
  "requests": 100, "succeeded": 100, "failed": 0,
  "errors": {},
  "per_instance": {
    "127.0.0.1:9000": {"attempts": 36, "succeeded": 36, "failed": 0},
    "127.0.0.1:9001": {"attempts": 37, "succeeded": 37, "failed": 0},
    "127.0.0.1:9002": {"attempts": 30, "succeeded": 27, "failed": 3}
  },
  "latency_ms": {"avg": 4.1, "p50": 3.2, "p95": 9.8, "max": 112.4},
  "duration_ms": 1530.2
}
```

- `requests`, `succeeded`, and `failed` count requests.
- `errors` maps each final error code to the number of failed requests that ended with it.
- `per_instance` has an entry for every instance that received at least one attempt, counting the attempts sent to it and how many of them succeeded and failed.
- `latency_ms` describes successful requests only, measured from when a request starts to when its final result is known, including any retries: the average, the median (p50), the 95th percentile (p95), and the maximum. Percentiles use the nearest-rank method. If no request succeeded, these four values are null.
- `duration_ms` is the time from when the first request started to when the last one finished.

## 8  Client behavior

### 8.1  Requests and attempts

A request is one computation the user asked for. The client makes up to 1 + max-retries attempts for each request. In each attempt, the client asks the load balancer for an instance, sends stats.compute to it, and waits for the response. The whole attempt, including opening the connection if needed, must finish within the attempt timeout, which is timeout-ms milliseconds or the time left before the request's deadline, whichever is shorter (Section 8.8). Otherwise the attempt fails with TIMEOUT, or with DEADLINE_EXCEEDED if the deadline was the limit.

The client may reuse connections between attempts or open a new connection for each attempt. After a TIMEOUT or DEADLINE_EXCEEDED, the client must close that connection, because a late response could otherwise be read as the answer to a later request.

### 8.2  The instance list

The client calls registry.lookup for the service "stats" when it starts, before its first attempt, and again every refresh-ms milliseconds. If a lookup fails, the client keeps using the last list it received. When an instance disappears from the list, the client forgets it. When a new instance appears, the client adds it with its circuit breaker CLOSED. An instance that stays in the list keeps its circuit breaker state.

### 8.3  Eligible instances

An instance is eligible for an attempt if it is in the current list and its circuit breaker allows an attempt (Section 8.6). That means the breaker is CLOSED; or it is OPEN and breaker-reset-ms milliseconds have passed since it opened; or it is HALF_OPEN and no attempt to that instance is in progress. If no instance is eligible, the attempt fails immediately with NO_INSTANCES.

### 8.4  Load balancing

- **round_robin.** The client keeps a position in the instance list, which is sorted by instance_id. To choose an instance, it starts at that position and moves forward until it finds an eligible instance, wrapping from the end of the list to the start. It chooses that instance, and the position moves to the entry after it. If the position is past the end of the list, for example after an instance disappeared, it wraps to the start. When every instance is eligible and requests are sent one at a time, the numbers of attempts sent to any two instances differ by at most one.
- **least_connections.** The client chooses the eligible instance with the fewest attempts currently in progress from this client. Ties may be broken in any way. A client cannot see other clients' connections, so the count covers only its own attempts.

### 8.5  Retries and backoff

- If an attempt fails with a code marked Yes in Table 2 and attempts remain, the client waits and then makes another attempt. Before attempt number a (a = 2, 3, and so on), it waits base-delay-ms × 2<sup>a − 2</sup> milliseconds. With the defaults, the waits are 100, 200, and 400 milliseconds.
- Each attempt, including a retry, asks the load balancer for an instance, so a retry may go to a different instance.
- If an attempt fails with a code marked No, the client stops and reports that error without retrying.
- Before waiting, the client checks the request's deadline. If the wait is at least as long as the time left, the client does not wait; the request ends with DEADLINE_EXCEEDED (Section 8.8).
- If every attempt fails, the client reports the error code of the last attempt.

### 8.6  Circuit breakers

The client keeps one circuit breaker for each instance in its list. A breaker is in one of three states: CLOSED (normal), OPEN (the instance is skipped), or HALF_OPEN (trial attempts are allowed).

For the breaker, an attempt is a **failure** if it ends with TIMEOUT, CONNECTION_ERROR, PROTOCOL_ERROR, or INTERNAL, and a **success** if the instance returned `ok` set to true. Any other error code, such as INVALID_PARAMS, is neither: the instance worked correctly and the request itself was bad, so the breaker does not change. DEADLINE_EXCEEDED is also neither, because whether a deadline passes depends on the client's time limit, not only on the instance.

*Table 8. Circuit breaker transitions.*

| State | Event | New state |
|---|---|---|
| CLOSED | Success | CLOSED, and the count of consecutive failures resets to 0 |
| CLOSED | Failure, and consecutive failures are still below breaker-threshold | CLOSED |
| CLOSED | Failure, and consecutive failures now equal breaker-threshold | OPEN |
| OPEN | The load balancer chooses the instance after breaker-reset-ms milliseconds have passed since the breaker opened | HALF_OPEN |
| HALF_OPEN | Success, and successes since entering HALF_OPEN now equal breaker-successes | CLOSED |
| HALF_OPEN | Success, and successes since entering HALF_OPEN are still below breaker-successes | HALF_OPEN |
| HALF_OPEN | Failure | OPEN, and the breaker-reset-ms wait starts again |

- No attempt may be sent to an instance whose breaker is OPEN until breaker-reset-ms milliseconds have passed since it opened.
- While a breaker is HALF_OPEN, at most one attempt to that instance may be in progress at a time.
- An attempt's result changes the breaker only if the breaker has not changed state since that attempt started. For example, when several attempts to an instance are in progress and the breaker opens, the results of the other attempts do not affect it.

### 8.7  Event log

If `--events FILE` is given, the client writes one JSON object per line to FILE (the JSON Lines format), creating the file or replacing an existing one. Every object has `t_ms`, the time in milliseconds since the client started, and `event`, one of the types in Table 9. The grading tests read this file to check load balancing, retries, and circuit breakers, so it must match what the client actually did.

*Table 9. Event types.*

| event | Other fields | Written when |
|---|---|---|
| instances | `ids`: array of instance_id strings in list order | After the first successful lookup, and whenever the set of instances changes |
| attempt | `request`, `attempt`, `instance_id`, `request_id`, `deadline_ms` | An attempt starts. instance_id is null if no instance was eligible. |
| result | `request`, `attempt`, `instance_id`, `request_id`, `ok`, `code`, `latency_ms` | An attempt ends. code is null when ok is true. |
| backoff | `request`, `next_attempt`, `delay_ms` | The client starts waiting before a retry. |
| breaker | `instance_id`, `from`, `to` | A breaker changes state. |

`request` numbers requests 1, 2, 3, and so on in the order they start, and `attempt` numbers the attempts of one request starting at 1. `request_id` is the value sent in the frame header, and `deadline_ms` is the deadline sent with that attempt. When requests run at the same time, lines for different requests may be interleaved, but every line must be complete: two threads must never write into the same line.

Example, with instances started using `--id s0` and `--id s1`, where s0 has stopped:

```
{"t_ms": 12.4, "event": "instances", "ids": ["s0", "s1"]}
{"t_ms": 13.0, "event": "attempt", "request": 1, "attempt": 1, "instance_id": "s0", "request_id": 1, "deadline_ms": 5000}
{"t_ms": 13.4, "event": "result", "request": 1, "attempt": 1, "instance_id": "s0", "request_id": 1, "ok": false, "code": "CONNECTION_ERROR", "latency_ms": 0.4}
{"t_ms": 13.5, "event": "backoff", "request": 1, "next_attempt": 2, "delay_ms": 100}
{"t_ms": 113.7, "event": "attempt", "request": 1, "attempt": 2, "instance_id": "s1", "request_id": 1, "deadline_ms": 4899}
{"t_ms": 115.2, "event": "result", "request": 1, "attempt": 2, "instance_id": "s1", "request_id": 1, "ok": true, "code": null, "latency_ms": 1.5}
```

The second attempt sends a deadline of 4899 milliseconds because 100.7 milliseconds of the 5000-millisecond limit had passed since the first attempt started.

### 8.8  Deadlines

Each request has a time limit of deadline-ms milliseconds, which starts when its first attempt starts. If deadline-ms is 0, the request has no limit: the client sends 0 in the deadline_ms field and otherwise behaves as in Sections 8.1 to 8.7.

- Before each attempt, the client computes the time left. If none is left, the request ends with DEADLINE_EXCEEDED.
- Each attempt sends the time left, rounded down to a whole number of milliseconds and at least 1, in the deadline_ms field.
- An attempt's timeout is timeout-ms or the time left, whichever is shorter. If the time left was the limit and it runs out, the attempt ends with DEADLINE_EXCEEDED, and so does the request.
- Before a retry, if the backoff wait (Section 8.5) is at least as long as the time left, the client does not wait; the request ends with DEADLINE_EXCEEDED.
- If an instance responds with DEADLINE_EXCEEDED, the request ends with DEADLINE_EXCEEDED.

## 9  Summary of values

*Table 10. Defaults and fixed values.*

| Setting | Value | Set by |
|---|---|---|
| Maximum body size | 1,048,576 bytes | Fixed |
| Header size | 5 bytes (version 1), 17 bytes (version 2) | Fixed |
| Concurrent connections per server | At least 32 | Fixed |
| Idle connection timeout | 30 s | Fixed |
| Server shutdown | Within 2 s | Fixed |
| Registry TTL | 6000 ms | Registry --ttl-ms |
| Heartbeat interval | TTL ÷ 3 (2000 ms by default) | Returned by registry.register |
| Expiry deadline | TTL + 1000 ms after the last heartbeat | Fixed |
| Registration retry interval | 1000 ms | Fixed |
| Deregistration on shutdown | Gives up after 1 s | Fixed |
| Attempt timeout | 2000 ms | Client --timeout-ms |
| Request deadline | 5000 ms | Client --deadline-ms |
| Retries | 3 | Client --max-retries |
| Backoff base delay | 100 ms | Client --base-delay-ms |
| Breaker threshold | 3 failures | Client --breaker-threshold |
| Breaker reset time | 5000 ms | Client --breaker-reset-ms |
| Half-open successes | 2 | Client --breaker-successes |
| Instance list refresh | 1000 ms | Client --refresh-ms |

Timing checks in the grading tests allow a tolerance of [FILL IN: 200] milliseconds.

Any change to this document will be announced on Canvas and will come with a new document version number.
