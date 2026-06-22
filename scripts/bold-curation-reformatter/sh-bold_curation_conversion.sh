#!/bin/bash
#SBATCH --job-name=bold_curation
#SBATCH --partition=medium
#SBATCH --output=bold_curation_%j.out
#SBATCH --error=bold_curation_%j.err
#SBATCH --mem=10G
#SBATCH --cpus-per-task=1

# ── Paths (edit these) ─────────────────────────────────────────────────────
LOG_FOLDER="/mnt/shared/projects/nhm/museomix/BGE/bold_curation/logfiles_library_curation/"
BOLD_DATA="/mnt/shared/projects/nhm/museomix/BGE/bold_curation/BOLD_Public.22-May-2026.tsv"
OUTPUT_DIR="/mnt/shared/projects/nhm/museomix/BGE/bold_curation/output_files/"
INITIALS="BP"

# ── Run ────────────────────────────────────────────────────────────────────
echo "Job started: $(date)"
echo "Node: $(hostname)"
echo "Python: $(python3 --version)"
echo ""

python3 bold_curation_report.py \
    "${LOG_FOLDER}" \
    "${BOLD_DATA}" \
    --output_dir "${OUTPUT_DIR}" \
    --initials "${INITIALS}"

echo ""
echo "Job finished: $(date)"
