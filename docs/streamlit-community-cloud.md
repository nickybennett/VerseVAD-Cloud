# Private Streamlit Community Cloud Deployment

This private repository is the deployment copy of VerseVAD. It contains the
licensed runtime datasets that are intentionally absent from the public
repository.

## Deployment coordinates

After the latest private changes are committed and pushed, create the app with:

- Repository: `nickybennett/VerseVAD-Cloud`
- Branch: `main`
- Main file path: `streamlit_app.py`
- Python version: `3.12`

Community Cloud recognizes the root `uv.lock` and installs the exact locked
environment. The `espeakng-loader` lock includes a compatible Linux x86-64
wheel, so no separate `packages.txt` system dependency is required.

If the repository or branch is reported as missing, authorize private-
repository access under Streamlit Community Cloud **Settings → Linked accounts
→ Source control** and refresh the deployment form.

## Repository privacy and app privacy

The GitHub repository must remain **Private**. Repository privacy and Streamlit
app visibility are separate settings. Unless the applicable dataset licenses
expressly permit a public hosted service, keep the Streamlit app private and
invite viewers explicitly.

Never place dataset credentials in source control or in the app. This
deployment reads only the exact checksum-pinned files committed to the private
repository.

## Hosted project-data behavior

The local desktop application stores Project/Corpus data persistently on the
user's computer. Community Cloud has an ephemeral, process-shared filesystem,
so the cloud entrypoint enables a safer policy:

- every browser session receives an unguessable, separate SQLite database;
- one visitor cannot list another visitor's projects through VerseVAD;
- appearance choices remain in Streamlit session state instead of a shared
  preference file; and
- Project/Corpus data may disappear after disconnect, app restart,
  redeployment, or hibernation.

Users must download any corpus export they need to retain. Single Poem, Other
Text, and Lexicon Explorer remain in-memory workflows.

## Updating the private deployment

Develop and publish ordinary code changes in the public `VerseVAD` repository.
Then update this separate private clone:

```powershell
cd "C:\Users\nickj\Documents\VerseVAD-Cloud"
git fetch upstream
git merge upstream/main
git push origin main
```

The private dataset commit and cloud-only files remain on the private branch.
Review merge conflicts carefully and confirm the remotes before every push:

```powershell
git remote -v
```

`origin` must be `nickybennett/VerseVAD-Cloud`; `upstream` must be the public
`nickybennett/VerseVAD` repository.
