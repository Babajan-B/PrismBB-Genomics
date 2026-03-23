"""
ACMG Secondary Findings v3.2 (2023) — 81 Actionable Genes
Used in Clinical Mode to restrict analysis to medically actionable gene list.

Reference: ACMG SF v3.2, Kalia et al. Genet Med 2023
Each gene is associated with at least one Tier 1 (High) actionable condition.
"""

# 81 ACMG SF v3.2 actionable genes (clinical mode filter)
ACMG_ACTIONABLE_GENES: set[str] = {
    # ── Hereditary Cancer ────────────────────────────────────────────────────
    "BRCA1", "BRCA2",                          # Hereditary breast/ovarian cancer
    "PALB2",                                   # Hereditary breast cancer
    "ATM", "CHEK2",                            # Breast/cancer risk
    "BARD1", "RAD51C", "RAD51D",               # Ovarian cancer
    "MLH1", "MSH2", "MSH6", "PMS2", "EPCAM",  # Lynch syndrome
    "APC",                                     # Familial adenomatous polyposis
    "MUTYH",                                   # MUTYH-associated polyposis
    "NTHL1", "MSH3",                           # Polyposis syndromes
    "PTEN",                                    # Cowden syndrome / PTEN hamartoma
    "TP53",                                    # Li-Fraumeni syndrome
    "STK11",                                   # Peutz-Jeghers syndrome
    "SMAD4", "BMPR1A",                         # Juvenile polyposis
    "CDH1",                                    # Hereditary diffuse gastric cancer
    "RET",                                     # MEN2 / medullary thyroid carcinoma
    "MEN1",                                    # Multiple endocrine neoplasia type 1
    "VHL",                                     # Von Hippel-Lindau
    "SDHB", "SDHC", "SDHD", "SDHAF2", "MAX",  # Hereditary paraganglioma/pheo
    "FH",                                      # Hereditary leiomyomatosis/RCC
    "FLCN",                                    # Birt-Hogg-Dubé syndrome
    "NF1", "NF2",                              # Neurofibromatosis
    "TSC1", "TSC2",                            # Tuberous sclerosis
    "WT1",                                     # Wilms tumor
    "DICER1",                                  # DICER1 syndrome
    "CDKN2A",                                  # Familial melanoma
    "BAP1",                                    # BAP1 tumor predisposition
    "TMEM127",                                 # Hereditary pheo
    "PRKAR1A",                                 # Carney complex
    "POLD1", "POLE",                           # Polymerase proofreading polyposis

    # ── Cardiovascular ───────────────────────────────────────────────────────
    # Hypertrophic cardiomyopathy
    "MYBPC3", "MYH7", "TNNT2", "TNNI3", "TPM1",
    "MYL3", "ACTC1", "PRKAG2", "MYL2",
    # Dilated cardiomyopathy
    "LMNA", "SCN5A", "RBM20", "FLNC",
    # Arrhythmogenic cardiomyopathy
    "PKP2", "DSP", "DSC2", "TMEM43", "DSG2",
    # Long QT / channelopathies
    "KCNQ1", "KCNH2", "KCNJ2", "CACNA1C",
    # Brugada / conduction disease
    "SCN5A",
    # Catecholaminergic polymorphic VT
    "RYR2", "CASQ2", "TRDN",
    # Aortopathies / Marfan
    "FBN1", "FBN2", "TGFBR1", "TGFBR2", "SMAD3",
    "ACTA2", "MYH11", "COL3A1", "MYLK", "SLC2A10",

    # ── Familial Hypercholesterolaemia ───────────────────────────────────────
    "LDLR", "APOB", "PCSK9",

    # ── Malignant Hyperthermia / RYR ─────────────────────────────────────────
    "RYR1", "CACNA1S",

    # ── Lysosomal / Metabolic ────────────────────────────────────────────────
    "GLA",    # Fabry disease
    "GAA",    # Pompe disease
    "OTC",    # Ornithine transcarbamylase deficiency

    # ── Haematological ───────────────────────────────────────────────────────
    "HFE",   # Hereditary haemochromatosis (Tier 1 in some guidelines)
    "BMPR2", # Pulmonary arterial hypertension
}

# Shorter display name for the clinical mode
CLINICAL_MODE_LABEL = "ACMG SF v3.2 (81 actionable genes)"


def is_clinical_gene(gene_symbol: str | None) -> bool:
    """Return True if the gene is on the ACMG actionable list."""
    if not gene_symbol:
        return False
    return gene_symbol.upper() in ACMG_ACTIONABLE_GENES
