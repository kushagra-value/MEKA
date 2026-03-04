# TechCorp Data Protection Policy

**Document ID:** POL-DP-001  
**Version:** 2.4  
**Classification:** INTERNAL  
**Effective Date:** January 1, 2024  
**Last Reviewed:** February 28, 2024  
**Policy Owner:** Data Protection Officer (Maria Gonzalez)  
**Approved By:** Chief Information Security Officer, General Counsel  

---

## 1. Purpose and Scope

This policy defines TechCorp's obligations and controls for protecting personal data and sensitive business information throughout its lifecycle. It establishes the technical and organizational measures required under the General Data Protection Regulation (GDPR), with particular emphasis on Article 32 (Security of Processing), and supports compliance with SOC 2 Trust Services Criteria, ISO 27001, and applicable national data protection laws.

This policy applies to all TechCorp employees, contractors, data processors, and sub-processors who handle, access, store, or transmit data classified as Confidential or above, as well as any personal data as defined under GDPR Article 4(1).

---

## 2. Data Classification

TechCorp uses a four-tier data classification system. All data assets must be classified at creation and reclassified upon any change in sensitivity or regulatory status.

### 2.1 Classification Levels

**PUBLIC**
- Definition: Information intended for unrestricted distribution.
- Examples: Marketing materials, published blog posts, open-source code, press releases.
- Controls: No special handling required. Standard integrity controls apply.

**INTERNAL**
- Definition: Information intended for TechCorp employees and authorized contractors. Disclosure would cause minimal harm.
- Examples: Internal wikis, engineering documentation, non-sensitive meeting notes, organizational charts.
- Controls: Access restricted to authenticated TechCorp personnel. Encrypted in transit (TLS 1.2+). No public sharing without approval.

**CONFIDENTIAL**
- Definition: Sensitive business information whose unauthorized disclosure could cause significant harm to TechCorp or its stakeholders.
- Examples: Financial reports, security audit reports (SA-2024-Q1, SA-2024-Q3), strategic plans, source code, vulnerability assessments, incident reports.
- Controls: Access restricted on need-to-know basis. Encrypted at rest (AES-256) and in transit (TLS 1.2+). Access logging enabled. Data loss prevention (DLP) rules active. No external sharing without NDA and CISO approval.

**RESTRICTED**
- Definition: Highly sensitive data whose unauthorized disclosure would cause severe harm, regulatory penalties, or legal liability. Includes all personal data subject to GDPR.
- Examples: Customer PII (names, emails, addresses, payment data), employee HR records, authentication credentials, encryption keys, health data, data covered by attorney-client privilege.
- Controls: All CONFIDENTIAL controls, plus: field-level encryption where applicable, access limited to named individuals with documented business justification, quarterly access reviews, enhanced audit logging (who accessed what, when, from where), data masking in non-production environments. Retention limits enforced per Section 5.

### 2.2 Data Classification Register

The DPO maintains a Data Classification Register in Confluence (Compliance > Data Classification), updated quarterly. Each entry documents: data asset name, classification level, data controller, data processor(s), legal basis for processing (per GDPR Article 6), retention period, and storage location.

---

## 3. GDPR Compliance Framework

### 3.1 Legal Basis for Processing (Article 6)

All processing of personal data must have a documented legal basis. TechCorp's primary legal bases are:

- **Contract performance (Article 6(1)(b)):** Processing customer data necessary for service delivery (e.g., account management, billing, support).
- **Legitimate interest (Article 6(1)(f)):** Security monitoring, fraud detection, service analytics. Subject to Legitimate Interest Assessment (LIA) documented by the DPO.
- **Consent (Article 6(1)(a)):** Marketing communications, optional analytics, cookies beyond strictly necessary. Consent must be freely given, specific, informed, unambiguous, and as easy to withdraw as to give.
- **Legal obligation (Article 6(1)(c)):** Tax records, regulatory reporting, law enforcement cooperation.

### 3.2 Security of Processing — Article 32

In compliance with GDPR Article 32, TechCorp implements the following technical and organizational measures, appropriate to the risk level of the processing:

**Technical Measures:**
1. **Encryption at rest:** All RESTRICTED and CONFIDENTIAL data encrypted using AES-256. Database-level encryption enabled on PostgreSQL (TDE) and RDS. S3 server-side encryption (SSE-S3 or SSE-KMS) mandatory for all buckets. Kubernetes secrets encrypted at rest in etcd using KMS provider.
2. **Encryption in transit:** TLS 1.2 minimum for all external communications. TLS 1.3 preferred. Internal service mesh (Istio) configured for mutual TLS (mTLS) — enforcement upgraded from PERMISSIVE to STRICT following SA-2024-Q1 finding. Certificate management via cert-manager with 90-day rotation.
3. **Pseudonymization:** Customer data used for analytics and ML training must be pseudonymized. Direct identifiers (name, email, phone) replaced with reversible tokens. The tokenization key is stored separately in AWS KMS with access restricted to the Data Engineering lead and DPO.
4. **Access controls:** Role-based access control (RBAC) enforced across all systems. Principle of least privilege applied per the Kubernetes Security Guide (ref: POL-K8S-SEC-001) and IAM policies. Multi-factor authentication mandatory for all access to RESTRICTED data.
5. **Backup and recovery:** RESTRICTED data backed up daily with 30-day retention. Recovery Point Objective (RPO): 4 hours. Recovery Time Objective (RTO): 8 hours. Backups encrypted and stored in geographically separate region (eu-west-1 for primary data in us-east-1).

**Organizational Measures:**
1. **Data protection training:** All employees handling personal data complete annual GDPR training. Role-specific training for Engineering, Customer Support, and HR teams.
2. **Data Processing Agreements (DPAs):** In place with all sub-processors per Article 28. Current sub-processors: AWS (infrastructure), Stripe (payments), SendGrid (email), Okta (identity), Datadog (monitoring). Sub-processor register maintained by the DPO and reviewed quarterly.
3. **Data Protection Impact Assessments (DPIAs):** Conducted for all new processing activities involving RESTRICTED data, large-scale profiling, or automated decision-making per Article 35. DPIAs reviewed and approved by the DPO before processing begins.
4. **Regular security assessments:** Quarterly security audits (ref: SA-2024-Q1, SA-2024-Q3) and annual penetration testing by external firms.

### 3.3 Data Subject Rights (Articles 15–22)

TechCorp has implemented processes to fulfill data subject rights requests within the 30-day statutory deadline:

- **Right of access (Article 15):** Data subjects can request a copy of their personal data via privacy@techcorp.com or the in-app Privacy Center.
- **Right to rectification (Article 16):** Corrections processed within 5 business days.
- **Right to erasure (Article 17):** Erasure requests evaluated against retention obligations. Automated deletion pipeline ensures removal from all primary stores, backups (within backup rotation cycle), and sub-processor systems within 30 days. Anonymized analytics data is retained.
- **Right to data portability (Article 20):** Export available in JSON and CSV formats via self-service portal.
- **Right to object (Article 21):** Processing ceased within 48 hours of validated objection for direct marketing. Legitimate interest objections evaluated by the DPO.

---

## 4. Encryption Requirements

### 4.1 Encryption Standards

| Context | Algorithm | Key Length | Protocol | Notes |
|---|---|---|---|---|
| Data at rest — databases | AES-256-GCM | 256-bit | — | TDE on PostgreSQL/RDS |
| Data at rest — object storage | AES-256 | 256-bit | SSE-KMS | AWS-managed or customer-managed keys |
| Data at rest — K8s secrets | AES-CBC | 256-bit | KMS provider | Migrating to AES-GCM in Q4 2024 |
| Data in transit — external | — | — | TLS 1.2+ (1.3 preferred) | RSA 2048 or ECDSA P-256 certificates |
| Data in transit — internal | — | — | mTLS via Istio | STRICT mode enforced |
| Field-level encryption | AES-256-GCM | 256-bit | Application-level | For SSN, payment card tokens, health data |
| Password hashing | bcrypt | — | — | Cost factor 12, migrated from MD5 per SA-2024-Q1 |
| Key management | — | — | AWS KMS | Automatic key rotation every 365 days |

### 4.2 Key Management

- All encryption keys managed through AWS KMS (us-east-1, with replica in eu-west-1)
- Customer-managed keys (CMKs) used for RESTRICTED data
- Key access restricted to named IAM roles with CloudTrail logging of all KMS API calls
- Key rotation: automatic annual rotation for KMS keys; manual rotation within 24 hours if compromise suspected
- Emergency key revocation procedure documented in the Incident Response Policy (POL-IR-001, Phase 3)

---

## 5. Data Retention and Disposal

| Data Category | Retention Period | Disposal Method |
|---|---|---|
| Customer account data | Duration of contract + 2 years | Automated deletion pipeline |
| Transaction/billing records | 7 years (tax/legal obligation) | Secure deletion after retention period |
| Security logs | 90 days hot / 1 year cold | Automatic lifecycle policy (S3 → Glacier → deletion) |
| Incident records | Indefinite | N/A — permanent retention for legal/compliance |
| Employee HR records | Duration of employment + 6 years | Secure deletion by HR Operations |
| Marketing consent records | Duration of consent + 3 years | Automated deletion pipeline |
| Backup data | 30 days (rolling) | Overwritten by backup rotation |

Data disposal must render data irrecoverable. For digital media: cryptographic erasure (delete encryption keys) or NIST SP 800-88 compliant overwriting. For physical media: cross-cut shredding (DIN 66399 Level P-5 minimum).

---

## 6. Breach Notification Procedures

### 6.1 Internal Breach Assessment

Upon detection of a potential personal data breach, the DPO must be notified immediately via dpo@techcorp.internal. The DPO, in consultation with the Incident Response Team (per POL-IR-001), performs a breach assessment evaluating:

1. Nature of the breach (confidentiality, integrity, availability)
2. Categories of data affected and number of data subjects
3. Likely consequences for data subjects
4. Measures taken or proposed to mitigate adverse effects

### 6.2 Supervisory Authority Notification (Article 33)

If the breach is likely to result in a risk to the rights and freedoms of data subjects, TechCorp must notify the relevant supervisory authority **within 72 hours** of becoming aware of the breach. The notification must include:

- Nature of the breach including categories and approximate number of data subjects
- Name and contact details of the DPO
- Likely consequences of the breach
- Measures taken or proposed to address the breach

The DPO is responsible for preparing and submitting this notification, with review by General Counsel. If full information is not available within 72 hours, information may be provided in phases per Article 33(4).

**Recent example:** The S3 bucket misconfiguration identified in SA-2024-Q1 (CVE-2024-1003) was assessed by the DPO and reported to the ICO under Article 33 on March 18, 2024, as the exposure potentially affected 450,000+ EU data subjects.

### 6.3 Data Subject Notification (Article 34)

If the breach is likely to result in a **high risk** to the rights and freedoms of data subjects, affected individuals must be notified "without undue delay." Notification is not required if:
- Data was encrypted/pseudonymized and keys were not compromised
- Subsequent measures ensure the high risk is no longer likely to materialize
- Individual notification would involve disproportionate effort (in which case, public communication is used)

### 6.4 Notification Templates

Pre-approved notification templates are maintained in Confluence (Compliance > Breach Notification) for:
- Supervisory authority notification (ICO, CNIL, BfDI)
- Data subject notification (email template, in-app notice)
- Press statement (coordinated with Communications Lead per POL-IR-001)

---

## 7. Data Protection Officer Responsibilities

The DPO (Maria Gonzalez, dpo@techcorp.internal) has the following responsibilities per GDPR Articles 37–39:

1. Inform and advise TechCorp and its employees on GDPR obligations
2. Monitor compliance with GDPR and internal data protection policies
3. Provide advice on Data Protection Impact Assessments (Article 35)
4. Act as the contact point for data subjects and supervisory authorities
5. Maintain the Records of Processing Activities (Article 30)
6. Report directly to the CEO on data protection matters (independence per Article 38)
7. Coordinate with the CISO and IRT on data breach assessment and notification
8. Conduct quarterly reviews of sub-processor compliance and DPA adherence

---

## 8. Third-Party Data Sharing

Personal data may only be shared with third parties under the following conditions:
- A valid Data Processing Agreement (Article 28) or Data Sharing Agreement is in place
- The transfer has a documented legal basis (Article 6)
- For international transfers outside the EEA: Standard Contractual Clauses (SCCs) per Article 46(2)(c) or adequacy decision per Article 45
- The DPO has approved the transfer following a transfer impact assessment
- The recipient's security measures have been validated (questionnaire or audit)

---

## 9. Policy Compliance and Enforcement

Violations of this policy may result in disciplinary action up to and including termination of employment or contract. Violations that constitute criminal offenses will be reported to law enforcement.

TechCorp conducts annual compliance audits of this policy. Findings are reported to the CISO, General Counsel, and the Board's Audit Committee.

---

**Revision History:**
| Version | Date | Author | Changes |
|---|---|---|---|
| 2.4 | 2024-02-28 | Maria Gonzalez | Added S3 breach notification case study, updated sub-processor list |
| 2.3 | 2023-11-15 | Maria Gonzalez | Updated encryption standards, added field-level encryption requirements |
| 2.2 | 2023-06-01 | Maria Gonzalez | Aligned with ISO 27001:2022 revision |
| 2.0 | 2023-01-01 | Robert Singh | Major revision for GDPR enforcement updates |

---

*This policy is the property of TechCorp. For data protection inquiries, contact dpo@techcorp.internal. For general policy questions, contact compliance@techcorp.internal.*
