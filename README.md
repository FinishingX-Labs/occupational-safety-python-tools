# FinishingX AI Review Tools

A collection of Python tools developed by FinishingX to support document review,
occupational safety work, audit preparation, and training-material review.

These tools are designed to assist qualified users. They provide structured
observations, comparisons, suggestions, and traceable outputs. They do not
replace professional judgement, legal advice, site observation, audits, risk
assessments, or compliance decisions.

Each tool has its own folder. Detailed instructions are provided in the
documentation PDF contained in the relevant tool folder, including installation,
configuration, usage, outputs, limitations, and cost information.

## Tools included

| Tool | Purpose | Detailed documentation |
|---|---|---|
| **Document Assistant** | Answers questions about one document supplied by the user. Each displayed statement is tied to a passage in that document and checked against a verbatim quotation. | [Open tool folder](./ChatBot_GitHub/) |
| **Regulatory Comparison Tool** | Compares one of your documents against a regulatory text you supply. It breaks the regulatory text into requirements and reports whether each requirement is covered, divergent, not covered, or unclear. | [Open tool folder](./RegulatoryCheck_GitHub/) |
| **Risk Assessment Review Assistant** | Reviews an existing occupational risk-assessment spreadsheet and suggests additional prevention measures, missing controls, ownership, deadline, and wording improvements. It does not assess or rate risks. | [Open tool folder](./RiskAssessment_analyse_GitHub/) |
| **Training Material Compliance Check** | Reviews an occupational-safety training presentation against supplied regulatory, internal-documentation, and risk-assessment reference material. Findings are written into the PowerPoint speaker notes. | [Open tool folder](./Projet1_extraction_GitHub/) |
| **Audit Review Assistant** | A self-review aid for completed audit records. It helps an auditor identify unsupported, vague, inconsistent, incomplete, or unclear entries before issuing an audit. It reviews the audit record, not the organisation or the auditor. | [Open tool folder](./Audit_review_GitHub/) |

## Start here

1. Choose the tool that matches your task from the table above.
2. Open that tool’s folder.
3. Open and read the documentation PDF in that folder.
4. Follow that tool’s installation and configuration instructions.
5. Create a local `.env` file containing your API key where required.
6. Run the tool from its own folder.

The documentation PDF in each tool folder is the authoritative guide for that
tool. It contains tool-specific package requirements, configuration variables,
input formats, commands, generated files, known limitations, and warnings about
cost.

## Important safeguards

- These tools produce **assistance and recommendations**, not approvals,
  certifications, legal conclusions, or compliance determinations.
- Review all output before relying on it or sharing it.
- Do not treat an absence of findings as proof that a document, presentation,
  assessment, audit, or organisation is compliant.
- Do not upload or commit client documents, personal data, confidential
  information, API keys, copyrighted standards, licensed regulatory
  publications, or proprietary evaluation material unless you have the right
  to do so.
- Keep `.env` files out of version control. They may contain API keys.
- Check the cost warnings in the relevant tool documentation before processing
  long documents, large spreadsheets, extensive regulations, or long
  presentations.

## License

Copyright © 2026 FinishingX media, s.r.o.

This software is licensed under the PolyForm Noncommercial License 1.0.0.
Noncommercial use, modification, and redistribution are permitted subject to
that license.

Commercial use requires a separate written license from FinishingX media, s.r.o.
Contact: info@finishingx.de

See [LICENSE](./LICENSE) for the complete license terms.
