# Deprecation & Retirement Policy

**Status:** skeleton at EP-01. EP-03 completes it. `M0-CON-021` is not claimed
until then.

## Lifecycle states

A contract is in exactly one state: `draft`, `active`, `deprecated`, or
`retired`. The state is recorded in the catalog and validated.

```text
draft -> active -> deprecated -> retired
```

## Deprecation

Deprecating a contract announces intent to remove it. It does not remove it.
A deprecated contract keeps working for its published consumers, and carries
deprecation metadata naming the replacement and the earliest retirement point.

## Retirement

Retirement removes a contract from the supported set. It is a breaking change
and requires the corresponding major-version treatment. A contract is not
retired while a listed consumer still depends on the version in question.

## Immutability still applies

Deprecating or retiring a contract never edits an already-published release
artifact. The change is expressed in a new release.

## To be completed in EP-03

- minimum deprecation window;
- required deprecation metadata fields and their validation;
- consumer sign-off before retirement.
