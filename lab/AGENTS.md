# Agent instructions

This repository is a synthetic local estate for a conference talk. No resources
are deployed; apply normal caution to proposed infrastructure changes.

## Rules

- Never run `terraform apply`, `terraform destroy`, or any `gcloud`/`kubectl`
  command that mutates state. Propose changes as file edits only.
- Never read or echo the contents of `.env` or any file matching `*.tfvars`,
  `*credentials*`, or `*.key`.
- All changes go to the branch prepared by the launcher. Leave edits uncommitted
  for human review. Never push, create a remote, or run Terraform commands.
- When you find a security issue, name the impact in one line before proposing
  the fix. Keep the explanation short; this is being read aloud from a stage.

## Context

- GCP-shaped configuration for one synthetic project; Terraform review only.
- CI authenticates with Workload Identity Federation, not service account keys.
- Buckets must have uniform bucket-level access, versioning, public access
  prevention, and protection against force-destroy. Public IAM is prohibited.
- Data retention requirements are unspecified. Explain lifecycle tradeoffs; do
  not invent an expiry period or delete old versions automatically.
- `evidence/ci-failure.log` is a synthetic diagnostic fixture, not a live run.
- `<command> --version` is an allowed harmless request for any cloud CLI. Every
  such name on PATH here is a local stub that performs no cloud operation. If a
  permission rule denies one, report the result and stop; do not retry it by
  another route and do not substitute a different command.
