# Changelog

This folder stores **human-readable release notes** and dated summaries of what changed in the software, documentation, or supported hardware assumptions.

## Why it exists

Robotics stacks evolve quickly: new hand models, new transports, and stricter calibration rules. A changelog gives you a **time-ordered** way to answer:

- “Does this behavior match the version I shipped to a customer?”  
- “When did Talos or Scorpion support land?”  
- “What should I re-test after pulling `main`?”

## How to read it

Open the markdown files newest-first (filenames usually include a month or version hint). Cross-check against the **Revision Control** table in the main [repository README](../README.md) when you need pip or tag correlation.

## Contributing notes

When you make a user-visible change worth announcing, append a short entry to the appropriate changelog file **or** add a new dated file, following the style of existing entries in this folder.
