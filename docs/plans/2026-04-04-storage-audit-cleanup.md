# Storage Audit & Cleanup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reduce ~134GB of scattered local storage by deleting junk, archiving knowledge to Obsidian, and organizing what remains.

**Architecture:** Work category-by-category from highest ROI (easy big deletions first) to nuanced decisions last. Each task is a self-contained triage decision. Nothing is permanently deleted without a review step first.

**Tech Stack:** zsh, `du`, `rm`, `mv`, Obsidian vault at `~/Vaults/Command-Center/`

---

## Current State (as of 2026-04-04)

| Directory | Size | Notes |
|---|---|---|
| ~/Downloads | 74GB | Software installers, Google Takeout, type beats, Audio WAVs |
| ~/Desktop | 24GB | Videos, DJI footage, nested old-laptop backups, demos |
| ~/Documents | 20GB | FL Studio (12GB) + Kits (8GB) |
| ~/Projects | 16GB | 19 repos, recently consolidated |
| ~/AIOS | 263MB | Keep — active infrastructure |
| ~/Music | 162MB | Check contents |
| ~/Vaults | 13MB | Keep — Obsidian second brain |

**Estimated recoverable without losing anything meaningful: 40–55GB**

---

## Task 1: Safe Deletes — Reinstallable Software (~27GB)

These are large files that can be re-downloaded if ever needed again.

**Files:**
- Delete: `~/Downloads/Waves 18.12.24 Mac/` (9.3GB)
- Delete: `~/Downloads/gtakeout/` (15GB) — raw Takeout zips, already processed or pipeline exists
- Delete: `~/Downloads/javafx-sdk-20.0.2/` (99MB)
- Delete: `~/Downloads/Boris FX Hub Installer_CrumplePop-1.1.31-mac.app` (50MB)
- Delete: `~/Downloads/ERA_Bundle_v6.2.00-VoiceChanger_v1.3.10-MAC/` (10MB)
- Delete: `~/Downloads/PitchShifter/` (95MB)
- Delete: `~/Downloads/TheMasker/` (40MB)
- Delete: `~/Downloads/SelfControl.app` (20MB)
- Delete: `~/Downloads/Femor/` (check if audio plugin, re-downloadable)

- [ ] **Step 1: Confirm gtakeout status**

```bash
ls ~/Downloads/gtakeout/
# Verify these are raw .zip files not yet processed, or already processed
# If the Takeout pipeline (~/AIOS/bin/) has already run → safe to delete
ls ~/AIOS/bin/ | grep takeout
```

Expected: Either pipeline exists (safe to delete zips) or confirm manually.

- [ ] **Step 2: Delete reinstallable software**

```bash
rm -rf ~/Downloads/"Waves 18.12.24 Mac"/
rm -rf ~/Downloads/javafx-sdk-20.0.2/
rm -rf ~/Downloads/Boris\ FX\ Hub\ Installer_CrumplePop-1.1.31-mac.app
rm -rf ~/Downloads/ERA_Bundle_v6.2.00-VoiceChanger_v1.3.10-MAC/
rm -rf ~/Downloads/PitchShifter/
rm -rf ~/Downloads/TheMasker/
rm -rf ~/Downloads/SelfControl.app
rm -rf ~/Downloads/Femor/
```

- [ ] **Step 3: Delete Google Takeout zips (only after confirming Step 1)**

```bash
rm -rf ~/Downloads/gtakeout/
rm -rf ~/Downloads/Takeout/  # smaller older takeout
```

- [ ] **Step 4: Verify freed space**

```bash
du -sh ~/Downloads/
```

Expected: Should drop from 74GB to ~45-50GB.

- [ ] **Step 5: No commit needed — filesystem only**

---

## Task 2: Duplicates and Redundant Archives (~3GB)

**Files:**
- Delete: `~/Desktop/Dsci-proj.zip` (1.3GB — project already lives at `~/Projects/Dsci-proj/`)
- Review: `~/Desktop/Desktop/` (3.1GB — nested old laptop backup)
- Review: `~/Desktop/Documents/` (1.6GB — nested old laptop backup)

- [ ] **Step 1: Verify Dsci-proj is safely in Projects**

```bash
ls ~/Projects/Dsci-proj/ | head -5
du -sh ~/Projects/Dsci-proj/
# Confirm zip is redundant
```

- [ ] **Step 2: Delete Dsci-proj.zip**

```bash
rm ~/Desktop/Dsci-proj.zip
```

- [ ] **Step 3: Audit nested Desktop backup**

```bash
ls ~/Desktop/Desktop/
# Subdirs: camcorder, Code, Java, Songs, spotify, untitled folder 2
ls ~/Desktop/Desktop/Code/
ls ~/Desktop/Desktop/Songs/
du -sh ~/Desktop/Desktop/*/
```

Expected: Old Mac backup from 2024. Code likely already in git. Songs might be unique.

- [ ] **Step 4: Decision — nested Desktop/Documents folders**

For `~/Desktop/Desktop/Code/` — check if any repo not in `~/Projects/`:
```bash
ls ~/Desktop/Desktop/Code/ 2>/dev/null
```

For `~/Desktop/Desktop/Songs/` — if music files not backed up elsewhere, move to `~/Desktop/demos/` or keep. Otherwise delete.

For `~/Desktop/Documents/` (has Adobe, curseforge, Image-Line, Zoom subfolders):
```bash
du -sh ~/Desktop/Documents/*/
# Image-Line data here may duplicate ~/Documents/Image-Line/
diff <(ls ~/Desktop/Documents/Image-Line/ 2>/dev/null) <(ls ~/Documents/Image-Line/ 2>/dev/null)
```

- [ ] **Step 5: Delete confirmed-redundant backup dirs**

```bash
# Only after Step 4 confirms nothing unique
rm -rf ~/Desktop/Desktop/
rm -rf ~/Desktop/Documents/
```

---

## Task 3: Type Beats and Junk Audio in Downloads (~700MB)

128 loose MP3 type beat files + `~/Downloads/Audio/` (674MB of shoe recording WAVs).

- [ ] **Step 1: Audit Audio folder contents**

```bash
ls ~/Downloads/Audio/ | head -5
du -sh ~/Downloads/Audio/
# "shoe1_2025-12-01..." WAVs — voice/audio recordings from Dec 2025
# Decide: are these recordings you want to keep?
```

- [ ] **Step 2: Decide on Audio WAVs**

If these are studio recordings or voice memos worth keeping:
```bash
mkdir -p ~/Desktop/STEREO/shoe-recordings-2025
mv ~/Downloads/Audio/*.wav ~/Desktop/STEREO/shoe-recordings-2025/
```

If disposable:
```bash
rm -rf ~/Downloads/Audio/
```

- [ ] **Step 3: Bulk-delete type beat MP3s in Downloads**

These are free internet beats — re-findable, not originals:
```bash
# Preview what will be deleted
ls ~/Downloads/*.mp3 | head -10
ls ~/Downloads/*.mp3 | wc -l  # should be ~128
```

```bash
rm ~/Downloads/*.mp3
```

- [ ] **Step 4: Verify**

```bash
ls ~/Downloads/*.mp3 2>/dev/null || echo "All loose MP3s cleared"
```

---

## Task 4: Coursework and Notes → Second Brain (~600MB)

Archive these to Obsidian, then delete source dirs.

**Files:**
- `~/Desktop/Stats Learning/` (579MB) → vault
- `~/Desktop/arch/` (424KB) → vault
- `~/Desktop/sylly/` (264KB) → vault
- `~/Desktop/comp nets/` (36KB) → vault
- `~/Desktop/Book/` (12MB) → vault
- PDFs on Desktop → vault or delete

- [ ] **Step 1: Audit Stats Learning contents**

```bash
ls ~/Desktop/"Stats Learning "/
du -sh ~/Desktop/"Stats Learning "/*/
```

- [ ] **Step 2: Move Stats Learning to vault**

```bash
mkdir -p ~/Vaults/Command-Center/Resources/Coursework/stats-learning
cp -r ~/Desktop/"Stats Learning "/* ~/Vaults/Command-Center/Resources/Coursework/stats-learning/
```

- [ ] **Step 3: Create vault index note for Stats Learning**

```bash
cat > ~/Vaults/Command-Center/Resources/Coursework/stats-learning/README.md << 'EOF'
---
tags: [coursework, statistics, machine-learning]
archived: 2026-04-04
source: ~/Desktop/Stats Learning
---
# Stats Learning Materials

CWRU DSCI coursework materials archived from Desktop.
EOF
```

- [ ] **Step 4: Move remaining coursework to vault**

```bash
mkdir -p ~/Vaults/Command-Center/Resources/Coursework
cp -r ~/Desktop/arch/ ~/Vaults/Command-Center/Resources/Coursework/arch/
cp -r ~/Desktop/sylly/ ~/Vaults/Command-Center/Resources/Coursework/syllabi/
cp -r ~/Desktop/"comp nets"/ ~/Vaults/Command-Center/Resources/Coursework/comp-nets/
cp -r ~/Desktop/Book/ ~/Vaults/Command-Center/Writing/book-draft/
```

- [ ] **Step 5: Process Desktop PDFs**

```bash
ls ~/Desktop/*.pdf
# Appointment Booked - MyHealthConnect.pdf → keep or archive to vault/Admin
# GitHub Issue Resolution Modeling.pdf → vault/Research
```

```bash
mkdir -p ~/Vaults/Command-Center/Resources/Research
mv ~/Desktop/"GitHub Issue Resolution Modeling.pdf" ~/Vaults/Command-Center/Resources/Research/
mkdir -p ~/Vaults/Command-Center/Admin
mv ~/Desktop/"Appointment Booked - MyHealthConnect.pdf" ~/Vaults/Command-Center/Admin/
```

- [ ] **Step 6: Delete sourced dirs from Desktop**

```bash
rm -rf ~/Desktop/"Stats Learning "/
rm -rf ~/Desktop/arch/
rm -rf ~/Desktop/sylly/
rm -rf ~/Desktop/"comp nets"/
rm -rf ~/Desktop/Book/
```

- [ ] **Step 7: Clean Desktop screenshots (stale)**

```bash
ls ~/Desktop/Screenshot*.png | wc -l
ls ~/Desktop/Screenshot*.png
# Review dates — everything older than 2 weeks is likely disposable
```

```bash
# Delete screenshots older than 14 days
find ~/Desktop -maxdepth 1 -name "Screenshot*.png" -mtime +14 -delete
find ~/Desktop -maxdepth 1 -name "*.jpeg" -mtime +14 -delete
```

---

## Task 5: Videos Decision (~12GB)

Drone footage and screen recordings are large — needs explicit keep/delete/archive decision.

**Files:**
- `~/Desktop/Videos/` (9.9GB) — OBS recordings, DJI clips, PPro projects
- `~/Desktop/+./` (4.7GB) — DJI drone footage from Oct 2025 (MP4 + LRF)
- `~/Desktop/DJI_20260213090420_0124_D.MP4` (1.3GB) — drone video loose
- `~/Desktop/Screen Recording 2026-02-09 at 10.16.15 PM.mov` (943MB)
- `~/Desktop/Screen Recording 2026-03-26 at 12.15.11 PM.mov` (561KB)

- [ ] **Step 1: Audit Videos folder**

```bash
du -sh ~/Desktop/Videos/*/
ls ~/Desktop/Videos/DJI/
ls ~/Desktop/Videos/OBS/
ls ~/Desktop/Videos/PPro/
```

- [ ] **Step 2: Decision point — drone footage**

Options:
- **Keep locally**: Leave in `~/Desktop/Videos/DJI/` — no action
- **Archive to external**: `rsync -av ~/Desktop/+./ /Volumes/ExternalDrive/DJI-Oct2025/`
- **Delete**: Only if you're confident you don't need the Oct 2025 drone footage

For LRF files (DJI low-res proxy files) — these are always safe to delete if you have the MP4:
```bash
find ~/Desktop/+./ -name "*.LRF" | wc -l
find ~/Desktop/+./ -name "*.LRF" -delete  # safe, proxies only
```

- [ ] **Step 3: Delete loose screen recordings if not needed**

```bash
# Review what these are:
# Feb 9 recording (943MB) — what was this capturing?
# Mar 26 recording (561KB) — tiny, probably fine to delete
rm ~/Desktop/"Screen Recording 2026-03-26 at 12.15.11 PM.mov"
# Feb 9 recording: delete only if you know what it is
```

---

## Task 6: Projects Cleanup (~2-3GB recoverable)

- [ ] **Step 1: Check pre-cr-suite duplication**

```bash
du -sh ~/Projects/pre-cr-suite/ ~/Projects/pre-cr-suite-lsp/
ls ~/Projects/pre-cr-suite/
ls ~/Projects/pre-cr-suite-lsp/
git -C ~/Projects/pre-cr-suite remote -v
git -C ~/Projects/pre-cr-suite-lsp remote -v
```

If `-lsp` is a superset/active branch of `pre-cr-suite`, the original may be deletable.

- [ ] **Step 2: Move claude-improvement-lab to Projects**

Currently at `~/Desktop/claude-improvement-lab/` but not in `~/Projects/`.
```bash
mv ~/Desktop/claude-improvement-lab/ ~/Projects/claude-improvement-lab/
```

- [ ] **Step 3: Archive claude-config**

```bash
ls ~/Desktop/claude-config/
# Check if this duplicates ~/.claude/ configs
diff ~/Desktop/claude-config/ ~/.claude/ 2>/dev/null || ls ~/Desktop/claude-config/
```

If fully redundant:
```bash
rm -rf ~/Desktop/claude-config/
```

- [ ] **Step 4: Check inactive project candidates**

```bash
# Show last commit date for each project
for d in ~/Projects/*/; do
  echo "$(git -C $d log -1 --format='%cr' 2>/dev/null || echo 'no git') — $d"
done | sort
```

Projects inactive > 6 months with no active development: candidates for archiving or deletion.

---

## Task 7: Documents Music Production (20GB — explicit decision)

`~/Documents/Image-Line/` (12GB FL Studio) and `~/Documents/Kits/` (8GB drum kits) are large but may be actively used.

- [ ] **Step 1: Check FL Studio activity**

```bash
du -sh ~/Documents/Image-Line/*/
ls ~/Documents/Image-Line/
# Check: are these FL Studio user data files? Replaceable from backup?
```

- [ ] **Step 2: Kits audit**

```bash
du -sh ~/Documents/Kits/*/
ls ~/Documents/Kits/ | head -20
# Are these kits you actively use in FL Studio or archived?
```

- [ ] **Step 3: Decision**

If FL Studio is uninstalled or kits aren't actively used → archive to external or delete.
If actively producing → keep, but note these 20GB are music production tools.

No automated action here — requires your explicit decision.

---

## Task 8: Downloads Miscellaneous Cleanup (~400MB)

- [ ] **Step 1: Clean remaining Downloads junk**

```bash
# These are safe to delete:
rm -rf ~/Downloads/cwrudsci-26s-dscix52-prof-06a357b59275/  # 735MB — coursework, archive if needed
rm -rf ~/Downloads/src/  # 33MB — check first
rm ~/Downloads/craig-Ke5FLZiHQI-KzhN_ZqWIoYC7X8.aac  # 39MB Discord recording
rm -rf ~/Downloads/"Archive 2"/
```

- [ ] **Step 2: Handle debian VM**

```bash
du -sh ~/Downloads/debian_rysca_arm.utm/
# 12GB — active UTM VM or abandoned?
# If actively used: mv ~/Downloads/debian_rysca_arm.utm/ ~/VMs/ (or wherever UTM stores VMs)
# If not used in months: delete
```

- [ ] **Step 3: Final Downloads tally**

```bash
du -sh ~/Downloads/
ls ~/Downloads/ | wc -l
```

---

## Task 9: FOLDER01 and STEREO (Audio Stems)

- [ ] **Step 1: Audit FOLDER01**

```bash
ls ~/Desktop/FOLDER01/
# MONO-000.wav through MONO-008.wav — stems from a recording session
du -sh ~/Desktop/FOLDER01/
```

- [ ] **Step 2: Decision**

If these are stems from an active track → keep or move to `~/Desktop/demos/` with a descriptive folder name.
If orphaned / don't know what project they're from → delete.

- [ ] **Step 3: Audit STEREO folder**

```bash
ls ~/Desktop/STEREO/
du -sh ~/Desktop/STEREO/*/
```

---

## Final State Check

- [ ] **Run final storage summary**

```bash
du -sh ~/Desktop ~/Downloads ~/Projects ~/Documents ~/Vaults ~/AIOS ~/Music
df -h /
```

Expected: Desktop < 15GB, Downloads < 30GB (from 74GB).

---

## Decision Reference Card

| Item | Size | Action | Status |
|---|---|---|---|
| Waves installer | 9.3GB | **Delete** — re-downloadable | pending |
| gtakeout zips | 15GB | **KEEP** — actively used | ✅ kept |
| Dsci-proj.zip | 1.3GB | **Delete** — in Projects/ already | pending |
| Type beat MP3s (128 files) | ~400MB | **Delete** — free internet beats | pending |
| Desktop/Desktop/ (nested) | 3.1GB | **Review → Delete** — old backup | pending |
| Desktop/Documents/ (nested) | 1.6GB | **Review → Delete** — old backup | pending |
| Stats Learning/ | 579MB | **Archive → Vault → Delete** | pending |
| arch/, sylly/, comp nets/ | ~700KB | **Archive → Vault → Delete** | pending |
| Book/ | 12MB | **Archive → Vault** | pending |
| claude-improvement-lab/ | 2.6MB | **Move to ~/Projects/** | pending |
| App installers (misc) | ~350MB | **Delete** | pending |
| Debian VM | 12GB | **Deleted** | ✅ done |
| FL Studio + Kits | 20GB | **KEEP** — actively used | ✅ kept |
| Video footage | ~16GB | **Consolidated → ~/Desktop/Video-Upload/** | ✅ done — upload to Drive then delete |
