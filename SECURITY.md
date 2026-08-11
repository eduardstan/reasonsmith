# Security

## Reporting a vulnerability

Please report suspected vulnerabilities privately by email to **stan.i.eduard@gmail.com**. Please do not open a public issue for an unpatched security problem. Include a description of the issue, the affected version, steps to reproduce it, and any relevant logs or proof of concept (with secrets removed).

We will acknowledge a report within one week and aim to provide an initial assessment within two weeks. Remediation can take longer when investigation or a release is in progress; we will keep the reporter updated when we can.

## Scope

In scope are vulnerabilities in reasonsmith itself, including unsafe handling of inputs, solver integration, the subprocess invocation of the BLACK LTLf solver ([black-sat.org](https://www.black-sat.org)), TOML pack loading, and importing a caller-supplied system module. In particular, please report behavior that unexpectedly executes code, escapes the intended process boundary, exposes data, or misrepresents a security-relevant result.

reasonsmith runs a solver and shells out to the BLACK LTLf solver ([black-sat.org](https://www.black-sat.org)) as a subprocess. It loads TOML packs supplied by the user and can import a system module supplied by the caller. A pack or system module is code the operator has chosen to run: reasonsmith does not sandbox either one. Compromise of the operator's own environment, or an intentionally malicious pack or system module run with the operator's permissions, is therefore not by itself a vulnerability in reasonsmith.

## Supported versions

Security fixes are made for the latest released version. Please upgrade to the latest release before reporting an issue when possible.
