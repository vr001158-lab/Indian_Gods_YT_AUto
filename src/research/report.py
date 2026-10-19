# src/research/report.py
# Hardened v0.2 — coordinates collection, scoring, dedup, gap analysis, and output.

import sys
import json
import time
from pathlib import Path

from src.research.collector import ResearchCollector
from src.research.scorer   import TopicScorer
from src.research.dedup    import deduplicate_topics, _fingerprint
from src.decision.validator import _load_published_topics

OUTPUT_DIR = Path("data/research")
HISTORY_FILE = Path("data/publishing_history.json")

# ── Topic seed list ───────────────────────────────────────────────────────────
SUGGESTED_TOPICS = [
    {
        "topic":           "Why Lord Ganesha Has One Broken Tusk",
        "category":        "Hindu mythology",
        "deity":           "ganesha",
        "suggested_angle": (
            "The story behind Ganesha's broken tusk teaches deeper lessons on "
            "sacrifice than the popular version most people know."
        ),
    },
    {
        "topic":           "Why Lord Shiva Wears a Snake Around His Neck",
        "category":        "Stories of deities",
        "deity":           "shiva",
        "suggested_angle": (
            "The snake Vasuki around Shiva's neck represents the mastery of ego and "
            "poison — we explore the lesser-known cosmic context that placed him there."
        ),
    },
    {
        "topic":           "The Mystery of Narasimha Avatar",
        "category":        "Hindu mythology",
        "deity":           "vishnu",
        "suggested_angle": (
            "Why Vishnu had to manifest as a half-man, half-lion, and the unique "
            "grammatical loopholes in Hiranyakashipu's death conditions."
        ),
    },
    {
        "topic":           "Why Hanuman Covered Himself in Sindoor",
        "category":        "Traditions",
        "deity":           "hanuman",
        "suggested_angle": (
            "Hanuman's absolute devotion to Rama led him to paint his entire body "
            "orange — we unpack the literal and symbolic dimensions of this act."
        ),
    },
    {
        "topic":           "The Story of Krishna Lifting Govardhan Hill",
        "category":        "Stories of deities",
        "deity":           "krishna",
        "suggested_angle": (
            "More than a display of strength, this story represents the shift of "
            "devotion from nature worship (Indra) to direct spiritual connection."
        ),
    },
    {
        "topic":           "How Goddess Lakshmi Emerged from Samudra Manthan",
        "category":        "Spiritual history",
        "deity":           "lakshmi",
        "suggested_angle": (
            "The churning of the cosmic ocean yields spiritual gems — we detail why "
            "Lakshmi chose Vishnu as her eternal consort over other gods."
        ),
    },
    {
        "topic":           "Why We Perform Aarti and Ring Bells in Temples",
        "category":        "Traditions",
        "deity":           "traditions",
        "suggested_angle": (
            "The acoustic symbolism and historical roots of temple rituals explained "
            "clearly for a modern devotional audience."
        ),
    },
    {
        "topic":           "The Hidden Meaning of Lord Shiva's Trishul",
        "category":        "Symbolism",
        "deity":           "shiva",
        "suggested_angle": (
            "Shiva's trident governs the three gunas (Sattva, Rajas, Tamas) and the "
            "states of waking, dreaming, and deep sleep."
        ),
    },
    {
        "topic":           "Mysteries of Tirupati Balaji Temple Wealth",
        "category":        "Historical/religious places",
        "deity":           "vishnu",
        "suggested_angle": (
            "Why Lord Venkateswara took a massive loan from Kubera, and why devotees "
            "donate their hair to repay the cosmic interest."
        ),
    },
    {
        "topic":           "Why Ganesha's Mouse Is His Vehicle",
        "category":        "Hindu mythology",
        "deity":           "ganesha",
        "suggested_angle": (
            "The tiny mouse as Ganesha's vahana is not comic relief — it represents "
            "mastery over desire that gnaws invisibly at the mind."
        ),
    },
    {
        "topic":           "Why Shiva Drank Cosmic Poison",
        "category":        "Stories of deities",
        "deity":           "shiva",
        "suggested_angle": (
            "Neelkanth is more than a blue throat: Halahala shows why the cosmos "
            "needed a god willing to hold poison without becoming poison."
        ),
    },
    {
        "topic":           "Why Nandi Guards Kailash",
        "category":        "Symbolism",
        "deity":           "shiva",
        "suggested_angle": (
            "Nandi is not merely a bull statue — waiting in stillness before Shiva "
            "is the discipline that turns devotion into dharma."
        ),
    },
    {
        "topic":           "Why Vishnu Rests on Shesha",
        "category":        "Stories of deities",
        "deity":           "vishnu",
        "suggested_angle": (
            "Ananta Shesha is the remaining that never ends — we unpack why "
            "preservation is portrayed as rest, not as endless labour."
        ),
    },
    {
        "topic":           "Why Krishna Plays the Flute",
        "category":        "Stories of deities",
        "deity":           "krishna",
        "suggested_angle": (
            "The hollow flute is the devotee's emptied ego — we explore why "
            "Krishna's music calls without commanding."
        ),
    },
    {
        "topic":           "Why Hanuman Crossed the Ocean",
        "category":        "Hindu mythology",
        "deity":           "hanuman",
        "suggested_angle": (
            "The leap to Lanka is not only strength — it is the moment Hanuman "
            "remembered who he was after forgetting his own power."
        ),
    },
    {
        "topic":           "Why Rama Drew His Bow",
        "category":        "Stories of deities",
        "deity":           "rama",
        "suggested_angle": (
            "Kodanda is dharma under pressure — we look at when Rama chose the "
            "bow and what that choice costs a righteous king."
        ),
    },
    {
        "topic":           "Why Lakshmi Chooses the Lotus",
        "category":        "Symbolism",
        "deity":           "lakshmi",
        "suggested_angle": (
            "Prosperity that stays unstained in muddy water — the lotus seat "
            "explains why abundance and purity are taught together."
        ),
    },
    {
        "topic":           "Why Temple Lamps Stay Lit Overnight",
        "category":        "Traditions",
        "deity":           "traditions",
        "suggested_angle": (
            "Akhanda deepam is not decoration — continuous flame marks a vow "
            "that the sacred presence is never left in darkness."
        ),
    },
    {
        "topic":           "Why Tulsi Is Planted in Courtyards",
        "category":        "Traditions",
        "deity":           "traditions",
        "suggested_angle": (
            "The household tulsi vrindavan is a living shrine — we explain the "
            "devotional and seasonal logic behind planting it at home."
        ),
    },
    {
        "topic":           "Why Rudraksha Beads Are Worn",
        "category":        "Traditions",
        "deity":           "shiva",
        "suggested_angle": (
            "Rudraksha is described as Shiva's tear — we separate folklore from "
            "the practice of wearing mala as a reminder of inner stillness."
        ),
    },
    {
        "topic":           "Why Conch Shells Are Blown at Dawn",
        "category":        "Traditions",
        "deity":           "traditions",
        "suggested_angle": (
            "Shankha nada is treated as an auspicious opening of the day — we "
            "unpack acoustic, ritual, and symbolic reasons for the dawn conch."
        ),
    },
    {
        "topic":           "Why Ganga Flows from Shiva's Hair",
        "category":        "Hindu mythology",
        "deity":           "shiva",
        "suggested_angle": (
            "Catching Ganga in jata is not a special effect — it is the story of "
            "force tamed so a celestial river can nourish the earth."
        ),
    },
    {
        "topic":           "Why Sudarshana Chakra Never Misses",
        "category":        "Symbolism",
        "deity":           "vishnu",
        "suggested_angle": (
            "The discus is time and precise justice — we explore why Vishnu's "
            "weapon is said to return only after dharma is restored."
        ),
    },
    {
        "topic":           "Why Ayodhya Is Called Rama's Birthplace",
        "category":        "Historical/religious places",
        "deity":           "rama",
        "suggested_angle": (
            "Janmabhoomi is more than geography — we look at why Ayodhya is "
            "remembered as the city where maryada took human form."
        ),
    },
    {
        "topic":           "Why Goddess Durga Has Ten Arms",
        "category":        "Hindu mythology",
        "deity":           "durga",
        "suggested_angle": (
            "Each weapon in Durga's ten hands represents a divine potency combined "
            "to conquer Mahishasura — we detail the symbolic power behind each emblem."
        ),
    },
    {
        "topic":           "Why Saraswati Holds the Veena and Sacred Book",
        "category":        "Symbolism",
        "deity":           "saraswati",
        "suggested_angle": (
            "Saraswati represents pure knowledge and cosmic harmony — the veena "
            "tunes the intellect while the sacred manuscript embodies eternal truth."
        ),
    },
    {
        "topic":           "Why Lord Brahma Is Rarely Worshipped in Temples",
        "category":        "Stories of deities",
        "deity":           "brahma",
        "suggested_angle": (
            "The curse of Bhrigu and the pillar of light — we unpack why creation's "
            "architect lacks active temple worship across India."
        ),
    },
    {
        "topic":           "Why Kartikeya Rides a Peacock",
        "category":        "Hindu mythology",
        "deity":           "kartikeya",
        "suggested_angle": (
            "Murugan's peacock vahana represents the conquest of pride and vanity, "
            "turning ego into a loyal vessel for spiritual warfare."
        ),
    },
    {
        "topic":           "Why Lord Jagannath Has Large Round Eyes and Wooden Form",
        "category":        "Historical/religious places",
        "deity":           "vishnu",
        "suggested_angle": (
            "The sacred wooden daru form of Puri Jagannath hides ancient tribal and "
            "Vedic origins — we detail the divine unfulfilled craft of Vishwakarma."
        ),
    },
    {
        "topic":           "Why Parvati Performed Severe Tapas for Shiva",
        "category":        "Stories of deities",
        "deity":           "parvati",
        "suggested_angle": (
            "Aparna's intense penance demonstrates that true union requires equal "
            "spiritual stature — transforming devotion into unshakeable power."
        ),
    },
    {
        "topic":           "Why Surya Dev Rides a Chariot of Seven Horses",
        "category":        "Symbolism",
        "deity":           "surya",
        "suggested_angle": (
            "The seven horses of Surya represent the seven colors of light, the seven "
            "days of the week, and the vital rays that sustain terrestrial life."
        ),
    },
    {
        "topic":           "Why Yamraj Rides a Buffalo and Holds the Noose",
        "category":        "Hindu mythology",
        "deity":           "yama",
        "suggested_angle": (
            "Yama is the lord of cosmic justice (Dharmaraja) — his buffalo represents "
            "unyielding momentum, while the pasha binds only the karma of the soul."
        ),
    },
    {
        "topic":           "Why Lord Dhanvantari Emerged with Amrita in Samudra Manthan",
        "category":        "Spiritual history",
        "deity":           "dhanvantari",
        "suggested_angle": (
            "Dhanvantari bringing the pot of nectar marks the birth of Ayurveda — "
            "we explore the spiritual link between cosmic health and immortal wisdom."
        ),
    },
    {
        "topic":           "Why Kubera Is the Treasurer of the Devas",
        "category":        "Hindu mythology",
        "deity":           "kubera",
        "suggested_angle": (
            "Once a humble seeker, Kubera's austerity earned him the custodianship "
            "of wealth — teaching that material resources are held as a cosmic trust."
        ),
    },
    {
        "topic":           "Why Garuda Is Vishnu's Eternal Vahana",
        "category":        "Symbolism",
        "deity":           "garuda",
        "suggested_angle": (
            "Garuda embodies the swiftness of Vedic mantras — soaring high above "
            "earthly illusions while guarding sacred order against hidden corruption."
        ),
    },
    {
        "topic":           "Why Kalabhairava Guards the Sacred City of Kashi",
        "category":        "Historical/religious places",
        "deity":           "shiva",
        "suggested_angle": (
            "Kotwal of Kashi — Bhairava absolves the lingering karmic debts of "
            "seekers entering Varanasi, ensuring spiritual liberation at life's end."
        ),
    },
    {
        "topic":           "Why Lord Dattatreya Has Three Heads and Four Dogs",
        "category":        "Symbolism",
        "deity":           "dattatreya",
        "suggested_angle": (
            "The synthesis of Brahma, Vishnu, and Shiva — Dattatreya's four dogs "
            "represent the four Vedas following the supreme unattached guru."
        ),
    },
    {
        "topic":           "Why Hanuman Ate the Sun Thinking It Was a Fruit",
        "category":        "Hindu mythology",
        "deity":           "hanuman",
        "suggested_angle": (
            "Bal Hanuman's cosmic leap to catch the sun reveals unlimited innocence "
            "and the divine powers that were subsequently veiled until needed."
        ),
    },
    {
        "topic":           "Why Goddess Kali Stepped on Lord Shiva's Chest",
        "category":        "Stories of deities",
        "deity":           "kali",
        "suggested_angle": (
            "Shiva placing himself under Kali's foot calms the uncontrollable cosmic "
            "fury — symbolizing unmanifest consciousness restraining pure active power."
        ),
    },
    # ── Expanded Fresh Devotional Topics (Phase 2L+) ─────────────────────────
    {
        "topic":           "The Cosmic Mystery of Nataraja Shiva Dance of Creation",
        "category":        "Symbolism",
        "deity":           "shiva",
        "suggested_angle": (
            "Ananda Tandava is not merely a dance — the drum, flame, and dwarf demon "
            "encapsulate the five cosmic activities of creation, preservation, and dissolution."
        ),
    },
    {
        "topic":           "Why Lord Shiva Applies Sacred Ash Bhasma on His Entire Body",
        "category":        "Traditions",
        "deity":           "shiva",
        "suggested_angle": (
            "Vibhuti signifies the impermanence of mortal existence — Shiva teaches devotees "
            "to burn ignorance and wear detachment as their greatest ornament."
        ),
    },
    {
        "topic":           "The Legend of Somnath The First Jyotirlinga and Chandra Penance",
        "category":        "Historical/religious places",
        "deity":           "shiva",
        "suggested_angle": (
            "Why the Moon God prayed at Prabhas Patan to cure Daksha's curse, establishing "
            "the indestructible shrine of eternal devotion."
        ),
    },
    {
        "topic":           "Why Lord Shiva Holds the Damru and Creation of Sounds",
        "category":        "Symbolism",
        "deity":           "shiva",
        "suggested_angle": (
            "The hourglass beats of Shiva's damru birthed the Maheshwara Sutras — the primordial "
            "sound frequencies that formed the foundation of sacred language."
        ),
    },
    {
        "topic":           "The Mystery of Kedarnath Temple Surviving Himalayan Flood",
        "category":        "Historical/religious places",
        "deity":           "shiva",
        "suggested_angle": (
            "How the divine Bhim Shila boulder sheltered Kedarnath during the deluge, revealing "
            "the spiritual resilience anchored in ancient Himalayan devotion."
        ),
    },
    {
        "topic":           "Why Lord Shiva Manifested as Ardhanarishvara Half Man Half Woman",
        "category":        "Stories of deities",
        "deity":           "shiva",
        "suggested_angle": (
            "Prakriti and Purusha united in one divine form — demonstrating that creation "
            "is impossible without complete equality of masculine and feminine energies."
        ),
    },
    {
        "topic":           "The Story of Markandeya How Shiva Defeated Death",
        "category":        "Stories of deities",
        "deity":           "shiva",
        "suggested_angle": (
            "Kalantaka Shiva emerging from the Lingam to save young Markandeya from Yama's noose, "
            "showing that true devotion conquers mortal destiny."
        ),
    },
    {
        "topic":           "The Sacred Meaning of Crescent Moon on Lord Shiva Head",
        "category":        "Symbolism",
        "deity":           "shiva",
        "suggested_angle": (
            "Chandrashekhara adorned with the growing moon symbolizes control of the fluctuating mind "
            "and cosmic time cycle held peacefully on the crown."
        ),
    },
    {
        "topic":           "The Story of Matsya Avatar How Vishnu Saved the Vedas",
        "category":        "Hindu mythology",
        "deity":           "vishnu",
        "suggested_angle": (
            "Vishnu's first incarnation as the golden horned fish guiding Manu's boat through the great cosmic deluge "
            "to protect the seeds of creation."
        ),
    },
    {
        "topic":           "Why Lord Vishnu Manifested as Kurma the Giant Tortoise",
        "category":        "Hindu mythology",
        "deity":           "vishnu",
        "suggested_angle": (
            "The cosmic tortoise bearing the crushing weight of Mount Mandara teaches the virtue of unshakeable "
            "patience when storms churn our lives."
        ),
    },
    {
        "topic":           "The Secret of Varaha Avatar Rescuing Mother Earth",
        "category":        "Stories of deities",
        "deity":           "vishnu",
        "suggested_angle": (
            "Why the boar incarnation dived into the primordial abyss to rescue Bhudevi from Hiranyaksha's grip, "
            "restoring universal dharma."
        ),
    },
    {
        "topic":           "How Vamana Avatar Humbled King Mahabali in Three Steps",
        "category":        "Hindu mythology",
        "deity":           "vishnu",
        "suggested_angle": (
            "Trivikrama measuring earth and heavens in two strides and placing the third on Mahabali's head, "
            "transforming ego into selfless surrender."
        ),
    },
    {
        "topic":           "The Miracle of Gajendra Moksha Why Vishnu Saved an Elephant",
        "category":        "Stories of deities",
        "deity":           "vishnu",
        "suggested_angle": (
            "The king of elephants calling out 'Narayana' in agony as Makara grips him, proving God rushes "
            "without delay to true sincere surrender."
        ),
    },
    {
        "topic":           "The Legend of Mohini Avatar How Vishnu Tricked Asuras",
        "category":        "Hindu mythology",
        "deity":           "vishnu",
        "suggested_angle": (
            "The enchanting divine form that distributed the nectar of immortality to the devas, showing wisdom "
            "protects righteousness when brute force fails."
        ),
    },
    {
        "topic":           "The Mystery of Vaikuntha The Supreme Abode of Narayana",
        "category":        "Spiritual history",
        "deity":           "vishnu",
        "suggested_angle": (
            "Vaikuntha is the realm free from anxiety, sorrow, and time — we explore the spiritual geography "
            "described in the Bhagavata Purana."
        ),
    },
    {
        "topic":           "Why Krishna Stole Butter as Makhan Chor Hidden Lesson",
        "category":        "Stories of deities",
        "deity":           "krishna",
        "suggested_angle": (
            "Stealing butter is not childhood mischief — freshly churned butter represents the purified, tender heart "
            "of the devotee that Krishna steals away with love."
        ),
    },
    {
        "topic":           "How Krishna Subdued Kaliya the Giant Water Serpent",
        "category":        "Hindu mythology",
        "deity":           "krishna",
        "suggested_angle": (
            "Dancing upon the multi-headed snake in Yamuna's waters teaches the neutralization of toxic thoughts "
            "through joyous spiritual grace."
        ),
    },
    {
        "topic":           "The Deep Meaning of Krishna Vishwaroopam Cosmic Form",
        "category":        "Spiritual history",
        "deity":           "krishna",
        "suggested_angle": (
            "The revelation on Kurukshetra battlefield showing all galaxies, gods, and warriors entering Krishna's fiery mouth, "
            "revealing the oneness of cosmic time."
        ),
    },
    {
        "topic":           "The Unbreakable Friendship of Krishna and Poor Brahmin Sudama",
        "category":        "Stories of deities",
        "deity":           "krishna",
        "suggested_angle": (
            "Sudama offering dry flattened rice and Krishna washing his dusty feet, establishing that pure devotion "
            "outweighs all material riches."
        ),
    },
    {
        "topic":           "Why Lord Krishna Wears a Peacock Feather on His Crown",
        "category":        "Symbolism",
        "deity":           "krishna",
        "suggested_angle": (
            "The peacock offering its molted plumes in ecstasy to Krishna represents beauty unattached to vanity, "
            "borne effortlessly by the divine."
        ),
    },
    {
        "topic":           "The Sacred Mystery of Raas Leela Pure Soul Devotion",
        "category":        "Spiritual history",
        "deity":           "krishna",
        "suggested_angle": (
            "Krishna multiplying himself to dance beside every Gopi in Vrindavan is the allegory of the Divine "
            "communing with every individual soul simultaneously."
        ),
    },
    {
        "topic":           "How Lord Krishna Protected Draupadi in Royal Assembly",
        "category":        "Stories of deities",
        "deity":           "krishna",
        "suggested_angle": (
            "The miraculous endless stream of cloth when Draupadi raised both hands in total surrender, "
            "demonstrating infallible protection for the helpless."
        ),
    },
    {
        "topic":           "The Sacred Story of Shabri Berries Pure Heart Devotion",
        "category":        "Stories of deities",
        "deity":           "rama",
        "suggested_angle": (
            "Rama gladly tasting half-eaten wild berries from an elderly tribal devotee teaches that love transcends "
            "all ritual formalities."
        ),
    },
    {
        "topic":           "How Jatayu Fought Ravana to Protect Devi Sita",
        "category":        "Hindu mythology",
        "deity":           "rama",
        "suggested_angle": (
            "The noble vulture fighting to his dying breath against the demon king embodies the supreme duty "
            "of standing for dharma even when outmatched."
        ),
    },
    {
        "topic":           "The Mystery of Floating Stones of Ram Setu Across Sea",
        "category":        "Historical/religious places",
        "deity":           "rama",
        "suggested_angle": (
            "Writing the sacred name of Rama on ocean rocks and building the divine bridge between Rameshwaram and Lanka, "
            "where faith overrules gravity."
        ),
    },
    {
        "topic":           "How Kevat the Boatman Washed Rama Feet Before River Crossing",
        "category":        "Stories of deities",
        "deity":           "rama",
        "suggested_angle": (
            "The humble boatman requesting to wash Rama's feet fearing his dust might turn his wooden boat into a woman like Ahalya, "
            "a masterclass in sweet devotion."
        ),
    },
    {
        "topic":           "Why Lord Rama Accepted Fourteen Years Exile Without Hesitation",
        "category":        "Spiritual history",
        "deity":           "rama",
        "suggested_angle": (
            "Maryada Purushottama smiling serenely when informed of his exile, demonstrating that upholding a father's pledge "
            "is far greater than earthly sovereignty."
        ),
    },
    {
        "topic":           "The Lesson of Golden Deer Why Illusion Traps the Mind",
        "category":        "Stories of deities",
        "deity":           "rama",
        "suggested_angle": (
            "Maricha's deceitful sparkling form pulling Rama away warns how worldly attractions lure spiritual seekers "
            "out of their protected boundaries."
        ),
    },
    {
        "topic":           "How Hanuman Carried Dronagiri Mountain for Sanjeevani Herb",
        "category":        "Hindu mythology",
        "deity":           "hanuman",
        "suggested_angle": (
            "Unable to recognize the life-giving herb in darkness, Hanuman lifted the entire mountain on his palm, "
            "proving devotion solves problems with limitless courage."
        ),
    },
    {
        "topic":           "Why Hanuman Tore His Chest to Reveal Rama and Sita Inside",
        "category":        "Symbolism",
        "deity":           "hanuman",
        "suggested_angle": (
            "When gifted a priceless pearl necklace, Hanuman cracked pearls with his teeth looking for Rama, "
            "then ripped open his chest to show they live in his heart."
        ),
    },
    {
        "topic":           "The Mystery of Panchamukhi Hanuman Five Faces and Weapons",
        "category":        "Symbolism",
        "deity":           "hanuman",
        "suggested_angle": (
            "The five faces (Monkey, Lion, Eagle, Boar, Horse) extinguish five lamps at once to slay Ahiravana in Patala, "
            "symbolizing total protection in five directions."
        ),
    },
    {
        "topic":           "How Hanuman Set Golden Lanka on Fire with Burning Tail",
        "category":        "Hindu mythology",
        "deity":           "hanuman",
        "suggested_angle": (
            "Ravana lighting cloth on Hanuman's tail turned into the fiery demise of Lanka's pride, showing pride "
            "always generates the spark of its own undoing."
        ),
    },
    {
        "topic":           "The Humility of Hanuman Writing Ramayana on Mountain Rocks",
        "category":        "Stories of deities",
        "deity":           "hanuman",
        "suggested_angle": (
            "Hanuman carving the Hanumad Ramayana on rocks with his claws and discarding it into the sea so Valmiki's work "
            "would be celebrated without competition."
        ),
    },
    {
        "topic":           "Why Hanuman Forgotten Powers Were Awakened by Jambavan",
        "category":        "Hindu mythology",
        "deity":           "hanuman",
        "suggested_angle": (
            "Cursed as a child to forget his strength until reminded by wise elders, teaching that every soul holds divine "
            "strength waiting for a spiritual catalyst."
        ),
    },
    {
        "topic":           "Why Lord Ganesha Is Always Worshipped First in Every Ritual",
        "category":        "Traditions",
        "deity":           "ganesha",
        "suggested_angle": (
            "The divine boon granting Ganesha Prathama Pujya status ensures that wisdom and obstacle-clearing precede "
            "all earthly and spiritual endeavors."
        ),
    },
    {
        "topic":           "The Story of Lord Ganesha and Kubera Endless Feast",
        "category":        "Stories of deities",
        "deity":           "ganesha",
        "suggested_angle": (
            "Ganesha eating all the food in Kubera's golden palace and demanding more, teaching the wealthy treasurer "
            "that pride cannot satisfy divine truth."
        ),
    },
    {
        "topic":           "Why Ganesha Loves Modak Sweet and Durva Grass Blades",
        "category":        "Traditions",
        "deity":           "ganesha",
        "suggested_angle": (
            "The Anandam sweet representing spiritual bliss and the humble 21 blades of Durva grass cooling the heat of worldly desires, "
            "symbolizing inner peace."
        ),
    },
    {
        "topic":           "The Legend of Chandra Curse Why Ganesha Punished the Moon",
        "category":        "Hindu mythology",
        "deity":           "ganesha",
        "suggested_angle": (
            "Chandra laughing at Ganesha stumbling on Chaturthi led to the curse that vanity causes waxing and waning, "
            "warning against arrogance."
        ),
    },
    {
        "topic":           "How Ganesha Won the Race of the Universe Circling Parents",
        "category":        "Stories of deities",
        "deity":           "ganesha",
        "suggested_angle": (
            "While Kartikeya flew on his peacock around the globe, Ganesha circled Shiva and Parvati, teaching that honoring "
            "parents encompasses the entire universe."
        ),
    },
    {
        "topic":           "Why Tirupati Balaji Laddu Prasadam Has Miraculous Secret",
        "category":        "Traditions",
        "deity":           "vishnu",
        "suggested_angle": (
            "The 300-year culinary tradition of the Tirupati Potu kitchen producing blessed laddus with cardamom and pure ghee, "
            "a divine token of Venkateswara grace."
        ),
    },
    {
        "topic":           "The Divine Marriage of Srinivasa and Goddess Padmavathi",
        "category":        "Stories of deities",
        "deity":           "vishnu",
        "suggested_angle": (
            "The celestial wedding at Narayanavanam fulfilling Sage Bhrigu's quest, and why Lord Venkateswara settled eternally "
            "on the Seven Hills."
        ),
    },
    {
        "topic":           "The Secret Behind Continuous Moisture on Tirumala Balaji Idol",
        "category":        "Historical/religious places",
        "deity":           "vishnu",
        "suggested_angle": (
            "The sanctum mystery of the stone deity maintaining living body temperature and radiating cool mist amidst burning lamps, "
            "a wonder of Tirumala."
        ),
    },
    {
        "topic":           "The Miracle of Manikandan Bringing Tigress Milk to Palace",
        "category":        "Stories of deities",
        "deity":           "ayyappa",
        "suggested_angle": (
            "Young Manikandan riding fearlessly on a fierce tigress back to the kingdom, fulfilling his mission and proving his divine "
            "descent as Lord Ayyappa."
        ),
    },
    {
        "topic":           "The Spiritual Meaning of 18 Sacred Gold Steps at Sabarimala",
        "category":        "Symbolism",
        "deity":           "ayyappa",
        "suggested_angle": (
            "The Pathinettam Padi climbing toward the sanctum represents conquering five senses, eight raggas, three gunas, and ignorance."
        ),
    },
    {
        "topic":           "The Mystery of Makara Jyothi Celestial Light at Sabarimala",
        "category":        "Historical/religious places",
        "deity":           "ayyappa",
        "suggested_angle": (
            "The divine star Sirius Makara Sankranti alignment over Ponrambalamedu where lakhs of pilgrims cry Swamiye Saranam Ayyappa in ecstasy."
        ),
    },
    {
        "topic":           "Why Sabarimala Pilgrims Observe 41 Days of Strict Vratam",
        "category":        "Traditions",
        "deity":           "ayyappa",
        "suggested_angle": (
            "The Mandalam penance of wearing black, walking barefoot, and seeing every fellow pilgrim as God itself, "
            "dissolving social distinctions."
        ),
    },
    {
        "topic":           "Why Lord Murugan Holds the Invincible Vel Spear of Wisdom",
        "category":        "Symbolism",
        "deity":           "kartikeya",
        "suggested_angle": (
            "The sharp spear bestowed by Goddess Parvati represents Jnana Shakti — broad, deep, and sharp wisdom that slays the demon of ignorance."
        ),
    },
    {
        "topic":           "The Fierce Battle of Soorasamharam and Triumph of Murugan",
        "category":        "Hindu mythology",
        "deity":           "kartikeya",
        "suggested_angle": (
            "Murugan splitting the giant mango tree demon Soorapadman into a loyal peacock vahana and cock flag, turning darkness into devotion."
        ),
    },
    {
        "topic":           "Why Kartikeya Renounced All Possessions and Settled at Palani",
        "category":        "Historical/religious places",
        "deity":           "kartikeya",
        "suggested_angle": (
            "Dandaayudhapani standing with staff and loincloth atop Palani hill, reminding humanity that the fruit of supreme wisdom "
            "lies beyond material titles."
        ),
    },
    {
        "topic":           "The Eight Divine Forms of Ashta Lakshmi and Their Secrets",
        "category":        "Symbolism",
        "deity":           "lakshmi",
        "suggested_angle": (
            "Wealth is not just currency — Adi, Dhanya, Dhairya, Gaja, Santana, Vijaya, Vidya, and Dhana Lakshmi embody "
            "holistic universal prosperity."
        ),
    },
    {
        "topic":           "How Goddess Durga Slain Mahishasura in Nine Sacred Nights",
        "category":        "Stories of deities",
        "deity":           "durga",
        "suggested_angle": (
            "Formed by the combined radiance of all Devas to eliminate the shapeshifting buffalo demon, celebrating the triumph "
            "of light over cosmic chaos."
        ),
    },
    {
        "topic":           "Why Goddess Saraswati Wears Pure White Attire and Veena",
        "category":        "Symbolism",
        "deity":           "saraswati",
        "suggested_angle": (
            "The spotless white sari represents unblemished pure intellect, while tuning the veena strings symbolizes disciplining the mind's thoughts."
        ),
    },
    {
        "topic":           "The Story of Sati Sacrifice and Creation of 51 Shakti Peethas",
        "category":        "Historical/religious places",
        "deity":           "parvati",
        "suggested_angle": (
            "Sati giving up her body at Daksha's Yajna and Vishnu's Sudarshana Chakra consecrating her limbs across the Indian subcontinent "
            "as sacred power centers."
        ),
    },
    {
        "topic":           "Why Goddess Annapurna Fed Shiva in Varanasi",
        "category":        "Stories of deities",
        "deity":           "parvati",
        "suggested_angle": (
            "When Shiva declared food is an illusion, nature dried up until Shiva begged Annapurna for alms, recognizing physical sustenance "
            "as divine maternal grace."
        ),
    },
    {
        "topic":           "Why Gayatri Mantra Is Known as Mother of All Vedic Chants",
        "category":        "Traditions",
        "deity":           "traditions",
        "suggested_angle": (
            "The 24 syllables praying to Savitur to illuminate the intellect, acting as an ancient sonic shield of spiritual clarity."
        ),
    },
    {
        "topic":           "The Spiritual Science Behind Pradakshina Clockwise Temple Walks",
        "category":        "Traditions",
        "deity":           "traditions",
        "suggested_angle": (
            "Circumambulating the sanctum clockwise keeps the central deity at the right shoulder, aligning inner energy with the earth's natural magnetic vortex."
        ),
    },
    {
        "topic":           "Why We Break Coconuts Before Starting Any Auspicious Work",
        "category":        "Traditions",
        "deity":           "traditions",
        "suggested_angle": (
            "Shattering the tough fibrous outer shell to offer sweet water and white kernel symbolizes breaking the ego "
            "to reveal inner purity to the divine."
        ),
    },
    {
        "topic":           "The Hidden Sacred Geometry Behind Mystical Sri Yantra",
        "category":        "Symbolism",
        "deity":           "traditions",
        "suggested_angle": (
            "Nine interlocking triangles forming 43 smaller triangles in the Bindu, mapping the cosmic creation from unmanifest oneness "
            "to manifest reality."
        ),
    },
    {
        "topic":           "Why Number 108 Holds Cosmic Significance in Hindu Dharma",
        "category":        "Traditions",
        "deity":           "traditions",
        "suggested_angle": (
            "The exact mathematical ratio of distance between Sun, Earth, and Moon with celestial diameters, encoded in japa malas and sacred chants."
        ),
    },
]


# ── Content gap analysis ──────────────────────────────────────────────────────

def analyze_content_gap(scores: dict, data_source: str) -> str:
    """
    Returns a cautious, evidence-qualified content-gap label.
    Claims are weakened when based on mock/offline data.
    """
    is_real = data_source in ("youtube_api", "cached_youtube_api")
    demand       = scores["demand_score"]
    competition  = scores["competition_score"]
    freshness    = scores["freshness_score"]
    curiosity    = scores["curiosity_score"]
    dominant     = scores["stats"]["dominant_count"]

    qualifier = "" if is_real else " (based on mock data — requires real validation)"

    if dominant >= 4:
        return f"High Saturation: Many channels dominate this topic with high-view videos. A highly distinctive angle is needed to compete{qualifier}."
    if demand >= 70 and competition >= 80:
        return (
            f"Possible gap — low saturation with moderate-to-high demand signals. "
            f"Potential opportunity based on available signals{qualifier}."
        )
    if demand >= 75 and freshness <= 40:
        return (
            f"Possible evergreen refresh opportunity — older high-view content exists "
            f"but few recent uploads detected. Requires further validation{qualifier}."
        )
    if curiosity >= 90 and demand <= 55:
        return (
            f"Curiosity-hook topic with modest search demand — may suit a short, "
            f"high-hook Shorts format. Insufficient evidence to claim a gap{qualifier}."
        )
    return f"Insufficient evidence to identify a specific content gap{qualifier}."


def select_topics_to_scan(
    seeds: list | None = None,
    limit: int | None = None,
    history_file: str | Path | None = None,
) -> list:
    """
    Filter published topics/titles and near-duplicate fingerprints against publishing_history,
    deduplicate among seeds, then apply limit.
    """
    if history_file is None:
        history_file = HISTORY_FILE
    raw_seeds = seeds if seeds is not None else SUGGESTED_TOPICS
    published_strings = _load_published_topics(history_file)
    published_prints = [_fingerprint(p) for p in published_strings if p]

    fresh_seeds = []
    for item in raw_seeds:
        top_str = (item.get("topic") or "").strip().lower()
        if top_str in published_strings:
            continue
        fp = _fingerprint(top_str)
        if any(len(fp & pub_fp) >= 3 for pub_fp in published_prints):
            continue
        fresh_seeds.append(item)

    unique = deduplicate_topics(fresh_seeds)
    skipped = len(raw_seeds) - len(unique)
    if skipped:
        print(
            f"ℹ️  Skipping {skipped} seed topic(s) already published or near-duplicate in publishing_history.json "
            f"({len(unique)} fresh unpublished remaining).",
            file=sys.stderr,
        )
    if not unique:
        print(
            "⚠️  WARNING: All suggested seed topics have been published or match previous videos! "
            "Please expand SUGGESTED_TOPICS with fresh topics.",
            file=sys.stderr,
        )
    if limit is not None:
        unique = unique[:limit]
    print(
        f"ℹ️  Research will scan {len(unique)} unpublished seed topic(s).",
        file=sys.stderr,
    )
    return unique


# ── Pipeline ──────────────────────────────────────────────────────────────────

def run_research_pipeline(
    api_key: str = None,
    limit: int = None,
    max_search_calls: int = 10,
    cache_ttl_hours: int = 24,
    history_file: str | Path | None = None,
) -> list:
    """
    Runs the full research pipeline: dedup → exclude published → collect → score → persist.

    Parameters
    ----------
    api_key           : YouTube Data API v3 key (None = offline/mock mode)
    limit             : cap number of unpublished topics scanned (None = all unpublished)
    max_search_calls  : quota budget for YouTube search.list this run
    cache_ttl_hours   : cache entry freshness window
    history_file      : publishing history used only to skip already-published seeds

    Returns
    -------
    Sorted list of candidate dicts, best score first.
    """
    if history_file is None:
        history_file = HISTORY_FILE
    collector = ResearchCollector(
        api_key=api_key,
        max_search_calls=max_search_calls,
        cache_ttl_hours=cache_ttl_hours,
    )

    topics_to_scan = select_topics_to_scan(
        SUGGESTED_TOPICS,
        limit=limit,
        history_file=history_file,
    )

    results = []
    any_mock = False

    for item in topics_to_scan:
        topic_text  = item["topic"]
        deity       = item["deity"]

        # Collect
        search_result = collector.search_youtube_videos(topic_text)
        videos        = search_result["videos"]
        data_source   = search_result["data_source"]
        is_mock       = search_result["is_mock"]
        if is_mock:
            any_mock = True

        # Festival proximity
        festival_info = collector.get_festival_info(deity)

        # Score
        scores = TopicScorer.calculate_score(
            topic_meta    = item,
            youtube_videos= videos,
            festival_info  = festival_info,
            data_source   = data_source,
        )

        # Content gap
        gap = analyze_content_gap(scores, data_source)

        # Assemble candidate
        candidate = {
            # Identity
            "topic":           topic_text,
            "category":        item["category"],
            "deity":           deity,
            "suggested_angle": item["suggested_angle"],

            # Data provenance
            "data_source":     data_source,
            "is_mock":         is_mock,
            "confidence":      scores["confidence"],

            # Festival
            "closest_festival":  festival_info["festival_name"],
            "days_to_festival":  festival_info["days_remaining"],
            "festival_verified": festival_info["verified"],
            "festival_source":   festival_info["source"],

            # Score
            "score_version":      scores["score_version"],
            "overall_score":      scores["overall_score"],
            "demand_score":       scores["demand_score"],
            "relevance_score":    scores["relevance_score"],
            "competition_score":  scores["competition_score"],
            "evergreen_score":    scores["evergreen_score"],
            "freshness_score":    scores["freshness_score"],
            "curiosity_score":    scores["curiosity_score"],
            "long_form_potential":scores["long_form_potential"],
            "shorts_potential":   scores["shorts_potential"],

            # Evidence
            "content_gap":   gap,
            "related_videos": [
                {
                    "title":        v["title"],
                    "views":        v["views"],
                    "url":          v["url"],
                    "published_at": v["published_at"],
                }
                for v in videos[:3]
            ],
            "stats": scores["stats"],
        }
        results.append(candidate)

    # Sort best-first
    results.sort(key=lambda x: x["overall_score"], reverse=True)

    # Persist
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_file = OUTPUT_DIR / f"research_results_{timestamp}.json"
    try:
        out_file.write_text(
            json.dumps(results, indent=2, ensure_ascii=False),
            encoding="utf-8"
        )
        print(f"\n📂 Research candidates saved → {out_file}", file=sys.stderr)
    except Exception as e:
        print(f"⚠️  Warning: Failed to save research results: {e}", file=sys.stderr)

    if any_mock:
        print(
            "\n⚠️  WARNING: One or more topic scores are based on OFFLINE / MOCK data.\n"
            "   Results should NOT be used for production scheduling decisions\n"
            "   without re-running with a valid YouTube API connection.",
            file=sys.stderr
        )

    return results


# ── Console report ────────────────────────────────────────────────────────────

def print_report(candidates: list):
    """Outputs the formatted report to stdout."""
    any_mock = any(c.get("is_mock") for c in candidates)

    print("\n" + "=" * 54)
    print("🌅  DIVINE DHARSHANAM DAILY — TOPIC RESEARCH REPORT")
    print(f"    Scoring: Topic Opportunity Score {candidates[0]['score_version'] if candidates else 'v0.1'}")
    if any_mock:
        print("    ⚠️  MODE: OFFLINE / MOCK RESEARCH — not real YouTube data")
    print("=" * 54)

    for idx, c in enumerate(candidates, 1):
        src_label = f"[{c['data_source'].upper()}]"
        conf_label = f"confidence={c['confidence']}"
        fest_note = "" if c["festival_verified"] else " (unverified date)"

        print(f"\n{idx}. {c['topic']}")
        print(f"   Category:    {c['category']}  {src_label}  {conf_label}")
        print(f"   Festival:    {c['closest_festival']} in {c['days_to_festival']} days{fest_note}")
        print(f"\n   Score:       {c['overall_score']}/100")
        print(
            f"   Demand:{c['demand_score']:>4}  Relevance:{c['relevance_score']:>4}  "
            f"Competition:{c['competition_score']:>4}  Evergreen:{c['evergreen_score']:>4}"
        )
        print(f"   Curiosity:{c['curiosity_score']:>4}  Freshness:{c['freshness_score']:>4}  "
              f"Long-form:{c['long_form_potential']:>4}  Shorts:{c['shorts_potential']:>4}")
        print(f"\n   Suggested Angle:")
        print(f"   \"{c['suggested_angle']}\"")
        print(f"\n   Content Gap:")
        print(f"   {c['content_gap']}")
        print(f"\n   Evidence ({c['data_source']}):")
        for v in c["related_videos"]:
            print(f"   • {v['title']} — {v['views']:,} views — {v['url']}")
        print("\n" + "-" * 54)
