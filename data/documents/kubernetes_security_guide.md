# TechCorp Kubernetes Security Guide

**Document ID:** POL-K8S-SEC-001  
**Version:** 1.3  
**Classification:** INTERNAL  
**Effective Date:** March 1, 2024  
**Last Reviewed:** September 30, 2024 (post SA-2024-Q3 audit)  
**Maintained By:** Platform Engineering & Security Operations  

---

## 1. Overview

This guide establishes TechCorp's security standards for Kubernetes cluster operations across all environments (production, staging, development). These guidelines were developed in response to findings from the Q1 and Q3 2024 security audits (SA-2024-Q1, SA-2024-Q3) and align with the CIS Kubernetes Benchmark v1.8, NSA/CISA Kubernetes Hardening Guide, and NIST SP 800-190 (Application Container Security Guide).

**Applicable Clusters:**
- `prod-k8s-01` — Production (AWS EKS, us-east-1)
- `stg-k8s-01` — Staging (AWS EKS, us-east-1)
- `dev-k8s-01` — Development (AWS EKS, us-east-1)

---

## 2. RBAC Best Practices

Role-Based Access Control (RBAC) is the primary authorization mechanism for Kubernetes API access. The Q3 2024 audit (CVE-2024-2001) identified Critical misconfigurations in RBAC that allowed privilege escalation from a compromised pod to cluster-admin access within minutes. The following standards are mandatory.

### 2.1 Principle of Least Privilege

- **Never use `cluster-admin` for application workloads.** The `cluster-admin` ClusterRole grants unrestricted access to all resources in all namespaces. Application service accounts must use namespace-scoped Roles, not ClusterRoles.
- **Create purpose-specific Roles.** Each service account should have a custom Role granting only the specific verbs and resources it needs. Example: a logging agent needs `get` and `list` on `pods` and `pods/log` — not `*` on `*`.
- **Audit RBAC bindings quarterly.** Use `kubectl auth can-i --list --as=system:serviceaccount:<namespace>:<sa>` to verify effective permissions for every service account.

### 2.2 Service Account Management

- **Disable automatic token mounting.** Set `automountServiceAccountToken: false` in the PodSpec for all workloads that do not require Kubernetes API access. This prevents compromised containers from accessing the service account token at `/var/run/secrets/kubernetes.io/serviceaccount/token`.
- **Do not use the `default` service account for workloads.** Create dedicated service accounts for each deployment. The `default` service account in each namespace must have zero RBAC bindings.
- **Use short-lived tokens.** Prefer projected service account tokens (`TokenRequest` API) with audience binding and expiration over long-lived secret-based tokens.

### 2.3 RBAC Policy Enforcement

- **Deploy OPA Gatekeeper or Kyverno** to enforce RBAC constraints:
  - Block creation of ClusterRoleBindings to `cluster-admin` for service accounts
  - Block RoleBindings granting `pods/exec`, `secrets`, or wildcard permissions without explicit approval
  - Require the `app.kubernetes.io/managed-by` label on all RBAC resources

---

## 3. Network Policies

The Q3 2024 audit (CVE-2024-2004) found that only 3 of 23 namespaces had NetworkPolicy resources, allowing unrestricted lateral movement. The following standards address this finding.

### 3.1 Default Deny

Every namespace must have a default-deny ingress and egress NetworkPolicy:

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny-all
  namespace: <namespace>
spec:
  podSelector: {}
  policyTypes:
    - Ingress
    - Egress
```

After applying the default deny, create explicit allow policies for each legitimate communication path.

### 3.2 Namespace Isolation

- **Production namespaces** (`production`, `payment`, `auth`) must not accept ingress from development or staging namespaces.
- **System namespaces** (`kube-system`, `monitoring`, `logging`) must have explicit allow-list policies for each service that requires access.
- **Use namespace labels** for policy selectors: `environment: production`, `environment: staging`, `team: platform`.

### 3.3 Egress Controls

- Restrict egress to known external endpoints using FQDN-based policies (via Calico or Cilium).
- Block direct internet access from application pods — route through an egress proxy for audit logging.
- Allow DNS (port 53 to `kube-dns`) explicitly in all egress policies.

---

## 4. Pod Security Standards

### 4.1 Enforce Pod Security Admission

Enable Kubernetes Pod Security Admission (PSA) with the following profiles per namespace:

| Namespace Type | PSA Level | Mode |
|---|---|---|
| Production workloads | `restricted` | `enforce` |
| System/infrastructure | `baseline` | `enforce` |
| Development | `baseline` | `warn` |

### 4.2 Mandatory Pod Security Context

All production pods must specify a security context that meets the `restricted` profile:

- `runAsNonRoot: true`
- `readOnlyRootFilesystem: true`
- `allowPrivilegeEscalation: false`
- `capabilities.drop: ["ALL"]`
- `seccompProfile.type: RuntimeDefault`

The Q3 2024 audit (CVE-2024-2006) found 15 pods running as root with `privileged: true`. Deploy Kyverno/Gatekeeper policies to block pods that do not comply with the restricted profile in production namespaces.

### 4.3 Resource Limits

All containers must specify CPU and memory requests and limits to prevent denial-of-service conditions within the cluster. LimitRange resources should be configured in each namespace to enforce defaults.

---

## 5. Container Image Security

### 5.1 Image Scanning

Per SA-2024-Q3 finding CVE-2024-2002, TechCorp mandates image vulnerability scanning at multiple stages:

1. **Build time:** Trivy scan integrated into the CI/CD pipeline (GitLab CI). Images with Critical CVEs are blocked from being pushed to the registry.
2. **Registry level:** Harbor registry configured with automatic Trivy scanning on push. Images older than 30 days are re-scanned weekly.
3. **Runtime:** Continuous scanning of running images via Prisma Cloud Defender. Alerts generated for newly disclosed CVEs affecting deployed images.

**Blocking thresholds:**
- **Critical CVE:** Deployment blocked. Immediate remediation required.
- **High CVE:** Deployment blocked in production. 7-day remediation window for staging.
- **Medium/Low CVE:** Warning only. Tracked in vulnerability backlog.

### 5.2 Image Provenance and Signing

- All production images must be signed using Sigstore/cosign before deployment.
- Admission controller (Kyverno) validates image signatures before allowing pod creation.
- Images must reference a digest (`image@sha256:...`), not a mutable tag (`:latest`, `:v1`).

### 5.3 Base Image Standards

- Approved base images: `distroless` (Google), `chainguard` images, or TechCorp-maintained golden images based on Alpine.
- `ubuntu`, `debian`, and `centos` full images are prohibited in production. Existing workloads must migrate by Q1 2025.
- Base images must be updated within 7 days of a patch release for Critical CVEs.

---

## 6. Secrets Management

### 6.1 Current State and Migration Plan

The Q3 2024 audit (CVE-2024-2005) found 8 deployments storing credentials as plain-text environment variables. TechCorp is migrating to a centralized secrets management architecture:

**Target Architecture (Q4 2024):**
- **HashiCorp Vault** as the central secrets store
- **External Secrets Operator** to sync Vault secrets into Kubernetes
- **Dynamic secrets** for database credentials (Vault database secrets engine)
- **Automatic rotation** every 30 days for static secrets

### 6.2 Interim Standards

Until Vault migration is complete:
- Store all secrets as Kubernetes Secret resources (not environment variables in Deployment manifests)
- Enable etcd encryption at rest using the KMS provider (AWS KMS)
- Restrict `secrets` RBAC permissions to only service accounts that require them
- Never commit secrets to Git repositories — use sealed-secrets or SOPS for GitOps workflows

### 6.3 Secrets Hygiene

- Rotate all credentials immediately upon suspicion of compromise (per Incident Response Policy, Phase 3)
- Audit secret access via Kubernetes audit logs (enabled per SA-2024-Q1 remediation)
- Remove unused secrets quarterly as part of the namespace hygiene process

---

## 7. Audit Logging

### 7.1 Kubernetes Audit Policy

Kubernetes API server audit logging must be enabled on all clusters (remediated per SA-2024-Q1 finding CVE-2024-1008). The audit policy captures:

- **RequestResponse level:** For `secrets`, `configmaps`, `roles`, `rolebindings`, `clusterroles`, `clusterrolebindings`, `serviceaccounts`
- **Request level:** For `pods`, `deployments`, `services`, `ingresses`
- **Metadata level:** For all other resources
- **None:** For read-only requests to `/healthz`, `/readyz`, and `kube-system` events (to reduce log volume)

### 7.2 Log Pipeline

Audit logs are shipped via Fluentd to Elasticsearch with the following retention:
- **Hot storage:** 90 days (searchable via Kibana)
- **Cold storage:** 1 year (archived to S3 Glacier)

Per the Incident Response Policy (POL-IR-001, Section 7), these logs support forensic analysis and must maintain integrity. The Q3 2024 finding on log injection (CVE-2024-2003) highlights the need for log integrity validation, which is being implemented via hash-chain verification.

---

## 8. Cluster Maintenance

- **Kubernetes version:** Stay within N-2 of the latest stable release. Current: v1.28. Upgrade to v1.29 scheduled for Q4 2024.
- **Patching:** Security patches applied within 48 hours for Critical CVEs, 7 days for High, 30 days for Medium.
- **etcd security:** etcd communication encrypted with TLS. etcd data encrypted at rest. Access restricted to API server only.
- **API server hardening:** Anonymous authentication disabled. RBAC enabled (no ABAC). Admission controllers: NodeRestriction, PodSecurity, ResourceQuota, LimitRanger, MutatingAdmissionWebhook (Kyverno).

---

*This guide is maintained by the Platform Engineering team. For questions or exception requests, contact platform-security@techcorp.internal. Exceptions require CISO approval and must be documented with a compensating control plan.*
