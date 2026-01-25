#!/bin/bash
#SBATCH --partition=day
#SBATCH --output=%j_gap_analysis_out.out
#SBATCH --error=%j_gap_analysis_err.err
#SBATCH --mem=40G
#SBATCH --cpus-per-task=4
#SBATCH --mail-user=b.price@nhm.ac.uk
#SBATCH --mail-type=ALL

module load python/3.7

# Define paths
SCRIPT_DIR="/hpc/groups/genomics-collections/ukbol_accelerated/gap_fill/bold-data-fun/scripts/gap-analysis"
SPECIES_LIST="/hpc/groups/genomics-collections/ukbol_accelerated/gap_fill/uksi_valid_species_output.tsv"
RESULT_OUTPUT="/hpc/groups/genomics-collections/ukbol_accelerated/gap_fill/midori_lrRNA/MIDORI2_TOTAL_NUC_GB269_lrRNA_otus_taxid.tsv"
ASSESSED_BAGS="/hpc/groups/genomics-collections/ukbol_accelerated/gap_fill/midori_lrRNA/assessed_BAGS.tsv"
OUTPUT_FILE="/hpc/groups/genomics-collections/ukbol_accelerated/gap_fill/midori_lrRNA/lrRNA_gap_analysis.tsv"

cd $SCRIPT_DIR

python gap_analysis.py \
    --species-list "$SPECIES_LIST" \
    --result-output "$RESULT_OUTPUT" \
    --assessed-bags "$ASSESSED_BAGS" \
    --output "$OUTPUT_FILE"

echo "Complete!"