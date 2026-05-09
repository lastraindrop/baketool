# Contributing to BakeNexus

Thank you for your interest in contributing to BakeNexus!

## How to Contribute

1. **Reporting Bugs**: Use GitHub Issues to report bugs. Please include your Blender version and steps to reproduce.
2. **Feature Requests**: Open an issue to discuss new features.
3. **Pull Requests**:
   - Fork the repository.
   - Create a new branch for your feature or fix.
   - Ensure all tests pass by running `python automation/multi_version_test.py`.
   - Submit a pull request.

## Development Setup

1. Install Blender (3.3+).
2. Clone the repository into your Blender scripts/addons folder.
3. Use the `dev_tools/` for extracting translations or running specific tests.

## Code Style

- Follow PEP 8 for Python code.
- Ensure all UI strings are wrapped in `pgettext` or `iface_` for translation support.
- Document new functions and classes with docstrings.

---
BakeNexus is licensed under GPL-3.0-or-later.
