"""Test script to determine which parsing method is used for each citation."""

import sys
from citation_parser import (
    GROBID_AVAILABLE, HABANERO_AVAILABLE, OPENALEX_AVAILABLE,
    parse_with_grobid, extract_doi, lookup_doi_metadata, 
    lookup_openalex, parse_citation_fallback, parse_citation
)

def test_citation(citation_text: str, index: int):
    """Test a single citation and report which method was used."""
    print(f"\n{'='*80}")
    print(f"Citation {index}:")
    print(f"{'='*80}")
    print(f"Text: {citation_text[:100]}...")
    print()
    
    # Track which methods are available
    print("Available parsers:")
    print(f"  GROBID: {'✓' if GROBID_AVAILABLE else '✗'}")
    print(f"  Crossref (habanero): {'✓' if HABANERO_AVAILABLE else '✗'}")
    print(f"  OpenAlex: {'✓' if OPENALEX_AVAILABLE else '✗'}")
    print()
    
    # Try GROBID first
    grobid_result = None
    if GROBID_AVAILABLE:
        try:
            grobid_result = parse_with_grobid(citation_text)
            if grobid_result:
                print("✓ GROBID: SUCCESS")
                print(f"  Title: {grobid_result.get('title', 'N/A')[:80]}")
                print(f"  DOI: {grobid_result.get('doi', 'N/A')}")
            else:
                print("✗ GROBID: Failed or no title")
        except Exception as e:
            print(f"✗ GROBID: Error - {e}")
    else:
        print("✗ GROBID: Not available")
    
    # Check for DOI
    doi = extract_doi(citation_text)
    if doi:
        print(f"✓ DOI found in text: {doi}")
        if HABANERO_AVAILABLE:
            try:
                crossref_result = lookup_doi_metadata(doi)
                if crossref_result:
                    print("✓ Crossref DOI lookup: SUCCESS")
                    print(f"  Title: {crossref_result.get('title', 'N/A')[:80]}")
                else:
                    print("✗ Crossref DOI lookup: No results")
            except Exception as e:
                print(f"✗ Crossref DOI lookup: Error - {e}")
    else:
        print("✗ No DOI found in text")
    
    # Test full parse_citation function
    print("\n--- Full parse_citation() result ---")
    try:
        result = parse_citation(citation_text)
        if result:
            print("✓ parse_citation: SUCCESS")
            print(f"  Title: {result.get('title', 'N/A')[:80]}")
            print(f"  Year: {result.get('year', 'N/A')}")
            print(f"  Venue: {result.get('venue', 'N/A')[:60] if result.get('venue') else 'N/A'}")
            print(f"  DOI: {result.get('doi', 'N/A')}")
            print(f"  Abstract: {'Yes' if result.get('abstract') else 'No'}")
            print(f"  URL: {'Yes' if result.get('url') else 'No'}")
            print(f"  Keywords: {'Yes' if result.get('keywords') else 'No'}")
            print(f"  Citation Count: {result.get('citation_count', 'N/A')}")
            
            # Infer which method was likely used
            print("\n--- Inferred parsing method ---")
            if result.get('abstract') or result.get('url') or result.get('citation_count'):
                if grobid_result and result.get('title') == grobid_result.get('title'):
                    print("→ Likely: GROBID + Crossref/OpenAlex enrichment")
                elif doi and result.get('doi') == doi:
                    print("→ Likely: Crossref DOI lookup")
                else:
                    print("→ Likely: GROBID + OpenAlex enrichment")
            elif grobid_result and result.get('title') == grobid_result.get('title'):
                print("→ Likely: GROBID only")
            else:
                print("→ Likely: Fallback regex parser")
        else:
            print("✗ parse_citation: Failed")
    except Exception as e:
        print(f"✗ parse_citation: Error - {e}")
        import traceback
        traceback.print_exc()

# Citations to test
citations = [
    "Kazerouni, A. S.*, Chen, Y. A.*, Phelps, M. D., Hippe, D. S., Youn, I., Lee, J. M., Partridge, S. C. & Rahbar, H. Time to Enhancement Measured From Ultrafast Dynamic Contrast-Enhanced MRI for Improved Breast Lesion Diagnosis. Journal of Breast Imaging wbae089 (2025). doi:10.1093/jbi/wbae089",
    "Oviedo, F., Kazerouni, A. S., Liznerski, P., Xu, Y., Hirano, M., Vandermeulen, R. A., Kloft, M., Blum, E., Alessio, A. M., Li, C. I., Weeks, W. B., Dodhia, R., Lavista Ferres, J. M., Rahbar, H. & Partridge, S. C. Cancer Detection in Breast MRI Screening via Explainable AI Anomaly Detection. Radiology 316, e241629 (2025).",
    "Park, V. Y., Hippe, D. S., Kazerouni, A. S., Biswas, D., Bryant, M. L., Li, I., Javid, S. H., Kilgore, M., Kim, J., Kim, A. G., Scheel, J. R., Lowry, K. P., Lam, D. L., Partridge, S. & Rahbar, H. Multiparametric breast MRI to problem-solve mammographically detected suspicious calcifications. European Journal of Radiology 112467 (2025).",
    "Slavkova, K. P., Kang, R., Kazerouni, A. S., Biswas, D., Belenky, V., Chitalia, R., Horng, H., Hirano, M., Xiao, J., Corsetti, R. L., Javid, S. H., Spell, D. W., Wolff, A. C., Sparano, J. A., Khan, S. A., Comstock, C. E., Romanoff, J., Gatsonis, C., Lehman, C. D., Partridge, S. C., Steingrimsson, J., Kontos, D. & Rahbar, H. MRI-based Radiomic Features for Risk Stratification of Ductal Carcinoma in Situ in a Multicenter Setting (ECOG-ACRIN E4112 Trial). Radiology 315, e241628 (2025).",
    "Javid, S. H., Kazerouni, A. S., Hippe, D. S., Hirano, M., Schnuck-Olapo, J., Biswas, D., Bryant, M. L., Li, I., Xiao, J., Kim, A. G., Guo, A., Dontchos, B., Kilgore, M., Kim, J., Partridge, S. C. & Rahbar, H. Preoperative MRI to Predict Upstaging of DCIS to Invasive Cancer at Surgery. Ann Surg Oncol (2025). doi:10.1245/s10434-024-16837-x",
    "Moloney, B., Li, X., Hirano, M., Saad Eddin, A., Lim, J. Y., Biswas, D., Kazerouni, A. S., Tudorica, A., Li, I., Bryant, M. L., Wille, C., Pyle, C., Rahbar, H., Hsieh, S. K., Rice-Stitt, T. L., Dintzis, S. M., Bashir, A., Hobbs, E., Zimmer, A., Specht, J. M., Phadke, S., Fleege, N., Holmes, J. H., Partridge, S. C. & Huang, W. Initial experience in implementing quantitative DCE-MRI to predict breast cancer therapy response in a multi-center and multi-vendor platform setting. Front. Oncol. 14, (2024).",
    "Youn, I., Biswas, D., Hippe, D. S., Winter, A. M., Kazerouni, A. S., Javid, S. H., Lee, J. M., Rahbar, H. & Partridge, S. C. Diagnostic Performance of Point-of-Care Apparent Diffusion Coefficient Measures to Reduce Biopsy in Breast Lesions at MRI: Clinical Validation. Radiology 310, e232313 (2024).",
    "Li, W., Partridge, S. C., Newitt, D. C., Steingrimsson, J., Marques, H. S., Bolan, P. J., Hirano, M., Bearce, B. A., Kalpathy-Cramer, J., Boss, M. A., Teng, X., Zhang, J., Cai, J., Kontos, D., Cohen, E. A., Mankowski, W. C., Liu, M., Ha, R., Pellicer-Valero, O. J., Maier-Hein, K., Rabinovici-Cohen, S., Tlusty, T., Ozery-Flato, M., Parekh, V. S., Jacobs, M. A., Yan, R., Sung, K., Kazerouni, A. S., DiCarlo, J. C., Yankeelov, T. E., Chenevert, T. L. & Hylton, N. M. Breast Multiparametric MRI for Prediction of Neoadjuvant Chemotherapy Response in Breast Cancer: The BMMR2 Challenge. Radiology: Imaging Cancer 6, e230033 (2024).",
    "Kazerouni, A. S., Peterson, L. M., Jenkins, I., Novakova-Jiresova, A., Linden, H. M., Gralow, J. R., Hockenbery, D. M., Mankoff, D. A., Porter, P. L., Partridge, S. C. & Specht, J. M. Multimodal prediction of neoadjuvant treatment outcome by serial FDG PET and MRI in women with locally advanced breast cancer. Breast Cancer Res 25, 138 (2023).",
    "Kennedy, L. C., Kazerouni, A. S., Chau, B., Biswas, D., Alvarez, R., Durenberger, G., Dintzis, S. M., Stanton, S. E., Partridge, S. C. & Gadi, V. Associations of Multiparametric Breast MRI Features, Tumor-Infiltrating Lymphocytes, and Immune Gene Signature Scores Following a Single Dose of Trastuzumab in HER2-Positive Early-Stage Breast Cancer. Cancers 15, 4337 (2023).",
]

if __name__ == "__main__":
    print("Testing citation parsing methods...")
    print(f"Total citations to test: {len(citations)}")
    
    for i, citation in enumerate(citations, 1):
        test_citation(citation, i)
        if i < len(citations):
            print("\n" + "="*80 + "\n")
    
    print("\n" + "="*80)
    print("Summary:")
    print("="*80)
    print(f"GROBID available: {GROBID_AVAILABLE}")
    print(f"Crossref available: {HABANERO_AVAILABLE}")
    print(f"OpenAlex available: {OPENALEX_AVAILABLE}")

