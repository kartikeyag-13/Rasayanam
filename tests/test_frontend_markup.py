from pathlib import Path
import re
import unittest


PAGE = Path(__file__).resolve().parents[1] / "static" / "index.html"


class FrontendMarkupTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = PAGE.read_text(encoding="utf-8")

    def test_no_literal_backslash_n_in_page_source(self):
        self.assertNotIn("\\n", self.html)

    def test_journey_navigation_is_in_flow_and_keeps_all_destinations(self):
        self.assertRegex(self.html, r"\.journey-nav\{position:relative")
        self.assertNotRegex(self.html, r"\.journey-nav\{position:fixed")
        nav = re.search(r'<nav class="journey-nav".*?</nav>', self.html, re.S)
        self.assertIsNotNone(nav)
        self.assertEqual(nav.group(0).count('data-stage='), 5)
        self.assertIn("min-height:42px", self.html)

    def test_aqi_number_is_in_gauge_and_label_is_outside_it(self):
        gauge_stack = re.search(r'<div class="gauge-stack">(.*?)</div><div class="aqi-desc">', self.html, re.S)
        self.assertIsNotNone(gauge_stack)
        content = gauge_stack.group(1)
        gauge = re.search(r'<div class="gauge">(.*?)</div>', content, re.S)
        self.assertIsNotNone(gauge)
        self.assertIn('id="aqiValue"', gauge.group(1))
        self.assertNotIn("gauge-label", gauge.group(1))
        self.assertIn("gauge-label", content)
        self.assertIn(".gauge-number{position:relative;z-index:1", self.html)
        self.assertIn(".gauge svg{z-index:0", self.html)

    def test_mobile_hero_keeps_branding_and_heading_in_flow(self):
        self.assertIn("logo.style.position='static'", self.html)
        self.assertIn(".topbar .nav{margin-left:auto}", self.html)
        self.assertIn("padding:124px 0 82px", self.html)
        self.assertIn(".hero .eyebrow{max-width:100%", self.html)
        self.assertIn(".heritage-stamp{right:8px;top:0", self.html)
        self.assertIn(".topbar .brand img{display:block;width:100%;height:auto}", self.html)

    def test_doctor_directory_progressive_disclosure_and_filters(self):
        self.assertIn('id="doctorMore" type="button" aria-controls="doctorGrid" aria-expanded="false" hidden', self.html)
        self.assertIn("Math.min(3,filtered.length)", self.html)
        self.assertIn("const showAll=hasFilters||doctorExpanded", self.html)
        self.assertIn("Array.isArray(d.specialties)?d.specialties", self.html)
        self.assertIn("more.textContent=doctorExpanded?'Show less':'View all doctors ('", self.html)
        self.assertIn("card.inert=collapsed", self.html)
        self.assertIn("if(d.website)", self.html)
        self.assertIn("$('#doctorCity').addEventListener('input',updateDoctorFilters)", self.html)
        self.assertIn("$('#doctorSpecialty').addEventListener('change',updateDoctorFilters)", self.html)

    def test_leaf_and_labels_share_logo_timeline_and_orbit_continuously(self):
        self.assertEqual(self.html.count('id="heroLeaf"'), 1)
        self.assertEqual(self.html.count('id="brandLogo"'), 1)
        self.assertIn("animation.startTime=coordinatedStart", self.html)
        self.assertIn("animateHeroComposition(coordinatedStart)", self.html)
        self.assertIn("leafDrop.startTime=startTime", self.html)
        self.assertIn("entrance.startTime=startTime", self.html)
        self.assertIn("{transform:'translate(0px,0px)',offset:0", self.html)
        self.assertIn("{duration:1650,delay:labelDelay+index*220,fill:'both',easing:'linear'}", self.html)
        self.assertIn("item.style.transform=targetTransform", self.html)
        self.assertIn("const samples=96", self.html)
        self.assertIn("{duration:path.period,iterations:Infinity,easing:'linear'}", self.html)
        self.assertIn("period:52000", self.html)
        self.assertIn(".orbit-item.one{top:70px;right:0}", self.html)
        self.assertIn(".orbit-item.one{right:-5px;top:30px}", self.html)
        self.assertIn(".orbit-label{position:relative;inset:auto;display:block", self.html)
        self.assertNotIn("animation:float", self.html)
        self.assertNotIn("animation:orbit", self.html)
        self.assertIn("if(skip||reduced){settleLogo();settleHeroComposition()", self.html)


if __name__ == "__main__":
    unittest.main()
