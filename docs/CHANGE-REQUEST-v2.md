# CS446/CS646 Homework 2: Change Request, Protocol Version 2

Released November 24, 2026. Due with your final submission on Wednesday, December 9, 2026.

This document describes the change from protocol version 1 to version 2. The exact rules are in the updated specification, `docs/SPEC.md` (document version 2.0). If this document and the specification disagree, follow the specification.

## 1  What is changing and why

Version 1 of the protocol has two gaps that real RPC systems close:

- **A response cannot be matched to its request.** A version 1 client can only assume that the next response on a connection answers its last request. That is why version 1 makes the client close a connection after a timeout. Version 2 puts a request ID in the header of every frame, and the server copies it into the response. The same ID is used for every retry of a request, so you can follow one request through the event log.
- **Nobody knows when the client has given up.** In version 1, a stats instance keeps working on a request even after the client has timed out and moved on. Version 2 puts a deadline in every request: how much longer the client is willing to wait. The instance replies early when it cannot finish in time, and the client stops retrying when its time is used up. Production RPC frameworks such as gRPC also let a client attach a deadline to each call.

The deadline is a number of milliseconds, not a clock time, because the clocks on your computer and on your VMs do not agree exactly.

## 2  Summary of changes

*Table 1. What changes, and where the specification describes it.*

| Part | What changes | Specification |
|---|---|---|
| Framing (`rpc/`) | A new version 2 frame with a 17-byte header that adds request_id and deadline_ms. Send version 2 requests; accept both versions; answer in the request's version; check the request_id of each response. | Sections 2.2 to 2.6, and 4 |
| Stats service | Enforce deadlines: reply within the deadline, or with DEADLINE_EXCEEDED. | Section 6.3 |
| Registry | Accept version 2 requests and copy each request_id into the response. Ignore deadlines. | Sections 2.4 and 2.5 |
| Client | Request IDs; a time limit for each whole request (`--deadline-ms`); shorter attempt timeouts near the deadline; no retries past it; two new fields in the event log. | Sections 7.4, 8.1, and 8.5 to 8.8 |
| Error codes | New code DEADLINE_EXCEEDED. UNSUPPORTED_VERSION now means a version byte other than 1 or 2. | Section 5 |

Everything else in the specification is unchanged. To see every changed line of the specification after you pull, run `git log -p -- docs/SPEC.md`.

## 3  Getting the change

Your combined milestone, due Wednesday, November 25 and tagged `m2`, is graded on version 1. You may start version 2 before then, but keep your version 1 behavior working. Commit any work in progress, then pull:

```
git status                      # everything committed?
git pull --no-rebase origin main
```

The pull adds this document and replaces `docs/SPEC.md` with version 2.0. Your servers must still accept version 1 requests, so keep your version 1 tests and run them alongside your new version 2 tests.

## 4  Suggested approach

- Start a new chat. Give the agent this document and the specification, and ask for a plan that lists every file it will change, before any code is written.
- Change one program at a time: `rpc/` first, then `registry/`, `services/stats/`, and `client/`. Commit after each one.
- After each step, run your version 1 tests as well as your version 2 tests. Accepting version 1 requests and answering them in version 1 is easy to break while adding version 2.
- Update `AGENTS.md` if your rules for the agent change.
- Defects the agent introduces during the migration belong in `AI_REVIEW.md` like any others.

## 5  Deployment

Your final deployment on GCP (handout Section 7) runs version 2 of all three programs. Your servers must still accept version 1 requests, as the specification requires.

## 6  Grading and questions

Protocol version 2 is graded as described in the handout (Section 9, Table 5), with course tests that check both version 2 and version 1 requests. Questions about this change request: [Canvas discussion](https://umassboston.instructure.com/courses/45568/discussion_topics/269179).
