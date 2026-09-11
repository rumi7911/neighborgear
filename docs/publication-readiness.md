# Publication readiness — 11 September 2026

Local preparation only. No GitHub repository was created, no files were uploaded, and no AWS resources were enabled.

## Completed review

- MIT license, reproducible setup instructions, pinned lockfiles, architecture diagrams, submission draft and video script are present.
- The GitHub verification workflow uses simulator mode and explicitly disables the credits gate. It runs Python tests, infrastructure lint, frontend tests and a production build. It has not yet run on GitHub.
- Removed the developer's absolute home-directory paths from three policy-review/setup documents. Run their commands from the repository root.
- Added `.env.*` and `.DS_Store` ignore rules while preserving `.env.example`. Checked that root and nested environment variants are ignored and the example remains publishable.
- A targeted text scan found no remaining matches for AWS access-key ID patterns, private-key headers, the known owner account ID/email or developer home path in the scanned non-generated files. This limited scan is not a comprehensive secret audit and cannot prove the absence of credentials.
- Existing SQLite databases, dependency directories, build output and evaluation JSON are ignored.

## Before publishing

1. Confirm the destination GitHub account and repository name, and approve public publication.
2. Review the exact staged file list and diff, including the design image, before the first commit. Do not include billing screenshots, private operator evidence, credentials or actual recipient data.
3. Perform a dedicated secret scan over the final publication contents. The repository currently has no commits or remote; future history also needs checking if that changes.
4. Publish the reviewed source and verify the hosted CI result. Local test evidence is recorded separately in `local-rehearsal-2026-09-10.md`.
5. Keep deployment and live-model claims conditional until measured. Add verified repository, demo, video and article URLs only after those artifacts exist.

## AWS status

The last verified quota-request state was Pending on 10 September. Safari was locked during the 11 September check, so no fresh approval status was obtained. Publication preparation does not depend on quota approval.
