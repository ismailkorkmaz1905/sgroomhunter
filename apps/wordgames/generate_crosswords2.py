"""
Crossword generator: algorithmically find valid word quadruples from word lists.
For each size (3,4,5):
  - w1 (across row 0): A..Z chars
  - w2 (down col 0):   A..Z chars  constraint: w2[0]==w1[0]
  - w3 (down col n-1): A..Z chars  constraint: w3[0]==w1[n-1]
  - w4 (across row n-1): A..Z chars constraint: w4[0]==w2[n-1], w4[n-1]==w3[n-1]

Clue generation: use a simple dict lookup per language.
"""
import json, itertools, random
from pathlib import Path
from wordgames_validation import validate_crossword_pool

BASE = Path(__file__).parent / "data" / "crosswords"
random.seed(99)

BLOCKS = {
    3: [[1, 1]],
    4: [[1, 1], [1, 2], [2, 1], [2, 2]],
    5: [[1, 1], [1, 2], [1, 3], [2, 1], [2, 2], [2, 3], [3, 1], [3, 2], [3, 3]],
}


def make_puzzle(size, w1, c1, w2, c2, w3, c3, w4, c4):
    last = size - 1
    return {
        "size": size,
        "blocks": BLOCKS[size],
        "entries": [
            {"number": 1, "direction": "across", "row": 0,    "col": 0,    "answer": w1, "clue": c1},
            {"number": 2, "direction": "down",   "row": 0,    "col": 0,    "answer": w2, "clue": c2},
            {"number": 3, "direction": "down",   "row": 0,    "col": last, "answer": w3, "clue": c3},
            {"number": 4, "direction": "across", "row": last, "col": 0,    "answer": w4, "clue": c4},
        ],
    }


def valid_quad(w1, w2, w3, w4):
    """Check intersection constraints."""
    size = len(w1)
    if not (len(w2) == len(w3) == len(w4) == size):
        return False
    if w2[0] != w1[0]:    return False
    if w3[0] != w1[-1]:   return False
    if w4[0] != w2[-1]:   return False
    if w4[-1] != w3[-1]:  return False
    return True


def find_quads(words_by_len, size, n=8, exclude_used=None):
    """Find n valid quadruples of words with given size."""
    ws = [w.lower() for w in words_by_len.get(size, []) if w.isalpha()]
    if exclude_used:
        used = {w for quad in exclude_used for w in quad}
        ws = [w for w in ws if w not in used]
    random.shuffle(ws)
    found = []
    # Group by first/last letter for fast lookup
    from collections import defaultdict
    by_first = defaultdict(list)
    by_last  = defaultdict(list)
    for w in ws:
        by_first[w[0]].append(w)
        by_last[w[-1]].append(w)

    for w1 in ws:
        if len(found) >= n:
            break
        # w2: starts with w1[0]
        for w2 in by_first.get(w1[0], []):
            if w2 == w1: continue
            # w3: starts with w1[-1]
            for w3 in by_first.get(w1[-1], []):
                if w3 in (w1, w2): continue
                # w4: starts with w2[-1], ends with w3[-1]
                for w4 in by_first.get(w2[-1], []):
                    if w4 in (w1, w2, w3): continue
                    if w4[-1] == w3[-1]:
                        found.append((w1, w2, w3, w4))
                        if len(found) >= n:
                            break
                if len(found) >= n: break
            if len(found) >= n: break
    return found


# ---------------------------------------------------------------------------
# Word lists per language with clues
# ---------------------------------------------------------------------------

EN_CLUES = {
    # 3-letter
    "hot": "Very warm", "ham": "Cured pork", "top": "Highest point", "map": "Guide to places",
    "big": "Large", "bus": "Road vehicle", "gem": "Precious stone", "sum": "Result of addition",
    "par": "Expected score", "pod": "Pea container", "raw": "Uncooked", "dew": "Morning moisture",
    "cup": "Small vessel", "cob": "Corn on the ___", "pit": "Hole in ground", "bit": "Small piece",
    "jar": "Glass container", "jot": "Write briefly", "rot": "Decay", "dot": "Tiny mark",
    "hat": "Head covering", "hug": "Warm embrace", "ten": "Number after nine", "gin": "Clear spirit",
    "sad": "Unhappy", "sow": "Plant seeds", "den": "Animal shelter", "win": "Come first",
    "bat": "Cricket equipment", "ban": "Prohibit", "tan": "Light brown", "nun": "Religious sister",
    "cut": "Slice through", "car": "Motor vehicle", "tap": "Light knock", "cot": "Baby bed",
    "fog": "Low-lying cloud", "fin": "Fish limb", "nod": "Head gesture", "fib": "Small lie",
    "log": "Chunk of wood", "lip": "Mouth edge", "gap": "Space or opening", "yap": "Sharp bark",
    "pen": "Writing tool", "pig": "Farm animal", "gun": "Weapon", "pin": "Small fastener",
    "mud": "Wet dirt", "mug": "Large cup", "pun": "Wordplay joke", "nun": "Convent sister",
    "rug": "Floor covering", "run": "Move fast", "sun": "Daytime star", "sip": "Small drink",
    "nap": "Short sleep", "pop": "Burst sound", "cat": "House pet", "cow": "Milk animal",
    "tin": "Metal can", "dog": "Loyal pet", "dry": "Not wet", "lip": "Mouth edge",
    # 4-letter
    "bold": "Brave or daring", "brew": "Make tea or beer", "dusk": "End of daylight", "walk": "Move on foot",
    "gift": "Something given", "glow": "Emit soft light", "time": "Clock measures this", "wore": "Had on",
    "keep": "Hold onto", "king": "Male monarch", "pond": "Small lake", "gold": "Yellow metal",
    "firm": "Solid or company", "fawn": "Baby deer", "mist": "Light fog", "next": "Coming after",
    "camp": "Outdoor shelter", "coin": "Metal money", "path": "Narrow trail", "nosh": "Eat snacks",
    "harp": "Stringed instrument", "hard": "Difficult", "pave": "Cover with asphalt", "dune": "Sand hill",
    "stem": "Plant stalk", "snow": "Frozen precipitation", "mild": "Not harsh", "wand": "Magic stick",
    "meat": "Animal protein", "moon": "Earth's satellite", "tide": "Sea level change", "name": "What you're called",
    "look": "Direct eyes at", "lamp": "Light source", "kite": "Flies on a string", "page": "Book sheet",
    "rent": "Monthly payment", "road": "Cars drive on this", "tone": "Voice quality", "dive": "Jump in water",
    "boat": "Small watercraft", "burn": "Be on fire", "dark": "Absence of light", "knot": "Tied loop",
    "bark": "Dog sound or tree skin", "brim": "Hat edge or full", "dark": "No light", "risk": "Danger",
    "arch": "Curved structure", "arts": "Creative fields", "task": "Job to do", "rust": "Iron oxide",
    "gust": "Wind burst", "grip": "Hold firmly", "drip": "Fall in drops", "spin": "Rotate",
    "claw": "Animal nail", "clan": "Family group", "flap": "Move up and down", "snap": "Break sharply",
    "wrap": "Cover around", "wasp": "Stinging insect", "swap": "Exchange", "strap": "Narrow strip",
    # 5-letter
    "flame": "Burning fire tongue", "field": "Open grassy area", "enter": "Go into", "diner": "Roadside restaurant",
    "grasp": "Grip tightly", "gloom": "Dim darkness", "prize": "Award for winning", "mouse": "Small rodent",
    "blast": "Explosion", "braid": "Woven hair strands", "tiger": "Striped wild cat", "rider": "One who rides",
    "snore": "Loud sleep sound", "stein": "Beer mug", "envoy": "Diplomatic messenger", "nasty": "Unpleasant",
    "plumb": "Test vertical", "prose": "Written language", "board": "Flat wood piece", "embed": "Fix inside",
    "chant": "Repetitive song", "crave": "Desire strongly", "troll": "Online agitator", "expel": "Force out",
    "swamp": "Marshy wetland", "spike": "Sharp point", "pixel": "Screen dot", "excel": "Perform very well",
    "trend": "Popular direction", "toxin": "Poison", "depth": "Distance down", "notch": "V-shaped cut",
    "table": "Flat-top furniture", "tulip": "Spring flower", "eager": "Excited and ready", "piper": "Pipe musician",
    "crown": "Royal headpiece", "cabin": "Small wooden house", "nicer": "More pleasant", "never": "At no time",
    "brave": "Courageous", "brand": "Company mark", "delta": "River mouth", "allow": "Permit",
    "chaos": "Complete disorder", "chord": "Musical notes together", "drama": "Exciting situation", "alpha": "First Greek letter",
    "angel": "Heavenly being", "apple": "Common red fruit", "earth": "Our planet", "light": "Electromagnetic radiation",
    "night": "Dark part of day", "tight": "Firmly fixed", "right": "Correct or direction", "sight": "Ability to see",
    "giant": "Very large being", "plant": "Living organism", "slant": "Diagonal angle", "grant": "Give officially",
}

TR_CLUES = {
    # 3-letter Turkish words
    "hız": "Sürat, tempo", "hal": "Durum veya pazar", "zor": "Güç, çetin", "ler": "Çoğul eki",
    "göl": "Kapalı su kütlesi", "gün": "24 saatlik zaman", "son": "En sondaki", "sap": "Tutamak",
    "nar": "Kırmızı meyveli ağaç", "yol": "Güzergah", "yaz": "Sıcak mevsim", "kol": "Üst uzuv",
    "tel": "İnce metal ip", "kot": "Denim pantolon", "ışık": "Aydınlık", "ses": "Kulakla duyulan",
    "baş": "Vücudun üst kısmı", "göz": "Görme organı", "diz": "Bacak eklemi", "el": "Elin parçası",
    "kar": "Beyaz yağış", "kış": "Soğuk mevsim", "yer": "Konum, zemin", "ön": "Ön taraf",
    "ad": "İsim", "ev": "Konut", "su": "H₂O", "ay": "Gece ışığı veya zaman birimi",
    "göç": "Yer değiştirme", "tat": "Damak tadı", "kut": "Uğur, bereket", "sal": "Nehir salı",
    # 4-letter Turkish words
    "masa": "Mobilya", "mart": "Yılın 3. ayı", "anka": "Efsanevi kuş", "atık": "Artık madde",
    "kale": "Savunma yapısı", "kara": "Siyah veya toprak", "eser": "Sanat yapıtı", "atar": "Fırlatır",
    "renk": "Işığın görüntüsü", "dere": "Küçük akarsu", "dolu": "Dolu olan", "elde": "Sahipte",
    "gemi": "Deniz taşıtı", "genç": "Yaşı az", "mide": "Sindirim organı", "ince": "Kalın olmayan",
    "boya": "Renklendirici madde", "boru": "İçi boş silindir", "yurt": "Vatan veya konut", "arsa": "Yapılmamış arazi",
    "hava": "Soluk aldığımız gaz", "hale": "Işık halkası", "elma": "Yaygın meyve", "arka": "Geri taraf",
    "dava": "Hukuki süreç", "dava": "İddia", "para": "Para birimi", "paha": "Değer, fiyat",
    "tane": "Adet, birer birer", "tank": "Askeri araç", "ayna": "Yansıtıcı yüzey", "aile": "Akrabalar",
    "dalga": "Su veya ses dalgası", "dal": "Ağaç kolu", "dam": "Çatı veya kilit",
    # 5-letter Turkish words
    "deniz": "Tuzlu su kütlesi", "duman": "Yangın çıkışı", "zemin": "Taban, yer", "neden": "Sebep",
    "kalem": "Yazı aracı", "kadın": "Yetişkin bayan", "maden": "Yer altı kaynağı",
    "güneş": "Güneş sistemi yıldızı", "güzel": "Estetik açıdan hoş", "şeker": "Tatlı madde", "lider": "Önder",
    "nehir": "Akan su yolu", "niyet": "Amaç, kasıt", "tarih": "Geçmiş olaylar",
    "bahar": "İlkbahar mevsimi", "bilgi": "Öğrenilen şey", "çiçek": "Bitkinin renkli kısmı",
    "aslan": "Afrika'nın büyük kedisi", "asker": "Ordu mensubu", "resim": "Görsel sanat eseri",
    "okul": "Eğitim kurumu", "küçük": "Büyük olmayan", "tablo": "Resim veya veri tablosu",
    "yıldız": "Gök cismi", "kitap": "Yazılı eser", "sabah": "Günün başlangıcı",
}

NL_CLUES = {
    # 3-letter Dutch
    "uur": "Zestig minuten", "uit": "Niet thuis", "ros": "Bruinrood paard", "tas": "Draagbare zak",
    "dag": "24 uur", "dak": "Bovenkant van huis", "gek": "Dwaas, gek", "koe": "Melkdier",
    "zee": "Zout wateroppervlak", "zin": "Betekenis of gevoel", "eis": "Recht of vraag",
    "wit": "Sneeuwkleur", "web": "Spinnenweb", "tak": "Boomarm", "bak": "Container",
    "bad": "Badobject", "ban": "Verbod", "bij": "Insect dat honing maakt", "bol": "Ronde vorm",
    "dos": "Uitrusting", "oog": "Zichtorgaan", "oor": "Gehoororgaan", "bos": "Groep bomen",
    "bus": "Openbaar vervoer", "dam": "Waterweg blokkade", "fel": "Fel, intens", "gel": "Dikke vloeistof",
    "gom": "Wis rubber", "gut": "Darmen", "hak": "Achterkant schoen", "hal": "Entree ruimte",
    "hap": "Hap eten", "hek": "Omheining", "hem": "Hem (persoon)", "hol": "Holle ruimte",
    "ijs": "Bevroren water", "ink": "Schrijfvloeistof", "jet": "Straalvliegtuig", "job": "Werk",
    "kap": "Omhulsel of kapsel", "kat": "Huisdier", "kei": "Steen", "kip": "Pluimvee",
    "lam": "Schaap of verlamd", "lap": "Stuk stof", "lat": "Houten balk", "les": "Onderwijs sessie",
    "map": "Kaart of ordner", "mat": "Vloerkleed", "mes": "Snijgereedschap", "mol": "Dier of chemische eenheid",
    "mop": "Schoonmaakborstel", "nep": "Nagemaakt", "net": "Visnet of netjes", "rib": "Botstructuur",
    "rok": "Vrouwenkleding", "sap": "Fruitvloeistof", "sla": "Salade", "sop": "Zeepwater",
    # 4-letter Dutch
    "boom": "Groot gewas", "band": "Muziekgroep", "mist": "Nevel", "dier": "Levend wezen",
    "reis": "Tocht", "rood": "Bloedkleur", "stad": "Nederzetting", "deur": "Opening in muur",
    "huis": "Woongebouw", "hoed": "Hoofddeksel", "slim": "Intelligent", "wolf": "Roofdier",
    "warm": "Niet koud", "fles": "Glazen container", "goud": "Edelmetaal", "glas": "Transparant materiaal",
    "dans": "Rhythmische beweging", "snel": "Vlug", "dorp": "Klein woonplaats", "plek": "Locatie",
    "plus": "Extra", "klem": "Vastgezet", "smal": "Niet breed", "land": "Landgebied",
    "berg": "Heuvel of opslaan", "boek": "Gebonden tekst", "bron": "Waterontspring", "brug": "Oversteek",
    "deel": "Stuk van geheel", "eeuw": "100 jaar", "geld": "Betaalmiddel", "golf": "Watergolf of sport",
    "haar": "Lichaamshaar", "hand": "Lichaamsdeel", "heel": "Volledig of hiel", "held": "Superheld",
    "hoek": "Geometrisch hoek", "jong": "Niet oud", "kaas": "Zuivelproduct", "kamp": "Kampeerplaats",
    "kant": "Zijde of kant", "kern": "Binnenste deel", "klap": "Slag", "klok": "Tijdmeter",
    "knop": "Drukschakelaar", "koek": "Gebakje", "koel": "Fris", "kool": "Groente",
    "koor": "Zanggroep", "kraan": "Watertap"[:4], "laag": "Niet hoog", "lang": "Groot in lengte",
    # 5-letter Dutch
    "toren": "Hoog gebouw", "tafel": "Meubelstuk", "negen": "Getal 9", "laden": "Vullen",
    "water": "H₂O", "wacht": "Bewaker", "regen": "Neerslag", "groen": "Graskleur",
    "bloem": "Plantendeel", "brood": "Gebakken graan", "molen": "Windmachine", "deken": "Wollen deken",
    "prijs": "Kosten of prijs", "plank": "Houten lat", "schip": "Vaartuig", "fiets": "Tweewieler",
    "taart": "Gebak", "tabel": "Overzicht", "krant": "Dagblad", "alarm": "Waarschuwing",
    "arena": "Sportveld", "atlas": "Kaartboek", "basis": "Grondslag", "baron": "Adellijke titel",
    "beker": "Drinkbeker", "beton": "Bouwmateriaal", "brief": "Geschreven boodschap", "buurt": "Wijk",
    "curve": "Gebogen lijn", "datum": "Dag van kalender", "extra": "Meer dan normaal", "flink": "Behoorlijk",
    "gevel": "Voorkant gebouw", "groep": "Verzameling", "haven": "Aanlegplaats", "hemel": "Lucht boven ons",
    "hotel": "Logeerplaats", "idool": "Bewonderd persoon", "inval": "Plotseling bezoek", "kaart": "Stuk papier",
    "kamer": "Ruimte in huis", "keten": "Schakels", "kleur": "Tint", "klimt": "Beklimt",
    "kloof": "Diepe opening", "knoop": "Verbinding punt", "komst": "Aankomst",
}

ID_CLUES = {
    # 3-letter Indonesian
    "air": "Zat cair H₂O", "ada": "Hadir", "rak": "Papan penyimpan",
    "bau": "Aroma", "bak": "Wadah besar", "cat": "Zat warna", "cap": "Tanda cetakan",
    "dom": "Bisu", "doa": "Permohonan", "mas": "Emas atau panggilan",
    "ibu": "Orang tua perempuan", "isi": "Konten, kandungan",
    "abu": "Sisa pembakaran", "aki": "Baterai besar", "ala": "Cara, gaya",
    "api": "Nyala panas", "asa": "Harapan", "ata": "Jenis rotan",
    "bak": "Wadah", "ban": "Lintasan karet", "bar": "Batang logam",
    "bas": "Nada rendah", "bot": "Sepatu bot", "box": "Kotak",
    "bui": "Hujan lebat", "buk": "Buku (singkat)",
    "cek": "Memeriksa", "cit": "Bunyi kecil", "cor": "Tuang semen",
    "dah": "Kata seru", "dan": "Konjungsi", "dar": "Awalan",
    "eks": "Mantan", "elo": "Kamu (slang)", "emas": "Logam mulia"[:3],
    "era": "Zaman", "eta": "Huruf Yunani",
    "gam": "Diam tak bergerak", "gas": "Materi berwujud gas", "gel": "Zat kental",
    "ham": "Daging babi asap", "han": "Panggilan hormat Korea",
    "ide": "Gagasan", "iya": "Kata setuju",
    "jam": "Alat penunjuk waktu", "jus": "Sari buah",
    "kal": "Kalori singkat", "kas": "Uang tunai", "kat": "Lantai gedung",
    "lab": "Laboratorium", "las": "Menyambung logam", "lot": "Bagian atau undian",
    "mad": "Marah", "mai": "Nama bulan Mei", "mal": "Pusat perbelanjaan",
    "nas": "Teks Al-Quran", "net": "Jaring bersih",
    "oli": "Pelumas mesin", "ops": "Kata seru",
    "pas": "Cocok, tepat", "pel": "Mengepel lantai", "per": "Setiap",
    "raj": "Penguasa India lama", "ram": "Domba jantan", "rob": "Melanda",
    "sah": "Resmi, legal", "sal": "Garam", "set": "Kumpulan",
    "teh": "Minuman daun teh", "ter": "Imbuhan kata", "tim": "Kelompok",
    "ubi": "Umbi-umbian", "uji": "Mencoba menguji",
    "vas": "Wadah bunga", "vet": "Dokter hewan",
    "war": "Warna", "wol": "Bahan dari domba",
    # 4-letter Indonesian
    "bola": "Objek bundar", "baju": "Pakaian", "alam": "Lingkungan", "jamu": "Minuman herbal",
    "daya": "Kemampuan", "duit": "Uang slang", "foto": "Gambar kamera", "gula": "Pemanis",
    "guru": "Pengajar", "hati": "Organ atau perasaan", "hari": "24 jam", "tiga": "Angka 3",
    "ikut": "Turut serta", "kota": "Daerah perkotaan", "laut": "Air asin besar",
    "meja": "Furniture datar", "nama": "Identitas seseorang", "nasi": "Beras matang",
    "pagi": "Waktu awal hari", "rasa": "Perasaan atau cita rasa", "satu": "Angka 1",
    "tahu": "Mengerti atau makanan", "uang": "Alat pembayaran", "waktu": "Durasi"[:4],
    "abdi": "Hamba setia", "akar": "Bagian tumbuhan", "alat": "Perangkat",
    "anak": "Keturunan", "aneh": "Tidak biasa", "asli": "Genuina",
    "baik": "Positif", "baru": "Tidak lama", "bawa": "Membawa",
    "beda": "Berbeda", "beli": "Membeli", "bisa": "Mampu",
    "buka": "Membuka", "buku": "Publikasi tertulis", "bumi": "Planet kita",
    "cari": "Mencari", "cepa": "Cepat"[:4], "coba": "Mencoba",
    "dada": "Bagian dada", "dahi": "Bagian depan kepala", "daun": "Bagian tumbuhan",
    "debu": "Partikel halus", "desa": "Daerah pedesaan", "diam": "Tidak bersuara",
    "enak": "Terasa baik", "erat": "Kencang", "esok": "Hari berikutnya",
    "gigi": "Organ pengunyah", "gila": "Tidak waras", "guna": "Manfaat",
    "hapu": "Menghapus"[:4], "hias": "Menghias", "hidup": "Kehidupan"[:4],
    "ikat": "Mengikat", "iklan": "Reklame"[:4], "ilmu": "Pengetahuan",
    "jaga": "Berjaga", "jalan": "Tempat berjalan"[:4], "jauh": "Berjauhan",
    "jual": "Menjual", "juga": "Selain itu",
    "kaku": "Tidak lentur", "kali": "Sungai atau kali lipat", "kamu": "Kau",
    "kaya": "Makmur", "kecil": "Tidak besar"[:4], "kena": "Terkena",
    "keras": "Tidak lunak"[:4], "kerja": "Pekerjaan"[:4],
    # 5-letter Indonesian
    "dapur": "Ruang memasak", "dalam": "Di bagian dalam", "rapat": "Pertemuan", "lampu": "Sumber cahaya",
    "kapal": "Kendaraan laut", "karya": "Hasil kreasi", "yakin": "Percaya penuh",
    "malam": "Waktu setelah senja", "mahal": "Harga tinggi", "mulai": "Dimulai", "lahir": "Keluar dari rahim",
    "pasar": "Tempat jual beli", "panah": "Senjata busur", "radar": "Alat deteksi", "rehat": "Istirahat",
    "suara": "Bunyi didengar", "sabar": "Tidak terburu", "abadi": "Kekal", "riset": "Penelitian",
    "tugas": "Kewajiban", "tiang": "Penyangga", "siang": "Tengah hari", "gaung": "Gema suara",
    "udara": "Gas dihirup", "untuk": "Bagi, tujuan", "akhir": "Paling akhir", "kisah": "Cerita",
    "negri": "Negeri", "nenas": "Buah nanas", "islam": "Agama", "salam": "Ungkapan hormat",
    "pohon": "Tumbuhan besar", "pintu": "Akses masuk", "paham": "Mengerti", "panas": "Suhu tinggi",
    "perlu": "Dibutuhkan", "pikir": "Berpikir", "pilot": "Pengemudi pesawat", "pohon": "Tumbuhan",
    "pusat": "Titik tengah", "ragam": "Variasi", "ramai": "Banyak orang", "ramah": "Bersikap baik",
    "sawah": "Lahan padi", "sebab": "Alasan", "segera": "Cepat"[:5], "senang": "Bahagia"[:5],
    "serta": "Beserta", "siapa": "Kata tanya orang",
    "tahan": "Bertahan", "tanam": "Menanam", "tanpa": "Without",
    "tempat": "Lokasi"[:5], "tepat": "Sesuai", "terus": "Berlanjut",
    "tidak": "Negasi", "tidur": "Istirahat tidur", "tigra": "Tigra"[:5],
    "timur": "Arah matahari terbit", "tinggi": "Ketinggian"[:5], "tirai": "Penutup jendela",
    "tubuh": "Badan manusia",
}

MS_CLUES = {
    # 3-letter Malay
    "air": "Cecair H₂O", "ada": "Wujud, hadir", "rak": "Papan penyimpan",
    "bau": "Aroma", "bak": "Bekas besar", "cat": "Bahan warna", "cap": "Tanda cetakan",
    "gol": "Jaringan bola sepak", "get": "Pintu gerbang", "lam": "Huruf Arab", "mat": "Alas lantai",
    "had": "Sempadan", "hak": "Hak milik", "dan": "Kata hubung", "kan": "Pengesahan",
    "abu": "Sisa pembakaran", "aki": "Bateri besar", "ala": "Cara, gaya",
    "api": "Nyala haba", "asa": "Harapan",
    "ban": "Larangan", "bar": "Batang logam",
    "cek": "Memeriksa", "cor": "Tuang simen",
    "dan": "Konjungsi", "era": "Zaman",
    "gas": "Berwujud gas", "gel": "Zat pekat",
    "ide": "Gagasan", "iya": "Setuju",
    "jam": "Alat menunjukkan waktu", "jus": "Sari buah",
    "kas": "Tunai", "lab": "Makmal",
    "las": "Kimpalan logam", "lot": "Lot atau undian",
    "mal": "Pusat membeli-belah", "net": "Jaring bersih",
    "oli": "Pelincir enjin", "pas": "Tepat",
    "sah": "Rasmi, sah", "set": "Himpunan",
    "teh": "Minuman daun", "tim": "Kumpulan",
    "ubi": "Ubi kayu", "uji": "Mencuba menguji",
    "wol": "Bahan dari biri-biri",
    # 4-letter Malay
    "bola": "Objek bulat", "baju": "Pakaian", "alam": "Persekitaran", "jamu": "Minuman herba",
    "cara": "Kaedah", "daya": "Tenaga", "foto": "Gambar kamera", "gula": "Pemanis",
    "guru": "Pengajar", "hati": "Organ atau perasaan", "hari": "24 jam", "tiga": "Nombor 3",
    "jaga": "Mengawasi", "juta": "Sejuta", "anda": "Kata ganti diri kedua", "atap": "Bumbung",
    "kota": "Kawasan bandar", "laut": "Air masin besar", "nama": "Identiti", "nasi": "Beras masak",
    "pagi": "Awal hari", "rasa": "Perasaan", "satu": "Nombor 1", "tahu": "Mengerti atau makanan",
    "abdi": "Hamba setia", "akar": "Bahagian tumbuhan", "alat": "Perkakas",
    "anak": "Keturunan", "asli": "Tulen", "baik": "Positif",
    "baru": "Tidak lama", "bawa": "Membawa", "beda": "Berbeza",
    "beli": "Membeli", "bisa": "Mampu", "buka": "Membuka",
    "buku": "Penerbitan bertulis", "bumi": "Planet kita",
    "cari": "Mencari", "coba": "Mencuba", "dada": "Bahagian dada",
    "daun": "Bahagian tumbuhan", "enak": "Sedap", "gigi": "Organ pengunyah",
    "guna": "Manfaat", "ikat": "Mengikat", "ilmu": "Pengetahuan",
    "jalan": "Tempat berjalan"[:4], "jauh": "Berjauhan", "jual": "Menjual",
    "kamu": "Kau", "kaya": "Makmur", "kena": "Terkena",
    "rela": "Sanggup, ikhlas", "ikan": "Hidupan air bersisik",
    # 5-letter Malay
    "dapur": "Bilik memasak", "dalam": "Di bahagian dalam", "rumah": "Tempat tinggal", "mahir": "Pakar",
    "kapal": "Kenderaan laut", "karya": "Hasil ciptaan", "yakin": "Percaya sepenuhnya",
    "malam": "Waktu selepas senja", "mahal": "Harga tinggi", "mulai": "Bermula", "lahir": "Keluar dari rahim",
    "pasar": "Tempat beli-belah", "panah": "Senjata busur", "radar": "Alat pengesan", "rehat": "Berehat",
    "suara": "Bunyi didengari", "sabar": "Tidak tergesa", "abadi": "Kekal", "riset": "Penyelidikan",
    "tugas": "Tanggungjawab", "tiang": "Penyangga", "siang": "Tengah hari", "gaung": "Gema",
    "udara": "Gas dihirup", "untuk": "Tujuan", "akhir": "Paling akhir", "kisah": "Cerita",
    "negri": "Negeri", "nenas": "Buah nanas", "islam": "Agama", "salam": "Ucapan hormat",
    "pohon": "Pokok besar", "pintu": "Akses masuk", "paham": "Faham", "panas": "Suhu tinggi",
    "pusat": "Titik tengah", "ragam": "Variasi", "ramai": "Banyak orang", "ramah": "Mesra",
    "sawah": "Kawasan padi", "sebab": "Sebab musabab",
    "tahan": "Bertahan", "tanam": "Menanam", "tanpa": "Tanpa",
    "tepat": "Sesuai", "terus": "Berterusan", "tidak": "Tidak",
    "tidur": "Berehat tidur", "timur": "Arah matahari terbit",
    "tubuh": "Badan manusia",
}

LANG_CLUES = {"en": EN_CLUES, "tr": TR_CLUES, "nl": NL_CLUES, "id": ID_CLUES, "ms": MS_CLUES}
LANG_WORDS = {lang: list(clues.keys()) for lang, clues in LANG_CLUES.items()}


def words_by_length(words):
    wbl = {}
    for w in words:
        w = w.lower()
        if w.isalpha():
            wbl.setdefault(len(w), []).append(w)
    return wbl


TARGET_SIZES = [(3, 5), (4, 8), (5, 7)]  # (size, count)
TARGET_TOTAL = 20  # new puzzles per language


errors_total = 0
for lang in ["en", "tr", "nl", "id", "ms"]:
    path = BASE / f"{lang}.json"
    with open(path) as f:
        existing = json.load(f)

    clues = LANG_CLUES[lang]
    wbl = words_by_length(LANG_WORDS[lang])
    new_puzzles = []
    used_words = set()

    for size, count in TARGET_SIZES:
        quads = find_quads(wbl, size, n=count * 3)  # find extra in case some fail clue lookup
        added = 0
        for w1, w2, w3, w4 in quads:
            if added >= count:
                break
            if any(w not in clues for w in (w1, w2, w3, w4)):
                continue
            p = make_puzzle(size, w1, clues[w1], w2, clues[w2], w3, clues[w3], w4, clues[w4])
            new_puzzles.append(p)
            used_words.update([w1, w2, w3, w4])
            added += 1
        print(f"  [{lang}] size-{size}: found {added}/{count}")

    combined = existing + new_puzzles
    try:
        validate_crossword_pool(lang, combined)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(combined, f, ensure_ascii=False, indent=2)
        print(f"{lang}: {len(existing)} + {len(new_puzzles)} = {len(combined)} crosswords written OK")
    except Exception as e:
        print(f"{lang} VALIDATION ERROR: {e}")
        errors_total += 1

if errors_total == 0:
    print("\nAll done!")
else:
    print(f"\n{errors_total} language(s) had errors.")
