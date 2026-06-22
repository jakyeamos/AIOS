# Module: Dependency Policy

Module ID: `@module:dependency_policy`

Respect the host repo package manager, lockfile, and dependency policy. Treat dependency changes as high blast-radius until tests and builds prove otherwise.

Before adding a package, check whether the standard library, existing dependency, or framework utility already solves the problem.

Networked registry queries and installs require explicit permission in restricted runtimes.

