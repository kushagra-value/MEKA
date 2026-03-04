# TechCorp Incident Response Policy

**Document ID:** POL-IR-001  
**Version:** 3.2  
**Classification:** INTERNAL  
**Effective Date:** January 1, 2024  
**Last Reviewed:** March 15, 2024  
**Policy Owner:** Chief Information Security Officer (CISO)  
**Approved By:** Executive Leadership Team  

---

## 1. Purpose and Scope

This policy establishes TechCorp's framework for identifying, responding to, containing, and recovering from security incidents. It applies to all employees, contractors, and third-party service providers who access TechCorp systems, networks, or data.

An **security incident** is defined as any event that compromises the confidentiality, integrity, or availability of TechCorp's information assets, including but not limited to: unauthorized access, data breaches, malware infections, denial-of-service attacks, insider threats, policy violations, and physical security breaches.

This policy aligns with NIST SP 800-61 Rev 2 (Computer Security Incident Handling Guide), ISO 27001:2022 Annex A.16, and GDPR Articles 33 and 34 regarding breach notification requirements. All incidents are tracked through TechCorp's incident management system using the INC-XXX identifier format (see `incident_tickets.json` for current incident log).

---

## 2. Incident Response Team Structure

### 2.1 Core Incident Response Team (IRT)

| Role | Primary | Backup | Contact |
|---|---|---|---|
| Incident Commander | Sarah Chen (CISO) | Marcus Rivera (VP Security) | irt-commander@techcorp.internal |
| Technical Lead | James Park (Staff Security Engineer) | Priya Sharma (Sr. Security Engineer) | irt-tech@techcorp.internal |
| Communications Lead | Diana Torres (VP Communications) | Alex Kim (PR Manager) | irt-comms@techcorp.internal |
| Legal Counsel | Robert Singh (General Counsel) | External: Baker & Associates | legal@techcorp.internal |
| Data Protection Officer | Maria Gonzalez (DPO) | — | dpo@techcorp.internal |

### 2.2 Extended Response Team

For P1 and P2 incidents, the IRT may activate subject-matter experts from:
- **Platform Engineering** — For Kubernetes, cloud infrastructure, and CI/CD incidents
- **Application Security** — For application-layer vulnerabilities and exploitation
- **Customer Success** — For customer-impacting incidents requiring proactive outreach
- **Finance** — For incidents involving financial data or regulatory penalties

---

## 3. Severity Classification

All security incidents are classified using a four-tier priority system (P1–P4). Classification determines response time, escalation path, and communication requirements.

### P1 — Critical

**Definition:** Active exploitation causing or imminently causing significant harm. Complete compromise of production systems, active data exfiltration, ransomware deployment, or breach affecting >10,000 data subjects.

**Examples:**
- Active unauthorized access to customer PII databases
- Ransomware infection spreading across production systems
- Complete authentication service compromise (ref: CVE-2024-1001 type incidents)
- Production Kubernetes cluster-admin compromise (ref: CVE-2024-2001)

**Response Targets:**
- **Acknowledge:** 15 minutes
- **Triage and Classify:** 30 minutes
- **Containment:** 4 hours
- **MTTR Target:** 24 hours
- **Post-Incident Review:** Mandatory within 72 hours

**Escalation:** Automatic notification to CISO, CEO, General Counsel, and DPO. External legal counsel engaged. Board notification within 24 hours if data breach confirmed.

---

### P2 — High

**Definition:** Confirmed vulnerability under active exploitation with limited scope, or significant security control failure without confirmed data loss. Potential to escalate to P1 if uncontained.

**Examples:**
- Unauthenticated API endpoint discovered with evidence of unauthorized access (ref: CVE-2024-1002, INC-003)
- Misconfigured S3 bucket with public access to sensitive data (ref: CVE-2024-1003)
- Compromised employee credentials with evidence of lateral movement
- Container escape in production environment

**Response Targets:**
- **Acknowledge:** 30 minutes
- **Triage and Classify:** 1 hour
- **Containment:** 8 hours
- **MTTR Target:** 72 hours (3 business days)
- **Post-Incident Review:** Mandatory within 5 business days

**Escalation:** CISO and VP Engineering notified. DPO consulted if personal data is involved.

---

### P3 — Medium

**Definition:** Security vulnerability or policy violation without confirmed exploitation. Elevated risk requiring planned remediation within defined SLAs.

**Examples:**
- Vulnerability scan revealing unpatched Critical CVEs in production (ref: CVE-2024-2002)
- Over-permissive RBAC configurations discovered during audit (ref: SA-2024-Q3 findings)
- Failed phishing simulation with >20% click rate
- Missing encryption on internal service communication

**Response Targets:**
- **Acknowledge:** 4 hours
- **Triage and Classify:** 8 hours
- **MTTR Target:** 30 business days
- **Post-Incident Review:** Recommended for recurring patterns

**Escalation:** Security Operations team lead notified. Engineering team owner assigned.

---

### P4 — Low

**Definition:** Minor security finding or policy deviation with minimal risk. Informational findings or hardening opportunities.

**Examples:**
- Missing security headers on internal-only dashboards
- Default credentials on development/test systems
- Verbose error messages exposing stack traces in staging
- Expired SSL certificates on decommissioned systems

**Response Targets:**
- **Acknowledge:** 1 business day
- **MTTR Target:** 90 business days
- **Post-Incident Review:** Not required

**Escalation:** Tracked in backlog. Addressed during regular security sprint cycles.

---

## 4. Incident Response Lifecycle

### Phase 1: Detection and Reporting

Security incidents may be detected through:
- **Automated monitoring:** SIEM alerts (Splunk), IDS/IPS (Suricata), endpoint detection (CrowdStrike), cloud security monitoring (AWS GuardDuty, CloudTrail anomalies)
- **Internal reports:** Employee reports via #security-incidents Slack channel or security@techcorp.internal
- **External reports:** Bug bounty program (HackerOne), customer reports, threat intelligence feeds, law enforcement notification
- **Audit findings:** Quarterly security audits (ref: SA-2024-Q1, SA-2024-Q3)

All potential incidents must be reported within **1 hour** of discovery. Failure to report a known security incident is a policy violation subject to disciplinary action.

### Phase 2: Triage and Classification

The on-call Security Operations analyst performs initial triage:
1. Verify the incident is genuine (not a false positive)
2. Assign severity classification (P1–P4) per Section 3
3. Create an incident ticket (INC-XXX) in the incident management system
4. Activate the appropriate response team based on severity
5. Begin evidence preservation — snapshot affected systems, preserve logs

### Phase 3: Containment

Containment strategies are determined by the Technical Lead based on incident type:
- **Network containment:** Isolate affected network segments, block malicious IPs at WAF/firewall
- **Account containment:** Disable compromised credentials, revoke OAuth tokens, invalidate sessions
- **System containment:** Quarantine affected hosts/containers, pause affected Kubernetes deployments
- **Data containment:** Restrict access to affected data stores, enable additional logging

For P1 incidents, the Incident Commander has the authority to take production systems offline if necessary to prevent further harm, with immediate notification to VP Engineering and CTO.

### Phase 4: Eradication and Recovery

1. Identify and eliminate the root cause (malware, misconfiguration, vulnerability)
2. Apply patches, update configurations, rotate compromised credentials
3. Restore systems from known-good backups where applicable
4. Verify system integrity before returning to production
5. Implement monitoring for recurrence indicators

### Phase 5: Post-Incident Review

Post-incident reviews (PIRs) are mandatory for P1 and P2 incidents and recommended for P3 incidents with recurring patterns.

**PIR Requirements:**
- Conducted within the timeframe specified in Section 3 for the incident severity
- Facilitated by a team member who was **not** the Incident Commander for that incident
- Blameless format — focus on systemic improvements, not individual fault
- Documented using the PIR template (stored in Confluence: Security > Post-Incident Reviews)
- Action items tracked in Jira with assigned owners and due dates

**PIR Deliverables:**
- Timeline of events (detection → containment → resolution)
- Root cause analysis (direct cause, contributing factors, systemic issues)
- Impact assessment (systems affected, data exposed, business impact)
- Lessons learned and recommended improvements
- Specific, actionable follow-up items with deadlines

---

## 5. Communication Protocols

### 5.1 Internal Communication

| Severity | Communication Channel | Frequency | Audience |
|---|---|---|---|
| P1 | Dedicated Slack war room + bridge call | Every 30 minutes until contained | IRT + Extended Team + Executive Leadership |
| P2 | Dedicated Slack channel | Every 2 hours until contained | IRT + Relevant Engineering Teams |
| P3 | Incident ticket updates | Daily during active investigation | Security Operations + Assigned Team |
| P4 | Incident ticket updates | Weekly or on status change | Security Operations |

### 5.2 External Communication

External communication is **only** authorized through the Communications Lead, with approval from the Incident Commander and Legal Counsel.

**Regulatory Notification:**
- **GDPR (Article 33):** Supervisory authority must be notified within 72 hours of becoming aware of a personal data breach. The DPO is responsible for coordinating this notification with Legal Counsel.
- **GDPR (Article 34):** Data subjects must be notified "without undue delay" if the breach is likely to result in high risk to their rights and freedoms. See Data Protection Policy (POL-DP-001) for detailed procedures.
- **Contractual obligations:** Review all applicable DPAs and customer contracts for specific notification requirements.

### 5.3 Law Enforcement

Engagement with law enforcement requires approval from the General Counsel. The CISO may authorize immediate engagement in cases involving imminent threat to safety, state-sponsored attacks, or ransomware involving critical infrastructure.

---

## 6. Metrics and Reporting

The Security Operations team tracks the following KPIs, reported monthly to the CISO and quarterly to the Board:

- **MTTD (Mean Time to Detect):** Target < 24 hours for P1/P2
- **MTTR (Mean Time to Remediate):** Per severity targets in Section 3
- **Incident volume by severity and category**
- **Percentage of incidents resolved within SLA**
- **Post-incident review completion rate** (target: 100% for P1/P2)
- **Recurrence rate** (same root cause within 90 days)

---

## 7. Evidence Preservation and Log Retention

All incident-related evidence must be preserved according to the following requirements:

- **Security logs:** Minimum 90-day retention in hot storage (Elasticsearch), 1-year retention in cold storage (S3 Glacier)
- **Incident artifacts:** Forensic images, memory dumps, network captures preserved for the duration of the investigation plus 2 years
- **Incident tickets:** Retained indefinitely in the incident management system
- **Chain of custody:** Documented for all evidence that may be used in legal proceedings

Log sources must include: application logs, system logs, authentication logs, network flow logs, DNS query logs, Kubernetes audit logs (per SA-2024-Q1 finding CVE-2024-1008 remediation), and cloud provider audit trails (AWS CloudTrail, S3 access logs).

---

## 8. Training and Exercises

- **All employees:** Annual security awareness training including incident reporting procedures
- **IRT members:** Quarterly tabletop exercises simulating P1 incident scenarios
- **Engineering teams:** Annual red team / blue team exercises
- **Phishing simulations:** Monthly, with targeted training for employees who fail

---

## 9. Policy Review

This policy is reviewed annually or upon significant changes to TechCorp's threat landscape, regulatory environment, or organizational structure. Amendments require approval from the CISO and Executive Leadership Team.

**Revision History:**
| Version | Date | Author | Changes |
|---|---|---|---|
| 3.2 | 2024-03-15 | Sarah Chen | Updated MTTR targets, added K8s-specific containment procedures |
| 3.1 | 2023-09-01 | Sarah Chen | Added GDPR Article 33/34 notification procedures |
| 3.0 | 2023-01-15 | Marcus Rivera | Major revision — aligned with NIST SP 800-61 Rev 2 |

---

*This policy is the property of TechCorp. For questions or clarifications, contact security-policy@techcorp.internal.*
