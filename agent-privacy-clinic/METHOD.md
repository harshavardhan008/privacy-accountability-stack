# Agent Privacy Readiness Scorecard: method

## Purpose

To learn how often organizations that deploy AI agents have five basic privacy controls in place. The results will be reported as descriptive statistics. They will not claim to represent all organizations.

## Instrument

Five yes/no questions (purpose, minimization, record, approval, sandbox), one status question (`none`, `pilot`, `production`: does the respondent's organization have agents touching personal data), and one optional role field. The page computes a score from 0 to 5 and a short result code such as `AAR1|pilot|10101|engineer`.

## Consent notice shown on the page

> This check is anonymous. It stores nothing on this page and sends nothing unless you choose to submit your result code. The code contains your five answers, your agent status, and your role, and nothing that identifies you or your organization. Submitted codes will be summarized in aggregate and may appear in a talk, a paper, or a report. You can use the page without submitting.

## Data handling

* No names, emails, IP addresses, or organization names are collected by the page.
* If you collect codes with a form tool, turn off collection of respondent emails and IP addresses, and do not add free-text fields.
* Store the raw codes in a file. Run `aar score codes.txt` to summarize.
* Groups with fewer than 5 respondents are suppressed in the output.

## Analysis plan (written before any data is collected)

Report: number of responses, mean score, percent answering yes to each check, percent scoring zero or one, and mean score by agent status. No significance testing and no causal claims. The sample is self-selected and will skew toward people who attend privacy and AI events, so results will be described as responses from attendees and not as industry rates. Any change to this plan after data arrives will be stated in the write-up.

## Ethics

Check whether your institution treats an anonymous professional survey as exempt from human-subjects review, and get that in writing if you plan to publish. If you are not affiliated with a review board, say so in the write-up and keep the survey anonymous and voluntary.

## Running it at an event

1. Host `index.html` on any static host (GitHub Pages works).
2. Set `SUBMIT_URL` near the top of the file to a form that accepts one text field. Use `{code}` where the result code goes.
3. Generate a QR code: `python tools/make_qr.py <url> scorecard_qr.png`.
4. Put the QR on the last slide and on handouts. Give people a minute to use it.
5. Collect the codes, run `aar score`, and publish the summary with the date and event.

## Limitations

Self-reported answers. Yes/no questions hide partial implementations. The five checks are a starting set, not a complete model of readiness. Attendees may answer for a different agent than the one you would have chosen. Say all of this when you report results.
