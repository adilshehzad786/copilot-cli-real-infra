# Security

## This repository contains intentionally vulnerable code

Everything under [`lab/`](lab/) is a teaching fixture for a conference talk. It is
deliberately broken, and a security scanner is *supposed* to flag it. Nothing here
is deployed, and none of it should be copied into a real project.

The deliberate defects:

| File | Defect | Why it is there |
|---|---|---|
| `lab/terraform/main.tf` | `google_storage_bucket_iam_member` granting `roles/storage.objectViewer` to `allUsers` | The public exposure the agent is asked to find in Demo 2 |
| `lab/terraform/main.tf` | No `uniform_bucket_level_access`, no `public_access_prevention`, `force_destroy = true` | The rest of the hardening exercise. Uniform access alone would leave the public grant in place — that is the lesson |
| `lab/.github/workflows/ci.yml` | Missing `id-token: write` | The failure Demo 1 diagnoses |
| `.github/workflows/ci.yml` | The same missing permission, at the repository root | The live exhibit. It fails by design at the auth step, before anything reaches Google Cloud; the repository variables it references hold intentionally fake, well-formed values |
| `lab/.github/workflows/ci.yml` | A federated cloud identity held while running Terraform from a pull request | Named out loud from the stage. It is the same borrowed-access story as the agent's, so fixing it quietly would remove the point |
| `lab/evidence/ci-failure.log` | A planted instruction in contributor build output | Demonstrates prompt injection through content the agent reads. Demo 1 runs with no shell, so it is provably inert |
| `lab/.env` (created during setup) | A fake secret | Gives the denied-path policy a real file to deny. Contains `DEMO_SENTINEL=synthetic-not-a-secret` |

The expected fixes are in [docs/answers.md](docs/answers.md).

`lab/stubs/` contains twelve symlinks to a four-line shell script that prints a
marker and exits. No command in this lab can reach a cloud API. (`gh` is
deliberately not stubbed: Copilot CLI borrows the GitHub CLI's login to
authenticate, so shadowing it breaks the session itself.)

## Reporting a real vulnerability

If you find something genuinely wrong — a command in the documentation that would
damage a reader's machine, a policy file that grants more than it claims, or
anything in the deck that misstates a product's security behaviour — open an issue.

## Running the lab safely

Use a disposable VM or container with no cloud credentials and no attached cloud
identity. The lab's `PATH` stubs and copied directory are accident prevention, not
an isolation boundary: your OS user, home directory and real credentials are all
still present. The sandbox policy denies a list of paths *someone thought of*,
which is precisely the pattern the talk criticises.

Do not put a real secret in `.env`. Do not point the lab at a real repository.
