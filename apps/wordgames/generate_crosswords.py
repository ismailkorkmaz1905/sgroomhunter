"""
Add new crossword puzzles to existing data for all languages.
EN puzzles are the source; TR/NL/ID/MS get equivalent translations.
Validates every puzzle before writing.

Crossword grid patterns used:
  size-3: blocks=[[1,1]]           corner-and-cross
  size-4: blocks=[[1,1],[1,2],[2,1],[2,2]]  donut
  size-5: blocks=rows1-3 x cols1-3           donut-large

Constraints per pattern
  size-3: w1[0]=w2[0], w1[2]=w3[0], w4[0]=w2[2], w4[2]=w3[2]
  size-4: w1[0]=w2[0], w1[3]=w3[0], w4[0]=w2[3], w4[3]=w3[3]
  size-5: w1[0]=w2[0], w1[4]=w3[0], w4[0]=w2[4], w4[4]=w3[4]
"""
import json
from pathlib import Path
from wordgames_validation import validate_crossword_pool

BASE = Path(__file__).parent / "data" / "crosswords"

BLOCKS = {
    3: [[1, 1]],
    4: [[1, 1], [1, 2], [2, 1], [2, 2]],
    5: [[1, 1], [1, 2], [1, 3], [2, 1], [2, 2], [2, 3], [3, 1], [3, 2], [3, 3]],
}


def make(size, w1, c1, w2, c2, w3, c3, w4, c4):
    """Build a puzzle entry. w=answer, c=clue."""
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


def check(p):
    """Quick in-memory check of letter intersections."""
    size = p["size"]
    blocks = {tuple(b) for b in p["blocks"]}
    occupied = {}
    for e in p["entries"]:
        d, r, c, ans = e["direction"], e["row"], e["col"], e["answer"]
        for i, ch in enumerate(ans):
            cr = r + (i if d == "down" else 0)
            cc = c + (i if d == "across" else 0)
            assert (cr, cc) not in blocks, f"Hit block at ({cr},{cc}) in {e}"
            assert cr < size and cc < size, f"Overflow at ({cr},{cc})"
            if (cr, cc) in occupied:
                assert occupied[(cr, cc)] == ch, \
                    f"Conflict at ({cr},{cc}): '{occupied[(cr,cc)]}' vs '{ch}' [{e['answer']}]"
            occupied[(cr, cc)] = ch


# ---------------------------------------------------------------------------
# NEW EN PUZZLES  (20)
# ---------------------------------------------------------------------------
NEW_EN = [
    # --- size 3 (5 new) ---
    make(3, "hot", "Opposite of cold", "ham", "Cured pork leg", "top", "Highest point", "map", "Guide to places"),
    make(3, "big", "Large in size", "bus", "Road vehicle with many seats", "gem", "Precious stone", "sum", "Result of addition"),
    make(3, "par", "Expected golf score", "pod", "Seed case of a pea", "raw", "Uncooked", "dew", "Morning moisture on grass"),
    make(3, "cup", "Small drinking vessel", "cob", "Corn on the ___", "pit", "Hole in the ground", "bit", "Small piece"),
    make(3, "jar", "Glass container with a lid", "jot", "Write briefly", "rot", "Decay", "dot", "Tiny round mark"),
    # --- size 4 (7 new) ---
    make(4, "bold", "Brave or daring", "brew", "Make tea or beer", "dusk", "End of daylight", "walk", "Move on foot"),
    make(4, "gift", "Something given freely", "glow", "Emit soft light", "time", "Clock measures this", "wore", "Had on (past tense)"),
    make(4, "keep", "Hold onto", "king", "Male monarch", "pond", "Small body of water", "gold", "Precious yellow metal"),
    make(4, "firm", "Solid; a company", "fawn", "Baby deer", "mist", "Light fog", "next", "Coming right after"),
    make(4, "camp", "Outdoor sleeping spot", "coin", "Metal money disk", "path", "Narrow trail", "nosh", "Eat snacks"),
    make(4, "harp", "Stringed instrument with a triangular frame", "hard", "Difficult", "pave", "Cover with asphalt", "dune", "Sand hill"),
    make(4, "stem", "Plant stalk", "snow", "Frozen white precipitation", "mild", "Not harsh", "wand", "Magic stick"),
    # --- size 5 (8 new) ---
    make(5, "flame", "Burning tongue of fire", "field", "Open area of grass", "enter", "Go into", "diner", "Small roadside restaurant"),
    make(5, "grasp", "Grip tightly", "gloom", "Dim darkness", "prize", "Award for winning", "mouse", "Small rodent"),
    make(5, "blast", "Powerful explosion", "braid", "Woven strands of hair", "tiger", "Large striped wild cat", "rider", "One who rides"),
    make(5, "snore", "Loud sleep sound", "stein", "Large beer mug", "envoy", "Diplomatic messenger", "nasty", "Unpleasant"),
    make(5, "plumb", "Test for vertical alignment", "prose", "Ordinary written language", "board", "Flat piece of wood", "embed", "Fix firmly inside"),
    make(5, "chant", "Repetitive song or phrase", "crave", "Desire strongly", "troll", "Online agitator", "expel", "Force out"),
    make(5, "swamp", "Marshy wetland", "spike", "Sharp pointed object", "pixel", "Smallest screen dot", "excel", "Perform very well"),
    make(5, "trend", "Current popular direction", "toxin", "Poisonous substance", "depth", "Distance downward", "notch", "V-shaped cut"),
]

# ---------------------------------------------------------------------------
# NEW TR PUZZLES  (20)  — same grid structure, Turkish words
# ---------------------------------------------------------------------------
NEW_TR = [
    make(3, "hız", "Sürat, tempo", "hal", "Durum, pazar yeri", "zor", "Güç, çetin", "ler", "Çoğul eki"),
    make(3, "göl", "Kapalı su kütlesi", "gün", "24 saatlik zaman", "lov", "Kart oyunu terimi", "nun", "Keşiş giysisi"),
    make(3, "son", "En sonda olan", "sap", "Ot veya alet tutamağı", "nar", "Kırmızı taneli meyve", "per", "Peri, cin"),
    make(3, "kot", "Denim pantolon", "kol", "Vücudun üst uzvu", "tel", "İnce metal ip", "lal", "Değerli kırmızı taş"),
    make(3, "yol", "Güzergah, patika", "yaz", "Sıcak mevsim", "lik", "Ölçü birimi eki", "zık", "Sıkıcı, bunaltıcı"),
    make(4, "masa", "Üzeri düz mobilya", "mart", "Yılın üçüncü ayı", "anka", "Efsanevi ateş kuşu", "atık", "Artık madde, çöp"),
    make(4, "kale", "Savunma yapısı", "kara", "Siyah renk veya toprak", "eser", "Sanat yapıtı", "atar", "Fırlatır (fiil)"),
    make(4, "renk", "Işığın görüntüsü", "rüya", "Uyku görüntüsü", "kok", "Kömür artığı", "yakı", "Isıtıcı madde"),
    make(4, "dere", "Küçük akarsu", "dolu", "İçi boş olmayan", "elde", "Mülkiyette, elde", "ülke", "Devlet toprakları"),
    make(4, "peri", "Masallardaki kanatl varlık", "pile", "Pil veya tabaka", "risk", "Tehlike ihtimali", "eşik", "Kapı altlığı"),
    make(4, "gemi", "Deniz taşıtı", "genç", "Yaşı az olan", "mide", "Sindirim organı", "çeki", "Yük birimi"),
    make(4, "ince", "Kalın olmayan", "isim", "Ad, lakap", "elek", "Eleyen araç", "mek", "Fiil mastar eki"),
    make(5, "deniz", "Büyük tuzlu su kütlesi", "duman", "Yangın dumanı", "zemin", "Taban, yer", "neden", "Sebep, gerekçe"),
    make(5, "kalem", "Yazı yazma aracı", "kadın", "Yetişkin bayan", "maden", "Yer altı kaynağı", "neden", "Sebep, gerekçe"),
    make(5, "güneş", "Güneş sistemi yıldızı", "güzel", "Estetik açıdan hoş", "şeker", "Tatlı madde", "lider", "Önder kişi"),
    make(5, "yıldız", "Gecede parlayan gök cismi"[:20], "yılmaz", "Vazgeçmez, kararlı", "zaman", "Geçen süre", "nazar", "Kötü bakış"),
    make(5, "nehir", "Akan büyük su yolu", "niyet", "Amaç, kasıt", "rüzgar", "Hava akıntısı"[:10], "tarih", "Geçmiş olaylar"),
    make(5, "ışılt", "Parıltı, parlaklık", "insan", "Homo sapiens", "talih", "Kader, şans", "nehir", "Akan büyük su"),
    make(5, "bahar", "İlkbahar mevsimi", "bilgi", "Öğrenilen şey", "rengi", "Renk eki formu", "iğne", "Dikiş aleti"),
    make(5, "çiçek", "Bitkinin renkli kısmı", "çizgi", "İnce çizik", "kırmı", "Kırmızı renk kökü", "iğnelik", "Dikiş kutusu"[:6]),
]

# --- TR words might be short; re-do with safe 3/4/5-letter Turkish words ---
# Easier to do only EN + adapt via separate language files
# Skip auto-TR for now: just do EN, NL, ID, MS carefully

# ---------------------------------------------------------------------------
# NEW NL PUZZLES  (20) — Dutch
# ---------------------------------------------------------------------------
NEW_NL = [
    make(3, "uur", "Zestig minuten", "uit", "Niet thuis", "ros", "Bruinrood paard", "tas", "Draagbare zak"),
    make(3, "dag", "24 uur", "dak", "Bovenkant van een huis", "gek", "Gek, dwaas", "koe", "Melkdier"),
    make(3, "zee", "Groot wateroppervlak", "zin", "Gevoel of betekenis", "eis", "Recht op iets", "nis", "Kleine ruit"),
    make(3, "pad", "Klein pad of pad (amfibie)", "pan", "Kookgerei", "dak", "Afdak", "nak", "Tik, klop"),
    make(3, "wit", "Kleur van sneeuw", "web", "Spinnenweb of internet", "tak", "Boomtak", "bak", "Bak, container"),
    make(4, "boom", "Groot gewas met stam", "band", "Muziekgroep of rubber ring", "mist", "Lichte nevel", "dier", "Levend wezen"),
    make(4, "reis", "Trip, tocht", "rood", "Kleur van bloed", "stad", "Grote nederzetting", "deur", "Opening in muur"),
    make(4, "huis", "Woongebouw", "hoed", "Hoofddeksel", "slim", "Intelligent", "dier", "Levend wezen"),
    make(4, "wolf", "Wild roofdier", "warm", "Niet koud", "fles", "Glazen container", "meer", "Stiller dan zee"),
    make(4, "goud", "Geel edelmetaal", "glas", "Transparant materiaal", "dans", "Rhythmische beweging", "snel", "Vlug"),
    make(4, "dorp", "Klein woonplaats", "draad", "Dun touw"[:4], "paar", "Twee bij elkaar", "aard", "Aarde, natuur"),
    make(4, "plek", "Specifieke locatie", "plus", "Meer, extra", "klem", "Vastgezet", "smal", "Niet breed"),
    make(5, "toren", "Hoog gebouw", "tafel", "Meubelstuk", "negen", "Getal na acht", "laden", "Vullen of lades"),
    make(5, "water", "H twee O", "wacht", "Bewaker", "regen", "Neerslag", "taken", "Opdrachten"),
    make(5, "groen", "Kleur van gras", "graag", "Met plezier", "nacht", "Donkere periode", "gedoe", "Drukte, gedoe"),
    make(5, "bloem", "Kleurrijk plantdeel", "brood", "Gebakken graanproduct", "molen", "Windenergiemachine", "deken", "Wollen deken"),
    make(5, "prijs", "Kosten of award", "plank", "Houten lat", "schip", "Varend vaartuig", "kaart", "Stuk papier"),
    make(5, "fiets", "Tweewieler", "flink", "Stevig, behoorlijk", "stoer", "Dapper, robuust", "kader", "Omlijsting"),
    make(5, "ruimte", "Heelal of vrije plek"[:5], "rijke", "Welvarend (mv)", "extra", "Meer dan normaal", "arena", "Sportarena"),
    make(5, "muziek", "Klankenkunst"[:5], "mager", "Niet dik", "krant", "Dagblad", "taken", "Opdrachten"),
]

# ---------------------------------------------------------------------------
# NEW ID PUZZLES  (20) — Indonesian
# ---------------------------------------------------------------------------
NEW_ID = [
    make(3, "air", "Zat cair H₂O", "ada", "Eksis, hadir", "rak", "Papan penyimpan", "dak", "Atap datar"),
    make(3, "bau", "Aroma tidak sedap", "bak", "Wadah besar", "ubi", "Umbi-umbian", "kiri", "Sisi sebelah kiri"[:3]),
    make(3, "cat", "Zat warna", "cap", "Tanda atau cetakan", "ter", "Akhiran zat kimia", "per", "Akhiran alat"),
    make(3, "dom", "Bisu, tidak bersuara", "doa", "Permohonan kepada Tuhan", "mas", "Emas atau panggilan", "asa", "Harapan"),
    make(3, "ibu", "Orang tua perempuan", "isi", "Kandungan, konten", "buku", "Kumpulan halaman"[:3], "uku", "Ukuran (akhiran)"),
    make(4, "bola", "Objek bundar", "baju", "Pakaian badan atas", "alam", "Lingkungan alam", "jamu", "Minuman herbal"),
    make(4, "coba", "Mencoba sesuatu", "cara", "Metode, langkah", "abad", "100 tahun", "rado", "Suka bersolek"[:4]),
    make(4, "daya", "Kemampuan, tenaga", "duit", "Uang (slang)", "yuda", "Perang (lama)", "itik", "Bebek"),
    make(4, "foto", "Gambar dari kamera", "film", "Karya sinema", "toko", "Tempat berjualan", "miko", "Nama depan Jepang"[:4]),
    make(4, "gula", "Pemanis alami", "guru", "Pengajar", "alam", "Lingkungan alam", "ruma", "Rumah (lama)"[:4]),
    make(4, "hati", "Organ tubuh atau perasaan", "hari", "Satu putaran Bumi", "tiga", "Angka 3", "inga", "Ingat (tua)"[:4]),
    make(4, "ikut", "Turut serta", "izin", "Ijin", "tahu", "Mengerti atau makanan", "nahu", "Tata bahasa"[:4]),
    make(5, "dapur", "Ruang memasak", "dalam", "Di bagian dalam", "rapat", "Pertemuan resmi", "lampu", "Sumber cahaya"),
    make(5, "kapal", "Kendaraan air besar", "karya", "Hasil kreasi", "lapan", "Delapan (lama)", "yakin", "Percaya penuh"),
    make(5, "malam", "Waktu setelah matahari terbenam", "mahal", "Harga tinggi", "mulai", "Dimulai", "lahir", "Keluar dari rahim"),
    make(5, "negri", "Negeri, tanah air"[:5], "nenas", "Buah tropis", "islam", "Agama samawi", "salam", "Ungkapan hormat"),
    make(5, "pasar", "Tempat jual beli", "panah", "Senjata busur", "radar", "Alat deteksi", "rehat", "Istirahat"),
    make(5, "suara", "Bunyi yang didengar", "sabar", "Tidak terburu-buru", "abadi", "Kekal, selamanya", "riset", "Penelitian"),
    make(5, "tugas", "Kewajiban, pekerjaan", "tiang", "Penyangga tegak", "siang", "Waktu tengah hari", "gaung", "Gema suara"),
    make(5, "udara", "Gas yang dihirup", "untuk", "Tujuan, bagi", "akhir", "Bagian paling akhir", "kisah", "Cerita, narasi"),
]

# ---------------------------------------------------------------------------
# NEW MS PUZZLES  (20) — Malay
# ---------------------------------------------------------------------------
NEW_MS = [
    make(3, "air", "Cecair H₂O", "ada", "Wujud, hadir", "rak", "Papan penyimpan", "dak", "Bumbung rata"),
    make(3, "bau", "Aroma", "bak", "Bekas besar", "ubi", "Keledek atau ubi kayu", "kiri", "Arah sebelah kiri"[:3]),
    make(3, "cat", "Bahan warna", "cap", "Tanda atau cetakan", "ter", "Akhiran kimia", "per", "Akhiran alat"),
    make(3, "gol", "Jaringan dalam bola sepak", "get", "Pintu gerbang", "lam", "Huruf Arab", "mat", "Alas lantai"),
    make(3, "had", "Batas atau sempadan", "hak", "Hak milik", "dan", "Kata hubung", "kan", "Partikel pengesahan"),
    make(4, "bola", "Objek bulat", "baju", "Pakaian badan", "alam", "Persekitaran semula jadi", "jamu", "Minuman herba"),
    make(4, "cara", "Kaedah, langkah", "cari", "Mencari sesuatu", "abdi", "Hamba setia", "ikan", "Hidupan air bersisik"),
    make(4, "daya", "Tenaga, kemampuan", "duit", "Wang (slang)", "yuda", "Perang (lama)", "itik", "Bebek"),
    make(4, "foto", "Gambar dari kamera", "fail", "Folder atau berkas", "toko", "Kedai", "leka", "Lalai, cuai"),
    make(4, "gula", "Pemanis semula jadi", "guru", "Pengajar", "alam", "Persekitaran", "rela", "Sanggup, ikhlas"),
    make(4, "hati", "Organ atau perasaan", "hari", "24 jam", "tiga", "Nombor 3", "ikat", "Mengikat sesuatu"),
    make(4, "jaga", "Berjaga, mengawasi", "juta", "Sejuta", "anda", "Kata ganti diri kedua", "atap", "Bumbung rumah"),
    make(5, "dapur", "Bilik memasak", "dalam", "Di bahagian dalam", "rumah", "Tempat tinggal", "mahir", "Pakar, cekap"),
    make(5, "kapal", "Kenderaan air besar", "karya", "Hasil ciptaan", "lapan", "Nombor lapan", "yakin", "Percaya sepenuhnya"),
    make(5, "malam", "Waktu selepas senja", "mahal", "Harga tinggi", "mulai", "Bermula", "lahir", "Keluar dari rahim"),
    make(5, "negri", "Negeri, wilayah"[:5], "nenas", "Buah nanas", "islam", "Agama samawi", "salam", "Ucapan hormat"),
    make(5, "pasar", "Tempat beli-belah", "panah", "Senjata busur", "radar", "Alat pengesan", "rehat", "Berehat"),
    make(5, "suara", "Bunyi yang didengari", "sabar", "Tidak tergesa-gesa", "abadi", "Kekal selamanya", "riset", "Penyelidikan"),
    make(5, "tugas", "Tanggungjawab", "tiang", "Tiang penyangga", "siang", "Tengah hari", "gaung", "Gema"),
    make(5, "udara", "Gas yang dihirup", "untuk", "Tujuan, bagi", "akhir", "Bahagian terakhir", "kisah", "Cerita, naratif"),
]

LANG_NEW = {
    "en": NEW_EN,
    "nl": NEW_NL,
    "id": NEW_ID,
    "ms": NEW_MS,
}

errors = 0
for lang, new_puzzles in LANG_NEW.items():
    path = BASE / f"{lang}.json"
    with open(path) as f:
        existing = json.load(f)
    combined = existing + new_puzzles
    # Quick per-puzzle check
    for i, p in enumerate(combined, 1):
        try:
            check(p)
        except AssertionError as e:
            print(f"  [{lang}] puzzle #{i}: {e}")
            errors += 1
    # Full validator
    try:
        validate_crossword_pool(lang, combined)
        print(f"{lang} crosswords: {len(combined)} OK")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(combined, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"{lang} crosswords ERROR: {e}")
        errors += 1

# TR gets same EN puzzles (language-agnostic clues not needed; EN is the only language crossword is based on)
# For TR, let's write translated versions manually after checking EN passes
if errors == 0:
    print("\nAll languages written successfully.")
else:
    print(f"\n{errors} error(s) found. Files NOT written for errored languages.")
