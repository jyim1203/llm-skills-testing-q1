---
name: python-repo-maintenance
description: Use when resolving an issue in a Python repository: inspect the structure, trace the current behavior, make the smallest correct change, and verify it with tests.
generated_from: assets/prompts/workflow_instructions.md
body_sha256: 05b85856a462e78909445981407e07c8348a452aef205e9c47996f4131c4068e
---

# Experimental workflow instructions

> **Single source of truth.** This exact text is used by *both* Condition B
> (pasted directly into the prompt) and Condition C (packaged as the body of
> `SKILL.md`). Do not edit one without regenerating the other via
> `scripts/build_skill.py`. The runner asserts the two hashes match.

When working on a repository task, follow this workflow:

1. **Inspect the repository.** Look at the directory structure and locate the
   modules and tests most relevant to the issue.
2. **Read and trace the code.** Read the related source and follow the current
   behavior end to end before making any edit.
3. **Translate the issue into expected behavior.** State what the correct
   behavior should be, and identify the likely cause and any constraints.
4. **Implement the smallest reasonable change.** Keep the fix consistent with
   the existing design and conventions of the codebase.
5. **Run the relevant tests.** Execute the tests that cover the affected code
   and check for regressions.
6. **Review the diff.** Re-read your changes and confirm they address the issue,
   then summarize what changed and what you actually verified.
