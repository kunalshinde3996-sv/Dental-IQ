"""Reference vocabularies for the synthetic seed.

Everything here is SYNTHETIC and only roughly realistic. Names are common Goan
first-name/surname combinations generated at random and do not refer to real
people. The distributions are hand-tuned to look plausible for a teaching
hospital at Bambolim (Tiswadi). They are NOT epidemiological estimates.
"""
from app.models.enums import Department, StudentYear, Taluka, ToothCondition

# --- People -----------------------------------------------------------------

MALE_FIRST = [
    "Rohan", "Siddhesh", "Pratik", "Sanket", "Akshay", "Vishal", "Omkar", "Gaurav",
    "Joel", "Ryan", "Clinton", "Savio", "Anthony", "Francis", "Melwyn", "Agnelo",
    "Imran", "Sameer", "Rajesh", "Mahesh", "Suresh", "Ganesh", "Dattaram", "Vinayak",
    "Prakash", "Nilesh", "Kunal", "Aditya", "Yash", "Shubham",
]
FEMALE_FIRST = [
    "Priya", "Sneha", "Pooja", "Shruti", "Neha", "Siddhi", "Rutuja", "Anjali",
    "Maria", "Sharon", "Fiona", "Glenda", "Leena", "Rosy", "Carol", "Sweedal",
    "Ayesha", "Farzana", "Sunita", "Vaishali", "Kavita", "Manisha", "Shobha", "Laxmi",
    "Sayali", "Tanvi", "Riya", "Aarti", "Gauri", "Pranali",
]
SURNAMES = [
    "Naik", "Gaonkar", "Kamat", "Shirodkar", "Parab", "Dessai", "Sawant", "Gauns",
    "Velip", "Prabhu", "Kerkar", "Volvoikar", "Mandrekar", "Haldankar", "Borkar",
    "Fernandes", "D'Souza", "Rodrigues", "Pereira", "Colaco", "Dias", "Furtado",
    "Menezes", "Costa", "Gomes", "Shaikh", "Khan", "Bandodkar", "Salgaonkar", "Kudchadkar",
]

# Relative patient catchment weights. Bambolim is in Tiswadi, so nearby talukas
# send more patients and the remote talukas fewer.
TALUKA_WEIGHTS: dict[Taluka, float] = {
    Taluka.tiswadi: 18, Taluka.bardez: 16, Taluka.salcete: 14, Taluka.ponda: 12,
    Taluka.mormugao: 10, Taluka.bicholim: 7, Taluka.pernem: 6, Taluka.quepem: 5,
    Taluka.sattari: 4, Taluka.sanguem: 3, Taluka.canacona: 3, Taluka.dharbandora: 2,
}
#: Talukas treated as predominantly rural (higher smokeless-tobacco use in the synthetic model).
RURAL_TALUKAS = {Taluka.sattari, Taluka.sanguem, Taluka.canacona, Taluka.dharbandora,
                 Taluka.quepem, Taluka.pernem, Taluka.bicholim}

# --- Academic ---------------------------------------------------------------

BATCH_BY_YEAR: dict[StudentYear, str] = {
    StudentYear.bds1: "2026-31",
    StudentYear.bds2: "2025-30",
    StudentYear.bds3: "2024-29",
    StudentYear.bds4: "2023-28",
    StudentYear.intern: "2022-27",
}

SUBJECTS_BY_YEAR: dict[StudentYear, list[str]] = {
    StudentYear.bds1: ["General Anatomy", "General Physiology", "Biochemistry",
                       "Dental Anatomy & Oral Histology"],
    StudentYear.bds2: ["General Pathology & Microbiology", "Pharmacology", "Dental Materials",
                       "Pre-clinical Prosthodontics", "Pre-clinical Conservative Dentistry"],
    StudentYear.bds3: ["General Medicine", "General Surgery", "Oral Pathology"],
    StudentYear.bds4: ["Oral Medicine & Radiology", "Conservative Dentistry & Endodontics",
                       "Periodontology", "Prosthodontics", "Oral & Maxillofacial Surgery",
                       "Pedodontics", "Orthodontics", "Public Health Dentistry"],
    StudentYear.intern: [],
}

# Required approved cases per department for each clinical year (synthetic, mid-year targets).
QUOTAS: dict[StudentYear, dict[Department, int]] = {
    StudentYear.bds3: {
        Department.oral_medicine: 12, Department.conservative: 8, Department.endodontics: 2,
        Department.periodontics: 8, Department.prosthodontics: 4, Department.oral_surgery: 8,
        Department.pedodontics: 5, Department.orthodontics: 2,
    },
    StudentYear.bds4: {
        Department.oral_medicine: 12, Department.conservative: 10, Department.endodontics: 4,
        Department.periodontics: 8, Department.prosthodontics: 5, Department.oral_surgery: 10,
        Department.pedodontics: 6, Department.orthodontics: 3,
    },
    StudentYear.intern: {
        Department.oral_medicine: 10, Department.conservative: 10, Department.endodontics: 5,
        Department.periodontics: 8, Department.prosthodontics: 6, Department.oral_surgery: 12,
        Department.pedodontics: 6, Department.orthodontics: 3,
    },
}

FACULTY_DESIGNATIONS = ["Professor & HOD", "Reader", "Senior Lecturer", "Lecturer"]

# --- Clinical vocabularies -------------------------------------------------

# Share of cases per department (adult patients). Children are routed mainly to Pedodontics.
DEPARTMENT_WEIGHTS: dict[Department, float] = {
    Department.oral_medicine: 24, Department.conservative: 18, Department.endodontics: 8,
    Department.periodontics: 15, Department.prosthodontics: 9, Department.oral_surgery: 15,
    Department.pedodontics: 7, Department.orthodontics: 4,
}

# Each template: (chief complaint, diagnosis, procedure, [(condition, surfaces, treatment)], n_teeth range)
CaseTemplate = tuple[str, str, str, list[tuple[ToothCondition, str | None, str | None]], tuple[int, int]]

TEMPLATES: dict[Department, list[CaseTemplate]] = {
    Department.oral_medicine: [
        ("Routine dental check-up", "Generalised chronic gingivitis with dental caries",
         "Comprehensive oral examination and charting; referred", [(ToothCondition.caries, "O", None)], (1, 4)),
        ("Pain in lower back tooth", "Chronic irreversible pulpitis", "Examination, IOPA radiograph; referred to Endodontics",
         [(ToothCondition.caries, "OD", "Referred for RCT")], (1, 1)),
        ("Burning sensation in mouth on eating spicy food", "Oral submucous fibrosis (OSMF), Stage II",
         "Examination, mouth-opening measurement, habit cessation counselling", [], (0, 0)),
        ("White patch on inner cheek", "Homogeneous leukoplakia, left buccal mucosa",
         "Examination, toluidine blue staining, referred for biopsy", [(ToothCondition.lesion, None, "Biopsy advised")], (1, 1)),
        ("Ulcer in mouth not healing for 3 weeks", "Non-healing ulcer, suspicious for malignancy",
         "Examination, urgent referral to Oral Surgery for incisional biopsy",
         [(ToothCondition.lesion, None, "Urgent biopsy referral")], (1, 1)),
        ("Swelling of gums and bad breath", "Chronic generalised periodontitis",
         "Examination, OPG advised; referred to Periodontics", [(ToothCondition.mobility, None, None)], (1, 3)),
        ("Routine dental check-up", "Plaque-induced gingivitis; dentition otherwise sound",
         "Comprehensive oral examination; oral hygiene instructions", [], (0, 0)),
    ],
    Department.conservative: [
        ("Food lodgement in back tooth", "Dentinal caries", "Class I composite restoration",
         [(ToothCondition.filled, "O", "Composite restoration")], (1, 2)),
        ("Sensitivity to cold", "Class II dentinal caries", "Class II GIC/composite restoration",
         [(ToothCondition.filled, "MO", "Composite restoration")], (1, 2)),
        ("Black spots on front teeth", "Class III caries", "Class III composite restoration",
         [(ToothCondition.filled, "M", "Composite restoration")], (1, 2)),
        ("Broken old filling", "Secondary caries under amalgam", "Removal and re-restoration",
         [(ToothCondition.filled, "OD", "Re-restoration")], (1, 1)),
    ],
    Department.endodontics: [
        ("Severe throbbing pain at night", "Symptomatic irreversible pulpitis", "Root canal treatment",
         [(ToothCondition.rct, None, "RCT completed")], (1, 1)),
        ("Swelling and pus near tooth", "Chronic apical abscess", "Root canal treatment with drainage",
         [(ToothCondition.rct, None, "RCT - multiple visits")], (1, 1)),
        ("Discoloured front tooth after fall", "Pulp necrosis, 11", "Root canal treatment and bleaching",
         [(ToothCondition.rct, None, "RCT completed")], (1, 1)),
    ],
    Department.periodontics: [
        ("Bleeding gums while brushing", "Plaque-induced generalised gingivitis", "Full-mouth scaling and polishing",
         [], (0, 0)),
        ("Loose teeth and gum recession", "Generalised periodontitis, Stage III Grade B",
         "Scaling, root planing; flap surgery planned", [(ToothCondition.mobility, None, "SRP")], (1, 4)),
        ("Stains on teeth", "Extrinsic tobacco stains with gingivitis", "Scaling, polishing, tobacco cessation advice",
         [], (0, 0)),
    ],
    Department.prosthodontics: [
        ("Missing teeth, difficulty chewing", "Partially edentulous arch (Kennedy Class III)",
         "Removable partial denture fabrication", [(ToothCondition.missing, None, "RPD")], (1, 4)),
        ("All teeth missing", "Completely edentulous maxilla and mandible", "Complete denture fabrication",
         [(ToothCondition.missing, None, "Complete denture")], (6, 12)),
        ("Root canal treated tooth needs cap", "Endodontically treated tooth requiring full coverage",
         "PFM crown preparation and cementation", [(ToothCondition.crown, None, "PFM crown")], (1, 1)),
    ],
    Department.oral_surgery: [
        ("Pain in broken tooth", "Grossly decayed tooth, non-restorable", "Extraction under LA",
         [(ToothCondition.extraction_indicated, None, "Extraction")], (1, 2)),
        ("Pain and swelling behind last tooth", "Impacted mandibular third molar with pericoronitis",
         "Surgical removal of impacted tooth", [(ToothCondition.impacted, None, "Surgical extraction")], (1, 1)),
        ("Loose painful tooth", "Chronic periodontitis with grade III mobility", "Extraction under LA",
         [(ToothCondition.extraction_indicated, None, "Extraction")], (1, 1)),
        ("Referred for biopsy of oral lesion", "Oral lesion for histopathological evaluation",
         "Incisional biopsy under LA", [(ToothCondition.lesion, None, "Incisional biopsy")], (1, 1)),
    ],
    Department.pedodontics: [
        ("Child has pain in back tooth", "Early childhood caries", "Pulpotomy and stainless-steel crown",
         [(ToothCondition.caries, "O", "Pulpotomy + SS crown")], (1, 3)),
        ("Routine check-up for child", "Deep pits and fissures, sealant indicated", "Pit and fissure sealant application",
         [(ToothCondition.sound, "O", "Sealant")], (2, 4)),
        ("Child fell and broke front tooth", "Ellis Class II fracture of 11", "Composite build-up",
         [(ToothCondition.fractured, "I", "Composite build-up")], (1, 1)),
        ("Decayed milk teeth", "Multiple carious primary teeth", "Restorations and fluoride varnish",
         [(ToothCondition.filled, "O", "GIC restoration")], (2, 4)),
        ("Routine check-up for child", "Healthy dentition", "Oral hygiene instruction and fluoride varnish",
         [(ToothCondition.sound, None, "Fluoride varnish")], (2, 4)),
    ],
    Department.orthodontics: [
        ("Irregular front teeth", "Angle's Class I malocclusion with anterior crowding",
         "Records, study models; fixed appliance planned", [], (0, 0)),
        ("Forwardly placed upper teeth", "Angle's Class II div 1 malocclusion",
         "Records, cephalometric analysis; treatment planning", [], (0, 0)),
    ],
}

#: Probability that a patient has dental caries, by age (upper bound inclusive). Hand-tuned to
#: plausible Indian levels: about half of children, rising to roughly two-thirds of older adults.
CARIES_PREVALENCE_BY_AGE: list[tuple[int, float]] = [
    (12, 0.50), (17, 0.56), (34, 0.68), (49, 0.70), (64, 0.73), (200, 0.75),
]

#: Templates used for patients with current tobacco/gutkha habits (oral-medicine screening).
TOBACCO_LESION_TEMPLATE_INDEXES = (2, 3, 4)

REJECTION_REMARKS = [
    "Incomplete case history - medical history section missing.",
    "Diagnosis not supported by findings; re-examine and re-submit.",
    "Tooth charting incomplete; record all carious surfaces.",
    "Radiograph interpretation missing.",
    "Treatment plan sequence incorrect; discuss with supervisor.",
]
APPROVAL_REMARKS = [None, None, None, "Good work.", "Well documented.", "Satisfactory.",
                    "Good chairside manner.", "Neat restoration."]
