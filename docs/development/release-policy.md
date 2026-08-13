# Release policy

Commit messages follow Conventional Commits. Releases are generated from `main` by `python-semantic-release` after branch protection and CI checks are configured. The release workflow is deliberately manual groundwork until those controls are verified. Version command design is planned for M1 and will report package version, schema version, and build commit.

Before 1.0, breaking changes bump the MINOR version; after 1.0, normal SemVer applies. Release notes must state evidence/benchmark changes and any public-data boundary changes.

