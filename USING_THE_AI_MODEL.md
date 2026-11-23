# Working with the Course AI Model on HW2

November 23, 2026

## What we found

The course model can do real HW2 work, but it cannot be trusted to check its own work. Course staff did all of Milestone 1 with it in VS Code, the way you would. It got to the end, but only because we caught its mistakes along the way.

- **It needed 5 corrections in 51 minutes.** Without them it would have stopped at the registry with code that did not start.
- **It is good at:** reading the SPEC, laying out files and functions, writing tests, and fixing a bug once it can see the error message.
- **It is bad at:** noticing it is wrong. Three times it said the work was done or the tests passed when they had not.

The model in the picker is still called "Nemotron-Cascade-2-30B-A3B". Since November 18 that name is answered by a different, stronger model (Gemma 4 31B); you do not need to change anything.

## Where it goes wrong

Most of the time lost in our run came from believing the agent's summary instead of checking it. Each row is something that actually happened.

| What happened | What you see | What to do |
| --- | --- | --- |
| Said "all tests passed" when one still failed | A confident summary; the test output above it ends with `FAILED (failures=1)` | Read the last line of the test run yourself. Only `OK` means passed |
| Ran only the tests for the current step | Its tests pass, but code from an earlier step is now broken | Ask it to run the whole suite: `python -m unittest discover -s tests -v` |
| Committed only one of the four files it changed | "All changes committed", but `git status` still lists files | Run `git status` after every commit |
| Could not find a bug because the code hid the error | It moves the same lines around, or flips a comment back and forth, and the test result never changes | Stop it and make the error visible (next sections) |
| Wrote tests with pytest and ran `pip install` | Third-party packages appear in your project | HW2 is standard library only. Put that in AGENTS.md before any code |
| Forgot what it had changed | It describes its own edit wrongly, often after VS Code compacts a long chat | Check the code with `git diff` rather than trusting its description |

## A workflow that works

Give it one small, well-defined piece at a time, and verify each piece yourself before you move on.

1. **Write AGENTS.md first.** Include: Python 3.10+, standard library only (tests too, so `unittest`), follow `docs/SPEC.md` exactly, never edit `docs/`, logs to standard error, run all tests before committing. In our run, the step done before AGENTS.md existed used pytest; after it existed, the agent followed the rules.
2. **One piece per request.** For example: the framing layer, then the shared server, then the registry, then the stats service. Name the SPEC sections each piece needs.
3. **Ask for tests with every piece,** and say how they should run: start the programs as subprocesses, wait for `READY`, use a free port.
4. **Check its claims before you accept them:**
   - Run `python -m unittest discover -s tests -v` and read the last line.
   - Run `git status` to see whether anything is left uncommitted.
   - Run `git diff HEAD~1` to see what the last commit really changed.
5. **Commit each working piece** so you can always go back with `git checkout`.
6. **Start a new chat for each new piece.** Everything it needs is in the files and in git. A long chat is slower, and VS Code eventually shortens it to a summary that can be wrong. Stay in the same chat only to fix the piece you are on.

## When it gets stuck

If the test result stays the same after two or three changes, the agent cannot see the cause. Press the stop button and give it a way to see the error; do not let it keep guessing.

**Why it gets stuck.** In our run, a server caught every exception with `except Exception: pass`. The real error, a misspelled class name, was thrown away, so the agent saw only a dropped connection. It spent 6 minutes changing unrelated lines. Once it could read the error, it fixed the bug in one edit.

**Ways to make an error visible:**

- Never swallow exceptions while you develop: print them to standard error with a traceback.
- Tests that start your programs as subprocesses hide their output. Start the program yourself in a terminal and send it the failing request; its standard error shows the real error.
- Run only the failing test: `python -m unittest tests.test_registry.TestRegistry.test_name -v`.
- If a test hangs, run it alone and look at what changed since the last commit: `git diff`.

**Prompts that worked for us:**

```
The tests start the registry as a subprocess, so its stderr never reaches the test output and you cannot see the exception. Start the registry yourself in the background, send it the request that fails, read its stderr, and fix the cause it shows. Then run all the tests and commit.
```

```
You said all the tests passed, but your last test run ended with FAILED (failures=1). Find out why that test fails, fix it, and run all the tests again. Only say the tests pass when the output ends with OK. Then commit.
```

```
You only ran this step's tests. Run all the tests with `python -m unittest discover -s tests -v`; one of the earlier tests now fails. Make every test pass, then run `git status` and commit everything that belongs to this step.
```

If the same error keeps coming back even after a hint like these, stop the agent and start a new chat. A long history full of failed attempts pulls it back into the same mistakes.

## Safety

Keep VS Code asking before every command, and read each command before you click Allow. The agent runs commands on your own computer.

- **Do not turn on auto-approve.** In our run, with auto-approve on, VS Code refused `Stop-Process -Name python`. The agent rewrote it as a loop over process IDs and killed every Python process on the machine, not just the ones it had started.
- **Deny commands that stop processes by name or delete folders** (`Stop-Process -Name`, `taskkill /IM`, `pkill`, `rm -rf`, `rmdir /s`). Ask it to stop the specific process it started instead.
- **Deny `pip install`.** HW2 allows the standard library only, and an install changes your Python for every project.
- **Commit before risky changes,** so `git checkout` can undo anything the agent breaks.

## Good to know

- **Hours:** the course model is switched on at 8:00 AM and ready about 10 minutes later, and switched off at 1:00 AM, US Eastern time. Outside those hours you get an "offline" message.
- **Use Agent mode.** In Ask mode the model is read-only: it will describe the change but cannot make it.
- **Chat length:** VS Code allows about 120,000 tokens per chat. In our run it shortened the chat to a summary 3 times in 51 minutes, each time at about 100,000 tokens. One piece per chat avoids this.
- **Your conversations are recorded,** as the setup guide says, so course staff can help when something goes wrong. Tell us the date and time if you want us to look at a session.
