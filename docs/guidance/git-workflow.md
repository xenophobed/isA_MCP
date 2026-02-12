# Git Workflow Guide for isA_MCP

This document outlines the git workflow conventions for the isA_MCP project. Following these guidelines ensures consistent collaboration and maintainable version history.

## Table of Contents

- [Branching Strategy](#branching-strategy)
- [Commit Conventions](#commit-conventions)
- [Pull Request Workflow](#pull-request-workflow)
- [Branch Naming Examples](#branch-naming-examples)

---

## Branching Strategy

The isA_MCP project uses a modified GitFlow branching model optimized for continuous delivery.

### Branch Types

| Branch | Purpose | Naming | Lifetime |
|--------|---------|--------|----------|
| `main` | Production-ready code | `main` | Permanent |
| `develop` | Integration branch for features | `develop` | Permanent |
| `feature/*` | New features and enhancements | `feature/<description>` | Temporary |
| `fix/*` | Bug fixes | `fix/<description>` | Temporary |
| `hotfix/*` | Urgent production fixes | `hotfix/<description>` | Temporary |
| `release/*` | Release preparation | `release/<version>` | Temporary |

### Branch Hierarchy

```
main (production)
  |
  +-- hotfix/* (urgent fixes, merged to main AND develop)
  |
develop (integration)
  |
  +-- feature/* (new features)
  |
  +-- fix/* (bug fixes)
  |
  +-- release/* (release prep, merged to main AND develop)
```

### Branch Descriptions

#### main
- Contains production-ready, tested code
- Protected branch - no direct commits allowed
- Only receives merges from `release/*` and `hotfix/*` branches
- Every commit on main should be tagged with a version

#### develop
- Primary integration branch for ongoing development
- Contains the latest delivered development changes
- Source branch for all feature and fix branches
- Must pass all tests before merging features

#### feature/*
- Created from `develop` for new functionality
- Examples of features in isA_MCP context:
  - `feature/add-vision-tool` - Adding a new vision analysis tool
  - `feature/skill-caching` - Implementing skill service caching
  - `feature/sse-improvements` - Enhancing SSE streaming
  - `feature/consul-health-checks` - Adding Consul health check integration

#### fix/*
- Created from `develop` for non-urgent bug fixes
- Examples:
  - `fix/memory-leak` - Fixing memory leak in tool discovery
  - `fix/qdrant-connection-timeout` - Resolving database timeout issues
  - `fix/embedding-batch-size` - Correcting batch processing logic

#### hotfix/*
- Created from `main` for critical production issues
- Must be merged back to both `main` AND `develop`
- Examples:
  - `hotfix/security-patch` - Urgent security vulnerability fix
  - `hotfix/db-connection-crash` - Critical database connection failure

#### release/*
- Created from `develop` when preparing a release
- Only bug fixes, documentation, and release-oriented changes allowed
- Merged to both `main` and `develop` when complete
- Examples:
  - `release/v0.2.0` - Version 0.2.0 release preparation
  - `release/staging-v0.1.1` - Staging release preparation

---

## Commit Conventions

The isA_MCP project follows the [Conventional Commits](https://www.conventionalcommits.org/) specification.

### Commit Message Format

```
<type>(<scope>): <description>

[optional body]

[optional footer(s)]
```

### Commit Types

| Type | Description | Example |
|------|-------------|---------|
| `feat` | New feature | `feat(tools): add web scraping tool` |
| `fix` | Bug fix | `fix(search): correct vector similarity threshold` |
| `docs` | Documentation only | `docs(readme): update installation steps` |
| `style` | Formatting, no code change | `style(core): fix indentation in main.py` |
| `refactor` | Code change without fix/feature | `refactor(discovery): simplify tool registration` |
| `perf` | Performance improvement | `perf(qdrant): optimize batch embedding queries` |
| `test` | Adding or updating tests | `test(skill): add unit tests for skill service` |
| `chore` | Maintenance tasks | `chore(deps): update fastmcp to 2.0.0` |
| `build` | Build system changes | `build(docker): optimize multi-stage build` |
| `ci` | CI configuration changes | `ci(github): add staging deploy workflow` |

### Scope Examples for isA_MCP

Scopes should correspond to the affected component or service:

| Scope | Component |
|-------|-----------|
| `tools` | Tool implementations in `tools/` |
| `discovery` | Auto-discovery system |
| `sync` | Sync service |
| `skill` | Skill service |
| `search` | Hierarchical search service |
| `core` | Core MCP server (`main.py`) |
| `qdrant` | Qdrant vector database integration |
| `postgres` | PostgreSQL integration |
| `api` | API endpoints |
| `config` | Configuration management |
| `docker` | Docker/container configuration |
| `k8s` | Kubernetes manifests |

### Commit Message Examples

**Feature with scope:**
```
feat(tools): add vision analyzer for image processing

Implements a new MCP tool that uses OpenAI's vision API to analyze
images and extract structured information.

Closes #42
```

**Bug fix:**
```
fix(search): prevent duplicate results in hierarchical search

The search service was returning duplicate tools when multiple skills
matched the same tool. Added deduplication logic based on tool ID.
```

**Breaking change:**
```
feat(api)!: restructure tool response format

BREAKING CHANGE: Tool response now includes metadata object.
Clients must update to handle the new response structure.
```

**Chore with multiple changes:**
```
chore: clean up deprecated code and update dependencies

- Remove unused legacy discovery module
- Update pydantic to 2.5.0
- Fix deprecation warnings in tests
```

### Commit Best Practices

1. **Atomic commits**: Each commit should represent a single logical change
2. **Present tense**: Use "add feature" not "added feature"
3. **Imperative mood**: Use "fix bug" not "fixes bug"
4. **No period**: Don't end the subject line with a period
5. **50/72 rule**: Subject line max 50 chars, body wrapped at 72 chars
6. **Reference issues**: Include issue numbers when applicable

---

## Pull Request Workflow

### Creating a Pull Request

1. **Create feature branch from develop**
   ```bash
   git checkout develop
   git pull origin develop
   git checkout -b feature/add-new-tool
   ```

2. **Make changes with atomic commits**
   ```bash
   # Work on your feature
   git add services/new_tool.py
   git commit -m "feat(tools): implement new tool skeleton"

   git add tests/unit/test_new_tool.py
   git commit -m "test(tools): add unit tests for new tool"
   ```

3. **Keep branch updated with develop**
   ```bash
   git fetch origin
   git rebase origin/develop
   ```

4. **Push and create PR**
   ```bash
   git push -u origin feature/add-new-tool
   # Create PR via GitHub CLI or web interface
   gh pr create --base develop --title "feat(tools): add new tool" --body "..."
   ```

5. **Request review**
   - Assign appropriate reviewers
   - Add relevant labels (e.g., `enhancement`, `needs-review`)
   - Link related issues

6. **Address feedback**
   - Make requested changes in new commits
   - Respond to all review comments
   - Request re-review when ready

7. **Merge to develop**
   - Ensure all CI checks pass
   - Use squash merge for feature branches
   - Delete the feature branch after merge

### PR Title Format

PR titles should follow the same commit convention format:

```
<type>(<scope>): <description>
```

Examples:
- `feat(tools): add vision analyzer tool`
- `fix(search): resolve duplicate results issue`
- `docs(api): add OpenAPI documentation`

### PR Description Template

```markdown
## Summary
Brief description of changes and motivation.

## Changes
- List of specific changes made
- Another change
- And another

## Testing
- [ ] Unit tests added/updated
- [ ] Component tests pass
- [ ] Integration tests pass
- [ ] Manual testing performed

## Related Issues
Closes #123
Related to #456

## Checklist
- [ ] Code follows project style guidelines
- [ ] Self-review completed
- [ ] Documentation updated if needed
- [ ] No sensitive data committed
```

### Merge Strategies

| Branch Type | Merge To | Strategy |
|-------------|----------|----------|
| `feature/*` | `develop` | Squash merge |
| `fix/*` | `develop` | Squash merge |
| `release/*` | `main` | Merge commit |
| `release/*` | `develop` | Merge commit |
| `hotfix/*` | `main` | Merge commit |
| `hotfix/*` | `develop` | Merge commit |

---

## Branch Naming Examples

### Feature Branches

```
feature/add-vision-tool
feature/implement-skill-caching
feature/consul-integration
feature/sse-progress-tracking
feature/batch-embedding-api
feature/tool-marketplace-ui
```

### Fix Branches

```
fix/memory-leak-discovery
fix/qdrant-timeout
fix/duplicate-tool-registration
fix/embedding-dimension-mismatch
fix/consul-fallback-url
```

### Hotfix Branches

```
hotfix/security-jwt-validation
hotfix/database-connection-pool
hotfix/critical-search-failure
```

### Release Branches

```
release/v0.2.0
release/v1.0.0-rc1
release/staging-v0.1.1
```

---

## Quick Reference

### Starting New Work

```bash
# Update develop
git checkout develop && git pull

# Create feature branch
git checkout -b feature/my-feature

# Work and commit
git add . && git commit -m "feat(scope): description"

# Push and create PR
git push -u origin feature/my-feature
gh pr create --base develop
```

### Keeping Branch Updated

```bash
git fetch origin
git rebase origin/develop
# Resolve conflicts if any
git push --force-with-lease
```

### After PR is Merged

```bash
git checkout develop
git pull
git branch -d feature/my-feature
```

---

See also:
- [Release Process](./release-process.md)
- [Git Commands Reference](./git-commands.md)
- [Contributing Guidelines](../../CONTRIBUTING.md)
