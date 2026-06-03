# CodeGraph Image Failure Report

Date: 2026-06-03

## Scope

This report uses CodeGraph plus runtime logs to analyze image-generation and image-edit failures in `chatgpt2api`.

Current CodeGraph index status:

- Files: 198
- Nodes: 3,729
- Edges: 7,961
- Database: `.codegraph/codegraph.db`

## What CodeGraph Is

`@colbymchenry/codegraph` is a local code intelligence tool. It indexes a repository into a graph database and lets an agent query symbols, callers, callees, impacted files, and affected tests. It is useful for tracing code paths, but it does not currently expose a built-in `report` command. Reports like this one are generated manually from `codegraph status`, `query`, `callees`, and source/log inspection.

Useful commands:

```powershell
codegraph status
codegraph query "stream_image_outputs_with_pool"
codegraph callees stream_image_outputs_with_pool
codegraph query "resolve_conversation_image_urls"
```

## Image Edit Request Chain

CodeGraph and source inspection show this request path:

```text
POST /v1/images/edits
api/ai.py
api/image_inputs.py
services/protocol/openai_v1_image_edit.py
services/protocol/conversation.py::stream_image_outputs_with_pool
services/openai_backend_api.py::stream_conversation
services/protocol/conversation.py::stream_image_outputs
services/openai_backend_api.py::resolve_conversation_image_urls
services/openai_backend_api.py::_poll_image_results
```

The account slot lifecycle is centered in `stream_image_outputs_with_pool`, which calls:

- `account_service.get_available_access_token`
- `account_service.mark_image_result`
- `account_service.release_image_slot`

## Current Log Diagnosis

Log file:

```text
10e1d6b06ac59900d744db56951ec68d85786a6b36f1bb5ed8621f12b6d6d8a8-json.log
```

The completed failure is conversation:

```text
6a1fa0a0-8180-83e8-809d-44af6d5631e9
```

Timeline:

- `03:33:50`: image upload prepared, `75,926` bytes, `688x1504`, `image/jpeg`.
- `03:33:50`: upload registered as `file_00000000c3fc720cb53c004c5334397c`.
- `03:33:51`: upload completed.
- `03:33:56`: image result resolution started.
- `03:33:56`: upstream response had `has_message=true`, `message_len=507`, `tool_invoked=false`, `blocked=false`, `terminal_message=false`, and no `file_ids` or `sediment_ids`.
- `03:34:07` through `03:43:53`: 57 polling attempts all returned empty `file_ids=[]` and `sediment_ids=[]`.
- `03:43:56`: `image_poll_timeout`, `timeout_secs=600`, `attempts_made=57`.
- `03:43:56`: `/v1/images/edits` returned `502 Bad Gateway`.

This specific failure was not caused by a large image upload. The failed input image was only about 76 KB, and the upload completed successfully.

It was also not a total network or service-wide bandwidth outage. During the same 10-minute window, other image jobs succeeded and produced file IDs:

- `6a1fa0ca-e538-83e8-a9fb-ee0bd7d11bce` hit `file_0000000040d871f5b357d8d5e6e0f80d`.
- `6a1fa113-cb74-83e8-9ff1-04861b9688a8` hit `file_00000000ed84722fac825772f9ceada0`.
- `6a1fa182-ce54-83e8-b880-388263cc73bf` hit `file_00000000da3c720ca3974675ae3fb444`.
- `6a1fa1f9-0be8-83e8-a552-4d050daab3e4` hit `file_0000000075fc720c85d62354ac962323`.
- `6a1fa256-2d18-83e8-9932-5805792def74` hit `file_00000000f9d8720c83651d0dca12f908`.
- `6a1fa2cd-9380-83e8-a677-d05389a9885f` hit `file_000000005288720c89a527a7198cc281`.

## Root Cause

For this log, the direct failure cause is:

```text
ChatGPT upstream accepted the edit conversation but never exposed a generated image asset id within 600 seconds.
```

In service terms:

```text
resolve_conversation_image_urls -> _poll_image_results -> ImagePollTimeoutError -> 502
```

The log does not prove local upload failure, local bandwidth failure, or account pool exhaustion. It points to an upstream per-conversation image job that did not produce `file_ids`/`sediment_ids`.

The suspicious detail is `tool_invoked=false` plus `has_message=true` for an image edit request. That means the upstream conversation returned text content but no image asset. Because the text was not classified as terminal/refusal by the current detector, the service waited for the full image poll timeout.

## Already Addressed in v1.4.3

The current code now has mitigations for the failure modes found in these logs:

- Adds image upload instrumentation: `image_upload_prepare`, `image_upload_registered`, `image_upload_complete`, `image_upload_failed`.
- Rejects oversized image references/uploads before sending them upstream.
- Detects terminal upstream image text/refusal cases earlier instead of always waiting 600 seconds.
- Releases image account concurrency slots in a `finally` path if a stream is closed before `mark_image_result`.
- Keeps regression coverage for poll timeout slot release and terminal text behavior.

## Added Follow-Up Instrumentation

After the `10e1...` log review, the image stream path now logs the upstream assistant text when ChatGPT returns text but no generated image asset IDs:

- `image_stream_resolve_start` includes `message_preview`, `message_len`, and `message_truncated`.
- `image_stream_text_without_image` records the ambiguous state before polling starts.
- `image_stream_poll_timeout` carries the same upstream text context through the timeout warning.
- `/api/logs` call-log details now also persist `conversation_id`, `upstream_message_preview`, `upstream_message_len`, `tool_invoked`, `turn_use_case`, `blocked`, and `terminal_message`, so the frontend log detail modal can show the concrete upstream reason without reading Docker stdout logs.

With this in place, the next occurrence should show the concrete upstream text that previously appeared only as `message_len=507`.

## Remaining Risk

The old `10e1...` log still cannot reveal the exact upstream text content for the failed `message_len=507` response because the message body was not logged at that time. Future logs should include the relevant preview.

Recommended next instrumentation:

- Add upstream finish/status details if ChatGPT exposes them in future response shapes.
- Optionally route `tool_invoked=false && has_message=true && no image ids` to an earlier failure path after a shorter grace window.
