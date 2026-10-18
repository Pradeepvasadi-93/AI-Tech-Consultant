# Task 3 Design — LangGraph + Groq

## Graph
A compiled LangGraph `StateGraph` passes a typed project state through five explicit nodes: Transcript Analyst, Product Feasibility, Scope Agent, Estimation Agent, and Proposal/Review Agent. Groq is called through `langchain-groq`; model and API key are configurable through environment variables.

## Evidence and scope
The Transcript Analyst extracts requirements, decisions, constraints, assumptions, client commitments, open questions, and short source excerpts. Long transcripts are processed in chunks and merged. Product Feasibility calls Task 1's `/query` endpoint per requirement and classifies evidence as existing configuration, existing with limitation, potential custom development, or needs clarification. Missing evidence does not prove a feature is unsupported.

## Estimation and proposal
The Estimation Agent emits low/likely/high hour ranges with rationale, assumptions, dependencies, and confidence. The proposal includes scope, acceptance criteria, pricing assumptions, responsibilities, exclusions, risks, open questions, and next steps. Price remains unquoted when no hourly rate is configured.

## Persistence and approval
SQLite stores projects, versions, approved baseline, audit events, and simulated sends. Follow-up meetings compare with the approved baseline, not an unapproved draft. A specific version must be approved before the send endpoint can record a simulated send; duplicate sends are rejected.

## Limitations
Verify the Task 1 response contract and Groq model availability in the target environment. Model-generated requirement IDs and title matching can be imperfect. Evaluation results require manual semantic grading. Estimates need engineer review; simulated send is not real client delivery.
