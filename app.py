import streamlit as st
import os
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from zip_utils import extract_zip, clear_temp_files, process_folder

base_cols = ['Название закупки', 'Примечание (Извещение)', 'Дата заключения контракта', 'Номер контракта', 
             'Сумма экономии', 'Закон', 'Ответственное лицо', 'ИНН', 'Сумма контракта']

# Заголовок страницы
st.title("Работа с ZIP архивами и поиск по ИНН")

# Диалоговое окно для загрузки архива
uploaded_file = st.file_uploader("Загрузите ZIP архив", type=["zip"])

# Инициализация переменных
file_path = "uploaded_archive.zip"
extract_dir = "extracted_files"

# Путь к таблице в директории db
db_path = "db/ДАННЫЕ ДИПЛОМ БОЛЬШИЕ.xlsx"

if uploaded_file is not None:
    # Сохраняем загруженный файл
    with open(file_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    st.success(f"Архив успешно загружен: {uploaded_file.name}")

    # Кнопка для разархивирования
    if st.button("Разархивировать и обработать"):
        try:
            # Извлекаем ZIP архив
            files = extract_zip(file_path, extract_dir)
            if files:
                st.write("Список файлов в архиве:")
                for file in files:
                    st.write(file)

                # Поиск папок с "Заявка" в названии
                keyword = "Заявка"
                folder_count = 0
                all_inns = set()

                for root, dirs, files in os.walk(extract_dir):
                    for dir_name in dirs:
                        if keyword.lower() in dir_name.lower():
                            folder_count += 1
                            folder_path = os.path.join(root, dir_name)
                            st.write(f"Обработка папки: {folder_path}")

                            result = process_folder(folder_path)
                            if result["inn_list"]:
                                st.write(f"Результаты для папки {dir_name}:")
                                st.write(f"Найденные ИНН: {result['inn_list']}")
                                all_inns.update(result["inn_list"])
                            else:
                                st.warning(f"В папке {dir_name} не найдено ИНН.")

                st.success(f"Количество папок с '{keyword}' в названии: {folder_count}")

                if os.path.exists(db_path):
                    df = pd.read_excel(db_path, usecols=base_cols, dtype={"ИНН": str})
                    
                    # Преобразование даты
                    df['Дата заключения контракта'] = pd.to_datetime(
                        df['Дата заключения контракта'],
                        dayfirst=True,
                        format='%d.%m.%Y',
                        errors='coerce'
                    )
                    
                    df['Год'] = df['Дата заключения контракта'].dt.year
                    df['Месяц'] = df['Дата заключения контракта'].dt.month
                    df['Квартал'] = df['Дата заключения контракта'].dt.quarter
                    
                    st.write("Исходная таблица из директории db:")
                    st.dataframe(df)

                    if all_inns:
                        filtered_df = df[df["ИНН"].astype(str).isin(all_inns)]
                        
                        # Преобразование суммы с учетом запятых как десятичных разделителей
                        for col in ['Сумма экономии', 'Сумма контракта']:
                            filtered_df[col] = (
                                filtered_df[col]
                                .astype(str)
                                .str.replace(',', '.')
                                .replace(' ', '')
                                .replace('[^\d.]', '', regex=True)
                                .pipe(pd.to_numeric, errors='coerce')
                            )
                        
                        st.write("Отфильтрованные строки по найденным ИНН:")
                        st.dataframe(filtered_df)
                        
                        # Раздел с графиками
                        st.header("📊 Визуализация данных")
                        
                        # Создаем две колонки для компактного отображения
                                      
                            # 1. Круговая диаграмма распределения по законам
                        st.subheader("Распределение по законам")
                        if not filtered_df['Закон'].empty:
                            law_counts = filtered_df['Закон'].value_counts()
                            fig, ax = plt.subplots(figsize=(4, 4))
                            ax.pie(law_counts, labels=law_counts.index, autopct='%1.1f%%')
                            st.pyplot(fig)
                        else:
                            st.warning("Нет данных о законах")
                        
                       
                            # 2. Топ ответственных лиц по количеству контрактов
                        st.subheader("Топ ответственных лиц")
                        if not filtered_df['Ответственное лицо'].empty:
                            responsible_counts = filtered_df['Ответственное лицо'].value_counts().head(10)
                            fig, ax = plt.subplots(figsize=(10, 6))
                            responsible_counts.plot(kind='barh', ax=ax)
                            ax.set_xlabel('Количество контрактов')
                            st.pyplot(fig)
                        else:
                            st.warning("Нет данных об ответственных лицах")
                        
                        # 5. Распределение сумм контрактов
                        st.subheader("Распределение сумм контрактов")
                        if not filtered_df['Сумма контракта'].empty:
                            fig, ax = plt.subplots(figsize=(10, 5))
                            sns.histplot(
                                filtered_df['Сумма контракта'].dropna(), 
                                bins=30, 
                                kde=True,
                                log_scale=True,
                                ax=ax
                            )
                            ax.set_xlabel('Сумма контракта (логарифмическая шкала)')
                            st.pyplot(fig)
                        
                        # 6. Топ поставщиков по сумме контрактов
                        st.subheader("Топ поставщиков по сумме контрактов")
                        if not filtered_df[['ИНН', 'Сумма контракта']].empty:
                            top_suppliers = filtered_df.groupby('ИНН')['Сумма контракта'].sum().nlargest(10)
                            fig, ax = plt.subplots(figsize=(10, 6))
                            top_suppliers.plot(kind='barh', ax=ax)
                            ax.set_title('Топ поставщиков по сумме контрактов')
                            ax.set_xlabel('Общая сумма контрактов')
                            st.pyplot(fig)

                        # 3. Топ закупок с наибольшей экономией
                        st.subheader("Топ-10 закупок с наибольшей экономией")
                        if not filtered_df.empty:
                            top_savings = filtered_df.nlargest(10, 'Сумма экономии')[['Название закупки', 'Сумма экономии', 'Закон']]
                            
                            fig, ax = plt.subplots(figsize=(12, 8))
                            sns.barplot(data=top_savings, y='Название закупки', x='Сумма экономии', hue='Закон', dodge=False)
                            ax.set_title('Топ-10 закупок с максимальной экономией')
                            ax.set_xlabel('Сумма экономии (руб)')
                            ax.set_ylabel('')
                            st.pyplot(fig)
                        
                    else:
                        st.warning("Не найдено ИНН для фильтрации таблицы.")
                else:
                    st.error(f"Файл {db_path} не найден в директории db.")

            else:
                st.warning("Архив пуст.")
        except Exception as e:
            st.error(f"Ошибка: {e}")

    # Удаление временных файлов
    if st.button("Очистить временные файлы"):
        try:
            clear_temp_files(file_path, extract_dir)
            st.success("Временные файлы удалены.")
        except Exception as e:
            st.error(f"Ошибка: {e}")
else:
    st.info("Пожалуйста, загрузите ZIP архив.")