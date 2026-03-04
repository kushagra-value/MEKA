# TechCorp OAuth & OIDC Security Guidelines

**Document ID:** POL-AUTH-002  
**Version:** 2.1  
**Classification:** INTERNAL  
**Effective Date:** May 1, 2024  
**Last Reviewed:** May 1, 2024 (major revision following SA-2024-Q1 findings)  
**Maintained By:** Application Security Team  

---

## 1. Overview

This document establishes TechCorp's security guidelines for OAuth 2.0 and OpenID Connect (OIDC) implementations across all services. These guidelines were significantly revised following the Q1 2024 security audit (SA-2024-Q1), which identified Critical vulnerabilities in TechCorp's authentication platform (CVE-2024-1001, CVE-2024-1005, CVE-2024-1006). The guidelines incorporate recommendations from RFC 6749, RFC 6819, the OAuth 2.0 Security Best Current Practice (RFC 9700), and the OpenID Connect Core 1.0 specification.

**Applicable Systems:**
- `auth.techcorp.internal` — TechCorp OAuth 2.0 / OIDC Provider (primary authorization server)
- All first-party and third-party clients registered with the authorization server
- API Gateway (`api-gw.techcorp.internal`) — token validation and enforcement point

---

## 2. Authorization Grant Types

### 2.1 Approved Grant Types

| Grant Type | Use Case | Requirements |
|---|---|---|
| Authorization Code + PKCE | Web applications, SPAs, mobile apps, CLI tools | PKCE mandatory for ALL clients (public and confidential). See Section 3. |
| Client Credentials | Service-to-service authentication (machine-to-machine) | Client secret stored in Vault (not environment variables). Scopes restricted to minimum required. |
| Device Authorization (RFC 8628) | IoT devices, smart TVs, CLI tools without browser | Polling interval enforced server-side. Short-lived device codes (5-minute expiry). |

### 2.2 Deprecated / Prohibited Grant Types

| Grant Type | Status | Rationale |
|---|---|---|
| Implicit | **Prohibited** | Access token exposed in URL fragment. Superseded by Authorization Code + PKCE per RFC 9700. All clients migrated as of April 2024. |
| Resource Owner Password Credentials (ROPC) | **Prohibited** | Exposes user credentials to the client. Legacy CRM integration migrated to Authorization Code flow in Q2 2024 (per SA-2024-Q1 remediation). |

---

## 3. PKCE Requirements

Proof Key for Code Exchange (PKCE, RFC 7636) is **mandatory for all clients** — both public and confidential — as of May 1, 2024. This requirement was implemented in response to CVE-2024-1001 (OAuth token leakage via redirect URI manipulation), where PKCE would have prevented authorization code interception even with a compromised redirect URI.

### 3.1 Implementation Requirements

- **Code challenge method:** `S256` is mandatory. The `plain` method is rejected by the authorization server.
- **Code verifier:** Minimum 43 characters, maximum 128 characters, generated using a cryptographically secure random number generator. Must contain only unreserved characters per RFC 3986 (A-Z, a-z, 0-9, `-`, `.`, `_`, `~`).
- **Server enforcement:** The authorization server rejects authorization requests without a `code_challenge` parameter. Token exchange requests without a valid `code_verifier` are rejected.
- **Binding:** The authorization server binds the code challenge to the authorization code and the specific client_id. Codes are single-use and expire after 60 seconds.

### 3.2 Client Registration

All clients must register with the authorization server before use. Registration requires:
- **Redirect URIs:** Exact-match validation (no wildcards, no partial matching). Each URI must use HTTPS (exception: `http://localhost` for local development only). Maximum 5 registered redirect URIs per client.
- **Application type:** `web`, `native`, `spa`, or `service` — determines applicable security controls.
- **Token endpoint auth method:** `private_key_jwt` (preferred) or `client_secret_post` for confidential clients. `none` for public clients (PKCE provides protection).

---

## 4. Token Lifecycle Management

### 4.1 Access Tokens

Access tokens authorize API requests and must be short-lived to minimize the impact of token leakage.

| Parameter | Value | Rationale |
|---|---|---|
| Format | JWT (signed with RS256) | Enables stateless validation at the API Gateway. Algorithm confusion attacks prevented by strict RS256 whitelist (per CVE-2024-1005 remediation). |
| Lifetime | 15 minutes | Reduced from 24 hours following SA-2024-Q1 audit. Limits exposure window for leaked tokens. |
| Signing key | RSA 2048-bit, rotated every 90 days | JWKS endpoint (`/.well-known/jwks.json`) publishes current and previous key for graceful rotation. |
| Audience (`aud`) | Must match the API identifier | Tokens without a valid audience claim are rejected by the API Gateway. |
| Scope | Minimum required per client | Over-scoped tokens flagged in quarterly access reviews. |

**Validation requirements at the API Gateway:**
1. Verify signature using public keys from the JWKS endpoint (cached with 5-minute TTL)
2. Validate `exp` (expiration), `nbf` (not before), `iss` (issuer), `aud` (audience)
3. Verify `scope` includes the required scope for the requested resource
4. Check token against the revocation list (Redis-backed, sub-millisecond lookups)
5. Reject tokens using the `none` algorithm or any algorithm not in the whitelist

### 4.2 Refresh Tokens

Refresh tokens enable long-lived sessions without exposing long-lived access tokens.

| Parameter | Value | Rationale |
|---|---|---|
| Lifetime | 30 days (reduced from 90 days per SA-2024-Q1) | Balances user experience with security. |
| Rotation | **One-time use with rotation** | Each refresh token exchange issues a new refresh token. The previous token is immediately invalidated. See Section 4.3. |
| Storage | Server-side only (opaque reference) | Refresh tokens are opaque strings, not JWTs. The actual token data is stored server-side in PostgreSQL. |
| Binding | Bound to client_id and user_id | Refresh tokens cannot be used by a different client than the one that originally requested them. |
| Revocation | Immediate on logout, password change, or security event | All refresh tokens for a user are revoked on password change or account compromise detection. |

### 4.3 Refresh Token Rotation

Refresh token rotation is a critical defense against token theft. TechCorp implements automatic rotation per RFC 6819 Section 5.2.2.3:

1. Client presents refresh token `RT1` to the token endpoint.
2. Server validates `RT1`, issues new access token `AT2` and new refresh token `RT2`.
3. `RT1` is immediately marked as used and cannot be redeemed again.
4. If `RT1` is presented again (replay attack), the server detects the reuse, revokes the **entire token family** (all descendants of the original authorization), and logs a security alert.
5. The security alert triggers an automated notification to the Security Operations team and is recorded as a potential incident (ref: Incident Response Policy, Section 4, Phase 1).

**Token family tracking:** Each authorization code exchange creates a token family identified by a `family_id`. All refresh tokens descended from that authorization belong to the same family. Reuse detection operates at the family level.

---

## 5. Token Storage Best Practices

### 5.1 By Client Type

**Web Applications (server-rendered):**
- Store tokens server-side in an encrypted session store (Redis with AES-256 encryption).
- Use HTTP-only, Secure, SameSite=Strict cookies for session identifiers.
- Never expose tokens to client-side JavaScript.

**Single-Page Applications (SPAs):**
- Use the Backend-for-Frontend (BFF) pattern: the SPA communicates with a server-side BFF that manages tokens. Tokens never reach the browser.
- If BFF is not feasible: store access tokens in memory only (JavaScript closure, not `localStorage` or `sessionStorage`). Accept that tokens are lost on page refresh and use silent refresh via hidden iframe or refresh tokens (with rotation) to reacquire.
- **Never store tokens in `localStorage`** — vulnerable to XSS attacks. This was a contributing factor in INC-005.

**Mobile Applications:**
- Store tokens in platform-secure storage: iOS Keychain (with `kSecAttrAccessibleWhenUnlockedThisDeviceOnly`), Android Keystore.
- Use system browser (not embedded WebView) for authorization flows to prevent credential theft.
- Implement certificate pinning for communication with the authorization server.

**Service-to-Service (Client Credentials):**
- Store client secrets in HashiCorp Vault (target architecture) or Kubernetes Secrets (interim, per Kubernetes Security Guide Section 6).
- Never embed client secrets in source code, Docker images, or CI/CD pipeline configurations.
- Rotate client secrets every 90 days. Dual-secret support enables zero-downtime rotation.

---

## 6. Known Vulnerability Patterns

The following vulnerability patterns have been identified through TechCorp's security audits and incident history. All developers working on authentication-related features must be familiar with these patterns.

### 6.1 Redirect URI Manipulation (CVE-2024-1001)

**Pattern:** Attacker registers or discovers a permissive redirect URI that redirects authorization codes or tokens to an attacker-controlled endpoint.
**TechCorp history:** SA-2024-Q1 found that partial wildcard matching in redirect URI validation allowed `https://techcorp.com.attacker.com` to pass validation. Resulted in INC-001 (unauthorized access to 12,000 customer records).
**Mitigation:** Exact-match redirect URI validation (Section 3.2). No wildcards. No subdomain matching.

### 6.2 Algorithm Confusion (CVE-2024-1005)

**Pattern:** Attacker exploits JWT validation libraries that accept the `none` algorithm or allow switching from asymmetric (RS256) to symmetric (HS256) signing, enabling token forgery.
**TechCorp history:** SA-2024-Q1 found the `jsonwebtoken` library (v8.5.1) did not reject the `none` algorithm explicitly.
**Mitigation:** Strict algorithm whitelist (RS256 only). Library upgraded. Server-side validation rejects tokens with any other `alg` header value.

### 6.3 Token Leakage via Referrer Headers

**Pattern:** Access tokens included in URL fragments or query parameters leak to third parties via the `Referer` HTTP header when the user navigates to an external link.
**Mitigation:** Implicit flow prohibited (Section 2.2). Access tokens never appear in URLs. `Referrer-Policy: no-referrer` header enforced on all authenticated pages.

### 6.4 CSRF in Authorization Flow

**Pattern:** Attacker initiates an authorization flow and tricks the victim into completing it, linking the attacker's identity to the victim's session.
**Mitigation:** The `state` parameter is mandatory and validated. PKCE provides additional CSRF protection. Nonce validation enforced for OIDC `id_token` responses.

### 6.5 Credential Stuffing on Token Endpoint (CVE-2024-1006)

**Pattern:** Attacker performs high-volume authentication attempts using breached credential lists from other services.
**TechCorp history:** SA-2024-Q1 found no rate limiting on `/oauth/token` and `/login` — 50,000 attempts in 10 minutes went undetected.
**Mitigation:** Rate limiting (10 req/min/IP, 5 failed/15min/account). CAPTCHA after 3 failures. Anomaly detection in WAF. Breach credential detection (Have I Been Pwned API integration).

---

## 7. Monitoring and Alerting

The following OAuth-specific events must trigger alerts in the SIEM:
- Refresh token reuse detection (automatic token family revocation)
- >5 failed token exchange attempts from the same client in 1 minute
- Token requests with unregistered redirect URIs
- Token requests using deprecated grant types
- JWT validation failures (signature, expiration, audience mismatch)
- Unusual geographic patterns for refresh token usage (e.g., token used from two countries within 1 hour)

Alerts are routed to the Security Operations on-call and processed per the Incident Response Policy (POL-IR-001).

---

## 8. Compliance Mapping

| Requirement | Framework | OAuth Control |
|---|---|---|
| Access token expiration | SOC 2 CC6.1 | 15-minute access tokens (Section 4.1) |
| Credential protection | GDPR Article 32 | Encryption of tokens at rest and in transit (Section 5) |
| Authentication logging | SOC 2 CC7.2 | SIEM integration for all OAuth events (Section 7) |
| Session management | ISO 27001 A.9.4.2 | Refresh token rotation, revocation on security events (Section 4.2) |
| Breach detection | GDPR Article 33 | Refresh token reuse alerts, anomaly detection (Section 7) |

---

*These guidelines are maintained by the Application Security team. For questions, exception requests, or to report a potential OAuth vulnerability, contact appsec@techcorp.internal.*
