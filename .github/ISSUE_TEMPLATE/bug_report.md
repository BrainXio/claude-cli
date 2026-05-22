---
name: Bug Report
description: Report something that is not working as expected
title: "[BUG] "
labels:
  - bug
assignees: ""
body:
  - type: markdown
    attributes:
      value: |
        ## Description
        A clear and concise summary of the bug.
  - type: textarea
    id: steps-to-reproduce
    attributes:
      label: Steps to Reproduce
      description: "Ordered steps to reproduce the bug: what did you do, in what order?"
      placeholder: |
        1.
        2.
        3.
    validations:
      required: true
  - type: textarea
    id: expected-behavior
    attributes:
      label: Expected Behavior
      description: What should have happened instead of the bug?
    validations:
      required: true
  - type: textarea
    id: actual-behavior
    attributes:
      label: Actual Behavior
      description: What actually happened? Include any error messages or unexpected outcomes.
    validations:
      required: true
  - type: textarea
    id: logs-output
    attributes:
      label: Logs / Output
      description: Relevant log entries, error traces, or command output (use a code block)
      placeholder: |
        ```text
        <paste logs here>
        ```
    validations:
      required: false
  - type: textarea
    id: possible-fix
    attributes:
      label: Possible Fix (Optional)
      description: If you have an idea of what is causing the bug, describe it here.
    validations:
      required: false
  - type: textarea
    id: additional-context
    attributes:
      label: Additional Context
      description: Any other context such as branch, commit SHA, or related issues.
    validations:
      required: false
---
