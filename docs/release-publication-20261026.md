# Paired official publication receipt — 2026-10-26

Rudy explicitly authorized paired formal publication. Both releases are complete
and verified. This receipt is a LOCAL documentation follow-up, not another change
to the tagged release contents. It has not been pushed as part of the releases.

| Integration | Version | Tagged final default-branch commit | Published UTC |
| --- | --- | --- | --- |
| rudyll/ha-gts-wavepump | [v0.7.0](https://github.com/rudyll/ha-gts-wavepump/releases/tag/v0.7.0) | cf19946046f96c602ca2103ee99b2c98b5491bbf | 2026-10-26T05:12:26Z |
| rudyll/ha-zetlight-led | [v0.23.0](https://github.com/rudyll/ha-zetlight-led/releases/tag/v0.23.0) | ca242cf14fba3fc9c554e030aec7d7a671ff13fb | 2026-10-26T05:12:32Z |

Observed remote verification: both releases are latest, non-draft, non-prerelease;
tag and main manifests carry semantic versions0.7.0/0.23.0; annotated tags peel
to the exact final commits above. Release bodies match remote tagged changelogs
and local reviewed bodies byte-for-byte. No commit-hash remote-version fallback
is expected from missing GitHub Release metadata. Actual HACS UI refresh was not
queried; release availability does not prove the local HA installation updated.

GTS final default-branch contents were pushed from the isolated public worktree,
then v0.7.0 created and pushed. Primary GTS private acceptance history was excluded
and never pushed. Zetlight final contents were pushed before v0.23.0. Release
creation used --verify-tag/--latest with reviewed --notes-file. No force push,
tag movement or release-note edit occurred. Verification outputs are in
/private/tmp/reef-releases-20261026/publication-verified.json; the generated safe
receipt below contains only public version/commit/Release metadata.

Existing verified software evidence:71GTS tests/41subtests;102Zetlight tests/
52subtests with unchanged source; native offline config/service validation and
actual-template→fan method day/night simulations. Physical flow and hardware
failure acceptance remain separate. No HA install/reload, blueprint import,
automation activation, device operation, personal-data export or monitor was done.

Known limitations remain in release notes: explicit pump-clock agreement, reviewed
physical limits, separate blueprint migration and diagnostic channel-label width.
Old imported automation settings do not automatically change when HACS updates.

F28/GTS-R11 DONE for formal publication. Deployment/blueprint migration and
supervised acceptance remain unapproved; do not start them from this receipt.
Next possible task requires scoped user authorization and a strong-reasoning model.
