from tkinter import *
from tkinter import ttk, messagebox
import tkintermapview
import json
import os
import requests
from bs4 import BeautifulSoup
import re

obiekty_sakralne = []
duchowni = []
pracownicy = []


class ObiektSakralny:
    def __init__(self, nazwa, miejscowosc, typ_obiektu):
        self.nazwa = nazwa
        self.miejscowosc = miejscowosc
        self.typ_obiektu = typ_obiektu
        self.coordinates = self.get_coordinates()
        self.marker = None
        if self.coordinates[0] != 0 and self.coordinates[1] != 0:
            self.marker = map_widget.set_marker(self.coordinates[0], self.coordinates[1], text=self.nazwa)

    def get_coordinates(self):
        try:
            search_terms = [
                f'{self.nazwa}_{self.miejscowosc}',
                f'{self.typ_obiektu}_{self.nazwa}_{self.miejscowosc}',
                f'Kościół_{self.nazwa}_{self.miejscowosc}' if self.typ_obiektu == 'Kościół' else None,
                f'{self.nazwa}_w_{self.miejscowosc}',
                f'{self.nazwa}',
                f'{self.miejscowosc}_{self.nazwa}',
                f'{self.miejscowosc}'
            ]

            search_terms = [term for term in search_terms if term is not None]

            print(f"Szukam współrzędnych dla: {self.nazwa} w {self.miejscowosc}")

            for term in search_terms:
                try:
                    url_term = term.replace(" ", "_")
                    url = f'https://pl.wikipedia.org/wiki/{url_term}'

                    print(f"Próbuję URL: {url}")

                    headers = {
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                    }

                    response = requests.get(url, timeout=10, headers=headers)

                    if response.status_code == 200:
                        soup = BeautifulSoup(response.text, 'html.parser')

                        coords = self._extract_coordinates_from_infobox(soup)
                        if coords:
                            print(f"Znaleziono współrzędne w infoboxie: {coords}")
                            return coords

                        coords = self._extract_coordinates_from_classes(soup)
                        if coords:
                            print(f"Znaleziono współrzędne w klasach: {coords}")
                            return coords

                        coords = self._extract_coordinates_from_geo(soup)
                        if coords:
                            print(f"Znaleziono współrzędne w geo: {coords}")
                            return coords

                except Exception as e:
                    print(f"Błąd przy pobieraniu {url}: {e}")
                    continue

            print(f"Nie znaleziono współrzędnych, używam domyślnych dla Warszawy")
            return [52.2297, 21.0122]

        except Exception as e:
            print(f"Ogólny błąd przy pobieraniu współrzędnych: {e}")
            return [52.2297, 21.0122]

    def _extract_coordinates_from_infobox(self, soup):
        try:
            infobox = soup.find('table', class_='infobox')
            if infobox:
                geohack_links = infobox.find_all('a', href=re.compile(r'geohack'))
                for link in geohack_links:
                    href = link.get('href', '')
                    match = re.search(r'params=([0-9.]+)_N_([0-9.]+)_E', href)
                    if match:
                        lat = float(match.group(1))
                        lon = float(match.group(2))
                        return [lat, lon]

                coord_text = infobox.get_text()
                coords = self._parse_coordinates_from_text(coord_text)
                if coords:
                    return coords

            return None
        except:
            return None

    def _extract_coordinates_from_classes(self, soup):
        try:
            longitude_elem = soup.select('.longitude')
            latitude_elem = soup.select('.latitude')

            if longitude_elem and latitude_elem:
                for i in range(min(len(longitude_elem), len(latitude_elem))):
                    try:
                        lon_text = longitude_elem[i].get_text().strip()
                        lat_text = latitude_elem[i].get_text().strip()

                        longitude = self._clean_coordinate(lon_text)
                        latitude = self._clean_coordinate(lat_text)

                        if longitude and latitude:
                            return [latitude, longitude]
                    except:
                        continue

            return None
        except:
            return None

    def _clean_coordinate(self, coord_text):
        try:
            cleaned = re.sub(r'[^\d.,°′″NSEW-]', '', coord_text)
            cleaned = cleaned.replace(',', '.')

            if '°' in cleaned or '′' in cleaned or '″' in cleaned:
                return self._convert_dms_to_decimal(coord_text)

            numbers = re.findall(r'\d+\.?\d*', cleaned)
            if numbers:
                return float(numbers[0])

            return None
        except:
            return None

    def _convert_dms_to_decimal(self, dms_text):
        try:
            patterns = [
                r'(\d+)°(\d+)′(\d+)″',
                r'(\d+)°(\d+)′',
                r'(\d+)°'
            ]

            for pattern in patterns:
                match = re.search(pattern, dms_text)
                if match:
                    degrees = float(match.group(1))
                    minutes = float(match.group(2)) if len(match.groups()) > 1 else 0
                    seconds = float(match.group(3)) if len(match.groups()) > 2 else 0

                    decimal = degrees + minutes / 60 + seconds / 3600

                    if 'S' in dms_text.upper() or 'W' in dms_text.upper():
                        decimal = -decimal

                    return decimal

            return None
        except:
            return None

    def _extract_coordinates_from_geo(self, soup):
        try:
            geo_elem = soup.find(class_='geo')
            if geo_elem:
                coord_text = geo_elem.get_text()
                coords = self._parse_coordinates_from_text(coord_text)
                return coords
            return None
        except:
            return None

    def _parse_coordinates_from_text(self, text):
        try:
            numbers = re.findall(r'\d+\.?\d*', text)
            if len(numbers) >= 2:
                lat = float(numbers[0])
                lon = float(numbers[1])

                if 49 <= lat <= 55 and 14 <= lon <= 25:
                    return [lat, lon]

            return None
        except:
            return None

    def to_dict(self):
        return {
            'nazwa': self.nazwa,
            'miejscowosc': self.miejscowosc,
            'typ_obiektu': self.typ_obiektu,
            'coordinates': self.coordinates
        }

    @classmethod
    def from_dict(cls, data):
        obj = cls(data['nazwa'], data['miejscowosc'], data['typ_obiektu'])
        obj.coordinates = data.get('coordinates', [52.23, 21.00])
        return obj

    def show_selected_objects_on_map(self):
        map_widget.delete_all_marker()

        for obj in obiekty_sakralne:
            if obj.coordinates[0] != 0 and obj.coordinates[1] != 0:
                obj.marker = map_widget.set_marker(obj.coordinates[0], obj.coordinates[1], text=obj.nazwa)

        if obiekty_sakralne:
            map_widget.set_position(obiekty_sakralne[0].coordinates[0], obiekty_sakralne[0].coordinates[1])
            map_widget.set_zoom(8)

class Duchowny:
    def __init__(self, imie, nazwisko, funkcja, obiekt_sakralny):
        self.imie = imie
        self.nazwisko = nazwisko
        self.funkcja = funkcja
        self.obiekt_sakralny = obiekt_sakralny

    def to_dict(self):
        return {
            'imie': self.imie,
            'nazwisko': self.nazwisko,
            'funkcja': self.funkcja,
            'obiekt_sakralny': self.obiekt_sakralny
        }

    @classmethod
    def from_dict(cls, data):
        return cls(data['imie'], data['nazwisko'], data['funkcja'], data['obiekt_sakralny'])

class Pracownik:
    def __init__(self, imie, nazwisko, stanowisko, obiekt_sakralny):
        self.imie = imie
        self.nazwisko = nazwisko
        self.stanowisko = stanowisko
        self.obiekt_sakralny = obiekt_sakralny

    def to_dict(self):
        return {
            'imie': self.imie,
            'nazwisko': self.nazwisko,
            'stanowisko': self.stanowisko,
            'obiekt_sakralny': self.obiekt_sakralny
        }

    @classmethod
    def from_dict(cls, data):
        return cls(data['imie'], data['nazwisko'], data['stanowisko'], data['obiekt_sakralny'])


def save_data_to_json():
    data = {
        'obiekty_sakralne': [obj.to_dict() for obj in obiekty_sakralne],
        'duchowni': [duch.to_dict() for duch in duchowni],
        'pracownicy': [prac.to_dict() for prac in pracownicy]
    }

    with open('sakralne_dane.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_data_from_json():
    global obiekty_sakralne, duchowni, pracownicy

    if os.path.exists('sakralne_dane.json'):
        try:
            with open('sakralne_dane.json', 'r', encoding='utf-8') as f:
                data = json.load(f)

            obiekty_sakralne = [ObiektSakralny.from_dict(obj) for obj in data.get('obiekty_sakralne', [])]
            duchowni = [Duchowny.from_dict(duch) for duch in data.get('duchowni', [])]
            pracownicy = [Pracownik.from_dict(prac) for prac in data.get('pracownicy', [])]

            # Odtwórz markery na mapie
            for obj in obiekty_sakralne:
                if obj.coordinates[0] != 0 and obj.coordinates[1] != 0:
                    obj.marker = map_widget.set_marker(obj.coordinates[0], obj.coordinates[1], text=obj.nazwa)

            show_obiekty_sakralne()
            show_duchowni()
            show_pracownikow()

        except Exception as e:
            messagebox.showerror("Błąd", f"Nie można załadować danych: {str(e)}")

def update_combo_boxes():
    obiekty_nazwy = [obj.nazwa for obj in obiekty_sakralne]
    combo_obiekt_duchowny['values'] = obiekty_nazwy
    combo_obiekt_pracownik['values'] = obiekty_nazwy

def add_obiekt_sakralny():
    nazwa = entry_nazwa_obiektu.get().strip()
    miejscowosc = entry_miejscowosc_obiektu.get().strip()
    typ_obiektu = combo_typ_obiektu.get().strip()

    if not nazwa or not miejscowosc or not typ_obiektu:
        messagebox.showwarning("Błąd", "Wypełnij wszystkie pola!")
        return

    obiekt = ObiektSakralny(nazwa, miejscowosc, typ_obiektu)
    obiekty_sakralne.append(obiekt)

    show_obiekty_sakralne()
    save_data_to_json()

    entry_nazwa_obiektu.delete(0, END)
    entry_miejscowosc_obiektu.delete(0, END)
    combo_typ_obiektu.set("")
    entry_nazwa_obiektu.focus()


def show_obiekty_sakralne():
    listbox_obiekty_sakralne.delete(0, END)
    for idx, obiekt in enumerate(obiekty_sakralne):
        listbox_obiekty_sakralne.insert(idx, f'{idx + 1}. {obiekt.nazwa} - {obiekt.miejscowosc} ({obiekt.typ_obiektu})')


def remove_obiekt_sakralny():
    try:
        i = listbox_obiekty_sakralne.index(ACTIVE)
        if obiekty_sakralne[i].marker:
            obiekty_sakralne[i].marker.delete()
        obiekty_sakralne.pop(i)
        show_obiekty_sakralne()
        save_data_to_json()
    except:
        messagebox.showwarning("Błąd", "Wybierz obiekt do usunięcia!")


def show_obiekt_details():
    try:
        i = listbox_obiekty_sakralne.index(ACTIVE)
        obiekt = obiekty_sakralne[i]

        label_nazwa_szczegoly_wartosc.config(text=obiekt.nazwa)
        label_miejscowosc_szczegoly_wartosc.config(text=obiekt.miejscowosc)
        label_typ_szczegoly_wartosc.config(text=obiekt.typ_obiektu)

        if obiekt.coordinates[0] != 0 and obiekt.coordinates[1] != 0:
            map_widget.set_zoom(12)
            map_widget.set_position(obiekt.coordinates[0], obiekt.coordinates[1])
        show_wszyscy_on_map()
    except:
        messagebox.showwarning("Błąd", "Wybierz obiekt do wyświetlenia!")


def edit_obiekt_sakralny():
    try:
        i = listbox_obiekty_sakralne.index(ACTIVE)
        obiekt = obiekty_sakralne[i]

        entry_nazwa_obiektu.delete(0, END)
        entry_nazwa_obiektu.insert(0, obiekt.nazwa)
        entry_miejscowosc_obiektu.delete(0, END)
        entry_miejscowosc_obiektu.insert(0, obiekt.miejscowosc)
        combo_typ_obiektu.set(obiekt.typ_obiektu)

        # Usuń marker z mapy
        if obiekt.marker:
            obiekt.marker.delete()

        obiekty_sakralne.pop(i)
        show_obiekty_sakralne()
        save_data_to_json()

    except:
        messagebox.showwarning("Błąd", "Wybierz obiekt do edycji!")


def show_obiekty_sakralne_on_map():
    map_widget.delete_all_marker()

    for obj in obiekty_sakralne:
        if obj.coordinates[0] != 0 and obj.coordinates[1] != 0:
            marker_text = f"{obj.nazwa},{obj.miejscowosc} ({obj.typ_obiektu})"
            obj.marker = map_widget.set_marker(obj.coordinates[0], obj.coordinates[1], text=marker_text)

    if obiekty_sakralne:
        map_widget.set_position(obiekty_sakralne[0].coordinates[0], obiekty_sakralne[0].coordinates[1])
        # map_widget.set_zoom(8)

def add_duchowny():
    imie = entry_imie_duchowny.get().strip()
    nazwisko = entry_nazwisko_duchowny.get().strip()
    funkcja = entry_funkcja_duchowny.get().strip()
    obiekt_idx = combo_obiekt_duchowny.current()

    if not imie or not nazwisko or not funkcja or obiekt_idx == -1:
        messagebox.showwarning("Błąd", "Wypełnij wszystkie pola!")
        return

    obiekt_nazwa = obiekty_sakralne[obiekt_idx].nazwa
    duchowny = Duchowny(imie, nazwisko, funkcja, obiekt_nazwa)
    duchowni.append(duchowny)

    show_duchowni()
    save_data_to_json()

    entry_imie_duchowny.delete(0, END)
    entry_nazwisko_duchowny.delete(0, END)
    entry_funkcja_duchowny.delete(0, END)
    combo_obiekt_duchowny.set("")
    entry_imie_duchowny.focus()


def show_duchowni():
    listbox_duchowni.delete(0, END)
    for idx, duchowny in enumerate(duchowni):
        listbox_duchowni.insert(idx,
                                f'{idx + 1}. {duchowny.imie} {duchowny.nazwisko} - {duchowny.funkcja} ({duchowny.obiekt_sakralny})')


def remove_duchowny():
    try:
        i = listbox_duchowni.index(ACTIVE)
        duchowni.pop(i)
        show_duchowni()
        save_data_to_json()
    except:
        messagebox.showwarning("Błąd", "Wybierz duchownego do usunięcia!")


def edit_duchowny():
    try:
        i = listbox_duchowni.index(ACTIVE)
        duchowny = duchowni[i]

        entry_imie_duchowny.delete(0, END)
        entry_imie_duchowny.insert(0, duchowny.imie)
        entry_nazwisko_duchowny.delete(0, END)
        entry_nazwisko_duchowny.insert(0, duchowny.nazwisko)
        entry_funkcja_duchowny.delete(0, END)
        entry_funkcja_duchowny.insert(0, duchowny.funkcja)

        for idx, obj in enumerate(obiekty_sakralne):
            if obj.nazwa == duchowny.obiekt_sakralny:
                combo_obiekt_duchowny.current(idx)
                break

        duchowni.pop(i)
        show_duchowni()
        save_data_to_json()

    except:
        messagebox.showwarning("Błąd", "Wybierz duchownego do edycji!")


def show_duchowni_on_map():
    map_widget.delete_all_marker()

    obiekty_z_duchownymi = set()
    for duchowny in duchowni:
        obiekty_z_duchownymi.add(duchowny.obiekt_sakralny)

    markers_added = False
    for obj in obiekty_sakralne:
        if obj.nazwa in obiekty_z_duchownymi and obj.coordinates[0] != 0 and obj.coordinates[1] != 0:
            duchowni_w_obiekcie = [d for d in duchowni if d.obiekt_sakralny == obj.nazwa]
            duchowni_tekst = ", \n".join([f"{d.imie} {d.nazwisko} ({d.funkcja})" for d in duchowni_w_obiekcie])

            marker_text = f"Duchowni: \n{duchowni_tekst}"
            obj.marker = map_widget.set_marker(obj.coordinates[0], obj.coordinates[1], text=marker_text)
            markers_added = True

    if markers_added and obiekty_sakralne:
        for obj in obiekty_sakralne:
            if obj.nazwa in obiekty_z_duchownymi:
                map_widget.set_position(obj.coordinates[0], obj.coordinates[1])
                #map_widget.set_zoom(8)
                break


def add_pracownik():
    imie = entry_imie_pracownik.get().strip()
    nazwisko = entry_nazwisko_pracownik.get().strip()
    stanowisko = entry_stanowisko_pracownik.get().strip()
    obiekt_idx = combo_obiekt_pracownik.current()

    if not imie or not nazwisko or not stanowisko or obiekt_idx == -1:
        messagebox.showwarning("Błąd", "Wypełnij wszystkie pola!")
        return

    obiekt_nazwa = obiekty_sakralne[obiekt_idx].nazwa
    pracownik = Pracownik(imie, nazwisko, stanowisko, obiekt_nazwa)
    pracownicy.append(pracownik)

    show_pracownikow()
    save_data_to_json()

    entry_imie_pracownik.delete(0, END)
    entry_nazwisko_pracownik.delete(0, END)
    entry_stanowisko_pracownik.delete(0, END)
    combo_obiekt_pracownik.set("")
    entry_imie_pracownik.focus()


def show_pracownikow():
    listbox_pracownicy.delete(0, END)
    for idx, pracownik in enumerate(pracownicy):
        listbox_pracownicy.insert(idx,
                                  f'{idx + 1}. {pracownik.imie} {pracownik.nazwisko} - {pracownik.stanowisko} ({pracownik.obiekt_sakralny})')


def remove_pracownik():
    try:
        i = listbox_pracownicy.index(ACTIVE)
        pracownicy.pop(i)
        show_pracownikow()
        save_data_to_json()
    except:
        messagebox.showwarning("Błąd", "Wybierz pracownika do usunięcia!")


def edit_pracownik():
    try:
        i = listbox_pracownicy.index(ACTIVE)
        pracownik = pracownicy[i]

        entry_imie_pracownik.delete(0, END)
        entry_imie_pracownik.insert(0, pracownik.imie)
        entry_nazwisko_pracownik.delete(0, END)
        entry_nazwisko_pracownik.insert(0, pracownik.nazwisko)
        entry_stanowisko_pracownik.delete(0, END)
        entry_stanowisko_pracownik.insert(0, pracownik.stanowisko)

        for idx, obj in enumerate(obiekty_sakralne):
            if obj.nazwa == pracownik.obiekt_sakralny:
                combo_obiekt_pracownik.current(idx)
                break

        pracownicy.pop(i)
        show_pracownikow()
        save_data_to_json()

    except:
        messagebox.showwarning("Błąd", "Wybierz pracownika do edycji!")

def show_pracownicy_on_map():
    map_widget.delete_all_marker()

    obiekty_z_pracownikami = set()
    for pracownik in pracownicy:
        obiekty_z_pracownikami.add(pracownik.obiekt_sakralny)

    markers_added = False
    for obj in obiekty_sakralne:
        if obj.nazwa in obiekty_z_pracownikami and obj.coordinates[0] != 0 and obj.coordinates[1] != 0:
            # Znajdź pracowników pracujących w tym obiekcie
            pracownicy_w_obiekcie = [p for p in pracownicy if p.obiekt_sakralny == obj.nazwa]
            pracownicy_tekst = ", \n".join([f"{p.imie} {p.nazwisko} ({p.stanowisko})" for p in pracownicy_w_obiekcie])

            marker_text = f"Pracownicy:\n{pracownicy_tekst}"
            obj.marker = map_widget.set_marker(obj.coordinates[0], obj.coordinates[1], text=marker_text)
            markers_added = True

    if markers_added and obiekty_sakralne:
        # Znajdź pierwszy obiekt z pracownikami i wycentruj mapę
        for obj in obiekty_sakralne:
            if obj.nazwa in obiekty_z_pracownikami:
                map_widget.set_position(obj.coordinates[0], obj.coordinates[1])
                #map_widget.set_zoom(8)
                break

def show_wszyscy_on_map():
    map_widget.delete_all_marker()

    for obj in obiekty_sakralne:
        if obj.coordinates[0] != 0 and obj.coordinates[1] != 0:
            duchowni_w_obiekcie = [d for d in duchowni if d.obiekt_sakralny == obj.nazwa]
            pracownicy_w_obiekcie = [p for p in pracownicy if p.obiekt_sakralny == obj.nazwa]

            marker_text = obj.nazwa
            if duchowni_w_obiekcie:
                duchowni_tekst = ", ".join([f"{d.imie} {d.nazwisko}" for d in duchowni_w_obiekcie])
                marker_text += f"\nDuchowni: \n{duchowni_tekst}"
            if pracownicy_w_obiekcie:
                pracownicy_tekst = ", ".join([f"{p.imie} {p.nazwisko}" for p in pracownicy_w_obiekcie])
                marker_text += f"\nPracownicy: \n{pracownicy_tekst}"

            obj.marker = map_widget.set_marker(obj.coordinates[0], obj.coordinates[1], text=marker_text)

    if obiekty_sakralne:
        map_widget.set_position(obiekty_sakralne[0].coordinates[0], obiekty_sakralne[0].coordinates[1])
        map_widget.set_zoom(8)


root = Tk()
root.title('System zarządzania obiektami sakralnymi')
root.geometry('1400x800')
main_frame = Frame(root)
main_frame.pack(fill='both', expand=True, padx=10, pady=10)

# Lewa strona - notebook z zakładkami
left_frame = Frame(main_frame)
left_frame.pack(side='left', fill='both', expand=True)

# Prawa strona - mapa
right_frame = Frame(main_frame)
right_frame.pack(side='right', fill='both', expand=True, padx=(10, 0))

# Tworzenie mapy w prawej ramce
map_widget = tkintermapview.TkinterMapView(right_frame, width=700, height=750)
map_widget.pack(fill='both', expand=True)
map_widget.set_position(52.23, 21.00)
map_widget.set_zoom(6)

notebook = ttk.Notebook(left_frame)
notebook.pack(fill='both', expand=True, padx=10, pady=10)

frame_obiekty = ttk.Frame(notebook)
notebook.add(frame_obiekty, text='Obiekty sakralne')

ramka_lista_obiektow = Frame(frame_obiekty)
ramka_formularz_obiektow = Frame(frame_obiekty)
ramka_szczegoly_obiektow = Frame(frame_obiekty)

# Ujednolicony szablon dla obiektów sakralnych
ramka_lista_obiektow.grid(row=0, column=0, padx=10, pady=5, sticky='nsew')
ramka_formularz_obiektow.grid(row=0, column=1, padx=10, pady=5, sticky='nsew')
ramka_szczegoly_obiektow.grid(row=1, column=0, columnspan=2, padx=10, pady=5, sticky='ew')

# Konfiguracja grid
frame_obiekty.grid_columnconfigure(0, weight=1)
frame_obiekty.grid_columnconfigure(1, weight=1)

Label(ramka_lista_obiektow, text='Lista obiektów sakralnych', font=('Arial', 12, 'bold')).grid(row=0, column=0,
                                                                                               columnspan=3, pady=5)

listbox_obiekty_sakralne = Listbox(ramka_lista_obiektow, width=40, height=12)
listbox_obiekty_sakralne.grid(row=1, column=0, columnspan=3, pady=5)

Button(ramka_lista_obiektow, text='Usuń obiekt', command=remove_obiekt_sakralny).grid(row=2, column=0, padx=2, pady=2)
Button(ramka_lista_obiektow, text='Edytuj obiekt', command=edit_obiekt_sakralny).grid(row=2, column=1, padx=2, pady=2)
Button(ramka_lista_obiektow, text='Pokaż szczegóły', command=show_obiekt_details).grid(row=2, column=2, padx=2, pady=2)
Button(ramka_lista_obiektow, text='Pokaż mapę obiektów', command=show_obiekty_sakralne_on_map).grid(row=3, column=0,
                                                                                                    columnspan=3,
                                                                                                    padx=2, pady=2)

Label(ramka_formularz_obiektow, text='Dodaj obiekt sakralny', font=('Arial', 12, 'bold')).grid(row=0, column=0,
                                                                                               columnspan=2, pady=5)

Label(ramka_formularz_obiektow, text='Nazwa obiektu:').grid(row=1, column=0, sticky=W, pady=2)
entry_nazwa_obiektu = Entry(ramka_formularz_obiektow, width=25)
entry_nazwa_obiektu.grid(row=1, column=1, pady=2)

Label(ramka_formularz_obiektow, text='Miejscowość:').grid(row=2, column=0, sticky=W, pady=2)
entry_miejscowosc_obiektu = Entry(ramka_formularz_obiektow, width=25)
entry_miejscowosc_obiektu.grid(row=2, column=1, pady=2)

Label(ramka_formularz_obiektow, text='Typ obiektu:').grid(row=3, column=0, sticky=W, pady=2)
combo_typ_obiektu = ttk.Combobox(ramka_formularz_obiektow, width=22,
                                 values=['Kościół', 'Cmentarz', 'Kaplica', 'Bazylika', 'Katedra', 'Klasztor',
                                         'Synagoga', 'Meczet'])
combo_typ_obiektu.grid(row=3, column=1, pady=2)

Button(ramka_formularz_obiektow, text='Dodaj obiekt', command=add_obiekt_sakralny).grid(row=4, column=0, columnspan=2,
                                                                                        pady=10)

Label(ramka_szczegoly_obiektow, text='Szczegóły obiektu sakralnego:', font=('Arial', 12, 'bold')).grid(row=0, column=0,
                                                                                                       columnspan=6,
                                                                                                       pady=5)

Label(ramka_szczegoly_obiektow, text='Nazwa:').grid(row=1, column=0, sticky=W, padx=5)
label_nazwa_szczegoly_wartosc = Label(ramka_szczegoly_obiektow, text='-----', relief='sunken', width=15)
label_nazwa_szczegoly_wartosc.grid(row=1, column=1, padx=5)

Label(ramka_szczegoly_obiektow, text='Miejscowość:').grid(row=1, column=2, sticky=W, padx=5)
label_miejscowosc_szczegoly_wartosc = Label(ramka_szczegoly_obiektow, text='-----', relief='sunken', width=15)
label_miejscowosc_szczegoly_wartosc.grid(row=1, column=3, padx=5)

Label(ramka_szczegoly_obiektow, text='Typ:').grid(row=1, column=4, sticky=W, padx=5)
label_typ_szczegoly_wartosc = Label(ramka_szczegoly_obiektow, text='-----', relief='sunken', width=15)
label_typ_szczegoly_wartosc.grid(row=1, column=5, padx=5)

frame_duchowni = ttk.Frame(notebook)
notebook.add(frame_duchowni, text='Duchowni')

# Ujednolicony szablon dla duchownych
ramka_lista_duchownych = Frame(frame_duchowni)
ramka_formularz_duchownych = Frame(frame_duchowni)

ramka_lista_duchownych.grid(row=0, column=0, padx=10, pady=5, sticky='nsew')
ramka_formularz_duchownych.grid(row=0, column=1, padx=10, pady=5, sticky='nsew')

# Konfiguracja grid
frame_duchowni.grid_columnconfigure(0, weight=1)
frame_duchowni.grid_columnconfigure(1, weight=1)

Label(ramka_lista_duchownych, text='Lista duchownych', font=('Arial', 12, 'bold')).grid(row=0, column=0, columnspan=3, pady=5)

listbox_duchowni = Listbox(ramka_lista_duchownych, width=40, height=12)
listbox_duchowni.grid(row=1, column=0, columnspan=3, pady=5)

Button(ramka_lista_duchownych, text='Usuń duchownego', command=remove_duchowny).grid(row=2, column=0, padx=2, pady=2)
Button(ramka_lista_duchownych, text='Edytuj duchownego', command=edit_duchowny).grid(row=2, column=1, padx=2, pady=2)
Button(ramka_lista_duchownych, text='Pokaż mapę duchownych', command=show_duchowni_on_map).grid(row=3, column=0, columnspan=3, padx=2, pady=2)

Label(ramka_formularz_duchownych, text='Dodaj duchownego', font=('Arial', 12, 'bold')).grid(row=0, column=0, columnspan=2, pady=5)

Label(ramka_formularz_duchownych, text='Imię:').grid(row=1, column=0, sticky=W, pady=2)
entry_imie_duchowny = Entry(ramka_formularz_duchownych, width=25)
entry_imie_duchowny.grid(row=1, column=1, pady=2)

Label(ramka_formularz_duchownych, text='Nazwisko:').grid(row=2, column=0, sticky=W, pady=2)
entry_nazwisko_duchowny = Entry(ramka_formularz_duchownych, width=25)
entry_nazwisko_duchowny.grid(row=2, column=1, pady=2)

Label(ramka_formularz_duchownych, text='Funkcja:').grid(row=3, column=0, sticky=W, pady=2)
entry_funkcja_duchowny = Entry(ramka_formularz_duchownych, width=25)
entry_funkcja_duchowny.grid(row=3, column=1, pady=2)

Label(ramka_formularz_duchownych, text='Obiekt sakralny:').grid(row=4, column=0, sticky=W, pady=2)
combo_obiekt_duchowny = ttk.Combobox(ramka_formularz_duchownych, width=22, state='readonly')
combo_obiekt_duchowny.grid(row=4, column=1, pady=2)

Button(ramka_formularz_duchownych, text='Dodaj duchownego', command=add_duchowny).grid(row=5, column=0, columnspan=2, pady=10)
frame_pracownicy = ttk.Frame(notebook)
notebook.add(frame_pracownicy, text='Pracownicy')

# Ujednolicony szablon dla pracowników
ramka_lista_pracownikow = Frame(frame_pracownicy)
ramka_formularz_pracownikow = Frame(frame_pracownicy)

ramka_lista_pracownikow.grid(row=0, column=0, padx=10, pady=5, sticky='nsew')
ramka_formularz_pracownikow.grid(row=0, column=1, padx=10, pady=5, sticky='nsew')

# Konfiguracja grid
frame_pracownicy.grid_columnconfigure(0, weight=1)
frame_pracownicy.grid_columnconfigure(1, weight=1)

Label(ramka_lista_pracownikow, text='Lista pracowników', font=('Arial', 12, 'bold')).grid(row=0, column=0, columnspan=3, pady=5)

listbox_pracownicy = Listbox(ramka_lista_pracownikow, width=40, height=12)
listbox_pracownicy.grid(row=1, column=0, columnspan=3, pady=5)

Button(ramka_lista_pracownikow, text='Usuń pracownika', command=remove_pracownik).grid(row=2, column=0, padx=2, pady=2)
Button(ramka_lista_pracownikow, text='Edytuj pracownika', command=edit_pracownik).grid(row=2, column=1, padx=2, pady=2)
Button(ramka_lista_pracownikow, text='Pokaż mapę pracowników', command=show_pracownicy_on_map).grid(row=3, column=0, columnspan=3, padx=2, pady=2)

Label(ramka_formularz_pracownikow, text='Dodaj pracownika', font=('Arial', 12, 'bold')).grid(row=0, column=0, columnspan=2, pady=5)

Label(ramka_formularz_pracownikow, text='Imię:').grid(row=1, column=0, sticky=W, pady=2)
entry_imie_pracownik = Entry(ramka_formularz_pracownikow, width=25)
entry_imie_pracownik.grid(row=1, column=1, pady=2)

Label(ramka_formularz_pracownikow, text='Nazwisko:').grid(row=2, column=0, sticky=W, pady=2)
entry_nazwisko_pracownik = Entry(ramka_formularz_pracownikow, width=25)
entry_nazwisko_pracownik.grid(row=2, column=1, pady=2)

Label(ramka_formularz_pracownikow, text='Stanowisko:').grid(row=3, column=0, sticky=W, pady=2)
entry_stanowisko_pracownik = Entry(ramka_formularz_pracownikow, width=25)
entry_stanowisko_pracownik.grid(row=3, column=1, pady=2)

Label(ramka_formularz_pracownikow, text='Obiekt sakralny:').grid(row=4, column=0, sticky=W, pady=2)
combo_obiekt_pracownik = ttk.Combobox(ramka_formularz_pracownikow, width=22, state='readonly')
combo_obiekt_pracownik.grid(row=4, column=1, pady=2)

Button(ramka_formularz_pracownikow, text='Dodaj pracownika', command=add_pracownik).grid(row=5, column=0, columnspan=2, pady=10)

def on_tab_changed(event):
    update_combo_boxes()


load_data_from_json()
update_combo_boxes()

root.mainloop()