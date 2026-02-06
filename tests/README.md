# isA MCP Testing Guide

**The authoritative reference for all testing in the isA MCP service.**

---

## Quick Navigation

| Section | Purpose |
|---------|---------|
| [Test Pyramid](#test-pyramid) | Which test layer to use |
| [Directory Structure](#directory-structure) | Where files go |
| [Running Tests](#running-tests) | How to execute tests |
| [Infrastructure](#infrastructure) | What you need running |

---

## Quick Start

### Prerequisites

| Test Type | Environment | Needs K8s | Needs Port-Forward |
|---------|------|:-------:|:----------------:|
| **Unit** | Local (dev) | No | No |
| **Component** | Local (dev) | No | No |
| **Integration** | K8s (test) | Yes | Yes (direct) |
| **API** | K8s (test) | Yes | Yes (direct) |
| **Smoke** | K8s (test) | Yes | Yes (gateway) |

### Environment 1: Local Development (Unit + Component)

```bash
# 1. Create and activate virtual environment
uv venv .venv
source .venv/bin/activate

# 2. Install dev dependencies
uv pip install -r deployment/requirements/dev.txt

# 3. Load dev environment
source deployment/environments/dev.env

# 4. Run tests - NO infrastructure needed!
pytest tests/unit -v
pytest tests/component -v
```

### Environment 2: K8s Testing (Integration + API + Smoke)

```bash
# 1. Verify K8s context
kubectl config current-context  # Should be: kind-isa-cloud-local

# 2. Port-forward infrastructure
kubectl port-forward -n isa-cloud-staging svc/isa-postgres-grpc 50061:50061 &
kubectl port-forward -n isa-cloud-staging svc/qdrant 6333:6333 &
kubectl port-forward -n isa-cloud-staging svc/redis 6379:6379 &

# 3. Port-forward MCP service (for integration/API tests)
kubectl port-forward -n isa-cloud-staging svc/mcp 8300:8300 &

# 4. Port-forward gateway (for smoke tests)
kubectl port-forward -n isa-cloud-staging svc/apisix-gateway 8000:8000 &

# 5. Load test environment
source deployment/environments/test.env

# 6. Run tests
pytest tests/integration -v       # Direct service access
pytest tests/api -v               # Direct service access
./tests/smoke/mcp/smoke_test.sh   # Via APISIX gateway
```

---

## Test Pyramid

```
                    ┌─────────────────┐
                    │   Smoke Tests   │  ← Via Gateway (APISIX)
                    │   (tests/smoke) │
                    └────────┬────────┘
                    ┌────────┴────────┐
                    │   API Tests     │  ← Direct Service Access
                    │   (tests/api)   │
                    └────────┬────────┘
               ┌─────────────┴─────────────┐
               │   Integration Tests       │  ← Real DB, Mocked External
               │   (tests/integration)     │
               └─────────────┬─────────────┘
          ┌──────────────────┴──────────────────┐
          │       Component Tests               │  ← Mocked Everything
          │       (tests/component)             │
          └──────────────────┬──────────────────┘
     ┌───────────────────────┴───────────────────────┐
     │              Unit Tests                       │  ← Pure Logic
     │              (tests/unit)                     │
     └───────────────────────────────────────────────┘
```

### Test Layers Explained

| Layer | Folder | What It Tests | Mocking |
|-------|--------|---------------|---------|
| **Unit** | `tests/unit/` | Pure business logic, no I/O | Everything mocked |
| **Component** | `tests/component/` | Service interactions | External APIs mocked |
| **Integration** | `tests/integration/` | DB operations | External APIs mocked |
| **API** | `tests/api/` | HTTP endpoints | Real service, external mocked |
| **Smoke** | `tests/smoke/` | End-to-end via gateway | Nothing mocked |

---

## Directory Structure

```
tests/
├── README.md                    # This file
├── conftest.py                  # Global fixtures
├── fixtures/                    # Shared test fixtures
│   └── ...
├── contracts/                   # CDD contracts per service
│   ├── progress/
│   ├── prompt/
│   ├── resource/
│   ├── search/
│   ├── skill/
│   ├── sync/
│   ├── tool/
│   └── vector/
├── unit/                        # Layer 1: Unit tests
│   ├── golden/                  # Characterization tests
│   └── tdd/                     # New feature tests
├── component/                   # Layer 2: Component tests
│   ├── golden/
│   └── tdd/
├── integration/                 # Layer 3: Integration tests
│   ├── golden/
│   └── tdd/
├── api/                         # Layer 4: API tests
│   ├── golden/
│   └── tdd/
├── smoke/                       # Layer 5: Smoke tests
│   └── mcp/
├── eval/                        # Evaluation tests (ML/AI)
│   └── ...
└── test_data/                   # Test data files
    ├── documents/
    ├── prompts/
    └── tools/
```

### Golden vs TDD Folders

| Folder | Purpose | When to Use |
|--------|---------|-------------|
| `golden/` | Characterization tests | Capture existing behavior |
| `tdd/` | Test-driven tests | Write new features |

---

## Running Tests

### By Layer

```bash
# Unit tests (fast, no infra)
pytest tests/unit -v

# Component tests (mocked, no infra)
pytest tests/component -v

# Integration tests (needs port-forward)
pytest tests/integration -v

# API tests (needs port-forward)
pytest tests/api -v

# Smoke tests (needs gateway)
./tests/smoke/mcp/smoke_test.sh
```

### By Marker

```bash
# Run only fast tests
pytest -m "not slow" -v

# Run only golden tests
pytest -m golden -v

# Run only TDD tests
pytest -m tdd -v
```

### With Coverage

```bash
pytest tests/unit tests/component --cov=services --cov-report=html
```

---

## Infrastructure

### Required Services

| Service | Port | Required For |
|---------|------|--------------|
| PostgreSQL (gRPC) | 50061 | Integration, API |
| Qdrant | 6333 | Integration, API |
| Redis (gRPC) | 50063 | Integration, API |
| MCP Service | 8300 | Integration, API |
| APISIX Gateway | 8000 | Smoke |

### Port-Forward Commands

```bash
# Infrastructure
kubectl port-forward -n isa-cloud-staging svc/isa-postgres-grpc 50061:50061 &
kubectl port-forward -n isa-cloud-staging svc/qdrant 6333:6333 &
kubectl port-forward -n isa-cloud-staging svc/redis 6379:6379 &

# MCP Service
kubectl port-forward -n isa-cloud-staging svc/mcp 8300:8300 &

# Gateway
kubectl port-forward -n isa-cloud-staging svc/apisix-gateway 8000:8000 &
```

---

## CDD Contracts

Each service has contracts in `tests/contracts/{service}/`:

| File | Layer | Purpose |
|------|-------|---------|
| `data_contract.py` | L4 | Pydantic schemas, TestDataFactory |
| `logic_contract.md` | L5 | Business rules, state machines |
| `system_contract.md` | L6 | Implementation patterns |

See `TDD_ARCHITECTURE.md` for detailed contract specifications.
