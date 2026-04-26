# Phase 3: Test structure and maintainability

## Context
After behavior and reliability are improved, the remaining work is to make future completion enhancements easier to test and review.

## Goal
Improve the maintainability and extensibility of the completion test suite.

## Scope
- Move the suite to a clearer test structure, such as a standard Python test framework.
- Reduce duplication across shell-specific test paths.
- Make it easier to add new completion scenarios as the CLI grows.

## Deliverables
- A test layout that supports clearer failures and easier extension.
- Shared helpers or fixtures for repeated shell setup and assertions.
- Parameterized scenarios for common completion expectations where appropriate.

## Out of scope
- Introducing unrelated tooling outside the existing Python-based test approach.
- Expanding CLI feature scope beyond completion testing.

## Acceptance criteria
- Adding a new completion scenario requires minimal duplication across shells.
- Failures identify the shell and scenario clearly.
- The suite remains runnable through the repository's existing build/test entry point.
