# ADR-0002: Keep Visitors as Extractors

## Status

Accepted.

## Context

Visitors are close to source syntax and can easily become dumping grounds for scoring logic.

## Decision

Visitors must extract structure only. Reusable syntactic classification belongs in `analysis.utils`. Energy smell detection, complexity scoring, carbon prediction, and optimization recommendations must live in future analysis engines.

## Trade-Offs

Some visitor fields such as `contains_api_call` and `contains_file_io` remain because they are existing structural output. Their implementation is centralized in reusable call inspection utilities.
