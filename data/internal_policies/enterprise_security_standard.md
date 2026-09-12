# Enterprise Baseline Security & Compliance Standards (Policy ID: POL-SEC-2026-V3)

## 1. Data Encryption Standard
- **Encryption at Rest**: All customer data, intellectual property, backups, and logs must be encrypted using AES-256 or ChaCha20-Poly1305 with dedicated customer-managed encryption keys (CMEK) or AWS KMS / GCP KMS managed keys.
- **Encryption in Transit**: All data transmitted across public networks or between microservices must enforce TLS 1.3 (TLS 1.2 minimum). Deprecated cipher suites (TLS 1.0, 1.1, SSLv3) are strictly prohibited.
- **Key Rotation**: Cryptographic keys must automatically rotate at least once every 365 days.

## 2. Artificial Intelligence & Machine Learning Governance
- **Zero Training Policy**: Vendors providing AI, LLM, or automated processing features must strictly guarantee that customer proprietary data, queries, prompts, and inference outputs will NOT be used to train, fine-tune, or evaluate public or proprietary AI models.
- **Data Isolation**: Multi-tenant AI services must provide logical isolation of vector databases and embedding stores.
- **Opt-Out is Insufficient**: AI non-training must be the default operational state, not an opt-out setting.

## 3. Data Retention and Expungement SLAs
- **Contract Termination**: Upon contract expiration or termination, all customer data, user metadata, and vector index embeddings must be permanently purged within thirty (30) calendar days.
- **Backup Sanitization**: Backups must be sanitized and completely overwritten within ninety (90) days maximum.
- **Certificate of Destruction**: The vendor must provide a formal written Certificate of Destruction signed by an executive officer within 15 days of data purge.

## 4. Subprocessor Governance & Third-Party Risk
- **Prior Notification**: Vendors must provide at least thirty (30) days prior written notice before onboarding any new subprocessor that handles or stores customer data.
- **Equivalence Standard**: All subprocessors must adhere to data protection obligations that are at least as stringent as those agreed upon with the primary vendor.
- **Certifications**: All data-hosting subprocessors must hold current SOC 2 Type II or ISO/IEC 27001 certifications.

## 5. Security Incident & Breach Notification
- **Notification Timeline**: In the event of a confirmed or reasonably suspected security breach, data exfiltration, or unauthorized access, the vendor must notify the Enterprise Security Operations Center (SOC) within twenty-four (24) hours.
- **Incident Brief**: The initial notification must include root cause hypothesis, scope of affected records, and immediate containment countermeasures.

## 6. Identity, Authentication, and Access Control
- **Single Sign-On (SSO)**: The solution must natively support enterprise SAML 2.0 or OIDC federation (e.g., Okta, Azure AD, Google Workspace).
- **Multi-Factor Authentication (MFA)**: MFA is mandatory for all administrative access and privileged accounts.
- **Role-Based Access Control (RBAC)**: Fine-grained permissions and least-privilege enforcement must be supported out of the box.

## 7. Independent Audits & Certifications
- **SOC 2 Type II**: Vendor must provide an annual SOC 2 Type II report covering Security, Confidentiality, and Availability with clean auditor opinion (no material exceptions).
- **Penetration Testing**: Annual independent third-party penetration testing must be conducted, and an executive summary must be provided upon request.
