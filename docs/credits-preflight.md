# Credits and deployment gate

## Quota request checkpoint — 10 September 2026

With explicit owner approval conditional on no charges or plan upgrade, submitted an Ireland Lambda Concurrent executions quota request for 1,000 through the root console. The console required a requested value at least equal to the default 1,000; it would not accept the application's calculated minimum of 104. Request history verified **Pending**, requested value 1,000, dated 10 September. This is not approval or an applied quota increase. No plan upgrade, application resource deployment, model invocation or changes to the template's 2 + 1 + 1 reserved concurrency limits occurred. Quota compatibility remains blocked until approval and a fresh applied-limit check. Earlier statements that no quota request occurred are historical.

Read-only preflight completed, 10 September: owner-approved NeighborGearPreflightReadOnly was attached and its exact saved contents verified in IAM. The non-root plugin successfully listed the user's one OAuth managed policy, one preflight inline policy and zero groups, and read Ireland Lambda settings: concurrency 10, unreserved 10, zero functions. This supersedes the missing-read-permission blocker below. Quota compatibility remains unresolved; no quota increase or deployment occurred. Billing balance and service eligibility were not refreshed by these checks.

Latest access checkpoint, 10 September: the OAuth sign-in policy was attached with owner approval, MFA remains enabled, and STS verified the reconnected plugin as NeighborGearOperator (not root). The next preflight's self-policy/group listings and Ireland Lambda GetAccountSettings were all denied for missing identity permissions. Reauthentication is no longer the blocker; scoped read access and subsequent deployment authorization remain pending. No quota increase, deployment or model invocation occurred.

Status: **credit balance and core service coverage verified; application deployment and paid Bedrock evaluation remain disabled.** Only the previously approved monitoring budget and operator sign-in setup have been created in AWS.

## Access-policy checkpoint — 9 September 2026

Shutdown review checkpoint: application expiry, ten-attempt admission and the dry-run-first shutdown CLI are implemented and tested locally. The new [shutdown permission review](../infra/iam-review/shutdown-review.md) records an Autopilot 0.3.0 scan with broad-resource findings; its output is not approved for attachment. Owner maintenance access, actual cloud shutdown and the first UTC test window remain open. Historical account observations below are not a current balance or credential check.

User reports successful non-root IAM console login after MFA resynchronization. The 8 September plugin recheck succeeded but still returned root; the plugin must use a separately verified non-root session before deployment. Lambda concurrency remains 10 and is marked adjustable; no increase was requested. The existing 2 + 1 + 1 reservations require a documented minimum of 104 with the 100-unit unreserved pool, assuming no other reservations.

Review-only policies and source-policy scan findings are in [the access review](../infra/iam-review/README.md). No policy was attached. The fixed workload boundary, explicit workload roles, artifact-upload draft and named-resource provisioning component are prepared locally. The new owner scaffold is disabled and its deployment roles have deny-all quarantine. Full provisioning permissions and bootstrap activation are still unfinished; these drafts are not a deployment-ready bootstrap. Live IAM validation/simulation is still pending; current offline verification is reported in the task, not inferred from older test counts.

## Read-only verification — 7 September 2026

- API and Billing console: active Free plan, $100 remaining, $0 reported credit use. Credit expires 5 September 2027; the Free plan expires earlier, 5 March 2027. Billing estimates can lag.
- Applicable credit products explicitly include Bedrock, AgentCore, Lambda, API Gateway, DynamoDB, S3, SQS, CloudFront, CloudWatch and CloudFormation. Scheduler coverage still requires confirmation; the console lists CloudWatch Events rather than Scheduler by name.
- Nova Lite is authorized/available in eu-west-1; its EU profile is active. AgentCore listing is accessible, but create/invoke permissions and quotas remain untested.
- The connected identity was root during API verification. Root MFA is enabled and no root access keys are present. On 8 September, created `NeighborGearOperator` through the owner's signed-in Safari console with no policies, groups or access keys. The owner subsequently set its console password and MFA; Safari showed **Enabled with MFA**, one assigned MFA device, zero access keys and zero API keys. The user subsequently reported successful operator sign-in. Scoped deployment roles remain uncreated. Plugin reauthentication now works but returns root; Safari sign-in does not change the plugin identity.
- Lambda account concurrency in eu-west-1 is 10, with no functions deployed. The application's positive reserved concurrency settings need resolution before deployment. AWS's documented reservation rule leaves 100 units unreserved; do not assume this new account supports the current configuration or remove the limits silently.
- `infra/cost-controls.yaml` is prepared and locally tested, not deployed. The matching notification-only budget `NeighborGear-gross-account-spend` was instead created directly through the AWS Budgets API after the owner supplied the recipient; read-back verified HEALTHY status, five alert subscriptions and no actions. Avoid creating a duplicate through CloudFormation. IAM setup, quota resolution, Scheduler coverage, the application stop control and a detailed first-stage cost estimate remain gates.

See `docs/superpowers/plans/2026-09-07-aws-safe-first-deployment.md` for the execution checklist. Verification evidence containing account identifiers and billing details stays out of Git.

Source: [Lambda reserved concurrency](https://docs.aws.amazon.com/lambda/latest/dg/configuration-concurrency.html).

Before deployment, record evidence in a private operator document (do not commit account numbers, screenshots of billing or credentials):

1. The participant owns/controls the AWS account and can use Bedrock Nova Lite and AgentCore in the selected region.
2. Credits are actually issued to that account, with balance, expiry date and eligible services. A submitted credit request is not issued credit.
3. Estimate costs through the end of judging for Bedrock input/output, AgentCore active compute, API/Lambda invocations, DynamoDB reads/writes/storage, SQS, EventBridge, S3, CloudFront transfer and logs. Use the current AWS pricing pages and calculator; no price estimate here has been verified.
4. Set a conservative aggregate model-run allowance, per-run maximum tokens, API throttling, protected judge access and an expiry/disable date. Keep a substantial credit reserve rather than budgeting the entire award.
5. Configure billing alerts and a documented operator shutdown procedure. Alerts may be delayed and are **not a hard spending cap**. A credits-verification environment flag is an operator attestation, not a balance lookup or guarantee.
6. Recheck eligible services and balance immediately before enabling the model or deploying. Stop if coverage is uncertain. Do not fall back to personal spending.

Account setup, AWS Builder ID, the credit application and accepting terms require the participant. Credit requests in the approved plan close 11 September at 20:00 UK time; recheck the [official resources](https://agentsforhumans.devpost.com/resources) before applying. Never paste keys into chat or frontend environment variables.

Protected-demo limitations: sandbox tokens are bearer credentials, not staff identity verification. A shared judge creation key is appropriate only for this fictional hackathon sandbox. Production use would require real authorization, retention policy, operational controls and partner review.
