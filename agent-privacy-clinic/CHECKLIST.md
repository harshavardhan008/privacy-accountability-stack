# Agent Privacy Clinic checklist

Use before an AI agent touches personal data. Print it, or run the scorecard in `index.html`.

## The five checks

| # | Check | Ask |
|---|---|---|
| 1 | **Purpose** | Does every request carry a purpose, and is it checked at each tool call? |
| 2 | **Minimization** | Does each tool return only the fields that purpose needs? |
| 3 | **Record** | Is a record written for every action, including denied ones, without storing the data itself? |
| 4 | **Approval** | Does a person approve writes and sends that leave your boundary? |
| 5 | **Sandbox** | Did the agent run on synthetic data with real business rules before real data? |

## Five more worth asking

| # | Topic | Ask |
|---|---|---|
| 6 | Handoffs | When one agent hands work to another, does the purpose travel along and stay fixed? |
| 7 | Memory | Is agent memory limited to one request, and cleared when it ends? |
| 8 | Summaries | Can you list every place an agent can write text, and the data each may hold? |
| 9 | Withdrawal | If a person withdraws consent today, can you list every action that touched them? |
| 10 | Owner | Does every agent have a named owner who can answer for what it did? |

## Reading your score

Scoring zero or one of the five means the agent is running on trust. Two or three means some controls exist but a request can still go wrong without leaving evidence. Four or five means you can likely answer an auditor, and the next step is testing the controls, not adding more.

A score describes controls, not outcomes. A five does not mean nothing can leak.
