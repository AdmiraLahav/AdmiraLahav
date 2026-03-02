good title + 
5:30
tell a story, not:
go to x
press Y
here is the vuln
Impact: the worst thing we can exploit with this vulns

chatpgt avg:
# Report Title
A concise summary of the bug.

## Affected Asset or Program
- Target (domain/app)
- Environment (production/stage)

## Vulnerability Type
- Classification (e.g. IDOR, XSS, SSRF, Auth Bypass)

## Detailed Description
Explain in plain language what the vulnerability is, why it exists, and under which conditions it can be triggered. Include relevant parameters, logic flaws, and any context.

## Impact Assessment
Describe the real impact if this bug were exploited:
- What can an attacker do?
- What data or functionality is at risk?
- Any user scopes affected (admin, regular user, API client)?

## Steps to Reproduce
1. Go to `https://…`
2. Use this request or payload: [show HTTP request or script]
3. Observe …
4. Expected vs actual behavior

## Proof of Concept (PoC)
(Optional but highly recommended)
- Screenshots
- HTTP requests
- curl commands

## Remediation Details
Explain how this should be fixed or was fixed by the vendor:
- Code change
- Config change
- Security control to add

## Original Report Link
- [Link to vendor disclosure / public page]
