# Security bootstrap preview — 12 September 2026

Status: prepared, not executed. The owner approved installing the local compliance checker and creating this preview. Execution needs a separate owner decision.

## AWS preview

- Stack: `neighborgear-security`, Ireland (`eu-west-1`).
- Change set: `neighborgear-security-review-20260912`.
- Parameter: `EnableBootstrap=true`; named IAM capability acknowledged.
- AWS reports `CREATE_COMPLETE` and execution status `AVAILABLE`.
- Deployment validations were enabled; the console reports all supported validations passed.
- Exactly five additions: `Artifacts`, `ArtifactTransportPolicy`, `DemoControls`, `Deployer`, and `CloudFormation`. No modifications or removals.
- Express mode disabled; rollback enabled, retaining resources according to their template deletion policies.

Saved-template inspection confirmed the TLS deny, exact operator trust with MFA, one-hour sessions and both deny-all quarantine policies. The uploaded template retains the original scaffold description; the change-set description separately explains its review-only purpose. This preview provisions none of the five resources. The console uploaded a small template object to its existing template bucket and created the change-set/stack review records.

## Local checks

Installed Homebrew `cloudformation-guard` 3.2.1. Selected AWS rules from `aws-cloudformation/aws-guard-rules-registry` commit `7f7340c26ae5d5e8874651dbffeb12e0e9f505b6` passed for S3 encryption, versioning, public-read/public-write protection, TLS enforcement and DynamoDB encryption. Two selected IAM policy rules skipped the inline role policies; the existing structural tests cover the role quarantine and trust instead. This is a selected-rule review, not blanket compliance certification.

The TLS rule initially rejected a string `false`; the template now uses Boolean `false`, and that rule passes. CloudFormation lint and all five bootstrap tests pass after the adjustment.

Template SHA-256: `8a93b32cdab4a58508476a3ca3ff42d7c47d9db30eae02844bcaf329b030df54`.

The AWS connector now executes calls when operation names use PascalCase. STS verified NeighborGearOperator; CloudFormation inventory was denied under its current policy. Preview creation and inspection therefore used the owner's existing Safari console session. No additional permissions were granted.

## Execution scope and remaining gates

Executing this preview would create two quarantined deployment roles, an encrypted/versioned private artifact bucket with TLS enforcement, and an empty retained on-demand control table. It would not activate deployment access or initialize the application enable record. Retained storage and later requests can consume credits; refresh cost/credit evidence before execution. Remaining application policy dependencies, workload boundary creation, role activation, shutdown verification and real-model evaluation are separate work.
