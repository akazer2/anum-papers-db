"""Quick test script for citation parsing."""

from citation_parser import parse_citation

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
    "Slavkova, K. P., Patel, S. H., Cacini, Z., Kazerouni, A. S., Gardner, A. L., Yankeelov, T. E. & Hormuth, D. A. Mathematical modelling of the dynamics of image-informed tumor habitats in a murine model of glioma. Sci Rep 13, 2916 (2023).",
    "Partridge, S. C. & Kazerouni, A. S. Editorial for \"Contrasts Between Diffusion-Weighted Imaging and Dynamic Contrast-Enhanced MR in Diagnosing Malignancies of Breast Nonmass Enhancement Lesions Based on Morphologic Assessment\". Journal of Magnetic Resonance Imaging 58, 975–976 (2023).",
    "Shalom, E. S., Kim, H., van der Heijden, R. A., Ahmed, Z., Patel, R., Hormuth II, D. A., DiCarlo, J. C., Yankeelov, T. E., Sisco, N. J., Dortch, R. D., Stokes, A. M., Inglese, M., Grech-Sollars, M., Toschi, N., Sahoo, P., Singh, A., Verma, S. K., Rathore, D. K., Kazerouni, A. S., Partridge, S. C., … LoCastro, E., Paudyal, R., Wolansky, I. A., Shukla-Dave, A., Schouten, P., Gurney-Champion, O. J., Jiřík, R., Macíček, O., Bartoš, M., Vitouš, J., Das, A. B., Kim, S. G., Bokacheva, L., Mikheev, A., Rusinek, H., Berks, M., Hubbard Cristinacce, P. L., Little, R. A., Cheung, S., O'Connor, J. P. B., Parker, G. J. M., Moloney, B., LaViolette, P. S., Bobholz, S., Duenweg, S., Virostko, J., Laue, H. O., Sung, K., Nabavizadeh, A., Saligheh Rad, H., Hu, L. S., Sourbron, S., Bell, L. C. & Fathi Kazerooni, A. The ISMRM Open Science Initiative for Perfusion Imaging (OSIPI): Results from the OSIPI–Dynamic Contrast-Enhanced challenge. Magnetic Resonance in Medicine 1–19 (2023).",
    "DiCarlo, J. C., Jarrett, A. M., Kazerouni, A. S., Virostko, J., Sorace, A., Slavkova, K. P., Woodard, S., Avery, S., Patt, D., Goodgame, B. & Yankeelov, T. E. Analysis of simplicial complexes to determine when to sample for quantitative DCE MRI of the breast. Magnetic Resonance in Medicine 89, 1134–1150 (2023).",
    "Kazerouni, A. S., Rahbar, H. & Partridge, S. C. Is NME the Enemy of Breast DWI? European Journal of Radiology 110648 (2022). doi:10.1016/j.ejrad.2022.110648",
    "Kazerouni, A. S., Hormuth, D. A., Davis, T., Bloom, M. J., Mounho, S., Rahman, G., Virostko, J., Yankeelov, T. E. & Sorace, A. G. Quantifying Tumor Heterogeneity via MRI Habitats to Characterize Microenvironmental Alterations in HER2+ Breast Cancer. Cancers 14, 1837 (2022).",
    "Virostko, J., Sorace, A. G., Slavkova, K. P., Kazerouni, A. S., Jarrett, A. M., DiCarlo, J. C., Woodard, S., Avery, S., Goodgame, B., Patt, D. & Yankeelov, T. E. Quantitative multiparametric MRI predicts response to neoadjuvant therapy in the community setting. Breast Cancer Res 23, 110 (2021).",
    "Yang, J., Davis, T., Kazerouni, A. S., Chen, Y.-I., Bloom, M. J., Yeh, H.-C., Yankeelov, T. E. & Virostko, J. Longitudinal FRET Imaging of Glucose and Lactate Dynamics and Response to Therapy in Breast Cancer Cells. Mol Imaging Biol (2021).",
    "Jarrett, A. M., Kazerouni, A. S., Wu, C., Virostko, J., Sorace, A. G., DiCarlo, J. C., Hormuth, D. A., Ekrut, D. A., Patt, D., Goodgame, B., Avery, S. & Yankeelov, T. E. Quantitative magnetic resonance imaging and tumor forecasting of breast cancer patients in the community setting. Nat Protoc 1–30 (2021).",
    "Slavkova, K. P., DiCarlo, J. C., Kazerouni, A. S., Virostko, J., Sorace, A. G., Patt, D., Goodgame, B. & Yankeelov, T. E. Characterizing errors in pharmacokinetic parameters from analyzing quantitative abbreviated DCE-MRI data in breast cancer. Tomography 7, 253–267 (2021).",
    "Kazerouni, A. S.*, Gadde, M.*, Gardner, A., Hormuth, D. A., Jarrett, A. M., Johnson, K. E., Lima, E. A. B. F., Lorenzo, G., Phillips, C., Brock, A. & Yankeelov, T. E. Integrating quantitative assays with biologically based mathematical modeling for predictive oncology. iScience 23, 101807 (2020).",
    "Jarrett, A. M., Hormuth, D. A., Wu, C., Kazerouni, A. S., Ekrut, D. A., Virostko, J., Sorace, A. G., DiCarlo, J. C., Kowalski, J., Patt, D., Goodgame, B., Avery, S. & Yankeelov, T. E. Evaluating patient-specific neoadjuvant regimens for breast cancer via a mathematical model constrained by quantitative magnetic resonance imaging data. Neoplasia 22, 820–830 (2020).",
    "Syed, A. K., Whisenant, J. G., Barnes, S. L., Sorace, A. G. & Yankeelov, T. E. Multiparametric analysis of longitudinal quantitative MRI data to identify distinct tumor habitats in preclinical models of breast cancer. Cancers 12, 1682 (2020).",
    "Gadde, M., Phillips, C., Ghousifam, N., Sorace, A. G., Wong, E., Krishnamurthy, S., Syed, A. K., Rahal, O., Yankeelov, T. E., Woodward, W. A. & Rylander, M. N. In vitro vascularized tumor platform for modeling tumor‐vasculature interactions of inflammatory breast cancer. Biotechnology and Bioengineering bit.27487 (2020). doi:10.1002/bit.27487",
    "Bloom, M. J., Jarrett, A. M., Triplett, T. A., Syed, A. K., Davis, T., Yankeelov, T. E. & Sorace, A. G. Anti-HER2 induced myeloid cell alterations correspond with increasing vascular maturation in a murine model of HER2+ breast cancer. BMC Cancer 20, 359 (2020).",
    "Syed, A. K., Woodall, R., Whisenant, J. G., Yankeelov, T. E. & Sorace, A. G. Characterizing trastuzumab-induced alterations in intratumoral heterogeneity with quantitative imaging and immunohistochemistry in HER2+ breast cancer. Neoplasia 21, 17–29 (2019).",
    "Quach, M. E., Syed, A. K. & Li, R. A Uniform Shear Assay for Human Platelet and Cell Surface Receptors via Cone-plate Viscometry. JoVE (Journal of Visualized Experiments) e59704 (2019). doi:10.3791/59704",
    "Jarrett, A. M., Bloom, M. J., Godfrey, W., Syed, A. K., Ekrut, D. A., Ehrlich, L. I., Yankeelov, T. E. & Sorace, A. G. Mathematical modelling of trastuzumab-induced immune response in an in vivo murine model of HER2+ breast cancer. Math Med Biol 36, 381–410 (2019).",
    "Quach, M. E., Dragovich, M. A., Chen, W., Syed, A. K., Cao, W., Liang, X., Deng, W., De Meyer, S. F., Zhu, G., Peng, J., Ni, H., Bennett, C. M., Hou, M., Ware, J., Deckmyn, H., Zhang, X. F. & Li, R. Fc-independent immune thrombocytopenia via mechanomolecular signaling in platelets. Blood 131, 787–796 (2018).",
    "Zhang, J., Rector, J., Lin, J. Q., Young, J. H., Sans, M., Katta, N., Giese, N., Yu, W., Nagi, C., Suliburk, J., Liu, J., Bensussan, A., DeHoog, R. J., Garza, K. Y., Ludolph, B., Sorace, A. G., Syed, A. K., Zahedivash, A., Milner, T. E. & Eberlin, L. S. Nondestructive tissue analysis for ex vivo and in vivo cancer diagnosis using a handheld mass spectrometry system. Science Translational Medicine 9, (2017).",
    "Sorace, A. G., Syed, A. K., Barnes, S. L., Quarles, C. C., Sanchez, V., Kang, H. & Yankeelov, T. E. Quantitative [18F]FMISO PET Imaging shows reduction of hypoxia following trastuzumab in a murine model of HER2+ breast cancer. Mol Imaging Biol 19, 130–137 (2017).",
    "Sorace, A. G., Harvey, S., Syed, A. K. & Yankeelov, T. E. Imaging considerations and interprofessional opportunities in the care of breast cancer patients in the neoadjuvant setting. Seminars in Oncology Nursing 33, 425–439 (2017).",
    "Deng, W., Wang, Y., Druzak, S. A., Healey, J. F., Syed, A. K., Lollar, P. & Li, R. A discontinuous autoinhibitory module masks the A1 domain of von Willebrand factor. Journal of Thrombosis and Haemostasis 15, 1867–1877 (2017).",
    "Liang, X., Syed, A. K., Russell, S. R., Ware, J. & Li, R. Dimerization of glycoprotein Ibα is not sufficient to induce platelet clearance. Journal of Thrombosis and Haemostasis 14, 381–386 (2016).",
    "Deng, W., Xu, Y., Chen, W., Paul, D. S., Syed, A. K., Dragovich, M. A., Liang, X., Zakas, P., Berndt, M. C., Di Paola, J., Ware, J., Lanza, F., Doering, C. B., Bergmeier, W., Zhang, X. F. & Li, R. Platelet clearance via shear-induced unfolding of a membrane mechanoreceptor. Nature Communications 7, 12863 (2016).",
    "Chen Wenchun, Liang Xin, Syed A. K., Jessup Paula, Church William R., Ware Jerry, Josephson Cassandra D. & Li Renhao. Inhibiting GPIbα shedding preserves post-transfusion recovery and hemostatic function of platelets after prolonged storage. Arteriosclerosis, Thrombosis, and Vascular Biology 36, 1821–1828 (2016).",
    "Ban, K., Wile, B., Cho, K.-W., Kim, S., Song, M.-K., Kim, S. Y., Singer, J., Syed, A. K., Yu, S. P., Wagner, M., Bao, G. & Yoon, Y. Non-genetic purification of ventricular cardiomyocytes from differentiating embryonic stem cells through molecular beacons targeting IRX-4. Stem Cell Reports 5, 1239–1249 (2015).",
]

print(f"Testing {len(citations)} citations...\n")
print("=" * 80)

success_count = 0
fail_count = 0
total_authors = 0

for i, citation in enumerate(citations, 1):
    result = parse_citation(citation)
    
    if result:
        authors = result.get('authors', [])
        title = result.get('title', 'N/A')
        year = result.get('year', 'N/A')
        venue = result.get('venue', 'N/A')
        
        print(f"\n{i}. ✅ SUCCESS")
        print(f"   Title: {title[:60]}...")
        print(f"   Year: {year}, Venue: {venue}")
        print(f"   Authors: {len(authors)}")
        if len(authors) > 0:
            print(f"   First 3: {', '.join(authors[:3])}")
            if len(authors) > 3:
                print(f"   ... and {len(authors) - 3} more")
        total_authors += len(authors)
        success_count += 1
    else:
        print(f"\n{i}. ❌ FAILED")
        print(f"   Citation: {citation[:80]}...")
        fail_count += 1

print("\n" + "=" * 80)
print(f"\nSUMMARY:")
print(f"  ✅ Success: {success_count}/{len(citations)} ({success_count/len(citations)*100:.1f}%)")
print(f"  ❌ Failed: {fail_count}/{len(citations)}")
print(f"  📊 Total authors extracted: {total_authors}")
print(f"  📊 Average authors per citation: {total_authors/success_count if success_count > 0 else 0:.1f}")

