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
        "summary": "The official Indian AQI framework: sub-indices for PM2.5, PM10, NO₂, SO₂, CO, O₃ and NH₃ combined into one 0–500 index with six categories and health advisories.",
        "why_it_matters": "Every AQI number on this platform is computed with exactly these CPCB breakpoints — so what you see matches what the government reports.",
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
        "benefits": "Soothes an irritated airway, helps loosen phlegm and eases the scratchy throat that polluted air causes. Ginger and tulsi are both anti-inflammatory.",
        "when": "2–3 cups a day on high-AQI days, especially after coming indoors.",
        "caution": "No honey for infants under 1 year. Go easy if you have acid reflux.",
    },
    {
        "id": "haldi-doodh",
        "name": "Haldi Doodh (Golden Milk)",
        "hindi_name": "हल्दी दूध",
        "category": "Home remedy",
        "ingredients": ["½ tsp turmeric", "A pinch of black pepper", "1 cup warm milk (or plant milk)"],
        "benefits": "Turmeric's curcumin is a well-studied anti-inflammatory; black pepper boosts absorption. Traditional night-time recovery drink for cough and chest congestion.",
        "when": "Once at bedtime through Diwali–winter season.",
        "caution": "Skip if you are lactose intolerant or on blood-thinning medication — ask your doctor first.",
    },
    {
        "id": "honey-lemon-ginger",
        "name": "Shehad–Nimbu–Adrak",
        "hindi_name": "शहद–नींबू–अदरक",
        "category": "Home remedy",
        "ingredients": ["1 tbsp honey", "Half lemon", "Thin ginger slices", "Warm water"],
        "benefits": "Coats and calms a raw throat, keeps airway mucosa hydrated and adds vitamin C.",
        "when": "At the first sign of throat irritation or dry cough — 2× a day.",
        "caution": "Add honey only after the water cools below ~60 °C; not for infants <1 year.",
    },
    {
        "id": "mulethi-water",
        "name": "Mulethi Ka Paani",
        "hindi_name": "मुलेठी का पानी",
        "category": "Home remedy",
        "ingredients": ["2–3 pieces mulethi (licorice root)", "1 cup water"],
        "benefits": "Licorice coats and relieves throat irritation and dry cough; a classic post-pollution gargle/drink.",
        "when": "Once or twice a day when the throat feels hoarse or phlegm sticks.",
        "caution": "Avoid in hypertension, pregnancy or kidney disease without consulting a doctor — licorice can raise blood pressure.",
    },
    {
        "id": "saline-gargle",
        "name": "Warm Saline Gargles",
        "hindi_name": "नमक के गरारे",
        "category": "Self-care",
        "ingredients": ["½ tsp salt", "1 cup lukewarm water"],
        "benefits": "Draws out irritants and mucus from the throat, reduces inflammation and gives quick relief from smoke-sting after crackers or smog.",
        "when": "2–3 times a day, and immediately after prolonged outdoor exposure.",
        "caution": "Use lukewarm, never hot water. Spit it out; do not swallow.",
    },
    {
        "id": "steam-inhalation",
        "name": "Steam Inhalation (Ajwain / Eucalyptus)",
        "hindi_name": "भाप लेना",
        "category": "Self-care",
        "ingredients": ["Bowl of steaming water", "Optional: 1 tsp ajwain or 2–3 eucalyptus leaves", "Towel"],
        "benefits": "Thins mucus, relieves nasal block and sinus pressure caused by particulate-laden air.",
        "when": "Once daily in the evening during heavy pollution; extra dose when congested.",
        "caution": "8–10 minutes max, keep a safe distance from the water. Not for children under 6 (burn risk); stop if it triggers wheezing.",
    },
    {
        "id": "kaadha",
        "name": "Kali Mirch–Tulsi Kaadha",
        "hindi_name": "काली मिर्च काढ़ा",
        "category": "Herbal tea",
        "ingredients": ["5–6 tulsi leaves", "4–5 black peppercorns", "½ tsp turmeric", "1-inch ginger", "1 cup water (reduced to half)"],
        "benefits": "Warming immunity decoction that opens up congestion and calms cough reflexes during firecracker season.",
        "when": "Once a day, morning or evening, during Diwali week.",
        "caution": "Strong — avoid on an empty stomach if you have gastritis. Skip for small children.",
    },
    {
        "id": "giloy-kadha",
        "name": "Giloy (Guduchi) Kadha",
        "hindi_name": "गिलोय काढ़ा",
        "category": "Herbal tea",
        "ingredients": ["2-inch giloy stem (or 1 tsp powder)", "1 cup water", "Optional: honey"],
        "benefits": "Used in Ayurveda as an immunomodulator and general tonic through the infection-prone winter season.",
        "when": "Once daily for a week around Diwali.",
        "caution": "Consult your doctor if you are pregnant, diabetic or on immunosuppressants.",
    },
    {
        "id": "vitamin-c-foods",
        "name": "Amla & Vitamin-C Rich Foods",
        "hindi_name": "आंवला और विटामिन सी",
        "category": "Food",
        "ingredients": ["Fresh amla / guava / orange", "Bell peppers", "Sprouts & seasonal salads"],
        "benefits": "Antioxidants counteract the oxidative stress that PM2.5 creates in lung tissue; vitamin C supports repair of airway lining.",
        "when": "Daily through the pollution season — one serving each morning.",
        "caution": "Whole fruit is better than juice (less sugar spike).",
    },
    {
        "id": "eye-compress",
        "name": "Cool Water / Rose-Water Eye Rinse",
        "hindi_name": "आँखों की सिकाई",
        "category": "Self-care",
        "ingredients": ["Clean cool water or sterile rose water", "Clean towel/cotton"],
        "benefits": "Flushes particulates and calms the burning, watery eyes that smoke and smog cause.",
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
