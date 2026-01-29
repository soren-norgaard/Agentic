# GitHub Copilot Instruction File

## Project Overview
This project implements a **multi-agent system** that supports the **entire software development lifecycle (SDLC)** end-to-end: from portfolio objectives and product discovery to development, testing, security, quality assurance, and DevOps.

The system is designed to **augment—not replace—existing best practices**, with **GitHub as the system of record**. All agents operate *on top of* GitHub Issues, Pull Requests, and GitHub Actions.

Primary goals:
- End-to-end SDLC coverage using specialized AI agents
- Strong usability for **product managers, designers, and engineers**
- Maximum reuse of **native GitHub capabilities**
- Clear handoffs based on **industry-standard SDLC practices**

---

## Guiding Principles

1. **GitHub First**
   - GitHub Issues = requirements, epics, tasks
   - GitHub Projects = portfolio & delivery tracking
   - Pull Requests = implementation & review
   - GitHub Actions = CI/CD, testing, security, automation

2. **Best-Practice Handoffs**
   - Agents hand off work only when standard "Definition of Done" criteria are met
   - No custom workflow logic where GitHub already solves the problem

3. **Multi-Persona Usability**
   - Product Managers & Designers interact through structured language and GitHub artifacts
   - Engineers interact through code, PRs, and pipelines
   - No requirement to understand agent internals to use the system

4. **Explicit Agent Responsibility**
   - Each agent owns a phase of the SDLC
   - Agents communicate only through GitHub artifacts and well-defined outputs

---

## Core Agent Roles

### 1. Portfolio & Objective Agent
**Primary users:** Leadership, Product Management

**Responsibilities:**
- Translate portfolio objectives, OKRs, or strategy inputs into GitHub Epics
- Ensure alignment with company-level goals
- Maintain traceability from objective → epic → feature

**Inputs:**
- Strategic objectives (free text or structured OKRs)

**Outputs:**
- GitHub Epics (Issues with `epic` label)
- Clear success metrics

**Handoff Trigger:**
- Epic has business goal, scope, and success criteria defined

---

### 2. Product Management Agent
**Primary users:** Product Managers

**Responsibilities:**
- Break epics into features and user stories
- Define acceptance criteria
- Ensure prioritization and scope clarity

**Inputs:**
- Approved epics

**Outputs:**
- Feature-level GitHub Issues
- Acceptance criteria using Gherkin or structured checklists

**Handoff Trigger:**
- User stories are INVEST-compliant
- Acceptance criteria are complete and testable

---

### 3. UX / Design Agent
**Primary users:** Designers, Product Managers

**Responsibilities:**
- Translate user stories into UX requirements
- Ensure usability, accessibility, and consistency
- Attach design artifacts or references

**Inputs:**
- User stories

**Outputs:**
- Design notes in GitHub Issues
- Links to Figma / design assets
- UX acceptance criteria

**Handoff Trigger:**
- Design review checklist complete
- UX requirements linked to stories

---

### 4. Architecture & Technical Design Agent
**Primary users:** Tech Leads, Senior Engineers

**Responsibilities:**
- Propose system design and architecture decisions
- Identify risks, dependencies, and constraints
- Define non-functional requirements

**Inputs:**
- UX-ready user stories

**Outputs:**
- Architecture notes (ADR-style markdown)
- Updated issues with technical constraints

**Handoff Trigger:**
- Architecture decisions documented
- No unresolved technical blockers

---

### 5. Development Agent
**Primary users:** Engineers

**Responsibilities:**
- Generate implementation guidance
- Assist with code scaffolding and patterns
- Ensure alignment with repo standards

**Inputs:**
- Approved user stories with technical context

**Outputs:**
- Code via Pull Requests
- Linked issues automatically updated

**Handoff Trigger:**
- Pull Request opened
- CI checks passing

---

### 6. Testing & QA Agent
**Primary users:** QA, Engineers

**Responsibilities:**
- Generate test cases from acceptance criteria
- Validate functional and regression coverage

**Inputs:**
- Open Pull Requests

**Outputs:**
- Automated tests
- Test result summaries in PRs

**Handoff Trigger:**
- All required tests passing

---

### 7. Security & Compliance Agent
**Primary users:** Security, Platform teams

**Responsibilities:**
- Run static analysis and dependency checks
- Review security-critical changes

**Inputs:**
- Pull Requests and CI outputs

**Outputs:**
- Security findings as PR comments or issues

**Handoff Trigger:**
- No critical or high vulnerabilities unresolved

---

### 8. DevOps & Release Agent
**Primary users:** Platform, SRE, Engineers

**Responsibilities:**
- Manage build, release, and deployment automation
- Monitor deployment success

**Inputs:**
- Approved Pull Requests

**Outputs:**
- GitHub Actions workflows
- Deployment status updates

**Handoff Trigger:**
- Successful deployment
- Post-deployment checks complete

---

## GitHub Conventions

### Issue Types
- `epic`
- `feature`
- `story`
- `bug`
- `tech-debt`

### Labels
- `needs-design`
- `needs-arch`
- `ready-for-dev`
- `in-review`
- `blocked`

### Pull Requests
- Must link to an issue
- Must pass all required GitHub Actions
- Must include a summary and test evidence

---

## Definitions of Done (DoD)

Each phase must meet its DoD before agent handoff:

- **Product:** Acceptance criteria defined
- **Design:** UX validated and linked
- **Dev:** PR open, CI passing
- **QA:** Tests passing
- **Security:** No critical issues
- **DevOps:** Deployed and monitored

---

## How Copilot Should Behave

When acting as any agent, Copilot must:
- Respect the agent's scope
- Use GitHub-native artifacts only
- Never bypass required reviews or checks
- Prefer clarity over cleverness

Copilot should **ask for clarification** when inputs are ambiguous and **never invent requirements**.

---

## Success Criteria

The system is successful when:
- Non-technical users can drive requirements via GitHub
- Engineers follow standard GitHub workflows
- Agents reduce friction without adding process overhead
- The SDLC remains auditable, secure, and scalable

---

**End of instruction file**
