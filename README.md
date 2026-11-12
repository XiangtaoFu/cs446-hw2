# CS446/CS646 HW2: A Resilient Microservice System

> **Starter repository.** Clone this repository to start HW2 (handout Section 5), and do not push to it.
> Keep your own copy private. The handout is on Canvas, and the specification is [`docs/SPEC.md`](docs/SPEC.md).
> `README.md` is one of your graded files: replace the prompts below with your own content, and delete this note.

## Repository layout

| Path | Owner | Contents |
|---|---|---|
| `docs/` | Course | The specification and related documents. Do not edit; updates arrive with `git pull`. |
| `AGENTS.md` | You | Rules for your coding agent. Create it before you write any code (handout Section 6.3). |
| `rpc/` | You | Shared library used by all three programs: framing, messages, server loop, client stub. |
| `registry/` | You | The registry program. |
| `services/stats/` | You | The stats service program. |
| `client/` | You | Load balancing, retries, circuit breakers, and the command line. |
| `tests/` | You | Your own tests. |
| `deploy/` | You | Scripts and screenshots for your GCP deployment. |
| `chatlogs/` | You | Exported agent sessions. |
| `README.md`, `DESIGN.md`, `DEPLOYMENT.md`, `AI_REVIEW.md` | You | Documentation (handout Section 8.2). |

Course updates, including the protocol version 2 change request on [FILL IN: change request date], arrive with:

```
git pull --no-rebase origin main
```

Commit your work before you pull.

## How to run

*Write how to start the registry, the stats instances, and the client, on your computer and on GCP.*

## How to run the tests

*Write how to run your own tests in `tests/`.*

## Status

*Write what works and what does not, as of this submission.*

## Author

*Your name, and whether you are in CS446 or CS646.*
