# Phase 1: Completion coverage and assertion quality

## Context
- Zsh completion support has already been added.
- Completion installation checks have already been added.
- This phase covers the next highest-value gaps in completion behavior validation.

## Goal
Improve confidence that completion results are correct, not just present somewhere in the output.

## Scope
- Add prefix-filtering scenarios for supported shells.
- Verify exact completion candidates for the tested command shapes.
- Fail when unexpected completion candidates are returned.
- Check command/query exit status where that is not already enforced.

## Deliverables
- Expanded tests for partial token completion such as `de` and `bu`.
- Assertions that compare the actual completion set against the expected set.
- Validation that shell-specific completion commands complete successfully.

## Out of scope
- PTY synchronization improvements.
- Broader negative and edge-case scenarios.
- Test framework refactors.

## Acceptance criteria
- Tests cover both "show all completions" and prefix-filtered completions.
- Tests fail if an unexpected completion candidate appears.
- Fish completion checks validate success status in addition to output.
