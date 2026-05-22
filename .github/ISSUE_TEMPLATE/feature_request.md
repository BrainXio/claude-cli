---
name: Feature Request
description: Suggest an idea or enhancement
title: "[FEATURE] "
labels:
  - enhancement
assignees: ""
body:
  - type: markdown
    attributes:
      value: |
        ## Problem Description
        Describe the problem, limitation, or friction point this enhancement would address.
        Be concrete — cite a specific scenario or pain point, not a vague future need.
  - type: textarea
    id: proposed-solution
    attributes:
      label: Proposed Solution
      description: Describe the solution you are proposing.
    validations:
      required: true
  - type: textarea
    id: alternatives-considered
    attributes:
      label: Alternatives Considered
      description: What other approaches did you consider? Why were they rejected?
    validations:
      required: false
  - type: dropdown
    id: pr-contribution
    attributes:
      label: Would you submit a PR?
      description: Are you planning to contribute the implementation yourself?
      options:
        - "Yes — I will implement this"
        - "No — someone else should handle it"
        - "Need guidance — I want to contribute but need direction"
    validations:
      required: true
  - type: textarea
    id: additional-context
    attributes:
      label: Additional Context
      description: Attach mock configs, diagrams, or any other supporting material.
    validations:
      required: false
---
