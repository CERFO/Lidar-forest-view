import csv
import json
import os


def readCSV(filename, delimiter=',', header=True):
    """Lit un fichier CSV et retourne l'en-tête (si demandé) et les lignes."""
    rows = []
    with open(filename, 'r', encoding='utf-8') as file:
        csvreader = csv.reader(file, delimiter=delimiter)
        if header:
            header_row = next(csvreader)
        for row in csvreader:
            rows.append(row)
    if header:
        return header_row, rows
    else:
        return rows


def CSV_to_dict(filename, delimiter=','):
    """Lit un fichier CSV et retourne une liste de dictionnaires (une par ligne)."""
    data = []
    with open(filename, 'r', encoding='utf-8') as file:
        reader = csv.DictReader(file, delimiter=delimiter)
        for row in reader:
            data.append(dict(row))
    return data


def writeCSV(filename, data, header=None, delimiter=','):
    """
    Exporte des données vers un fichier CSV.

    Args:
        filename (str): Nom du fichier CSV à créer
        data (list): Liste de listes contenant les données
        header (list, optional): Entête des colonnes
        delimiter (str): Séparateur (par défaut: virgule)
    """
    with open(filename, 'w', newline='', encoding='utf-8') as file:
        csvwriter = csv.writer(file, delimiter=delimiter)
        if header:
            csvwriter.writerow(header)
        csvwriter.writerows(data)
    print(f"Données exportées vers {filename}")


def export_photo_info_to_csv(photo_info, filename):
    """
    Exporte les informations des photos vers un fichier CSV.

    Args:
        photo_info (list): Liste des informations des photos
        filename (str): Nom (path complet) du fichier CSV de sortie
    """
    if isinstance(photo_info[0][0], list):
        header = ['image_avant', 'image_arrière', 'timestamp', 'x', 'y', 'z', 'roll', 'pitch', 'yaw']
    else:
        header = ['image', 'timestamp', 'x', 'y', 'z', 'roll', 'pitch', 'yaw']

    csv_data = []
    for info in photo_info:
        if isinstance(info[0], list):
            row = [
                info[0][0], info[0][1], info[1], info[2], info[3], info[4],
                info[5], info[6], info[7]
            ]
        else:
            row = [
                info[0], info[1], info[2], info[3], info[4],
                info[5], info[6], info[7]
            ]
        csv_data.append(row)
    writeCSV(filename, csv_data, header)


def readJSON(filename):
    """Lit un fichier JSON et retourne les données."""
    with open(filename, 'r', encoding='utf-8') as file:
        data = json.load(file)
    return data


def writeJSON(filename, data):
    """
    Exporte des données vers un fichier JSON.

    Args:
        filename (str): Nom du fichier JSON à créer
        data (dict): Dictionnaire contenant les données à exporter
    """
    with open(filename, 'w', encoding='utf-8') as file:
        json.dump(data, file, indent=4, ensure_ascii=False)
    print(f"Données exportées vers {filename}")
