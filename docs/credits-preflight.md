# Credits and deployment gate

## Simulator activation review — 13 September 2026

Created the standard update change set `neighborgear-simulator-access-review-20260913` for the existing `neighborgear-security` stack in Ireland. CloudFormation reported `CREATE_COMPLETE` / `AVAILABLE`; all supported deployment validations passed. The exact diff contained two in-place IAM role policy changes and one MFA-gated operator assume-role policy, with no replacements, application resources or model runtime. After a separate action-time owner approval, the exact change set executed successfully and the security stack reached `UPDATE_COMPLETE`. Application deployment and model invocation remain disabled. See the [change-set review](../infra/iam-review/simulator-access-changeset-review.md).

## Security bootstrap checkpoint — 12 September 2026

Immediately before execution, a fresh owner Billing console check showed **$120.00 total and estimated promotional credit remaining, $0.00 used**, across two active credits expiring 5 September 2027. After an explicit action-time owner approval, the prevalidated `neighborgear-security-review-20260912` change set was executed in Ireland. Stack `neighborgear-security` reached `CREATE_COMPLETE`; all five resources completed: the private encrypted/versioned artifact bucket, its TLS-only policy, the retained on-demand control table, and two one-hour, deny-all-quarantined deployment roles.

The execution did not activate deployment access, initialize the application enable record, deploy application compute or invoke a model. A post-deployment AWS connector readback was denied across CloudFormation, IAM, S3 and DynamoDB because NeighborGearOperator remains intentionally narrow; the root console provided the stack/resource status evidence. Remaining policy assembly, workload boundary creation, role activation and application deployment are separate gates.

## Network change-set checkpoint — 12 September 2026

Created the review-only CloudFormation change set `neighborgear-network-review-20260912` for stack `neighborgear-network` in `eu-west-1`. Its captured inputs were `ApplicationStackName=neighborgear-demo`, `CreditsVerified=true` and `EnableNetwork=true`. CloudFormation reported `CREATE_COMPLETE` / `AVAILABLE`, and all supported deployment validations passed.

After a fresh explicit owner approval, executed exactly that seven-addition change set with rollback-all and deletion of newly created resources on failure. CloudFormation reached `CREATE_COMPLETE`: the HTTP API and default stage, private S3 web bucket and bucket policy, CloudFront distribution, origin access control and origin request policy all completed successfully. The five stack outputs were captured only in a gitignored local environment file; account-specific identifiers remain outside the public repository. No application compute, business data or model invocation has been deployed yet.

## Quota approval checkpoint — 11 September 2026

AWS Support reports the Ireland Lambda Concurrent executions request as fully approved at 1,000. A fresh root-console check of quota `L-B99A9384` in `eu-west-1` then verified **Applied account-level quota value: 1,000** and utilization of 0. The template's 2 + 1 + 1 reserved concurrency settings are therefore compatible with AWS's requirement to retain 100 unreserved executions, assuming a final pre-deployment check still shows no competing reservations. This clears the Lambda quota gate only; it does not authorize deployment, model invocation, permissions changes or personal spending. The private support case identifier and account evidence are deliberately excluded from this public repository.

## Fresh credit and cost checkpoint — 11 September 2026

A fresh Billing console check showed **$120.00 remaining, $0.00 used**, across two active promotional credits that expire 5 September 2027. The active Free Tier credit's product list includes Amazon Bedrock foundation models and the project's core serverless services. The AgentCore Runtime console is accessible in Ireland and shows zero runtime resources. No model or runtime was invoked during this check.

The proposed bounded evaluation is 20 live model runs: ten fixed local scenarios and ten protected cloud/demo runs. A deliberately conservative estimate assumes 13 model turns per run, 30,000 input tokens and 2,048 output tokens per turn, plus 50 one-minute AgentCore sessions at a continuous peak of 1 vCPU and 2 GB and a $1 contingency for logs, API, queue and storage. Using the published Nova Lite and AgentCore prices, that envelope is approximately **$1.69**: $0.60 Bedrock, $0.09 AgentCore compute and $1.00 contingency. This is a planning ceiling, not an observed bill or a guarantee of credit eligibility.

Amazon Nova Lite's documented EU inference profile is `eu.amazon.nova-lite-v1:0`, with Ireland among its source Regions and Converse support. Bedrock now enables serverless foundation-model access on first invocation subject to IAM and account prerequisites; the first invocation remains deliberately untested. The project must still stop if a fresh credit or permission check differs, and the first paid invocation requires explicit owner approval.

Local AWS CLI access is not configured, and the AWS plugin connection expired during this checkpoint. Live non-root IAM validation, deployment-role activation and cloud deployment therefore remain pending. No static access keys will be created as a shortcut.

Later on 11 September, the plugin was reconnected and STS verified NeighborGearOperator rather than root. The live Lambda API confirmed 1,000 concurrent and unreserved executions, zero functions and zero code storage. After an exact owner approval, the existing preflight inline policy gained only two non-mutating policy-validation actions. Access Analyzer returned zero findings across the five reviewed identity-policy bundles, and positive/negative IAM simulations enforced the intended MFA, role, resource and model boundaries. Review-only placeholders for resources that do not exist yet still require replacement and revalidation. Deployment permissions and paid invocation remain disabled.

On 12 September, after another exact owner approval, the preflight policy gained only `iam:GetContextKeysForCustomPolicy`, a read-only helper for custom-policy simulation; console read-back confirmed the saved scope. The exact route/integration policy rendered with the deployed HTTP API ID produced zero AWS policy-editor findings. API Gateway V2 simulation allowed all four intended exact-API operations, then denied unrelated-API POST and PATCH while exact-API GET and DELETE controls stayed allowed. The simulation-only policy was not created or attached. The AWS connector was unavailable during this checkpoint, so this evidence came from the authenticated owner console. No application deployment or model invocation occurred.

Pricing sources: [AgentCore](https://aws.amazon.com/bedrock/agentcore/pricing/), [Nova Lite](https://aws.amazon.com/blogs/machine-learning/customizing-text-content-moderation-with-amazon-nova/), and [Lambda](https://aws.amazon.com/lambda/pricing/). Model reference: [Amazon Nova Lite model card](https://docs.aws.amazon.com/bedrock/latest/userguide/model-card-amazon-nova-lite.html).

## Quota request checkpoint — 10 September 2026 (historical)

With explicit owner approval conditional on no charges or plan upgrade, submitted an Ireland Lambda Concurrent executions quota request for 1,000 through the root console. The console required a requested value at least equal to the default 1,000; it would not accept the application's calculated minimum of 104. Request history verified **Pending**, requested value 1,000, dated 10 September. This is not approval or an applied quota increase. No plan upgrade, application resource deployment, model invocation or changes to the template's 2 + 1 + 1 reserved concurrency limits occurred. Quota compatibility remains blocked until approval and a fresh applied-limit check. Earlier statements that no quota request occurred are historical.

Read-only preflight completed, 10 September: owner-approved NeighborGearPreflightReadOnly was attached and its exact saved contents verified in IAM. The non-root plugin successfully listed the user's one OAuth managed policy, one preflight inline policy and zero groups, and read Ireland Lambda settings: concurrency 10, unreserved 10, zero functions. This supersedes the missing-read-permission blocker below. Quota compatibility remains unresolved; no quota increase or deployment occurred. Billing balance and service eligibility were not refreshed by these checks.

Latest access checkpoint, 10 September: the OAuth sign-in policy was attached with owner approval, MFA remains enabled, and STS verified the reconnected plugin as NeighborGearOperator (not root). The next preflight's self-policy/group listings and Ireland Lambda GetAccountSettings were all denied for missing identity permissions. Reauthentication is no longer the blocker; scoped read access and subsequent deployment authorization remain pending. No quota increase, deployment or model invocation occurred.

Status: **quota, credit-balance, planning-cost, exact deployed-API policy and quarantined security-scaffold gates verified; application deployment and paid Bedrock evaluation remain disabled pending remaining policy assembly, workload-boundary creation, role activation, live IAM validation and explicit deployment/invocation approvals.** The approved monitoring budget, operator sign-in setup, owner-managed network prerequisite and quarantined security scaffold now exist in AWS.

## Access-policy checkpoint — 9 September 2026

Shutdown review checkpoint: application expiry, ten-attempt admission and the dry-run-first shutdown CLI are implemented and tested locally. The new [shutdown permission review](../infra/iam-review/shutdown-review.md) records an Autopilot 0.3.0 scan with broad-resource findings; its output is not approved for attachment. Owner maintenance access, actual cloud shutdown and the first UTC test window remain open. Historical account observations below are not a current balance or credential check.

User reports successful non-root IAM console login after MFA resynchronization. The 8 September plugin recheck succeeded but still returned root; the plugin must use a separately verified non-root session before deployment. Lambda concurrency remains 10 and is marked adjustable; no increase was requested. The existing 2 + 1 + 1 reservations require a documented minimum of 104 with the 100-unit unreserved pool, assuming no other reservations.

Review-only policies and source-policy scan findings are in [the access review](../infra/iam-review/README.md). No deployment policy was attached. The fixed workload boundary, explicit workload roles, artifact-upload draft and named-resource provisioning component are prepared locally. The new owner scaffold is disabled and its deployment roles have deny-all quarantine. Full provisioning permissions and bootstrap activation are still unfinished; these drafts are not a deployment-ready bootstrap. Later checkpoints supersede this historical note for the reviewed bundles and exact deployed-API component; remaining AgentCore/workload-identity validation is still pending.

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
