<!--
  SYNC IMPACT REPORT
  ==================
  Version change: N/A → 1.0.0 (initial adoption)

  Added Principles:
  - I. TDD Cycle (Red-Green-Refactor)
  - II. TDD Methodology
  - III. Tidy First Approach
  - IV. Commit Discipline
  - V. Code Quality Standards
  - VI. Refactoring Guidelines
  - VII. Development Workflow

  Added Sections:
  - Core Principles (7 principles)
  - Code Quality Standards
  - Development Workflow
  - Governance

  Removed Sections: None (initial creation)

  Templates requiring updates:
  - .specify/templates/plan-template.md: ✅ Updated - Constitution Check section now has TDD/Tidy First gates
  - .specify/templates/spec-template.md: ✅ No changes needed - User scenarios align with TDD approach
  - .specify/templates/tasks-template.md: ✅ Updated - TDD language and Tidy First commit guidance added
  - .specify/templates/checklist-template.md: ✅ No changes needed
  - .specify/templates/agent-file-template.md: ✅ No changes needed

  Follow-up TODOs: None
-->

# LoTa-Bench Constitution

## Core Principles

### I. TDD Cycle (Red-Green-Refactor)

The TDD cycle MUST be followed for all production code:

1. **Red**: Write a failing test that defines a small increment of functionality
2. **Green**: Write the minimum code necessary to make the test pass
3. **Refactor**: Improve code structure only after tests pass

This cycle is NON-NEGOTIABLE. No production code may be written without a failing
test first. The cycle repeats for each new piece of functionality.

### II. TDD Methodology

Tests MUST be written following these guidelines:

- Start by writing the simplest failing test that defines new functionality
- Use meaningful test names that describe behavior (e.g., `shouldSumTwoPositiveNumbers`)
- Make test failures clear and informative with descriptive assertion messages
- Write just enough code to make the test pass—no more
- Run all tests (except long-running tests) after each change
- One test at a time: write it, make it run, then improve structure

### III. Tidy First Approach

All code changes MUST be separated into two distinct types:

1. **Structural Changes**: Rearranging code without changing behavior
   - Renaming variables, methods, or classes
   - Extracting methods or classes
   - Moving code between files
   - Reorganizing imports or dependencies

2. **Behavioral Changes**: Adding or modifying actual functionality
   - New features or capabilities
   - Bug fixes that alter output
   - Performance optimizations that change behavior

**Rules**:
- Structural and behavioral changes MUST NOT be mixed in the same commit
- When both are needed, structural changes MUST come first
- Structural changes MUST be validated by running tests before AND after
- Tests MUST pass identically before and after structural changes

### IV. Commit Discipline

Commits MUST only be made when ALL of the following conditions are met:

1. ALL tests are passing
2. ALL compiler/linter warnings have been resolved
3. The change represents a single logical unit of work
4. The commit message clearly states whether it contains structural or behavioral changes

**Commit Message Format**:
- Structural commits: `refactor: [description of structural change]`
- Behavioral commits: `feat|fix|test: [description of behavioral change]`

Prefer small, frequent commits over large, infrequent ones.

### V. Code Quality Standards

All code MUST adhere to these quality standards:

- **Eliminate duplication ruthlessly**: DRY (Don't Repeat Yourself) is mandatory
- **Express intent clearly**: Names and structure MUST reveal purpose
- **Make dependencies explicit**: No hidden dependencies or global state
- **Single responsibility**: Methods MUST focus on one task
- **Minimize state and side effects**: Prefer pure functions where possible
- **Simplicity**: Use the simplest solution that could possibly work (YAGNI)

### VI. Refactoring Guidelines

Refactoring MUST follow these rules:

- Refactor ONLY when tests are passing (in the "Green" phase)
- Use established refactoring patterns with their proper names
- Make one refactoring change at a time
- Run tests after EACH refactoring step
- Prioritize refactorings that:
  1. Remove duplication
  2. Improve clarity and readability
  3. Reduce complexity
  4. Make dependencies explicit

### VII. Development Workflow

When approaching a new feature, follow this workflow:

1. Write a simple failing test for a small part of the feature (Red)
2. Implement the bare minimum to make it pass (Green)
3. Run tests to confirm they pass
4. Make any necessary structural changes (Tidy First), running tests after each
5. Commit structural changes separately with `refactor:` prefix
6. Add another test for the next small increment of functionality
7. Repeat until the feature is complete
8. Commit behavioral changes separately with `feat:|fix:|test:` prefix

This process MUST be followed precisely, prioritizing clean, well-tested code
over quick implementation.

## Code Quality Standards

### Testing Requirements

- Unit tests MUST cover all public methods with meaningful business logic
- Integration tests MUST cover critical user journeys
- Contract tests MUST cover external API boundaries
- Test coverage is measured by behavior covered, not lines executed
- Tests MUST be fast enough to run frequently (long-running tests may be excluded
  from the standard test run but MUST be clearly marked)

### Observability

- Structured logging MUST be used for all significant operations
- Error messages MUST be clear and actionable
- Text I/O ensures debuggability: stdin/args → stdout, errors → stderr

## Development Workflow

### Feature Development Process

1. **Understand**: Read and understand the requirements fully
2. **Plan**: Break the feature into small, testable increments
3. **Test First**: Write failing tests for the first increment
4. **Implement**: Write minimum code to pass tests
5. **Refactor**: Improve structure while keeping tests green
6. **Commit**: Small, atomic commits (structural separate from behavioral)
7. **Repeat**: Continue for each increment until feature complete

### Code Review Requirements

All code MUST be reviewed for:
- TDD compliance (tests exist and were written first)
- Tidy First compliance (structural and behavioral changes separated)
- Code quality standards adherence
- Commit discipline compliance

## Governance

This constitution supersedes all other development practices in this project.

### Amendment Procedure

1. Propose amendment in writing with rationale
2. Document the change type (principle addition/removal/modification)
3. Obtain approval from project maintainers
4. Update constitution with new version number
5. Create migration plan if existing code needs updates
6. Propagate changes to dependent templates

### Versioning Policy

Constitution versions follow semantic versioning:
- **MAJOR**: Backward incompatible principle removals or redefinitions
- **MINOR**: New principle added or materially expanded guidance
- **PATCH**: Clarifications, wording, typo fixes, non-semantic refinements

### Compliance Review

- All PRs MUST verify compliance with this constitution
- Complexity MUST be justified against these principles
- The plan-template.md "Constitution Check" section MUST be completed for all features

**Version**: 1.0.0 | **Ratified**: 2026-01-22 | **Last Amended**: 2026-01-22
