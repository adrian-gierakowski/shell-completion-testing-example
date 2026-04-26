# Phase 2: Shell reliability and edge-case coverage

## Context
Phase 1 tightens behavioral assertions. This phase focuses on reducing flakiness and extending scenario coverage.

## Goal
Make the completion test suite more reliable across shells and more representative of real failure modes.

## Scope
- Improve shell readiness and synchronization before sending completion triggers.
- Add negative and edge-case scenarios.
- Verify behavior for already-complete inputs and unknown prefixes.
- Ensure spawned interactive shells are shut down cleanly where practical.

## Deliverables
- More reliable PTY interaction setup for interactive shell tests.
- Tests for unknown prefixes returning no candidates.
- Tests for already-complete commands and trailing-space behavior.
- Cleanup or exit handling for spawned shells.

## Out of scope
- Large-scale test framework migration.
- Reorganizing the suite into a new project structure.

## Acceptance criteria
- Interactive shell tests no longer depend on immediate post-spawn command timing alone.
- The suite covers at least one no-match scenario and one already-complete scenario.
- Interactive test runs leave no hanging shell processes.
