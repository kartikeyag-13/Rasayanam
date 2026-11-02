"""Curated health content: respiratory-health articles, local doctor/ENT
directory, and herbal teas & home remedies.

Disclaimer: the directory is a curated discovery aid, not a referral service —
users must verify timings/availability before visiting.
"""

from __future__ import annotations

# ------------------------------------------------------------------ articles --
ARTICLES: list[dict] = [
    {
        "id": "who-health-impacts",
        "title": "Health impacts of air pollution",
        "source": "World Health Organization (WHO)",
        "url": "https://www.who.int/teams/environment-climate-change-and-health/air-quality-energy-and-health/health-impacts",
        "tag": "Overview",
        "summary": "WHO explains how short-term exposure to particulate matter reduces lung function, worsens asthma and triggers respiratory infections — and how long-term exposure drives chronic obstructive pulmonary disease and lung cancer.",
        "why_it_matters": "This is the global baseline for understanding why an AQI above 200 is not just 'haze' — it is a measurable insult to lung tissue.",
    },
    {
        "id": "who-topic",
        "title": "Air pollution — health topic",
        "source": "World Health Organization (WHO)",
        "url": "https://www.who.int/health-topics/air-pollution",
        "tag": "Overview",
        "summary": "WHO's hub on air pollution: 7 million premature deaths a year are linked to air pollution, with households and ambient (outdoor) pollution both implicated.",
        "why_it_matters": "Puts Diwali-scale pollution spikes into global context — short peaks sit on top of a year-round exposure burden.",
    },
    {
        "id": "epa-pm-respiratory",
        "title": "Particle pollution and respiratory effects",
        "source": "United States EPA",
        "url": "https://www.epa.gov/pmcourse/particle-pollution-and-respiratory-effects",
        "tag": "PM2.5 / PM10",
        "summary": "Evidence review of how fine particles penetrate deep into the alveoli: cough, wheeze, airway inflammation, asthma attacks, reduced lung function and increased respiratory infections.",
        "why_it_matters": "PM2.5 is the pollutant that dominates Diwali nights — this explains the mechanism behind the numbers on your dashboard.",
    },
    {
        "id": "pmc-airway-diseases",
        "title": "Air pollution and chronic airway diseases: what should people do?",
        "source": "PMC / NIH (Jiang et al., 2016)",
        "url": "https://pmc.ncbi.nlm.nih.gov/articles/PMC4740163/",
        "tag": "Research",
        "summary": "Peer-reviewed review of how air pollution induces acute exacerbations of COPD, new-onset asthma and rising respiratory morbidity/mortality — plus practical protective measures.",
        "why_it_matters": "The research backing for our health advisories: masks, purifiers, avoiding exertion on high-AQI days.",
    },
    {
        "id": "lung-sota",
        "title": "State of the Air — Health risks",
        "source": "American Lung Association",
        "url": "https://www.lung.org/research/sota/health-risks",
        "tag": "Research",
        "summary": "Large-population studies linking air pollution to death from cardiovascular and respiratory causes — heart disease, stroke, influenza and pneumonia — even at pollution levels below current standards.",
        "why_it_matters": "High AQI is not only a lung problem: it stresses the heart too, which matters for elderly family members during Diwali week.",
    },
    {
        "id": "cpcb-aqi",
        "title": "National Air Quality Index — how AQI is computed",
        "source": "Central Pollution Control Board (CPCB), India",
        "url": "https://cpcb.nic.in/",
        "tag": "Indian standards",
        "summary": "The Indian AQI framework converts available pollutant concentrations into sub-indices, then uses the highest valid sub-index to describe air quality. CPCB's full framework covers more pollutant species than the five currently available to Rasayanam.",
        "why_it_matters": "Rasayanam applies CPCB concentration breakpoints to its available CAMS pollutants. Its gridded estimates are useful for context, but are not official CPCB reference-monitor AQI readings.",
    },
    {
        "id": "caqm-grap",
        "title": "Commission for Air Quality Management (CAQM) — GRAP measures for NCR",
        "source": "CAQM, Government of India",
        "url": "https://caqm.gov.in/",
        "tag": "Indian standards",
        "summary": "The Graded Response Action Plan that kicks in as AQI crosses stage thresholds in Delhi-NCR: construction bans, truck restrictions, school adjustments and firecracker orders around Diwali.",
        "why_it_matters": "Explains the official actions likely to trigger at the forecast AQI levels shown in the prediction section.",
    },
]

# ------------------------------------------------------------------- doctors --
# Curated directory of hospitals/clinics with ENT & respiratory care in the
# cities covered by our monitoring stations. Verify details before visiting.
DOCTORS: list[dict] = [
    # ---- New Delhi ----
    {
        "id": "aiims-delhi",
        "name": "All India Institute of Medical Sciences (AIIMS)",
        "city": "New Delhi",
        "area": "Ansari Nagar",
        "type": "Government Super-specialty",
        "specialties": ["ENT (Otorhinolaryngology)", "Pulmonology", "Cardiology", "Emergency"],
        "focus": "Dedicated Dept. of Otorhinolaryngology & Head-Neck Surgery and respiratory medicine clinics; national reference centre.",
        "website": "https://www.aiims.edu",
    },
    {
        "id": "safdarjung",
        "name": "Safdarjung Hospital (VMMC & Safdarjung Hospital)",
        "city": "New Delhi",
        "area": "Safdarjung",
        "type": "Government Tertiary",
        "specialties": ["ENT", "Pulmonology", "Emergency Medicine"],
        "focus": "Large government hospital with ENT OPD, chest medicine department and 24×7 emergency — close to the Safdarjung monitoring station.",
        "website": "https://vmmc-sjh.nic.in",
    },
    {
        "id": "gangaram",
        "name": "Sir Ganga Ram Hospital",
        "city": "New Delhi",
        "area": "Rajinder Nagar",
        "type": "Private Multispecialty",
        "specialties": ["ENT", "Pulmonology", "Allergy & Immunology"],
        "focus": "Established ENT and allergy/asthma services; well-known respiratory department.",
        "website": "https://sgrh.com",
    },
    {
        "id": "blk-max",
        "name": "BLK-Max Super Speciality Hospital",
        "city": "New Delhi",
        "area": "Pusa Road",
        "type": "Private Multispecialty",
        "specialties": ["ENT (Head & Neck Surgery)", "Pulmonology"],
        "focus": "ENT head-neck surgery and pulmonary medicine units.",
        "website": "https://blkhospital.com",
    },
    {
        "id": "max-saket",
        "name": "Max Super Speciality Hospital",
        "city": "New Delhi",
        "area": "Saket",
        "type": "Private Multispecialty",
        "specialties": ["ENT", "Pulmonology"],
        "focus": "ENT and respiratory care with multiple OPD slots across the week.",
        "website": "https://maxhealthcare.in",
    },
    {
        "id": "mamc-lok-nayak",
        "name": "Maulana Azad Medical College & Lok Nayak Hospital",
        "city": "New Delhi",
        "area": "Bahadur Shah Zafar Marg",
        "type": "Government Medical College",
        "specialties": ["ENT", "Pulmonology", "Emergency"],
        "focus": "Government teaching hospital with ENT and chest departments; casualty services.",
        "website": None,
    },
    # ---- Gurugram ----
    {
        "id": "medanta",
        "name": "Medanta – The Medicity",
        "city": "Gurugram",
        "area": "Sector 38",
        "type": "Private Multispecialty",
        "specialties": ["ENT", "Pulmonology", "Critical Care"],
        "focus": "ENT institute and respiratory/internal medicine care; large OPD.",
        "website": "https://medanta.org",
    },
    {
        "id": "fortis-gurugram",
        "name": "Fortis Memorial Research Institute (FMRI)",
        "city": "Gurugram",
        "area": "Sector 44",
        "type": "Private Multispecialty",
        "specialties": ["ENT", "Pulmonology"],
        "focus": "ENT and pulmonary medicine with sleep-disorder breathing services.",
        "website": "https://fortishealthcare.com",
    },
    {
        "id": "artemis",
        "name": "Artemis Hospital",
        "city": "Gurugram",
        "area": "Sector 51",
        "type": "Private Multispecialty",
        "specialties": ["ENT", "Pulmonology"],
        "focus": "Multispecialty hospital with ENT & head-neck and respiratory departments.",
        "website": None,
    },
    # ---- Noida ----
    {
        "id": "gims-greater-noida",
        "name": "Government Institute of Medical Sciences (GIMS)",
        "city": "Noida",
        "area": "Greater Noida",
        "type": "Government Medical College",
        "specialties": ["ENT", "Pulmonology", "Emergency"],
        "focus": "Government teaching hospital with ENT OPD and general chest medicine.",
        "website": None,
    },
    {
        "id": "kailash-noida",
        "name": "Kailash Hospital",
        "city": "Noida",
        "area": "Sector 27",
        "type": "Private Multispecialty",
        "specialties": ["ENT", "Pulmonology"],
        "focus": "Multispecialty chain hospital with ENT and respiratory OPDs.",
        "website": None,
    },
    {
        "id": "yatharth-noida",
        "name": "Yatharth Hospital & Trauma Centre",
        "city": "Noida",
        "area": "Sector 110 / Greater Noida West",
        "type": "Private Multispecialty",
        "specialties": ["ENT", "Pulmonology", "Emergency"],
        "focus": "Hospital with ENT & 24×7 emergency covering Noida expressway belt.",
        "website": None,
    },
    # ---- Ambala ----
    {
        "id": "civil-ambala",
        "name": "Civil Hospital, Ambala",
        "city": "Ambala",
        "area": "Ambala City",
        "type": "Government District Hospital",
        "specialties": ["ENT", "General Medicine"],
        "focus": "District hospital ENT OPD run by the Civil Surgeon's office — the local public option for basic ENT care.",
        "website": None,
    },
    # ---- Hisar ----
    {
        "id": "mamc-agroha",
        "name": "Maharaja Agrasen Medical College & Hospital",
        "city": "Hisar",
        "area": "Agroha",
        "type": "Government Medical College",
        "specialties": ["ENT", "Pulmonology", "Emergency"],
        "focus": "Teaching hospital for the Hisar region with ENT and chest departments.",
        "website": None,
    },
    {
        "id": "civil-hisar",
        "name": "Civil Hospital, Hisar",
        "city": "Hisar",
        "area": "Hisar City",
        "type": "Government District Hospital",
        "specialties": ["ENT", "General Medicine"],
        "focus": "District-level public hospital with ENT OPD services.",
        "website": None,
    },
    # ---- Amritsar ----
    {
        "id": "gmc-amritsar",
        "name": "Government Medical College & Hospital, Amritsar",
        "city": "Amritsar",
        "area": "Green Avenue Road",
        "type": "Government Medical College",
        "specialties": ["ENT (Otorhinolaryngology)", "Pulmonology", "Emergency"],
        "focus": "Major government teaching hospital for Punjab's Majha region; full ENT department.",
        "website": None,
    },
    {
        "id": "sgrd-amritsar",
        "name": "Sri Guru Ram Das Institute of Medical Sciences & Research",
        "city": "Amritsar",
        "area": "Model Town",
        "type": "Private Trust Teaching",
        "specialties": ["ENT", "Pulmonology"],
        "focus": "Trust-run teaching hospital with ENT & respiratory medicine services.",
        "website": None,
    },
    # ---- Ludhiana ----
    {
        "id": "cmc-ludhiana",
        "name": "Christian Medical College & Hospital (CMC)",
        "city": "Ludhiana",
        "area": "Brown Road",
        "type": "Private Trust Teaching",
        "specialties": ["ENT", "Pulmonology"],
        "focus": "Long-established teaching hospital with ENT and pulmonary departments.",
        "website": None,
    },
    {
        "id": "dmch-ludhiana",
        "name": "Dayanand Medical College & Hospital (DMCH)",
        "city": "Ludhiana",
        "area": "Tagore Nagar",
        "type": "Private Trust Teaching",
        "specialties": ["ENT", "Pulmonology", "Emergency"],
        "focus": "Major private teaching hospital with ENT & chest medicine units.",
        "website": None,
    },
    {
        "id": "civil-ludhiana",
        "name": "Civil Hospital, Ludhiana",
        "city": "Ludhiana",
        "area": "Civil Lines",
        "type": "Government District Hospital",
        "specialties": ["ENT", "General Medicine"],
        "focus": "Public district hospital ENT OPD for the Ludhiana district.",
        "website": None,
    },
]

# ------------------------------------------------------------------- remedies --
REMEDIES: list[dict] = [
    {
        "id": "tulsi-adrak-tea",
        "name": "Tulsi–Adrak Tea",
        "hindi_name": "तुलसी–अदरक की चाय",
        "category": "Herbal tea",
        "ingredients": ["8–10 tulsi leaves", "1-inch ginger (grated)", "1 cup water", "honey to taste", "1 squeeze of lemon"],
        "benefits": "A warm, aromatic drink that may provide temporary throat comfort and hydration. It has not been shown to prevent or treat pollution-related lung injury.",
        "when": "2–3 cups a day on high-AQI days, especially after coming indoors.",
        "caution": "No honey for infants under 1 year. Go easy if you have acid reflux.",
    },
    {
        "id": "haldi-doodh",
        "name": "Haldi Doodh (Golden Milk)",
        "hindi_name": "हल्दी दूध",
        "category": "Home remedy",
        "ingredients": ["½ tsp turmeric", "A pinch of black pepper", "1 cup warm milk (or plant milk)"],
        "benefits": "A traditional warm milk beverage. Culinary turmeric is not a proven treatment for cough, chest congestion or air-pollution exposure.",
        "when": "Once at bedtime through Diwali–winter season.",
        "caution": "Skip if you are lactose intolerant or on blood-thinning medication — ask your doctor first.",
    },
    {
        "id": "honey-lemon-ginger",
        "name": "Shehad–Nimbu–Adrak",
        "hindi_name": "शहद–नींबू–अदरक",
        "category": "Home remedy",
        "ingredients": ["1 tbsp honey", "Half lemon", "Thin ginger slices", "Warm water"],
        "benefits": "A warm drink that may temporarily soothe throat irritation; honey should not be given to infants under one year.",
        "when": "At the first sign of throat irritation or dry cough — 2× a day.",
        "caution": "Add honey only after the water cools below ~60 °C; not for infants <1 year.",
    },
    {
        "id": "mulethi-water",
        "name": "Mulethi Ka Paani",
        "hindi_name": "मुलेठी का पानी",
        "category": "Home remedy",
        "ingredients": ["No DIY oral preparation recommended; consult a clinician before use."],
        "benefits": "Licorice has traditional use for throat discomfort, but oral use carries clinically relevant risks and should not be self-prescribed.",
        "when": "Once or twice a day when the throat feels hoarse or phlegm sticks.",
        "caution": "Avoid in hypertension, pregnancy or kidney disease without consulting a doctor — licorice can raise blood pressure.",
    },
    {
        "id": "saline-gargle",
        "name": "Warm Saline Gargles",
        "hindi_name": "नमक के गरारे",
        "category": "Self-care",
        "ingredients": ["½ tsp salt", "1 cup lukewarm water"],
        "benefits": "A simple salt-water gargle may temporarily soothe a scratchy throat. It does not remove particles from the lungs.",
        "when": "2–3 times a day, and immediately after prolonged outdoor exposure.",
        "caution": "Use lukewarm, never hot water. Spit it out; do not swallow.",
    },
    {
        "id": "steam-inhalation",
        "name": "Steam Inhalation (Ajwain / Eucalyptus)",
        "hindi_name": "भाप लेना",
        "category": "Self-care",
        "ingredients": ["A comfortably warm shower or commercially designed humidifier", "Ready-made sterile saline spray (optional)"],
        "benefits": "Bowl-based steam inhalation has limited evidence of benefit and creates a scald risk; safer alternatives are described on the detail page.",
        "when": "Once daily in the evening during heavy pollution; extra dose when congested.",
        "caution": "8–10 minutes max, keep a safe distance from the water. Not for children under 6 (burn risk); stop if it triggers wheezing.",
    },
    {
        "id": "kaadha",
        "name": "Kali Mirch–Tulsi Kaadha",
        "hindi_name": "काली मिर्च काढ़ा",
        "category": "Herbal tea",
        "ingredients": ["5–6 tulsi leaves", "4–5 black peppercorns", "½ tsp turmeric", "1-inch ginger", "1 cup water (reduced to half)"],
        "benefits": "A mild spiced infusion may be enjoyed as a beverage if tolerated. It is not proven to boost immunity or protect against pollution.",
        "when": "Once a day, morning or evening, during Diwali week.",
        "caution": "Strong — avoid on an empty stomach if you have gastritis. Skip for small children.",
    },
    {
        "id": "giloy-kadha",
        "name": "Giloy (Guduchi) Kadha",
        "hindi_name": "गिलोय काढ़ा",
        "category": "Herbal tea",
        "ingredients": ["No DIY ingredients or self-dosing instructions recommended."],
        "benefits": "Giloy is a medicinal herb with potential risks; this project does not recommend unsupervised home use or claim pollution-related benefit.",
        "when": "Once daily for a week around Diwali.",
        "caution": "Consult your doctor if you are pregnant, diabetic or on immunosuppressants.",
    },
    {
        "id": "vitamin-c-foods",
        "name": "Amla & Vitamin-C Rich Foods",
        "hindi_name": "आंवला और विटामिन सी",
        "category": "Food",
        "ingredients": ["Fresh amla / guava / orange", "Bell peppers", "Sprouts & seasonal salads"],
        "benefits": "A varied diet containing vitamin-C-rich foods supports normal nutrition but does not neutralize inhaled pollution.",
        "when": "Daily through the pollution season — one serving each morning.",
        "caution": "Whole fruit is better than juice (less sugar spike).",
    },
    {
        "id": "eye-compress",
        "name": "Cool Water / Rose-Water Eye Rinse",
        "hindi_name": "आँखों की सिकाई",
        "category": "Self-care",
        "ingredients": ["Clean cool potable water", "Clean, soft cloth"],
        "benefits": "A clean cool compress may temporarily soothe mild irritation. Homemade liquids should not be placed into the eyes.",
        "when": "As often as needed after outdoor time; before sleep on cracker nights.",
        "caution": "Use fresh clean water only; do not share towels. Persistent redness or vision change needs an eye doctor.",
    },
]


def doctor_facets() -> dict:
    cities = sorted({d["city"] for d in DOCTORS})
    specs = sorted({s for d in DOCTORS for s in d["specialties"]})
    return {"cities": cities, "specialties": specs}


def filter_doctors(city: str | None = None, specialty: str | None = None) -> list[dict]:
    out = DOCTORS
    if city:
        out = [d for d in out if d["city"].lower() == city.lower()]
    if specialty:
        out = [d for d in out if any(specialty.lower() in s.lower() for s in d["specialties"])]
    return out


# Structured recipe detail. Ayurvedic notes describe traditional framing only;
# they are not clinical efficacy claims or a substitute for a registered clinician.
REMEDY_DETAILS: dict[str, dict] = {
    "tulsi-adrak-tea": {
        "summary": "A mild, warming tulsi-and-ginger infusion for hydration and temporary throat comfort.",
        "preparation": ["Rinse 8–10 fresh tulsi leaves.", "Slice or grate about 1 inch of fresh ginger.", "Simmer the ginger in 1 cup of water for 5 minutes.", "Turn off the heat, add tulsi, cover and steep for 3–4 minutes.", "Strain. Let it cool slightly; add a little honey or lemon only if tolerated."],
        "time_minutes": 10, "servings": 1,
        "ayurvedic_perspective": "In Ayurveda, tulsi is traditionally described as having a warming, aromatic quality; ginger (shunthi/ardraka) is traditionally used in digestive and warming preparations. These are traditional descriptions, not proof that the drink treats pollution injury.",
        "evidence_note": "Warm fluids may soothe a dry throat and support hydration. There is no good clinical evidence that this tea removes inhaled particles, detoxifies lungs, or prevents pollution-related disease.",
        "safety": "May aggravate reflux or heartburn in some people. Check for herb allergies and medicine interactions. Honey must never be given to infants under 1 year.",
        "when_to_seek_help": "Seek medical advice for persistent wheezing, fever, worsening cough or breathlessness; urgent care for chest pain or breathlessness at rest.",
    },
    "haldi-doodh": {
        "summary": "A simple turmeric milk beverage traditionally enjoyed warm; it is a comfort drink, not a respiratory treatment.",
        "preparation": ["Warm 1 cup of milk or an unsweetened alternative over low heat.", "Whisk in ½ teaspoon turmeric until evenly dispersed.", "Optionally add a very small pinch of black pepper if it suits your stomach.", "Warm for 2–3 minutes without boiling over; serve warm."],
        "time_minutes": 5, "servings": 1,
        "ayurvedic_perspective": "Haldi (haridra) is traditionally described as pungent and warming and is used in food and household preparations. This traditional context does not establish a therapeutic effect on air pollution exposure.",
        "evidence_note": "Curcumin has been studied in laboratory and clinical contexts, but this household drink has not been shown to prevent or treat pollution-related lung injury.",
        "safety": "Avoid if the ingredients trigger reflux or allergy. Concentrated turmeric supplements can interact with medicines and are not equivalent to culinary amounts. Ask a clinician before medicinal use if pregnant, on anticoagulants, or with gallbladder disease.",
        "when_to_seek_help": "Do not use this instead of prescribed asthma/COPD medication or medical assessment.",
    },
    "honey-lemon-ginger": {
        "summary": "A warm honey, lemon and ginger drink that may temporarily soothe throat irritation.",
        "preparation": ["Simmer 3–4 thin ginger slices in 1 cup of water for 4–5 minutes.", "Allow the infusion to cool until comfortably warm.", "Stir in 1 teaspoon to 1 tablespoon of honey and a squeeze of lemon.", "Sip slowly; reduce or omit lemon if acidity is a problem."],
        "time_minutes": 8, "servings": 1,
        "ayurvedic_perspective": "Ginger is traditionally used in warming preparations; honey (madhu) has a place in classical Ayurvedic formulations. Traditional use should not be interpreted as evidence of protection from particulate matter.",
        "evidence_note": "Honey may provide modest symptomatic relief for cough in some people, but this drink does not clean the lungs or reduce the AQI dose inhaled.",
        "safety": "Never give honey to a child under 1 year. Lemon and ginger may worsen reflux. Consider sugar intake if using honey frequently.",
        "when_to_seek_help": "Seek care if symptoms persist, worsen, or include wheezing or shortness of breath.",
    },
    "mulethi-water": {
        "summary": "Mulethi (licorice) has traditional use for throat discomfort, but routine home-prepared oral use is not recommended because dose and safety are uncertain.",
        "preparation": ["This project does not provide a self-dosing recipe for oral mulethi.", "If a registered clinician specifically recommends it, use only the product and dose they specify.", "Do not combine multiple licorice-containing products."],
        "time_minutes": None, "servings": None,
        "ayurvedic_perspective": "Yashtimadhu is traditionally described as sweet and soothing and appears in classical formulations. Traditional use does not remove the known risks of glycyrrhizin.",
        "evidence_note": "Evidence for licorice in most health conditions is limited. NCCIH notes that glycyrrhizin can cause serious adverse effects, including blood-pressure and heart-rhythm problems.",
        "safety": "Avoid unsupervised oral use, especially with high blood pressure, heart or kidney disease, pregnancy, high salt intake, or medicines such as corticosteroids. Discuss all herbal products with a clinician.",
        "when_to_seek_help": "Choose warm water or a simple saline gargle for mild throat comfort instead; obtain medical advice for persistent symptoms.",
        "references": [{"label":"NCCIH — Licorice Root: Usefulness and Safety","url":"https://www.nccih.nih.gov/health/licorice-root"}],
    },
    "saline-gargle": {
        "summary": "A simple salt-water gargle that may temporarily ease a scratchy throat. Spit it out; do not swallow.",
        "preparation": ["Dissolve ½ teaspoon of table salt in 1 cup (about 240 ml) of clean, lukewarm water.", "Take a small mouthful and gargle gently for several seconds.", "Spit it out. Repeat with the remaining solution; prepare a fresh batch each time."],
        "time_minutes": 3, "servings": 1,
        "ayurvedic_perspective": "Gargling (kavala/gandusha practices) is described in Ayurveda, though the classical procedures and substances vary. This simple saline gargle is a modern household comfort measure, not a substitute for a prescribed Ayurvedic procedure.",
        "evidence_note": "May soothe throat discomfort for some people. It does not remove particles from the lower airways or prevent pollution effects.",
        "safety": "Use lukewarm, not hot, water. Do not swallow. Young children who cannot gargle safely should not use this method.",
        "when_to_seek_help": "Seek care for severe sore throat, difficulty swallowing, high fever or breathing difficulty.",
    },
    "steam-inhalation": {
        "summary": "The traditional bowl-of-boiling-water steam method is not recommended because of scald risk and limited evidence of benefit. Use safer comfort options instead.",
        "preparation": ["Do not lean over a bowl or pot of hot water, and do not cover the head with a towel over boiling water.", "For comfort, consider a comfortably warm shower or a commercially designed humidifier used and cleaned according to its instructions.", "For nasal dryness, consider a ready-made sterile saline spray."],
        "time_minutes": None, "servings": None,
        "ayurvedic_perspective": "Swedana (therapeutic sweating/warming procedures) exists in Ayurveda, but this does not validate the safety or efficacy of improvised hot-water steam inhalation.",
        "evidence_note": "Steam inhalation has not shown strong evidence of benefit for congestion and can cause serious burns. It does not remove air pollution from the lungs.",
        "safety": "Avoid bowls of hot water for inhalation, especially around children. Do not add essential oils if they trigger asthma or irritation.",
        "when_to_seek_help": "Persistent congestion, wheezing or breathlessness warrants clinical advice.",
        "references": [{"label":"NHS / British Burn Association safety warning","url":"https://www.royaldevon.nhs.uk/news/nhs-and-british-burn-association-issue-public-safety-warning-steam-inhalation-causes-burns/"}],
    },
    "kaadha": {
        "summary": "A mild tulsi-ginger drink inspired by traditional kadha preparations. Keep it gentle; very concentrated spice mixtures can irritate the stomach.",
        "preparation": ["Add 4–5 tulsi leaves and 2 thin ginger slices to 1½ cups of water.", "Optionally add 1 lightly crushed black peppercorn; omit if sensitive to spice.", "Simmer gently for 5 minutes, then switch off and steep for 2 minutes.", "Strain and drink warm. Do not reduce it to a highly concentrated decoction."],
        "time_minutes": 9, "servings": 1,
        "ayurvedic_perspective": "Tulsi, ardraka and maricha are used in traditional warming preparations. Ayurvedic qualities are traditional explanatory concepts; they are not evidence of a protective effect against PM2.5.",
        "evidence_note": "A warm drink may be soothing and hydrating. There is no reliable evidence that kadha prevents infection or reverses pollution-related lung injury.",
        "safety": "Avoid or dilute if you have reflux, gastritis or spice sensitivity. Do not use as a substitute for medical treatment.",
        "when_to_seek_help": "Get medical assessment for persistent cough, wheezing or breathlessness.",
    },
    "giloy-kadha": {
        "summary": "Giloy is a medicinal herb, not an everyday tea ingredient. This project does not recommend a do-it-yourself giloy kadha.",
        "preparation": ["No home-preparation or self-dosing instructions are provided.", "Do not use raw plant material or an unidentified product.", "If considering giloy, discuss the exact product with a registered Ayurvedic physician and your regular clinician first."],
        "time_minutes": None, "servings": None,
        "ayurvedic_perspective": "Guduchi is traditionally described as a rasayana in Ayurveda. That traditional classification is not proof that it treats pollution exposure or is safe for every person.",
        "evidence_note": "Human evidence for many promoted uses is limited. The NIH LiverTox monograph documents clinically apparent liver injury associated with Tinospora cordifolia products; risk-benefit needs professional assessment.",
        "safety": "Avoid self-medication, particularly with liver disease, autoimmune conditions, pregnancy, diabetes medicines or immunosuppressants. Product identity and dose matter.",
        "when_to_seek_help": "Stop and seek medical advice if jaundice, dark urine, persistent nausea, abdominal pain or unusual fatigue develops.",
        "references": [{"label":"NIH LiverTox — Tinospora","url":"https://www.ncbi.nlm.nih.gov/books/NBK608429/"}],
    },
    "vitamin-c-foods": {
        "summary": "A food plate featuring amla, guava, citrus and vegetables. It supports general nutrition but is not a pollution antidote.",
        "preparation": ["Wash fresh fruit and vegetables thoroughly under clean running water.", "Serve one whole fruit such as guava, orange or amla (as tolerated).", "Add bell pepper or other vegetables to a meal; sprouts should be fresh and safely handled.", "Prefer whole fruit over sweetened juice."],
        "time_minutes": 5, "servings": 1,
        "ayurvedic_perspective": "Amla (amalaki) is traditionally valued as a food and rasayana. Food-based use is different from concentrated extracts or supplements.",
        "evidence_note": "Vitamin C is an essential nutrient and contributes to normal physiological functions. Eating vitamin-C-rich foods has not been shown to neutralize inhaled pollution or prevent pollution-related disease.",
        "safety": "Amla and citrus may aggravate acidity in some people. Wash produce well; avoid raw sprouts if you are at higher risk from foodborne illness.",
        "when_to_seek_help": "Nutrition complements, but does not replace, exposure reduction and appropriate medical care.",
    },
    "eye-compress": {
        "summary": "A clean, cool compress around closed eyelids may soothe mild irritation. Do not put homemade rose water or herbal mixtures into the eyes.",
        "preparation": ["Wash your hands.", "Wet a clean, soft cloth with cool potable water and wring it out.", "Place it gently over closed eyelids for a few minutes without pressing on the eyes.", "Use a clean section of cloth for each eye and wash it after use."],
        "time_minutes": 5, "servings": 1,
        "ayurvedic_perspective": "Traditional eye-care practices (netra kriya) are described in Ayurveda, but homemade liquids should not be placed in the eye. Use only sterile ophthalmic products recommended by an eye-care professional.",
        "evidence_note": "A cool clean compress may provide temporary comfort. It does not treat eye injury, infection or pollution exposure.",
        "safety": "Do not use homemade rose water, herbal extracts or non-sterile liquids in the eyes. Seek urgent eye care for pain, light sensitivity, vision change or chemical exposure.",
        "when_to_seek_help": "Persistent redness, pain, discharge or blurred vision needs medical assessment.",
    },
}

def get_remedy(remedy_id: str) -> dict | None:
    base = next((item for item in REMEDIES if item["id"] == remedy_id), None)
    if base is None:
        return None
    return {**base, **REMEDY_DETAILS.get(remedy_id, {})}
