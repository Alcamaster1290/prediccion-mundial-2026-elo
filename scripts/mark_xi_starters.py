#!/usr/bin/env python3
"""Mark sourced XI starters for AlterFutbol squad-only teams."""

import argparse
import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


STARTERS_BY_TEAM = {
    "mex": [
        "Raúl Rangel",
        "César Montes",
        "Johan Vásquez",
        "Jorge Sánchez",
        "Jesús Gallardo",
        "Érik Lira",
        "Álvaro Fidalgo",
        "Brian Gutiérrez",
        "Roberto Alvarado",
        "Julián Quiñones",
        "Raúl Jiménez",
    ],
    "zaf": [
        "Ronwen Williams",
        "Ime Okon",
        "Mbekezeli Mbokazi",
        "Khuliso Mudau",
        "Aubrey Modiba",
        "Teboho Mokoena",
        "Sphephelo Sithole",
        "Relebohile Mofokeng",
        "Tshepang Moremi",
        "Oswin Appollis",
        "Lyle Foster",
    ],
    "cze": [
        "Matěj Kovář",
        "Robin Hranáč",
        "Ladislav Krejčí",
        "Štěpán Chaloupek",
        "Vladimír Coufal",
        "David Jurásek",
        "Tomáš Souček",
        "Vladimír Darida",
        "Pavel Šulc",
        "Patrik Schick",
        "Lukáš Provod",
    ],
    "can": [
        "Dayne St. Clair",
        "Moïse Bombito",
        "Derek Cornelius",
        "Alistair Johnston",
        "Alphonso Davies",
        "Ismaël Koné",
        "Stephen Eustáquio",
        "Tajon Buchanan",
        "Liam Millar",
        "Jonathan David",
        "Cyle Larin",
    ],
    "qat": [
        "Meshaal Barsham",
        "Boualem Khoukhi",
        "Lucas Mendes",
        "Ayoub Al-Oui",
        "Homam Ahmed Al-Amin",
        "Ahmed Fathi",
        "Jassem Gaber",
        "Mohamed Al-Mannai",
        "Edmílson Júnior",
        "Akram Afif",
        "Almoez Ali",
    ],
    "mar": [
        "Yassine Bono",
        "Issa Diop",
        "Nayef Aguerd",
        "Achraf Hakimi",
        "Noussair Mazraoui",
        "Neil El Aynaoui",
        "Samir El Mourabet",
        "Bilal El Khannouss",
        "Brahim Díaz",
        "Abde Ezzalzouli",
        "Ayoub El Kaabi",
    ],
    "pry": [
        "Roberto Fernández",
        "Gustavo Gómez",
        "Omar Alderete",
        "Juan José Cáceres",
        "Junior Alonso",
        "Andrés Cubas",
        "Diego Gómez",
        "Ramón Sosa",
        "Miguel Almirón",
        "Julio Enciso",
        "Antonio Sanabria",
    ],
    # The local Australia XI image carries Czech player names; this XI is resolved from
    # the article's position-by-position analysis instead of that invalid image.
    "aus": [
        "Matthew Ryan",
        "Harry Souttar",
        "Alessandro Circati",
        "Cameron Burgess",
        "Jordan Bos",
        "Jacob Italiano",
        "Aiden O’Neill",
        "Jackson Irvine",
        "Connor Metcalfe",
        "Nestory Irankunda",
        "Mohamed Touré",
    ],
    "tur": [
        "Uğurcan Çakır",
        "Merih Demiral",
        "Abdülkerim Bardakcı",
        "Zeki Çelik",
        "Ferdi Kadıoğlu",
        "Hakan Çalhanoğlu",
        "İsmail Yüksek",
        "Orkun Kökçü",
        "Arda Güler",
        "Kenan Yıldız",
        "Kerem Aktürkoğlu",
    ],
    "ecu": [
        "Hernán Galíndez",
        "Joel Ordóñez",
        "Willian Pacho",
        "Alan Franco",
        "Piero Hincapié",
        "Moisés Caicedo",
        "Pedro Vite",
        "John Yeboah",
        "Nilson Angulo",
        "Gonzalo Plata",
        "Énner Valencia",
    ],
    "ned": [
        "Bart Verbruggen",
        "Virgil van Dijk",
        "Jan Paul van Hecke",
        "Denzel Dumfries",
        "Nathan Aké",
        "Ryan Gravenberch",
        "Frenkie de Jong",
        "Tijjani Reijnders",
        "Donyell Malen",
        "Cody Gakpo",
        "Memphis Depay",
    ],
    "egy": [
        "Mostafa Oufa Shobeir",
        "Yasser Ibrahim",
        "Mohamed Abdelmonem",
        "Mohamed Hany",
        "Karim Hafez",
        "Marwan Ateya",
        "Mohanad Lasheen",
        "Emam Ashour",
        "Mohamed Salah",
        "Mahmoud “Trezeguet” Hassan",
        "Omar Marmoush",
    ],
    "irn": [
        "Alireza Beiranvand",
        "Hossein Kanaani",
        "Ali Nemati",
        "Arya Yousefi",
        "Ehsan Hajsafi",
        "Saeed Ezatolahi",
        "Mohammad Ghorbani",
        "Saman Ghoddos",
        "Mohammad Mohebi",
        "Mehdi Ghayedi",
        "Mehdi Taremi",
    ],
    "ury": [
        "Sergio Rochet",
        "Ronald Araújo",
        "José María Giménez",
        "Guillermo Varela",
        "Mathías Olivera",
        "Manuel Ugarte",
        "Federico Valverde",
        "Rodrigo Bentancur",
        "Agustín Canobbio",
        "Maximiliano Araujo",
        "Darwin Núñez",
    ],
    "sen": [
        "Édouard Mendy",
        "Kalidou Koulibaly",
        "Moussa Niakhaté",
        "Krépin Diatta",
        "El Hadji Malick Diouf",
        "Idrissa Gueye",
        "Pape Gueye",
        "Habib Diarra",
        "Iliman Ndiaye",
        "Sadio Mané",
        "Nicolas Jackson",
    ],
    "irq": [
        "Jalal Hassan",
        "Zaid Tahseen",
        "Akam Hashem",
        "Hussein Ali",
        "Merchas Doski",
        "Amir Al-Ammari",
        "Aimar Sher",
        "Youssef Amyn",
        "Ali Jasim",
        "Ali Al-Hammadi",
        "Aymen Hussein",
    ],
    "arg": [
        "Emiliano Martínez",
        "Cristian Romero",
        "Lisandro Martínez",
        "Nahuel Molina",
        "Nicolás Tagliafico",
        "Enzo Fernández",
        "Rodrigo De Paul",
        "Alexis Mac Allister",
        "Lionel Messi",
        "Thiago Almada",
        "Julián Álvarez",
    ],
    "alg": [
        "Luca Zidane",
        "Aïssa Mandi",
        "Ramy Bensebaïni",
        "Rafik Belghali",
        "Rayan Aït-Nouri",
        "Nabil Bentaleb",
        "Hicham Boudaoui",
        "Farès Chaïbi",
        "Riyad Mahrez",
        "Ibrahim Maza",
        "Mohamed Amoura",
    ],
    "uzb": [
        "Abduvokhid Nematov",
        "Abdulla Abdullaev",
        "Rustam Ashurmatov",
        "Abdukodir Khusanov",
        "Khozhiakbar Alizhonov",
        "Sherzod Nasrullaev",
        "Otabek Shukurov",
        "Odildzhon Khamrobekov",
        "Azizjon Ganiev",
        "Oston Urunov",
        "Eldor Shomurodov",
    ],
    "cro": [
        "Dominik Livaković",
        "Josip Šutalo",
        "Duje Ćaleta-Car",
        "Joško Gvardiol",
        "Josip Stanišić",
        "Luka Sučić",
        "Mateo Kovačić",
        "Luka Modrić",
        "Andrej Kramarić",
        "Martin Baturina",
        "Ante Budimir",
    ],
    "gha": [
        "Lawrence Ati-Zigi",
        "Jonas Adjetey",
        "Jerome Opoku",
        "Marvin Senaya",
        "Gideon Mensah",
        "Thomas Partey",
        "Elisha Owusu",
        "Antoine Semenyo",
        "Abdul Fatawu",
        "Kamaldeen Sulemana",
        "Jordan Ayew",
    ],
    "pan": [
        "Orlando Mosquera",
        "José Córdoba",
        "Fidel Escobar",
        "Andrés Andrade",
        "Amir Murillo",
        "Jorge Gutiérrez",
        "Aníbal Godoy",
        "Adalberto Carrasquilla",
        "José Luis Rodríguez",
        "Ismael Díaz",
        "José Fajardo",
    ],
}


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_json(path, data):
    Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def apply_starters(teams_data, starters_by_team=STARTERS_BY_TEAM):
    teams_by_id = {team["id"]: team for team in teams_data.get("teams", [])}
    report = {}

    for code, starter_names in starters_by_team.items():
        if len(starter_names) != 11:
            raise ValueError(f"{code} has {len(starter_names)} configured starters, expected 11")
        if len(set(starter_names)) != 11:
            raise ValueError(f"{code} has duplicate configured starters")

        team = teams_by_id.get(code)
        if team is None:
            raise ValueError(f"{code} team not found")

        players = team.get("players") or []
        players_by_name = {player["name"]: player for player in players}
        missing = [name for name in starter_names if name not in players_by_name]
        if missing:
            raise ValueError(f"{code} missing starters: {missing}")

        starter_set = set(starter_names)
        for player in players:
            player["titular"] = player["name"] in starter_set

        starter_count = sum(1 for player in players if player.get("titular") is True)
        if starter_count != 11:
            raise ValueError(f"{code} marked {starter_count} starters, expected 11")
        report[code] = starter_count

    return report


def main():
    parser = argparse.ArgumentParser(description="Mark sourced XI starters in data/teams.json")
    parser.add_argument("--teams", default=str(REPO_ROOT / "data" / "teams.json"))
    args = parser.parse_args()

    teams_path = Path(args.teams)
    teams_data = load_json(teams_path)
    report = apply_starters(teams_data)
    write_json(teams_path, teams_data)
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
