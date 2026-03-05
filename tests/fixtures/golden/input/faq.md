# Private LLM FAQ

## How are answers grounded?
Answers are generated only from authorized indexed chunks and return citations.

## What happens when ingestion fails?
The file enters `failed` status and can be retried using the reprocess action.

## How is upload-and-ask tracked?
Requests move through `waiting_for_index`, `executing`, and then a terminal state.
