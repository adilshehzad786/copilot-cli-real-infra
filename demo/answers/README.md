# Review guide (excluded from the generated estate)

## Beat A — the CI diagnosis

The workflow requests no OIDC token permission, so the `auth` step never gets the
variables it needs. Add `id-token: write`.

Job-level `permissions` **replaces** the workflow-level block rather than merging
with it, so both scopes must be listed or `checkout` loses `contents: read`:

```yaml
jobs:
  plan:
    permissions:
      contents: read
      id-token: write
```

Granting it at the workflow level instead is equally valid here, because there is
only one job. Say which one you mean.

Two qualifications worth keeping ready, because a sharp audience raises them:

- **This holds for a same-repository branch pull request.** On a pull request from
  a fork, GitHub forces `GITHUB_TOKEN` read-only and the `id-token` scope cannot be
  granted at all. That case needs a `workflow_run` or an environment-gated job.
- **The permission only permits requesting a token.** The provider trust
  conditions, the claim mapping, the impersonation grant and the resource IAM all
  still have to be right. This log takes you to the first failure, not to a
  working pipeline. See the [auth action's setup](https://github.com/google-github-actions/auth#usage).

If someone asks why a stateless plan needs a service account at all: the Google
provider resolves Application Default Credentials at provider-configure time,
before any resource is evaluated, so `terraform plan` fails with "could not find
default credentials" even though this configuration makes no API call. Verified
against hashicorp/google 6.50.0 and 8.2.0. GitHub-hosted runners have no GCE
metadata, so on a real runner the auth step is load-bearing.

One more defect in the fixture, deliberately left in and worth naming from the
stage before someone names it for you: the job holds a federated cloud identity
while running Terraform that came from the pull request. That is handing a
credential to untrusted input — the same borrowed-access story as the agent's. A
real pipeline splits it into an unauthenticated `validate` on `pull_request` and
an authenticated `plan` behind an environment gate. The fixture keeps one job so
the demo stays legible. These notes stay here rather than in the workflow because
the estate's copy of that file is what the model reads.

## Beat B — the bucket answer

The answer should:

- Remove the `allUsers` IAM member **and** set `public_access_prevention = "enforced"`.
  Uniform access alone does not remove a public IAM grant — this is the point of
  the beat.
- Enable `uniform_bucket_level_access` and versioning.
- Set `force_destroy = false` so Terraform cannot delete a populated bucket.
- Explain that versioning increases storage cost and needs a deliberate retention
  policy. Do not invent a lifecycle rule or an expiry period.

`google_storage_bucket_iam_member` is non-authoritative, so deleting the block
removes exactly that one binding and nothing else. With public access prevention
enforced, the binding cannot be re-added.

Versioning and soft delete are different controls. An overwrite without versioning
is not necessarily unrecoverable: [Cloud Storage soft delete](https://docs.cloud.google.com/storage/docs/soft-delete)
retains overwritten and deleted objects, with a seven-day default retention period.

`hardened-main.tf.example` is an expected review answer, not a migration plan.
Uniform access breaks workloads that rely on object ACLs, and public access
prevention breaks public readers. A real change needs a locked provider version, a
reviewed saved plan, and a workload and retention review before CI applies it with
its separate deployment identity. These local edits mutate nothing and need no
state rollback.

## Checking it locally

```bash
terraform fmt -check demo/terraform
terraform -chdir=demo/terraform init -backend=false && terraform -chdir=demo/terraform validate
```

`validate` needs the provider downloaded, which is a deliberate network step the
launchers never take. Neither formatting nor validation establishes IAM
correctness. See the [bucket resource documentation](https://registry.terraform.io/providers/hashicorp/google/latest/docs/resources/storage_bucket).
