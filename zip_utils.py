import os
import zipfile
import xml.etree.ElementTree as ET
from PyPDF2 import PdfReader
import re

def extract_zip(file_path, extract_dir):
    """
    Извлекает ZIP архив в указанную директорию.
    Возвращает список извлеченных файлов.
    """
    try:
        # Создаем директорию для извлеченных файлов
        os.makedirs(extract_dir, exist_ok=True)

        # Открываем ZIP архив
        with zipfile.ZipFile(file_path, "r") as zf:
            # Проверяем, что архив не поврежден
            if zf.testzip() is None:
                print("ZIP архив не поврежден.")
            else:
                raise ValueError("ZIP архив поврежден.")

            # Извлекаем все файлы
            zf.extractall(path=extract_dir)
            print(f"Файлы извлечены в директорию: {extract_dir}")

            # Получаем список файлов
            files = os.listdir(extract_dir)
            return files
    except zipfile.BadZipFile:
        raise ValueError("ZIP архив поврежден или имеет неподдерживаемый формат.")
    except Exception as e:
        raise Exception(f"Ошибка при извлечении ZIP архива: {e}")

def clear_temp_files(file_path, extract_dir):
    """
    Удаляет временные файлы (архив и извлеченные файлы).
    """
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
        if os.path.exists(extract_dir):
            for root, dirs, files in os.walk(extract_dir, topdown=False):
                for name in files:
                    os.remove(os.path.join(root, name))
                for name in dirs:
                    os.rmdir(os.path.join(root, name))
            os.rmdir(extract_dir)
        print("Временные файлы удалены.")
    except Exception as e:
        raise Exception(f"Ошибка при удалении временных файлов: {e}")

def count_folders_with_name(extract_dir, keyword):
    """
    Считает количество папок, в названии которых содержится ключевое слово.
    """
    count = 0
    try:
        # Рекурсивно обходим директорию
        for root, dirs, files in os.walk(extract_dir):
            for dir_name in dirs:
                # Проверяем, содержит ли название папки ключевое слово
                if keyword.lower() in dir_name.lower():
                    count += 1
        return count
    except Exception as e:
        raise Exception(f"Ошибка при поиске папок: {e}")


def parse_xml(file_path):
    """
    Парсит XML файл и возвращает его содержимое в виде словаря.
    """
    try:
        tree = ET.parse(file_path)
        root = tree.getroot()
        data = {}
        for child in root:
            data[child.tag] = child.text
        return data
    except Exception as e:
        raise Exception(f"Ошибка при парсинге XML файла {file_path}: {e}")

def parse_pdf(file_path):
    """
    Извлекает текст из PDF файла и возвращает его.
    """
    try:
        reader = PdfReader(file_path)
        text = ""
        for page in reader.pages:
            text += page.extract_text()
        return text
    except Exception as e:
        raise Exception(f"Ошибка при извлечении текста из PDF файла {file_path}: {e}")

def process_folder(folder_path):
    """
    Обрабатывает папку, находит файлы с "ЕГРЮЛ" в названии и извлекает ИНН.
    Возвращает словарь с результатами.
    """
    result = {"folder_name": os.path.basename(folder_path), "inn_list": set()}  # Используем set для хранения уникальных ИНН
    try:
        for root, dirs, files in os.walk(folder_path):
            for file in files:
                # Проверяем, содержит ли имя файла "ЕГРЮЛ" и является ли он PDF или XML
                if ("ЕГРЮЛ" in file) or ("Выписка" in file) and (file.endswith(".pdf") or file.endswith(".xml")):
                    file_path = os.path.join(root, file)
                    if file.endswith(".xml"):
                        with open(file_path, "r", encoding="utf-8") as f:
                            data = f.read()  # Читаем XML как текст
                    elif file.endswith(".pdf"):
                        reader = PdfReader(file_path)
                        data = ""
                        for page in reader.pages:
                            data += page.extract_text()

                    # Извлекаем ИНН из данных
                    inns = extract_inn_from_data(data)
                    if inns:
                        result["inn_list"].update(inns)  # Добавляем ИНН в множество

        # Преобразуем множество обратно в список для удобства
        result["inn_list"] = list(result["inn_list"])
        return result
    except Exception as e:
        raise Exception(f"Ошибка при обработке папки {folder_path}: {e}")

def extract_inn_from_data(data):
    """
    Извлекает ИНН из данных (XML или текста PDF) с помощью регулярных выражений.
    ИНН может быть 10-значным (для юрлиц) или 12-значным (для физлиц).
    Ищет ИНН в формате "ИНН<цифры>" или "ИНН:<цифры>".
    """
    # Регулярное выражение для поиска ИНН
    inn_pattern = re.compile(
        r'\(?ИНН\)?:?\s*(\d{10}|\d{12})\b'  # Ищет "ИНН" или "ИНН:", затем 10 или 12 цифр
    )
    # Находим все совпадения и извлекаем только цифры
    inns = inn_pattern.findall(data)
    return inns