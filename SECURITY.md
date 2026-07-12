# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 1.x     | :white_check_mark: |
| < 1.0   | :x:                |

## Reporting a Vulnerability

We take security vulnerabilities seriously. If you discover a security issue in ShotFlow, please report it privately — do not file a public issue.

**How to report:**

1. Open a draft security advisory on GitHub:
   https://github.com/MS33834/ShotFlow/security/advisories/new

2. Alternatively, contact the maintainers directly through the project's
   [discussion page](https://github.com/MS33834/ShotFlow/discussions).

**What to include:**

- A clear description of the vulnerability
- Steps to reproduce (proof of concept preferred)
- Potential impact assessment
- Any suggested mitigations or fixes (optional)

**Response timeline:**

- **Acknowledgement**: within 48 hours of submission
- **Initial triage**: within 5 business days
- **Fix (if accepted)**: timeline depends on severity, typically 7–30 days
- **Public disclosure**: coordinated between reporter and maintainers

We appreciate your help in keeping ShotFlow secure.

## Security Best Practices for Users

1. **API keys**: Never commit provider API keys to the repository. Use the
   `.env` file (already in `.gitignore`) for local credentials.
2. **Database**: Change the default `SECRET_KEY` in production. Use a strong,
   randomly generated key.
3. **Access control**: The ShotFlow REST API does not implement authentication
   by default. Use a reverse proxy (e.g., Nginx) with authentication in
   production deployments.
4. **MCP server**: The MCP server runs over stdio transport and is designed for
   local agent orchestration. Do not expose it as a network service without
   additional security measures.
