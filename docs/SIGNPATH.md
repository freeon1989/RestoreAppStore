# SignPath setup (after approval)

This file is a checklist for the repository owner. Do not put API tokens, organization IDs or personal addresses in the repository.

## Once SignPath Foundation approves the project

1. In the SignPath dashboard, install the SignPath GitHub App on `freeon1989/RestoreAppStore`.
2. Create a project linked to this repository. A reasonable slug is `restoreappstore`.
3. Create a signing policy, for example `release-signing`, that requires an approver for each request.
4. Create an artifact configuration from [signpath/artifact-configuration.xml](signpath/artifact-configuration.xml). A reasonable slug is `windows-release`.
5. Create an API token with permission to submit signing requests (not to approve them).

## GitHub repository settings

Under Settings → Secrets and variables → Actions:

| Kind | Name | Value |
| --- | --- | --- |
| Secret | `SIGNPATH_API_TOKEN` | the API token from SignPath |
| Variable | `SIGNPATH_ORGANIZATION_ID` | organization id from the SignPath URL or settings |
| Variable | `SIGNPATH_PROJECT_SLUG` | e.g. `restoreappstore` |
| Variable | `SIGNPATH_SIGNING_POLICY_SLUG` | e.g. `release-signing` |
| Variable | `SIGNPATH_ARTIFACT_CONFIGURATION_SLUG` | e.g. `windows-release` |

The Windows workflow already contains the `signpath/github-action-submit-signing-request` step. It runs only when `SIGNPATH_ORGANIZATION_ID` is set, and only on a `v*` tag or a manual `workflow_dispatch` with `sign` enabled.

The approver must confirm each request in SignPath. The job waits for that confirmation. After it finishes, download the `RestoreAppStore-windows-signed` artifact, recompute SHA-256 if needed, and attach the signed files to the GitHub Release.
