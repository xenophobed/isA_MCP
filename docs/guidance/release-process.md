# Release Process for isA_MCP

This document describes the release process for the isA_MCP project, including version numbering, release preparation, and deployment procedures.

## Table of Contents

- [Version Numbering](#version-numbering)
- [Release Types](#release-types)
- [Release Process Steps](#release-process-steps)
- [Testing Checklist](#testing-checklist)
- [Changelog Management](#changelog-management)
- [Hotfix Process](#hotfix-process)

---

## Version Numbering

isA_MCP follows [Semantic Versioning 2.0.0](https://semver.org/) (SemVer).

### Format

```
MAJOR.MINOR.PATCH[-PRERELEASE][+BUILD]
```

### Version Components

| Component | When to Increment | Example |
|-----------|-------------------|---------|
| **MAJOR** | Breaking API changes | `2.0.0` |
| **MINOR** | New features, backward compatible | `0.3.0` |
| **PATCH** | Bug fixes, backward compatible | `0.2.1` |

### Pre-release Identifiers

| Identifier | Purpose | Example |
|------------|---------|---------|
| `alpha` | Early testing, unstable | `v0.2.0-alpha.1` |
| `beta` | Feature complete, testing | `v0.2.0-beta.2` |
| `rc` | Release candidate | `v0.2.0-rc.1` |
| `staging` | Staging environment release | `v0.1.0-staging` |

### Version Examples for isA_MCP

```
v0.1.0          # Initial staging release (current)
v0.1.1          # Patch release with bug fixes
v0.2.0          # New features (public APIs, monitoring)
v0.2.0-alpha.1  # Alpha release for v0.2.0
v1.0.0          # First stable production release
v1.0.0-rc.1     # Release candidate for v1.0.0
```

### What Constitutes a Breaking Change

In the context of isA_MCP, breaking changes include:

- Changes to MCP tool input/output schemas
- Removal or renaming of public API endpoints
- Changes to configuration file format
- Database schema changes requiring migration
- Removal of supported Python versions

---

## Release Types

### Regular Release

Standard release with new features and/or bug fixes.

```
develop -> release/vX.Y.Z -> main + develop
```

### Patch Release

Bug fixes only, no new features.

```
develop -> release/vX.Y.Z -> main + develop
```

### Hotfix Release

Urgent fix for production issues.

```
main -> hotfix/vX.Y.Z -> main + develop
```

### Staging Release

Release to staging environment for testing.

```
develop -> release/staging-vX.Y.Z -> staging environment
```

---

## Release Process Steps

### 1. Prepare Release Branch

```bash
# Ensure develop is up to date
git checkout develop
git pull origin develop

# Create release branch
git checkout -b release/v0.2.0

# Push release branch
git push -u origin release/v0.2.0
```

### 2. Update Version Numbers

Update version in all relevant files:

**main.py or version.py:**
```python
__version__ = "0.2.0"
```

**pyproject.toml (if used):**
```toml
[project]
version = "0.2.0"
```

**deployment/k8s manifests:**
```yaml
image: isa-mcp:v0.2.0
```

Commit version updates:
```bash
git add .
git commit -m "chore(release): bump version to 0.2.0"
```

### 3. Update Changelog

Update `CHANGELOG.md` with all changes since the last release. See [Changelog Management](#changelog-management) for format.

```bash
git add CHANGELOG.md
git commit -m "docs(changelog): update for v0.2.0"
```

### 4. Run Full Test Suite

Execute all test layers to ensure release quality:

```bash
# Run complete test suite
python -m pytest tests/ -v --tb=short

# Run TDD tests specifically
python -m pytest -m tdd -v

# Run integration tests
python -m pytest tests/integration/ -v

# Check test coverage
python -m pytest tests/ --cov=. --cov-report=html
```

All tests must pass before proceeding.

### 5. Final Review

- Review all commits in the release branch
- Verify documentation is up to date
- Check for any security vulnerabilities
- Validate Docker build works correctly

```bash
# Build Docker image
docker build -t isa-mcp:v0.2.0 -f deployment/Dockerfile .

# Test the image
docker run --rm isa-mcp:v0.2.0 python -c "import main; print('OK')"
```

### 6. Merge to Main

```bash
# Switch to main
git checkout main
git pull origin main

# Merge release branch (no fast-forward)
git merge --no-ff release/v0.2.0 -m "release: v0.2.0"

# Push main
git push origin main
```

### 7. Create Release Tag

```bash
# Create annotated tag
git tag -a v0.2.0 -m "Release v0.2.0

Features:
- Public APIs for Skill and Search services
- Enhanced monitoring with Prometheus integration
- Improved error handling in discovery service

Bug Fixes:
- Fixed memory leak in tool registration
- Resolved Qdrant connection timeout issues"

# Push tag
git push origin v0.2.0
```

### 8. Merge Back to Develop

```bash
git checkout develop
git pull origin develop
git merge --no-ff release/v0.2.0 -m "chore: merge release/v0.2.0 back to develop"
git push origin develop
```

### 9. Create GitHub Release

```bash
# Using GitHub CLI
gh release create v0.2.0 \
  --title "v0.2.0" \
  --notes-file RELEASE_NOTES.md \
  --latest
```

Or create via GitHub web interface:
1. Go to Releases page
2. Click "Create a new release"
3. Select tag `v0.2.0`
4. Add release title and notes
5. Publish release

### 10. Cleanup

```bash
# Delete release branch locally
git branch -d release/v0.2.0

# Delete release branch remotely
git push origin --delete release/v0.2.0
```

---

## Testing Checklist

Before any release, verify the following:

### Unit Tests
- [ ] All unit tests pass
- [ ] New features have unit test coverage
- [ ] Test coverage >= 95%

### Component Tests
- [ ] Service contracts are validated
- [ ] Mock integrations work correctly
- [ ] Error handling is tested

### Integration Tests
- [ ] Database connections work
- [ ] Qdrant vector operations succeed
- [ ] Redis caching functions correctly
- [ ] Consul service discovery works

### API Tests
- [ ] All endpoints return expected responses
- [ ] Authentication/authorization works
- [ ] Error responses are correct

### Manual Testing
- [ ] MCP server starts successfully
- [ ] Health endpoint returns correct status
- [ ] Tool discovery completes
- [ ] Hierarchical search returns results
- [ ] SSE streaming works

### Infrastructure
- [ ] Docker image builds successfully
- [ ] Kubernetes manifests are valid
- [ ] Environment variables are documented
- [ ] No sensitive data in commits

### Documentation
- [ ] README is up to date
- [ ] API documentation is current
- [ ] Changelog is updated
- [ ] Migration guide (if breaking changes)

---

## Changelog Management

### Changelog Format

Follow the [Keep a Changelog](https://keepachangelog.com/) format:

```markdown
# Changelog

All notable changes to isA_MCP will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/),
and this project adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added
- New features not yet released

## [0.2.0] - 2025-02-15

### Added
- Public API endpoints for Skill service
- Public API endpoints for Hierarchical Search service
- Prometheus metrics integration
- Grafana dashboard templates

### Changed
- Improved error messages in discovery service
- Optimized batch embedding queries

### Fixed
- Memory leak in tool registration process
- Qdrant connection timeout on large queries
- Duplicate tool results in search

### Security
- Updated dependencies to address CVE-XXXX-YYYY

## [0.1.0] - 2025-01-18

### Added
- Initial release with core MCP functionality
- Auto-discovery system for tools, prompts, resources
- Skill service for tool categorization
- Hierarchical search with Qdrant
- SSE progress streaming
- PostgreSQL and Qdrant integration
```

### Change Categories

| Category | Description |
|----------|-------------|
| **Added** | New features |
| **Changed** | Changes to existing functionality |
| **Deprecated** | Features to be removed in future |
| **Removed** | Removed features |
| **Fixed** | Bug fixes |
| **Security** | Security-related changes |

---

## Hotfix Process

For urgent production issues that cannot wait for a regular release.

### 1. Create Hotfix Branch from Main

```bash
git checkout main
git pull origin main
git checkout -b hotfix/v0.1.1
```

### 2. Apply Fix

Make the minimum necessary changes to fix the issue:

```bash
# Fix the issue
git add .
git commit -m "fix(core): resolve critical database connection failure"
```

### 3. Update Version

```bash
# Bump patch version
# Update __version__ = "0.1.1"
git commit -am "chore(release): bump version to 0.1.1"
```

### 4. Test Thoroughly

```bash
# Run affected tests
python -m pytest tests/ -v

# Manual verification of the fix
```

### 5. Merge to Main

```bash
git checkout main
git merge --no-ff hotfix/v0.1.1 -m "hotfix: v0.1.1 - fix database connection"
git tag -a v0.1.1 -m "Hotfix v0.1.1: Fix critical database connection failure"
git push origin main --tags
```

### 6. Merge to Develop

```bash
git checkout develop
git merge --no-ff hotfix/v0.1.1 -m "chore: merge hotfix/v0.1.1 to develop"
git push origin develop
```

### 7. Deploy Immediately

Deploy the hotfix to production as soon as possible.

### 8. Cleanup

```bash
git branch -d hotfix/v0.1.1
git push origin --delete hotfix/v0.1.1
```

---

## Release Schedule

### Recommended Cadence

| Release Type | Frequency | Day |
|--------------|-----------|-----|
| Major | As needed | - |
| Minor | Monthly | First Tuesday |
| Patch | As needed | Any day |
| Staging | Weekly | Thursday |

### Release Freeze

- No new features merged 2 days before release
- Only critical bug fixes allowed during freeze
- Focus on testing and documentation

---

See also:
- [Git Workflow](./git-workflow.md)
- [Git Commands Reference](./git-commands.md)
- [Contributing Guidelines](../../CONTRIBUTING.md)
