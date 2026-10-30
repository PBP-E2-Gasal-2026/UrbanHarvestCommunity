from django.core.management.base import BaseCommand
from django.utils.text import slugify

from authentication.models import Merchant, Profile, Role, User
from marketplace.models import Category, Product

CATEGORIES = ['Sayuran', 'Buah', 'Bibit', 'Kompos', 'Media Tanam']

# (nama, kategori, harga, stok, lokasi, satuan, minimal beli)
PRODUCTS = [
    ('Tomat Cherry Organik', 'Sayuran', 25000, 30, 'Depok', 'kg', 1),
    ('Kangkung Hidroponik', 'Sayuran', 8000, 50, 'Jakarta Selatan', 'ikat', 2),
    ('Selada Romaine', 'Sayuran', 12000, 18, 'Bogor', 'pcs', 1),
    ('Bayam Merah', 'Sayuran', 9000, 0, 'Depok', 'ikat', 1),
    ('Stroberi Segar', 'Buah', 45000, 0, 'Bogor', 'pack', 1),
    ('Melon Golden', 'Buah', 38000, 6, 'Bekasi', 'pcs', 1),
    ('Jeruk Lemon', 'Buah', 22000, 15, 'Tangerang', 'kg', 1),
    ('Pepaya California', 'Buah', 15000, 9, 'Depok', 'pcs', 1),
    ('Bibit Cabai Rawit', 'Bibit', 15000, 40, 'Depok', 'pot', 1),
    ('Bibit Tomat Servo', 'Bibit', 12000, 25, 'Bogor', 'pot', 1),
    ('Bibit Kemangi', 'Bibit', 7000, 60, 'Jakarta Timur', 'pot', 3),
    ('Bibit Terong Ungu', 'Bibit', 10000, 0, 'Bekasi', 'pot', 1),
    ('Kompos Daun 5kg', 'Kompos', 20000, 25, 'Bekasi', 'karung', 1),
    ('Pupuk Kascing 2kg', 'Kompos', 18000, 30, 'Depok', 'pack', 1),
    ('Bokashi Organik 5kg', 'Kompos', 27000, 12, 'Bogor', 'karung', 1),
    ('Cocopeat 2kg', 'Media Tanam', 18000, 12, 'Tangerang', 'pack', 1),
    ('Sekam Bakar 5kg', 'Media Tanam', 15000, 20, 'Bogor', 'karung', 1),
    ('Rockwool Hidroponik', 'Media Tanam', 55000, 8, 'Jakarta Selatan', 'pack', 1),
]


# Foto mockup dari Wikimedia Commons, dipakai sesuai lisensinya masing-masing.
MOCKUP_IMAGES = {
    'Tomat Cherry Organik': (
        'https://thumb.wikimedia.org/wikipedia/commons/thumb/a/ac/Yellow_cherry_tomatoes.jpg/960px-Yellow_cherry_tomatoes.jpg',
        'Yellow cherry tomatoes.jpg — CC BY-SA 4.0',
    ),
    'Kangkung Hidroponik': (
        'https://thumb.wikimedia.org/wikipedia/commons/thumb/9/9a/Ipomoea_aquatica_%282%29.JPG/960px-Ipomoea_aquatica_%282%29.JPG',
        'Ipomoea aquatica (2).JPG — CC BY-SA 3.0',
    ),
    'Selada Romaine': (
        'https://thumb.wikimedia.org/wikipedia/commons/thumb/6/6b/Romaine_lettuce.jpg/960px-Romaine_lettuce.jpg',
        'Romaine lettuce.jpg — CC BY-SA 3.0',
    ),
    'Bayam Merah': (
        'https://thumb.wikimedia.org/wikipedia/commons/thumb/4/44/Leaves_of_Amaranthus_tricolor.jpg/960px-Leaves_of_Amaranthus_tricolor.jpg',
        'Leaves of Amaranthus tricolor.jpg — CC BY-SA 4.0',
    ),
    'Stroberi Segar': (
        'https://thumb.wikimedia.org/wikipedia/commons/thumb/7/71/Strawberry_leaf_in_the_garden_closeup.jpg/960px-Strawberry_leaf_in_the_garden_closeup.jpg',
        'Strawberry leaf in the garden closeup.jpg — CC BY 2.0',
    ),
    'Melon Golden': (
        'https://thumb.wikimedia.org/wikipedia/commons/thumb/b/b1/Canteloupe_and_cross_section.jpg/960px-Canteloupe_and_cross_section.jpg',
        'Canteloupe and cross section.jpg — GFDL 1.2',
    ),
    'Jeruk Lemon': (
        'https://thumb.wikimedia.org/wikipedia/commons/thumb/e/e4/Lemon.jpg/960px-Lemon.jpg',
        'Lemon.jpg — CC BY-SA 2.5',
    ),
    'Pepaya California': (
        'https://thumb.wikimedia.org/wikipedia/commons/thumb/1/12/03_Preparing_papaya_fruit_-_papaya_peeled_and_cut_in_half.jpg/960px-03_Preparing_papaya_fruit_-_papaya_peeled_and_cut_in_half.jpg',
        '03 Preparing papaya fruit - papaya peeled and cut in half.jpg — CC BY 3.0',
    ),
    'Bibit Cabai Rawit': (
        'https://thumb.wikimedia.org/wikipedia/commons/thumb/f/f8/VitorJubini_MercadoDaVilaRubim_Vitoria_ES_%2839182859020%29_%28square_crop%29.jpg/960px-VitorJubini_MercadoDaVilaRubim_Vitoria_ES_%2839182859020%29_%28square_crop%29.jpg',
        'VitorJubini MercadoDaVilaRubim Vitoria ES (39182859020) (square crop).jpg — Public domain',
    ),
    'Bibit Tomat Servo': (
        'https://thumb.wikimedia.org/wikipedia/commons/thumb/a/a2/Tomato_seedlings_%28464347374%29.jpg/960px-Tomato_seedlings_%28464347374%29.jpg',
        'Tomato seedlings (464347374).jpg — CC BY 2.0',
    ),
    'Bibit Kemangi': (
        'https://thumb.wikimedia.org/wikipedia/commons/thumb/6/6e/Basil_plant_in_a_pot_02.jpg/960px-Basil_plant_in_a_pot_02.jpg',
        'Basil plant in a pot 02.jpg — CC BY-SA 4.0',
    ),
    'Bibit Terong Ungu': (
        'https://thumb.wikimedia.org/wikipedia/commons/thumb/4/4c/Young_eggplant_%28Solanum_melongena%29_seedling_1.jpg/960px-Young_eggplant_%28Solanum_melongena%29_seedling_1.jpg',
        'Young eggplant (Solanum melongena) seedling 1.jpg — CC BY-SA 4.0',
    ),
    'Kompos Daun 5kg': (
        'https://thumb.wikimedia.org/wikipedia/commons/thumb/f/f2/Compost_bin_with_compost.jpg/960px-Compost_bin_with_compost.jpg',
        'Compost bin with compost.jpg — CC BY-SA 4.0',
    ),
    'Pupuk Kascing 2kg': (
        'https://thumb.wikimedia.org/wikipedia/commons/thumb/2/2b/Organik-gubre-cesitleri.jpg/960px-Organik-gubre-cesitleri.jpg',
        'Organik-gubre-cesitleri.jpg — CC BY-SA 4.0',
    ),
    'Bokashi Organik 5kg': (
        'https://upload.wikimedia.org/wikipedia/commons/d/d9/Bokashi_bin_set.JPG',
        'Bokashi bin set.JPG — CC BY-SA 3.0',
    ),
    'Cocopeat 2kg': (
        'https://thumb.wikimedia.org/wikipedia/commons/thumb/9/9e/Traditional_worker_with_coconut_rope_%28edited%29.jpg/960px-Traditional_worker_with_coconut_rope_%28edited%29.jpg',
        'Traditional worker with coconut rope (edited).jpg — CC BY-SA 4.0',
    ),
    'Sekam Bakar 5kg': (
        'https://thumb.wikimedia.org/wikipedia/commons/thumb/9/9a/%E3%83%A2%E3%83%9F%E3%82%AC%E3%83%A9%E3%81%8F%E3%82%93%E7%82%AD%E3%81%A5%E3%81%8F%E3%82%8A.jpg/960px-%E3%83%A2%E3%83%9F%E3%82%AC%E3%83%A9%E3%81%8F%E3%82%93%E7%82%AD%E3%81%A5%E3%81%8F%E3%82%8A.jpg',
        'モミガラくん炭づくり.jpg — CC BY-SA 4.0',
    ),
    'Rockwool Hidroponik': (
        'https://thumb.wikimedia.org/wikipedia/commons/thumb/9/9c/Diagonal_Hydroponic_Pattern.jpg/960px-Diagonal_Hydroponic_Pattern.jpg',
        'Diagonal Hydroponic Pattern.jpg — CC BY 4.0',
    ),
}


# Titik kira-kira pusat tiap kota, cukup untuk menampilkan peta di mockup.
COORDINATES = {
    'Depok': (-6.402484, 106.794243),
    'Jakarta Selatan': (-6.261493, 106.810600),
    'Jakarta Timur': (-6.225014, 106.900447),
    'Bogor': (-6.597147, 106.806038),
    'Bekasi': (-6.238270, 106.975571),
    'Tangerang': (-6.178306, 106.631889),
}

# Akun demo lokal: (username, password, peran, lokasi produk yang dijual).
SELLERS = [
    ('petani_penjual', 'petani-123!', ('Depok', 'Jakarta Selatan', 'Jakarta Timur')),
    ('kebun_sinta', 'sinta-123!', ('Bogor', 'Bekasi', 'Tangerang')),
]

# Nama toko (model Merchant milik modul autentikasi) untuk akun penjual demo.
MERCHANTS = [
    ('petani_penjual', 'Kebun Urban Depok', 'Depok'),
    ('kebun_sinta', 'Kebun Sinta Bogor', 'Bogor'),
]


class Command(BaseCommand):
    help = 'Mengisi kategori, produk, dan akun demo untuk marketplace'

    def _user(self, username, password, roles):
        user, created = User.objects.get_or_create(
            username=username, defaults={'email': f'{username}@example.com'}
        )
        if created:
            user.set_password(password)
            user.save()
        user.roles.add(*roles)
        return user

    def handle(self, *args, **options):
        seller_role, _ = Role.objects.get_or_create(
            name='farmer-seller', defaults={'description': 'Petani - Penjual'}
        )
        # Registrasi memberi peran 'farmer' (Petani), jadi akun demo mengikuti aturan yang sama.
        farmer_role, _ = Role.objects.get_or_create(
            name='farmer', defaults={'description': 'Petani'}
        )
        sellers = {
            location: self._user(username, password, [seller_role, farmer_role])
            for username, password, locations in SELLERS
            for location in locations
        }
        buyer = self._user('pembeli_demo', 'pembeli-123!', [farmer_role])
        for user in {*sellers.values(), buyer}:
            Profile.objects.get_or_create(user=user)
        for username, name, location in MERCHANTS:
            Merchant.objects.get_or_create(
                owner=User.objects.get(username=username),
                defaults={'name': name, 'location': location,
                          'description': f'Hasil kebun urban segar dari {location}.'},
            )

        categories = {
            name: Category.objects.get_or_create(name=name, defaults={'slug': slugify(name)})[0]
            for name in CATEGORIES
        }
        for index, (name, category, price, stock, location, unit, min_order) in enumerate(PRODUCTS):
            # Geser sedikit per produk agar titik di peta tidak saling menumpuk.
            base_lat, base_lng = COORDINATES[location]
            latitude = round(base_lat + ((index % 5) - 2) * 0.012, 6)
            longitude = round(base_lng + ((index % 3) - 1) * 0.015, 6)
            Product.objects.update_or_create(
                name=name,
                defaults={
                    'seller': sellers[location],
                    'category': categories[category],
                    'price': price,
                    'stock': stock,
                    'unit': unit,
                    'min_order': min_order,
                    'location': location,
                    'pickup_address': f'Kebun komunitas {location}, dekat balai warga',
                    'pickup_notes': 'Senin–Sabtu, 07.00–11.00',
                    'latitude': latitude,
                    'longitude': longitude,
                    'description': f'{name} segar dari kebun urban di {location}, dirawat tanpa pestisida kimia.',
                    'image_url': MOCKUP_IMAGES.get(name, ('', ''))[0],
                },
            )
        self.stdout.write(self.style.SUCCESS(f'{len(PRODUCTS)} produk contoh siap.'))
