# Code signing policy

Free code signing provided by SignPath.io, certificate by SignPath Foundation.

This policy describes how Windows binaries of RestoreAppStore are signed after the SignPath Foundation application is approved. Until then, published builds are unsigned and Windows SmartScreen may show a warning.

## What is signed

Only binaries built from this public repository by GitHub Actions on GitHub-hosted runners are submitted for signing. The workflow is `.github/workflows/windows-build.yml`. Local or manual builds are not signed with the SignPath certificate.

The signed files are:

- the portable `RestoreAppStore-win-x64.exe`
- `RestoreAppStore/RestoreAppStore.exe` inside `RestoreAppStore-win-x64.zip`

Third-party open-source binaries that are shipped beside the app, including `ipatool-cpp.exe`, are not signed with this certificate.

## Team roles

The project is maintained by a single owner.

- Committers and reviewers: [freeon1989](https://github.com/freeon1989)
- Approvers of each signing request: [freeon1989](https://github.com/freeon1989), the repository owner

Each release signing request must be approved in SignPath before the signed files are published.

## Privacy

See the [privacy policy](privacy.md). SignPath's own policy is at [signpath.org/privacy-policy](https://signpath.org/privacy-policy).

## Further setup

Repository variables and the API token needed after approval are described in [SIGNPATH.md](SIGNPATH.md). They are not stored in this repository.
