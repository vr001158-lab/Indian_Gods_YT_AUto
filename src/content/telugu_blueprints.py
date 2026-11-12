# src/content/telugu_blueprints.py
# Comprehensive Telugu Devotional Blueprints & Offline Fallback Synthesis
# For Divine Dharshanam Daily (దివ్య దర్శనం) — Strictly Telugu (te-IN)

from __future__ import annotations

import json
import re
from typing import Any

from src.assets.selector import resolve_deity


# Technical and stage direction keywords that MUST NEVER leak into spoken TTS narration
ENGLISH_PROMPT_LEAK_WORDS: list[str] = [
    "scene", "visual", "description", "prompt", "camera", "8k", "shot",
    "footage", "cinematic", "close up", "slow motion", "zoom", "panning"
]

TELUGU_STAGE_TERMS: list[str] = [
    "దృశ్యం", "సన్నివేశం", "వర్ణన", "చిత్రం", "ఘట్టం", "వర్ణించడం", "చిత్రించడం"
]


def clean_spoken_narration(text: str) -> str:
    """
    Strips prompt instructions, stage meta-words, and technical directions
    from spoken narration text while preserving authentic devotional content.
    """
    if not text:
        return ""
    cleaned = text.strip()

    # Strip English technical prompt leaks
    for eng_term in ENGLISH_PROMPT_LEAK_WORDS:
        cleaned = re.sub(r"(?i)" + re.escape(eng_term) + r"", "", cleaned)

    # Strip Telugu stage instruction suffixes like "... దృశ్యం.", "... ఘట్టం.", "... వర్ణన.", "... చిత్రం."
    cleaned = re.sub(r"\s*(?:దృశ్యం|సన్నివేశం|వర్ణన|చిత్రం|ఘట్టం|వైభవం|దర్శనం)\.?$", ".", cleaned)
    # Strip prefixes like "దృశ్యం 1:", "సన్నివేశం:"
    cleaned = re.sub(r"^(?:దృశ్యం|సన్నివేశం|వర్ణన|చిత్రం|ఘట్టం)\s*[\d:.\-]*\s*", "", cleaned)

    # Clean whitespace and trailing dots
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    cleaned = re.sub(r"\.+", ".", cleaned)
    if cleaned and not cleaned.endswith((".", "!", "?", "।")):
        cleaned += "."
    return cleaned


def validate_spoken_narration(text: str) -> tuple[bool, list[str]]:
    """
    Strictly validates that narration contains only spoken narrative content,
    rejecting any leaked prompt descriptions or metadata words.
    """
    reasons: list[str] = []
    if not text or not text.strip():
        return False, ["Narration text is empty."]

    text_lower = text.lower()
    # 1. Reject English technical prompt words
    for eng_term in ENGLISH_PROMPT_LEAK_WORDS:
        if re.search(r"" + re.escape(eng_term) + r"", text_lower):
            reasons.append(f"Leaked technical prompt keyword detected: '{eng_term}'")

    # 2. Reject Telugu meta-instruction words when used as stage directions
    for meta_term in ["దృశ్యం", "వర్ణన", "సన్నివేశం"]:
        if meta_term in text:
            if re.search(r"(?:|[\s,])" + re.escape(meta_term) + r"(?:[\s.:]|$)", text):
                reasons.append(f"Leaked Telugu stage-direction term detected: '{meta_term}'")

    return len(reasons) == 0, reasons


TELUGU_DEITY_BRIEFS: dict[str, dict[str, Any]] = {
    "lord_shiva": {
        "title_options": [
            "శివుని మెడలో పాము ఎందుకు ఉంటుంది? అసలు రహస్యం",
            "వాసుకి నాగరాజు మరియు పరమశివుని పవిత్ర గాథ",
            "సముద్ర మథనం మరియు నీలకంఠుని అద్భుత లీల",
            "శివుని మెడలోని సర్పం: అహంకారాన్ని జయించే దివ్య సందేశం",
            "పరమేశ్వరుడు వాసుకిని ఆభరణంగా ఎందుకు ధరించాడు?"
        ],
        "primary_title": "శివుని మెడలో పాము ఎందుకు ఉంటుంది? అసలు రహస్యం",
        "hook": "దేవాది దేవుడైన పరమేశ్వరుడు బంగారు ఆభరణాలకు బదులుగా ప్రాణాంతకమైన సర్పాన్ని ఎందుకు ధరించాడో మీకు తెలుసా? ఇది కేవలం అలంకారం కాదు, మన జీవితంలోని సమస్యలను ఎదుర్కొనేందుకు ఒక గొప్ప ఆధ్యాత్మిక పాఠం.",
        "audience": "భక్తులు, పురాణ ఆసక్తిపరులు మరియు ఆధ్యాత్మిక సాధకులు.",
        "story_arc": [
            "మొదటి భాగం: కైలాసంలో ప్రశాంత ధ్యానంలో ఉన్న శివుడు మరియు మెడలో వాసుకి సర్పం.",
            "రెండవ భాగం: క్షీరసాగర మథనం, హాలాహల విషం మరియు పరమశివునికి తోడుగా నిలిచిన వాసుకి కథ.",
            "మూడవ భాగం: ప్రతికూల పరిస్థితులను నియంత్రించి అంతరంగిక ప్రశాంతతను పొందే దివ్య సందేశం."
        ],
        "script_structure": {
            "act_1_opening": "కైలాస పర్వతముపై పరమశివుడు ప్రశాంత ధ్యానంలో ఉండగా, ఆయన మెడలో నాగేంద్రుడు అలంకారంగా నిలిచాడు.",
            "act_2_explanation": "సముద్ర మథన సమయంలో లోకాలను రక్షించడానికి పరమశివుడు హాలాహల విషాన్ని స్వీకరించి నీలకంఠుడయ్యాడు.",
            "act_3_message": "విషాన్ని సైతం కంఠంలో నిలిపి లోకాలను రక్షించిన స్వామి మనోశక్తిని అనుసరించి ధైర్యంతో సాగాలి."
        },
        "visual_plan": [
            {
                "scene_number": 1,
                "duration_seconds": 15,
                "description": "కైలాస పర్వతముపై పరమశివుడు ధ్యానంలో ఉండగా మెడలో వాసుకి పాము ప్రశాంతంగా ఉన్న దృశ్యం.",
                "voice_text": "కైలాస పర్వతముపై పరమశివుడు ప్రశాంత ధ్యానంలో ఉండగా, ఆయన మెడలో నాగేంద్రుడు అలంకారంగా నిలిచాడు.",
                "image_prompt": "Cinematic close-up of meditating Lord Shiva, coiled cobra snake Vasuki on neck, Mount Kailash background, divine golden light, 8k",
                "video_prompt": "Serene camera panning slowly around meditating Lord Shiva, coiled cobra gently raising hood, divine mist"
            },
            {
                "scene_number": 2,
                "duration_seconds": 20,
                "description": "దేవదానవులు వాసుకిని తాడుగా చేసుకుని సముద్ర మథనం చేస్తున్న అద్భుత దృశ్యం.",
                "voice_text": "సముద్ర మథన సమయంలో వాసుకి త్రాడుగా నిలవగా, పాలకడలి నుంచి భయంకరమైన హాలాహల విషం పుట్టింది.",
                "image_prompt": "Samudra Manthan cosmic churning, devas and asuras pulling giant serpent Vasuki, Mount Mandara spinning, dramatic lighting",
                "video_prompt": "Epic wide shot of devas and asuras churning cosmic milk ocean with giant serpent Vasuki"
            },
            {
                "scene_number": 3,
                "duration_seconds": 25,
                "description": "హాలాహల విషాన్ని శివుడు సేవిస్తుండగా పార్వతీదేవి కంఠంపై చేయి వేసిన దివ్య ఘట్టం.",
                "voice_text": "సకల లోకాలను రక్షించడానికి పరమశివుడు ఆ విషాన్ని స్వీకరించి, తన కంఠంలో నిలిపి నీలకంఠుడయ్యాడు.",
                "image_prompt": "Lord Shiva calmly drinking blue glowing Halahala poison, Goddess Parvati placing hand on his neck, divine dramatic aura",
                "video_prompt": "Slow motion shot of Lord Shiva drinking blue poison, throat glowing blue as Parvati touches it"
            },
            {
                "scene_number": 4,
                "duration_seconds": 15,
                "description": "శివుడు వాసుకి సర్పాన్ని కంఠాభరణంగా ధరించి అనుగ్రహిస్తున్న దృశ్యం.",
                "voice_text": "ఆ విషపు వేడిని ఉపశమింపజేయడానికి వాసుకి సర్పం స్వామి మెడను చుట్టుకుని శాశ్వత ఆభరణంగా మారింది.",
                "image_prompt": "Lord Shiva gently placing cobra Vasuki around his blue throat, cobra bowing in devotion, peaceful expression",
                "video_prompt": "Lord Shiva smiling and placing majestic cobra around his neck, golden aura sparks"
            },
            {
                "scene_number": 5,
                "duration_seconds": 15,
                "description": "ఆధ్యాత్మిక సాధకుడు ప్రశాంత వాతావరణంలో ధ్యానిస్తున్న దృశ్యం.",
                "voice_text": "సమస్యలను చూసి భయపడకుండా, శివుని వలె ధైర్యంతో ఎదుర్కొంటే విజయం మనదే. ఓం నమః శివాయ.",
                "image_prompt": "Serene individual meditating calmly in peaceful nature, soft morning sunlight, symbolic harmony",
                "video_prompt": "Peaceful meditation scene transitioning to sacred temple glow, ambient serenity"
            }
        ],
        "voice_direction": {
            "tone": "భక్తిపూర్వకం, ప్రశాంతం మరియు గాంభీర్యం.",
            "speed": "సహజమైన, స్పష్టమైన వేగం (నిమిషానికి సుమారు 115 పదాలు).",
            "emotion": "ఆధ్యాత్మిక అనుభూతిని కలిగించేలా.",
            "language_style": "తేట తెలుగు, స్పష్టమైన ఉచ్ఛారణతో కూడిన భక్తి సంభాషణ."
        },
        "shorts_hooks": [
            "శివుని మెడలో పాము ఎందుకు ఉంటుందో మీకు తెలుసా?",
            "హాలాహల విషాన్ని అమృతంగా మార్చిన పరమేశ్వరుని కథ!",
            "మెడలోని పాము ద్వారా పరమశివుడు మనకిచ్చే అద్భుత సందేశం!"
        ],
        "seo_metadata": {
            "description": "పరమశివుని మెడలో వాసుకి సర్పం ఎందుకు ఉంటుంది? సముద్ర మథనం మరియు నీలకంఠుని పవిత్ర గాథ. దివ్య దర్శనంలో ఆధ్యాత్మిక సత్యాలు.",
            "keywords": ["శివుడు", "వాసుకి", "సముద్ర మథనం", "నీలకంఠుడు", "తెలుగు భక్తి", "పరమేశ్వరుడు", "దివ్య దర్శనం"],
            "hashtags": ["#శివుడు", "#మహాదేవ్", "#భక్తికథలు", "#దివ్యదర్శనం", "#తెలుగుభక్తి"],
            "category": "Education"
        }
    },
    "ganesha": {
        "title_options": [
            "వినాయకుడి ఏకదంతం వెనుక ఉన్న అసలు రహస్యం ఏమిటి?",
            "మహాభారత రచన కోసం గణపతి చేసిన పరమ త్యాగం",
            "ఏకదంతుడుగా వినాయకుడు ఎందుకు పూజలందుకుంటున్నాడు?",
            "లంబోదరుని ఒంటి దంతం: లక్ష్య సాధనకు ఇచ్చే దివ్య సందేశం",
            "గణేశుని విరిగిన దంతం కథ వింటే ఆశ్చర్యపోతారు!"
        ],
        "primary_title": "వినాయకుడి ఏకదంతం వెనుక ఉన్న అసలు రహస్యం ఏమిటి?",
        "hook": "విఘ్న నాయకుడైన గణపతికి ఒకే దంతం ఎందుకు ఉంటుందో మీకు తెలుసా? జ్ఞాన సంపద కోసం స్వామి చేసిన గొప్ప త్యాగం మన జీవితానికి సరికొత్త దిశానిర్దేశం చేస్తుంది.",
        "audience": "భక్తులు, విద్యార్థులు మరియు పురాణ ప్రేమికులు.",
        "story_arc": [
            "మొదటి భాగం: శ్రీ వినాయకుని ఏకదంత దివ్య స్వరూపం.",
            "రెండవ భాగం: వ్యాస మహర్షి మహాభారత పారాయణం మరియు కలం విరిగిపోవడంతో దంతాన్ని విరిచి కలంగా మార్చిన ఘట్టం.",
            "మూడవ భాగం: కర్తవ్య నిర్వహణలో ఎలాంటి ఆటంకాలకు లొంగకూడదనే ఆధ్యాత్మిక సందేశం."
        ],
        "script_structure": {
            "act_1_opening": "విఘ్న నాయకుడైన శ్రీ గణేశుని ఏకదంత దివ్య రూపం జ్ఞానానికి, పరిపూర్ణ ఏకాగ్రతకు నిదర్శనం.",
            "act_2_explanation": "వ్యాస మహర్షి చెబుతున్న మహాభారతాన్ని లిఖిస్తూ కలం విరిగిపోగా, స్వామి తన దంతాన్ని విరిచి లేఖినిగా మార్చాడు.",
            "act_3_message": "జ్ఞాన సముపార్జన కోసం దేహ సౌందర్యాన్ని త్యాగం చేసిన స్వామి భక్తి మార్గం మనకు ఆదర్శం."
        },
        "visual_plan": [
            {
                "scene_number": 1,
                "duration_seconds": 15,
                "description": "శ్రీ గణేశుని దివ్య ముఖారవిందం, ఏకదంతం ప్రస్ఫుటంగా కనిపిస్తున్న దృశ్యం.",
                "voice_text": "విఘ్న నాయకుడైన శ్రీ గణేశుని ఏకదంత దివ్య రూపం జ్ఞానానికి, పరిపూర్ణ ఏకాగ్రతకు నిదర్శనం.",
                "image_prompt": "Cinematic close up of Lord Ganesha showing single broken tusk, divine temple diya lights, golden ornaments, 8k",
                "video_prompt": "Camera slowly moving to reveal Lord Ganesha face highlighting the single broken tusk and gentle eyes"
            },
            {
                "scene_number": 2,
                "duration_seconds": 20,
                "description": "వ్యాస మహర్షి శ్లోకాలు చెబుతుండగా గణపతి తాళపత్రాలపై వేగంగా రాస్తున్న దృశ్యం.",
                "voice_text": "వ్యాస మహర్షి మహాభారతాన్ని చెబుతుండగా, గణపతి ఏమాత్రం ఆగకుండా తాళపత్రాలపై లిఖిస్తూ సాగాడు.",
                "image_prompt": "Sage Vyasa reciting verses, young radiant Ganesha writing rapidly on palm leaves with quill, forest hermitage aura",
                "video_prompt": "Vyasa speaking sacred Sanskrit verses as Ganesha hand glides swiftly across palm leaves"
            },
            {
                "scene_number": 3,
                "duration_seconds": 25,
                "description": "గణపతి లేఖిని విరిగిపోవడం, తక్షణమే తన దంతాన్ని విరిచి దివ్య కాంతిలో కలంగా మార్చడం.",
                "voice_text": "రచన మధ్యలో కలం విరిగిపోగా, ఏకాగ్రత చెదరకుండా గణపతి తన దంతాన్ని విరిచి కలంగా మార్చాడు.",
                "image_prompt": "Lord Ganesha breaking his own right tusk to continue writing Mahabharata, divine golden spark illuminating room",
                "video_prompt": "Dramatic close up of Ganesha snapping his right tusk without hesitation to keep writing"
            },
            {
                "scene_number": 4,
                "duration_seconds": 15,
                "description": "విరిగిన దంతంతో మహాభారత గ్రంథాన్ని ఆపకుండా పూర్తి చేస్తున్న దృశ్యం.",
                "voice_text": "ఆ పవిత్ర త్యాగంతో మహాభారత గ్రంథం పూర్తయి, లోకానికి అద్భుత ధర్మ సందేశం లభించింది.",
                "image_prompt": "Completed sacred Mahabharata manuscripts stacked with glowing aura, Ganesha smiling peacefully",
                "video_prompt": "Ganesha placing final leaf on sacred book as divine flower petals shower from heaven"
            },
            {
                "scene_number": 5,
                "duration_seconds": 20,
                "description": "విద్యార్థి శ్రద్ధతో విద్యను అభ్యసిస్తున్న దృశ్యం, అంకితభావానికి ప్రతీక.",
                "voice_text": "జ్ఞాన సాధనలో ఎలాంటి అడ్డంకులు ఎదురైనా త్యాగబుద్ధితో ముందుకు సాగాలన్నదే గణపతి ఇచ్చే సందేశం. ఓం గం గణపతయే నమః.",
                "image_prompt": "Modern devoted student studying under soft warm lamp, symbolic divine blessing overlay of Ganesha",
                "video_prompt": "Transition from ancient writing to focused student, symbolizing focus and devotion"
            }
        ],
        "voice_direction": {
            "tone": "స్ఫూర్తిదాయకం, గౌరవప్రదం మరియు స్పష్టం.",
            "speed": "సులభంగా అర్థమయ్యే వేగం (నిమిషానికి సుమారు 120 పదాలు).",
            "emotion": "జ్ఞానోదయం మరియు భక్తి.",
            "language_style": "తేట తెలుగు, చక్కని శైలి."
        },
        "shorts_hooks": [
            "వినాయకుడి దంతం ఎందుకు విరిగిందో తెలుసా?",
            "మహాభారతం రాయడానికి గణపతి చేసిన మహా త్యాగం!",
            "ఏకదంతుని కథలో దాగి ఉన్న అద్భుత విజయ రహస్యం!"
        ],
        "seo_metadata": {
            "description": "వినాయకుడు ఏకదంతుడు ఎలా అయ్యాడు? వ్యాస మహర్షి మహాభారత రచనలో గణపతి చేసిన పరమ త్యాగం. దివ్య దర్శనంలో పవిత్ర గాథ.",
            "keywords": ["వినాయకుడు", "గణపతి", "ఏకదంతం", "మహాభారతం", "వ్యాసుడు", "తెలుగు భక్తి", "దివ్య దర్శనం"],
            "hashtags": ["#వినాయకుడు", "#గణపతి", "#ఏకదంతం", "#మహాభారతం", "#దివ్యదర్శనం"],
            "category": "Education"
        }
    },
    "krishna": {
        "title_options": [
            "శ్రీకృష్ణుడు గోవర్ధన గిరిని చిటికెన వేలితో ఎందుకు ఎత్తాడు?",
            "గోవర్ధన ఉద్ధారణం: ఇంద్రుని గర్వభంగం చేసిన శ్రీకృష్ణుని లీల",
            "వ్రజవాసుల రక్షణ కోసం శ్రీకృష్ణుడు చేసిన అద్భుతం ఏమిటి?",
            "గోవర్ధన పర్వతం వెనుక ఉన్న దివ్య ఆధ్యాత్మిక రహస్యం",
            "శ్రీకృష్ణుని వేలిపై గోవర్ధన గిరి: ప్రకృతి రక్షణ సందేశం"
        ],
        "primary_title": "శ్రీకృష్ణుడు గోవర్ధన గిరిని చిటికెన వేలితో ఎందుకు ఎత్తాడు?",
        "hook": "ఏడు రోజుల పాటు కుండపోత వర్షం కురుస్తుంటే, శ్రీకృష్ణ పరమాత్మ గోవర్ధన పర్వతాన్ని చిటికెన వేలిపై ఎలా ఎత్తాడో తెలుసా? ఈ లీల వెనుక భగవంతుని శరణాగతి తత్వం దాగి ఉంది.",
        "audience": "భక్తులు, శ్రీకృష్ణ ఆరాధకులు మరియు సనాతన ధర్మ ప్రియులు.",
        "story_arc": [
            "మొదటి భాగం: వ్రేపల్లెపై దేవేంద్రుని కోపం మరియు ప్రళయ మేఘాల వర్షం.",
            "రెండవ భాగం: భయపడుతున్న వ్రజవాసులను కాపాడేందుకు శ్రీకృష్ణుడు గోవర్ధన గిరిని ఛత్రంలా ఎత్తడం.",
            "మూడవ భాగం: అహంకారం నశించి ఇంద్రుడు శరణు వేడడం మరియు భగవత్ శరణాగతి ప్రాముఖ్యత."
        ],
        "script_structure": {
            "act_1_opening": "గోకులంపై దేవేంద్రుడు కోపంతో భయంకరమైన ఉరుములు, మెరుపులతో ఎడతెరిపిలేని వర్షం కురిపించాడు.",
            "act_2_explanation": "గోపాలుర ఆర్తనాదాలు విన్న బాలకృష్ణుడు చిరునవ్వుతో గోవర్ధన గిరిని చిటికెన వేలిపై గొడుగులా నిలబెట్టాడు.",
            "act_3_message": "ప్రకృతిని ఆరాధించాలని, భగవంతుని శరణు వేడిన భక్తుడిని ఆయనే కాపాడతాడనే అమృత సందేశం."
        },
        "visual_plan": [
            {
                "scene_number": 1,
                "duration_seconds": 15,
                "description": "గోకులంపై ఉరుములు, మెరుపులతో భయంకరమైన వర్షం కురుస్తున్న దృశ్యం.",
                "voice_text": "గోకులంపై దేవేంద్రుడు కోపంతో భయంకరమైన ఉరుములు, మెరుపులతో ఎడతెరిపిలేని వర్షం కురిపించాడు.",
                "image_prompt": "Dark storm clouds, torrential rain and lightning over Gokulam village, worried villagers looking at sky, dramatic lighting",
                "video_prompt": "Cinematic wide angle showing thunder and heavy rain pouring over ancient Gokul"
            },
            {
                "scene_number": 2,
                "duration_seconds": 20,
                "description": "శ్రీకృష్ణుడు చిరునవ్వుతో గోవర్ధన పర్వతాన్ని సునాయాసంగా చిటికెన వేలిపై ఎత్తుతున్న దృశ్యం.",
                "voice_text": "గోపాలుర ఆర్తనాదాలు విన్న శ్రీకృష్ణుడు చిరునవ్వుతో గోవర్ధన గిరిని తన చిటికెన వేలిపై ఎత్తాడు.",
                "image_prompt": "Lord Krishna holding Govardhan hill with little finger of left hand, serene divine smile, peacock feather glowing, 8k",
                "video_prompt": "Slow camera crane up showing young Krishna lifting the massive mountain effortlessly"
            },
            {
                "scene_number": 3,
                "duration_seconds": 25,
                "description": "పర్వతం క్రింద గోవులు, గోపాలురు సురక్షితంగా ఆనందంతో శ్రీకృష్ణుని దర్శిస్తున్న దృశ్యం.",
                "voice_text": "ఏడు రోజుల పాటు ఆ కొండ గొడుగు క్రింద సమస్త గోకులం క్షేమంగా రక్షణ పొందింది.",
                "image_prompt": "Cows, calves, and Vraja villagers sheltered safely under Govardhan mountain, warm golden light from Krishna aura",
                "video_prompt": "Peaceful atmosphere under the mountain shelter, divine flute music aura and happy calves"
            },
            {
                "scene_number": 4,
                "duration_seconds": 15,
                "description": "దేవేంద్రుడు ఐరావతము దిగివచ్చి శ్రీకృష్ణుని పాదాలపై పడి క్షమాపణ కోరుతున్న దృశ్యం.",
                "voice_text": "శ్రీకృష్ణుని దివ్య మహిమను చూసిన ఇంద్రుడు తన గర్వాన్ని వీడి, స్వామి పాదాలపై పడి శరణు వేడాడు.",
                "image_prompt": "Lord Indra bowing down in absolute surrender before Lord Krishna, golden divine rays, peaceful sky",
                "video_prompt": "Clouds parting, sunbeams breaking through as Indra surrenders his pride before Krishna"
            },
            {
                "scene_number": 5,
                "duration_seconds": 15,
                "description": "శ్రీకృష్ణుని శరణువేడిన భక్తునికి లభించే అభయ ముద్ర దివ్య దర్శనం.",
                "voice_text": "భగవంతుని శరణు వేడిన భక్తుడిని ఆయనే కొండంత అండగా నిలిచి కాపాడతాడనేది కృష్ణ లీల పరమార్థం. జై శ్రీకృష్ణ.",
                "image_prompt": "Beautiful close up of Lord Krishna in pitambara with abhaya hasta blessing, peacock feather crown, serene temple aura",
                "video_prompt": "Golden light illuminating Krishna enchanting smile and flute"
            }
        ],
        "voice_direction": {
            "tone": "మధురభక్తి, భరోసా మరియు దివ్య గాంభీర్యం.",
            "speed": "స్పష్టమైన, లయబద్ధమైన శైలి (నిమిషానికి 120 పదాలు).",
            "emotion": "ఆనందం మరియు పరవశం.",
            "language_style": "తేట తెలుగు, శ్రీకృష్ణ లీలామృతం."
        },
        "shorts_hooks": [
            "శ్రీకృష్ణుడు గోవర్ధన గిరిని ఎందుకు ఎత్తాడో తెలుసా?",
            "చిటికెన వేలితో కొండను ఎత్తిన శ్రీకృష్ణుని అద్భుత లీల!",
            "ఇంద్రుని గర్వాన్ని అణచిన ఆ ఏడు రోజుల వర్షం కథ!"
        ],
        "seo_metadata": {
            "description": "శ్రీకృష్ణుడు గోవర్ధన పర్వతాన్ని ఎందుకు ఎత్తాడు? ఇంద్రుని గర్వభంగం మరియు వ్రజ రక్షణ దివ్య గాథ. దివ్య దర్శనంలో శ్రీకృష్ణ లీలలు.",
            "keywords": ["శ్రీకృష్ణుడు", "గోవర్ధన గిరి", "గోవర్ధన ఉద్ధారణం", "గోకులం", "ఇంద్రుడు", "తెలుగు భక్తి", "దివ్య దర్శనం"],
            "hashtags": ["#శ్రీకృష్ణుడు", "#గోవర్ధనగిరి", "#కృష్ణలీలలు", "#దివ్యదర్శనం", "#తెలుగుభక్తి"],
            "category": "Education"
        }
    },
    "ram": {
        "title_options": [
            "శబరి ఎంగిలి పండ్లను శ్రీరాముడు ఎందుకు ఆనందంగా తిన్నాడు?",
            "శబరి భక్తి మరియు మర్యాదా పురుషోత్తముని అపార కరుణ",
            "జాతి భేదాలు లేని శ్రీరాముని సమతా దృక్పథం ఏమిటి?",
            "శబరి ఎదురుచూపులు ఫలించిన పవిత్ర ఘట్టం",
            "రామచంద్రుని పాదపద్మాలను చేరిన శబరి దివ్య భక్తి కథ"
        ],
        "primary_title": "శబరి ఎంగిలి పండ్లను శ్రీరాముడు ఎందుకు ఆనందంగా తిన్నాడు?",
        "hook": "చక్రవర్తి కుమారుడైన శ్రీరామచంద్రుడు ఒక వృద్ధురాలు కొరికి ఇచ్చిన పండ్లను ఎందుకు అమృతంగా స్వీకరించాడో తెలుసా? భగవంతునికి కావాల్సింది ఆడంబరాలు కాదు, నిర్మలమైన భక్తి మాత్రమే.",
        "audience": "భక్తులు, రామాయణ ప్రేమికులు మరియు ఆధ్యాత్మిక సాధకులు.",
        "story_arc": [
            "మొదటి భాగం: మాతంగ ఆశ్రమంలో శ్రీరాముని రాక కోసం శబరి చేసిన దశాబ్దాల నిరీక్షణ.",
            "రెండవ భాగం: శ్రీరాముడు ఆశ్రమానికి రావడం, తీపి పండ్లను కొరికి ప్రేమతో సమర్పించడం.",
            "మూడవ భాగం: భక్తికి కులమతాలు, హోదాలతో పనిలేదని శ్రీరాముడు లోకానికి చాటిచెప్పిన సందేశం."
        ],
        "script_structure": {
            "act_1_opening": "మాతంగ ఆశ్రమంలో వృద్ధురాలైన శబరి ప్రతిరోజూ దారంతా పూలు చల్లుతూ శ్రీరాముని కోసం ఎదురుచూసింది.",
            "act_2_explanation": "రాముడు లక్ష్మణునితో విచ్చేయగా, శబరి తన స్వామికి తీపి పండ్లను ప్రేమతో సమర్పించింది.",
            "act_3_message": "పత్రం, పుష్పం, ఫలం, తోయం - భక్తితో సమర్పిస్తే భగవంతుడు ఆనందంగా స్వీకరిస్తాడనే పరమ సత్యం."
        },
        "visual_plan": [
            {
                "scene_number": 1,
                "duration_seconds": 15,
                "description": "మాతంగ ఆశ్రమంలో వృద్ధురాలైన శబరి దారిలో పూలు చల్లుతూ శ్రీరాముని కోసం ఎదురుచూస్తున్న దృశ్యం.",
                "voice_text": "మాతంగ ఆశ్రమంలో వృద్ధురాలైన శబరి ప్రతిరోజూ దారంతా పూలు చల్లుతూ శ్రీరాముని రాక కోసం ఎదురుచూసింది.",
                "image_prompt": "Elderly devout Shabari scattering fresh flowers on forest path outside hermitage, serene morning sunlight, 8k",
                "video_prompt": "Slow camera moving through forest path showing Shabari waiting patiently with tears of devotion"
            },
            {
                "scene_number": 2,
                "duration_seconds": 20,
                "description": "కోదండధారియైన శ్రీరాముడు, లక్ష్మణునితో కలిసి శబరి ఆశ్రమంలోకి ప్రవేశిస్తున్న దృశ్యం.",
                "voice_text": "దశాబ్దాల నిరీక్షణ ఫలించి, కోదండపాణియైన శ్రీరామచంద్రుడు లక్ష్మణునితో కలిసి ఆశ్రమానికి విచ్చేశాడు.",
                "image_prompt": "Lord Sri Rama holding Kodanda bow with brother Lakshmana entering peaceful hermitage, radiant blue aura",
                "video_prompt": "Lord Rama smiling with deep compassion as he enters the modest hut"
            },
            {
                "scene_number": 3,
                "duration_seconds": 25,
                "description": "శబరి ప్రేమతో పండ్లను అందిస్తుండగా, శ్రీరాముడు ఆనందంతో స్వీకరిస్తున్న దృశ్యం.",
                "voice_text": "స్వామికి చేదు పండ్లు రాకూడదనే అమాయక భక్తితో శబరి పండ్లను రుచి చూసి ప్రేమతో సమర్పించింది.",
                "image_prompt": "Lord Rama lovingly accepting berries from elderly Shabari with profound joy and compassion, divine light",
                "video_prompt": "Heartwarming scene of Lord Rama eating wild berries offered with pure unconditional love"
            },
            {
                "scene_number": 4,
                "duration_seconds": 15,
                "description": "శ్రీరాముడు శబరిని దివ్య ఆశీస్సులతో అనుగ్రహిస్తున్న దృశ్యం.",
                "voice_text": "ఆ నిర్మలమైన భక్తికి పరవశించిన శ్రీరాముడు ఎంగిలి పండ్లను అమృతంలా ఆనందంగా స్వీకరించి ఆశీర్వదించాడు.",
                "image_prompt": "Lord Rama blessing Shabari with divine abhaya hasta, golden light enveloping the hermitage",
                "video_prompt": "Shabari shedding tears of bliss as Rama places comforting hand in blessing"
            },
            {
                "scene_number": 5,
                "duration_seconds": 15,
                "description": "శ్రీరామచంద్రుని శాంత సుందర దివ్య స్వరూపం, ధర్మ పరిరక్షణ ప్రతీక.",
                "voice_text": "భగవంతునికి కావాల్సింది కులహోదాలు కాదు, నిర్మలమైన భక్తి మాత్రమేనని శ్రీరాముడు నిరూపించాడు. జై శ్రీరామ్.",
                "image_prompt": "Majestic portrait of Lord Sri Rama with serene divine smile, glowing tilak, Kodanda bow, warm temple aura",
                "video_prompt": "Cinematic slow zoom into Lord Rama gentle and compassionate eyes, chanting Jai Sri Ram aura"
            }
        ],
        "voice_direction": {
            "tone": "కరుణారసం, భక్తిపారవశ్యం మరియు ప్రశాంతం.",
            "speed": "నెమ్మదిగా, భావయుక్తంగా (నిమిషానికి 110 పదాలు).",
            "emotion": "కన్నీళ్లు తెప్పించే భక్తి భావం.",
            "language_style": "సరళమైన, మధురమైన తెలుగు."
        },
        "shorts_hooks": [
            "శబరి ఎంగిలి పండ్లను రాముడు ఎందుకు తిన్నాడో తెలుసా?",
            "జాతి భేదాలు లేని శ్రీరాముని అపార కరుణ!",
            "శబరి ఎదురుచూపుల్లో దాగి ఉన్న భక్తి రహస్యం!"
        ],
        "seo_metadata": {
            "description": "శ్రీరాముడు శబరి పండ్లను ఎందుకు స్వీకరించాడు? భక్తికి కులమతాలు లేవని చాటిన రామాయణ పరమ పవిత్ర గాథ. దివ్య దర్శనంలో రామ తత్వం.",
            "keywords": ["శ్రీరాముడు", "శబరి", "రామాయణం", "శబరి భక్తి", "తెలుగు భక్తి", "దివ్య దర్శనం", "అయోధ్య రాముడు"],
            "hashtags": ["#శ్రీరాముడు", "#శబరిభక్తి", "#రామాయణం", "#జైశ్రీరామ్", "#దివ్యదర్శనం"],
            "category": "Education"
        }
    },
    "hanuman": {
        "title_options": [
            "హనుమంతుడు సంజీవని కోసం ద్రోణగిరి కొండనే ఎందుకు ఎత్తాడు?",
            "లక్ష్మణుని ప్రాణాలను కాపాడిన ఆంజనేయుని దివ్య పరాక్రమం",
            "ద్రోణగిరి పర్వతాన్ని తెచ్చిన హనుమాన్ భక్తి తత్పరత",
            "సూర్యోదయానికి ముందే సంజీవని తెచ్చిన మారుతి లీల",
            "హనుమంతుని కొండంత భక్తి: అసాధ్యాన్ని సుసాధ్యం చేసే మార్గం"
        ],
        "primary_title": "హనుమంతుడు సంజీవని కోసం ద్రోణగిరి కొండనే ఎందుకు ఎత్తాడు?",
        "hook": "లక్ష్మణుని ప్రాణాలు కాపాడేందుకు ఒక్క సంజీవని మూలిక అవసరమైతే, హనుమంతుడు ఏకంగా ద్రోణగిరి పర్వతాన్నే ఎందుకు మోసుకువచ్చాడో తెలుసా? స్వామి కార్యం కోసం ఆయన చేసిన ఆ సాహసం అద్భుతం.",
        "audience": "భక్తులు, హనుమాన్ ఉపాసకులు మరియు యువత.",
        "story_arc": [
            "మొదటి భాగం: లంకలో లక్ష్మణుడు నాగపాశంతో మూర్ఛిల్లడం మరియు శ్రీరాముని విషాదం.",
            "రెండవ భాగం: సంజీవని మూలికను గుర్తించలేక ద్రోణగిరి పర్వతాన్నే అమాంతం ఎత్తిన హనుమంతుడు.",
            "మూడవ భాగం: సమయస్ఫూర్తితో లక్ష్మణుని ప్రాణాలు కాపాడి రామకార్యాన్ని సాధించిన సందేశం."
        ],
        "script_structure": {
            "act_1_opening": "లంక యుద్ధభూమిలో లక్ష్మణుడు మూర్ఛిల్లగా, శ్రీరాముని హృదయం తీవ్రంగా విలపించింది.",
            "act_2_explanation": "సంజీవనిని గుర్తించలేక, ఆలస్యం చేయకుండా హనుమంతుడు ద్రోణగిరి కొండనే చేతిపై ఎత్తుకుని బయలుదేరాడు.",
            "act_3_message": "సేవలో శంకించకుండా, అసాధ్యాన్ని సుసాధ్యం చేయాలనే ఆంజనేయ సందేశం మనకు మార్గదర్శకం."
        },
        "visual_plan": [
            {
                "scene_number": 1,
                "duration_seconds": 15,
                "description": "లంక యుద్ధభూమిలో లక్ష్మణుడు మూర్ఛిల్లగా, శ్రీరాముడు దుఃఖిస్తున్న దృశ్యం.",
                "voice_text": "లంక యుద్ధభూమిలో లక్ష్మణుడు నాగపాశంతో మూర్ఛిల్లగా, శ్రీరాముని హృదయం తీవ్రంగా విలపించింది.",
                "image_prompt": "Lord Rama cradling unconscious Lakshmana on Lanka battlefield, surrounded by Vanara warriors, tragic sunset sky, 8k",
                "video_prompt": "Cinematic shot of sorrowful Lord Rama holding Lakshmana as evening winds sweep the battlefield"
            },
            {
                "scene_number": 2,
                "duration_seconds": 20,
                "description": "హనుమంతుడు ఆకాశమార్గంలో హిమాలయాల వైపు వాయువేగంతో ఎగురుతున్న దృశ్యం.",
                "voice_text": "లక్ష్మణుని ప్రాణాలు కాపాడే సంజీవని మూలిక కోసం హనుమంతుడు వాయువేగంతో హిమాలయాల వైపు దూసుకెళ్లాడు.",
                "image_prompt": "Lord Hanuman flying at immense speed across starlit skies towards snowy Himalayan peaks, golden aura radiating",
                "video_prompt": "Dynamic aerial shot of Hanuman soaring above clouds with wind roaring around his glowing form"
            },
            {
                "scene_number": 3,
                "duration_seconds": 25,
                "description": "హనుమంతుడు ద్రోణగిరి పర్వతాన్ని ఒక చేతిపై సునాయాసంగా ఎత్తి నిలబెట్టిన దృశ్యం.",
                "voice_text": "ద్రోణగిరిపై మూలికను గుర్తించలేక, ఏమాత్రం ఆలస్యం చేయకుండా కొండనే తన చేతిపై ఎత్తుకుని బయలుదేరాడు.",
                "image_prompt": "Majestic Lord Hanuman lifting the entire glowing Dronagiri mountain with one hand, divine resolve in eyes",
                "video_prompt": "Low angle epic shot of Hanuman uprooting and lifting the mighty mountain effortlessly into the sky"
            },
            {
                "scene_number": 4,
                "duration_seconds": 15,
                "description": "లంకలో సంజీవని సుగంధంతో లక్ష్మణుడు కళ్ళు తెరిచి శ్రీరాముని కౌగిలించుకుంటున్న దృశ్యం.",
                "voice_text": "సూర్యోదయానికి ముందే లంకను చేరుకుని, సంజీవని సుగంధంతో లక్ష్మణునికి పునర్జన్మ ప్రసాదించాడు.",
                "image_prompt": "Lakshmana waking up smiling, joyful Lord Rama hugging his brother, Vanaras cheering, morning sunlight",
                "video_prompt": "Heartwarming scene of Lakshmana opening eyes as Rama embraces him with tears of boundless relief"
            },
            {
                "scene_number": 5,
                "duration_seconds": 15,
                "description": "శ్రీరాముని పాదాల వద్ద చేతులు జోడించి నిలిచిన భక్త హనుమంతుని దివ్య రూపం.",
                "voice_text": "స్వామి సేవలో అసాధ్యాన్ని సుసాధ్యం చేయవచ్చని నిరూపించిన ఆంజనేయుని భక్తి మనందరికీ ఆదర్శం. జై హనుమాన్.",
                "image_prompt": "Devout Hanuman bowing with folded hands before Lord Rama, blessing aura shining bright",
                "video_prompt": "Slow zoom on Hanuman serene and humble expression in service of Sri Rama"
            }
        ],
        "voice_direction": {
            "tone": "వీరరసం, భక్తి మరియు స్ఫూర్తిదాయకం.",
            "speed": "ఉత్సాహపూరితమైన వేగం (నిమిషానికి 125 పదాలు).",
            "emotion": "రోమాంచితమైన అనుభూతి.",
            "language_style": "శక్తివంతమైన, ఉద్వేగభరితమైన తెలుగు."
        },
        "shorts_hooks": [
            "హనుమంతుడు కొండనే ఎందుకు ఎత్తాడో తెలుసా?",
            "ఒక్క మూలిక కోసం ద్రోణగిరి పర్వతాన్నే తెచ్చిన ఆంజనేయుడు!",
            "లక్ష్మణుని ప్రాణాలు కాపాడిన హనుమంతుని సమయస్ఫూర్తి!"
        ],
        "seo_metadata": {
            "description": "హనుమంతుడు సంజీవని కోసం ద్రోణగిరి పర్వతాన్ని ఎందుకు మోసుకొచ్చాడు? లక్ష్మణుని ప్రాణ రక్షణ మరియు మారుతి దివ్య పరాక్రమం. దివ్య దర్శనంలో హనుమాన్ కథ.",
            "keywords": ["హనుమంతుడు", "సంజీవని", "ద్రోణగిరి", "ఆంజనేయుడు", "లక్ష్మణుడు", "తెలుగు భక్తి", "దివ్య దర్శనం"],
            "hashtags": ["#హనుమంతుడు", "#సంజీవని", "#ఆంజనేయ", "#జైహనుమాన్", "#దివ్యదర్శనం"],
            "category": "Education"
        }
    },
    "durga": {
        "title_options": [
            "మహిషాసురుడిని సంహరించిన దుర్గాదేవి దివ్య శక్తి ఏమిటి?",
            "మహిషాసుర మర్దిని: అధర్మంపై దైవశక్తి సాధించిన పరమ విజయం",
            "అమ్మవారి పద్దెనిమిది చేతులలోని దివ్యాయుధాల రహస్యం",
            "నవరాత్రులలో దుర్గాదేవి ఆరాధన ఎందుకు అంత విశేషం?",
            "సింహవాహిని దుర్గామాత: భక్తులకు ఇచ్చే అభయ సందేశం"
        ],
        "primary_title": "మహిషాసురుడిని సంహరించిన దుర్గాదేవి దివ్య శక్తి ఏమిటి?",
        "hook": "సమస్త దేవతల శక్తులు ఏకమై అవతరించిన జగన్మాత దుర్గాదేవి మహిషాసురుడిని ఎలా సంహరించిందో తెలుసా? చెడు ఎంత బలమైనదైనా, చివరికి దైవశక్తి ముందు లొంగక తప్పదు.",
        "audience": "భక్తులు, శక్తి ఉపాసకులు మరియు స్త్రీ సాధకులు.",
        "story_arc": [
            "మొదటి భాగం: మహిషాసురుని అరాచకాలు మరియు దేవతల మొర.",
            "రెండవ భాగం: త్రిమూర్తులు మరియు దేవతల తేజస్సుతో దుర్గాదేవి ఆవిర్భావం.",
            "మూడవ భాగం: మహిషాసుర సంహారం మరియు ధర్మ విజయం."
        ],
        "script_structure": {
            "act_1_opening": "మహిషాసురుని అరాచకాలతో లోకాలు అల్లాడిపోగా, దేవతలందరూ త్రిమూర్తులను శరణు వేడారు.",
            "act_2_explanation": "దివ్య తేజస్సులతో పద్దెనిమిది చేతులతో సింహారూఢురాలై జగన్మాత దుర్గాదేవి అవతరించింది.",
            "act_3_message": "అధర్మం ఎంత బలమైనదైనా, చివరికి దైవశక్తి ముందు లొంగక తప్పదనే సందేశం."
        },
        "visual_plan": [
            {
                "scene_number": 1,
                "duration_seconds": 15,
                "description": "మహిషాసురుని సైన్యం దేవతలను వేధిస్తున్న అంధకార దృశ్యం.",
                "voice_text": "మహిషాసురుని అరాచకాలతో లోకాలు అల్లాడిపోగా, దేవతలందరూ త్రిమూర్తులను ప్రార్థించారు.",
                "image_prompt": "Dark stormy skies, demon Mahishasura spreading chaos, devas seeking refuge in prayers, intense lighting",
                "video_prompt": "Dramatic camera showing turbulent clouds and worried celestial devas praying"
            },
            {
                "scene_number": 2,
                "duration_seconds": 20,
                "description": "సమస్త దేవతల తేజస్సుల నుండి పద్దెనిమిది చేతులతో దుర్గాదేవి ఆవిర్భవిస్తున్న దృశ్యం.",
                "voice_text": "సమస్త దేవతల తేజస్సుల నుంచి పద్దెనిమిది భుజాలతో సింహవాహినియై జగన్మాత దుర్గాదేవి ఆవిర్భవించింది.",
                "image_prompt": "Radiant Goddess Durga emerging from divine light beam, 18 armed holding celestial weapons, riding golden lion, 8k",
                "video_prompt": "Blinding rays coalescing into magnificent form of Goddess Durga mounted on majestic roaring lion"
            },
            {
                "scene_number": 3,
                "duration_seconds": 25,
                "description": "దుర్గాదేవి సింహవాహనంపై ఆయుధాలతో రాక్షస సేనలను ఎదుర్కొంటున్న దృశ్యం.",
                "voice_text": "దేవతలు ప్రసాదించిన దివ్యాయుధాలతో మహిషాసురుని సేనలను అమ్మవారు మట్టుబెట్టింది.",
                "image_prompt": "Epic battle scene of Goddess Durga striking down demon forces with glowing trishula and chakra, divine power aura",
                "video_prompt": "Dynamic tracking shot of Goddess Durga celestial weapons swirling and striking down demonic darkness"
            },
            {
                "scene_number": 4,
                "duration_seconds": 15,
                "description": "త్రిశూలంతో మహిషాసురుడిని సంహరించి లోకాలను రక్షించిన విజయ ఘట్టం.",
                "voice_text": "ధర్మ సంరక్షణ కోసం సాక్షాత్తు త్రిశూలంతో మహిషాసురుని సంహరించి మహిషాసుర మర్దినిగా నిలిచింది.",
                "image_prompt": "Goddess Durga thrusting trishula into Mahishasura, triumphant divine expression, devas showering flowers, radiant golden aura",
                "video_prompt": "Slow motion climax of Goddess Durga defeating the demon as golden celestial flowers rain down"
            },
            {
                "scene_number": 5,
                "duration_seconds": 15,
                "description": "శాంతరూపిణియైన దుర్గామాత భక్తులకు అభయమిస్తున్న దివ్య మంగళ దర్శనం.",
                "voice_text": "అధర్మం ఎంత బలమైనదైనా దైవశక్తి ముందు నశించక తప్పదని అమ్మవారి అవతారం చాటిచెప్పింది. జై దుర్గామాత.",
                "image_prompt": "Serene and compassionate Goddess Durga in abhaya mudra, gentle motherly smile, glowing temple lamps",
                "video_prompt": "Peaceful close up of Durga Mata compassionate smiling eyes bestowing eternal peace"
            }
        ],
        "voice_direction": {
            "tone": "గంభీరం, భక్తిపూర్వకం మరియు విజయానందం.",
            "speed": "లయబద్ధమైన శైలి (నిమిషానికి 120 పదాలు).",
            "emotion": "దివ్య శక్తి అనుభూతి.",
            "language_style": "ఉదాత్తమైన తెలుగు."
        },
        "shorts_hooks": [
            "మహిషాసురుడిని చంపడానికి దుర్గాదేవి ఎందుకు అవతరించింది?",
            "పద్దెనిమిది చేతుల దుర్గాదేవి ఆయుధాల రహస్యం!",
            "అధర్మంపై అమ్మవారి సాధించిన అద్భుత విజయం!"
        ],
        "seo_metadata": {
            "description": "మహిషాసుర మర్దిని గాథ: దుర్గాదేవి మహిషాసురుడిని ఎలా సంహరించింది? నవరాత్రుల విశిష్టత మరియు అమ్మవారి దివ్య శక్తి. దివ్య దర్శనంలో పవిత్ర చరితం.",
            "keywords": ["దుర్గాదేవి", "మహిషాసుర మర్దిని", "నవరాత్రులు", "శక్తి", "తెలుగు భక్తి", "దివ్య దర్శనం", "అమ్మవారు"],
            "hashtags": ["#దుర్గాదేవి", "#మహిషాసురమర్దిని", "#నవరాత్రులు", "#శక్తిపూజ", "#దివ్యదర్శనం"],
            "category": "Education"
        }
    },
    "vamana": {
        "title_options": [
            "వామనుడు మూడు అడుగుల నేలను మాత్రమే ఎందుకు కోరాడు?",
            "బలి చక్రవర్తి అహంకారాన్ని కరిగించిన త్రివిక్రమ అవతార లీల",
            "వామన రూపంలో వచ్చిన శ్రీమహావిష్ణువు విశ్వరూప దర్శనం",
            "మూడు అడుగులతో బ్రహ్మాండాన్ని కొలిచిన వామనుని రహస్యం",
            "బలి దానగుణం మరియు వామనుని నిరంతర రక్షణ వెనుక ఉన్న కథ"
        ],
        "primary_title": "వామనుడు మూడు అడుగుల నేలను మాత్రమే ఎందుకు కోరాడు?",
        "hook": "లోకాలను జయించిన బలి చక్రవర్తి వద్దకు చిన్నారి వామనుడు వచ్చి కేవలం మూడు అడుగుల నేలను ఎందుకు దానంగా అడిగాడో తెలుసా? అహంకారాన్ని సమర్పిస్తే భగవంతుడే మనకు దాసుడవుతాడనేది ఈ లీల పరమార్థం.",
        "audience": "భక్తులు, పురాణ అధ్యయనకారులు మరియు ధర్మ సాధకులు.",
        "story_arc": [
            "మొదటి భాగం: యాగం చేస్తున్న బలి చక్రవర్తి సభకు వామనుని రాక.",
            "రెండవ భాగం: మూడు అడుగుల దానం అడగడం మరియు త్రివిక్రమ విశ్వరూపం.",
            "మూడవ భాగం: బలి శిరస్సుపై మూడవ అడుగు మరియు సుతల లోకానికి అధిపతిగా అనుగ్రహం."
        ],
        "script_structure": {
            "act_1_opening": "మహాబలి చక్రవర్తి యాగశాలకు చిరుప్రాయపు వామన బ్రహ్మచారి తేజస్సుతో విచ్చేశాడు.",
            "act_2_explanation": "శుక్రాచార్యుని హెచ్చరికను కాదని బలి దానం చేయగా, వామనుడు విశ్వరూప త్రివిక్రముడై లోకాలను కొలిచాడు.",
            "act_3_message": "భగవంతుని ముందు అహంకారాన్ని సమర్పిస్తే, ఆయన తానే మనకు రక్షకుడిగా నిలుస్తాడనే పరమ సత్యం."
        },
        "visual_plan": [
            {
                "scene_number": 1,
                "duration_seconds": 15,
                "description": "బలి చక్రవర్తి అశ్వమేధ యాగ వాటికకు వామన బ్రహ్మచారి తేజస్సుతో ప్రవేశిస్తున్న దృశ్యం.",
                "voice_text": "మహాబలి చక్రవర్తి యాగశాలకు చిరుప్రాయపు వామన బ్రహ్మచారి తేజస్సుతో విచ్చేశాడు.",
                "image_prompt": "Young glowing Vamana holding wooden umbrella and kamandalu entering grand yajna hall of King Bali, 8k",
                "video_prompt": "Cinematic tracking shot following radiant small Vamana entering the awe-struck court of King Bali"
            },
            {
                "scene_number": 2,
                "duration_seconds": 20,
                "description": "బలి చక్రవర్తి బంగారు కలశంతో వామనునికి దారపోస్తున్న పవిత్ర దృశ్యం.",
                "voice_text": "కోరిన కోరికగా కేవలం మూడు అడుగుల నేలను దానంగా ఇవ్వమని బలి చక్రవర్తిని కోరాడు.",
                "image_prompt": "King Bali pouring sacred water from golden jug into hands of Vamana, guru Shukracharya gesturing warning",
                "video_prompt": "Slow motion water pouring from golden spout into small hands of Vamana, sealing the cosmic promise"
            },
            {
                "scene_number": 3,
                "duration_seconds": 25,
                "description": "వామనుడు క్రమంగా బ్రహ్మాండమంత త్రివిక్రమ రూపంగా ఎదుగుతున్న అద్భుత దృశ్యం.",
                "voice_text": "దానం స్వీకరించిన తక్షణమే వామనుడు బ్రహ్మాండమంత త్రివిక్రమ విశ్వరూపాన్ని ధరించాడు.",
                "image_prompt": "Vamana expanding into cosmic Trivikrama form, one foot stepping on earth, another touching heavens, galaxy aura",
                "video_prompt": "Astounding scale shift as Vamana grows into colossal Trivikrama spanning the entire cosmos"
            },
            {
                "scene_number": 4,
                "duration_seconds": 15,
                "description": "బలి చక్రవర్తి చేతులు జోడించి మూడవ అడుగు కోసం తన శిరస్సును చూపుతున్న దృశ్యం.",
                "voice_text": "ఒక అడుగుతో భూమిని, రెండవ అడుగుతో ఆకాశాన్ని కొలిచి, మూడవ అడుగు కోసం బలి తన శిరస్సును సమర్పించాడు.",
                "image_prompt": "Humbled King Bali bowing down offering his head for the third stride of Trivikrama, peaceful surrender",
                "video_prompt": "King Bali with tears of devotion kneeling and pointing to his own head for the divine footstep"
            },
            {
                "scene_number": 5,
                "duration_seconds": 15,
                "description": "వామనమూర్తి బలిని ఆశీర్వదించి సుతల లోకానికి అధిపతిగా నియమిస్తున్న దృశ్యం.",
                "voice_text": "అహంకారాన్ని సమర్పిస్తే భగవంతుడే మనకు నిత్య రక్షకుడిగా నిలుస్తాడనేది వామనావతార సత్యం. ఓం నమో నారాయణాయ.",
                "image_prompt": "Lord Vishnu smiling benevolently at King Bali in Sutala realm, guarding his palace gates with mace",
                "video_prompt": "Lord Vishnu placing hand in eternal blessing on King Bali, golden realm shining with peace"
            }
        ],
        "voice_direction": {
            "tone": "శాంతం, తత్త్వబోధ మరియు భక్తి.",
            "speed": "స్పష్టమైన, సమతుల్య వేగం (నిమిషానికి 115 పదాలు).",
            "emotion": "ఆశ్చర్యం మరియు శరణాగతి.",
            "language_style": "తేట తెలుగు."
        },
        "shorts_hooks": [
            "వామనుడు మూడు అడుగుల నేలనే ఎందుకు అడిగాడు?",
            "బలి చక్రవర్తిని పాతాళానికి పంపిన అసలు కారణం!",
            "త్రివిక్రమ అవతారంలో దాగి ఉన్న గొప్ప తత్వం!"
        ],
        "seo_metadata": {
            "description": "వామనావతార రహస్యం: వామనుడు మూడు అడుగుల నేలను ఎందుకు కోరాడు? బలి చక్రవర్తి శరణాగతి మరియు త్రివిక్రమ లీల. దివ్య దర్శనంలో విష్ణు అవతారాలు.",
            "keywords": ["వామనుడు", "బలి చక్రవర్తి", "త్రివిక్రముడు", "దశావతారాలు", "విష్ణువు", "తెలుగు భక్తి", "దివ్య దర్శనం"],
            "hashtags": ["#వామనావతారం", "#త్రివిక్రమ", "#శ్రీమహావిష్ణువు", "#దశావతారం", "#దివ్యదర్శనం"],
            "category": "Education"
        }
    },
    "kurma": {
        "title_options": [
            "కూర్మావతారంలో విష్ణువు మందర పర్వతాన్ని ఎందుకు మోశాడు?",
            "క్షీరసాగర మథనం: కూర్మ రూపంలో శ్రీమహావిష్ణువు చూపిన ఓర్పు",
            "దేవదానవుల సంకటాన్ని తీర్చిన కూర్మావతార దివ్య లీల",
            "మందర పర్వతం మునిగిపోతుంటే కూర్మ స్వామి చేసిన అద్భుతం ఏమిటి?",
            "కూర్మావతార పరమార్థం: జీవితంలో ఓర్పు సాధించే అమోఘ మార్గం"
        ],
        "primary_title": "కూర్మావతారంలో విష్ణువు మందర పర్వతాన్ని ఎందుకు మోశాడు?",
        "hook": "పాలసముద్ర మథనంలో కొండ మునిగిపోతుంటే, శ్రీమహావిష్ణువు తాబేలు రూపంలో ఎందుకు రావాల్సి వచ్చిందో తెలుసా? లక్ష యోజనాల పర్వతాన్ని వీపుపై మోసిన ఆ కూర్మ లీల వెనుక మహా రహస్యం దాగి ఉంది.",
        "audience": "భక్తులు, పురాణ ప్రియులు మరియు సనాతన ధర్మ సాధకులు.",
        "story_arc": [
            "మొదటి భాగం: అమృతం కోసం సముద్ర మథనం మరియు మందర పర్వతం మునిగిపోవడం.",
            "రెండవ భాగం: శ్రీహరి లక్ష యోజనాల కూర్మ రూపం ధరించి పర్వతాన్ని మోయడం.",
            "మూడవ భాగం: ఓర్పు అనే గుణంతో అమృతాన్ని సాధించాలనే ఆధ్యాత్మిక సందేశం."
        ],
        "script_structure": {
            "act_1_opening": "పాలసముద్రంలో మందర పర్వతం మునిగిపోతుండగా దేవదానవులు ఆందోళనతో శ్రీహరిని శరణు వేడారు.",
            "act_2_explanation": "లక్ష యోజనాల విస్తీర్ణమున్న కూర్మ రూపంతో స్వామి పర్వతానికి ఆధారంగా నిలిచాడు.",
            "act_3_message": "జీవితంలో కష్టాలనే సముద్రాన్ని మథించేటప్పుడు ఓర్పు అనే ఆధారమే మనల్ని రక్షిస్తుందనే తత్వం."
        },
        "visual_plan": [
            {
                "scene_number": 1,
                "duration_seconds": 15,
                "description": "పాలసముద్రంలో మందర పర్వతం బరువుకు సముద్ర గర్భంలోకి మునిగిపోతున్న దృశ్యం.",
                "voice_text": "సముద్ర మథనం ప్రారంభమైన వేళ, బరువుకు మందర పర్వతం పాలసముద్రంలో మునిగిపోసాగింది.",
                "image_prompt": "Mount Mandara sinking into deep churning milk ocean, devas and asuras in panic, turbulent waves, 8k",
                "video_prompt": "Cinematic shot of colossal mountain slowly descending beneath foamy cosmic milk waves"
            },
            {
                "scene_number": 2,
                "duration_seconds": 20,
                "description": "శ్రీమహావిష్ణువు దివ్య కూర్మ రూపం దాల్చి సముద్రపు అడుగుభాగంలోకి ప్రవేశిస్తున్న దృశ్యం.",
                "voice_text": "దేవదానవుల ప్రార్థనలు ఆలకించిన శ్రీమహావిష్ణువు లక్ష యోజనాల కూర్మ రూపం ధరించాడు.",
                "image_prompt": "Gigantic divine Kurma tortoise diving into deep blue cosmic milk ocean, radiant shell glowing with Vishnu aura",
                "video_prompt": "Slow underwater descent of colossal radiant tortoise with gleaming sacred markings"
            },
            {
                "scene_number": 3,
                "duration_seconds": 25,
                "description": "కూర్మ స్వామి తన వీపుపై మందర పర్వతాన్ని సునాయాసంగా ధరించి నిలబెట్టిన అద్భుత దృశ్యం.",
                "voice_text": "సముద్రపు అగాధంలోకి దిగి, తన బలమైన వీపుపై మందర పర్వతాన్ని ఆధారంగా నిలిపాడు.",
                "image_prompt": "Massive Mount Mandara rotating smoothly balanced on the great shell of divine Kurma, sparkling foam, epic scale",
                "video_prompt": "Majestic view of mountain rotating steadily on the immovable back of Lord Kurma"
            },
            {
                "scene_number": 4,
                "duration_seconds": 15,
                "description": "సముద్ర మథనం విజయవంతమై కామధేనువు, లక్ష్మీదేవి, అమృతం ఉద్భవిస్తున్న దృశ్యం.",
                "voice_text": "ఆ ఆధారంతో మథనం విజయవంతమై లోకాలను కాపాడే అమృతం, లక్ష్మీదేవి ఉద్భవించాయి.",
                "image_prompt": "Goddess Lakshmi rising on lotus, celestial Kamadhenu, and glowing Amrita pot emerging from milk ocean, divine rays",
                "video_prompt": "Spectacular emergence of glowing treasures and Goddess Lakshmi from the golden churned waters"
            },
            {
                "scene_number": 5,
                "duration_seconds": 15,
                "description": "శ్రీమహావిష్ణువు అనుగ్రహ రూపాన్ని ధ్యానిస్తున్న దృశ్యం, ఓర్పుకు ప్రతీక.",
                "voice_text": "జీవితపు కష్టాల సాగరంలో నిలకడైన ఓర్పే మనకు రక్ష అని కూర్మావతారం బోధిస్తోంది. ఓం నమో భగవతే వాసుదేవాయ.",
                "image_prompt": "Lord Vishnu smiling peacefully in Vaikuntha with gentle eyes, blessing all worlds, warm temple diya light",
                "video_prompt": "Serene golden dissolve into tranquil face of Lord Vishnu blessing the devotee"
            }
        ],
        "voice_direction": {
            "tone": "గాంభీర్యం, స్థిరత్వం మరియు ప్రశాంతత.",
            "speed": "సమతుల్యమైన వేగం (నిమిషానికి 115 పదాలు).",
            "emotion": "ఆధ్యాత్మిక ధైర్యం.",
            "language_style": "తేట తెలుగు."
        },
        "shorts_hooks": [
            "విష్ణువు తాబేలు రూపంలో ఎందుకు వచ్చాడో తెలుసా?",
            "మందర పర్వతం మునిగిపోతుంటే విష్ణువు చేసిన అద్భుతం!",
            "కూర్మావతారంలో దాగి ఉన్న గొప్ప జీవన రహస్యం!"
        ],
        "seo_metadata": {
            "description": "కూర్మావతార పవిత్ర గాథ: సముద్ర మథనంలో విష్ణువు మందర పర్వతాన్ని ఎందుకు మోశాడు? అమృత మథనం మరియు ఓర్పు సందేశం. దివ్య దర్శనంలో దశావతారాలు.",
            "keywords": ["కూర్మావతారం", "సముద్ర మథనం", "విష్ణువు", "మందర పర్వతం", "అమృతం", "తెలుగు భక్తి", "దివ్య దర్శనం"],
            "hashtags": ["#కూర్మావతారం", "#సముద్రమథనం", "#దశావతారం", "#శ్రీమహావిష్ణువు", "#దివ్యదర్శనం"],
            "category": "Education"
        }
    },
    "narasimha": {
        "title_options": [
            "నరసింహ స్వామి స్తంభం నుంచే ఎందుకు ఆవిర్భవించాడు?",
            "ప్రహ్లాదుని నిశ్చల భక్తి: రాతి స్తంభాన్ని బద్దలుకొట్టిన దివ్య శక్తి",
            "హిరణ్యకశిపుని సంహరించిన ఉగ్ర నరసింహుని అవతార రహస్యం",
            "నర-మృగ రూపంలో శ్రీహరి ఎందుకు వచ్చాడు? అసలు సత్యం",
            "లక్ష్మీ నరసింహ స్వామి కరుణ: భక్తులకు లభించే అభయ వరం"
        ],
        "primary_title": "నరసింహ స్వామి స్తంభం నుంచే ఎందుకు ఆవిర్భవించాడు?",
        "hook": "సర్వాంతర్యామి అయిన భగవంతుడు రాతి స్తంభంలో కూడా ఉంటాడని ఒక చిన్నారి బాలుడు నమ్మితే, ఆ నమ్మకాన్ని నిజం చేయడానికి స్వామి ఎలా ఉద్భవించాడో తెలుసా? నరసింహావతార లీల భక్తి శక్తిని చాటిచెప్పే పరమ సత్యం.",
        "audience": "భక్తులు, నరసింహ ఉపాసకులు మరియు పురాణ సాధకులు.",
        "story_arc": [
            "మొదటి భాగం: రాక్షస సభలో హిరణ్యకశిపుని గర్వం మరియు ప్రహ్లాదుని అచంచల భక్తి.",
            "రెండవ భాగం: స్తంభం పగిలి ఉగ్ర నరసింహ స్వామి ఆవిర్భవించడం.",
            "మూడవ భాగం: సంధ్యా సమయంలో గడపపై సంహారం మరియు భక్తునికి అభయం."
        ],
        "script_structure": {
            "act_1_opening": "రాక్షస రాజసభలో నీ హరి ఎక్కడున్నాడని గర్వంతో గద్దించిన హిరణ్యకశిపుని సవాలును ప్రహ్లాదుడు స్వీకరించాడు.",
            "act_2_explanation": "స్తంభం బద్దలై అగ్నిజ్వాలలతో నర-మృగ రూపంలో స్వామి ఉగ్ర నరసింహ రూపం ధరించి ఆవిర్భవించాడు.",
            "act_3_message": "భగవంతుడు అంతటా ఉంటాడని, నిజమైన భక్తికి ఆయన ఎప్పుడూ రక్షకుడిగా నిలుస్తాడనే సందేశం."
        },
        "visual_plan": [
            {
                "scene_number": 1,
                "duration_seconds": 15,
                "description": "హిరణ్యకశిపుడు గదతో రాతి స్తంభాన్ని తాకి ప్రహ్లాదుడిని భయపెడుతున్న దృశ్యం.",
                "voice_text": "నీ హరి ఎక్కడున్నాడని గర్వంతో హిరణ్యకశిపుడు సభలోని రాతి స్తంభాన్ని గదతో బద్దలుకొట్టాడు.",
                "image_prompt": "Arrogant demon king Hiranyakashipu striking stone pillar with heavy golden mace, young Prahlada standing fearlessly with folded hands, 8k",
                "video_prompt": "Tense dramatic shot of mace striking stone pillar as cracks begin to glow bright orange"
            },
            {
                "scene_number": 2,
                "duration_seconds": 20,
                "description": "రాతి స్తంభం దద్దరిల్లి పగిలిపోగా, దివ్య అగ్నిజ్వాలలతో నరసింహ స్వామి ఉద్భవిస్తున్న దృశ్యం.",
                "voice_text": "ఆ క్షణమే భీకర గర్జనతో, అగ్నిజ్వాలల నడుమ నరసింహ స్వామి స్తంభం నుంచి ఆవిర్భవించాడు.",
                "image_prompt": "Stone pillar shattering with blinding divine light and fire, Lord Narasimha emerging with lion face, roaring, powerful aura",
                "video_prompt": "Slow motion explosion of stone pillar revealing fearsome and majestic Lord Narasimha"
            },
            {
                "scene_number": 3,
                "duration_seconds": 25,
                "description": "సంధ్యా సమయంలో ద్వారపు గడపపై హిరణ్యకశిపుని సంహరిస్తున్న ఉగ్ర నరసింహుని ఘట్టం.",
                "voice_text": "సంధ్యా సమయంలో, గడపపై హిరణ్యకశిపుని సంహరించి బాలుడైన ప్రహ్లాదుని రక్షించాడు.",
                "image_prompt": "Lord Narasimha slaying Hiranyakashipu on palace threshold during twilight sunset, divine cosmic balance restored",
                "video_prompt": "Cinematic wide angle at twilight showing the fulfillment of Brahma boons at palace doorway"
            },
            {
                "scene_number": 4,
                "duration_seconds": 15,
                "description": "ప్రహ్లాదుడు ప్రార్థించగా శాంతించిన శ్రీ లక్ష్మీ నరసింహ స్వామి దర్శనం.",
                "voice_text": "ప్రహ్లాదుని నిశ్చల భక్తికి పరవశించి, స్వామి లక్ష్మీ నరసింహునిగా శాంతించి అభయమిచ్చాడు.",
                "image_prompt": "Lord Narasimha pacified by Prahlada prayers, gentle loving expression, Goddess Lakshmi seated on lap, golden glow",
                "video_prompt": "Divine aura softens as Lord Narasimha places protective palm gently over child Prahlada head"
            },
            {
                "scene_number": 5,
                "duration_seconds": 15,
                "description": "శ్రీ నరసింహ స్వామి దివ్య అనుగ్రహ ముద్రతో భక్తులకు అభయమిస్తున్న పవిత్ర రూపం.",
                "voice_text": "నమ్మిన భక్తుడిని కాపాడటానికి భగవంతుడు ఏ రూపంలోనైనా ఆవిర్భవిస్తాడనేది నరసింహ గాథ. జై నరసింహ స్వామి.",
                "image_prompt": "Majestic portrait of Sri Lakshmi Narasimha Swamy in temple sanctum with glowing oil lamps and tulasi garlands",
                "video_prompt": "Slow reverent zoom on Lord Narasimha compassionate face, radiant and tranquil"
            }
        ],
        "voice_direction": {
            "tone": "రౌద్రం నుండి శాంతం, భక్తి మరియు గాంభీర్యం.",
            "speed": "నాటకీయమైన, స్పష్టమైన శైలి (నిమిషానికి 120 పదాలు).",
            "emotion": "దివ్య రక్షణ భరోసా.",
            "language_style": "ప్రామాణికమైన తెలుగు."
        },
        "shorts_hooks": [
            "నరసింహ స్వామి స్తంభంలోనే ఎందుకు వచ్చాడు?",
            "బాలుడు ప్రహ్లాదుని భక్తి చేసిన మహా అద్భుతం!",
            "హిరణ్యకశిపుని సంహారంలో దాగి ఉన్న బ్రహ్మ వరాల రహస్యం!"
        ],
        "seo_metadata": {
            "description": "నరసింహావతార వైభవం: నరసింహ స్వామి స్తంభం నుంచి ఎందుకు ఆవిర్భవించాడు? ప్రహ్లాద భక్తి మరియు హిరణ్యకశిపుని సంహారం. దివ్య దర్శనంలో నరసింహ లీల.",
            "keywords": ["నరసింహ స్వామి", "ప్రహ్లాదుడు", "హిరణ్యకశిపుడు", "దశావతారం", "తెలుగు భక్తి", "దివ్య దర్శనం", "లక్ష్మీ నరసింహ"],
            "hashtags": ["#నరసింహస్వామి", "#ప్రహ్లాదభక్తి", "#లక్ష్మీనరసింహ", "#దశావతారం", "#దివ్యదర్శనం"],
            "category": "Education"
        }
    },
    "7Kondala_Swami": {
        "title_options": [
            "తిరుమల ఏడుకొండల స్వామి శ్రీవారి దివ్య రహస్యాలు ఏమిటి?",
            "కలియుగ వైకుంఠం తిరుపతి: శ్రీ వేంకటేశ్వర స్వామి అవతార గాథ",
            "శ్రీనివాసుడు భక్తుల కోసం కొండపై ఎందుకు వెలిశాడు?",
            "తిరుమల ఆనంద నిలయం వెనుక ఉన్న పవిత్ర ఆధ్యాత్మిక సత్యం",
            "గోవింద నామస్మరణతో కలిగే అపార పుణ్య ఫలం ఏమిటి?"
        ],
        "primary_title": "తిరుమల ఏడుకొండల స్వామి శ్రీవారి దివ్య రహస్యాలు ఏమిటి?",
        "hook": "కోట్లాది భక్తులు 'గోవిందా గోవిందా' అంటూ ఏడుకొండలు ఎక్కి దర్శించుకునే తిరుమల శ్రీవారి లీలలు ఎందుకు అంత మహిమాన్వితమైనవో తెలుసా? కలియుగంలో భక్తులను రక్షించే ప్రత్యక్ష దైవమే మన శ్రీనివాసుడు.",
        "audience": "భక్తులు, తిరుమల యాత్రికులు మరియు శ్రీవారి సేవాపరులు.",
        "story_arc": [
            "మొదటి భాగం: శేషాచల పర్వతాలపై శ్రీనివాసుని దివ్య ఆగమనం.",
            "రెండవ భాగం: పద్మావతీ శ్రీనివాసుల పరిణయం మరియు భక్తుల పాపాలను హరించే వరం.",
            "మూడవ భాగం: నిత్యం శ్రీవారిని స్మరిస్తే లభించే శాంతి మరియు మోక్ష మార్గం."
        ],
        "script_structure": {
            "act_1_opening": "శేషాచల పర్వత శ్రేణులు, వేంకటాద్రిపై పచ్చని ప్రకృతి మధ్య తిరుమల క్షేత్రం విరాజిల్లుతోంది.",
            "act_2_explanation": "పద్మావతీ అమ్మవారితో పరిణయం, భక్తుల కోసం శ్రీవారు తానే రుణగ్రస్తుడై నిలిచాడు.",
            "act_3_message": "గోవింద నామస్మరణతో సకల పాపాలు నశించి మోక్షం లభిస్తుందనే కలియుగ ప్రత్యక్ష దైవ సందేశం."
        },
        "visual_plan": [
            {
                "scene_number": 1,
                "duration_seconds": 15,
                "description": "తిరుమల ఏడుకొండల ప్రకృతి సౌందర్యం మరియు ఆనంద నిలయ బంగారు గోపురం ప్రకాశిస్తున్న దృశ్యం.",
                "voice_text": "శేషాచల ఏడుకొండల పై భాగంలో ఆనంద నిలయ దివ్య విమానంతో తిరుమల క్షేత్రం విరాజిల్లుతోంది.",
                "image_prompt": "Golden Ananda Nilayam vimana tower of Tirumala glowing in morning sunlight, misty green Seshachalam hills, 8k",
                "video_prompt": "Aerial view gliding over serene lush Seshachalam seven hills revealing the golden temple dome"
            },
            {
                "scene_number": 2,
                "duration_seconds": 20,
                "description": "శ్రీనివాసుడు వకుళమాత ఆశ్రమంలో పాలు, పండ్లు ఆరగిస్తున్న ప్రశాంత దృశ్యం.",
                "voice_text": "భక్తుల కోరికలు తీర్చడానికి కలియుగ ప్రత్యక్ష దైవంగా శ్రీనివాసుడు వేంకటాద్రిపై వెలిశాడు.",
                "image_prompt": "Lord Srinivasa in simple hermit robes receiving fresh milk from loving mother Vakula Devi in humble forest hut",
                "video_prompt": "Touching moment of Vakula Mata serving Lord Srinivasa with motherly warmth"
            },
            {
                "scene_number": 3,
                "duration_seconds": 25,
                "description": "శ్రీ పద్మావతీ శ్రీనివాసుల కల్యాణ మహోత్సవం, దేవతలు పూలవాన కురిపిస్తున్న వైభవం.",
                "voice_text": "పద్మావతీ అమ్మవారితో దివ్య పరిణయం జరిగి, భక్తుల రక్షణే తన కర్తవ్యంగా స్వీకరించాడు.",
                "image_prompt": "Grand celestial wedding of Lord Srinivasa and Goddess Padmavathi, devas showering flowers, radiant ornaments",
                "video_prompt": "Spectacular celestial wedding with golden garlands, sacred fire, and radiant smiling divine couple"
            },
            {
                "scene_number": 4,
                "duration_seconds": 15,
                "description": "లక్షలాది భక్తులు గోవింద నామస్మరణతో కొండలను అధిరోహిస్తున్న దృశ్యం.",
                "voice_text": "ఏడుకొండలెక్కి వచ్చే భక్తుల కష్టాలను తీర్చి, కోరిన వరాలను ప్రసాదించే కల్పవృక్షం శ్రీవారు.",
                "image_prompt": "Thousands of joyful devotees walking up sacred stone steps of Tirumala hills chanting Govinda Govinda, evening lamps",
                "video_prompt": "Inspiring shot of pilgrims holding deepams climbing the sacred footpath with pure devotional fervor"
            },
            {
                "scene_number": 5,
                "duration_seconds": 15,
                "description": "శ్రీ వేంకటేశ్వర స్వామి దివ్య మంగళ విగ్రహ దర్శనం, శంఖ చక్రాలు మరియు అభయ హస్తం.",
                "voice_text": "గోవింద నామస్మరణతో సకల పాపాలు తొలగి శాంతి, సంపదలు లభిస్తాయి. ఏడుకొండలవాడా వెంకటరమణ గోవిందా గోవిందా.",
                "image_prompt": "Magnificent close up of Lord Venkateswara idol in Tirumala, glowing diamond crown, pitambara, katyavalambita and varada mudra",
                "video_prompt": "Reverent slow zoom onto the serene, compassionate face of Lord Balaji surrounded by camphor flame aura"
            }
        ],
        "voice_direction": {
            "tone": "పరమభక్తి, ఆర్తి మరియు ఆనందం.",
            "speed": "లయబద్ధమైన శైలి (నిమిషానికి 115 పదాలు).",
            "emotion": "ఆధ్యాత్మిక సమర్పణ.",
            "language_style": "మధురమైన తెలుగు, గోవింద నామస్మరణ."
        },
        "shorts_hooks": [
            "తిరుమల శ్రీవారి మెడలోని కాసులమాల రహస్యం ఏమిటి?",
            "ఏడుకొండల స్వామి కలియుగ దైవం ఎలా అయ్యాడు?",
            "గోవిందా అని పిలిస్తే శ్రీవారు పలికే అద్భుత గాథ!"
        ],
        "seo_metadata": {
            "description": "తిరుమల వేంకటేశ్వర స్వామి దివ్య వైభవం: కలియుగ దైవం శ్రీవారి అవతార రహస్యం మరియు ఏడుకొండల ప్రాశస్త్యం. దివ్య దర్శనంలో తిరుపతి గాథ.",
            "keywords": ["తిరుపతి", "వేంకటేశ్వర స్వామి", "బాలాజీ", "ఏడుకొండలు", "గోవిందా", "తెలుగు భక్తి", "దివ్య దర్శనం"],
            "hashtags": ["#తిరుపతి", "#వేంకటేశ్వరస్వామి", "#గోవిందా", "#ఏడుకొండలవాడా", "#దివ్యదర్శనం"],
            "category": "Education"
        }
    },
    "lord_vishnu": {
        "title_options": [
            "గజేంద్ర మోక్షం: మొసలి బారిన పడ్డ ఏనుగును విష్ణువు ఎలా కాపాడాడు?",
            "శ్రీమహావిష్ణువు గరుడవాహనారూఢుడై రావడానికి గల అసలు కారణం",
            "గజేంద్రుని ఆర్తనాదం మరియు భగవంతుని తక్షణ శరణాగతి రక్షణ",
            "తామర పువ్వు సమర్పణ: అహంకారం వీడితే లభించే మోక్షం",
            "గజేంద్ర మోక్షం ఇచ్చే పరమ ఆధ్యాత్మిక పాఠం ఏమిటి?"
        ],
        "primary_title": "గజేంద్ర మోక్షం: మొసలి బారిన పడ్డ ఏనుగును విష్ణువు ఎలా కాపాడాడు?",
        "hook": "మొసలి నోట్లో చిక్కుకుని వేయి సంవత్సరాలు పోరాడిన గజేంద్రుడు, చివరికి ఒక్క తామర పువ్వుతో శ్రీహరిని పిలిస్తే ఏం జరిగిందో తెలుసా? స్వశక్తి వీడి భగవంతుడిని శరణు వేడితే ఆయన క్షణాల్లో వచ్చి రక్షిస్తాడు.",
        "audience": "భక్తులు, భాగవత ప్రియులు మరియు సనాతన ధర్మ సాధకులు.",
        "story_arc": [
            "మొదటి భాగం: సరస్సులో జలకాలాడే గజేంద్రుని కాలును మొసలి పట్టుకోవడం.",
            "రెండవ భాగం: వేయి ఏళ్ళ పోరాటం తర్వాత నిస్సహాయుడై 'నారాయణా' అని ఆర్తనాదం చేయడం.",
            "మూడవ భాగం: సుదర్శన చక్రంతో శ్రీహరి గజేంద్రుని రక్షించి మోక్షం ప్రసాదించడం."
        ],
        "script_structure": {
            "act_1_opening": "తామర సరస్సులో గజేంద్రుడు కుటుంబంతో జలకాలాడగా, మొసలి ఆయన కాలు పట్టుకుంది.",
            "act_2_explanation": "బంధువులు వదిలివెళ్ళిన తర్వాత భగవంతుడే దిక్కని కమలాన్ని పైకెత్తి నారాయణా అని ఆర్తనాదం చేశాడు.",
            "act_3_message": "స్వశక్తి విఫలమైన చోట భగవత్ భక్తి ప్రారంభిస్తే, ఆయనే స్వయంగా వచ్చి రక్షిస్తాడనే అమృత సందేశం."
        },
        "visual_plan": [
            {
                "scene_number": 1,
                "duration_seconds": 15,
                "description": "తామర సరస్సులో మొసలి గజేంద్రుని కాలును గట్టిగా పట్టుకుని లాగుతున్న నాటకీయ దృశ్యం.",
                "voice_text": "తామర కొలనులో మొసలి పట్టుకు చిక్కి గజేంద్రుడు ప్రాణాపాయ స్థితిలో విలపించాడు.",
                "image_prompt": "Dramatic struggle in lotus lake, massive crocodile biting elephant Gajendra foot, splashing water, tense atmosphere, 8k",
                "video_prompt": "Cinematic water level shot of crocodile pulling struggling elephant in lotus filled lake"
            },
            {
                "scene_number": 2,
                "duration_seconds": 20,
                "description": "గజేంద్రుడు తొండంతో తామర పువ్వును ఆకాశం వైపు పైకెత్తి శ్రీహరిని శరణు వేడుతున్న దృశ్యం.",
                "voice_text": "తన బలం, బంధువులు విఫలమైన వేళ తొండంతో తామర పువ్వునెత్తి 'శ్రీమన్నారాయణా' అని ఆర్తనాదం చేశాడు.",
                "image_prompt": "Exhausted elephant Gajendra lifting a single fresh lotus trunk towards heaven in total surrender, weeping eyes",
                "video_prompt": "Emotional slow motion shot of elephant lifting glowing pink lotus flower towards golden sunset clouds"
            },
            {
                "scene_number": 3,
                "duration_seconds": 25,
                "description": "శ్రీమహావిష్ణువు గరుడునిపై సుదర్శన చక్రం చేతబట్టి మెరుపు వేగంతో దిగివస్తున్న దృశ్యం.",
                "voice_text": "భక్తుని పిలుపు విన్న క్షణంలోనే శ్రీమహావిష్ణువు గరుడారూఢుడై సుదర్శన చక్రంతో మెరుపులా దూసుకొచ్చాడు.",
                "image_prompt": "Lord Vishnu riding majestic celestial eagle Garuda, glowing Sudarshana Chakra spinning on finger, lightning speed descent",
                "video_prompt": "Epic descent from clouds: Lord Vishnu on golden-winged Garuda swooping down with blinding speed"
            },
            {
                "scene_number": 4,
                "duration_seconds": 15,
                "description": "సుదర్శన చక్రం మొసలి బంధాన్ని చేధించి గజేంద్రుని కాపాడుతున్న దివ్య ఘట్టం.",
                "voice_text": "సుదర్శన చక్రంతో మొసలి బంధాన్ని ఛేదించి గజేంద్రునికి మోక్షాన్ని అనుగ్రహించాడు.",
                "image_prompt": "Sudarshana chakra slicing the crocodile grip in bright burst of divine light, liberating the soul",
                "video_prompt": "Blinding circular flash of Sudarshana chakra liberating both souls in shimmering light burst"
            },
            {
                "scene_number": 5,
                "duration_seconds": 15,
                "description": "శ్రీమహావిష్ణువు గజేంద్రుని తలనిమిరి దివ్య లోకానికి తీసుకెళ్తున్న ప్రశాంత దృశ్యం.",
                "voice_text": "స్వశక్తి వీడి భగవంతుని శరణాగతి వేడితే ఆయనే స్వయంగా వచ్చి రక్షిస్తాడు. ఓం నమో నారాయణాయ.",
                "image_prompt": "Lord Vishnu lovingly caressing elephant head with abhaya hasta, golden divine light enveloping peaceful lake",
                "video_prompt": "Tranquil camera movement showing Lord Vishnu gentle hand resting on grateful elephant forehead"
            }
        ],
        "voice_direction": {
            "tone": "ఆర్తి, కరుణ మరియు దివ్య భరోసా.",
            "speed": "భావోద్వేగభరితమైన వేగం (నిమిషానికి 115 పదాలు).",
            "emotion": "శరణాగతి పరవశం.",
            "language_style": "శ్రీమద్భాగవత శైలి తేట తెలుగు."
        },
        "shorts_hooks": [
            "గజేంద్రుని పిలుపు విన్న విష్ణువు ఎందుకు అంత వేగంగా వచ్చాడు?",
            "మొసలి నోట్లో చిక్కుకున్న ఏనుగు చేసిన గొప్ప ప్రార్థన!",
            "ఒక్క తామర పువ్వుతో మోక్షాన్ని పొందిన గజేంద్రుని కథ!"
        ],
        "seo_metadata": {
            "description": "గజేంద్ర మోక్షం దివ్య గాథ: శ్రీమహావిష్ణువు గజేంద్రుడిని ఎలా రక్షించాడు? భాగవత పవిత్ర లీల మరియు శరణాగతి సందేశం. దివ్య దర్శనంలో విష్ణు వైభవం.",
            "keywords": ["గజేంద్ర మోక్షం", "విష్ణువు", "సుదర్శన చక్రం", "భాగవతం", "గరుడుడు", "తెలుగు భక్తి", "దివ్య దర్శనం"],
            "hashtags": ["#గజేంద్రమోక్షం", "#శ్రీమహావిష్ణువు", "#భాగవతం", "#శరణాగతి", "#దివ్యదర్శనం"],
            "category": "Education"
        }
    }
}


DEITY_NAME_TE: dict[str, str] = {
    "lord_shiva": "పరమశివుడు",
    "lord_vishnu": "శ్రీమహావిష్ణువు",
    "krishna": "శ్రీకృష్ణుడు",
    "ganesha": "శ్రీ గణేశుడు",
    "hanuman": "శ్రీ ఆంజనేయ స్వామి",
    "lakshmi_devi": "శ్రీ మహాలక్ష్మి అమ్మవారు",
    "narasimha": "శ్రీ లక్ష్మీ నరసింహ స్వామి",
    "ram": "శ్రీరామచంద్రుడు",
    "parvathi": "శ్రీ పార్వతీదేవి",
    "subramanya": "శ్రీ సుబ్రహ్మణ్య స్వామి",
    "ayyappa": "శ్రీ అయ్యప్ప స్వామి",
    "7Kondala_Swami": "శ్రీ వేంకటేశ్వర స్వామి",
    "durga": "శ్రీ దుర్గామాత",
    "vamana": "శ్రీ వామనావతారం",
    "kurma": "శ్రీ కూర్మావతారం"
}


TELUGU_BLUEPRINT_KEYWORDS: dict[str, list[str]] = {
    "lord_shiva": ["snake", "పాము", "vasuki", "వాసుకి", "హాలాహల", "halahala", "నీలకంఠ", "neelkanth", "throat", "neck", "serpent", "poison"],
    "ganesha": ["tusk", "broken tusk", "ఏకదంత", "దంతం", "tooth"],
    "krishna": ["govardhan", "గోవర్ధన", "govardhana", "గోవర్ధనగిరి", "చిటికెన వేలు"],
    "ram": ["shabari", "sabari", "శబరి", "fruit", "berries", "ఎంగిలి", "పండ్లు"],
    "hanuman": ["dronagiri", "ద్రోణగిరి", "sanjeevani", "sanjeevini", "సంజీవని", "carrying"],
    "durga": ["mahishasura", "మహిషాసుర", "demon", "lion", "సింహం", "arms"],
    "vamana": ["vamana", "వామన", "three steps", "three strides", "మూడు అడుగుల", "bali", "బలి"],
    "kurma": ["kurma", "కూర్మ", "mandara", "మందర", "tortoise", "turtle", "తాబేలు"],
    "narasimha": ["narasimha", "నరసింహ", "pillar", "స్తంభం", "hiranyakashipu", "హిరణ్యకశిపు"],
    "7Kondala_Swami": ["tirupati", "తిరుపతి", "venkateswara", "వేంకటేశ్వర", "balaji", "బాలాజీ", "ఏడుకొండల", "7kondala", "seven hills", "శ్రీనివాస", "శ్రీనివాసుడు", "శేషాచల", "seshachala", "తిరుమల", "tirumala", "గోవింద", "గోవిందా"],
    "lord_vishnu": ["gajendra", "గజేంద్ర", "moksha", "మోక్షం", "crocodile", "మొసలి", "elephant"],
}


def synthesize_telugu_brief(topic: str, deity_hint: str = "") -> dict[str, Any]:
    """
    Synthesizes a structured Telugu content brief for any devotional topic.
    If the topic matches one of our rich blueprints, returns that blueprint.
    Otherwise builds a dynamic blueprint following the same strict schema.
    Fails closed if both topic and deity_hint are empty.
    """
    if not (topic or "").strip() and not (deity_hint or "").strip():
        raise ValueError("Cannot synthesize Telugu content brief: missing topic and deity identifier.")

    topic_lower = (topic or "").lower()
    resolved_key = resolve_deity(topic, deity_hint=deity_hint, default=None)

    # 1. Semantic story match against rich blueprints
    candidate_keys = []
    if resolved_key and resolved_key in TELUGU_DEITY_BRIEFS:
        candidate_keys.append(resolved_key)
    hint_clean = (deity_hint or "").strip()
    for k in TELUGU_DEITY_BRIEFS:
        if hint_clean.lower() == k.lower() and k not in candidate_keys:
            candidate_keys.append(k)

    for k in candidate_keys:
        keywords = TELUGU_BLUEPRINT_KEYWORDS.get(k, [])
        if any(kw in topic_lower or kw in topic for kw in keywords):
            blueprint = json.loads(json.dumps(TELUGU_DEITY_BRIEFS[k], ensure_ascii=False))
            return blueprint

    # Strict Deity Isolation: If a candidate deity was resolved or hinted, use that
    # deity's blueprint directly rather than falling through to unrelated deities.
    if candidate_keys:
        k = candidate_keys[0]
        blueprint = json.loads(json.dumps(TELUGU_DEITY_BRIEFS[k], ensure_ascii=False))
        return blueprint

    # Check other blueprints in case topic directly names them without a candidate hint
    for k, keywords in TELUGU_BLUEPRINT_KEYWORDS.items():
        if any(kw in topic_lower or kw in topic for kw in keywords):
            blueprint = json.loads(json.dumps(TELUGU_DEITY_BRIEFS[k], ensure_ascii=False))
            return blueprint

    # 3. Dynamic synthesis for unlisted deities (e.g. Dattatreya, Surya, Yamaraj)
    subject_te = "శ్రీ భగవానుడు"
    if "dattatreya" in topic.lower() or "datta" in topic.lower() or "దత్తాత్రేయ" in topic:
        subject_te = "శ్రీ దత్తాత్రేయ స్వామి"
    elif resolved_key and resolved_key in DEITY_NAME_TE:
        subject_te = DEITY_NAME_TE[resolved_key]

    from src.script.generator import SPECIFIC_SUBJECT_GROUPS
    topic_clean_lower = (topic or "").lower()
    specific_subj_te = ""
    for g in SPECIFIC_SUBJECT_GROUPS:
        if any(kw in topic_clean_lower for kw in g if not any(ord(c) > 127 for c in kw)):
            te_candidates = [w for w in g if any(0x0C00 <= ord(c) <= 0x0C7F for c in w)]
            if te_candidates:
                specific_subj_te = sorted(te_candidates, key=len, reverse=True)[0]
                break

    clean_topic = topic.strip()
    if specific_subj_te and specific_subj_te not in subject_te and subject_te not in specific_subj_te:
        topic_display_te = f"{specific_subj_te} {subject_te}".strip()
    else:
        topic_display_te = specific_subj_te or subject_te

    title_options = [
        f"{topic_display_te} దివ్య వైభవం: పవిత్ర గాథ మరియు ఆధ్యాత్మిక రహస్యం",
        f"{topic_display_te} అనుగ్రహం: నిత్య జీవితంలో ఎదురయ్యే కష్టాల నివారణ",
        f"{topic_display_te} పవిత్ర లీల: భక్తులకు ఇచ్చే అమృత సందేశం",
        f"{topic_display_te} మహిమ: భక్తులను రక్షించే పరమ దివ్య శక్తి",
        f"{topic_display_te} దివ్య దర్శనం: మోక్షాన్ని ప్రసాదించే పవిత్ర మార్గం"
    ]
    primary_title = title_options[0]

    hook = (
        f"సనాతన ధర్మంలో ఎంతో ప్రాముఖ్యత కలిగిన {topic_display_te} పవిత్ర గాథ గురించి మీకు తెలుసా? "
        f"ఈ కథ కేవలం పురాణ విశేషం మాత్రమే కాదు, మన జీవితాల్లో ప్రతికూలతలను అధిగమించి "
        f"ఆధ్యాత్మిక శాంతిని పొందేందుకు ఒక దివ్య మార్గదర్శి."
    )

    story_arc = [
        f"మొదటి భాగం: {topic_display_te} యొక్క ప్రాముఖ్యత మరియు పురాణ నేపథ్యం.",
        f"రెండవ భాగం: ఈ పవిత్ర లీల వెనుక ఉన్న దైవ సంకల్పం మరియు ఆంతర్యం.",
        f"మూడవ భాగం: నిత్య జీవితంలో అనుసరించదగిన ఆధ్యాత్మిక సూత్రం మరియు పరమ సందేశం."
    ]

    script_structure = {
        "act_1_opening": f"పవిత్రమైన {topic_display_te} నేపథ్యాన్ని మనసారా స్మరిస్తూ భక్తితో ఈ దివ్య కథను ప్రారంభిద్దాం.",
        "act_2_explanation": f"పురాణ గ్రంథాలలో వివరించిన లీలలను అనుసరిస్తూ {topic_display_te} అపార దైవ సంకల్పాన్ని తెలుసుకుందాం.",
        "act_3_message": f"సదా ధర్మ మార్గంలో నడవాలని, సద్గుణాలతో జీవితాన్ని ధన్యం చేసుకోవాలని {topic_display_te} బోధిస్తున్నాడు."
    }

    visual_plan = [
        {
            "scene_number": 1,
            "duration_seconds": 15,
            "description": f"{clean_topic} ప్రాముఖ్యతను తెలిపే దివ్య దేవాలయ ప్రాంగణ దృశ్యం.",
            "voice_text": f"సనాతన ధర్మంలో అత్యంత మహిమాన్వితమైన {topic_display_te} దివ్య లీల మన మనస్సుకు ఎనలేని ప్రశాంతతను చేకూరుస్తుంది.",
            "image_prompt": f"Cinematic divine Indian temple sanctorum, warm golden diya lamps glowing, ancient sacred atmosphere depicting {clean_topic}, 8k",
            "video_prompt": f"Slow camera tracking across sacred temple bells and soft incense smoke with golden sunbeams"
        },
        {
            "scene_number": 2,
            "duration_seconds": 20,
            "description": f"పురాణ గాథలలోని దివ్య లీలను ప్రతిబింబించే అద్భుత దృశ్యం.",
            "voice_text": f"పురాణ గ్రంథాలలో వివరించిన ఈ పవిత్ర గాథ ద్వారా భగవంతుని దివ్య సంకల్పం మరియు భక్తుల రక్షణ స్పష్టమవుతాయి.",
            "image_prompt": f"Epic mythological scene illustrating {clean_topic}, glowing celestial light, traditional devotional art style, dramatic clouds",
            "video_prompt": f"Dynamic panning shot showing mythic celestial beings and divine radiance"
        },
        {
            "scene_number": 3,
            "duration_seconds": 25,
            "description": f"కథలోని ముఖ్య ఘట్టం, దైవశక్తి ఆవిర్భావ దర్శనం.",
            "voice_text": f"జీవితంలో క్లిష్ట సమయాలు ఎదురైనప్పుడు ధర్మ మార్గంలో నిలబడితే భగవంతుని అపార కరుణ ఎల్లప్పుడూ తోడుగా నిలుస్తుంది.",
            "image_prompt": f"Sacred divine blessing moment of {clean_topic}, golden aura expanding, serene compassionate expressions, highly detailed",
            "video_prompt": "Golden light expanding from the center, slow motion divine blessing shower"
        },
        {
            "scene_number": 4,
            "duration_seconds": 15,
            "description": f"భక్తులు చేతులు జోడించి పరవశంతో ప్రార్థిస్తున్న పవిత్ర దృశ్యం.",
            "voice_text": f"భక్తి శ్రద్ధలతో ఆ దైవాన్ని స్మరిస్తూ, నిత్య జీవితంలో సత్య ధర్మాలను ఆచరించడమే నిజమైన పూజ.",
            "image_prompt": "Devout pilgrims with folded hands filled with devotion, soft temple lamps reflecting in eyes",
            "video_prompt": "Gentle zoom on praying hands holding fresh jasmine and tulasi flowers"
        },
        {
            "scene_number": 5,
            "duration_seconds": 15,
            "description": f"ప్రశాంత ధ్యాన ముద్రలో నిమగ్నమైన సాధకుడు, ఆధ్యాత్మిక శాంతి ప్రతీక.",
            "voice_text": f"సమస్త లోకాలకు శాంతి, సౌభాగ్యాలు కలగాలని మనసారా ప్రార్థిద్దాం. ఓం శాంతిః శాంతిః శాంతిః.",
            "image_prompt": "Serene individual meditating in peaceful natural sunrise, glowing lotus aura overlay, symbolic wisdom",
            "video_prompt": "Peaceful transition from glowing diya flame to radiant morning horizon"
        }
    ]

    voice_direction = {
        "tone": "భక్తిపూర్వకం, ప్రశాంతం మరియు గాంభీర్యం.",
        "speed": "సహజమైన వేగం (నిమిషానికి 115 పదాలు).",
        "emotion": "ఆధ్యాత్మిక శాంతి.",
        "language_style": "తేట తెలుగు, స్పష్టమైన ఉచ్ఛారణ."
    }

    shorts_hooks = [
        f"{topic_display_te} వెనుక ఉన్న అసలు రహస్యం తెలుసా?",
        f"పురాణాలలో దాగి ఉన్న {topic_display_te} అద్భుత కథ!",
        f"{topic_display_te} ద్వారా భగవంతుడు మనకిచ్చే దివ్య సందేశం!"
    ]

    seo_metadata = {
        "description": f"{clean_topic} ప్రాముఖ్యత ఏమిటి? సనాతన ధర్మం మరియు పురాణాలలోని పవిత్ర గాథ. దివ్య దర్శనంలో ఆధ్యాత్మిక సత్యాలు.",
        "keywords": [clean_topic, "తెలుగు భక్తి", "పురాణ కథలు", "సనాతన ధర్మం", "దివ్య దర్శనం", "భక్తి మార్గం"],
        "hashtags": ["#దివ్యదర్శనం", "#తెలుగుభక్తి", "#సనాతనధర్మం", "#భక్తికథలు"],
        "category": "Education"
    }

    return {
        "title_options": title_options,
        "primary_title": primary_title,
        "hook": hook,
        "audience": "భక్తులు, పురాణ ఆసక్తిపరులు మరియు ఆధ్యాత్మిక సాధకులు.",
        "story_arc": story_arc,
        "script_structure": script_structure,
        "visual_plan": visual_plan,
        "voice_direction": voice_direction,
        "shorts_hooks": shorts_hooks,
        "seo_metadata": seo_metadata
    }


def synthesize_telugu_script_from_brief(brief: dict[str, Any], content_type: str = "short") -> dict[str, Any]:
    """
    Synthesizes a complete, production-ready Telugu script conforming strictly
    to `validate_script_output` schema based on brief metadata.
    Guarantees pure spoken devotional narration with ZERO leaked prompt directions.
    """
    title = (brief.get("primary_title") or (brief.get("title_options") or [""])[0] or "దివ్య దర్శనం").strip()
    struct = brief.get("script_structure") or {}
    visuals = brief.get("visual_plan") or []
    hook = brief.get("hook", "")

    opening = struct.get("act_1_opening", "")
    explanation = struct.get("act_2_explanation", "")
    message = struct.get("act_3_message", "")

    scenes: list[dict[str, Any]] = []
    if visuals:
        for i, v in enumerate(visuals, start=1):
            desc = v.get("description", title)
            # Pristine spoken voice text
            raw_voice = v.get("voice_text") or (opening if i == 1 else explanation if i == 2 else message if i == 3 else "")
            if not raw_voice:
                raw_voice = clean_spoken_narration(desc)

            clean_text = clean_spoken_narration(raw_voice)
            is_valid_narr, leak_issues = validate_spoken_narration(clean_text)
            if not is_valid_narr:
                # If stage meta-word was still present, fallback to clean narrative structure
                clean_text = clean_spoken_narration(opening if i <= 2 else explanation if i <= 4 else message)

            scenes.append({
                "scene": i,
                "duration_seconds": v.get("duration_seconds", 15),
                "visual_reference": desc,
                "voice_text": clean_text,
                "emotion": "భక్తిపూర్వకం మరియు ప్రశాంతం",
            })
    else:
        clean_text = clean_spoken_narration(f"దివ్య దర్శనానికి స్వాగతం. {hook} {opening} {explanation} {message}")
        scenes = [{
            "scene": 1,
            "duration_seconds": 45,
            "visual_reference": title,
            "voice_text": clean_text,
            "emotion": "భక్తిపూర్వకం మరియు ప్రశాంతం",
        }]

    # Full narration is composed strictly from scene voice texts
    narration = " ".join([s["voice_text"] for s in scenes]).strip()

    # Scale durations if needed
    ct = (content_type or "short").lower()
    total_dur = sum(s["duration_seconds"] for s in scenes)
    if ct == "short" and (total_dur < 35 or total_dur >= 60):
        per_scene = max(8, 45 // len(scenes))
        for s in scenes:
            s["duration_seconds"] = per_scene
        diff = 45 - sum(s["duration_seconds"] for s in scenes)
        scenes[-1]["duration_seconds"] += diff
        total_dur = sum(s["duration_seconds"] for s in scenes)

    # 3 Shorts scripts
    shorts_hooks = brief.get("shorts_hooks") or [f"{title} గురించి మీకు తెలుసా?"]
    shorts_scripts: list[dict[str, Any]] = []
    for i in range(3):
        hk = shorts_hooks[i] if i < len(shorts_hooks) else f"{title} - భాగం {i+1}"
        shorts_scripts.append({
            "title": f"{title[:28]}",
            "hook": hk,
            "body": f"{hk} {narration[:140]} నిత్యం పవిత్ర దివ్య దర్శనం కోసం లైక్ చేసి సబ్‌స్క్రైబ్ చేయండి!",
        })

    retention_hooks = [
        f"{title} వెనుక ఉన్న అత్యంత ముఖ్యమైన ఆధ్యాత్మిక రహస్యం ఏమిటి?",
        f"ఈ పవిత్ర గాథ ద్వారా మనం తెలుసుకోవాల్సిన పరమ సత్యం!",
    ]

    return {
        "title": title,
        "duration_seconds": int(total_dur),
        "narration": narration,
        "scene_scripts": scenes,
        "retention_hooks": retention_hooks,
        "shorts_scripts": shorts_scripts,
        "language_code": "te-IN",
        "generation_source": "template_fallback",
    }
