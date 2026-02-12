# Git Commands Quick Reference

A quick reference guide for common git operations used in the isA_MCP project.

## Table of Contents

- [Daily Workflow](#daily-workflow)
- [Branch Management](#branch-management)
- [Stash Operations](#stash-operations)
- [Rebase vs Merge](#rebase-vs-merge)
- [Conflict Resolution](#conflict-resolution)
- [History and Inspection](#history-and-inspection)
- [Cleanup Commands](#cleanup-commands)
- [Advanced Operations](#advanced-operations)

---

## Daily Workflow

### Starting Your Day

```bash
# Update your local repository
git fetch origin

# Check current status
git status

# View recent activity
git log --oneline -10

# Switch to develop and update
git checkout develop
git pull origin develop
```

### Creating a Feature Branch

```bash
# Create and switch to new branch
git checkout -b feature/add-vision-tool

# Or using newer syntax
git switch -c feature/add-vision-tool
```

### Making Changes

```bash
# Stage specific files
git add services/vision_tool.py tests/test_vision.py

# Stage all changes
git add .

# Stage interactively (review each change)
git add -p

# Commit with message
git commit -m "feat(tools): add vision analyzer tool"

# Commit with detailed message (opens editor)
git commit
```

### Pushing Changes

```bash
# Push new branch to remote
git push -u origin feature/add-vision-tool

# Push existing tracked branch
git push

# Push with force (use carefully!)
git push --force-with-lease
```

### Updating Your Branch

```bash
# Fetch and merge in one step
git pull origin develop

# Fetch then rebase (cleaner history)
git fetch origin
git rebase origin/develop
```

---

## Branch Management

### Listing Branches

```bash
# List local branches
git branch

# List all branches (including remote)
git branch -a

# List branches with last commit info
git branch -v

# List merged branches
git branch --merged develop

# List unmerged branches
git branch --no-merged develop
```

### Switching Branches

```bash
# Switch to existing branch
git checkout develop
# Or newer syntax
git switch develop

# Switch and create if doesn't exist
git checkout -b feature/new-feature
git switch -c feature/new-feature
```

### Renaming Branches

```bash
# Rename current branch
git branch -m new-name

# Rename specific branch
git branch -m old-name new-name

# Update remote after rename
git push origin -u new-name
git push origin --delete old-name
```

### Deleting Branches

```bash
# Delete local branch (safe - won't delete unmerged)
git branch -d feature/completed-feature

# Force delete local branch
git branch -D feature/abandoned-feature

# Delete remote branch
git push origin --delete feature/completed-feature
```

### Tracking Remote Branches

```bash
# Set upstream for current branch
git branch -u origin/feature/my-feature

# Push and set upstream
git push -u origin feature/my-feature

# View tracking info
git branch -vv
```

---

## Stash Operations

### Basic Stash

```bash
# Stash current changes
git stash

# Stash with descriptive message
git stash push -m "WIP: vision tool implementation"

# Stash including untracked files
git stash push -u -m "WIP: includes new files"

# Stash including ignored files
git stash push -a -m "WIP: includes everything"
```

### Viewing Stashes

```bash
# List all stashes
git stash list

# Show stash contents
git stash show

# Show stash contents with diff
git stash show -p

# Show specific stash
git stash show stash@{2} -p
```

### Applying Stashes

```bash
# Apply most recent stash (keeps stash)
git stash apply

# Apply and remove most recent stash
git stash pop

# Apply specific stash
git stash apply stash@{2}

# Apply to different branch
git checkout other-branch
git stash apply
```

### Managing Stashes

```bash
# Drop most recent stash
git stash drop

# Drop specific stash
git stash drop stash@{2}

# Clear all stashes
git stash clear

# Create branch from stash
git stash branch feature/from-stash stash@{0}
```

---

## Rebase vs Merge

### When to Use Each

| Scenario | Use | Command |
|----------|-----|---------|
| Updating feature branch with develop | Rebase | `git rebase develop` |
| Completing feature PR | Merge (squash) | `git merge --squash` |
| Merging release to main | Merge (no-ff) | `git merge --no-ff` |
| Public/shared branches | Merge | `git merge` |

### Rebase Operations

```bash
# Rebase current branch onto develop
git rebase develop

# Interactive rebase (edit, squash, reorder commits)
git rebase -i HEAD~5

# Rebase onto remote
git fetch origin
git rebase origin/develop

# Continue after resolving conflicts
git rebase --continue

# Abort rebase
git rebase --abort

# Skip problematic commit
git rebase --skip
```

### Merge Operations

```bash
# Standard merge (creates merge commit)
git merge feature/my-feature

# Fast-forward merge (if possible)
git merge --ff feature/my-feature

# No fast-forward (always create merge commit)
git merge --no-ff feature/my-feature

# Squash merge (combine all commits)
git merge --squash feature/my-feature
git commit -m "feat: add my feature"

# Abort merge
git merge --abort
```

### Interactive Rebase Commands

When using `git rebase -i`, you can:

| Command | Short | Description |
|---------|-------|-------------|
| pick | p | Use commit as-is |
| reword | r | Edit commit message |
| edit | e | Stop to amend commit |
| squash | s | Combine with previous commit |
| fixup | f | Combine, discard message |
| drop | d | Remove commit |
| reorder | - | Change line order |

Example workflow:
```bash
# Squash last 3 commits into one
git rebase -i HEAD~3

# In editor, change:
# pick abc1234 First commit
# squash def5678 Second commit
# squash ghi9012 Third commit
```

---

## Conflict Resolution

### Identifying Conflicts

```bash
# See files with conflicts
git status

# See conflict markers in file
cat conflicted-file.py

# Use merge tool
git mergetool
```

### Resolving Conflicts

```bash
# Edit conflicted file to resolve
vim conflicted-file.py

# After editing, mark as resolved
git add conflicted-file.py

# Continue the operation
git rebase --continue
# or
git merge --continue
```

### Conflict Markers

In conflicted files, you'll see:
```
<<<<<<< HEAD
Your current changes
=======
Incoming changes
>>>>>>> feature/other-branch
```

Edit to keep desired changes and remove markers.

### Using Theirs/Ours

```bash
# During merge - accept all incoming changes
git checkout --theirs conflicted-file.py

# During merge - keep all current changes
git checkout --ours conflicted-file.py

# During rebase (reversed!)
# Accept incoming (the branch you're rebasing onto)
git checkout --ours conflicted-file.py

# Keep your changes
git checkout --theirs conflicted-file.py
```

---

## History and Inspection

### Viewing History

```bash
# Basic log
git log

# One line per commit
git log --oneline

# With graph
git log --oneline --graph --all

# Limited to last N commits
git log -10

# Filter by author
git log --author="John"

# Filter by date
git log --since="2025-01-01" --until="2025-02-01"

# Filter by file
git log -- services/skill_service.py

# Filter by message
git log --grep="feat(tools)"

# Show what changed
git log -p

# Show stats
git log --stat
```

### Comparing Changes

```bash
# Working directory vs staging
git diff

# Staging vs last commit
git diff --staged

# Compare branches
git diff develop..feature/my-feature

# Compare specific file between branches
git diff develop..feature/my-feature -- services/tool.py

# Compare commits
git diff abc1234..def5678

# Show changes in a commit
git show abc1234
```

### Finding Commits

```bash
# Find commit that introduced a bug
git bisect start
git bisect bad          # Current commit is bad
git bisect good v0.1.0  # v0.1.0 was good
# Test each commit, mark good/bad until found
git bisect reset

# Find who changed a line
git blame services/skill_service.py

# Find commit containing specific text
git log -S "searchTerm" --oneline

# Find commit with regex in diff
git log -G "pattern.*regex" --oneline
```

---

## Cleanup Commands

### Removing Untracked Files

```bash
# See what would be deleted (dry run)
git clean -n

# Remove untracked files
git clean -f

# Remove untracked files and directories
git clean -fd

# Remove ignored files too
git clean -fdx

# Interactive clean
git clean -i
```

### Resetting Changes

```bash
# Unstage file (keep changes)
git reset HEAD file.py
# Or newer syntax
git restore --staged file.py

# Discard changes in working directory
git checkout -- file.py
# Or newer syntax
git restore file.py

# Reset to previous commit (keep changes staged)
git reset --soft HEAD~1

# Reset to previous commit (keep changes unstaged)
git reset HEAD~1
git reset --mixed HEAD~1

# Reset to previous commit (discard all changes)
git reset --hard HEAD~1

# Reset to match remote exactly
git fetch origin
git reset --hard origin/develop
```

### Pruning and Garbage Collection

```bash
# Remove stale remote-tracking branches
git fetch --prune

# Or prune without fetching
git remote prune origin

# Run garbage collection
git gc

# Aggressive garbage collection
git gc --aggressive

# Prune unreachable objects
git prune

# Verify repository integrity
git fsck
```

### Removing Files from History

```bash
# Remove file from entire history (DANGEROUS)
git filter-branch --force --index-filter \
  'git rm --cached --ignore-unmatch secrets.env' \
  --prune-empty --tag-name-filter cat -- --all

# Using BFG (faster alternative)
bfg --delete-files secrets.env
git reflog expire --expire=now --all
git gc --prune=now --aggressive
```

---

## Advanced Operations

### Cherry-Pick

```bash
# Apply specific commit to current branch
git cherry-pick abc1234

# Cherry-pick without committing
git cherry-pick --no-commit abc1234

# Cherry-pick range of commits
git cherry-pick abc1234..def5678

# Continue after resolving conflicts
git cherry-pick --continue

# Abort cherry-pick
git cherry-pick --abort
```

### Reflog (Recovery)

```bash
# View reflog
git reflog

# Recover deleted branch
git checkout -b recovered-branch abc1234

# Recover after bad reset
git reset --hard HEAD@{2}
```

### Worktrees (Multiple Working Directories)

```bash
# Add worktree for parallel work
git worktree add ../isA_MCP-hotfix hotfix/urgent-fix

# List worktrees
git worktree list

# Remove worktree
git worktree remove ../isA_MCP-hotfix

# Prune stale worktrees
git worktree prune
```

### Tags

```bash
# List tags
git tag

# Create lightweight tag
git tag v0.2.0

# Create annotated tag (recommended)
git tag -a v0.2.0 -m "Release v0.2.0"

# Tag specific commit
git tag -a v0.2.0 abc1234 -m "Release v0.2.0"

# Push single tag
git push origin v0.2.0

# Push all tags
git push origin --tags

# Delete local tag
git tag -d v0.2.0

# Delete remote tag
git push origin --delete v0.2.0
```

---

## Useful Aliases

Add these to your `~/.gitconfig`:

```ini
[alias]
    # Short status
    st = status -sb

    # Pretty log
    lg = log --oneline --graph --all --decorate

    # Last commit
    last = log -1 HEAD --stat

    # Undo last commit (keep changes)
    undo = reset HEAD~1 --mixed

    # Amend without editing message
    amend = commit --amend --no-edit

    # List branches by last commit
    recent = branch --sort=-committerdate --format='%(committerdate:short) %(refname:short)'

    # Show what I did today
    today = log --since=midnight --author='Your Name' --oneline

    # Diff with word-level changes
    wdiff = diff --word-diff

    # Stash with message shortcut
    save = stash push -m
```

---

See also:
- [Git Workflow](./git-workflow.md)
- [Release Process](./release-process.md)
- [Contributing Guidelines](../../CONTRIBUTING.md)
