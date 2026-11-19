# Publication checklist

- [x] Review the intended nine experiment packages, installation commands and documentation links.
- [x] Preserve original projects and private evidence outside the release.
- [x] Record B11's successful controlled runtime smoke test.
- [x] Publish historical observations only at the level supported by their evidence.
- [x] Label B15/B16 deployment helpers as offline-validated prototypes.
- [x] Check the release index for excluded paths, secrets, binaries, generated state and backups.
- [x] Prepare the first local commit in an independent Git checkout.
- [ ] Confirm authorship, institutional wording and file-level redistribution permissions. Review the inherited SEED and Aiken notices and the provenance of adapted source and configuration. [Attribution and licensing](../../NOTICE.md)
- [ ] Replace the local commit's placeholder Git identity with the approved author and committer identity.
- [ ] Confirm the destination repository and explicitly approve the push.

The release candidate is a source-only snapshot. The evidence scope in the README is suitable for review without additional runtime experiments. The rights, identity and push approval items are the remaining publication gates.

From the clean release checkout, after confirming rights and the author identity, use:

```bash
git config --local user.name "Approved author name"
git config --local user.email "Approved author email"
git commit --amend --no-edit --reset-author
python3 scripts/validate-static.py
git status --short --branch
git log -1 --format=fuller
git ls-files -ci --exclude-standard
git remote -v
```

Confirm the working tree is clean and the ignored-index check prints no paths. Create an empty GitHub repository in the approved owner account. After explicit publication approval, configure that repository's exact URL and push the reviewed commit:

```bash
git remote add origin "$approved_github_url"
git push -u origin main
```

Set `approved_github_url` to the new repository URL before running those two commands. Keep the local research archive, raw evidence and generated credentials outside the checkout.
